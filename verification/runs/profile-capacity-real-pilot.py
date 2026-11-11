"""Instrumented repeated100-account pilot for identifying costs; do not treat profiled timings as a throughput certificate."""
from pathlib import Path
import cProfile,json,os,pstats,runpy,sys,time
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);profiler=cProfile.Profile();started=time.perf_counter();sys.argv=['verification/runs/measure-capacity-real-sample-current.py','100']
try:
 profiler.enable();runpy.run_path(sys.argv[0],run_name='__main__')
finally:profiler.disable()
statistics=pstats.Stats(profiler);rows=[]
for (file,line,name),(primitive,calls,self_seconds,cumulative,callers) in statistics.stats.items():
 try:location=Path(file).resolve().relative_to(root).as_posix()
 except (ValueError,OSError):location='<runtime>/'+Path(file).name
 rows.append(dict(file=location,line=line,function=name,primitive_calls=primitive,calls=calls,self_seconds=self_seconds,cumulative_seconds=cumulative))
value=dict(scope=__doc__,instrumented=True,wall_seconds=time.perf_counter()-started,top_cumulative=sorted(rows,key=lambda row:row['cumulative_seconds'],reverse=True)[:100],top_self=sorted(rows,key=lambda row:row['self_seconds'],reverse=True)[:50]);(out/'capacity-pilot-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(scope=__doc__,wall_seconds=value['wall_seconds'],top_application=[row for row in value['top_cumulative'] if row['file'].startswith('backend/')][:15]),indent=2))
