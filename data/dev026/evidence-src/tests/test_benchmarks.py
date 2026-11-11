"""Passive-book accounting contracts and actual guarded service/API/worker path."""
from datetime import date
from pathlib import Path
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from conftest import minute_frame
from backend.lab import service, models
from backend.lab.api import create_app
from backend.lab.config import Costs,Portfolio,Strategy
from backend.lab.data import Action,DataError,normalize,prepare,save_dataset
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.worker import Worker

SPEC=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/benchmark-contract.json').read_text())
ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=1000,risk_fraction=.01,symbol_exposure=1,total_exposure=1,participation=1)
DAYS=['2026-10-05','2026-10-06','2026-10-07']


def run(raw,actions=(),costs=ZERO,account=ACCOUNT,start=DAYS[0],end=DAYS[0],cancel=None):
    from backend.lab.benchmarks import compare_passive
    return compare_passive(prepare(normalize(raw)[0],actions),costs,account,actions,start,end,cancel)


def prices(day=DAYS[0],symbol='SPY',opened=100,closed=110):
    frame=minute_frame(day,symbol)
    frame.loc[frame.index[-1],['high','close']]=[closed+.1,closed]
    frame.loc[:,['open','low']]=[opened, min(opened,closed)-.1]
    frame.loc[:,'high']=max(opened,closed)+.1
    frame.loc[frame.index[:-1],'close']=opened
    return frame


def test_hand_round_trip_and_flat_cash_benchmark():
    c=SPEC['cases']['round_trip']
    result=run(prices(),costs=ZERO.model_copy(update={'commission_per_share':1}))
    book=result['buy_hold'];trade=book['trades'][0]
    assert trade['entry_quantity']==c['quantity'] and trade['fees']==c['fees']
    assert trade['net_pnl']==c['net_profit'] and book['metrics']['net_profit']==c['net_profit']
    assert book['equity'][-1]['cash']==c['cash']
    assert result['cash']['metrics']['net_profit']==0 and result['cash']['equity'][0]['equity']==1000
    assert trade['entry_at']==(prices().timestamp.iloc[1]).isoformat()
    assert trade['liquidity_reference_at']==prices().timestamp.iloc[0].isoformat()
    assert book['allocation'][0]['actual_entry_notional']==900


def test_split_then_distribution_entitlement_and_unpaid_receivable():
    c=SPEC['cases']['action_path']
    raw=pd.concat([prices(),prices(DAYS[1],opened=50,closed=55)],ignore_index=True)
    actions=[Action('SPY',DAYS[1],'split',2),Action('SPY',DAYS[1],'dividend',1,'2026-10-09')]
    book=run(raw,actions,end=DAYS[1])['buy_hold'];trade=book['trades'][0]
    assert trade['entry_quantity']==c['entry_quantity'] and trade['exit_quantity']==c['exit_quantity']
    assert trade['distributions']==c['dividend'] and trade['net_pnl']==c['net_profit']
    for field in ['cash','receivables','equity']:
        expected={'cash':c['cash_before_payment'],'receivables':c['receivable'],'equity':c['equity']}[field]
        assert book['equity'][-1][field]==expected
    assert sum(r['cash_change'] for r in book['ledger'])+ACCOUNT.capital==c['cash_before_payment']
    assert book['metrics']['net_profit']==c['net_profit']


def test_distribution_payment_and_fractional_split_do_not_invent_value():
    raw=pd.concat([prices(),prices(DAYS[1],opened=200,closed=210),prices(DAYS[2],opened=210,closed=210)],ignore_index=True)
    actions=[Action('SPY',DAYS[1],'split',.5),Action('SPY',DAYS[1],'dividend',2,DAYS[2])]
    book=run(raw,actions,end=DAYS[2])['buy_hold'];trade=book['trades'][0]
    assert trade['exit_quantity']==5 and trade['distributions']==10
    assert trade['net_pnl']==60 and book['equity'][-1]['receivables']==0
    assert book['equity'][-1]['equity']==1060


def test_entry_day_new_shares_have_no_distribution_entitlement():
    book=run(prices(),[Action('SPY',DAYS[0],'dividend',10)])['buy_hold']
    assert book['trades'][0]['distributions']==0


