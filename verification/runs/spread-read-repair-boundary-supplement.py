"""Actual saved-record corruption boundaries on unchanged0.25 numerical source."""
from pathlib import Path
import json,os,sys,pytest
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from test_spread_worker import request
from backend.lab.config import canonical,identity
from backend.lab.store import StateError,SPREAD_SELECTION_INDEX_SQL

def record(name,values):
 p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/(name+'.json');p.write_text(json.dumps(dict(scope=__doc__,faults=values,new_financial_accounts=0),indent=2),encoding='utf-8')
def prepared(owned,monkeypatch):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 def forbidden(*a,**k):raise AssertionError('A saved-record boundary reopened prices or generated new signals')
 monkeypatch.setattr('backend.lab.service.load_window',forbidden);monkeypatch.setattr(lab,'spread_signal_probe',forbidden)
 return lab,parent,child

def test_saved_status_projection_link_and_total_byte_boundaries(owned,monkeypatch):
 lab,parent,child=prepared(owned,monkeypatch);done=[]
 with lab.store.db() as db:
  row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],)).fetchone();raw=row['details'];original=json.loads(raw)
  variants={'malformed_json':'{','oversized_original':'x'*4097,'changed_parent':canonical(original|dict(job_id='f'*32)),'changed_child_binding':canonical(original|dict(result_sha256='0'*64))}
  for name,value in variants.items():
   db.execute('UPDATE events SET details=? WHERE id=?',(value,row['id']))
   try:
    with pytest.raises(StateError):lab.spread_status(parent['id'])
    done.append(name)
   finally:db.execute('UPDATE events SET details=? WHERE id=?',(raw,row['id']))
  state=dict(db.execute('SELECT * FROM spread_state WHERE job_id=?',(parent['id'],)).fetchone())
  db.execute('UPDATE spread_state SET event_count=0 WHERE job_id=?',(parent['id'],))
  try:
   with pytest.raises(StateError,match='empty spread journal'):lab.spread_status(parent['id'])
   done.append('empty_count_nonempty_head')
  finally:db.execute('UPDATE spread_state SET event_count=? WHERE job_id=?',(state['event_count'],parent['id']))
  projection=json.loads(state['projection']);projection['unexpected_metadata']='x'*max(1,65000-len(canonical(projection).encode())-100)
  assert len(canonical(projection).encode())<=65536
  db.execute('UPDATE spread_state SET projection=?,projection_sha256=? WHERE job_id=?',(canonical(projection),identity(projection),parent['id']))
  try:
   with pytest.raises(StateError,match='64KiB'):lab.spread_status(parent['id'])
   done.append('whole_status_above_64k_with_individually_bounded_inputs')
  finally:db.execute('UPDATE spread_state SET projection=?,projection_sha256=? WHERE job_id=?',(state['projection'],state['projection_sha256'],parent['id']))
 queued=lab.create_spread(request(owned[1]));saved=lab.spread_status(queued['id']);assert saved['spread']['event_count']==0 and saved['account_job'] is None
 done.append('existing_state_table_without_new_job_row');assert lab.spread_status(parent['id'])['account_job']['id']==child['id'];record('saved-status-boundaries',done)

def test_selected_record_size_structure_index_and_request_boundaries(owned,monkeypatch):
 lab,parent,child=prepared(owned,monkeypatch);done=[]
 with lab.store.db() as db:
  row=next(r for r in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_protocol'",(parent['id'],)) if json.loads(r['details'])['event']['kind']=='version_selected');raw=row['details'];original=json.loads(raw)
  large=original|dict(owner='x'*16385);missing={k:v for k,v in original.items() if k!='owner'}
  for name,value in [('oversized_original_selection',canonical(large)),('missing_original_envelope_key',canonical(missing))]:
   db.execute('UPDATE events SET details=? WHERE id=?',(value,row['id']))
   try:
    with pytest.raises(StateError):lab.spread_selections(parent['id'])
    done.append(name)
   finally:db.execute('UPDATE events SET details=? WHERE id=?',(raw,row['id']))
  db.execute('DROP INDEX spread_selected_events');db.execute('CREATE INDEX spread_selected_events ON events(id)')
  try:
   with pytest.raises(StateError,match='seek index'):lab.spread_selections(parent['id'])
   done.append('wrong_selected_seek_index_definition')
  finally:db.execute('DROP INDEX spread_selected_events');db.execute(SPREAD_SELECTION_INDEX_SQL)
 for limit in [0,101,True,1.5]:
  with pytest.raises(StateError):lab.spread_selections(parent['id'],limit=limit)
  done.append('invalid_direct_page_limit_'+str(limit))
 assert len(lab.spread_selections(parent['id'])['versions'])==1;record('selected-record-boundaries',done)

def test_repair_wrong_kind_binding_missing_result_and_decode_boundaries(owned,monkeypatch):
 lab,parent,child=prepared(owned,monkeypatch);done=[]
 with pytest.raises(StateError,match='original spread parent'):lab.repair_spread_account_link(child['id'])
 done.append('wrong_original_job_kind')
 with lab.store.db() as db:
  row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],)).fetchone();raw=row['details'];original=json.loads(raw)
  for name,value in [('malformed_relationship_json','{'),('changed_parent_binding',canonical(original|dict(job_id='f'*32))),('changed_child_original_binding',canonical(original|dict(result_sha256='0'*64)))]:
   db.execute('UPDATE events SET details=? WHERE id=?',(value,row['id']))
   try:
    with pytest.raises(StateError):lab.repair_spread_account_link(parent['id'])
    done.append(name)
   finally:db.execute('UPDATE events SET details=? WHERE id=?',(raw,row['id']))
  result=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id DESC LIMIT 1",(parent['id'],)).fetchone()
  for name,column,value in [('missing_original_result_event','kind','retained_corrupt_result_kind'),('oversized_original_result_event','details','x'*4097)]:
   assert column in {'kind','details'};db.execute('UPDATE events SET '+column+'=? WHERE id=?',(value,result['id']))
   try:
    with pytest.raises(StateError):lab.repair_spread_account_link(parent['id'])
    done.append(name)
   finally:db.execute('UPDATE events SET '+column+'=? WHERE id=?',('result_saved' if column=='kind' else result['details'],result['id']))
 assert lab.repair_spread_account_link(parent['id'])['account_job']['id']==child['id']
 with lab.store.db() as db:
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==1
 assert lab.store.registry(job_id=child['id'])['totals']['computation_attempts']==0;record('repair-record-boundaries',done)
