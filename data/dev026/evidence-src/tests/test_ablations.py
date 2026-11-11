"""One-field and independent complete-session/account comparison contracts."""
from pathlib import Path
from copy import deepcopy
import json
import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from backend.lab import models,service
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import DataError,save_dataset
from backend.lab.worker import Worker
from backend.lab.api import create_app
from backend.lab.models import Study
from backend.lab.research import ResearchError
from fastapi.testclient import TestClient
from verification.reference_statistics import linear_quantile
from verification.strategy_fixtures import SPEC
from conftest import minute_frame

DAYS=['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12']

def request(**changes):
    cls=getattr(models,'AblationExperiment',None);assert cls is not None
    return cls(**(dict(dataset_id='a'*24,start=DAYS[0],end=DAYS[-1],strategy=Strategy(),field='target',alternatives=['2R','3R'])|changes))

def report(pnl,target='1R',trades=2):
    cfg=Strategy(target=target);value=1000;equity=[]
    for day,change in zip(DAYS,pnl):value+=change;equity.append(dict(date=day,equity=value))
    return dict(report_type='single_strategy',config=cfg.model_dump(),config_id=identity(cfg),dataset_id='a'*24,
        dataset_manifest_hash='b'*64,core_hash='c'*64,start=DAYS[0],end=DAYS[-1],costs=Costs().model_dump(),
        portfolio=Portfolio(capital=1000).model_dump(),news_dates=None,seed=42,equity=equity,
        trades=[dict(net_pnl=sum(pnl)/trades) for _ in range(trades)],
        signals=[dict(symbol='SPY',side=1,available_at=day+'T15:00:00+00:00') for day in DAYS[:2]],
        metrics=dict(trades=trades,net_profit=sum(pnl),daily_pnl=pnl,marked_sharpe=None,max_drawdown=.1))

def compare(a,b):
    from backend.lab.ablations import paired_comparison
    return paired_comparison(a,b,'target',42)

def test_ablation_freezes_only_one_validated_public_field():
    req=request();arms=req.arms();assert arms[0]==req.strategy
    assert len(arms)==3
    for arm in arms[1:]:assert [k for k,v in arm.model_dump().items() if v!=req.strategy.model_dump()[k]]==['target']
    assert {a.target for a in arms}=={'1R','2R','3R'}
    assert [a.model_dump() for a in request(alternatives=['3R','2R']).arms()]==[a.model_dump() for a in arms]

@pytest.mark.parametrize('changes',[
    dict(field='unknown'),dict(alternatives=[]),dict(alternatives=['1R']),dict(alternatives=['2R','2R']),
    dict(alternatives=['bad']),dict(field='confirmation',alternatives=['lower_bos']),
    dict(field='news',alternatives=['skip']),dict(news_dates=[DAYS[0]]),dict(alternatives=[{}]),
    dict(field='stop_reference',alternatives=['gap']),dict(alternatives=['2R']*33),
    dict(field='limit_expiry',alternatives=[1]),dict(field='confirmation_window',alternatives=[1])])
def test_ablation_invalid_or_coupled_settings_reject(changes):
    with pytest.raises(ValidationError):request(**changes)

def test_paired_daily_dollar_difference_and_bootstrap_are_independent():
    a=report([10,-5,2,0,4,-1]);b=report([20,-7,4,0,-2,3],'2R');actual=compare(a,b)
    diff=[10,-2,2,0,-6,4];expected=[]
    for draw in np.random.default_rng(42).integers(0,6,size=(2000,2)):
        sample=[]
        for start in draw:sample.extend(diff[(int(start)+j)%6] for j in range(5))
        expected.append(sum(sample[:6]))
    assert actual['net_difference']==8 and [r['difference'] for r in actual['daily_differences']]==diff
    assert actual['paired_pnl_interval']['low']==pytest.approx(linear_quantile(expected,.025),abs=1e-10)
    assert actual['paired_pnl_interval']['high']==pytest.approx(linear_quantile(expected,.975),abs=1e-10)
    assert actual['common_decision_signals']==2