def test_prior_volume_cap_does_not_read_current_or_future_volume():
    raw=prices();raw.loc[0,'volume']=7;raw.loc[1:,'volume']=1_000_000
    book=run(raw,account=ACCOUNT.model_copy(update={'participation':.5}))['buy_hold']
    assert book['trades'][0]['entry_quantity']==3 and book['metrics']['net_profit']==30
    raw.loc[2:,'volume']=1
    assert run(raw,account=ACCOUNT.model_copy(update={'participation':.5}))['buy_hold']['trades']==book['trades']


def test_zero_volume_is_one_failed_attempt_not_a_favorable_later_entry():
    raw=prices();raw.loc[0,'volume']=0
    book=run(raw)['buy_hold']
    assert book['trades']==[] and book['metrics']['net_profit']==0 and len(book['rejected'])==1


def test_equal_weight_shared_account_is_order_invariant():
    c=SPEC['cases']['equal_weights']
    raw=pd.concat([prices(symbol='AAA'),prices(symbol='BBB',opened=50,closed=45)],ignore_index=True)
    first=run(raw);second=run(raw.iloc[::-1])
    assert first==second
    assert [t['entry_quantity'] for t in first['buy_hold']['trades']]==c['quantities']
    assert first['buy_hold']['metrics']['net_profit']==c['net_profit']
    assert [x['target_initial_weight'] for x in first['buy_hold']['allocation']]==[.5,.5]


def test_lower_symbol_and_aggregate_limits_leave_cash_visible():
    raw=pd.concat([prices(symbol='AAA'),prices(symbol='BBB')],ignore_index=True)
    book=run(raw,account=ACCOUNT.model_copy(update={'total_exposure':.6,'symbol_exposure':.2}))['buy_hold']
    assert [x['target_initial_weight'] for x in book['allocation']]==[.2,.2]
    assert [t['entry_quantity'] for t in book['trades']]==[2,2]
    assert book['metrics']['net_profit']==40
    assert book['allocation'][0]['uninvested_initial_allocation']==0


def test_warmup_can_supply_prior_volume_but_never_a_prior_entry():
    raw=pd.concat([prices(),prices(DAYS[1])],ignore_index=True)
    book=run(raw,start=DAYS[1],end=DAYS[1])['buy_hold']
    assert book['trades'][0]['entry_at']==prices(DAYS[1]).timestamp.iloc[0].isoformat()
    assert len(book['equity'])==1


def test_cancellation_returns_no_completed_partial_book():
    with pytest.raises(InterruptedError): run(prices(),cancel=lambda:True)


@pytest.fixture
def saved(tmp_path):
    lab=service.Lab(tmp_path)
    m=save_dataset(lab.datasets_root,prices(),{'input_kind':'synthetic','source':'Hand benchmark path'},start=DAYS[0],end=DAYS[0])
    request_class=getattr(models,'BenchmarkExperiment',None)
    assert request_class is not None,'Benchmark input contract must be implemented.'
    request=request_class(dataset_id=m['id'],name='Benchmark contract',start=DAYS[0],end=DAYS[0],costs=ZERO,portfolio=ACCOUNT)
    return lab,m,request


def test_real_service_worker_persistence_and_output_integrity(saved):
    lab,m,request=saved
    job=lab.create_benchmarks(request);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed'
    report=lab.report(job['id'])
    assert report['report_type']=='passive_benchmarks' and report['dataset_id']==m['id']
    assert report['benchmarks']['buy_hold']['metrics']['net_profit']==100
    assert report['core_hash']==job['payload']['core_hash']
    assert service.Lab(lab.root).report(job['id'])==report
    lab.output_path(job['id']).write_bytes(b'tampered')
    with pytest.raises(ValueError,match='integrity'): lab.report(job['id'])


def test_real_api_and_json_export(saved):
    lab,_,request=saved
    with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        created=client.post('/api/benchmarks',json=request.model_dump(mode='json'))
        assert created.status_code==202,created.text
        job=created.json();Worker(client.app.state.lab).run_once()
        report=client.get('/api/jobs/'+job['id']+'/report').json()
        assert report==client.get('/api/jobs/'+job['id']+'/export/json').json()
        assert report['benchmarks']['cash']['metrics']['net_profit']==0


