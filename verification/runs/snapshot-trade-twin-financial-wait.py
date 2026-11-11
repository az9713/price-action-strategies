"""Record an actual live full-check handle and unchanged staged source; no pass claim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
identifier='20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage'
receipt_path=root/'verification/receipts'/(identifier+'.json')
expected=json.loads((root/'verification/runs/20261109T200841194002Z-trade-twins-financial-complete-books-corrected-opening-mark-hand-total-and-exact-30-module-gate-declaration/dev026-source-subject.json').read_text())
current={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
assert current==expected['source_files'] and len(current)==220
script="$p=Get-CimInstance Win32_Process -Filter 'ProcessId = 28880'; if($p){[ordered]@{pid=$p.ProcessId;created_at_utc=$p.CreationDate.ToUniversalTime().ToString('o');matches_expected_pytest_command=($p.CommandLine -like '*-m pytest*tests --cov=backend.lab*')}|ConvertTo-Json -Compress}"
observed=subprocess.run(['pwsh','-NoProfile','-Command',script],capture_output=True,text=True,check=True)
process=json.loads(observed.stdout) if observed.stdout.strip() else None
if receipt_path.exists():
 terminal=json.loads(receipt_path.read_text());state='terminal';exit_code=terminal['command']['exit_code']
else:
 assert process and process['pid']==28880 and process['matches_expected_pytest_command']
 assert process['created_at_utc'].startswith('2026-11-09T20:10:09')
 state='verified_live_wait';exit_code=None
value=dict(scope=__doc__,observed_at_utc=datetime.now(timezone.utc).isoformat(),full_check=dict(receipt=identifier,exec_session_id=24038,state=state,exit_code=exit_code,original_live_process=process),
 staged_source_files=current,staged_source_unchanged=True,final_acceptance_certified=False,
 next_actions=['Poll the same original full-check session; do not restart on an observation timeout.','After actual terminal success run check-current-trade-twins-full-gate.py against its original receipt and actual private coverage DB.','Run checkpoint-trade-twins-financial.py with original full and gate receipt IDs, then actual restore-trade-twins-financial.py.','Inspect managed0.25 runtime and owned-process retirement after no test processes remain.','Then install verified feature/exact-money prototypes; fix original source closed-profit summation; finish durable child/parts/trials/failures/recovery/API/UI/exports and actual product10000-set workloads.','Retain era/replication/stability/ensembles/100000 stress and every original83/422/120 final acceptance obligation.'])
(out/'verified-financial-stage-wait.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
(root/'verification/runs/trade-twins-current-work-state.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='staged_source_files'},indent=2))
