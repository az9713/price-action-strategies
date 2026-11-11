"""Current single managed main, source/asset parity and actual duplicate-start refusal."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=10) as r:return r.read()
before=json.loads(get('/api/health'));assert before['source_current'] and before['worker_ready'] and before['worker_alive'] and before['store_lease_held'] and before['core_hash']==current_core_hash()
jobs=json.loads(get('/api/jobs'));assert not [j for j in jobs if j['status'] in ['queued','running','canceling']]
script="Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object LocalPort -in 8767,8768,8769,8770,8771 | Select-Object LocalPort,OwningProcess | ConvertTo-Json -Compress"
p=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0
ports=json.loads(p.stdout);ports=[ports] if isinstance(ports,dict) else ports
assert ports==[dict(LocalPort=8767,OwningProcess=before['server_pid'])],ports
duplicate=subprocess.run([sys.executable,'-m','uvicorn','backend.lab.api:create_app','--factory','--host','127.0.0.1','--port','8771','--no-access-log'],cwd=root,capture_output=True,text=True,encoding='utf-8',timeout=30)
assert duplicate.returncode==3 and 'Another application instance already owns this store' in duplicate.stderr
(out/'duplicate-start-stdout.log').write_text(duplicate.stdout,encoding='utf-8');(out/'duplicate-start-stderr.log').write_text(duplicate.stderr,encoding='utf-8')
after=json.loads(get('/api/health'));assert all(after[k]==before[k] for k in ['server_pid','worker_pid','core_hash']) and after['worker_ready'] and after['store_lease_held']
files=[]
for path in sorted((root/'frontend/dist').rglob('*')):
 if path.is_file():
  relative=path.relative_to(root/'frontend/dist').as_posix();url='/' if relative=='index.html' else '/'+relative;raw=path.read_bytes();assert get(url)==raw
  files.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
value=dict(scope=__doc__,managed_session_id=82583,health=after,listeners=ports,duplicate_exit_code=duplicate.returncode,served_assets=files,
 old_session_stop=dict(session_id=62773,tool_exit_code=1,server_reported_shutdown_complete=True,old_pids_observed_absent=[32620,34232,49400]),
 verifier_corrections='Two unrecorded post-stop diagnostic commands incorrectly assumed optional psutil and nonexistent StoreLease.acquire/release methods. Neither passed; no positive lease-reacquisition check is claimed from them. Native process/listener checks observed the old tree gone, and the newly started server acquired the lease normally.',
 process_explanation='A managed instance normally has a virtual-environment launcher, HTTP process and spawned numerical worker. Obsolete verification servers previously remained alive; exceptional lifespan cleanup could leak a worker before D037. Historical fourth-child types were not recorded. No user taskkill is required for managed restarts.')
(out/'runtime-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
