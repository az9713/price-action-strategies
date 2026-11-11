"""Same complete source reads and hashes, with direct directory-entry paths.

No stat cache, digest cache, skipped checks, financial work or production edit.
"""
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
folders=sorted((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns,reverse=True)
folder=folders[0]
assert folder.resolve().is_relative_to((root/'data/dev027/funnel-browser').resolve())
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone()
assert row is not None
lab=Lab(folder)
original=research.current_core_subject

def direct_subject():
    folder=Path(research.__file__).resolve().parent
    project=folder.parents[1]
    prefix=folder.relative_to(project).as_posix()+'/'
    files={}
    with os.scandir(folder) as entries:
        for entry in entries:
            if entry.name.lower().endswith('.py'):
                with open(entry.path,'rb') as source:
                    files[prefix+entry.name]=hashlib.sha256(source.read()).hexdigest()
    for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock']:
        with open(project/name,'rb') as source:
            files[name]=hashlib.sha256(source.read()).hexdigest()
    return dict(source_files=files,runtime=research._RUNTIME.copy())

def counts():
    with lab.store.db() as db:
        return {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}

assert direct_subject()==original()
before=counts();measurements=[]
for mode in ['original','direct_paths','direct_paths','original','direct_paths','original']:
    function=original if mode=='original' else direct_subject
    counter={'full_source_checks':0}
    def measured():
        counter['full_source_checks']+=1
        return function()
    wall=time.perf_counter();cpu=time.process_time()
    with patch.object(research,'current_core_subject',measured):
        value=final_summary(lab,row[0])
    measurements.append(dict(mode=mode,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
        summary_sha256=identity(value),**counter))
assert len({r['summary_sha256'] for r in measurements})==1
assert len({r['full_source_checks'] for r in measurements})==1
assert before==counts() and direct_subject()==original()
from statistics import median
result=dict(scope=__doc__,measurements=measurements,
    median_wall_seconds={m:median(r['wall_seconds'] for r in measurements if r['mode']==m) for m in ['original','direct_paths']},
    median_cpu_seconds={m:median(r['cpu_seconds'] for r in measurements if r['mode']==m) for m in ['original','direct_paths']},
    exact_complete_subject_equal=True,original_state_unchanged=True,production_unchanged=True)
(out/'full-fingerprint-paths-prototype.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
