"""Authored saved-output expectations; no production-derived golden results."""
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import pytest


def account():
    return dict(report_type='single_strategy',start='2026-10-05',end='2026-10-06',
        provenance={'input_kind':'synthetic'},portfolio={'capital':1000},
        costs={'spread_bps':2,'slippage_bps':1,'borrow_annual':0.03},
        metrics={'net_profit':-12.25,'max_drawdown':0.02,'trades':2,'win_rate':0.5,
            'daily_pnl':[-20,7.75],'profit_without_ten_best_days':0,'marked_sharpe':None},
        equity=[{'date':'2026-10-05','equity':980},{'date':'2026-10-06','equity':987.75}],
        trades=[{'fees':1.25,'borrow':0.1},{'fees':1.5,'borrow':0.2}],
        charts={'SECRET_RAW_CANDLE':[]},ledger=[{'secret_nonpublic':'do-not-embed'}])


def blob(value):return json.dumps(value,allow_nan=False).encode()


def build(value=None):
    from backend.lab.presenter import build_deck
    return build_deck([('saved/report.json',blob(account() if value is None else value))])


def test_account_facts_and_private_projection():
    deck=build();facts=deck['facts'];texts=[f['text'] for f in facts.values()]
    assert '-$12.25' in texts and '2.00%' in texts and '3.00%' in texts
    assert '$980.00' in texts and '$987.75' in texts and 'Undefined' in texts
    serialized=json.dumps(deck)
    assert 'SECRET_RAW_CANDLE' not in serialized and 'do-not-embed' not in serialized
    assert deck['sources'][0]['sha256']==hashlib.sha256(blob(account())).hexdigest()
    assert any('lost money' in p['conclusion'] for p in deck['pages'])
    assert all(len(p.get('stats',[]))<=2 for p in deck['pages'])


def test_separate_decimal_audit_rejects_tampered_value_format_path_and_text():
    from backend.lab.presentation_audit import audit_deck,PresentationAuditError
    original=blob(account());deck=build()
    assert audit_deck({'saved/report.json':original},deck)['facts_checked']==len(deck['facts'])
    fid=next(k for k,v in deck['facts'].items() if v['path']==['metrics','net_profit'])
    for key,value in [('value',12.25),('value','-12.25'),('text','$12.25'),('format','percent'),('path',['metrics','unknown'])]:
        changed=deepcopy(deck);changed['facts'][fid][key]=value
        with pytest.raises(PresentationAuditError):audit_deck({'saved/report.json':original},changed)
    changed=deepcopy(deck);changed['pages'][0]['title']='Profit 999'
    with pytest.raises(PresentationAuditError):audit_deck({'saved/report.json':original},changed)
    with pytest.raises(PresentationAuditError):audit_deck({'saved/report.json':blob(account()|{'end':'2026-10-07'})},deck)


@pytest.mark.parametrize('number',[float('nan'),float('inf'),-float('inf')])
def test_nonfinite_source_rejects(number):
    from backend.lab.presenter import build_deck,PresentationError
    with pytest.raises(PresentationError):build_deck([('report.json',json.dumps({'value':number}).encode())])


@pytest.mark.parametrize('name',['../report.json','/absolute.json','C:/private.json','report\\file.json','.env','https://evil.test/a'])
def test_unsafe_source_name(name):
    from backend.lab.presenter import build_deck,PresentationError
    with pytest.raises(PresentationError):build_deck([(name,blob(account()))])


def test_duplicate_json_sources_unknown_type_and_missing_values_fail_closed():
    from backend.lab.presenter import build_deck,PresentationError
    for sources in [[],[('a.json',b'{"report_type":"single_strategy","report_type":"other"}')],
        [('a.json',blob(account())),('a.json',blob(account()))], [('a.json',blob({'report_type':'unknown'}))]]:
        with pytest.raises(PresentationError):build_deck(sources)
    damaged=account();del damaged['metrics']['net_profit']
    with pytest.raises(PresentationError):build(damaged)


def test_escaped_inert_offline_document_and_determinism():
    from backend.lab.presenter import render_html
    value=account();value['provenance']['input_kind']='</script><img src=x onerror=alert(1)>'
    deck=build(value);html=render_html(deck)
    assert html==render_html(deck)
    assert '</script><img' not in html and '\\u003c/script' in html
    from html import unescape
    assert 'connect-src \'none\'' in unescape(html) and "object-src 'none'" in unescape(html)
    assert 'https://cdn.' not in html and 'fetch(' not in html and 'eval(' not in html
    assert 'getUserMedia' not in html and 'innerHTML' not in html
    assert 'id="presentation-manifest"' in html and 'id="camera-guide"' in html


def test_null_zero_negative_and_half_even_formats():
    from backend.lab.presenter import format_value
    from backend.lab.presentation_audit import independent_format
    expected=[(None,'currency','Undefined'),(0,'currency','$0.00'),(-12.25,'currency','-$12.25'),
        (1.225,'number','1.22'),(1.235,'number','1.24'),(0.015,'percent','1.50%'),(2,'integer','2')]
    for raw,fmt,text in expected:
        assert format_value(raw,fmt)==text
        assert independent_format(None if raw is None else Decimal(str(raw)),fmt)==text


