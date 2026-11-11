"""Measured read-only code-check grouping prototype; no production authority change."""
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,sqlite3,sys,time
root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
from backend.lab import research
from backend.lab.service import Lab
from backend.lab.research_funnel_final import final_summary
from backend.lab.config import identity
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
folders=sorted((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns,reverse=True);folder=folders[0]
assert folder.resolve().is_relative_to((root/'data/dev027/funnel-browser').resolve())
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone();assert row is not None
lab=Lab(folder)
def counts():
 with lab.store.db() as db:return {table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}
before=counts();physical=research.current_core_hash;results=[]
for mode in ['all_nested_checks','entry_and_exit_code_checks']:
    counter={'calls':0}
    def checked():counter['calls']+=1;return physical()
    started=time.perf_counter()
    if mode=='all_nested_checks':
        with patch.object(research,'current_core_hash',checked):value=final_summary(lab,row[0])
    else:
        expected=checked();assert expected==research.core_hash()
        with patch.object(research,'current_core_hash',lambda:expected):value=final_summary(lab,row[0])
        assert checked()==expected
    results.append(dict(mode=mode,elapsed_seconds=time.perf_counter()-started,physical_full_code_checks=counter['calls'],complete_summary_sha256=identity(value)))
assert results[0]['complete_summary_sha256']==results[1]['complete_summary_sha256']
assert counts()==before and physical()==research.core_hash()
value=dict(scope=__doc__,measurements=results,original_state_unchanged=True,financial_accounts_executed=0,production_grouping_not_yet_implemented=True,
           preserved_in_both_runs='All original account, root, input, trial, checkpoint, candidate and closing data checks; only repeated static-code fingerprint calculation was grouped.')
(out/'saved-read-code-check-grouping-prototype.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
