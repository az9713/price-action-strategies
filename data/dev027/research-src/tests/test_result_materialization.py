"""D043 authored bounded saved-view and original-integrity contracts; real synthetic worker outputs."""
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,sqlite3
import pytest
from backend.lab.config import canonical
from backend.lab.worker import Worker
from backend.lab import service as service_module
from test_api import client_lab,seed,payload

@pytest.fixture
def saved(client_lab):
 client,lab=client_lab;manifest=seed(lab)
 response=client.post('/api/searches',json=payload(manifest)|dict(count=3,families=['break_of_structure'],timeframes=['1m'],sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1])))
 assert response.status_code==202,response.text;jid=response.json()['id'];Worker(lab).run_once()
 assert lab.store.job_status(jid)['status']=='completed'
 original=lab.result(jid);reports=[lab.report(jid,i) for i in range(3)]
 return client,lab,jid,original,reports

def test_worker_publishes_bounded_summary_rows_and_complete_originals(saved):
 client,lab,jid,original,reports=saved
 summary=client.get('/api/jobs/'+jid+'/result-summary');assert summary.status_code==200,summary.text
 view=summary.json();assert len(summary.content)<=65536 and view['job_id']==jid and view['row_count']==3 and view['index_integrity'] is True
 assert view['complete_result_url']=='/api/jobs/'+jid+'/result' and 'rows' not in view
 collected=[]
 for offset in [0,2]:
  page=client.get('/api/jobs/'+jid+'/result-rows',params=dict(limit=2,offset=offset));assert page.status_code==200 and len(page.content)<=2097152
  value=page.json();assert value['job_id']==jid and value['pagination']==dict(limit=2,offset=offset,total=3)
  collected.extend(value['rows'])
 assert len(collected)==3
 for indexed,source in zip(collected,original['rows']):
  assert all(indexed.get(key)==value for key,value in source.items())
 assert client.get('/api/jobs/'+jid+'/result').json()==original
 for part,report in enumerate(reports):assert client.get('/api/jobs/'+jid+'/report',params=dict(part=part)).json()==report
 for query in [dict(limit=0),dict(limit=101),dict(offset=-1)]:assert client.get('/api/jobs/'+jid+'/result-rows',params=query).status_code==422
 assert client.get('/api/jobs/'+jid+'/result-rows?offset=99').json()['rows']==[]

def test_summary_rows_and_selected_part_never_decode_unrelated_root_or_job_json(saved,monkeypatch):
 client,lab,jid,original,reports=saved;reader=service_module.compressed_read;original_db=lab.store.db;chunks=[];forbidden_reads=[]
 def forbid(*a,**kw):raise AssertionError('Complete root/input JSON was materialized by a saved-view request')
 def bounded_reader(path):
  if Path(path).name=='result.json.gz':forbid()
  return reader(path)
 monkeypatch.setattr(lab,'result',forbid);monkeypatch.setattr(lab.store,'job',forbid);monkeypatch.setattr(service_module,'compressed_read',bounded_reader)
 class Blob:
  def __init__(self,blob,state):self.blob=blob;self.state=state
  def read(self,n=-1):assert 0<n<=65536;chunks.append(n);return self.blob.read(n)
  def __enter__(self):return self
  def __exit__(self,*a):self.blob.close();self.state['blob']=False
  def __getattr__(self,key):return getattr(self.blob,key)
 class Connection:
  def __init__(self,db,state):self.db=db;self.state=state
  def blobopen(self,*a,**kw):
   self.state['blob']=True
   try:return Blob(self.db.blobopen(*a,**kw),self.state)
   except Exception:self.state['blob']=False;raise
  def __getattr__(self,key):return getattr(self.db,key)
 @contextmanager
 def restricted(*a,**kw):
  with original_db(*a,**kw) as db:
   state=dict(blob=False)
   def authorize(operation,table,column,*rest):
    if operation==sqlite3.SQLITE_READ and table=='jobs' and column=='payload' and not state['blob']:
     forbidden_reads.append((table,column));return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK
   db.set_authorizer(authorize);yield Connection(db,state)
 monkeypatch.setattr(lab.store,'db',restricted)
 for path in ['/report?part=2','/result-summary','/result-rows?limit=1&offset=2']:
  response=client.get('/api/jobs/'+jid+path);assert response.status_code==200,(path,response.text)
 assert chunks and max(chunks)<=65536 and forbidden_reads==[]

