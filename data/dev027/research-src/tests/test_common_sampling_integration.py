"""Actual common-search API/worker/registry/exports with preserved price and recovery guards."""
import csv,json
from io import StringIO
from copy import deepcopy
import pytest
import pandas as pd
from test_research_service import lab_data
from test_search_statistics_integration import short_search_data,client,headers
from test_portfolio_studies import DAYS,ZERO,ACCOUNT
from backend.lab.models import Search
from backend.lab.service import Lab,compressed_read
from backend.lab.worker import Worker
from backend.lab.config import Strategy,identity,canonical
from backend.lab.data import DataError
from backend.lab.presentation_audit import audit_deck
from backend.lab.store import StateError
from backend.lab.news import NewsCalendar

def spec(m,count=6,mode='common_random',**kwargs):
    value=dict(dataset_id=m['id'],start=m['quality']['start'],end=m['quality']['end'],count=count,
               families=['break_of_structure'],timeframes=['1m'],sampling_policy={'mode':mode})
    value.update(kwargs);return Search(**value)

def test_recipe_preview_and_invalid_axes_do_not_access_manifest_or_prices(lab_data,monkeypatch):
    lab,_=lab_data
    def forbidden(*a,**kw):raise AssertionError('Pure recipe preview reached dataset or prices')
    monkeypatch.setattr('backend.lab.service.read_manifest',forbidden);monkeypatch.setattr(Lab,'_evaluation_input',forbidden)
    with client(lab) as c:
        result=c.post('/api/searches/preview',headers=headers(c),json={'families':['break_of_structure'],'timeframes':['1m']})
        assert result.status_code==200 and result.json()['grid_count']==48
        for axes,status in [({'families':[],'timeframes':['1m']},422),({'families':['unknown'],'timeframes':['1m']},409),({'families':['breakout','breakout'],'timeframes':['1m']},409)]:
            assert c.post('/api/searches/preview',headers=headers(c),json=axes).status_code==status
    assert lab.store.jobs()==[]

def test_complete_nonempty_common_grid_keeps_all_initial_grades_and_saved_only_exports(short_search_data,monkeypatch):
    lab,m=short_search_data
    request=spec(m,48,'common_grid',costs=ZERO.model_dump(),portfolio=ACCOUNT.model_dump(),start=DAYS[4])
    with client(lab) as c:
        result=c.post('/api/searches',headers=headers(c),json=request.model_dump(mode='json'));assert result.status_code==202
        job=result.json();assert job['payload']['sampling']['unique']==48
        assert lab.store.registry(job_id=job['id'])['totals']['planned_occurrences']==48
        assert Worker(lab).run_once();state=lab.store.job(job['id']);assert state['status']=='completed',state.get('error')
        saved=lab.result(job['id']);screen=saved['search_screen'];assert len(saved['rows'])==len(screen['accounts'])==48
        assert saved['sampling_policy']==request.sampling_policy.model_dump() and saved['news_calendar'] is None and saved['news_calendar_id'] is None
        assert sum(r['metrics']['trades'] for r in saved['rows'])>0
        independent=dict(generated=48,signal_qualified=0,enough_trades=0,profitable=0,sharpe_passed=0)
        warmup_evidence=False
        for row,account in zip(saved['rows'],screen['accounts']):
            report=lab.report(job['id'],row['part'])
            window_count=sum(report['start']<=pd.Timestamp(s['available_at']).tz_convert('America/New_York').date().isoformat()<=report['end'] for s in report['signals'])
            warmup_evidence=warmup_evidence or len(report['signals'])>window_count
            assert row['signal_count']==account['signal_count']==window_count
            assert account['source_part_sha256']==row['report_sha256'] and account['trades']==len(report['trades'])
            assert account['net_profit']==report['metrics']['net_profit'] and account['marked_sharpe']==report['metrics']['marked_sharpe']
            gates=[account['signal_count']>=40,account['trades']>=30,account['net_profit']>0,account['marked_sharpe'] is not None and account['marked_sharpe']>=.5]
            for n,key in enumerate(list(independent)[1:]):independent[key]+=all(gates[:n+1])
        assert screen['counts']==screen['groups'][0]['counts']==independent
        assert warmup_evidence,'The authored late window must actually contain excluded warm-up evidence.'
        assert all(v=='not_run' for v in screen['later_stages'].values()) and lab.guard.studies()==[]
        def forbidden(*a,**kw):raise AssertionError('Saved discovery export reached prices or recomputation')
        monkeypatch.setattr(Lab,'_evaluation_input',forbidden);monkeypatch.setattr('backend.lab.sampling.initial_screen',forbidden)
        output=c.get('/api/jobs/'+job['id']+'/search-screen/export/json');assert output.status_code==200 and output.json()==screen
        output=c.get('/api/jobs/'+job['id']+'/search-screen/export/csv');assert output.status_code==200
        rows=list(csv.DictReader(StringIO(output.text)));assert len(rows)==48
        for observed,account in zip(rows,screen['accounts']):
            assert observed['include_news']=='False' and observed['news_calendar_id']=='' and observed['recipe_hash']==saved['sampling']['recipe_hash']
            assert observed['config_id']==account['config_id'] and observed['source_part_sha256']==account['source_part_sha256']
            for key in ['signal_count','trades','net_profit','initial_gates_passed']:assert observed[key]==str(account[key])
            assert observed['failures']==';'.join(account['failures'])
        output=c.get('/api/jobs/'+job['id']+'/export/presentation.json');assert output.status_code==200,output.text
        deck=output.json();assert audit_deck({job['id']+'/report.json':canonical(saved).encode()},deck)['facts_checked']>0
        paths={tuple(f['path']) for f in deck['facts'].values()}
        for key in independent:assert ('search_screen','counts',key) in paths and ('search_screen','groups',0,'counts',key) in paths
        for path in [('search_screen','settings','mode'),('search_screen','settings','include_news'),('sampling','recipe_hash'),('search_screen','signal_definition'),('search_screen','scope')]:assert path in paths