def test_all_behavior_rows_and_labels_retained_without_raw_records():
    rows=[dict(scope='instrument',subset='SPY',category='all',metric='forward_close_move_ATR',horizon=i,
        real_mean=0.2,control_mean=0.3,difference=-0.1,interval_low=-0.5,interval_high=0.2,
        real_n=4,control_n=8,unit='ATR',status='interval includes zero') for i in range(1,14)]
    value=dict(report_type='price_behavior',start='2026-10-05',end='2026-10-06',
        tables={'bos_forward':{'rows':rows}},provenance={'input_kind':'synthetic'},charts=[{'raw':'excluded'}])
    deck=build(value)
    ptrs={tuple(f['path']) for f in deck['facts'].values()}
    assert all(('tables','bos_forward','rows',i,'difference') in ptrs for i in range(13))
    assert all(('tables','bos_forward','rows',i,'real_n') in ptrs for i in range(13))
    assert 'excluded' not in json.dumps(deck)
    assert len([p for p in deck['pages'] if p.get('chart',{}).get('kind')=='differences'])==3


def test_nullable_behavior_category_is_a_sourced_undefined_value():
    row=dict(scope='pooled',subset=None,category=None,metric='hold_fraction',horizon=10,
        real_mean=None,control_mean=None,difference=None,interval_low=None,interval_high=None,
        real_n=0,control_n=0,unit='fraction',status='insufficient evidence')
    deck=build(dict(report_type='price_behavior',tables={'levels':{'rows':[row]}}))
    for field in ['subset','category']:
        fact=next(f for f in deck['facts'].values() if f['path']==['tables','levels','rows',0,field])
        assert fact['value'] is None and fact['text']=='Undefined'


@pytest.mark.parametrize('report_type', ['paired_ablations','matched_random_controls','passive_benchmarks','shared_capital_portfolio'])
def test_other_saved_report_adapters(report_type):
    a=account()
    if report_type=='shared_capital_portfolio':value=a|{'report_type':report_type}
    elif report_type=='paired_ablations':value=dict(report_type=report_type,start=a['start'],end=a['end'],
        comparison_rows=[dict(field='target_r',baseline_value=2,alternative_value=3,baseline_net_profit=-20,
            alternative_net_profit=-10,net_difference=10,interval_low=None,interval_high=None,sessions=2,status='Insufficient sessions')])
    elif report_type=='matched_random_controls':value=dict(report_type=report_type,start=a['start'],end=a['end'],
        comparison=dict(real_net_profit=-20,mean_control_net_profit=-10,net_difference=-10,control_accounts=2,
            exceedance_fraction=1,paired_pnl_interval=None))
    else:value=dict(report_type=report_type,start=a['start'],end=a['end'],benchmarks={'cash':a,'buy_hold':a})
    deck=build(value)
    assert deck['pages'] and deck['audit']['facts_checked']==len(deck['facts'])


def test_search_summary_rows_have_each_window_and_no_implied_final_win():
    value={'rows':[{'part':0,'config_id':'a','discovery':{'net_profit':-10,'trades':2,'marked_sharpe':None},
        'validation':{'net_profit':-5,'trades':1,'marked_sharpe':None},'passed':False}],
        'job_id':'authored-search','funnel':{'sampled':1,'passed':0}}
    deck=build(value)
    assert all('survived' not in p['conclusion'] for p in deck['pages'])
    texts=[f['text'] for f in deck['facts'].values()];assert '-$10.00' in texts and '-$5.00' in texts


def test_series_and_source_limits_reject_without_truncation():
    from backend.lab.presenter import build_deck,PresentationError
    value=account();value['equity']*=5001
    with pytest.raises(PresentationError):build(value)
    with pytest.raises(PresentationError):build_deck([(str(i)+'.json',blob(account())) for i in range(17)])


def test_exponent_overflow_in_an_unused_field_rejects_entire_source():
    from backend.lab.presenter import build_deck,PresentationError
    raw=blob(account())[:-1]+b',"unused":1e999}'
    with pytest.raises(PresentationError):build_deck([('report.json',raw)])


def test_boolean_ablation_labels_and_dates_are_sourced():
    a=account()
    value=dict(report_type='paired_ablations',start=a['start'],end=a['end'],comparison_rows=[dict(field='gap_filter',
        baseline_value=False,alternative_value=True,baseline_net_profit=-20,alternative_net_profit=-10,net_difference=10,
        interval_low=None,interval_high=None,status='Insufficient sessions')])
    deck=build(value);texts=[f['text'] for f in deck['facts'].values()]
    assert 'Enabled' in texts and 'Disabled' in texts and a['start'] in texts and a['end'] in texts


def test_independent_reader_rejects_unused_facts_and_wrong_typed_row():
    from backend.lab.presentation_audit import audit_deck,PresentationAuditError
    deck=build();changed=deepcopy(deck);changed['facts']['unused']=next(iter(changed['facts'].values()))
    with pytest.raises(PresentationAuditError):audit_deck({'saved/report.json':blob(account())},changed)
    changed=deepcopy(deck);f=next(x for x in changed['facts'].values() if x['row']==0);f['row']=False
    with pytest.raises(PresentationAuditError):audit_deck({'saved/report.json':blob(account())},changed)
