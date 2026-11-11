"""Actual owned-main managed-stop postconditions; never terminates a PID."""
from pathlib import Path
import json,os,socket,subprocess,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
from backend.lab.service import Lab
from backend.lab.runtime import StoreLease
from verification.record_check import redact
lab=Lab(root)
with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
mode=sys.argv[1]
def rows(ids):
 command='Get-CimInstance Win32_Process -Filter "'+ ' OR '.join('ProcessId='+str(int(i)) for i in ids)+'" | Select-Object ProcessId,ParentProcessId,Name,CreationDate | ConvertTo-Json -Compress'
 run=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
 value=json.loads(run.stdout) if run.stdout.strip() else []
 return value if isinstance(value,list) else [value]
if mode=='before':
 with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as response:health=json.load(response)
 assert health['source_current'] and health['worker_ready'] and health['store_lease_held']
 found=rows([health['server_pid'],health['worker_pid']]);server=next(p for p in found if p['ProcessId']==health['server_pid'])
 found+=rows([server['ParentProcessId']]);assert len({p['ProcessId'] for p in found})==3
 value=dict(scope=__doc__,phase=mode,health=health,owned_objects=found,pending_jobs=0)
else:
 snapshot=json.loads((root/sys.argv[2]).read_text(encoding='utf-8'));original={p['ProcessId']:p['CreationDate'] for p in snapshot['owned_objects']}
 current=rows(original);assert not any(p['ProcessId'] in original and p['CreationDate']==original[p['ProcessId']] for p in current)
 try:
  with socket.create_connection(('127.0.0.1',8767),timeout=2):raise AssertionError('Main port still listening')
 except OSError:pass
 with StoreLease(root):lease_reacquired=True
 value=dict(scope=__doc__,phase=mode,original_process_objects_exited=True,closed_port=8767,os_lease_reacquired=lease_reacquired,persistent_lock_file_is_not_live_ownership=True,pending_jobs=0)
(out/('managed-main-'+mode+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