def test_paired_negative_zero_and_no_trade_results_remain_explicit():
    a=report([10,-5,2,0,4,-1]);quiet=report([0]*6,'2R',0)
    result=compare(a,quiet);assert result['net_difference']==-10 and result['paired_pnl_interval'] is None
    same=report([10,-5,2,0,4,-1],'2R');result=compare(a,same)
    assert result['net_difference']==0 and result['paired_pnl_interval']['low']==result['paired_pnl_interval']['high']==0

def test_one_resampling_block_is_not_reported_as_precise_uncertainty():
    a=report([10,-5,2,0,4,-1]);b=report([20,-7,4,0,-2,3],'2R')
    for r in [a,b]:
        r['end']=DAYS[2];r['equity']=r['equity'][:3];r['metrics']['daily_pnl']=r['metrics']['daily_pnl'][:3]
        net=r['equity'][-1]['equity']-r['portfolio']['capital'];r['metrics']['net_profit']=net;r['trades']=[dict(net_pnl=net/2)]*2
    result=compare(a,b)
    assert result['net_difference']==10 and result['paired_pnl_interval'] is None

@pytest.mark.parametrize('kind',['configuration_hash','naive_clock','bad_side','news','paired_net'])
def test_saved_account_identity_clocks_calendar_and_pair_reconciliation_refuse_corruption(kind):
    a=report([10,-5,2,0,4,-1]);b=report([20,-7,4,0,-2,3],'2R')
    if kind=='configuration_hash':b['config_id']='d'*64
    if kind=='naive_clock':b['signals'][0]['available_at']=DAYS[0]+'T15:00:00'
    if kind=='bad_side':b['signals'][0]['side']=0
    if kind=='news':
        for r in [a,b]:r['config']['news']='skip';r['config_id']=identity(r['config'])
    if kind=='paired_net':
        # Each rounded account is within the individual dollar tolerance, but
        # the opposing errors violate the pair's unchanged absolute tolerance.
        a['metrics']['net_profit']-=8e-8;b['metrics']['net_profit']+=8e-8
    with pytest.raises(DataError):compare(a,b)

def test_decision_overlap_counts_duplicates_outside_dates_and_changed_eligibility():
    a=report([10,-5,2,0,4,-1]);b=report([20,-7,4,0,-2,3],'2R')
    b['signals']=[b['signals'][0],b['signals'][0],dict(symbol='QQQ',side=-1,available_at=DAYS[1]+'T15:00:00+00:00'),dict(symbol='SPY',side=1,available_at='2026-10-01T15:00:00+00:00')]
    result=compare(a,b)
    assert result['baseline_signals']==result['alternative_signals']==2
    assert result['common_decision_signals']==result['baseline_only_signals']==result['alternative_only_signals']==1

@pytest.mark.parametrize('kind',['missing','reordered','cost','capital','core','two_fields','nonfinite','pnl_disagrees','both_missing'])
def test_incompatible_or_incomplete_accounts_do_not_acquire_a_delta(kind):
    a=report([10,-5,2,0,4,-1]);b=report([20,-7,4,0,-2,3],'2R')
    if kind=='missing':b['equity'].pop()
    if kind=='both_missing':a['equity'].pop();b['equity'].pop()
    if kind=='reordered':b['equity'].reverse()
    if kind=='cost':b['costs']['borrow_annual']=.5
    if kind=='capital':b['portfolio']['capital']=2000
    if kind=='core':b['core_hash']='other'
    if kind=='two_fields':b['config']['entry']='limit';b['config_id']=identity(b['config'])
    if kind=='nonfinite':b['equity'][0]['equity']=float('nan')
    if kind=='pnl_disagrees':b['metrics']['daily_pnl'][0]+=1
    with pytest.raises(DataError):compare(a,b)

