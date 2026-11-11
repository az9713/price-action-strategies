"""Current managed owner/assets and duplicate-store refusal; no native PID inventory claim."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=15) as response:return response.read()
health=json.loads(get('/api/health'));assert health['server_pid']==40760 and health['source_current'] and health['worker_ready'] and health['worker_alive'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
assert not [j for j in json.loads(get('/api/jobs')) if j['status'] in ['queued','running','canceling']]
import sqlite3
with sqlite3.connect('file:'+(root/'data/lab.sqlite3').as_posix()+'?mode=ro',uri=True) as db:
 total,pending=db.execute("SELECT COUNT(*),COALESCE(SUM(status IN ('queued','running','canceling')),0) FROM jobs").fetchone();assert pending==0
duplicate=subprocess.run([sys.executable,'-m','uvicorn','backend.lab.api:create_app','--factory','--host','127.0.0.1','--port','8771','--no-access-log'],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
assert duplicate.returncode==3 and 'Another application instance already owns this store' in duplicate.stderr
for suffix,content in [('stdout',duplicate.stdout),('stderr',duplicate.stderr)]:
 (out/('duplicate-'+suffix+'.log')).write_text(content.replace(str(root),'<workspace>').replace(str(Path.home()),'<user-home>'),encoding='utf-8')
after=json.loads(get('/api/health'));assert all(health[k]==after[k] for k in ['server_pid','worker_pid','core_hash']) and after['worker_ready']
assets=[]
for p in sorted((root/'frontend/dist').rglob('*')):
 if p.is_file():
  name=p.relative_to(root/'frontend/dist').as_posix();assert get('/' if name=='index.html' else '/'+name)==p.read_bytes()
  assets.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
value=dict(scope=__doc__,managed_session=60178,health=after,duplicate_exit_code=3,assets=assets,database_jobs_observed=total,pending_jobs=0,native_process_absence_certified=False)
(out/'managed-runtime.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
