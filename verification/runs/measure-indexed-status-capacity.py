"""Prespecified queued-plan metadata measurement; no price execution or throughput claim."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,os,sqlite3,sys,tempfile,time,tracemalloc
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.config import FAMILIES,TIMEFRAMES,identity
from test_api import seed,payload

out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);rows=[]
counts=[10,100,1000,100000]
with tempfile.TemporaryDirectory(prefix='pa-indexed-status-capacity-') as directory:
 app=create_app(Path(directory),run_worker=False)
 with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
  client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
  manifest=seed(app.state.lab);store=app.state.lab.store
  for count in counts:
   request=payload(manifest)|dict(name='Frozen synthetic polling measurement',count=count,families=list(FAMILIES),timeframes=list(TIMEFRAMES),sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1]))
   begun=time.perf_counter();created=client.post('/api/searches',json=request);generation=time.perf_counter()-begun
   assert created.status_code==202,created.text[:500]
   jid=created.json()['id'];original=store.job(jid)['payload']
   assert len(original['configurations'])==count and original['sampling']['unique']==count
   before_hash=identity(original);proposals=len(original['sampling']['proposals']);del original
   original_db=store.db;denied=[];sql_reads=[]
   @contextmanager
   def restricted(*a,**kw):
    with original_db(*a,**kw) as db:
     def authorize(operation,table,column,*rest):
      if operation==sqlite3.SQLITE_READ:
       sql_reads.append((table,column))
       if table=='jobs' and column=='payload':denied.append((table,column));return sqlite3.SQLITE_DENY
      return sqlite3.SQLITE_OK
     db.set_authorizer(authorize);yield db
   store.db=restricted
   try:
    tracemalloc.start();begun=time.perf_counter();status=client.get('/api/jobs/'+jid);elapsed=time.perf_counter()-begun
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert status.status_code==200,status.text[:500]
    assert status.json()['payload']['configuration_count']==count
    assert len(status.content)<=65536
    listing=client.get('/api/jobs');assert listing.status_code==200 and len(listing.content)<=2097152
    begun=time.perf_counter();canceled=client.post('/api/jobs/'+jid+'/cancel');cancel_seconds=time.perf_counter()-begun
    assert canceled.status_code==200 and canceled.json()['status']=='canceled'
    resumed=client.post('/api/jobs/'+jid+'/resume');assert resumed.status_code==200 and resumed.json()['status']=='queued'
    assert not denied
   finally:store.db=original_db
   assert identity(store.job_inputs(jid)['payload'])==before_hash
   totals=store.registry(1,0,jid)['totals'];assert totals['planned_occurrences']==count and totals['computation_attempts']==0
   rows.append(dict(configurations=count,generation_seconds=generation,status_seconds=elapsed,status_bytes=len(status.content),status_python_peak_bytes=peak,creation_bytes=len(created.content),proposal_records=proposals,list_bytes=len(listing.content),cancel_seconds=cancel_seconds,sql_raw_payload_reads=len(denied),sql_read_events=len(sql_reads),immutable_payload_sha256=before_hash,executed_accounts=0))
   (out/'indexed-status-capacity.json').write_text(json.dumps(dict(counts_prespecified=counts,rows=rows,complete=False),indent=2),encoding='utf-8')
   print(json.dumps(rows[-1]),flush=True)
  assert app.state.worker_process is None
value=dict(scope=__doc__,counts_prespecified=counts,rows=rows,complete=True,server_started=False,price_accounts_executed=0,numerical_capacity_certified=False)
(out/'indexed-status-capacity.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
