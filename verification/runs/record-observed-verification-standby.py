"""Record observed machine standby separately from pytest wall-clock duration."""
from datetime import datetime,timezone
from pathlib import Path
import json,os,subprocess
root=Path.cwd();rid='20261110T155951599290Z-manifest-proof-portable-current-part-and-live-control-regression'
receipt=json.loads((root/'verification/receipts'/(rid+'.json')).read_text(encoding='utf-8'))
command="Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=[datetime]'2026-11-10T07:50:00'; EndTime=[datetime]'2026-11-10T10:00:00'; Id=506,507} -ErrorAction Stop | Where-Object { $_.ProviderName -eq 'Microsoft-Windows-Kernel-Power' } | ForEach-Object { [pscustomobject]@{created_utc=$_.TimeCreated.ToUniversalTime().ToString('o');id=$_.Id;description=(($_.Message -split '[\\r\\n]+')[0])} } | ConvertTo-Json -Compress"
result=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True,timeout=30)
assert result.returncode==0,result.stderr
events=json.loads(result.stdout);events.sort(key=lambda e:e['created_utc'])
def parsed(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
started=parsed(receipt['started_at_utc']);finished=parsed(receipt['finished_at_utc'])
entered=None;intervals=[]
for event in events:
    at=parsed(event['created_utc'])
    if event['id']==506:entered=at
    elif event['id']==507 and entered is not None:
        lo=max(entered,started);hi=min(at,finished)
        if hi>lo:intervals.append(dict(start=lo.isoformat(),end=hi.isoformat(),seconds=(hi-lo).total_seconds()))
        entered=None
standby=sum(i['seconds'] for i in intervals)
value=dict(scope=__doc__,original_passing_receipt=rid,events=events,observed_standby_intervals=intervals,
    observed_standby_seconds_overlapping_run=standby,recorded_command_wall_seconds=(finished-started).total_seconds(),
    wall_less_observed_standby_seconds=(finished-started).total_seconds()-standby,
    cpu_time_measured=False,human_active_work_measured=False,all60_original_tests_passed=True,
    caution='Observed awake wall time is neither CPU time nor complete-project active work. Original receipt durations remain unchanged.')
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'observed-verification-standby.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'events','observed_standby_intervals'}},indent=2))
