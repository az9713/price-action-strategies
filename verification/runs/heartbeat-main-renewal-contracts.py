"""A lease renewed by committed main-thread progress remains a valid renewal."""
from pathlib import Path
from threading import current_thread
import json,os,sqlite3,time
from backend.lab.service import Lab
from backend.lab.worker import Worker


def test_main_progress_renewals_prevent_false_background_lease_timeout(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    heartbeat=lab.store.heartbeat;busy=[];renewals=[];started=time.monotonic()
    def background_starved(*a,**k):
        if current_thread().name=='job-heartbeat':
            busy.append(time.monotonic())
            error=sqlite3.OperationalError('database is locked');error.sqlite_errorcode=sqlite3.SQLITE_BUSY;raise error
        value=heartbeat(*a,**k);renewals.append(time.monotonic());return value
    monkeypatch.setattr(lab.store,'heartbeat',background_starved)
    def controlled(j,cancel):
        deadline=time.monotonic()+11.5;count=0
        while time.monotonic()<deadline:
            assert not cancel(),'The background thread ignored successful owned main-thread lease renewals.'
            worker._progress(j,.5,'Actual main-thread renewal',count);count+=1;time.sleep(.1)
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once();state=lab.store.job(job['id'])
    remaining=None if state['lease_until'] is None else state['lease_until']-time.time()
    out=os.environ.get('PA_EVIDENCE_RUN_DIR')
    if out:Path(out,'actual-main-and-background-lease-observations.json').write_text(json.dumps(dict(
        background_busy_errors=len(busy),successful_real_owned_main_renewals=len(renewals),
        final_status=state['status'],remaining_actual_lease_seconds_after_worker_return=remaining,
        elapsed_seconds=time.monotonic()-started,financial_accounts_executed=0,
        current_guard_diagnostic=getattr(worker,'last_lease_failure',None)),indent=2),encoding='utf-8')
    assert len(busy)>=5 and len(renewals)>=5
    assert state['status']=='completed',('Main progress genuinely renewed this owned lease.',state['status'],remaining)