@pytest.mark.parametrize('kind',['input','root','part'])
def test_same_length_original_corruption_never_returns_certified_saved_values(saved,kind):
 client,lab,jid,original,reports=saved
 if kind=='input':
  with lab.store.db() as db:
   raw=db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()[0];value=json.loads(raw);value['seed']+=1;changed=canonical(value)
   assert len(changed.encode())==len(raw.encode());db.execute('UPDATE jobs SET payload=? WHERE id=?',(changed,jid))
 else:
  folder=lab.root/'data/jobs'/jid;path=folder/'result.json.gz' if kind=='root' else folder/'parts/000001.json.gz'
  raw=path.read_bytes();changed=bytearray(raw);changed[len(changed)//2]^=1;assert len(changed)==len(raw);path.write_bytes(changed)
 assert client.get('/api/jobs/'+jid+'/report?part=1').status_code==409
 if kind!='part':assert client.get('/api/jobs/'+jid+'/result-summary').status_code==409

def test_bad_view_is_visible_originals_survive_and_explicit_repair_changes_no_evidence(saved):
 client,lab,jid,original,reports=saved;folder=lab.root/'data/jobs'/jid
 files=[folder/'result.json.gz',*sorted((folder/'parts').glob('*.json.gz'))];before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
 events=[e for e in lab.store.events(jid) if e['kind']=='result_view_saved'];assert events,'New worker did not publish a saved-result view'
 path=folder/events[-1]['details']['filename'];raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
 response=client.get('/api/jobs/'+jid+'/result-summary');assert response.status_code==200
 assert response.json()['index_integrity'] is False and response.json()['requires_index'] is True and 'rows' not in response.json()
 assert client.get('/api/jobs/'+jid+'/result').json()==original
 repaired=client.post('/api/jobs/'+jid+'/result-view/repair');assert repaired.status_code==200,repaired.text
 assert repaired.json()['index_integrity'] is True and lab.result(jid)==original
 assert {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}==before

def test_missing_legacy_view_is_explicit_and_built_only_from_verified_originals(saved):
 client,lab,jid,original,reports=saved
 with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))
 response=client.get('/api/jobs/'+jid+'/result-summary');assert response.status_code==200
 assert response.json()['requires_index'] is True and response.json()['index_integrity'] is False and 'row_count' not in response.json()
 assert client.post('/api/jobs/'+jid+'/result-view/repair').status_code==200
 assert client.get('/api/jobs/'+jid+'/result-summary').json()['row_count']==3
 assert lab.result(jid)==original


def test_saved_diagnostic_pages_match_every_original_account_and_keep_nulls(saved):
 client,lab,jid,original,reports=saved
 for endpoint,key in [('statistics','search_statistics'),('screen','search_screen')]:
  accounts=[]
  for offset in range(3):
   response=client.get('/api/jobs/'+jid+'/result-'+endpoint,params=dict(limit=1,offset=offset));assert response.status_code==200,response.text
   value=response.json();assert value['pagination']==dict(limit=1,offset=offset,total=3)
   assert value['accounts_complete'] is False;accounts+=value['accounts']
  assert accounts==original[key]['accounts']
  complete=client.get('/api/jobs/'+jid+'/result-'+endpoint+'?limit=3').json()
  assert complete['accounts_complete'] is True and complete['accounts']==accounts
  assert client.get('/api/jobs/'+jid+'/result-'+endpoint+'?offset=99').json()['accounts']==[]

@pytest.mark.parametrize('target',['root','part'])
def test_missing_original_file_is_domain_conflict_without_certified_values(saved,target):
 client,lab,jid,original,reports=saved;folder=lab.root/'data/jobs'/jid
 path=folder/'result.json.gz' if target=='root' else folder/'parts/000001.json.gz';path.unlink()
 assert client.get('/api/jobs/'+jid+'/report?part=1').status_code==409
 if target=='root':assert client.get('/api/jobs/'+jid+'/result-summary').status_code==409

