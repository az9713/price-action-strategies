"""Sequential original real100/repeat,1000,10000 checks; unchanged per-count budgets."""
from pathlib import Path
import json,subprocess,sys

root=Path.cwd()
origin='data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7/origin.json'
entries=[]
for count in [100,1000,10000]:
    command=[sys.executable,'verification/record_check.py','--label',f'main-retry-current-real-market-{count}-capacity',
        '--input','verification/runs/measure-fresh-market-capacity-current-stage.py',
        '--input','verification/runs/capacity-real-sample-contract.json',
        '--input','verification/runs/run-main-retry-real-capacity-series.py',
        '--input',origin,
        '--',sys.executable,'verification/runs/check-research-command-stage.py',
        sys.executable,'verification/runs/measure-fresh-market-capacity-current-stage.py',origin,str(count)]
    print(json.dumps(dict(starting_actual_count=count,wall_budget_seconds=900,retries=0)),flush=True)
    result=subprocess.run(command,cwd=root)
    entries.append(dict(count=count,exit_code=result.returncode))
    (root/'verification/runs/main-retry-capacity-series-state.json').write_text(json.dumps(dict(
        scope=__doc__,entries=entries,next_count=None if count==10000 or result.returncode else {100:1000,1000:10000}[count],
        final_capacity_certified=bool(count==10000 and result.returncode==0)),indent=2),encoding='utf-8')
    if result.returncode:raise SystemExit(result.returncode)
