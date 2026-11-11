from contextlib import contextmanager
from io import BytesIO
from threading import Event
from concurrent.futures import ThreadPoolExecutor
import json
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from conftest import minute_frame
from backend.lab.api import create_app,local_authority
from backend.lab.config import Strategy
from backend.lab.data import save_dataset
from backend.lab.models import Experiment,Study
from backend.lab.store import StateError
from backend.lab.worker import Worker

@pytest.fixture
def client_lab(tmp_path):
    app=create_app(tmp_path,run_worker=False)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
        session=client.get('/api/session');assert session.status_code==200
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':session.json()['token']})
        yield client,app.state.lab

def seed(lab):
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']])
    return save_dataset(lab.datasets_root,frame,{'input_kind':'synthetic','source':'Offline test prices'},start='2026-11-02',end='2026-11-06')

def payload(m): return Experiment(dataset_id=m['id'],start='2026-11-02',end='2026-11-04').model_dump(mode='json')

def study_payload(m): return Study(name='API study',dataset_id=m['id'],
    discovery={'start':'2026-11-02','end':'2026-11-03'},validation={'start':'2026-11-04','end':'2026-11-04'},
    holdout={'start':'2026-11-05','end':'2026-11-06'},configurations=[Strategy()],minimum_trades=1).model_dump(mode='json')

@pytest.mark.parametrize('authority',['localhost','localhost:8765','127.0.0.1:123','[::1]:8765'])
def test_valid_local_authority(authority): assert local_authority(authority)

@pytest.mark.parametrize('authority',['evil.test','localhost.evil.test','localhost@evil.test','localhost:0','localhost:99999','localhost/path','127.0.0.1#evil','localhost?x=1','[::1',''])
def test_bad_local_authority(authority): assert not local_authority(authority)

def test_mutations_require_origin_and_token_even_when_origin_missing(client_lab):
    client,_=client_lab;data={'name':'safe','strategy':{}}
    for headers in [ {'host':'evil.test'}, {'origin':'http://evil.test'}, {'origin':'null'}, {'x-lab-token':'invalid'} ]:
        assert client.post('/api/strategies',json=data,headers=headers).status_code==403
    origin=client.headers.pop('origin')
    assert client.post('/api/strategies',json=data).status_code==403
    client.headers['origin']=origin;client.headers.pop('x-lab-token')
    assert client.post('/api/strategies',json=data).status_code==403

def test_cross_site_get_and_nonlocal_peer_rejected(client_lab,tmp_path):
    client,_=client_lab
    assert client.get('/api/session',headers={'sec-fetch-site':'cross-site'}).status_code==403
    assert client.get('/api/health',headers={'origin':'https://evil.test'}).status_code==403
    with TestClient(create_app(tmp_path,False),base_url='http://localhost',client=('192.0.2.1',1)) as remote:
        assert remote.get('/api/health').status_code==403

def test_health_schema_and_no_secret_echo(client_lab):
    client,lab=client_lab
    (lab.root/'.env').write_text('ALPACA_API_KEY=key-marker\nALPACA_SECRET_KEY=secret-marker',encoding='utf-8')
    response=client.get('/api/health');assert response.json()['credentials_configured']
    assert 'key-marker' not in response.text and 'secret-marker' not in response.text
    assert 'frame-ancestors' in response.headers['content-security-policy']
    schema=client.get('/api/schema').json();assert len(schema['families'])==10 and len(schema['timeframes'])==6
    assert client.get('/.env').status_code==404
    assert client.get('/data/lab.sqlite3').status_code==404

def test_real_api_worker_result_and_exports(client_lab):
    client,lab=client_lab;m=seed(lab)
    created=client.post('/api/experiments',json=payload(m));assert created.status_code==202
    jid=created.json()['id']
    assert client.get(f'/api/jobs/{jid}/result').status_code==409
    Worker(lab).run_once()
    job=client.get(f'/api/jobs/{jid}').json();assert job['status']=='completed' and 'owner' not in job
    report=client.get(f'/api/jobs/{jid}/report');assert report.status_code==200
    assert report.json()['metrics']['net_profit']==0 and report.json()['provenance']['input_kind']=='synthetic'
    exported=client.get(f'/api/jobs/{jid}/export/json');assert exported.json()==report.json()
    assert 'attachment' in exported.headers['content-disposition']
    assert client.get(f'/api/jobs/{jid}/export/csv').status_code==200
    assert any(e['kind']=='result_saved' for e in client.get(f'/api/jobs/{jid}/events').json())
    assert client.post(f'/api/jobs/{jid}/resume').status_code==409

