from pathlib import Path
import httpx
import pytest
from backend.lab.provider import Alpaca,credentials,ProviderError,parse_actions

@pytest.fixture
def env(tmp_path):
    path=tmp_path/'.env';path.write_text('ALPACA_API_KEY=test-key\nALPACA_SECRET_KEY=test-secret\n')
    return path

def bar(t): return {'t':t,'o':100,'h':101,'l':99,'c':100,'v':1000}

def test_missing_credentials_never_echoes_values(tmp_path):
    with pytest.raises(ProviderError): credentials(tmp_path/'absent')

def test_all_symbols_paginated_and_cached(env,tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.headers['APCA-API-KEY-ID']=='test-key'
        if request.url.params.get('page_token')=='second':
            return httpx.Response(200,json={'bars':{'SPY':[bar('2022-01-03T14:30:00Z')]},'next_page_token':None})
        return httpx.Response(200,json={'bars':{'QQQ':[bar('2022-01-03T14:30:00Z')]},'next_page_token':'second'})
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(handler)) as client:
        frame,meta=client.bars(['SPY','QQQ'],'2022-01-03','2022-01-03')
        assert set(frame.symbol)=={'SPY','QQQ'} and len(calls)==2
        again,_=client.bars(['SPY','QQQ'],'2022-01-03','2022-01-03')
        assert len(again)==2 and len(calls)==2 and meta['feed']=='sip'

def test_no_silent_feed_switch_or_secret_error(env,tmp_path):
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(lambda r:httpx.Response(403,text='test-secret test-key'))) as client:
        with pytest.raises(ProviderError) as exc: client.bars(['SPY'],'2022-01-03','2022-01-03')
        assert '403' in str(exc.value) and 'test-secret' not in str(exc.value) and 'test-key' not in str(exc.value)
        with pytest.raises(ProviderError): client._request('/v2/orders',{})

def test_repeat_cursor_and_missing_symbol_rejected(env,tmp_path):
    response={'bars':{'QQQ':[bar('2022-01-03T14:30:00Z')]},'next_page_token':'same'}
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(lambda r:httpx.Response(200,json=response))) as client:
        with pytest.raises(ProviderError,match='repeated'): client.bars(['QQQ'],'2022-01-03','2022-01-03')

def test_missing_symbol_rejected_after_exhaustion(env,tmp_path):
    response={'bars':{'QQQ':[bar('2022-01-03T14:30:00Z')]},'next_page_token':None}
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(lambda r:httpx.Response(200,json=response))) as client:
        with pytest.raises(ProviderError,match='SPY'): client.bars(['QQQ','SPY'],'2022-01-03','2022-01-03')

def test_retry_and_cancel(env,tmp_path,monkeypatch):
    monkeypatch.setattr('backend.lab.provider.time.sleep',lambda s:None)
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(429 if len(calls)==1 else 200,json={'bars':{'SPY':[bar('2022-01-03T14:30:00Z')]}})
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(handler)) as client:
        assert len(client.bars(['SPY'],'2022-01-03','2022-01-03')[0])==1 and len(calls)==2
        with pytest.raises(InterruptedError): client.bars(['SPY'],'2022-01-03','2022-01-03',cancel=lambda:True)

def test_actions_widen_process_date_query_and_parse(env,tmp_path):
    def handler(request):
        assert request.url.params['end']>'2022-02-28'
        return httpx.Response(200,json={'corporate_actions':{'cash_dividends':[{'id':'a','symbol':'AAPL','ex_date':'2022-02-28','payable_date':'2022-03-08','rate':.22}]}})
    with Alpaca(env,tmp_path/'cache',httpx.MockTransport(handler)) as client:
        raw,_=client.corporate_actions(['AAPL'],'2022-02-01','2022-02-28')
    actions,issues=parse_actions(raw,'2022-02-01','2022-02-28')
    assert not issues and actions[0].pay_date=='2022-03-08'

def test_unknown_and_malformed_actions_not_ignored():
    raw={'forward_splits':[{'symbol':'AAPL','ex_date':'2022-01-04','new_rate':4,'old_rate':1}],
         'stock_mergers':[{'symbol':'AAPL','effective_date':'2022-01-05'}],
         'cash_dividends':[{'symbol':'SPY','rate':1}]}
    actions,issues=parse_actions(raw,'2022-01-01','2022-01-31')
    assert len(actions)==1 and actions[0].value==4 and len(issues)==2
