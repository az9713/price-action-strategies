"""Instrumented partial real-data run; diagnose writers, never certify capacity."""
from contextlib import contextmanager
from pathlib import Path
from threading import Event,Lock,Timer,current_thread
import itertools,json,os,sys,time
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.service import Lab
from backend.lab.models import Search
from backend.lab.research import core_hash
from verification_resources import current_resources
from backend.lab.worker import Worker

folder=root/'data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7'
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);lab=Lab(folder)
limit=64
with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
origin=json.loads((folder/'origin.json').read_text());contract=json.loads((root/'verification/runs/capacity-real-sample-contract.json').read_text())
job=lab.create_experiment(Search(dataset_id=origin['dataset_id'],name='Instrumented'+str(limit)+'-of10000 writer diagnostic',count=10000,
    seed=contract['seed'],families=contract['families'],timeframes=contract['timeframes'],**contract['evaluation']))
real_db=lab.store.db;records=[];guard=Lock();ids=itertools.count();started=time.perf_counter();cold=[]
verify_original=lab.store._trials._verify_original
def verify(*a,**k):
    cold.append(dict(at=time.perf_counter()-started,thread=current_thread().name,job_id=a[0]));return verify_original(*a,**k)
lab.store._trials._verify_original=verify
def tag(sql):
    text=sql.strip().lower()
    if text.startswith('update jobs'):return 'update_jobs_runtime'
    if text.startswith('select kind,payload'):return 'read_original_payload'
    if 'json_group_array' in text:return 'read_complete_original_trial_projection'
    return text.split(None,1)[0].upper() if text else 'empty'
class Observed:
    def __init__(self,db):self.db=db;self.number=next(ids);self.writer=None;self.last=None
    def __getattr__(self,name):return getattr(self.db,name)
    def execute(self,sql,*args):
        at=time.perf_counter();kind=tag(sql);location=sys._getframe(1)
        caller=dict(file=Path(location.f_code.co_filename).name,function=location.f_code.co_name,line=location.f_lineno)
        error=None
        try:return self.db.execute(sql,*args)
        except BaseException as exc:error=dict(type=type(exc).__name__,code=getattr(exc,'sqlite_errorcode',None));raise
        finally:
            end=time.perf_counter();elapsed=end-at;normalized=sql.strip().upper()
            if normalized=='BEGIN IMMEDIATE' and error is None:self.writer=end
            value=dict(connection=self.number,thread=current_thread().name,tag=kind,at_seconds=at-started,
                elapsed_seconds=elapsed,gap_since_last_sql_seconds=None if self.last is None else at-self.last,
                writer_held_seconds=None if self.writer is None else end-self.writer,caller=caller,error=error)
            self.last=end
            if elapsed>.01 or value['writer_held_seconds'] is not None or error is not None:
                with guard:records.append(value)
            if normalized in {'COMMIT','ROLLBACK'}:self.writer=None
@contextmanager
def observed_db(*a,**k):
    before=time.perf_counter()
    with real_db(*a,**k) as db:
        opened=time.perf_counter()
        with guard:records.append(dict(tag='connection_open',thread=current_thread().name,elapsed_seconds=opened-before,at_seconds=before-started))
        yield Observed(db)
lab.store.db=observed_db
stop=Event();worker=Worker(lab,stop);progress=worker._progress
def bounded(j,fraction,note,checkpoint=None):
    result=progress(j,fraction,note,checkpoint)
    (out/'writer-diagnostic-progress.json').write_text(json.dumps(dict(job_id=j['id'],checkpoint=checkpoint,
        elapsed_seconds=time.perf_counter()-started,resources=current_resources()),indent=2),encoding='utf-8')
    if checkpoint is not None and checkpoint>=limit:stop.set()
    return result
worker._progress=bounded
deadline=Timer(180,stop.set);deadline.daemon=True;deadline.start()
try:
    assert worker.run_once()
finally:
    deadline.cancel()
    lab.store.db=real_db;lab.store._trials._verify_original=verify_original
state=lab.store.job(job['id']);failure=worker.last_lease_failure
summary=dict(scope=__doc__,job_id=job['id'],core_hash=core_hash(),planned_configurations=10000,requested_diagnostic_checkpoint=limit,
    state=state['status'],checkpoint=state['checkpoint'],elapsed_seconds=time.perf_counter()-started,
    worker_guard=failure,cold_original_verifications=cold,resources=current_resources(),
    long_sql=sorted(records,key=lambda r:r.get('elapsed_seconds',0),reverse=True)[:30],
    longest_writer_phases=sorted([r for r in records if r.get('writer_held_seconds') is not None],key=lambda r:r['writer_held_seconds'],reverse=True)[:30],
    financial_capacity_certified=False,diagnostic_deadline_seconds=180)
(out/'owned-writer-diagnostic.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(out/'owned-writer-observations.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in {'long_sql','longest_writer_phases','cold_original_verifications'}},indent=2))
if state['status']=='queued':lab.store.cancel(job['id'])
assert state['status']=='queued' and state['checkpoint']>=limit, (state['status'],state['checkpoint'],failure)
