"""Read-only native current app tree plus live duplicate-store refusal; no PID killing."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,runpy,urllib.request
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def health():
 with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as r:return json.load(r)
before=health();assert before['worker_ready'] and before['store_lease_held'] and before['source_current']
# Command lines are used only inside the local read-only filter; never exported.
script=r'''$all=@(Get-CimInstance Win32_Process);$project=[IO.Path]::GetFullPath((Get-Location).Path);$matches=@($all | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.Contains($project)});$ids=@($matches | ForEach-Object {[int]$_.ProcessId});for($i=0;$i -lt 8;$i++){$more=@($all | Where-Object {$_.Name -eq 'python.exe' -and $_.ParentProcessId -in $ids} | ForEach-Object {[int]$_.ProcessId});$ids=@($ids+$more | Sort-Object -Unique)};@($all | Where-Object {$_.ProcessId -in $ids} | ForEach-Object {[pscustomobject]@{pid=[int]$_.ProcessId;parent_pid=[int]$_.ParentProcessId;name=$_.Name;creation_time_utc=$_.CreationDate.ToUniversalTime().ToString('o');project_uvicorn=[bool]($_.CommandLine -and $_.CommandLine.Contains($project) -and $_.CommandLine.Contains('-m uvicorn backend.lab.api:create_app'))}}) | ConvertTo-Json -Depth 3'''
p=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,timeout=30)
assert p.returncode==0 and not p.stderr,p.stderr
rows=json.loads(p.stdout);rows=rows if isinstance(rows,list) else [rows];inventory={r['pid']:r for r in rows}
# The recording Python process and this audit have their own venv launchers.
# Exclude only this positively identified ancestry/tree, not arbitrary processes.
audit_ids=set();pid=os.getpid()
while pid in inventory and pid not in audit_ids:
 audit_ids.add(pid);pid=inventory[pid]['parent_pid']
for _ in range(8):
 audit_ids.update(r['pid'] for r in rows if r['parent_pid'] in audit_ids)
excluded=[r for r in rows if r['pid'] in audit_ids]
rows=[r for r in rows if r['pid'] not in audit_ids];by_id={r['pid']:r for r in rows}
assert before['server_pid'] in by_id and before['worker_pid'] in by_id
assert by_id[before['worker_pid']]['parent_pid']==before['server_pid']
server=by_id[before['server_pid']];launcher=by_id.get(server['parent_pid'])
assert server['project_uvicorn'] and launcher and launcher['project_uvicorn']
assert len([r for r in rows if r['project_uvicorn']])==2
assert {r['pid'] for r in rows}=={server['pid'],launcher['pid'],before['worker_pid']},rows
runpy.run_path(str(root/'verification/runs/check-evaluation-cache-managed-runtime.py'),run_name='__main__')
after=health();assert all(before[k]==after[k] for k in ['server_pid','worker_pid','core_hash'])
value=dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),scope=__doc__,root_cause='Repeated obsolete verification servers survived updates. Windows venv launcher, HTTP interpreter and spawned numerical worker made each instance appear as multiple PIDs.',project_python_tree=rows,owned_audit_tree_excluded=excluded,server_pid=server['pid'],launcher_pid=launcher['pid'],worker_pid=before['worker_pid'],separate_obsolete_project_python_detected=False,kill_performed=False,why_no_kill='All observed project Python processes form the single healthy current tree.',duplicate_store_start_rejected=True,limitations='Point-in-time CIM inventory of project-path Python matches and descendants; inaccessible metadata or unrelated processes are not globally certified.')
(out/'current-process-tree.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