@pytest.mark.parametrize('header',[None,[],{},'invalid-json'])
def test_reanchored_malformed_derived_database_is_visible_and_repairable(saved,header):
 from backend.lab.result_index import file_hash
 client,lab,jid,original,reports=saved;event=next(e for e in reversed(lab.store.events(jid)) if e['kind']=='result_view_saved')['details'];path=lab.root/'data/jobs'/jid/event['filename']
 with sqlite3.connect(path) as db:
  db.execute('DELETE FROM header')
  if header is not None:db.execute('INSERT INTO header VALUES(?)',(header if header=='invalid-json' else canonical(header),))
 db.close()
 changed=file_hash(path);destination=path.with_name(changed+'.view.sqlite3');path.rename(destination)
 event.update(filename=destination.name,sha256=changed)
 with lab.store.db() as db:lab.store.event('result_view_saved',jid,event,db)
 response=client.get('/api/jobs/'+jid+'/result-summary');assert response.status_code==200,response.text
 assert response.json()['requires_index'] is True
 assert client.post('/api/jobs/'+jid+'/result-view/repair').status_code==200
 assert lab.result(jid)==original


def test_publication_cancel_and_fault_leave_originals_and_event_unchanged(saved,monkeypatch):
 from backend.lab import result_index as module
 client,lab,jid,original,reports=saved;folder=lab.root/'data/jobs'/jid;events=lab.store.events(jid);root=(folder/'result.json.gz').read_bytes()
 def forbidden_projection(row):raise AssertionError('Cancellation must stop before indexing the first row')
 with monkeypatch.context() as canceled:
  canceled.setattr(module,'row_projection',forbidden_projection)
  with pytest.raises(InterruptedError):lab.result_index.build(jid,original,lambda:True)
 assert lab.store.events(jid)==events and not list(folder.glob('.view-*.tmp'))
 def failure(*args):raise OSError('Owned publication fault')
 monkeypatch.setattr(module.os,'replace',failure)
 with pytest.raises(OSError,match='Owned publication'):lab.result_index.build(jid,original)
 assert lab.store.events(jid)==events and not list(folder.glob('.view-*.tmp'))
 assert (folder/'result.json.gz').read_bytes()==root and lab.result(jid)==original


def test_projection_omissions_and_invalid_public_calls_are_explicit(saved):
 from backend.lab.result_index import row_projection,summary_projection
 from backend.lab.store import StateError
 client,lab,jid,original,reports=saved
 row=row_projection(dict(part=0,config_id='A',report_sha256='B',configurations=[{'field':'x'*5000}]*200,**{'value'+str(i):'y'*3500 for i in range(20)}))
 assert row['configuration_count']==200 and row['is_portfolio'] is True and 'configurations' in row['omitted_fields'] and len(canonical(row).encode())<=16384
 meta=summary_projection(dict(job_id=jid,kind='search',rows=[],**{'value'+str(i):'y'*3500 for i in range(25)}),jid)
 assert meta['omitted_fields'] and len(canonical(meta).encode())<=49152
 for value in [None,{},dict(part=-1),dict(part=True)]:
  with pytest.raises(StateError):row_projection(value)
 for limit,offset in [(True,0),(0,0),(101,0),(1,-1),(1,True)]:
  with pytest.raises(StateError):lab.result_index.rows(jid,limit,offset)
  with pytest.raises(StateError):lab.result_index.auxiliary(jid,'screen',limit,offset)
 for kind in ['invalid','']:
  with pytest.raises(StateError):lab.result_index.auxiliary(jid,kind)
 for part,window in [(-1,'report'),(True,'report'),(0,'invalid'),(99,'report')]:
  with pytest.raises(StateError):lab.result_index.part(jid,part,window)
 for value in ['..','../outside','']:
  with pytest.raises(StateError):lab.result_index.folder(value)