def test_import_csv_parquet_roundtrip_and_attestation(client_lab):
    client,lab=client_lab;frame=minute_frame('2026-11-02')
    fields={'start':'2026-11-02','end':'2026-11-02','input_kind':'synthetic'}
    response=client.post('/api/imports',data=fields,files={'file':('prices.csv',frame.to_csv(index=False),'text/csv')})
    assert response.status_code==201
    csv_id=response.json()['id'];assert response.json()['quality']['eligible']
    buffer=BytesIO();frame.to_parquet(buffer,index=False)
    result=client.post('/api/imports',data=fields,files={'file':('../../prices.parquet',buffer.getvalue(),'application/octet-stream')})
    assert result.status_code==201 and result.json()['bars_sha256']==response.json()['bars_sha256']
    fields['input_kind']='historical_market_data'
    history=client.post('/api/imports',data=fields,files={'file':('history.csv',frame.to_csv(index=False))}).json()
    assert history['metadata']['corporate_action_issues']
    request=Experiment(dataset_id=history['id'],start='2026-11-02',end='2026-11-02').model_dump(mode='json')
    assert client.post('/api/experiments',json=request).status_code==409
    assert client.get(f'/api/datasets/{csv_id}/audit').json()['id']==csv_id
    assert len(client.get('/api/datasets').json())==3

@pytest.mark.parametrize('field,value',[('adjustment','split'),('actions_json','{}'),('start','2026-11-03'),('input_kind','guaranteed')])
def test_import_contract_failure(client_lab,field,value):
    client,_=client_lab;fields={'start':'2026-11-02','end':'2026-11-02','input_kind':'synthetic',field:value}
    result=client.post('/api/imports',data=fields,files={'file':('prices.csv',minute_frame('2026-11-02').to_csv(index=False))})
    assert result.status_code==409

def test_malformed_oversized_invalid_requests_rejected(client_lab):
    client,_=client_lab
    assert client.post('/api/imports',data={'start':'2026-11-02','end':'2026-11-02'},files={'file':('bad.csv',b'not,prices')}).status_code==409
    assert client.post('/api/strategies',json={},headers={'content-length':str(70*1024*1024)}).status_code==413
    invalid=client.post('/api/strategies',json={'name':'valid','strategy':{'bogus':'do-not-reflect'}})
    assert invalid.status_code==422 and 'do-not-reflect' not in invalid.text
    assert client.get('/api/datasets/not-valid/audit').status_code==409
    assert client.get('/api/jobs/missing').status_code==409

def test_api_holdout_blocks_preview_experiment_and_selection(client_lab):
    client,lab=client_lab;m=seed(lab)
    result=client.post('/api/studies',json=study_payload(m));assert result.status_code==201
    sid=result.json()['id']
    assert client.get(f'/api/datasets/{m["id"]}/preview',params={'symbol':'SPY','start':'2026-11-05','end':'2026-11-06'}).status_code==409
    body={**payload(m),'end':'2026-11-06'}
    assert client.post('/api/experiments',json=body).status_code==409
    assert client.post(f'/api/datasets/{m["id"]}/select',json={'symbols':['SPY'],'start':'2026-11-05','end':'2026-11-06'}).status_code==409
    assert client.post(f'/api/studies/{sid}/screen').status_code==202
    assert client.post(f'/api/studies/{sid}/screen').status_code==409
    Worker(lab).run_once()
    assert client.get('/api/studies').json()[0]['status']=='no_candidates'
    assert client.post(f'/api/studies/{sid}/final').status_code==409

def test_strategy_parent_and_queue_cancel_resume(client_lab):
    client,lab=client_lab;m=seed(lab)
    first=client.post('/api/strategies',json={'name':'First','strategy':{}}).json()
    second=client.post('/api/strategies',json={'name':'Second','strategy':{'target':'2R'},'parent_id':first['id']}).json()
    assert second['parent_id']==first['id'] and len(client.get('/api/strategies').json())==2
    assert client.post('/api/strategies',json={'name':'Bad parent','strategy':{},'parent_id':'missing'}).status_code==409
    job=client.post('/api/experiments',json=payload(m)).json();jid=job['id']
    assert client.post(f'/api/jobs/{jid}/cancel').json()['status']=='canceled'
    assert client.post(f'/api/jobs/{jid}/resume').json()['status']=='queued'
    Worker(lab).run_once();assert client.get(f'/api/jobs/{jid}').json()['status']=='completed'

