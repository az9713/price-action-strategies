"""Actual shared-account service/API/worker paths with independent reference parity."""
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import csv
import io
import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import minute_frame
from backend.lab.api import create_app
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import save_dataset,normalize,prepare,DataError
from backend.lab.models import PortfolioExperiment,Study
from backend.lab.research import ResearchError
from backend.lab.service import Lab
from backend.lab.worker import Worker
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
from verification.strategy_fixtures import SPEC

ROOT=Path(__file__).resolve().parents[1]
SPECIFICATION=json.loads((ROOT/'verification/fixtures/portfolio-contract.json').read_text())
ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=10000,risk_fraction=.1,symbol_exposure=1,total_exposure=1,participation=1)
CONFIGS=[Strategy(family='break_of_structure',timeframe='1m',direction='long',swing_strength=2,
    stop_reference='level',stop_buffer=0,max_hold=0,target=target) for target in ['1R','5R']]


@pytest.fixture
def portfolio_data(tmp_path):
    raw=minute_frame(SPECIFICATION['date'])
    raw[['open','high','low','close']]=[96.,96.1,95.9,96.]
    for i,value in enumerate(SPEC['common_closes']):
        close=Decimal(str(value))
        raw.loc[i,['open','high','low','close']]=[float(close-Decimal('.02')),float(close+Decimal('.1')),float(close-Decimal('.1')),float(close)]
    lab=Lab(tmp_path);manifest=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Authored shared-account contract'},
        start=SPECIFICATION['date'],end=SPECIFICATION['date'])
    return lab,manifest,prepare(normalize(raw)[0])


def request(manifest,configs=None):
    return PortfolioExperiment(name='Two rules,one account',dataset_id=manifest['id'],
        configurations=CONFIGS if configs is None else configs,costs=ZERO,portfolio=ACCOUNT,
        start=SPECIFICATION['date'],end=SPECIFICATION['date'])


def complete(lab,value):
    job=lab.create_portfolio(value);assert Worker(lab).run_once()
    final=lab.store.job(job['id']);assert final['status']=='completed',final['error']
    return job,lab.report(job['id'])


def reference(report,frame):
    configs={c['config_id']:c['config'] for c in report['configurations']}
    expected=execute(primitive(frame),report['signals'],configs,report['costs'],report['portfolio'],start=report['start'],end=report['end'])
    assert_parity(SimpleNamespace(**report),expected)
    return expected


def test_actual_portfolio_matches_hand_cash_competition_and_independent_reference(portfolio_data):
    lab,m,frame=portfolio_data;_,report=complete(lab,request(m));expected=reference(report,frame)
    hand=SPECIFICATION['expected']
    assert len(report['signals'])==hand['signals'] and len(expected['trades'])==hand['shared_trades']
    trade=expected['trades'][0]
    for key in ['entry_quantity','entry_price','exit_price']:
        assert trade[key]==Decimal(str(hand[key]))
    assert trade['net_pnl']==Decimal(hand['net_profit'])
    assert report['metrics']['net_profit']==pytest.approx(float(hand['net_profit']),abs=1e-7)
    assert trade['strategy_id']==min(identity(c) for c in CONFIGS)
    assert report['report_type']=='shared_capital_portfolio' and report['config'] is None
    assert sum(r['trades'] for r in report['attribution'])==1
    assert sum(r['closed_trade_net_profit'] for r in report['attribution'])==pytest.approx(report['metrics']['net_profit'],abs=1e-7)
    independently_reset=[lab.evaluate(m['id'],c,ZERO,ACCOUNT,report['start'],report['end']) for c in CONFIGS]
    independent_sum=sum(r['metrics']['net_profit'] for r in independently_reset)
    assert independent_sum==pytest.approx(float(hand['independent_sum']),abs=1e-7)
    assert independent_sum!=pytest.approx(report['metrics']['net_profit'])


def test_configuration_order_does_not_change_allocation_or_report(portfolio_data):
    lab,m,_=portfolio_data
    first,a=complete(lab,request(m));second,b=complete(lab,request(m,list(reversed(CONFIGS))))
    assert first['payload']==second['payload'] and a==b


def test_single_rule_portfolio_equals_the_same_independent_account(portfolio_data):
    lab,m,frame=portfolio_data;_,portfolio=complete(lab,request(m,CONFIGS[:1]))
    single=lab.evaluate(m['id'],CONFIGS[0],ZERO,ACCOUNT,portfolio['start'],portfolio['end'])
    for key in ['trades','ledger','equity','rejected','metrics']:
        assert portfolio[key]==single[key]
    reference(portfolio,frame)