@pytest.fixture
def saved(tmp_path):
    raw=pd.concat([minute_frame(d) for d in DAYS[:3]],ignore_index=True);raw[['open','high','low','close']]=[96.,96.1,95.9,96.]
    for i,value in enumerate(SPEC['common_closes']):raw.loc[i,['open','high','low','close']]=[value-.02,value+.1,value-.1,value]
    lab=service.Lab(tmp_path);m=save_dataset(lab.datasets_root,raw,dict(input_kind='synthetic',source='Authored ablation fixture'),start=DAYS[0],end=DAYS[2])
    cfg=Strategy(family='break_of_structure',timeframe='1m',swing_strength=2,stop_reference='level',stop_buffer=0,max_hold=24)
    return lab,request(dataset_id=m['id'],start=DAYS[0],end=DAYS[2],strategy=cfg)

def test_actual_ablation_worker_saves_frozen_arms_comparisons_and_trials(saved):
    lab,req=saved;job=lab.create_ablation(req);before=lab.store.registry(job_id=job['id'])
    assert len(before['rows'])==3 and all(r['state']=='planned' and r['attempts']==0 for r in before['rows'])
    Worker(lab).run_once();state=lab.store.job(job['id']);assert state['status']=='completed',state['error']
    root=lab.report(job['id']);assert root['report_type']=='paired_ablations' and len(root['arms'])==3
    base=lab.report(job['id'],0);assert base['trades']
    for row in root['comparisons']:
        other=lab.report(job['id'],row['alternative_part'])
        assert row['net_difference']==pytest.approx(other['metrics']['net_profit']-base['metrics']['net_profit'],abs=1e-7)
    ledger=lab.store.registry(job_id=job['id']);assert all(r['state']=='completed' and r['attempts']==1 and r['artifact_sha256'] for r in ledger['rows'])

def test_ablation_payload_tamper_rejects_before_price_reads(saved,monkeypatch):
    lab,req=saved;job=lab.create_ablation(req)
    with lab.store.db() as db:
        payload=job['payload']|dict(seed=99);db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(payload),job['id']))
    monkeypatch.setattr(service,'load_window',lambda *a,**k:pytest.fail('Tampered plan read prices'))
    Worker(lab).run_once();state=lab.store.job(job['id']);assert state['status']=='failed' and 'frozen' in state['error'].lower()

def test_actual_api_exports_and_registry_do_not_read_prices(saved,monkeypatch):
    lab,req=saved
    with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        response=client.post('/api/ablations',json=req.model_dump(mode='json'));assert response.status_code==202,response.text
        job=response.json();Worker(client.app.state.lab).run_once();report=client.get('/api/jobs/'+job['id']+'/report').json()
        assert report['report_type']=='paired_ablations'
        assert client.get('/api/jobs/'+job['id']+'/export/json').json()==report
        assert 'net_difference' in client.get('/api/jobs/'+job['id']+'/export/csv').text
        assert 'entry_at' in client.get('/api/jobs/'+job['id']+'/export/csv?part=0').text
        monkeypatch.setattr(service,'load_window',lambda *a,**k:pytest.fail('Registry read market prices'))
        ledger=client.get('/api/trial-registry?job_id='+job['id']).json();assert ledger['totals']['planned_occurrences']==3
        full=client.get('/api/trial-registry/export/json?job_id='+job['id']);assert full.status_code==200 and len(full.json()['rows'])==3
        assert client.get('/api/trial-registry/export/csv?job_id='+job['id']).status_code==200
        assert client.get('/api/trial-registry/export/pdf?job_id='+job['id']).status_code==400
        for limit in [0,201]:assert client.get('/api/trial-registry?limit='+str(limit)).status_code==422
        assert client.post('/api/ablations',json=req.model_dump(mode='json')|dict(alternatives=['bad'])).status_code==422