def test_guard_before_any_benchmark_price_read(tmp_path,monkeypatch):
    lab=service.Lab(tmp_path)
    m=save_dataset(lab.datasets_root,pd.concat([minute_frame(d) for d in DAYS]),{'input_kind':'synthetic'},start=DAYS[0],end=DAYS[-1])
    lab.register_study(Study(name='Sealed',dataset_id=m['id'],discovery=dict(start=DAYS[0],end=DAYS[0]),
        validation=dict(start=DAYS[1],end=DAYS[1]),holdout=dict(start=DAYS[2],end=DAYS[2]),configurations=[Strategy()]))
    def forbidden(*args,**kwargs): raise AssertionError('Protected price read')
    monkeypatch.setattr(service,'load_window',forbidden)
    request_class=getattr(models,'BenchmarkExperiment',None)
    assert request_class is not None
    request=request_class(dataset_id=m['id'],start=DAYS[0],end=DAYS[-1])
    with pytest.raises(ResearchError): lab.create_benchmarks(request)
    with pytest.raises(ResearchError): lab.evaluate_benchmarks(m['id'],ZERO,ACCOUNT,DAYS[0],DAYS[-1])
    assert not lab.store.jobs()


def test_real_fractional_split_preserves_price_basis_and_cash():
    raw=pd.concat([prices(),prices(DAYS[1],opened=200,closed=210)],ignore_index=True)
    raw.loc[0,'volume']=3
    book=run(raw,[Action('SPY',DAYS[1],'split',.5)],end=DAYS[1])['buy_hold']
    trade=book['trades'][0]
    assert trade['entry_quantity']==3 and trade['exit_quantity']==1.5
    assert trade['net_pnl']==15 and book['equity'][-1]['cash']==1015


def test_passive_book_does_not_invent_a_stop_from_strategy_risk_fraction():
    raw=prices()
    assert run(raw)==run(raw,account=ACCOUNT.model_copy(update={'risk_fraction':.1}))


def test_cancel_resume_matches_full_account_and_detects_changed_manifest(saved,monkeypatch):
    lab,_,request=saved
    direct=lab.evaluate_benchmarks(request.dataset_id,ZERO,ACCOUNT,DAYS[0],DAYS[0])
    job=lab.create_benchmarks(request);original=lab.evaluate_benchmarks
    def interrupt(*args,**kwargs):
        lab.store.cancel(job['id']);return original(*args,**kwargs)
    monkeypatch.setattr(lab,'evaluate_benchmarks',interrupt)
    Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='canceled' and not lab.output_path(job['id']).exists()
    monkeypatch.setattr(lab,'evaluate_benchmarks',original)
    lab.store.resume(job['id']);Worker(lab).run_once()
    assert lab.report(job['id'])==direct
    with pytest.raises(DataError,match='manifest changed'):
        lab.evaluate_benchmarks(request.dataset_id,ZERO,ACCOUNT,DAYS[0],DAYS[0],expected_manifest='0'*64)


def test_no_evaluation_session_rejects_instead_of_a_zero_success():
    with pytest.raises(DataError,match='No eligible sessions'):
        run(prices(),start=DAYS[1],end=DAYS[1])


def test_single_observation_without_prior_volume_remains_cash():
    book=run(prices().iloc[:1])['buy_hold']
    assert book['trades']==[] and book['equity'][0]['equity']==1000
    assert len(book['rejected'])==1 and 'prior completed volume' in book['rejected'][0]['reason']


def test_warmup_only_instrument_is_not_bought_in_evaluation():
    raw=pd.concat([prices(symbol='AAA'),prices(DAYS[1],symbol='BBB')],ignore_index=True)
    book=run(raw,start=DAYS[1],end=DAYS[1])['buy_hold']
    assert [t['symbol'] for t in book['trades']]==['BBB']
    assert book['allocation'][0]['target_initial_weight']==1
