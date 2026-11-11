"""Actual request/job/worker/storage borrowing checks; synthetic prices are explicit."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from backend.lab import models
from backend.lab.borrow import BorrowScenario
from backend.lab.config import Costs,Strategy,identity
from backend.lab.data import DataError,save_dataset,prepare,normalize
from backend.lab.worker import Worker
from test_api import client_lab,seed,payload,study_payload
from test_random_controls import saved
from test_borrow import scenario,event
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute


def full_scenario(**changes):
    return scenario(start='2026-11-02',end='2026-11-06',**changes)


def test_actual_validate_api_canonicalizes_states_and_rejects_duplicate_json(client_lab):
    client,lab=client_lab
    value=full_scenario(events=[event('2026-11-04T09:31:00-05:00')])
    r=client.post('/api/borrow-scenarios/validate',json=value);assert r.status_code==200,r.text
    result=r.json();assert result['scenario']['events'][0]['effective_at']=='2026-11-04T14:31:00+00:00'
    assert result['scenario_id']==identity(result['scenario']) and lab.store.jobs()==[]
    duplicate=json.dumps(value)[:-1]+',"name":"conflicting duplicate"}'
    assert client.post('/api/borrow-scenarios/validate',content=duplicate,headers={'content-type':'application/json'}).status_code==409
    for change in [dict(events=[event('2026-11-04T14:31:00')]),dict(symbols=['../outside']),dict(events=[event('2026-11-04T14:31:00Z',rate=6)])]:
        assert client.post('/api/borrow-scenarios/validate',json=value|change).status_code==422
    assert lab.store.jobs()==[]


@pytest.mark.parametrize('kind',['experiment','search','portfolio','controls','ablation','benchmark'])
@pytest.mark.parametrize('fault',['incomplete','missing_symbol','coverage'])
def test_every_account_creation_rejects_bad_borrow_scope_before_prices(client_lab,monkeypatch,kind,fault):
    client,lab=client_lab;m=seed(lab);spec=full_scenario()
    if fault=='incomplete':spec['complete']=False
    elif fault=='missing_symbol':spec['symbols']=['QQQ']
    else:spec['start']='2026-11-03'
    inputs=payload(m)|dict(costs=Costs(borrow_scenario=spec).model_dump())
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Invalid borrowing scope reached raw prices.'))
    names=dict(experiment=(models.Experiment,lab.create_experiment),search=(models.Search,lab.create_experiment),
        portfolio=(models.PortfolioExperiment,lab.create_portfolio),controls=(models.ControlsExperiment,lab.create_controls),
        ablation=(models.AblationExperiment,lab.create_ablation),benchmark=(models.BenchmarkExperiment,lab.create_benchmarks))
    cls,create=names[kind]
    if kind in {'portfolio','benchmark'}:inputs.pop('strategy')
    if kind=='portfolio':inputs['configurations']=[Strategy().model_dump()]
    if kind=='search':inputs['count']=2
    with pytest.raises(DataError):create(cls(**inputs))
    assert lab.store.jobs()==[]


@pytest.mark.parametrize('side',[-1,1])
def test_actual_nonempty_single_worker_freezes_costs_and_matches_independent_account(saved,side):
    lab,m,request,frame=saved
    if side<0:
        raw=frame[['symbol','timestamp','open','high','low','close','volume']].copy()
        raw[['open','high','low','close']]=raw.assign(open=200-raw.open,high=200-raw.low,low=200-raw.high,close=200-raw.close)[['open','high','low','close']]
        m=save_dataset(lab.datasets_root,raw,dict(input_kind='synthetic',source='Mirrored authored borrow integration'))
        frame=prepare(normalize(raw)[0])
    rule=scenario(start='2026-10-05',end='2026-10-05',events=[event('2026-10-05T13:30:00Z')])
    cfg=Strategy(**(request.strategy.model_dump()|dict(direction='short' if side<0 else 'long')))
    costs=Costs(**(request.costs.model_dump()|dict(borrow_scenario=rule)))
    inputs={k:v for k,v in request.model_dump(mode='json').items() if k!='replicas'}
    job=lab.create_experiment(models.Experiment(**(inputs|dict(dataset_id=m['id'],costs=costs.model_dump(),strategy=cfg.model_dump()))))
    frozen=deepcopy(job['payload']);rule['name']='Later external edit'
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    assert lab.store.job(job['id'])['payload']==frozen
    report=lab.report(job['id']);assert report['costs']==frozen['costs'] and report['trades']
    assert all(t['side']==side for t in report['trades'])
    if side<0:assert sum(t['borrow'] for t in report['trades'])>0
    else:assert sum(t['borrow'] for t in report['trades'])==0
    expected=execute(primitive(frame),[s|dict(config_id=identity(cfg)) for s in report['signals']],{identity(cfg):cfg.model_dump()},costs.model_dump(),request.portfolio.model_dump(),start=str(request.start),end=str(request.end))
    assert_parity(SimpleNamespace(**report),expected)


def test_queued_borrow_cost_tamper_is_blocked_before_prices(client_lab,monkeypatch):
    client,lab=client_lab;m=seed(lab)
    job=lab.create_experiment(models.Experiment(**(payload(m)|dict(costs=Costs(borrow_scenario=full_scenario()).model_dump()))))
    altered=deepcopy(job['payload']);altered['costs']['borrow_scenario']['name']='Tampered'
    with lab.store.db() as db:db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(altered),job['id']))
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Tampered costs reached prices.'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()


@pytest.mark.parametrize('corrupt',[False,True])
def test_study_freeze_and_final_preconsume_borrow_guard(client_lab,monkeypatch,corrupt):
    client,lab=client_lab;m=seed(lab);inputs=study_payload(m)
    inputs['costs']=Costs(borrow_scenario=full_scenario()).model_dump()
    sid=lab.register_study(models.Study(**inputs))['id']
    assert lab.guard.study(sid)['spec']['costs']==inputs['costs']
    # Explicit state-transition fixture; flat synthetic prices did not pass screening.
    lab.guard.screened(sid,'borrow-test-only-injected-candidate',[Strategy().model_dump()]);job=lab.final(sid)
    if corrupt:
        spec=lab.guard.study(sid)['spec'];spec['costs']['borrow_scenario']['complete']=False
        with lab.store.db() as db:db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(spec),sid))
        monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Invalid frozen borrowing reached final prices.'))
    Worker(lab).run_once()
    if corrupt:
        assert lab.store.job(job['id'])['status']=='failed'
        assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
    else:
        assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
        assert lab.report(job['id'],0)['costs']==inputs['costs']
        assert lab.guard.study(sid)['status']=='final_complete'


def test_presenter_preserves_every_borrow_input_as_independently_resolved_fact():
    from test_presenter import account,blob
    from backend.lab.presenter import build_deck,render_html
    from backend.lab.presentation_audit import audit_deck
    value=account();spec=scenario(start='2026-10-05',end='2026-10-06',symbols=['SPY','QQQ'],name='Scenario <img src=x onerror=alert(1)>',note='Authored note',events=[
        event('2026-10-05T14:00:00Z'),event('2026-10-05T14:01:00Z',available=False,recall=True),event('2026-10-06T14:00:00Z',symbol='QQQ')])
    value['costs']=Costs(borrow_scenario=spec).model_dump();raw=blob(value)
    deck=build_deck([('saved/report.json',raw)]);audit=audit_deck({'saved/report.json':raw},deck)
    paths={tuple(f['path']) for f in deck['facts'].values()}
    for i in range(len(spec['events'])):
        for field in ['symbol','effective_at','annual_rate','available','recall']:assert ('costs','borrow_scenario','events',i,field) in paths
    for i in range(len(spec['symbols'])):assert ('costs','borrow_scenario','symbols',i) in paths
    document=render_html(deck)
    assert audit['facts_checked']==len(deck['facts']) and '\\u003cimg' in document and '<img' not in document


@pytest.mark.parametrize('fault',['cancel','shutdown','corrupt_part'])
def test_search_recovery_preserves_frozen_borrowing_and_verified_part(saved,monkeypatch,fault):
    lab,m,request,frame=saved
    spec=scenario(start='2026-10-05',end='2026-10-05',events=[event('2026-10-05T13:30:00Z')])
    inputs={k:v for k,v in request.model_dump(mode='json').items() if k!='replicas'}
    req=models.Search(**(inputs|dict(costs=Costs(**(request.costs.model_dump()|dict(borrow_scenario=spec))).model_dump(),count=2,timeframes=['1m'])))
    job=lab.create_experiment(req);frozen=deepcopy(job['payload']);worker=Worker(lab);original=worker._progress
    def interrupt(j,f,n,checkpoint=None):
        original(j,f,n,checkpoint)
        if checkpoint==1:
            if fault=='shutdown':worker.shutdown.set()
            else:lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',interrupt);worker.run_once()
    assert lab.store.job(job['id'])['status']==('queued' if fault=='shutdown' else 'canceled')
    part=lab.output_path(job['id']).parent/'parts/000000.json.gz';raw=part.read_bytes()
    req.costs.borrow_scenario.name='Changed external request after checkpoint'
    if fault=='corrupt_part':
        part.write_bytes(raw+b'authored corruption')
        monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Corrupt committed part reached prices.'))
    if fault!='shutdown':lab.store.resume(job['id'])
    Worker(lab).run_once();finished=lab.store.job(job['id']);assert finished['payload']==frozen
    if fault=='corrupt_part':assert finished['status']=='failed' and not lab.output_path(job['id']).exists()
    else:
        assert finished['status']=='completed',finished['error']
        assert part.read_bytes()==raw
        for row in lab.result(job['id'])['rows']:assert lab.report(job['id'],row['part'])['costs']==frozen['costs']
