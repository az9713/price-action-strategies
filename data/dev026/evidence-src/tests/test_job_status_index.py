"""Bound monitoring/control I/O independently of raw plans; keep exact full inputs available."""
from contextlib import contextmanager
import json,sqlite3
import pytest
from backend.lab.config import identity
from backend.lab.store import Store,StateError
from test_api import client_lab,seed,payload

def search(client_lab,count=1000):
 client,lab=client_lab;m=seed(lab);request=payload(m)|dict(count=count,families=['break_of_structure'],timeframes=['1m'],sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1]))
 response=client.post('/api/searches',json=request);assert response.status_code==202,response.text
 return client,lab,response.json(),response

@pytest.mark.parametrize('count',[10,1000])
def test_registered_and_polled_status_is_bounded_and_full_inputs_are_exact(client_lab,count):
 client,lab,job,created=search(client_lab,count);jid=job['id'];original=lab.store.job(jid)['payload']
 for response in [created,client.get('/api/jobs/'+jid)]:
  assert response.status_code==200 if response is not created else response.status_code==202
  assert len(response.content)<=65536
  value=response.json();assert value['payload']['configuration_count']==count
  assert 'configurations' not in value['payload'] and 'proposals' not in value['payload']['sampling']
  assert value['inputs_url']=='/api/jobs/'+jid+'/inputs'
 inputs=client.get('/api/jobs/'+jid+'/inputs');assert inputs.status_code==200
 assert inputs.json()['payload']==original and inputs.json()['payload_sha256']==identity(original)
 assert len(inputs.json()['payload']['configurations'])==count
 assert len(inputs.json()['payload']['sampling']['proposals'])>=count
 assert lab.store.registry(1,0,jid)['totals']['planned_occurrences']==count

def test_monitor_list_cancel_and_resume_never_read_or_decode_the_raw_payload(client_lab,monkeypatch):
 client,lab,job,_=search(client_lab);jid=job['id'];db_method=lab.store.db;reads=[]
 def forbid(*a,**k):raise AssertionError('Full job JSON was materialized by monitoring/control')
 monkeypatch.setattr(lab.store,'job',forbid);monkeypatch.setattr(lab.store,'jobs',forbid)
 @contextmanager
 def bounded_db(*a,**k):
  with db_method(*a,**k) as db:
   def authorize(action,table,column,*rest):
    if action==sqlite3.SQLITE_READ:
     reads.append((table,column))
     if table=='jobs' and column=='payload':return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK
   db.set_authorizer(authorize);yield db
 monkeypatch.setattr(lab.store,'db',bounded_db)
 for method,path,wanted in [('get','/api/jobs/'+jid,'queued'),('get','/api/jobs',None),('get','/api/trial-registry?job_id='+jid,None),('post','/api/jobs/'+jid+'/cancel','canceled'),('post','/api/jobs/'+jid+'/resume','queued')]:
  response=getattr(client,method)(path);assert response.status_code==200,(method,path,response.text)
  assert len(response.content)<=(2097152 if path=='/api/jobs' else 65536)
  if wanted:assert response.json()['status']==wanted
 assert ('jobs','payload') not in reads

def test_corrupt_index_is_visible_and_repair_preserves_authoritative_inputs(client_lab):
 client,lab,job,_=search(client_lab,10);jid=job['id'];before=lab.store.job(jid)['payload'];trials=lab.store.registry(100,0,jid)
 with lab.store.db() as db:db.execute("UPDATE job_input_index SET projection='{}' WHERE job_id=?",(jid,))
 response=client.get('/api/jobs/'+jid);assert response.status_code==200 and response.json()['index_integrity'] is False
 assert response.json()['payload']=={} and response.json()['integrity_error']
 assert client.get('/api/jobs').status_code==200
 exported=client.get('/api/jobs/'+jid+'/inputs');assert exported.status_code==200 and exported.json()['payload']==before
 fixed=client.post('/api/jobs/'+jid+'/repair-index');assert fixed.status_code==200 and fixed.json()['index_integrity'] is True
 assert lab.store.job(jid)['payload']==before and lab.store.registry(100,0,jid)==trials

def test_original_input_corruption_cannot_be_exported_or_repaired(client_lab):
 client,lab,job,_=search(client_lab,10);jid=job['id']
 with lab.store.db() as db:
  value=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()['payload']);value['seed']+=1
  db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(value),jid))
 assert client.get('/api/jobs/'+jid+'/inputs').status_code==409
 assert client.post('/api/jobs/'+jid+'/repair-index').status_code==409

def test_legacy_backfill_preserves_original_payload_bytes_and_trial_registry(client_lab):
 _,lab,job,_=search(client_lab,10);jid=job['id'];registry=lab.store.registry(100,0,jid)
 with lab.store.db() as db:
  original=db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()['payload']
  db.execute('DROP TABLE job_input_index')
 migrated=Store(lab.root)
 with migrated.db() as db:assert db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()['payload']==original
 assert migrated.job_status(jid)['index_integrity'] is True
 assert migrated.job_status(jid)['index_provenance']=='backfilled_stored_inputs'
 assert migrated.registry(100,0,jid)==registry

