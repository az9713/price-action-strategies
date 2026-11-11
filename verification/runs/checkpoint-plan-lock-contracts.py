"""Actual large-plan originals and bounded heartbeat contention contracts."""
from pathlib import Path
from threading import current_thread
import json,os,sqlite3,time
import pytest
from backend.lab import trials as module
from backend.lab.models import Search
from backend.lab.service import Lab
from backend.lab.store import StateError,Store
from backend.lab.worker import Worker
from test_trade_twin_source import original


def test_actual_10000_plan_warm_verification_keeps_fresh_rows_without_python_reencoding_every_occurrence(original,monkeypatch):
    lab,parent,_=original
    job=lab.create_experiment(Search(dataset_id=parent['payload']['dataset_id'],start=parent['payload']['start'],end=parent['payload']['end'],count=10000,seed=42))
    ledger=lab.store._trials;ledger.verify(job['id']);calculate=module.identity;calls=[];sql=[]
    def counted(value):
        if (isinstance(value,dict) and ('configurations' in value or set(value)=={'job_id','part','window'})) or isinstance(value,list) and len(value)==10000:
            calls.append(True)
        return calculate(value)
    monkeypatch.setattr(module,'identity',counted)
    with lab.store.db() as db:
        db.set_trace_callback(sql.append);started=time.perf_counter()
        ledger.verify(job['id'],db);ledger.verify(job['id'],db)
        elapsed=time.perf_counter()-started
        assert not db.in_transaction
    assert calls==[],'Repeated original-plan decoding/per-occurrence canonical identities reintroduced quadratic work.'
    warm_calls=len(calls)
    aggregates=[s for s in sql if 'json_group_array' in s.lower()]
    assert len(aggregates)==2,'Every warm verification must freshly aggregate all original immutable occurrence rows.'
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone()[0]==10000
        tail=dict(db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part DESC,window DESC LIMIT 1',(job['id'],)).fetchone())
        db.execute("UPDATE trial_plans SET config_id=? WHERE id=?",('0'*64,tail['id']))
    try:
        with pytest.raises(StateError):ledger.verify(job['id'])
    finally:
        with lab.store.db() as db:db.execute('UPDATE trial_plans SET config_id=? WHERE id=?',(tail['config_id'],tail['id']))
    ledger.verify(job['id'])
    out=os.environ.get('PA_EVIDENCE_RUN_DIR')
    if out:Path(out,'actual-large-plan-fresh-witness-work.json').write_text(json.dumps(dict(planned_original_configurations=10000,executed_financial_accounts=0,
        warm_full_original_row_aggregates=len(aggregates),repeated_large_python_identities=warm_calls,two_warm_verify_seconds=elapsed,last_original_row_corruption_refused=True,
        financial_capacity_certified=False),indent=2),encoding='utf-8')


def test_heartbeat_real_held_writer_has_bounded_lock_wait(tmp_path):
    store=Store(tmp_path);job=store.create_job('download',{});assert store.claim('bounded')['id']==job['id']
    with store.db() as writer:
        writer.execute('BEGIN IMMEDIATE');started=time.perf_counter()
        with pytest.raises(sqlite3.OperationalError):store.heartbeat(job['id'],'bounded')
        elapsed=time.perf_counter()-started
        writer.execute('ROLLBACK')
    assert elapsed<2,'A heartbeat must not block behind a long writer for the whole10-second default database timeout.'
    assert store.heartbeat(job['id'],'bounded') is False


def test_worker_retries_transient_busy_heartbeat_without_silent_thread_death(tmp_path,monkeypatch):
    lab=Lab(tmp_path);job=lab.store.create_job('download',{});worker=Worker(lab)
    heartbeat=lab.store.heartbeat;attempts=[]
    def transient(*a,**k):
        if current_thread().name=='job-heartbeat':
            attempts.append(True)
            if len(attempts)<=2:
                error=sqlite3.OperationalError('database is locked');error.sqlite_errorcode=sqlite3.SQLITE_BUSY;raise error
        return heartbeat(*a,**k)
    monkeypatch.setattr(lab.store,'heartbeat',transient)
    def controlled(*a):
        cancel=a[1];deadline=time.monotonic()+6
        while len(attempts)<3 and time.monotonic()<deadline:
            assert not cancel();time.sleep(.02)
        assert len(attempts)>=3,'The lease thread died after one transient busy error.'
        assert not cancel()
    monkeypatch.setattr(worker,'_execute',controlled)
    assert worker.run_once() and lab.store.job(job['id'])['status']=='completed'
