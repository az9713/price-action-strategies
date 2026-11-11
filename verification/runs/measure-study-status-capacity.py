"""Prespecified ASGI HTTP study metadata/input measurements; no numerical accounts or network SLO claim."""
from contextlib import contextmanager
from pathlib import Path
import hashlib,json,os,sqlite3,sys,tempfile,time,tracemalloc
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
import pandas as pd
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.config import FAMILIES,TIMEFRAMES,Strategy
from backend.lab.models import Search
from backend.lab.sampling import sample_common
from backend.lab.research import ResearchError
from backend.lab.data import save_dataset
from conftest import minute_frame
from test_api import payload,study_payload

out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);counts=[10,1000,100000];rows=[]
def original_digest(spec):
 excluded={'screening_report_hash','candidates','candidate_hash','final_job_id','reserved_final_job_id'}
 return hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k not in excluded},sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
with tempfile.TemporaryDirectory(prefix='pa-study-status-capacity-') as directory:
 app=create_app(Path(directory),run_worker=False)
 with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
  client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']});lab=app.state.lab
  for count in counts:
   symbol='S'+str(count);days=['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']
   frame=pd.concat([minute_frame(day,symbol=symbol) for day in days])
   manifest=save_dataset(lab.datasets_root,frame,{'input_kind':'synthetic','source':'Frozen metadata-only study capacity'},start=days[0],end=days[-1])
   request=Search(**(payload(manifest)|dict(count=count,families=list(FAMILIES),timeframes=list(TIMEFRAMES),sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1]))))
   begun=time.perf_counter();configurations,generation=sample_common(request);generation_seconds=time.perf_counter()-begun
   # Compact supported request fields fit the original65MiB body envelope.
   # The server freezes all resolved defaults; the exported original must equal every complete source config.
   compact=[Strategy(**c).model_dump(exclude_defaults=True) for c in configurations]
   body=study_payload(manifest)|dict(name='Metadata capacity '+str(count),configurations=compact)
   encoded=json.dumps(body,separators=(',',':'),allow_nan=False).encode();assert len(encoded)<=65*1024*1024
   begun=time.perf_counter();created=client.post('/api/studies',content=encoded,headers={'Content-Type':'application/json'});registration_seconds=time.perf_counter()-begun
   assert created.status_code==201,created.text[:500]
   sid=created.json()['id'];assert created.json()['spec']['configuration_count']==count and len(created.content)<=65536
   original_db=lab.store.db;raw_reads=[]
   @contextmanager
   def restricted(*a,**kw):
    with original_db(*a,**kw) as db:
     def authorize(operation,table,column,*rest):
      if operation==sqlite3.SQLITE_READ and table=='studies' and column=='spec':raw_reads.append((table,column));return sqlite3.SQLITE_DENY
      return sqlite3.SQLITE_OK
     db.set_authorizer(authorize);yield db
   lab.store.db=restricted
   try:
    tracemalloc.start();begun=time.perf_counter();status=client.get('/api/studies/'+sid);status_seconds=time.perf_counter()-begun
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();assert status.status_code==200 and len(status.content)<=65536
    listing=client.get('/api/studies');assert listing.status_code==200 and len(listing.content)<=2097152
    lab.guard.access([symbol],days[0],days[0],'metadata_scope_allowed')
    with lab.store.db() as db:before=db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]
    try:lab.guard.access([symbol],days[-1],days[-1],'metadata_scope_blocked')
    except ResearchError:pass
    else:raise AssertionError('Protected dates were exposed.')
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==before
    assert not raw_reads
   finally:lab.store.db=original_db
   begun=time.perf_counter();exported=client.get('/api/studies/'+sid+'/inputs');export_seconds=time.perf_counter()-begun
   assert exported.status_code==200;full=exported.json();spec=full['study']['spec']
   assert spec['configurations']==configurations and len(spec['configurations'])==count
   digest=original_digest(spec);assert digest==full['spec_hash']==created.json()['spec_hash']==status.json()['spec_hash']
   rows.append(dict(configurations=count,request_bytes=len(encoded),generation_seconds=generation_seconds,registration_seconds=registration_seconds,creation_bytes=len(created.content),status_bytes=len(status.content),status_seconds=status_seconds,status_python_peak_bytes=peak,list_bytes=len(listing.content),raw_study_spec_reads=len(raw_reads),input_export_bytes=len(exported.content),input_export_seconds=export_seconds,spec_hash=digest,fully_resolved_configs_equal=True,protected_read_blocked_before_viewed_write=True,price_accounts_executed=0))
   (out/'study-status-capacity.json').write_text(json.dumps(dict(counts_prespecified=counts,rows=rows,complete=False),indent=2),encoding='utf-8');print(json.dumps(rows[-1]),flush=True)
   del full,spec,configurations,compact,encoded,body,exported,generation
  with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==db.execute('SELECT COUNT(*) FROM trial_plans').fetchone()[0]==0
  assert app.state.worker_process is None
value=dict(scope=__doc__,counts_prespecified=counts,rows=rows,complete=True,numerical_capacity_certified=False,server_started=False,price_accounts_executed=0)
(out/'study-status-capacity.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