def test_malformed_legacy_input_does_not_block_other_statuses_or_startup(client_lab):
 client,lab,job,_=search(client_lab,10);jid=job['id']
 with lab.store.db() as db:
  db.execute('UPDATE jobs SET payload=? WHERE id=?',('not-json',jid));db.execute('DROP TABLE job_input_index')
 migrated=Store(lab.root)
 assert migrated.job_status(jid)['index_integrity'] is False
 assert client.get('/api/jobs').status_code==200
 assert client.get('/api/jobs/'+jid+'/inputs').status_code==409
 assert client.post('/api/jobs/'+jid+'/repair-index').status_code==409

def test_malformed_claim_is_failed_without_killing_the_worker_loop(client_lab):
 from backend.lab.worker import Worker
 client,lab,job,_=search(client_lab,10);jid=job['id']
 with lab.store.db() as db:db.execute('UPDATE jobs SET payload=? WHERE id=?',('not-json',jid))
 Worker(lab).run_once()
 assert lab.store.job_status(jid)['status']=='failed'
 assert lab.store.registry(100,0,jid)['totals']['computation_attempts']==0

def test_large_assumptions_and_universe_are_on_demand_without_new_input_limits(client_lab):
 _,lab,job,_=search(client_lab,10)
 p=lab.store.job(job['id'])['payload'];p=dict(p);p['news_calendar']={'documents':['x'*1000000]};p['costs']=dict(p['costs'],borrow_scenario={'events':[{'notes':'y'*1000000}]})
 p['dataset_context']=dict(p['dataset_context'],symbols=['BIG'+str(i).zfill(4) for i in range(1000)])
 # Metadata-only plan: no worker executes these authored assumption documents.
 p.pop('sampling',None);p.pop('configurations',None)
 new=lab.store.create_job('experiment',p);view=lab.store.job_status(new['id'])
 assert len(json.dumps(view).encode())<=65536
 assert 'dataset_context' not in view['payload']
 assert view['payload']['dataset_context_summary']['instrument_count']==1000
 assert view['payload']['dataset_context_summary']['complete'] is False
 assert 'costs' in view['payload']['omitted_fields'] and 'news_calendar' not in view['payload']
 full=lab.store.job_inputs(new['id']);assert full['payload']==p and len(full['payload']['dataset_context']['symbols'])==1000

def test_full_job_history_pages_and_message_previews_are_bounded(client_lab):
 client,lab=client_lab
 for i in range(505):
  lab.store.create_job('download',dict(name='測'*100,dataset_id='a'*24,count=i))
 with lab.store.db() as db:db.execute('UPDATE jobs SET note=?,error=?',('n'*10000,'e'*10000))
 first=client.get('/api/jobs');assert first.status_code==200 and len(first.json())==500
 assert len(first.content)<=2097152
 second=client.get('/api/jobs?offset=500&limit=10');assert second.status_code==200 and len(second.json())==5
 assert not {j['id'] for j in first.json()} & {j['id'] for j in second.json()}
 jid=first.json()[0]['id'];detail=client.get('/api/jobs/'+jid)
 assert len(detail.content)<=65536 and detail.json()['note_truncated'] and detail.json()['error_truncated']
 assert len(detail.json()['note'])==2048 and len(first.json()[0]['note'])==128
 full=client.get('/api/jobs/'+jid+'/inputs');assert full.status_code==200
 assert full.json()['stored_diagnostics']['note']=='n'*10000
 assert full.json()['stored_diagnostics']['error']=='e'*10000
 assert client.get('/api/jobs?offset=999').json()==[]
 for suffix in ['?limit=501','?limit=0','?offset=-1']:assert client.get('/api/jobs'+suffix).status_code==422
 for method,suffix in [('get',''),('get','/inputs'),('post','/repair-index')]:
  assert getattr(client,method)('/api/jobs/missing'+suffix).status_code==409

@pytest.mark.parametrize('damage',['missing','oversize','invalid-json','wrong-list','wrong-hash'])
def test_bad_derived_cache_is_visible_repairable_and_never_changes_inputs(client_lab,damage):
 client,lab,job,_=search(client_lab,10);jid=job['id'];original=lab.store.job_inputs(jid)
 with lab.store.db() as db:
  if damage=='missing':db.execute('DELETE FROM job_input_index WHERE job_id=?',(jid,))
  else:
   column,value={'oversize':('projection','x'*30000),'invalid-json':('projection','{'),'wrong-list':('list_projection','[]'),'wrong-hash':('projection_sha256','0'*64)}[damage]
   db.execute('UPDATE job_input_index SET '+column+'=? WHERE job_id=?',(value,jid))
 assert client.get('/api/jobs/'+jid).json()['index_integrity'] is False
 assert client.get('/api/trial-registry?job_id='+jid).json()['rows'][0]['job_index_integrity'] is False
 assert client.post('/api/jobs/'+jid+'/cancel').json()['status']=='canceled'
 assert client.post('/api/jobs/'+jid+'/resume').json()['status']=='queued'
 assert client.post('/api/jobs/'+jid+'/repair-index').json()['index_integrity'] is True
 assert lab.store.job_inputs(jid)['payload']==original['payload']
 assert lab.store.job_inputs(jid)['payload_sha256']==original['payload_sha256']