@pytest.mark.parametrize('fault',['cancel','summary_failure','corrupt_part','policy_tamper'])
def test_actual_common_recovery_preserves_original_parts_and_policy(lab_data,monkeypatch,fault):
    lab,m=lab_data;job=lab.create_experiment(spec(m));worker=Worker(lab)
    if fault=='policy_tamper':
        with lab.store.db() as db:
            p=lab.store.job(job['id'])['payload'];p['sampling_policy']['minimum_signals']=1
            db.execute('UPDATE jobs SET payload=? WHERE id=?',(canonical(p),job['id']))
        monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**kw:pytest.fail('Changed policy reached prices'))
        worker.run_once();assert lab.store.job(job['id'])['status']=='failed';assert not lab.output_path(job['id']).exists();return
    if fault=='summary_failure':
        def fail(*a,**kw):raise DataError('Authored initial grading failure')
        monkeypatch.setattr('backend.lab.sampling.initial_screen',fail)
    else:
        original=worker._progress
        def stop(j,p,n,checkpoint=None):
            original(j,p,n,checkpoint)
            if checkpoint==1:lab.store.cancel(j['id'])
        monkeypatch.setattr(worker,'_progress',stop)
    worker.run_once();assert lab.store.job(job['id'])['status'] in {'failed','canceled'} and not lab.output_path(job['id']).exists()
    part=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz';before=part.read_bytes()
    if fault=='corrupt_part':part.write_bytes(before+b'corrupt')
    monkeypatch.undo();lab.store.resume(job['id']);Worker(lab).run_once()
    if fault=='corrupt_part':assert lab.store.job(job['id'])['status']=='failed';return
    assert lab.store.job(job['id'])['status']=='completed' and part.read_bytes()==before
    assert len(lab.result(job['id'])['search_screen']['accounts'])==6
    with lab.store.db() as db:assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=? AND part=0',(job['id'],)).fetchone()[0]==1

