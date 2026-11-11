"""Actual search/API/worker and saved-only DSR exports; no injected accounts."""
import csv,hashlib,json,math
from io import StringIO
import pytest
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.models import Search
from backend.lab.worker import Worker
from backend.lab.data import DataError
from backend.lab.config import canonical
from backend.lab.presentation_audit import audit_deck
from test_research_service import lab_data
from test_portfolio_studies import study_data,DAYS,ZERO,ACCOUNT
from conftest import minute_frame
import pandas as pd
from backend.lab.service import Lab
from backend.lab.data import save_dataset

@pytest.fixture
def short_search_data(tmp_path):
    lab=Lab(tmp_path);frames=[]
    for day_index,day in enumerate(DAYS):
        frame=minute_frame(day)
        values=[1000+10*day_index-.1*minute+8*math.sin(2*math.pi*minute/64) for minute in range(390)]
        frame['close']=values;frame['open']=frame.close+.02;frame['high']=frame.close+.2;frame['low']=frame.close-.1
        frames.append(frame)
    manifest=save_dataset(lab.datasets_root,pd.concat(frames,ignore_index=True),{'input_kind':'synthetic','source':'Authored rising daily baselines and descending intraday cycles; original skip-run constraints retained'},start=DAYS[0],end=DAYS[-1])
    return lab,manifest

def client(lab):
    app=create_app(lab.root,run_worker=False)
    return TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',51000))

def headers(c):return {'Origin':'http://localhost:8765','X-Lab-Token':c.get('/api/session').json()['token']}

def test_actual_nonempty_search_freezes_policy_and_exports_all_saved_values_offline(short_search_data,monkeypatch):
    lab,m=short_search_data
    with client(lab) as c:
        request=dict(dataset_id=m['id'],start=DAYS[0],end=DAYS[-1],count=4,families=['break_of_structure'],timeframes=['1m'],costs=ZERO.model_dump(),portfolio=ACCOUNT.model_dump(),statistics={'effective_trials':[1,2,4],'dispersion_mode':'assumed','trial_sharpe_std':.2})
        response=c.post('/api/searches',json=request,headers=headers(c));assert response.status_code==202
        job=response.json();assert job['payload']['statistics']==request['statistics']
        frozen=next(e for e in lab.store.events(job['id']) if e['kind']=='trial_plan_frozen')
        assert frozen['details']['occurrences']==4
        Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
        result=lab.result(job['id']);s=result['search_statistics']
        assert sum(r['metrics']['trades'] for r in result['rows'])>0
        assert len(s['accounts'])==4 and s['raw_generation']=={k:result['sampling'][k] for k in ['attempts','unique','duplicates','rejected']}
        assert s['settings']==job['payload']['statistics']
        for row,account in zip(result['rows'],s['accounts']):
            assert account['source_part_sha256']==row['report_sha256'] and account['net_profit']==row['metrics']['net_profit']
        def forbidden(*a,**kw):raise AssertionError('Saved statistic export attempted numerical recomputation or raw prices')
        monkeypatch.setattr('backend.lab.service.load_window',forbidden)
        monkeypatch.setattr('backend.lab.worker.build_search_statistics',forbidden)
        exported=c.get('/api/jobs/'+job['id']+'/search-statistics/export/json');assert exported.status_code==200 and exported.json()==s
        text=c.get('/api/jobs/'+job['id']+'/search-statistics/export/csv');assert text.status_code==200
        rows=list(csv.DictReader(StringIO(text.text)));assert len(rows)==12
        for record,account in zip([rows[i:i+3] for i in range(0,12,3)],s['accounts']):
            for observed,scenario in zip(record,account['sensitivity']):
                assert int(observed['part'])==account['part'] and observed['config_id']==account['config_id']
                assert int(observed['effective_trials'])==scenario['effective_trials']
                assert observed['score']==('' if scenario['score'] is None else str(scenario['score']))
                assert observed['undefined_reason']==(scenario['undefined_reason'] or '')
        manifest=c.get('/api/jobs/'+job['id']+'/export/presentation.json');assert manifest.status_code==200,manifest.text
        deck=manifest.json();audit=audit_deck({job['id']+'/report.json':canonical(result).encode()},deck)
        assert audit['facts_checked']>0
        paths={tuple(f['path']) for f in deck['facts'].values()}
        for i in range(4):
            for key in ['net_profit','observations','daily_sharpe','skewness','raw_kurtosis','source_part_sha256']:assert ('search_statistics','accounts',i,key) in paths
            for j in range(3):assert ('search_statistics','accounts',i,'sensitivity',j,'score') in paths
        html=c.get('/api/jobs/'+job['id']+'/export/html');assert html.status_code==200 and 'Search-bias sensitivity' in html.text