def test_each_rule_saves_its_own_chart_clock(portfolio_data):
    lab,m,_=portfolio_data;configs=[CONFIGS[0],CONFIGS[0].model_copy(update={'timeframe':'5m'})]
    _,report=complete(lab,request(m,configs))
    assert len(report['chart_sets'][identity(configs[0])]['SPY'])==390
    assert len(report['chart_sets'][identity(configs[1])]['SPY'])==78
    assert report['charts']=={}
    for trade in report['trades']:
        assert report['chart_sets'][trade['strategy_id']][trade['symbol']]


@pytest.mark.parametrize('configs',[[],[CONFIGS[0],CONFIGS[0]],[CONFIGS[0]]*65])
def test_empty_duplicate_and_oversized_portfolios_reject(portfolio_data,configs):
    _,m,_=portfolio_data
    with pytest.raises(ValidationError): request(m,configs)


def test_public_evaluator_cannot_bypass_unique_rule_validation(portfolio_data):
    lab,m,_=portfolio_data
    for configs in [[],[CONFIGS[0],CONFIGS[0]]]:
        with pytest.raises(DataError): lab.evaluate_portfolio(m['id'],configs,ZERO,ACCOUNT,SPECIFICATION['date'],SPECIFICATION['date'])


def test_actual_api_portfolio_and_json_csv_exports(portfolio_data):
    lab,m,_=portfolio_data;app=create_app(lab.root,run_worker=False)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        value=request(m).model_dump(mode='json');created=client.post('/api/portfolios',json=value)
        assert created.status_code==202;job=created.json();assert job['kind']=='portfolio'
        assert job['payload']['configuration_count']==2
        assert 'configurations' not in job['payload']
        Worker(app.state.lab).run_once()
        report=client.get('/api/jobs/'+job['id']+'/report').json()
        assert report['report_type']=='shared_capital_portfolio' and report['metrics']['trades']==1
        assert client.get('/api/jobs/'+job['id']+'/export/json').json()==report
        rows=list(csv.DictReader(io.StringIO(client.get('/api/jobs/'+job['id']+'/export/csv').text)))
        assert len(rows)==1 and rows[0]['strategy_id']==report['trades'][0]['strategy_id']
        value['configurations']*=2
        assert client.post('/api/portfolios',json=value).status_code==422


def test_portfolio_does_not_bypass_sealed_dates_before_any_price_read(tmp_path,monkeypatch):
    lab=Lab(tmp_path);days=['2026-10-05','2026-10-06','2026-10-07']
    m=save_dataset(lab.datasets_root,pd.concat([minute_frame(d) for d in days]),{'input_kind':'synthetic'},start=days[0],end=days[-1])
    lab.register_study(Study(name='Sealed',dataset_id=m['id'],discovery={'start':days[0],'end':days[0]},
        validation={'start':days[1],'end':days[1]},holdout={'start':days[2],'end':days[2]},configurations=[CONFIGS[0]],minimum_trades=1))
    def forbidden(*args,**kwargs): raise AssertionError('Protected price read')
    monkeypatch.setattr('backend.lab.service.load_window',forbidden)
    value=request(m);value.end=pd.Timestamp(days[-1]).date()
    with pytest.raises(ResearchError): lab.create_portfolio(value)
    with pytest.raises(ResearchError): lab.evaluate_portfolio(m['id'],CONFIGS,ZERO,ACCOUNT,days[0],days[-1])
    assert not lab.store.jobs()


def test_cancel_resume_reexecutes_one_account_and_matches_uninterrupted(portfolio_data,monkeypatch):
    lab,m,_=portfolio_data;value=request(m);_,uninterrupted=complete(lab,value)
    job=lab.create_portfolio(value);original=lab.evaluate_portfolio
    def cancel_before_calculation(*args,**kwargs):
        lab.store.cancel(job['id']);return original(*args,**kwargs)
    monkeypatch.setattr(lab,'evaluate_portfolio',cancel_before_calculation)
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='canceled'
    assert not lab.output_path(job['id']).exists()
    monkeypatch.setattr(lab,'evaluate_portfolio',original);lab.store.resume(job['id']);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed' and lab.report(job['id'])==uninterrupted


def test_manifest_or_file_tampering_prevents_portfolio_output(portfolio_data):
    lab,m,_=portfolio_data;job=lab.create_portfolio(request(m))
    path=lab.datasets_root/m['id']/'minutes.parquet';path.write_bytes(path.read_bytes()+b'corrupt')
    Worker(lab).run_once();finished=lab.store.job(job['id'])
    assert finished['status']=='failed' and 'hash mismatch' in finished['error'] and not lab.output_path(job['id']).exists()
