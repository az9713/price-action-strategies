"""D044 read-connection reuse must preserve live control and ownership authority."""
from contextvars import copy_context
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from backend.lab.store import Store,StateError

@pytest.fixture
def running(tmp_path):
 store=Store(tmp_path);job=store.create_job('experiment',dict(name='Owned controls'));claimed=store.claim('owner');assert claimed['id']==job['id']
 assert callable(getattr(store,'control_reads',None)),'Job-local live control reader is not implemented'
 return store,job['id']


def test_repeated_live_checks_reuse_one_readonly_connection_without_raw_payload(running,monkeypatch):
 store,jid=running;connect=sqlite3.connect;connections=[];queries=[]
 def observed(*args,**kwargs):
  db=connect(*args,**kwargs);connections.append(db);db.set_trace_callback(queries.append)
  def authorize(operation,table,column,*rest):
   if operation==sqlite3.SQLITE_READ and table=='jobs' and column=='payload':raise AssertionError('Control read loaded raw input JSON')
   return sqlite3.SQLITE_OK
  db.set_authorizer(authorize);return db
 monkeypatch.setattr(sqlite3,'connect',observed)
 with store.control_reads():
  for _ in range(10):assert store.cancellation_requested(jid,'owner') is False
  assert len(connections)==1
  with pytest.raises(sqlite3.OperationalError):connections[0].execute('UPDATE jobs SET cancel_requested=1')
  assert not connections[0].in_transaction
 assert not any('journal_mode' in q.lower() for q in queries)
 with pytest.raises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')


def test_external_cancel_changes_are_visible_on_the_very_next_check(running):
 store,jid=running
 with store.control_reads():
  assert store.cancellation_requested(jid,'owner') is False
  with store.db() as db:db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(jid,))
  assert store.cancellation_requested(jid,'owner') is True
  with store.db() as db:db.execute('UPDATE jobs SET cancel_requested=0 WHERE id=?',(jid,))
  assert store.cancellation_requested(jid,'owner') is False

@pytest.mark.parametrize('change',['wrong_owner','queued','completed','deleted'])
def test_external_ownership_or_terminal_transition_rejects_immediately(running,change):
 store,jid=running
 with store.control_reads():
  assert store.cancellation_requested(jid,'owner') is False
  if change=='deleted':
   # Inject corruption through a separate owned test connection. Production
   # Store.db keeps its FK policy; ordinary deletion correctly rejects above.
   external=sqlite3.connect(store.path,isolation_level=None)
   try:external.execute('DELETE FROM jobs WHERE id=?',(jid,))
   finally:external.close()
  else:
   with store.db() as db:
    if change=='wrong_owner':db.execute('UPDATE jobs SET owner=? WHERE id=?',('different',jid))
    else:db.execute('UPDATE jobs SET status=? WHERE id=?',(change,jid))
  with pytest.raises(StateError):store.cancellation_requested(jid,'owner')


def test_nested_other_root_and_propagated_thread_context_do_not_share_connections(running,tmp_path,monkeypatch):
 store,jid=running;other=Store(tmp_path/'other');other_job=other.create_job('experiment',dict(name='Other owned controls'));other.claim('other-owner');connect=sqlite3.connect;connections=[]
 def observed(*a,**k):
  db=connect(*a,**k);connections.append(db);return db
 monkeypatch.setattr(sqlite3,'connect',observed)
 with store.control_reads():
  assert store.cancellation_requested(jid,'owner') is False;outer=connections[0]
  with store.control_reads():assert store.cancellation_requested(jid,'owner') is False
  assert len(connections)==1
  with other.control_reads():assert other.cancellation_requested(other_job['id'],'other-owner') is False
  assert len(connections)==2
  with pytest.raises(sqlite3.ProgrammingError):connections[1].execute('SELECT 1')
  context=copy_context()
  def threaded():
   with store.control_reads():return store.cancellation_requested(jid,'owner')
  with ThreadPoolExecutor(max_workers=1) as pool:assert pool.submit(context.run,threaded).result() is False
  assert len(connections)==3 and store.cancellation_requested(jid,'owner') is False
  assert outer.execute('SELECT 1').fetchone()[0]==1
 with pytest.raises(sqlite3.ProgrammingError):outer.execute('SELECT 1')


