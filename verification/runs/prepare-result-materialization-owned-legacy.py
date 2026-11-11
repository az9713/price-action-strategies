"""Prepare one actual owned legacy-view UI fixture; preserve all original input/result/part authority."""
from pathlib import Path
import hashlib,json,os,sqlite3,time,urllib.request
root=Path.cwd();base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=20) as response:return json.load(response)
def defaults(schema):return {key:value['default'] for key,value in schema['properties'].items() if 'default' in value}
session=get('/api/session');schema=get('/api/schema');body=dict(name='D043 owned legacy browser fixture',dataset_id='90f347229b2fb03ec112ee71',strategy=defaults(schema['strategy']),costs=defaults(schema['costs']),portfolio=defaults(schema['portfolio']),start='2022-01-03',end='2022-01-03',seed=42)
request=urllib.request.Request(base+'/api/experiments',data=json.dumps(body).encode(),headers={'Origin':base,'X-Lab-Token':session['token'],'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(request,timeout=30) as response:assert response.status==202;job=json.load(response)
jid=job['id'];deadline=time.monotonic()+120
while True:
 state=get('/api/jobs/'+jid)
 if state['status']=='completed':break
 assert state['status'] not in ['failed','canceled'] and time.monotonic()<deadline;time.sleep(.2)
path=root/'data/jobs'/jid/'result.json.gz';before=hashlib.sha256(path.read_bytes()).hexdigest()
with sqlite3.connect(root/'data/lab.sqlite3') as db:
 assert db.execute('SELECT COUNT(*) FROM events WHERE entity_id=? AND kind=?',(jid,'result_view_saved')).fetchone()[0]==1
 db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))
assert get('/api/jobs/'+jid+'/result-summary')['requires_index'] is True
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
value=dict(scope=__doc__,job_id=jid,root_sha256=before,derived_view_event_removed=1,original_authority_modified=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'owned-legacy-fixture.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
