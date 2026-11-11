"""Repeat complete saved reads with static source checks at readonly boundaries.

Prototype only: all original account, input, trial, checkpoint, event, final
consumption, candidate and closing-data checks remain. No result caching.
"""
from contextlib import closing
from pathlib import Path
from statistics import median
from unittest.mock import patch
import json,os,sqlite3,sys,time

root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
from backend.lab import research
from backend.lab.service import Lab
from backend.lab.research_funnel_final import final_summary
from backend.lab.config import identity
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
folder=sorted((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns,reverse=True)[0]
assert folder.resolve().is_relative_to((root/'data/dev027/funnel-browser').resolve())
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone()
assert row is not None
lab=Lab(folder);physical=research.current_core_hash
def counts():
    with lab.store.db() as db:
        return {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}
before=counts();measurements=[]
for mode in ['all_nested_checks','entry_and_exit','entry_and_exit','all_nested_checks','entry_and_exit','all_nested_checks']:
    counter={'physical_source_checks':0,'nested_requests':0}
    def checked():
        counter['physical_source_checks']+=1
        return physical()
    def deferred():
        counter['nested_requests']+=1
        return expected
    wall=time.perf_counter();cpu=time.process_time()
    if mode=='all_nested_checks':
        with patch.object(research,'current_core_hash',checked):value=final_summary(lab,row[0])
    else:
        expected=checked();assert expected==research.core_hash()
        with patch.object(research,'current_core_hash',deferred):value=final_summary(lab,row[0])
        assert checked()==expected
    measurements.append(dict(mode=mode,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
        summary_sha256=identity(value),**counter))
assert len({r['summary_sha256'] for r in measurements})==1
assert before==counts() and physical()==research.core_hash()
result=dict(scope=__doc__,measurements=measurements,
    median_wall_seconds={m:median(r['wall_seconds'] for r in measurements if r['mode']==m) for m in ['all_nested_checks','entry_and_exit']},
    median_cpu_seconds={m:median(r['cpu_seconds'] for r in measurements if r['mode']==m) for m in ['all_nested_checks','entry_and_exit']},
    original_state_unchanged=True,production_boundary_grouping_implemented=False)
(out/'saved-read-boundary-check-prototype.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