def test_exception_exit_closes_connection_and_restores_default_path(running,monkeypatch):
 store,jid=running;connect=sqlite3.connect;connections=[]
 def observed(*a,**k):
  db=connect(*a,**k);connections.append(db);return db
 monkeypatch.setattr(sqlite3,'connect',observed)
 with pytest.raises(RuntimeError):
  with store.control_reads():
   assert store.cancellation_requested(jid,'owner') is False;raise RuntimeError('Owned scope fault')
 with pytest.raises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')
 assert store.cancellation_requested(jid,'owner') is False and len(connections)==2



def test_other_store_without_scope_uses_its_own_live_database(running,tmp_path):
 store,jid=running;other=Store(tmp_path/'unscoped-other');job=other.create_job('experiment',dict(name='Independent root'));other.claim('different-owner')
 with store.control_reads():
  assert other.cancellation_requested(job['id'],'different-owner') is False
  assert store.cancellation_requested(jid,'owner') is False



def test_covering_index_upgrade_preserves_original_bytes_rowids_events_and_foreign_keys(tmp_path):
 import hashlib
 store=Store(tmp_path);job=store.create_job('experiment',dict(name='Owned large control-index fixture',padding='X'*(16*1024*1024)));jid=job['id'];store.claim('owner');events=store.events(jid)
 def frozen(db):
  row=db.execute('SELECT rowid,typeof(payload),length(CAST(payload AS BLOB)) FROM jobs WHERE id=?',(jid,)).fetchone();digest=hashlib.sha256()
  with db.blobopen('jobs','payload',row[0],readonly=True) as blob:
   while value:=blob.read(65536):digest.update(value)
  return tuple(row),digest.hexdigest()
 with store.db() as db:
  before=frozen(db);db.execute('DROP INDEX IF EXISTS jobs_live_control')
 rebuilt=Store(tmp_path)
 with rebuilt.db() as db:
  names={row[1] for row in db.execute('PRAGMA index_list(jobs)')};assert 'jobs_live_control' in names,'Existing stores did not acquire the required covering index'
  assert frozen(db)==before and db.execute('PRAGMA foreign_key_check').fetchall()==[]
  fields=[row[2] for row in db.execute('PRAGMA index_info(jobs_live_control)')];assert fields==['id','status','owner','cancel_requested']
 assert rebuilt.events(jid)==events and rebuilt.cancellation_requested(jid,'owner') is False


def test_both_hot_authority_reads_require_the_verified_covering_query_plan(running,monkeypatch):
 store,jid=running;connect=sqlite3.connect;queries=[]
 def observed(*args,**kwargs):
  db=connect(*args,**kwargs);db.set_trace_callback(queries.append);return db
 monkeypatch.setattr(sqlite3,'connect',observed)
 with store.control_reads():assert store.cancellation_requested(jid,'owner') is False
 store.start_trial(jid,0,'report','owner')
 for prefix in ['SELECT status,owner,cancel_requested FROM jobs','SELECT status,owner FROM jobs']:
  selected=[query for query in queries if query.startswith(prefix)];assert selected
  assert all('INDEXED BY jobs_live_control' in query for query in selected)
  with store.db() as db:
   plan=[row[-1] for row in db.execute('EXPLAIN QUERY PLAN '+selected[-1])]
  assert any('COVERING INDEX jobs_live_control' in row for row in plan)


def test_missing_required_query_plan_fails_closed_and_startup_repairs_index(running):
 store,jid=running
 with store.db() as db:
  names={row[1] for row in db.execute('PRAGMA index_list(jobs)')};assert 'jobs_live_control' in names
  db.execute('DROP INDEX jobs_live_control')
 with pytest.raises(sqlite3.OperationalError):store.cancellation_requested(jid,'owner')
 rebuilt=Store(store.root)
 assert rebuilt.cancellation_requested(jid,'owner') is False