def test_wrong_grid_count_persists_failure_without_any_account_computation(lab_data,monkeypatch):
    lab,m=lab_data;job=lab.create_experiment(spec(m,2,'common_grid'))
    assert job['payload']['sampling_failure'] and job['payload']['configurations']==[]
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**kw:pytest.fail('Failed generation reached prices'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()
    assert lab.store.registry(job_id=job['id'])['totals']['computation_attempts']==0

def test_full_proposal_hash_is_validated_before_atomic_registration(lab_data):
    lab,m=lab_data;job=lab.create_experiment(spec(m,2));payload=deepcopy(job['payload'])
    payload['sampling']['proposals'][0]['configuration']['target']='5R' if payload['sampling']['proposals'][0]['configuration']['target']!='5R' else '1R'
    with pytest.raises(StateError,match='proposal configuration identity'):lab.store.create_job('search',payload)
    payload['sampling']['proposals'][0]['configuration']={'family':'unknown'}
    with pytest.raises(StateError,match='not a valid configuration'):lab.store.create_job('search',payload)
    assert len(lab.store.jobs())==1

def test_screen_export_format_and_legacy_guards(lab_data,monkeypatch):
    lab,_=lab_data
    with client(lab) as c:
        monkeypatch.setattr(Lab,'result',lambda *a,**kw:pytest.fail('Unsupported format reached saved results'))
        assert c.get('/api/jobs/'+'a'*32+'/search-screen/export/html').status_code==409
        monkeypatch.setattr(Lab,'result',lambda *a,**kw:{'kind':'search'})
        assert c.get('/api/jobs/'+'a'*32+'/search-screen/export/json').status_code==409
        monkeypatch.setattr(Lab,'result',lambda *a,**kw:{'kind':'search','search_screen':{'policy_version':1,'settings':{} }})
        assert c.get('/api/jobs/'+'a'*32+'/search-screen/export/json').status_code==409

def test_common_news_modes_freeze_the_explicit_calendar_and_corruption_blocks_prices(short_search_data,monkeypatch):
    lab,m=short_search_data;start=m['quality']['start'];end=m['quality']['end']
    calendar=lab.news.save(NewsCalendar(name='Synthetic common sampling news',start=start,end=end,kinds=['fed'],complete=True,mode='synthetic',events=[{'date':start,'kind':'fed','label':'Authored event'}]))
    req=spec(m,64,'common_grid',sampling_policy={'mode':'common_grid','include_news':True},news_calendar_id=calendar['id'])
    job=lab.create_experiment(req);assert job['payload']['news_calendar']==calendar
    assert sum(c['news']=='skip' for c in job['payload']['configurations'])==16
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    saved=lab.result(job['id']);assert saved['search_screen']['settings']['include_news'] is True
    assert saved['news_calendar']==calendar and saved['news_calendar_id']==calendar['id'] and saved['sampling_policy']==req.sampling_policy.model_dump()
    assert saved['rows'][0]['signal_count']>0 and saved['rows'][3]['signal_count']<saved['rows'][0]['signal_count']
    assert all(pd.Timestamp(s['available_at']).tz_convert('America/New_York').date().isoformat()!=start for s in lab.report(job['id'],3)['signals'])
    assert all(lab.report(job['id'],part)['news_calendar']==calendar for part in [0,3,63])
    second=lab.create_experiment(req);p=lab.news.calendar_path(calendar['id']);p.write_bytes(p.read_bytes()+b'bad')
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**kw:pytest.fail('Corrupt common calendar reached prices'))
    with client(lab) as c:
        exported=c.get('/api/jobs/'+job['id']+'/search-screen/export/csv');assert exported.status_code==200
        assert all(r['include_news']=='True' and r['news_calendar_id']==calendar['id'] for r in csv.DictReader(StringIO(exported.text)))
        projected=c.get('/api/jobs/'+job['id']+'/export/presentation.json');assert projected.status_code==200,projected.text
        paths={tuple(f['path']) for f in projected.json()['facts'].values()}
        for path in [('news_calendar','id'),('news_calendar','spec','start'),('news_calendar','spec','end'),('news_calendar','spec','complete')]:assert path in paths
    Worker(lab).run_once();assert lab.store.job(second['id'])['status']=='failed' and not lab.output_path(second['id']).exists()
