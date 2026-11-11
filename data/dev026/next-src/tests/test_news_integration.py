from copy import deepcopy
from dataclasses import replace
from datetime import datetime,timezone
import json
import pandas as pd
import pytest
from backend.lab import models,news
from backend.lab.config import Strategy,Costs,Portfolio
from backend.lab.data import DataError
from backend.lab.worker import Worker
from backend.lab.signals import generate_signals
from verification.strategy_fixtures import scenario,SPEC
from test_api import client_lab,seed,payload
from test_random_controls import saved,feature,signal
from test_confirmation_filters import select,tables,AT
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
from types import SimpleNamespace
from backend.lab.config import identity


def calendar(start='2026-11-02',end='2026-11-06',**changes):
    return dict(name='Authored synthetic news',start=start,end=end,mode='synthetic',complete=True,
        kinds=['fed'],events=[dict(date=start,kind='fed',label='Authored news')])|changes


def test_actual_api_import_download_and_missing_scope_reject_before_price_reads(client_lab,monkeypatch):
    client,lab=client_lab;m=seed(lab)
    value=client.post('/api/news-calendars',json=calendar());assert value.status_code==201,value.text
    saved=value.json();assert client.get('/api/news-calendars/'+saved['id']).json()==saved
    assert any(v['id']==saved['id'] for v in client.get('/api/news-calendars').json())
    request=payload(m)|dict(strategy=Strategy(news='half').model_dump(),news_calendar_id=saved['id'])
    created=client.post('/api/experiments',json=request);assert created.status_code==202,created.text
    job=lab.store.job(created.json()['id']);assert job['payload']['news_calendar']==saved
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    report=lab.report(job['id']);assert report['news_calendar']==saved and report['news_dates']==['2026-11-02']
    assert client.get('/api/jobs/'+job['id']+'/export/json').json()['news_calendar']==saved
    def forbidden(*args,**kw):raise AssertionError('Invalid calendar must reject before prices.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    p=lab.news.calendar_path(saved['id']);p.write_bytes(p.read_bytes()+b'bad')
    with pytest.raises(DataError):lab.control_context(job['payload']|dict(replicas=2))


def test_worker_calendar_tamper_fails_without_raw_price_access(client_lab,monkeypatch):
    client,lab=client_lab;m=seed(lab);saved=lab.news.save(news.NewsCalendar(**calendar()))
    job=lab.create_experiment(models.Experiment(**(payload(m)|dict(news_calendar_id=saved['id'],strategy=Strategy(news='skip').model_dump()))))
    before=deepcopy(job['payload']);path=lab.news.calendar_path(saved['id']);path.write_bytes(path.read_bytes()+b'bad')
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Price read before corrupt calendar rejection'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
    assert lab.store.job(job['id'])['payload']==before and not lab.output_path(job['id']).exists()


def test_json_duplicates_csv_attestation_and_mode_errors_are_safe(client_lab):
    client,lab=client_lab
    raw=json.dumps(calendar())[:-1]+',"name":"duplicate"}'
    assert client.post('/api/news-calendars',content=raw,headers={'content-type':'application/json'}).status_code==409
    csv=b'date,kind,label,known_at\n2026-11-03,fed,Scenario,2026-11-02T12:00:00Z\n'
    metadata=calendar(mode='asof',events=[])
    r=client.post('/api/news-imports',files={'file':('../../news.csv',csv)},data={'metadata_json':json.dumps(metadata)})
    assert r.status_code==201,r.text
    assert r.json()['origin']=='user_csv'
    for body in [dict(mode='asof',events=[dict(date='2026-11-02',kind='fed',label='Naive',known_at='2026-11-02T12:00:00')]),dict(complete=False)]:
        r=client.post('/api/news-calendars',json=calendar(**body))
        if r.status_code==201:
            value=r.json()
            with pytest.raises(DataError):lab.news.clock(value['id'],'2026-11-02','2026-11-04',value)
        else:assert r.status_code==422


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['skip','half'])
@pytest.mark.parametrize('known_first',[True,False])
def test_actual_selector_uses_recorded_knowledge_at_confirmation(monkeypatch,side,mode,known_first):
    chosen=AT+pd.Timedelta(minutes=5)
    spec=news.NewsCalendar(**calendar('2026-10-05','2026-10-05',mode='asof',events=[dict(date='2026-10-05',kind='fed',label='Recorded event',known_at=(chosen+pd.Timedelta(microseconds=-1 if known_first else 1)).isoformat())]))
    signals,cfg=select(monkeypatch,tables(side),side,calendar=news.NewsClock(spec),news=mode)
    if mode=='skip' and known_first:assert signals==[]
    else:assert len(signals)==1 and signals[0].weight==(.5 if mode=='half' and known_first else 1)


