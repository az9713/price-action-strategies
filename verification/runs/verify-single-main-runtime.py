"""Actual main runtime, store-lease duplicate refusal and retired-instance closure."""
from pathlib import Path
import hashlib,json,os,socket,subprocess,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.research import current_core_hash
from verification.record_check import redact
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);base='http://127.0.0.1:8767'
def health():
 with urllib.request.urlopen(base+'/api/health',timeout=10) as response:return json.load(response)
def listening(port):
 try:
  with socket.create_connection(('127.0.0.1',port),timeout=2):return True
 except OSError:return False
before=health();assert before['source_current'] and before['worker_alive'] and before['worker_ready'] and before['store_lease_held'] and before['core_hash']==current_core_hash()
assert not any(listening(p) for p in [8768,8769,8770,8771])
argv=[sys.executable,'-m','uvicorn','backend.lab.api:create_app','--factory','--host','127.0.0.1','--port','8771','--no-access-log']
process=subprocess.Popen(argv,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
try:stdout,stderr=process.communicate(timeout=30)
except subprocess.TimeoutExpired:
 # This exact child process was started by this verifier and is still live.
 # Retire its complete Windows launcher tree; never select arbitrary Python PIDs.
 subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=True)
 process.communicate(timeout=10);raise AssertionError('Duplicate server unexpectedly remained running')
(out/'duplicate-stdout.log').write_text(redact(stdout),encoding='utf-8');(out/'duplicate-stderr.log').write_text(redact(stderr),encoding='utf-8')
assert process.returncode!=0 and 'already owns this store' in stderr,(process.returncode,stderr)
after=health();assert all(before[k]==after[k] for k in ['server_pid','worker_pid','core_hash']) and after['source_current'] and after['worker_ready'] and after['store_lease_held']
assert not any(listening(p) for p in [8768,8769,8770,8771])
with urllib.request.urlopen(base+'/',timeout=10) as response:assert response.read()==(root/'frontend/dist/index.html').read_bytes()
assets=[]
for p in (root/'frontend/dist/assets').iterdir():
 if p.suffix in {'.js','.css'}:
  with urllib.request.urlopen(base+'/assets/'+p.name,timeout=10) as response:raw=response.read()
  assert raw==p.read_bytes();assets.append(dict(path=p.name,sha256=hashlib.sha256(raw).hexdigest()))
result=dict(scope=__doc__+' Not final acceptance or provider authentication.',base_url=base,health=after,duplicate_process_exit_code=process.returncode,duplicate_store_refused=True,original_server_and_worker_unchanged=True,retired_ports_closed=[8768,8769,8770,8771],served_assets=assets)
(out/'single-main-runtime.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
