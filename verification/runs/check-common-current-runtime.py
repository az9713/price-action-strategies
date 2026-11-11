"""Current managed main, source/assets, idle queue and actual same-store duplicate refusal."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
base='http://127.0.0.1:8767';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as r:return r.read()
before=json.loads(get('/api/health'));assert before['source_current'] and before['worker_alive'] and before['worker_ready'] and before['store_lease_held'] and before['core_hash']==current_core_hash()
assert not [(j['id'],j['status']) for j in json.loads(get('/api/jobs')) if j['status'] in ['running','queued','canceling']]
duplicate=subprocess.run([sys.executable,'-m','uvicorn','backend.lab.api:create_app','--factory','--host','127.0.0.1','--port','8771','--no-access-log'],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
assert duplicate.returncode==3 and 'Another application instance already owns this store' in duplicate.stderr
(out/'duplicate-start-stdout.log').write_text(duplicate.stdout,encoding='utf-8');(out/'duplicate-start-stderr.log').write_text(duplicate.stderr,encoding='utf-8')
after=json.loads(get('/api/health'));assert all(before[k]==after[k] for k in ['server_pid','worker_pid','core_hash']) and after['worker_ready'] and after['store_lease_held']
assets=[]
for p in sorted((root/'frontend/dist').rglob('*')):
 if p.is_file():
  relative=p.relative_to(root/'frontend/dist').as_posix();raw=p.read_bytes();assert get('/' if relative=='index.html' else '/'+relative)==raw
  assets.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
value=dict(scope=__doc__,managed_session=35409,health=after,duplicate_exit_code=duplicate.returncode,served_assets=assets,
            stop_observation='verification/runs/common-sampling-complete-assumptions-managed-restart-observation.json',limitations='No OS-wide listener inventory certificate. Native TCP inventory previously omitted a known responding main endpoint; this check establishes HTTP owner identities, store lease, duplicate refusal and exact served assets.')
(out/'runtime-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