@pytest.mark.parametrize('side',[1,-1])
def test_real_minute_detectors_half_news_and_skip_on_both_sides(side):
    frame,event=scenario('break_of_structure','1m',side)
    cfg=Strategy(**(SPEC['config']|dict(family='break_of_structure',timeframe='1m')))
    first=str(frame.session.min());last=str(frame.session.max())
    clock=news.NewsClock(news.NewsCalendar(**calendar(first,last,events=[dict(date=first,kind='fed',label='Authored day')])))
    real=generate_signals(frame,cfg);assert real
    half=generate_signals(frame,Strategy(**(cfg.model_dump()|dict(news='half'))),clock)
    skip=generate_signals(frame,Strategy(**(cfg.model_dump()|dict(news='skip'))),clock)
    assert half and all(s.weight==.5 for s in half if s.available_at.tz_convert('America/New_York').date().isoformat()==first)
    assert all(s.available_at.tz_convert('America/New_York').date().isoformat()!=first for s in skip)


def test_news_controls_and_paired_accounts_execute_with_same_frozen_calendar(saved):
    lab,m,request,frame=saved
    version=lab.news.save(news.NewsCalendar(**calendar('2026-10-05','2026-10-05')))
    cfg=Strategy(**(request.strategy.model_dump()|dict(news='half')))
    inputs=request.model_dump(mode='json')|dict(news_calendar_id=version['id'],strategy=cfg.model_dump())
    job=lab.create_controls(models.ControlsExperiment(**inputs));Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    result=lab.report(job['id']);assert result['news_calendar']==version and result['matching']['matched_count']>0
    for row in result['books']:
        report=lab.report(job['id'],row['part']);assert report['news_calendar']==version
        assert all(s['weight']==.5 for s in report['signals'])
        expected=execute(primitive(frame),[s|{'config_id':identity(cfg)} for s in report['signals']],
            {identity(cfg):cfg.model_dump()},request.costs.model_dump(),request.portfolio.model_dump(),start=str(request.start),end=str(request.end))
        assert_parity(SimpleNamespace(**report),expected)
    fields={k:v for k,v in inputs.items() if k!='replicas'}
    fields['strategy']=request.strategy.model_dump();fields.update(field='news',alternatives=['half','skip'])
    ab=lab.create_ablation(models.AblationExperiment(**fields));Worker(lab).run_once()
    assert lab.store.job(ab['id'])['status']=='completed',lab.store.job(ab['id'])['error']
    paired=lab.report(ab['id']);assert paired['news_calendar']==version
    assert len(paired['comparisons'])==2 and all(a['config']['news'] in {'trade','half','skip'} for a in paired['arms'])


