"""D042 authored monitoring/scope/input integrity contracts, separate from price execution."""
from contextlib import contextmanager
import json,sqlite3
import pytest
from backend.lab.config import FAMILIES,TIMEFRAMES,identity,canonical
from backend.lab.models import Search
from backend.lab.sampling import sample_common
from backend.lab.research import ResearchError,study_input_hash
from backend.lab.store import Store
from test_api import client_lab,seed,payload,study_payload
from test_trial_registry import payload as trial_payload

def register(client_lab,count=10):
 client,lab=client_lab;manifest=seed(lab)
 request=Search(**(payload(manifest)|dict(count=count,families=list(FAMILIES),timeframes=list(TIMEFRAMES),sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1]))))
 configurations,_=sample_common(request)
 response=client.post('/api/studies',json=study_payload(manifest)|dict(configurations=configurations))
 assert response.status_code==201,response.text
 return client,lab,response.json()['id'],response

@pytest.mark.parametrize('count',[10,1000])
def test_study_creation_status_and_list_are_bounded_with_exact_full_inputs(client_lab,count):
 client,lab,sid,created=register(client_lab,count);original=lab.guard.study(sid)
 for response in [created,client.get('/api/studies/'+sid)]:
  assert response.status_code in {200,201} and len(response.content)<=65536
  value=response.json();assert value['spec']['configuration_count']==count and 'configurations' not in value['spec']
  assert value['index_integrity'] is True and value['inputs_url']=='/api/studies/'+sid+'/inputs'
 listing=client.get('/api/studies');assert listing.status_code==200 and len(listing.content)<=2097152
 assert listing.json()[0]['spec']['configuration_count']==count
 exported=client.get('/api/studies/'+sid+'/inputs');assert exported.status_code==200
 assert exported.json()['study']==original and exported.json()['spec_hash']==study_input_hash(original['spec'])
 assert len(exported.json()['study']['spec']['configurations'])==count

def test_study_monitor_and_protected_scope_never_select_raw_spec(client_lab,monkeypatch):
 client,lab,sid,_=register(client_lab,1000);original_db=lab.store.db;reads=[]
 @contextmanager
 def bounded(*a,**kw):
  with original_db(*a,**kw) as db:
   def authorize(operation,table,column,*rest):
    if operation==sqlite3.SQLITE_READ:
     reads.append((table,column))
     if table=='studies' and column=='spec':return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK
   db.set_authorizer(authorize);yield db
 monkeypatch.setattr(lab.store,'db',bounded)
 assert client.get('/api/studies').status_code==200
 assert client.get('/api/studies/'+sid).status_code==200
 lab.guard.access(['SPY'],'2026-11-02','2026-11-03','authored_allowed')
 lab.guard.access(['OTHER'],'2026-11-05','2026-11-06','authored_other_instrument')
 with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-05','2026-11-05','authored_blocked')
 assert ('studies','spec') not in reads

def test_corrupt_study_cache_is_visible_and_blocks_access_before_viewed_write(client_lab):
 client,lab,sid,_=register(client_lab);original=lab.guard.study(sid)
 with lab.store.db() as db:
  before=db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]
  db.execute("UPDATE study_input_index SET projection='{}' WHERE study_id=?",(sid,))
 view=client.get('/api/studies/'+sid);assert view.status_code==200 and view.json()['index_integrity'] is False
 assert view.json()['spec']=={} and view.json()['integrity_error']
 with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-02','2026-11-02','authored_unknown_scope')
 with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==before
 full=client.get('/api/studies/'+sid+'/inputs');assert full.status_code==200 and full.json()['study']==original
 repaired=client.post('/api/studies/'+sid+'/repair-index');assert repaired.status_code==200 and repaired.json()['index_integrity'] is True
 assert lab.guard.study(sid)==original
 lab.guard.access(['SPY'],'2026-11-02','2026-11-02','authored_repaired_scope')
 with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-06','2026-11-06','authored_protected')

def test_changed_original_study_cannot_export_or_repair_verified_inputs(client_lab):
 client,lab,sid,_=register(client_lab)
 with lab.store.db() as db:
  spec=json.loads(db.execute('SELECT spec FROM studies WHERE id=?',(sid,)).fetchone()[0]);spec['seed']+=1
  db.execute('UPDATE studies SET spec=? WHERE id=?',(canonical(spec),sid))
 assert client.get('/api/studies/'+sid+'/inputs').status_code==409
 assert client.post('/api/studies/'+sid+'/repair-index').status_code==409