def test_result_and_part_tamper_rejected(client_lab):
    client,lab=client_lab;m=seed(lab)
    job=client.post('/api/searches',json={**payload(m),'count':1,'timeframes':['1h']}).json();jid=job['id']
    Worker(lab).run_once()
    assert client.get(f'/api/jobs/{jid}/report',params={'part':0}).status_code==200
    part=lab.root/'data'/'jobs'/jid/'parts'/'000000.json.gz';part.write_bytes(part.read_bytes()+b'corrupt')
    assert client.get(f'/api/jobs/{jid}/report',params={'part':0}).status_code==409
    root=lab.output_path(jid);root.write_bytes(root.read_bytes()+b'corrupt')
    assert client.get(f'/api/jobs/{jid}/result').status_code==409

def test_worker_shutdown_requeues_instead_of_losing_work(client_lab,monkeypatch):
    _,lab=client_lab;m=seed(lab);job=lab.create_experiment(Experiment(**payload(m)))
    stop=Event();worker=Worker(lab,stop)
    def interrupted(job,cancel):
        stop.set()
        assert cancel()
        raise InterruptedError('Shutdown')
    monkeypatch.setattr(worker,'_execute',interrupted)
    worker.run_once();assert lab.store.job(job['id'])['status']=='queued'
    assert lab.store.events(job['id'])[-1]['kind']=='worker_shutdown_checkpoint'
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'

def test_screen_double_submit_transactional(client_lab):
    _,lab=client_lab;m=seed(lab);sid=lab.register_study(Study(**study_payload(m)))['id']
    def enqueue(_):
        try: return lab.screen(sid)['id']
        except StateError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: ids=list(pool.map(enqueue,[1,2]))
    assert sum(i is not None for i in ids)==1

def test_actual_spawned_worker_process_and_clean_shutdown(tmp_path,record_property):
    import os,time
    app=create_app(tmp_path,run_worker=True)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
        process=app.state.worker_process
        assert process.pid!=os.getpid() and process.is_alive()
        # Measure Windows process startup separately from execution. The earlier
        # arbitrary 20-second deadline combined import/startup and a queued job;
        # its failures remain retained, not certified as a performance pass.
        begun=time.monotonic()
        ready=app.state.worker_ready.wait(60)
        record_property('worker_startup_seconds',time.monotonic()-begun)
        assert ready and process.is_alive(), 'Worker did not become ready within the diagnostic startup envelope.'
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        manifest=seed(app.state.lab)
        created=client.post('/api/experiments',json=payload(manifest));assert created.status_code==202
        jid=created.json()['id'];begun=time.monotonic();deadline=begun+20
        while time.monotonic()<deadline:
            job=client.get('/api/jobs/'+jid).json()
            if job['status'] in {'completed','failed'}: break
            time.sleep(.1)
        record_property('three_session_job_seconds',time.monotonic()-begun)
        assert job['status']=='completed'
        assert client.get('/api/jobs/'+jid+'/report').json()['metrics']['net_profit']==0
    assert not process.is_alive()

def test_audit_and_discovery_subset_do_not_leak_future_action_values(client_lab):
    from backend.lab.data import load_dataset,Action
    client,lab=client_lab;original=seed(lab)
    frame,_=load_dataset(lab.datasets_root,original['id'])
    manifest=save_dataset(lab.datasets_root,frame,{'input_kind':'synthetic','corporate_actions_raw':{'future_cash':'7.65432189'}},
        [Action('SPY','2026-11-05','dividend',7.65432189)],start='2026-11-02',end='2026-11-06')
    assert client.post('/api/studies',json=study_payload(manifest)).status_code==201
    audit=client.get('/api/datasets/'+manifest['id']+'/audit')
    assert audit.status_code==200 and '7.65432189' not in audit.text
    assert 'corporate_actions_raw' not in audit.json()['metadata']
    subset=client.post('/api/datasets/'+manifest['id']+'/select',json={'symbols':['SPY'],'start':'2026-11-02','end':'2026-11-03'})
    assert subset.status_code==200 and '7.65432189' not in subset.text
    assert subset.json()['quality']['eligible']