def test_search_and_shared_portfolio_freeze_and_reconcile_calendar_weights(saved):
    lab,m,request,frame=saved
    version=lab.news.save(news.NewsCalendar(**calendar('2026-10-05','2026-10-05')))
    cfg=Strategy(**(request.strategy.model_dump()|dict(news='half')))
    base={k:v for k,v in request.model_dump(mode='json').items() if k not in {'replicas','strategy'}}|dict(news_calendar_id=version['id'])
    search=lab.create_experiment(models.Search(**(base|dict(strategy=cfg.model_dump(),count=2,families=[cfg.family],timeframes=['1m']))))
    assert all(c['news']=='half' for c in search['payload']['configurations'])
    Worker(lab).run_once();assert lab.store.job(search['id'])['status']=='completed'
    for row in lab.result(search['id'])['rows']:assert lab.report(search['id'],row['part'])['news_calendar']==version
    cfg2=Strategy(**(cfg.model_dump()|dict(target='3R')))
    job=lab.create_portfolio(models.PortfolioExperiment(**(base|dict(configurations=[cfg.model_dump(),cfg2.model_dump()]))))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    report=lab.report(job['id']);assert report['news_calendar']==version and report['trades']
    expected=execute(primitive(frame),report['signals'],{identity(c):c.model_dump() for c in [cfg,cfg2]},
        request.costs.model_dump(),request.portfolio.model_dump(),start=str(request.start),end=str(request.end))
    assert_parity(SimpleNamespace(**report),expected)


def test_study_registration_freezes_full_calendar_and_screening_detects_later_corruption(client_lab,monkeypatch):
    client,lab=client_lab;m=seed(lab);version=lab.news.save(news.NewsCalendar(**calendar()))
    body=dict(name='Calendar study',dataset_id=m['id'],discovery={'start':'2026-11-02','end':'2026-11-02'},
        validation={'start':'2026-11-03','end':'2026-11-04'},holdout={'start':'2026-11-05','end':'2026-11-06'},
        configurations=[Strategy(news='half').model_dump()],news_calendar_id=version['id'],minimum_trades=1)
    created=client.post('/api/studies',json=body);assert created.status_code==201,created.text
    sid=created.json()['id'];study=lab.guard.study(sid);assert study['spec']['news_calendar']==version
    job=lab.screen(sid);p=lab.news.calendar_path(version['id']);p.write_bytes(p.read_bytes()+b'bad')
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Corrupt study calendar must reject before prices.'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
    assert lab.guard.study(sid)['status']=='registered' and lab.guard.study(sid)['spec']['news_calendar']==version


def test_download_worker_sources_are_committed_and_not_research_trials(client_lab,monkeypatch):
    from test_news_acquisition import document
    client,lab=client_lab
    monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:document(url))
    r=client.post('/api/news-downloads',json=dict(start='2022-01-01',end='2022-01-31'));assert r.status_code==202
    jid=r.json()['id'];Worker(lab).run_once();assert lab.store.job(jid)['status']=='completed',lab.store.job(jid)['error']
    result=lab.result(jid);assert len(result['calendar']['spec']['events'])==3
    assert len([e for e in lab.store.events(jid) if e['kind']=='news_document_saved'])==2
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',(jid,)).fetchone()[0]==0


@pytest.mark.parametrize('fault',['cancel','shutdown','lost_checkpoint','corrupt_source','corrupt_checkpoint'])
def test_actual_worker_calendar_recovery_uses_only_committed_documents(client_lab,monkeypatch,fault):
    from test_news_acquisition import document
    client,lab=client_lab;calls=[]
    monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:(calls.append(url) or document(url)))
    created=client.post('/api/news-downloads',json=dict(start='2022-01-01',end='2022-01-31'));assert created.status_code==202
    jid=created.json()['id'];payload_before=deepcopy(lab.store.job(jid)['payload'])
    worker=Worker(lab);original=worker._progress
    def interrupt(job,fraction,note,checkpoint=None):
        original(job,fraction,note,checkpoint)
        if 0<fraction<1:
            if fault=='shutdown':worker.shutdown.set()
            else:lab.store.cancel(jid)
    monkeypatch.setattr(worker,'_progress',interrupt);assert worker.run_once()
    assert lab.store.job(jid)['status']==('queued' if fault=='shutdown' else 'canceled')
    assert lab.news.list()==[] and not lab.output_path(jid).exists() and len(calls)==1
    receipts=[e for e in lab.store.events(jid) if e['kind']=='news_document_saved'];assert len(receipts)==1
    source=receipts[0]['details']['document'];raw=lab.news.source_path(source['sha256']).read_bytes()
    checkpoint=lab.output_path(jid).parent/'news-documents.json'
    if fault=='lost_checkpoint':checkpoint.unlink()
    elif fault=='corrupt_source':lab.news.source_path(source['sha256']).write_bytes(raw+b'authored corruption')
    elif fault=='corrupt_checkpoint':
        cache=json.loads(checkpoint.read_text(encoding='utf-8'));cache['documents'][source['url']]['acquired_at']='2022-01-01T00:00:00Z'
        checkpoint.write_text(json.dumps(cache),encoding='utf-8')
    if fault!='shutdown':assert client.post('/api/jobs/'+jid+'/resume').status_code==200
    assert Worker(lab).run_once();finished=lab.store.job(jid)
    assert finished['payload']==payload_before
    if fault.startswith('corrupt'):
        assert finished['status']=='failed' and len(calls)==1
        assert not lab.output_path(jid).exists() and lab.news.list()==[]
    else:
        assert finished['status']=='completed',finished['error']
        assert len(calls)==2 and len(set(calls))==2
        assert lab.news.source_path(source['sha256']).read_bytes()==raw
        assert [e for e in lab.store.events(jid) if e['kind']=='news_document_saved'][0]==receipts[0]
        result=lab.result(jid);assert len(result['calendar']['spec']['events'])==3
        assert lab.news.load(result['news_calendar_id'])==result['calendar']