@pytest.mark.parametrize('bad',['not-json','[]',json.dumps(dict(strategy={},cost_arms=[dict(part=0)])),canonical(trial_payload()|dict(cost_arms=[dict(part=0,costs=trial_payload()['costs'])]*2)),pytest.param(b'not-json',id='blob-input')])
def test_unreconstructible_legacy_plan_does_not_abort_valid_neighbors_or_fabricate_attempts(tmp_path,bad):
 store=Store(tmp_path);good=canonical(trial_payload())
 with store.db() as db:
  for jid,kind,raw in [('bad','borrow_sensitivity',bad),('valid','experiment',good)]:
   db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,kind,raw,1,1))
 recovered=Store(tmp_path)
 with recovered.db() as db:
  assert db.execute('SELECT payload FROM jobs WHERE id=?',('bad',)).fetchone()[0]==bad
  assert db.execute('SELECT payload FROM jobs WHERE id=?',('valid',)).fetchone()[0]==good
  assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',('bad',)).fetchone()[0]==0
  assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==0
 assert recovered.registry(job_id='valid')['totals']['legacy_occurrences']==1
 assert recovered.job_status('bad')['index_integrity'] is False
 events=recovered.events('bad');assert len([e for e in events if e['kind']=='legacy_trial_plan_unrecoverable'])==1
 assert not [e for e in events if e['kind'] in ['trial_plan_frozen','legacy_trial_plan_reconstructed']]
 assert len([e for e in Store(tmp_path).events('bad') if e['kind']=='legacy_trial_plan_unrecoverable'])==1

@pytest.mark.parametrize('damage',['missing','scope','scope_hash','projection_hash','large','invalid-json'])
def test_unverified_derived_scope_blocks_even_disjoint_reads_and_repair_is_exact(client_lab,damage):
 client,lab,sid,_=register(client_lab);original=lab.store.study_inputs(sid)
 with lab.store.db() as db:
  if damage=='missing':db.execute('DELETE FROM study_input_index WHERE study_id=?',(sid,))
  else:
   column,value={'scope':('scope','{}'),'scope_hash':('scope_sha256','0'*64),'projection_hash':('projection_sha256','0'*64),'large':('projection','x'*30000),'invalid-json':('list_projection','{')}[damage]
   db.execute('UPDATE study_input_index SET '+column+'=? WHERE study_id=?',(value,sid))
 assert client.get('/api/studies/'+sid).json()['index_integrity'] is False
 with pytest.raises(ResearchError):lab.guard.access(['UNRELATED'],'2026-11-02','2026-11-02','authored_unknown_scope')
 assert client.post('/api/studies/'+sid+'/repair-index').json()['index_integrity'] is True
 assert lab.store.study_inputs(sid)==original

@pytest.mark.parametrize('field',['candidates','candidate_hash','screening_report_hash','reserved_final_job_id','final_job_id'])
def test_original_candidate_and_final_evidence_tampering_cannot_be_exported_or_repaired(client_lab,field):
 client,lab,sid,_=register(client_lab);spec=lab.guard.study(sid)['spec']
 lab.guard.screened(sid,'f'*64,[spec['configurations'][0]])
 with lab.store.db() as db:
  changed=json.loads(db.execute('SELECT spec FROM studies WHERE id=?',(sid,)).fetchone()[0])
  changed[field]=[] if field=='candidates' else '0'*64
  db.execute('UPDATE studies SET spec=? WHERE id=?',(canonical(changed),sid))
 assert client.get('/api/studies/'+sid+'/inputs').status_code==409
 assert client.post('/api/studies/'+sid+'/repair-index').status_code==409

def test_study_index_backfill_streams_and_preserves_original_bytes_and_bad_neighbors(client_lab):
 client,lab,sid,_=register(client_lab);before=lab.guard.study(sid)
 with lab.store.db() as db:
  original=db.execute('SELECT spec FROM studies WHERE id=?',(sid,)).fetchone()[0]
  db.execute('DROP TABLE study_input_index')
 recovered=Store(lab.root);assert recovered.study_status(sid)['index_provenance']=='backfilled_verified_registration'
 assert recovered.study_inputs(sid)['study']==before
 with recovered.db() as db:assert db.execute('SELECT spec FROM studies WHERE id=?',(sid,)).fetchone()[0]==original