@pytest.mark.parametrize('case',['missing_cache','bad_filename','wrong_root','metadata_hash','row_count','bad_sqlite','bad_event','missing_job','running_job','bad_input','root_identity','unknown_diagnostic','aux_cancel','changed_during_publish','empty_rows'])
def test_index_boundaries_and_recovery_preserve_original_authority(saved,case,monkeypatch):
 from backend.lab import result_index as module
 from backend.lab.store import StateError
 client,lab,jid,original,reports=saved;index=lab.result_index;folder=lab.root/'data/jobs'/jid
 event=next(e for e in reversed(lab.store.events(jid)) if e['kind']=='result_view_saved')['details']
 if case in ['bad_event','bad_input']:
  with lab.store.db() as db:
   if case=='bad_event':lab.store.event('result_saved',jid,[],db)
   else:db.execute('UPDATE jobs SET payload=? WHERE id=?',('[]',jid))
  with pytest.raises(StateError):index.build(jid,original)
 elif case=='root_identity':
  with pytest.raises(StateError):index.build(jid,original|dict(job_id='other'))
 elif case=='missing_job':
  with pytest.raises(StateError):index.summary('missing')
  with pytest.raises(StateError):index.build('missing',original)
 elif case=='running_job':
  with lab.store.db() as db:db.execute("UPDATE jobs SET status='running' WHERE id=?",(jid,))
  with pytest.raises(StateError):index.summary(jid)
 elif case=='unknown_diagnostic':
  changed=dict(original);changed.pop('search_screen');index.build(jid,changed)
  with pytest.raises(StateError):index.auxiliary(jid,'screen')
 elif case=='aux_cancel':
  calls=[]
  def cancel():calls.append(1);return len(calls)==2
  with pytest.raises(InterruptedError):index.build(jid,original,cancel)
  assert len(calls)==2 and not list(folder.glob('.view-*.tmp'))
 elif case=='changed_during_publish':
  replace=module.os.replace
  def mutate(*args):
   replace(*args)
   with lab.store.db() as db:db.execute("UPDATE jobs SET payload=payload||' ' WHERE id=?",(jid,))
  monkeypatch.setattr(module.os,'replace',mutate)
  with pytest.raises(StateError,match='changed during'):index.build(jid,original)
  assert not list(folder.glob('.view-*.tmp'))
 elif case=='empty_rows':
  empty=original|dict(rows=[]);empty.pop('search_statistics');empty.pop('search_screen');index.build(jid,empty)
  assert index.summary(jid)['row_count']==0 and index.rows(jid)['rows']==[]
 else:
  path=folder/event['filename']
  if case=='missing_cache':path.unlink()
  elif case=='bad_sqlite':
   path.write_bytes(b'owned invalid SQLite');digest=module.file_hash(path);destination=path.with_name(digest+'.view.sqlite3');path.rename(destination);event.update(filename=destination.name,sha256=digest)
  elif case=='bad_filename':event['filename']='../../outside'
  elif case=='wrong_root':event['root_sha256']='0'*64
  elif case=='metadata_hash':event['metadata_sha256']='0'*64
  elif case=='row_count':event['row_count']=999
  with lab.store.db() as db:lab.store.event('result_view_saved',jid,event,db)
  assert index.summary(jid)['requires_index'] is True
  assert lab.result(jid)==original


@pytest.mark.parametrize('content',[b'[]',b'{broken',b'{}'])
def test_verified_part_bytes_still_require_supported_original_container(saved,monkeypatch,content):
 from backend.lab import result_index as module
 from backend.lab.store import StateError
 client,lab,jid,original,reports=saved
 monkeypatch.setattr(module.gzip,'decompress',lambda raw:content)
 with pytest.raises(StateError):lab.result_index.part(jid,1)


def test_summary_keeps_complete_forty_group_funnel_with_bounded_metadata():
 from backend.lab.result_index import summary_projection
 groups=[dict(family='break_of_structure',timeframe=str(i),counts=dict(generated=1000,signal_qualified=800,enough_trades=600,profitable=300,sharpe_passed=50)) for i in range(40)]
 value=summary_projection(dict(kind='search',rows=[],search_screen=dict(accounts=[],groups=groups,oversized='x'*30000)),'owned')
 assert value['search_screen']['groups']==groups and value['search_screen']['omitted_fields']==['oversized']
 assert len(canonical(value).encode())<=65536