def cancel_first(lab,req,monkeypatch):
    job=lab.create_ablation(req);worker=Worker(lab);original=worker._progress
    def stop(j,fraction,note,checkpoint=None):
        if checkpoint==1:lab.store.cancel(j['id'])
        return original(j,fraction,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once()
    assert lab.store.job(job['id'])['status']=='canceled' and not lab.output_path(job['id']).exists()
    path=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz';assert path.exists()
    return job,path

def test_ablation_resume_reuses_verified_arm_and_keeps_attempt_history(saved,monkeypatch):
    lab,req=saved;job,path=cancel_first(lab,req,monkeypatch);before=path.read_bytes()
    lab.store.resume(job['id']);Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    assert path.read_bytes()==before
    rows=lab.store.registry(job_id=job['id'])['rows'];base=next(r for r in rows if r['part']==0)
    assert base['attempts']==1 and base['reuses']==1 and all(r['attempts']==1 for r in rows)

def test_ablation_corrupted_arm_fails_instead_of_recomputing_or_reusing(saved,monkeypatch):
    lab,req=saved;job,path=cancel_first(lab,req,monkeypatch);path.write_bytes(b'corrupt')
    lab.store.resume(job['id']);Worker(lab).run_once();state=lab.store.job(job['id'])
    assert state['status']=='failed' and 'integrity' in state['error'] and not lab.output_path(job['id']).exists()

def test_ablation_orphan_root_and_part_recompute_with_real_attempts(saved):
    lab,req=saved;job=lab.create_ablation(req);root=lab.output_path(job['id']);root.parent.mkdir(parents=True)
    root.write_bytes(b'untrusted root');parts=root.parent/'parts';parts.mkdir();(parts/'000000.json.gz').write_bytes(b'untrusted part')
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    assert all(r['attempts']==1 for r in lab.store.registry(job_id=job['id'])['rows'])

def test_ablation_sealed_warmup_and_eval_reject_before_price_reads(saved,monkeypatch):
    lab,req=saved
    lab.register_study(Study(name='Sealed',dataset_id=req.dataset_id,discovery=dict(start=DAYS[0],end=DAYS[0]),
        validation=dict(start=DAYS[1],end=DAYS[1]),holdout=dict(start=DAYS[2],end=DAYS[2]),configurations=[Strategy()]))
    monkeypatch.setattr(service,'load_window',lambda *a,**k:pytest.fail('Protected prices were read'))
    with pytest.raises(ResearchError):lab.create_ablation(req)

@pytest.mark.parametrize('invalid',[False,True])
def test_generator_exhaustion_preserves_every_duplicate_or_invalid_proposal(saved,monkeypatch,invalid):
    from backend.lab.models import Search
    class ConstantDraws:
        def choice(self,values):return 999 if invalid and values==[2,3,5,8] else values[0]
        def integers(self,low,high):return low
    lab,req=saved
    with monkeypatch.context() as m:
        m.setattr(service.np.random,'default_rng',lambda seed:ConstantDraws())
        job=lab.create_experiment(Search(dataset_id=req.dataset_id,start=req.start,end=req.end,count=2 if not invalid else 1,
            families=['change_of_character'],timeframes=['1h']))
    sampling=job['payload']['sampling'];assert job['payload']['sampling_failure']
    assert sampling['attempts']==len(sampling['proposals'])==(1000 if invalid else 2000)
    assert sampling['rejected' if invalid else 'duplicates']==(1000 if invalid else 1999)
    monkeypatch.setattr(service,'load_window',lambda *a,**k:pytest.fail('An exhausted sampler must not read prices'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
    ledger=lab.store.registry(job_id=job['id']);assert ledger['totals']['computation_attempts']==0
    assert ledger['totals']['generation']['proposals']==sampling['attempts']

@pytest.mark.parametrize('corrupt',[False,True])
def test_verified_root_resume_checks_every_part_and_reuses_without_new_executions(saved,monkeypatch,corrupt):
    lab,req=saved;job=lab.create_ablation(req);Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    if corrupt:(lab.root/'data/jobs'/job['id']/'parts/000001.json.gz').write_bytes(b'changed')
    with lab.store.db() as db:db.execute("UPDATE jobs SET status='failed' WHERE id=?",(job['id'],))
    lab.store.resume(job['id']);monkeypatch.setattr(service,'load_window',lambda *a,**k:pytest.fail('Verified root reuse read prices'))
    Worker(lab).run_once();state=lab.store.job(job['id'])
    assert state['status']==('failed' if corrupt else 'completed'),state['error']
    assert all(r['attempts']==1 for r in lab.store.registry(job_id=job['id'])['rows'])
