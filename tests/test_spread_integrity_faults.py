"""Rejected lifecycle edits, original journal corruption and bounded metadata reads."""
from copy import deepcopy
import json
import pytest
from backend.lab.config import Strategy,identity,canonical
from backend.lab.store import StateError
from backend.lab.spread import SpreadSettings
from backend.lab.spread_jobs import projection,initial,digest,integer,coordinate,SpreadJournal,bounded_status,event_page
from test_spread_journal import owned,start_probe,batch_record

S=SpreadSettings(families=['break_of_structure'],per_family=1,batch_size=2,max_batches_per_family=1)
C=dict(dataset_id='a'*24,dataset_manifest_hash='b'*64,primary_symbol='SPY',start='2026-11-02',end='2026-11-06')
CFG=Strategy(family='break_of_structure').model_dump()
P=dict(family='break_of_structure',batch=0,ordinal=1,config_id=identity(CFG))
HISTORY=[dict(kind='preparation_started',contract_hash='c'*64),dict(kind='preparation_batch',record=batch_record()),
 dict(kind='preparation_sealed',plan_id='d'*64),dict(kind='selection_started',plan_id='d'*64,context=C),
 dict(kind='batch_started',family=P['family'],batch=0,configuration_hash='f'*64),dict(kind='probe_planned',**P),
 dict(kind='probe_started',**P,attempt=1),dict(kind='probe_completed',**P,attempt=1,evidence=dict(signal_count=40,evidence_sha256='e'*64)),
 dict(kind='version_selected',**P,signal_count=40,configuration=CFG),
 dict(kind='batch_finished',family=P['family'],batch=0,selected_ordinal=1,outcomes=[dict(ordinal=0,config_id='a'*64,status='not_probed'),dict(ordinal=1,config_id=P['config_id'],status='selected')]),
 dict(kind='selection_finished',complete=True,selected_count=1,exhausted_families=[],selection_manifest_hash='f'*64)]

def before(index):
 p=initial(S)
 for event in HISTORY[:index]:p=projection(p,event,S,C)
 return p

@pytest.mark.parametrize('value',[None,True,-1,1.5,'3'])
def test_counter_domain_is_strict(value):
 with pytest.raises(StateError):integer(value)

@pytest.mark.parametrize('value',[None,42,'A'*64,'a'*63])
def test_evidence_identity_requires_full_lowercase_sha256(value):
 with pytest.raises(StateError):digest(value)

@pytest.mark.parametrize('update',[dict(family='unplanned'),dict(batch=1),dict(ordinal=2),dict(config_id='broken')])
def test_signal_coordinate_cannot_escape_the_frozen_budget(update):
 with pytest.raises(StateError):coordinate(S,P|update)

@pytest.mark.parametrize('index,update',[
 (0,{}),(1,{'record':batch_record()|{'relative_path':'../elsewhere'}}),
 (1,{'record':batch_record()|{'core_hash':'a'*64}}),(2,{}),(3,{'context':C|{'primary_symbol':'QQQ'}}),
 (4,{'batch':1}),(5,{}),(6,{'config_id':'a'*64}),(6,{'attempt':3}),
 (7,{'attempt':2}),(8,{'signal_count':41}),(8,{'configuration':CFG|{'direction':'short'}}),
 (9,{'selected_ordinal':0}),(9,{'outcomes':[]}),(9,{'outcomes':[dict(ordinal=1,config_id='a'*64,status='not_probed'),HISTORY[9]['outcomes'][1]]}),
 (9,{'outcomes':[dict(ordinal=0,config_id='a'*64,status='invented'),HISTORY[9]['outcomes'][1]]}),
 (9,{'outcomes':[dict(ordinal=0,config_id='a'*64,status='insufficient_signals'),HISTORY[9]['outcomes'][1]]}),
 (10,{'complete':False}),(10,{'selected_count':0}),(10,{'exhausted_families':['break_of_structure']})])
def test_corrupt_lifecycle_transition_is_rejected_without_mutating_prior_state(index,update):
 p=before(index);event=deepcopy(HISTORY[index])|deepcopy(update)
 if index==0:p=before(1)
 elif index==2:p=before(1)
 elif index==5:p=before(6)
 original=deepcopy(p)
 with pytest.raises(StateError):projection(p,event,S,C)
 assert p==original

@pytest.mark.parametrize('index,event',[
 (0,HISTORY[1]),(0,HISTORY[5]),(5,HISTORY[9]),(5,HISTORY[8]),(6,HISTORY[7]),
 (10,HISTORY[4]),(11,HISTORY[10]),(0,{'kind':'invented'})])
def test_missing_or_reordered_lifecycle_steps_cannot_be_inferred(index,event):
 with pytest.raises(StateError):projection(before(index),deepcopy(event),S,C)

def test_exhaustion_cannot_publish_a_partial_success_identity():
 p=before(5)
 p=projection(p,dict(kind='batch_finished',family=P['family'],batch=0,selected_ordinal=None,outcomes=[dict(ordinal=i,config_id='a'*64,status='duplicate') for i in range(2)]),S,C)
 with pytest.raises(StateError):projection(p,dict(kind='selection_finished',complete=False,selected_count=0,exhausted_families=S.families,selection_manifest_hash='f'*64),S,C)

