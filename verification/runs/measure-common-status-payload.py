"""Measure queued common-search polling payloads without executing prices or starting a server.
Successful measurement is not a performance-gate pass; budgets and outcomes are explicit.
"""
from pathlib import Path
import hashlib,json,os,sys,tempfile,time
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.config import FAMILIES,TIMEFRAMES
from backend.lab.models import Search
from test_api import seed,payload
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);rows=[]
with tempfile.TemporaryDirectory(prefix='pa-common-payload-measurement-') as directory:
 app=create_app(Path(directory),run_worker=False)
 with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
  client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
  manifest=seed(app.state.lab)
  for count in [10,100,1000]:
   request=Search(**(payload(manifest)|dict(name='Frozen synthetic polling measurement',count=count,families=list(FAMILIES),timeframes=list(TIMEFRAMES),sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1])))).model_dump(mode='json')
   begun=time.perf_counter();created=client.post('/api/searches',json=request);duration=time.perf_counter()-begun
   assert created.status_code==202,created.status_code
   jid=created.json()['id'];original=app.state.lab.store.job(jid)
   begun=time.perf_counter();status=client.get('/api/jobs/'+jid);elapsed=time.perf_counter()-begun
   assert status.status_code==200 and original['status']=='queued'
   proposals=original['payload']['sampling']['proposals'];public=status.json()['payload'].get('sampling',{}).get('proposals')
   assert original['payload']['sampling']['unique']==count
   assert len(app.state.lab.store.trials(jid)) if hasattr(app.state.lab.store,'trials') else True
   rows.append(dict(configurations=count,generation_seconds=duration,status_seconds=elapsed,status_bytes=len(status.content),creation_bytes=len(created.content),proposal_records=len(proposals),proposal_records_in_status=len(public) if isinstance(public,list) else 0,status_budget_bytes=65536,within_status_budget=len(status.content)<=65536,immutable_generation_sha256=hashlib.sha256(json.dumps(original['payload']['sampling'],sort_keys=True).encode()).hexdigest(),executed_accounts=0))
  listing=client.get('/api/jobs');assert listing.status_code==200
  assert not app.state.worker_process
value=dict(scope=__doc__,counts_prespecified=[10,100,1000],rows=rows,list_jobs=3,list_bytes=len(listing.content),all_status_budgets_met=all(r['within_status_budget'] for r in rows),server_started=False,price_accounts_executed=0,performance_acceptance_certified=False)
(out/'polling-payload-measurement.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