def test_worker_revalidates_calendar_sources_before_reusing_saved_download_result(client_lab,monkeypatch):
    from test_news_acquisition import document
    client,lab=client_lab;monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:document(url))
    jid=client.post('/api/news-downloads',json=dict(start='2022-01-01',end='2022-01-31')).json()['id']
    worker=Worker(lab);original=worker._progress
    def interrupt(job,fraction,note,checkpoint=None):
        original(job,fraction,note,checkpoint)
        if fraction==1 and note=='Results saved and content-bound.':lab.store.cancel(jid)
    monkeypatch.setattr(worker,'_progress',interrupt);worker.run_once()
    assert lab.store.job(jid)['status']=='canceled' and lab.output_path(jid).exists()
    from backend.lab.service import compressed_read
    saved=compressed_read(lab.output_path(jid));source=saved['calendar']['sources'][0];path=lab.news.source_path(source['sha256'])
    path.write_bytes(path.read_bytes()+b'authored corruption')
    assert client.post('/api/jobs/'+jid+'/resume').status_code==200
    monkeypatch.setattr(news,'fetch_document',lambda *a,**k:pytest.fail('Committed corruption must reject, never silently refetch.'))
    Worker(lab).run_once();assert lab.store.job(jid)['status']=='failed'


@pytest.mark.parametrize('corrupt',[False,True])
def test_final_worker_calendar_freeze_and_preconsume_integrity_guard(client_lab,monkeypatch,corrupt):
    client,lab=client_lab;m=seed(lab);version=lab.news.save(news.NewsCalendar(**calendar()))
    cfg=Strategy(news='half')
    spec=models.Study(name='Calendar final transition fixture',dataset_id=m['id'],discovery={'start':'2026-11-02','end':'2026-11-03'},
        validation={'start':'2026-11-04','end':'2026-11-04'},holdout={'start':'2026-11-05','end':'2026-11-06'},
        configurations=[cfg],news_calendar_id=version['id'],minimum_trades=1)
    sid=lab.register_study(spec)['id']
    # Explicit transition fixture: flat synthetic prices did not pass candidate selection.
    lab.guard.screened(sid,'test-only-injected-calendar-candidate',[cfg.model_dump()])
    job=lab.final(sid)
    if corrupt:
        path=lab.news.calendar_path(version['id']);path.write_bytes(path.read_bytes()+b'bad')
        monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Calendar must reject before holdout prices.'))
    Worker(lab).run_once()
    if corrupt:
        assert lab.store.job(job['id'])['status']=='failed'
        assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
        assert not lab.output_path(job['id']).exists()
    else:
        assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
        report=lab.report(job['id'],0);assert report['news_calendar']==version and len(report['equity'])==2
        assert lab.guard.study(sid)['status']=='final_complete'
        assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