def test_original_jump_geometry_remains_an_honest_zero_trade_control(study_data):
    lab,m,_=study_data
    job=lab.create_experiment(Search(dataset_id=m['id'],start=DAYS[0],end=DAYS[-1],count=4,families=['break_of_structure'],timeframes=['1m'],costs=ZERO,portfolio=ACCOUNT))
    Worker(lab).run_once();result=lab.result(job['id'])
    assert sum(r['metrics']['trades'] for r in result['rows'])==0
    assert all(v['score'] is None for a in result['search_statistics']['accounts'] for v in a['sensitivity'])

@pytest.mark.parametrize('fault',['cancel','failed_summary','corrupt_part','policy_tamper'])
def test_search_summary_interruptions_and_tampering_preserve_committed_accounts(lab_data,monkeypatch,fault):
    lab,m=lab_data;job=lab.create_experiment(Search(dataset_id=m['id'],start='2026-11-02',end='2026-11-06',count=2,timeframes=['1h']))
    worker=Worker(lab);progress=worker._progress
    if fault=='policy_tamper':
        def forbidden(*a,**kw):raise AssertionError('Changed policy reached price reads')
        monkeypatch.setattr(lab,'_evaluation_input',forbidden)
        with lab.store.db() as db:
            payload=lab.store.job(job['id'])['payload'];payload['statistics']['effective_trials']=[1]
            db.execute('UPDATE jobs SET payload=? WHERE id=?',(canonical(payload),job['id']))
        worker.run_once();assert lab.store.job(job['id'])['status']=='failed';assert not lab.output_path(job['id']).exists();return
    if fault=='failed_summary':
        def fail(*a,**kw):raise DataError('Authored diagnostic failure after complete accounts')
        monkeypatch.setattr('backend.lab.worker.build_search_statistics',fail)
    else:
        def interrupt(j,p,n,checkpoint=None):
            progress(j,p,n,checkpoint)
            if checkpoint==1:lab.store.cancel(j['id'])
        monkeypatch.setattr(worker,'_progress',interrupt)
    worker.run_once();assert lab.store.job(job['id'])['status'] in {'canceled','failed'}
    assert not lab.output_path(job['id']).exists()
    part=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz';original=part.read_bytes()
    if fault=='corrupt_part':part.write_bytes(original+b'corrupt')
    monkeypatch.undo();lab.store.resume(job['id']);Worker(lab).run_once()
    if fault=='corrupt_part':assert lab.store.job(job['id'])['status']=='failed';return
    assert lab.store.job(job['id'])['status']=='completed' and part.read_bytes()==original
    assert len(lab.result(job['id'])['search_statistics']['accounts'])==2
    with lab.store.db() as db:assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=? AND part=0',(job['id'],)).fetchone()[0]==1

@pytest.mark.parametrize('settings',[{'effective_trials':[True]},{'effective_trials':[3]},{'dispersion_mode':'assumed'},{'trial_sharpe_std':.1}])
def test_invalid_assumptions_are_rejected_before_price_or_manifest_access(lab_data,monkeypatch,settings):
    lab,m=lab_data
    with client(lab) as c:
        def forbidden(*a,**kw):raise AssertionError('Invalid statistics reached data access')
        monkeypatch.setattr('backend.lab.service.read_manifest',forbidden)
        response=c.post('/api/searches',headers=headers(c),json=dict(dataset_id=m['id'],start='2026-11-02',end='2026-11-06',count=2,statistics=settings))
        assert response.status_code==422


def test_export_rejects_unsupported_format_before_reading_any_saved_result(lab_data,monkeypatch):
    lab,_=lab_data
    with client(lab) as c:
        def forbidden(*a,**kw):raise AssertionError('Unsupported export reached saved result access')
        monkeypatch.setattr(Lab,'result',forbidden)
        response=c.get('/api/jobs/'+'a'*32+'/search-statistics/export/html')
        assert response.status_code==409 and 'json or csv' in response.json()['detail']


@pytest.mark.parametrize('saved',[{'kind':'experiment'},{'kind':'search'},{'kind':'search','search_statistics':[]},{'kind':'search','search_statistics':{'policy_version':99}}])
def test_legacy_and_nonsearch_results_are_not_silently_recomputed(lab_data,monkeypatch,saved):
    lab,_=lab_data
    with client(lab) as c:
        monkeypatch.setattr(Lab,'result',lambda *a,**kw:saved)
        response=c.get('/api/jobs/'+'a'*32+'/search-statistics/export/json')
        assert response.status_code==409 and 'Original evidence is unchanged' in response.json()['detail']