@pytest.mark.parametrize('limit,offset',[(0,0),(501,0),(True,0),(1,-1),(1,True)])
def test_study_history_rejects_invalid_direct_pages(tmp_path,limit,offset):
 with pytest.raises(ValueError):Store(tmp_path).study_statuses(limit,offset)

def test_malformed_legacy_sampling_rolls_back_the_already_inserted_trial(tmp_path):
 store=Store(tmp_path);raw=canonical(trial_payload()|dict(sampling=['malformed']))
 with store.db() as db:db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',('bad-sampling','experiment',raw,1,1))
 recovered=Store(tmp_path)
 with recovered.db() as db:
  assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',('bad-sampling',)).fetchone()[0]==0
  assert db.execute('SELECT payload FROM jobs WHERE id=?',('bad-sampling',)).fetchone()[0]==raw
 assert recovered.job_status('bad-sampling')['index_integrity'] is False

@pytest.mark.parametrize('damage',['blob','checksummed_nonobject_scope'])
def test_malformed_but_checksummed_scope_and_blob_cache_fail_visibly_closed(client_lab,damage):
 import hashlib
 from backend.lab.study_index import binding
 client,lab,sid,_=register(client_lab)
 with lab.store.db() as db:
  if damage=='blob':db.execute('UPDATE study_input_index SET projection=? WHERE study_id=?',(sqlite3.Binary(b'broken'),sid))
  else:
   row=dict(db.execute('SELECT * FROM study_input_index WHERE study_id=?',(sid,)).fetchone());raw='[]';scope_hash=hashlib.sha256(raw.encode()).hexdigest()
   checksum=binding(row['spec_hash'],json.loads(row['projection']),json.loads(row['list_projection']),scope_hash,row['provenance'])
   db.execute('UPDATE study_input_index SET scope=?,scope_sha256=?,projection_sha256=? WHERE study_id=?',(raw,scope_hash,checksum,sid))
 view=client.get('/api/studies/'+sid);assert view.status_code==200 and view.json()['index_integrity'] is False
 with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-02','2026-11-02','malformed_cache')

def test_large_study_documents_and_universe_remain_on_demand_and_projection_is_bounded():
 from copy import deepcopy
 from backend.lab.study_index import projections
 p=dict(symbols=['S'+str(i).zfill(5) for i in range(1000)],holdout=dict(start='2026-11-05',end='2026-11-06'),configurations=[{}]*1000)
 for key in ['core_hash','dataset_manifest_hash','costs','portfolio','seed','minimum_trades','minimum_sharpe','news_calendar_id','candidate_hash','screening_report_hash']:
  p[key]='x'*3900
 p['dataset_context']=dict(symbols=p['symbols'],documents=['y'*1000000]);before=deepcopy(p)
 detail,listed,scope=projections(p)
 assert p==before and detail['configuration_count']==1000 and detail['instrument_count']==1000
 assert len(canonical(detail).encode())<=24576 and len(canonical(listed).encode())<=1024
 assert scope['symbols']==p['symbols'] and 'dataset_context' in detail['omitted_fields']

@pytest.mark.parametrize('changes',[dict(symbols=[]),dict(symbols=[None]),dict(holdout={}),dict(holdout=dict(start='2026-11-06',end='2026-11-05')),dict(final_job_id={}),dict(reserved_final_job_id='x'*3000)])
def test_unrepresentable_legacy_protection_fields_cannot_form_a_verified_scope(changes):
 from backend.lab.study_index import projections
 p=dict(symbols=['SPY'],holdout=dict(start='2026-11-05',end='2026-11-06'),configurations=[{}])|changes
 with pytest.raises((ValueError,TypeError,KeyError)):projections(p)

def test_bad_legacy_study_neighbor_does_not_abort_valid_index_backfill(client_lab):
 client,lab,sid,_=register(client_lab);original=lab.store.study_inputs(sid)
 with lab.store.db() as db:
  db.execute('INSERT INTO studies(id,name,dataset_id,spec,status,created,updated) VALUES(?,?,?,?,?,?,?)',('invalid','Invalid legacy scope',original['study']['dataset_id'],'[]','registered',1,1))
  db.execute('DROP TABLE study_input_index')
 recovered=Store(lab.root);assert recovered.study_inputs(sid)==original and recovered.study_status(sid)['index_integrity'] is True
 assert recovered.study_status('invalid')['index_integrity'] is False
 with recovered.db() as db:assert db.execute('SELECT spec FROM studies WHERE id=?',('invalid',)).fetchone()[0]=='[]'

