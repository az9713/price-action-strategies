"""Actual new-job counterexample for aggregate instrument/synthetic context, before implementation."""
from pathlib import Path
from io import StringIO
import csv,json,os,sys,time,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.models import Search
base='http://127.0.0.1:8767';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
contract=json.loads((root/'verification/runs/aggregate-provenance-contract-v1.json').read_text(encoding='utf-8'))
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as response:return response.read()
original=json.loads(get('/api/jobs/'+contract['source_request_job']))['payload']
audit=json.loads(get('/api/datasets/'+original['dataset_id']+'/audit'))
assert audit['metadata']['input_kind']=='synthetic' and audit['quality']['eligible']
expected=dict(dataset_id=audit['id'],dataset_manifest_hash=audit['manifest_sha256'],input_kind='synthetic',source=audit['metadata'].get('provider',audit['metadata'].get('source','Imported')),symbols=audit['quality']['symbols'])
request={k:original[k] for k in ['dataset_id','start','end','strategy','costs','portfolio','seed']}
request.update(name='Authored aggregate provenance synthetic control',count=1,families=['break_of_structure'],timeframes=['1m'],statistics=dict(effective_trials=[1],dispersion_mode='empirical'),sampling_policy=dict(mode='common_random'))
request=Search(**request).model_dump(mode='json')
(out/'frozen-request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
token=json.loads(get('/api/session'))['token']
call=urllib.request.Request(base+'/api/searches',data=json.dumps(request).encode(),headers={'Content-Type':'application/json','Origin':base,'X-Lab-Token':token},method='POST')
with urllib.request.urlopen(call,timeout=30) as response:job=json.load(response)
jid=job['id'];deadline=time.monotonic()+120
while time.monotonic()<deadline:
 job=json.loads(get('/api/jobs/'+jid))
 if job['status'] in {'completed','failed','canceled'}:break
 time.sleep(.2)
assert job['status']=='completed',dict(job_id=jid,status=job['status'])
saved=json.loads(get('/api/jobs/'+jid+'/result'));deck=json.loads(get('/api/jobs/'+jid+'/export/presentation.json'))
columns=next(csv.reader(StringIO(get('/api/jobs/'+jid+'/search-screen/export/csv').decode())))
facts={tuple(f['path']):f['raw_value'] for f in deck['facts'].values()} if deck['facts'] and all('raw_value' in f for f in deck['facts'].values()) else {tuple(f['path']):f for f in deck['facts'].values()}
missing=[]
for name,document in [('payload',job['payload']),('saved',saved)]:
 context=document.get('dataset_context',{})
 for key,wanted in expected.items():
  if context.get(key)!=wanted:missing.append(name+'.dataset_context.'+key)
for column in contract['required_csv_columns']:
 if column not in columns:missing.append('csv.'+column)
for key in ['input_kind','source','symbols','dataset_manifest_hash']:
 if ('dataset_context',key) not in facts:missing.append('offline.dataset_context.'+key)
value=dict(scope=__doc__,job_id=jid,dataset_id=audit['id'],core_hash=saved['core_hash'],expected_dataset_context=expected,accounts=len(saved['rows']),missing=missing,financial_selection_criteria=False,final_data_access=False)
(out/'aggregate-provenance-first-contract.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2));assert not missing,'Aggregate provenance contract is not implemented; do not certify it.'