def test_backfill_rejects_valid_json_with_changed_frozen_inputs(client_lab):
 _,lab,job,_=search(client_lab,10);jid=job['id']
 with lab.store.db() as db:
  p=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()[0]);p['seed']+=1
  db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(p),jid));db.execute('DROP TABLE job_input_index')
 migrated=Store(lab.root)
 assert migrated.job_status(jid)['index_integrity'] is False
 with pytest.raises(StateError):migrated.job_inputs(jid)
 with pytest.raises(StateError):migrated.repair_job_index(jid)

def test_projection_bounds_unicode_large_study_plans_and_does_not_mutate_inputs():
 from copy import deepcopy
 from backend.lab.job_index import project,small,DETAIL_BYTES,LIST_BYTES
 p=dict(name='界'*4096,dataset_id='a'*24,trial_configurations=[dict(strategy=i) for i in range(1000)],
        dataset_context=dict(symbols=['S'+str(i) for i in range(1000)]),sampling=dict(proposals=[{}]*1000),
        costs=dict(documents=['x'*1000000]),strategy=dict(nested=[{'x':i} for i in range(200)]))
 before=deepcopy(p);detail,listed=project(p)
 assert p==before and detail['configuration_count']==1000
 assert detail['sampling']['proposal_count']==1000 and 'proposals' not in detail['sampling']
 assert detail['dataset_context_summary']['instrument_count']==1000
 assert len(json.dumps(detail,ensure_ascii=False).encode())<=DETAIL_BYTES
 assert len(json.dumps(listed,ensure_ascii=False).encode())<=LIST_BYTES
 for value in [object(),list(range(129)),{str(i):i for i in range(65)},'x'*5000]:assert not small(value)
 assert small({'yes':[True,None,1,1.25]})
 with pytest.raises(ValueError):project([])

def test_projection_aggregate_pruning_and_early_node_bound():
 from backend.lab.job_index import project,small,SCALARS,DETAIL_BYTES,LIST_BYTES
 from backend.lab.config import canonical
 # Many individually acceptable fields still need an aggregate byte budget.
 p={key:'x'*4000 for key in SCALARS};detail,listed=project(p)
 assert len(canonical(detail).encode())<=DETAIL_BYTES and detail['omitted_fields']
 assert len(canonical(listed).encode())<=LIST_BYTES
 assert not small([[0,1] for _ in range(128)])

def test_pending_study_index_matches_only_pending_kind_and_blocks_corrupt_cache(tmp_path):
 store=Store(tmp_path)
 assert not store.pending_study_job('download','one')
 first=store.create_job('download',dict(study_id='one'));second=store.create_job('download',dict(study_id='two'))
 assert store.pending_study_job('download','one') and store.pending_study_job('download','two')
 assert not store.pending_study_job('download','absent') and not store.pending_study_job('news_download','one')
 store.cancel(first['id']);assert not store.pending_study_job('download','one')
 with store.db() as db:db.execute("UPDATE job_input_index SET projection='{}' WHERE job_id=?",(second['id'],))
 with pytest.raises(StateError,match='repair'):store.pending_study_job('download','two')
 store.repair_job_index(second['id']);assert store.pending_study_job('download','two')

def test_borrowing_scenarios_remain_in_bounded_status_and_large_arms_are_on_demand(client_lab):
 client,lab=client_lab;m=seed(lab)
 response=client.post('/api/borrow-sensitivity',json=payload(m));assert response.status_code==202
 value=response.json();full=lab.store.job_inputs(value['id'])['payload']
 assert value['payload']['cost_arms']==full['cost_arms'] and len(full['cost_arms'])==4
 assert value['payload']['rate_policy']==full['rate_policy'] and len(response.content)<=65536
 enlarged=dict(full,cost_arms=[dict(arm,documentation='x'*1000000) for arm in full['cost_arms']])
 job=lab.store.create_job('download',enlarged);view=lab.store.job_status(job['id'])
 assert 'cost_arms' in view['payload']['omitted_fields'] and 'cost_arms' not in view['payload']
 assert lab.store.job_inputs(job['id'])['payload']['cost_arms']==enlarged['cost_arms']

@pytest.mark.parametrize('limit,offset',[(True,0),(501,0),(0,0),(1,-1),(1,True)])
def test_store_page_contract_rejects_nonintegers_and_out_of_bounds(tmp_path,limit,offset):
 with pytest.raises(StateError):Store(tmp_path).job_statuses(limit,offset)