@pytest.mark.parametrize('fault',['state_binding','state_hash','metadata_json','metadata_hash','metadata_bytes','original_missing','original_payload','index_json','foreign_kind','input_projection_bytes'])
def test_corrupt_saved_metadata_never_authorizes_reuse(tmp_path,fault):
 store,job,j=owned(tmp_path,SpreadJournal)
 with store.db() as db:
  if fault=='state_binding':db.execute("UPDATE spread_state SET payload_sha256=?",('f'*64,))
  elif fault=='state_hash':db.execute("UPDATE spread_state SET projection_sha256=?",('f'*64,))
  elif fault=='metadata_json':db.execute("UPDATE spread_state SET projection='{' ")
  elif fault=='metadata_hash':db.execute("UPDATE spread_state SET projection='{}'")
  elif fault=='metadata_bytes':db.execute("UPDATE spread_state SET projection=?",(' '*1000000,))
  elif fault=='original_missing':db.execute("DELETE FROM events WHERE kind='trial_plan_frozen'")
  elif fault=='original_payload':db.execute("UPDATE events SET details='{}' WHERE kind='trial_plan_frozen'")
  elif fault=='index_json':db.execute("UPDATE job_input_index SET projection='{' ")
  elif fault=='foreign_kind':db.execute("UPDATE jobs SET kind='search'")
  else:db.execute("UPDATE job_input_index SET projection=?",(' '*1000000,))
 if fault in {'metadata_json','metadata_hash','metadata_bytes','foreign_kind'}:
  with pytest.raises(StateError):bounded_status(store,job['id'])
 else:
  with pytest.raises(StateError):j.load()

@pytest.mark.parametrize('fault',['json','hash','large','extra'])
def test_journal_page_rejects_corrupt_or_oversized_original_envelope(tmp_path,fault):
 store,job,j=owned(tmp_path,SpreadJournal);j.append(HISTORY[0])
 with store.db() as db:
  row=db.execute("SELECT id,details FROM events WHERE kind='spread_protocol'").fetchone();value=json.loads(row['details'])
  if fault=='json':raw='{'
  elif fault=='large':raw=' '*1000000
  elif fault=='extra':raw=json.dumps(value|{'extra':'changed'})
  else:raw=json.dumps(value|{'event_sha256':'a'*64})
  db.execute('UPDATE events SET details=? WHERE id=?',(raw,row['id']))
 with pytest.raises(StateError):event_page(store,job['id'])

@pytest.mark.parametrize('limit',[0,21,True,'2'])
def test_journal_page_rejects_nonbounded_page_requests(tmp_path,limit):
 store,job,j=owned(tmp_path,SpreadJournal)
 with pytest.raises(StateError):event_page(store,job['id'],limit=limit)

@pytest.mark.parametrize('fault',['json','hash','deleted','cutoff'])
def test_original_stream_is_checked_again_after_initial_validation(tmp_path,fault):
 store,job,j=owned(tmp_path,SpreadJournal);j.append(HISTORY[0]);j.load()
 if fault=='cutoff':
  with pytest.raises(StateError):list(j.iter_envelopes(j.replay_through+1))
  return
 with store.db() as db:
  if fault=='deleted':db.execute("DELETE FROM events WHERE kind='spread_protocol'")
  elif fault=='json':db.execute("UPDATE events SET details='{' WHERE kind='spread_protocol'")
  else:
   row=db.execute("SELECT details FROM events WHERE kind='spread_protocol'").fetchone();value=json.loads(row['details']);value['previous']='f'*64
   db.execute("UPDATE events SET details=? WHERE kind='spread_protocol'",(json.dumps(value),))
 with pytest.raises(StateError):list(j.iter_envelopes(j.replay_through))

def test_artifact_binding_is_reserved_for_a_completed_signal(tmp_path):
 store,job,j=owned(tmp_path,SpreadJournal)
 with pytest.raises(StateError):j.append(HISTORY[0],artifact_sha256='a'*64)
 assert j.status()['event_count']==0

@pytest.mark.parametrize('fault',['duplicate_seal','unplanned_start','changed_artifact','missing_phase','malformed_phase','duplicate_plan'])
def test_staged_registry_cannot_be_rebased_on_modified_original_events(tmp_path,fault):
 store,job,j=owned(tmp_path,SpreadJournal);point=start_probe(j,job)
 j.append(dict(kind='probe_completed',**point,attempt=1,evidence=dict(signal_count=40,evidence_sha256='e'*64)),artifact_sha256='f'*64)
 with store.db() as db:
  if fault in {'duplicate_seal','unplanned_start','duplicate_plan'}:
   kind={'duplicate_seal':'preparation_sealed','unplanned_start':'probe_started','duplicate_plan':'probe_planned'}[fault]
   row=next(r for r in db.execute("SELECT details FROM events WHERE kind='spread_protocol'") if json.loads(r['details'])['event']['kind']==kind)
   value=json.loads(row['details'])
   if fault=='unplanned_start':value['event']['ordinal']=0
   store.event('spread_protocol',job['id'],value,db)
  elif fault=='changed_artifact':db.execute("UPDATE trial_attempts SET artifact_sha256=?",('a'*64,))
  elif fault=='missing_phase':db.execute("DELETE FROM events WHERE kind='staged_trial_frozen'")
  else:db.execute("UPDATE events SET details='{' WHERE kind='staged_trial_frozen'")
 with pytest.raises(StateError):store.verify_trial_plan(job['id'])
