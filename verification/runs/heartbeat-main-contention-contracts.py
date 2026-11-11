"""Real main-progress writer contention must not create terminal job failure."""
from threading import Event,Thread
import sqlite3,time
import pytest
from backend.lab.service import Lab
from backend.lab.worker import Worker


def test_main_progress_retries_transient_real_writer_without_failing_job(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    ready=Event();release=Event();errors=[];observed=[]
    def writer():
        try:
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');ready.set()
                release.wait(1.6);db.execute('ROLLBACK')
        except BaseException as error:errors.append(error)
    def controlled(j,cancel):
        held=Thread(target=writer);held.start()
        try:
            assert ready.wait(2);started=time.monotonic()
            worker._progress(j,.5,'Actual main-thread checkpoint after transient writer',1)
            observed.append(time.monotonic()-started)
            assert not cancel()
        finally:release.set();held.join(3)
        assert not held.is_alive() and not errors
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once()
    state=lab.store.job(job['id'])
    assert state['status']=='completed',('A transient writer lock made main progress terminally fail.',state['status'],state['error'])
    assert observed and 1<=observed[0]<5 and state['checkpoint']==1


def test_main_progress_persistent_writer_stops_without_certifying_then_original_recovers(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    ready=Event();release=Event();errors=[];elapsed=[]
    def writer():
        try:
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');ready.set();release.wait(15);db.execute('ROLLBACK')
        except BaseException as error:errors.append(error)
    def controlled(j,cancel):
        held=Thread(target=writer);held.start()
        try:
            assert ready.wait(2);started=time.monotonic()
            with pytest.raises(InterruptedError):worker._progress(j,.5,'Must not certify under persistent writer',1)
            elapsed.append(time.monotonic()-started)
            assert cancel()
            raise InterruptedError('Unsafe renewal deliberately refused.')
        finally:release.set();held.join(3)
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and not errors and 9<=elapsed[0]<14
    assert worker.last_lease_failure['kind']=='renewal_timeout'
    assert lab.store.job(job['id'])['status']=='running'
    assert not any(e['kind']=='result_saved' for e in lab.store.events(job['id']))
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=? WHERE id=?',(time.time()-1,job['id']))
    assert lab.store.claim('new-owner')['id']==job['id']


def test_shutdown_interrupts_main_progress_retries_and_requeues_same_job(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});stop=Event();worker=Worker(lab,stop)
    ready=Event();release=Event();errors=[]
    def writer():
        try:
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');ready.set();stop.wait(1);stop.set();release.wait(5);db.execute('ROLLBACK')
        except BaseException as error:errors.append(error)
    def controlled(j,cancel):
        held=Thread(target=writer);held.start()
        try:
            assert ready.wait(2)
            worker._progress(j,.5,'Shutdown while main renewal waits',1)
        finally:release.set();held.join(3)
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and not errors
    assert lab.store.job(job['id'])['status']=='queued'
    assert lab.store.claim('resuming-original')['id']==job['id']


@pytest.mark.parametrize('code',[sqlite3.SQLITE_IOERR,sqlite3.SQLITE_CORRUPT])
def test_main_nonbusy_database_fault_is_never_retried_or_certified(tmp_path,monkeypatch,code):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab);calls=[]
    def fault(*a,**k):
        calls.append(1);error=sqlite3.OperationalError('Authored nonbusy main heartbeat fault')
        error.sqlite_errorcode=code;raise error
    monkeypatch.setattr(lab.store,'heartbeat',fault)
    monkeypatch.setattr(worker,'_execute',lambda j,cancel:worker._progress(j,.5,'Refused',1))
    assert worker.run_once() and len(calls)==1
    assert worker.last_lease_failure['kind']=='database_failure'
    assert lab.store.job(job['id'])['status']=='running'
    assert not any(e['kind']=='result_saved' for e in lab.store.events(job['id']))


def test_main_retry_freshly_refuses_new_owner_without_modifying_its_job(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab);heartbeat=lab.store.heartbeat;calls=[]
    def replace_owner(*a,**k):
        calls.append(1)
        if len(calls)==1:
            with lab.store.db() as db:db.execute('UPDATE jobs SET owner=? WHERE id=?',('new-owner',job['id']))
            error=sqlite3.OperationalError('Authored transient busy with actual ownership replacement')
            error.sqlite_errorcode=sqlite3.SQLITE_BUSY;raise error
        return heartbeat(*a,**k)
    monkeypatch.setattr(lab.store,'heartbeat',replace_owner)
    monkeypatch.setattr(worker,'_execute',lambda j,cancel:worker._progress(j,.5,'Stale update',1))
    assert worker.run_once() and len(calls)==2
    state=lab.store.job(job['id'])
    assert state['status']=='running' and state['owner']=='new-owner' and state['checkpoint']==0