def test_unknown_study_inputs_repair_and_api_pages_are_explicit(client_lab):
 client,lab=client_lab
 for suffix in ['', '/inputs']:
  assert client.get('/api/studies/unknown'+suffix).status_code==409
 assert client.post('/api/studies/unknown/repair-index').status_code==409
 for query in ['?limit=0','?limit=501','?offset=-1']:assert client.get('/api/studies'+query).status_code==422
 assert client.get('/api/studies?offset=999').json()==[]

def test_maximum_retained_study_history_is_paged_and_utf8_bounded(client_lab):
 client,lab,sid,_=register(client_lab);base=lab.guard.study(sid);spec=base['spec']
 # Retained metadata fixture only; these are not505 accepted price-data registrations.
 with lab.store.db() as db:
  db.execute('BEGIN IMMEDIATE')
  for n in range(504):
   identifier='history'+str(n).zfill(5)
   db.execute('INSERT INTO studies(id,name,dataset_id,spec,status,created,updated) VALUES(?,?,?,?,?,?,?)',(identifier,'測'*100,base['dataset_id'],canonical(spec),'registered',n,n))
   lab.store.event('study_registered',identifier,dict(spec_hash=study_input_hash(spec),holdout=spec['holdout']),db)
   lab.store._study_index.add(db,identifier,spec)
  db.execute('COMMIT')
 first=client.get('/api/studies');second=client.get('/api/studies?offset=500&limit=10')
 assert first.status_code==second.status_code==200 and len(first.content)<=2097152
 assert len(first.json())==500 and len(second.json())==5
 assert not {s['id'] for s in first.json()} & {s['id'] for s in second.json()}

def test_matching_recomputed_candidate_hash_does_not_replace_frozen_selection(client_lab):
 client,lab,sid,_=register(client_lab);spec=lab.guard.study(sid)['spec'];lab.guard.screened(sid,'f'*64,[spec['configurations'][0]])
 with lab.store.db() as db:
  changed=json.loads(db.execute('SELECT spec FROM studies WHERE id=?',(sid,)).fetchone()[0]);changed['candidates']=[changed['configurations'][1]];changed['candidate_hash']=identity(changed['candidates'])
  db.execute('UPDATE studies SET spec=? WHERE id=?',(canonical(changed),sid))
 assert client.get('/api/studies/'+sid+'/inputs').status_code==409
 assert client.post('/api/studies/'+sid+'/repair-index').status_code==409

def test_cached_scope_requires_exact_live_final_owner_and_consumed_lifecycle(client_lab,monkeypatch):
 client,lab,sid,_=register(client_lab);spec=lab.guard.study(sid)['spec']
 # Authority-only transition fixture: no screening outcomes or numerical account is claimed.
 lab.guard.screened(sid,'f'*64,[spec['configurations'][0]]);job=lab.final(sid)
 from backend.lab.data import read_manifest
 manifest=read_manifest(lab.datasets_root,spec['dataset_context']['dataset_id']);lab.guard.begin_final(sid,job['id'],manifest)
 original_db=lab.store.db
 @contextmanager
 def restricted(*a,**kw):
  with original_db(*a,**kw) as db:
   db.set_authorizer(lambda operation,table,column,*rest:sqlite3.SQLITE_DENY if operation==sqlite3.SQLITE_READ and table=='studies' and column=='spec' else sqlite3.SQLITE_OK)
   yield db
 monkeypatch.setattr(lab.store,'db',restricted)
 lab.guard.access(['SPY'],'2026-11-05','2026-11-06','owner_allowed',sid,job['id'])
 with original_db() as db:before=db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]
 for owner,final in [(sid,'wrong-job'),('wrong-study',job['id']),(sid,None),(None,job['id'])]:
  with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-05','2026-11-06','owner_blocked',owner,final)
 with original_db() as db:
  assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==before
  db.execute("UPDATE studies SET status='screened' WHERE id=?",(sid,))
 with pytest.raises(ResearchError):lab.guard.access(['SPY'],'2026-11-05','2026-11-06','not_consumed',sid,job['id'])
 for state in ['final_failed','final_complete']:
  with original_db() as db:db.execute('UPDATE studies SET status=? WHERE id=?',(state,sid))
  lab.guard.access(['SPY'],'2026-11-05','2026-11-06','same_owner_continuation',sid,job['id'])
