"""Actual API/worker preflight of the frozen browser fixture; no profit threshold or selection tuning."""
from pathlib import Path
import json,os,sys,time,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.models import Search
base='http://127.0.0.1:8767';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def get(path):
 with urllib.request.urlopen(base+path,timeout=20) as r:return json.load(r)
health=get('/api/health');assert health['source_current'] and health['worker_ready']
fixture=json.loads((root/'verification/fixtures/search-statistics-browser-contract.json').read_text(encoding='utf-8'))
manifest=get('/api/datasets/'+fixture['dataset_id']);quality=manifest['quality']
request=Search(dataset_id=fixture['dataset_id'],name='D038 frozen browser fixture independent API preflight',start=quality['start'],end=quality['end'],count=fixture['count'],seed=fixture['seed'],families=fixture['families'],timeframes=fixture['timeframes'],statistics=fixture['statistics']).model_dump(mode='json')
token=get('/api/session')['token'];message=urllib.request.Request(base+'/api/searches',data=json.dumps(request).encode(),headers={'Content-Type':'application/json','Origin':base,'X-Lab-Token':token},method='POST')
with urllib.request.urlopen(message,timeout=20) as r:assert r.status==202;job=json.load(r)
(out/'queued-job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
deadline=time.monotonic()+360
while True:
 state=get('/api/jobs/'+job['id'])
 if state['status'] in ['completed','failed','canceled']:break
 assert time.monotonic()<deadline,'Actual preflight exceeded frozen functional timeout'
 time.sleep(.5)
assert state['status']=='completed',state.get('error')
saved=get('/api/jobs/'+job['id']+'/result');assert saved['search_statistics']['settings']==fixture['statistics']
trades=sum(r['metrics']['trades'] for r in saved['rows']);defined=sum(v['score'] is not None for a in saved['search_statistics']['accounts'] for v in a['sensitivity'])
assert trades>0 and defined>0
(out/'saved-search.json').write_text(json.dumps(saved,indent=2),encoding='utf-8')
result=dict(job_id=job['id'],core_hash=health['core_hash'],raw_configurations=len(saved['rows']),trades=trades,defined_scores=defined,profits=[r['metrics']['net_profit'] for r in saved['rows']],scope=__doc__+' Same fixed seed/configuration cohort will be exercised through the UI; this is not another market replication or untouched test.')
(out/'preflight-observations.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
