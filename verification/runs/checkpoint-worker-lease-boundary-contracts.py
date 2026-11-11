"""Original verifier byte provenance and real heartbeat writer-lock boundaries."""
from pathlib import Path
from threading import Event,Thread,current_thread,enumerate as threads
import ast,hashlib,json,sqlite3,time
import pytest
from backend.lab import trials as trial_module
from backend.lab.service import Lab
from backend.lab.worker import Worker


def test_cold_verification_preserves_the_exact_original_algorithm():
    before=Path(__file__).with_name('checkpoint-lock-before')
    record=json.loads((before/'provenance.json').read_text())
    original_path=before/'trials.py';raw=original_path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==next(r['sha256'] for r in record['files'] if r['path']=='backend/lab/trials.py')
    old=next(n for n in ast.parse(raw).body if isinstance(n,ast.ClassDef) and n.name=='TrialLedger')
    new=next(n for n in ast.parse(Path(trial_module.__file__).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='TrialLedger')
    original=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='verify')
    retained=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_verify_original')
    assert isinstance(original.body[0],ast.If) and ast.unparse(original.body[0].test)=='db is None'
    assert ast.dump(ast.Module(body=original.body[1:],type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=retained.body,type_ignores=[]),include_attributes=False)


def test_real_transient_writer_lock_recovers_heartbeat_and_retires_thread(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    ready=Event();release=Event();renewed=Event();busy=[];errors=[];heartbeat=lab.store.heartbeat
    def held():
        try:
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');ready.set();release.wait(7);db.execute('ROLLBACK')
        except BaseException as error:errors.append(error)
    def measured(*a,**k):
        try:result=heartbeat(*a,**k)
        except sqlite3.OperationalError as error:
            busy.append(getattr(error,'sqlite_errorcode',None));raise
        if current_thread().name=='job-heartbeat' and busy:renewed.set()
        return result
    monkeypatch.setattr(lab.store,'heartbeat',measured)
    def controlled(job,cancel):
        writer=Thread(target=held);writer.start()
        try:
            assert ready.wait(2);deadline=time.monotonic()+3
            while time.monotonic()<deadline:
                assert not cancel();time.sleep(.02)
            release.set()
            assert renewed.wait(3) and not cancel()
        finally:release.set();writer.join(3)
        assert not writer.is_alive() and not errors
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and lab.store.job(job['id'])['status']=='completed'
    assert busy and not any(t.name=='job-heartbeat' for t in threads())


def test_real_persistent_writer_lock_stops_before_lease_is_trusted_and_keeps_job_recoverable(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    ready=Event();release=Event();errors=[];observed=[]
    def held():
        try:
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');ready.set();release.wait(17);db.execute('ROLLBACK')
        except BaseException as error:errors.append(error)
    def controlled(job,cancel):
        writer=Thread(target=held);writer.start();started=time.monotonic()
        try:
            assert ready.wait(2)
            while not cancel() and time.monotonic()-started<14:time.sleep(.02)
            observed.append(time.monotonic()-started)
            assert cancel() and observed[0]<14
            raise InterruptedError('Actual heartbeat writer lock made continued lease ownership unsafe.')
        finally:release.set();writer.join(3)
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and observed and not errors
    assert lab.store.job(job['id'])['status']!='completed'
    assert not any(e['kind']=='result_saved' for e in lab.store.events(job['id']))
    assert not any(t.name=='job-heartbeat' for t in threads())
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=? WHERE id=?',(time.time()-1,job['id']))
    assert lab.store.claim('recovered-after-observed-lease-loss')['id']==job['id']


@pytest.mark.parametrize('fault',['io_error','unexpected_error'])
def test_non_busy_heartbeat_failure_signals_main_without_unhandled_thread_exception(tmp_path,monkeypatch,fault):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    def failed(*a,**k):
        if fault=='unexpected_error':raise RuntimeError('Authored lease renewal failure')
        error=sqlite3.OperationalError('disk I/O error');error.sqlite_errorcode=sqlite3.SQLITE_IOERR;raise error
    monkeypatch.setattr(lab.store,'heartbeat',failed)
    def controlled(job,cancel):
        deadline=time.monotonic()+3
        while not cancel() and time.monotonic()<deadline:time.sleep(.02)
        assert cancel()
        raise InterruptedError('Observed non-busy renewal failure')
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and lab.store.job(job['id'])['status']!='completed'
    assert not any(t.name=='job-heartbeat' for t in threads())
