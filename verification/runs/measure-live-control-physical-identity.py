"""Old/new fresh live-control polling; no numerical work or outcome reuse."""
from pathlib import Path
from statistics import median
import importlib.util,json,os,sys,time,uuid
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab import store as current
spec=importlib.util.spec_from_file_location('backend.lab._original_live_store',Path(__file__).with_name('store-before-control-identity-optimization.py'))
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
folder=root/'data/dev027/control-identity-bench'/uuid.uuid4().hex
store=current.Store(folder);job=store.create_job('experiment',dict(name='Authored live control polling benchmark'));store.claim('bench-owner')
old=original.Store(folder)
def counts():
    with store.db() as db:return {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}
before=counts();measurements=[]
for mode in ['original','physical_identity','physical_identity','original']:
    instance=old if mode=='original' else store;module=original if mode=='original' else current
    query_count=[0]
    def observed(sql):
        if sql.startswith('SELECT status,owner,cancel_requested FROM jobs'):query_count[0]+=1
    wall=time.perf_counter();cpu=time.process_time()
    with instance.control_reads():
        module._control_reader.get()[2].set_trace_callback(observed)
        for _ in range(30000):assert instance.cancellation_requested(job['id'],'bench-owner') is False
    measurements.append(dict(mode=mode,polls=30000,fresh_sql_queries=query_count[0],wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu))
    assert query_count[0]==30000
assert before==counts()
value=dict(scope=__doc__,authored_store=folder.relative_to(root).as_posix(),measurements=measurements,
    actual_control_polls=120000,actual_fresh_sql_queries=120000,original_store_counts_unchanged=True,
    median_wall_seconds={m:median(r['wall_seconds'] for r in measurements if r['mode']==m) for m in ['original','physical_identity']},
    median_cpu_seconds={m:median(r['cpu_seconds'] for r in measurements if r['mode']==m) for m in ['original','physical_identity']},
    numerical_or_market_capacity_certified=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'live-control-physical-identity-measurement.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
