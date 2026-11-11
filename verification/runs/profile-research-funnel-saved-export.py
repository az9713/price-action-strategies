"""Read-only profile of a completed authored browser study, not a capacity claim."""
from contextlib import closing
from pathlib import Path
import cProfile,json,os,pstats,sqlite3,sys,time
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
from backend.lab.service import Lab
from backend.lab.research_funnel_exports import build_export
from backend.lab.research import core_hash
candidates=sorted((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns,reverse=True)
folder=candidates[0];assert folder.is_dir() and folder.resolve().is_relative_to((root/'data/dev027/funnel-browser').resolve())
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
 row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone()
 assert row is not None,'No completed authored final available for this profile.'
lab=Lab(folder)
def counts():
 with lab.store.db() as db:return {table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}
before=counts();profile=cProfile.Profile();started=time.perf_counter();built=profile.runcall(build_export,lab,row[0],'csv',table='accounts');elapsed=time.perf_counter()-started
size=built['path'].stat().st_size;built['path'].unlink();assert counts()==before
stats=pstats.Stats(profile);rows=[]
for (filename,line,name),(primitive,calls,internal,cumulative,callers) in stats.stats.items():rows.append(dict(file=Path(filename).name,line=line,function=name,calls=calls,primitive_calls=primitive,internal_seconds=internal,cumulative_seconds=cumulative))
rows.sort(key=lambda r:r['cumulative_seconds'],reverse=True)
value=dict(scope=__doc__,core_hash=core_hash(),elapsed_seconds=elapsed,output_bytes=size,versions=2,final_account_rows=4,authoritative_state_unchanged=True,top_cumulative=rows[:35],all_function_records=rows)
(out/'saved-export-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='all_function_records'},indent=2))
