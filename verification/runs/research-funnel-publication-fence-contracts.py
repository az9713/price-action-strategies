"""Actual cancel/shutdown/owner loss after root bytes, before original publication."""
import importlib.util,hashlib
from pathlib import Path
from threading import Event
import pytest
from backend.lab import service
from backend.lab import worker as worker_module
from backend.lab.worker import Worker
from backend.lab.research_funnel_arms import queue_arms

spec=importlib.util.spec_from_file_location('funnel_arm_original_fixtures',Path(__file__).with_name('research-funnel-arm-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs;registration=fixtures.registration;planned=fixtures.planned


@pytest.mark.parametrize('boundary',['cancel','shutdown','reclaimed_owner'])
def test_inactive_or_canceled_worker_cannot_publish_after_root_candidate_write(planned,monkeypatch,boundary):
    lab,study=planned;queue_arms(lab,study['id']);stop=Event();fired=[];newer=[]
    with lab.store.db() as db:jid=db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()[0]
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    old_write=worker_module.compressed_write
    def write(path,value):
        old_write(path,value)
        if value.get('job_id')!=jid or fired:return
        fired.append(True)
        if boundary=='cancel':lab.store.cancel(jid)
        elif boundary=='shutdown':stop.set()
        else:
            # Explicit stale-owner fault injection while the old worker still
            # exists. A different actual owner claims and completes the same
            # original job, reusing its real checkpoints; no outcome is forged.
            with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(jid,))
            def no_prices(*a,**k):raise AssertionError('Reclaimed complete parts must not rerun financial accounts.')
            monkeypatch.setattr(lab,'_evaluation_input',no_prices)
            assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
            newer.append(hashlib.sha256(lab.output_path(jid).read_bytes()).hexdigest())
    monkeypatch.setattr(worker_module,'compressed_write',write)
    monkeypatch.setattr(service,'compressed_write',write)
    assert Worker(lab,stop).run_once() and fired==[True]
    with lab.store.db() as db:
        count=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]
        assert count==(1 if boundary=='reclaimed_owner' else 0),'An inactive/canceled root publication must not become original evidence.'
        assert [r[0] for r in db.execute('SELECT attempts FROM trial_plans WHERE job_id=? ORDER BY part',(jid,))]==[1,1]
    if boundary=='reclaimed_owner':
        assert hashlib.sha256(lab.output_path(jid).read_bytes()).hexdigest()==newer[0]
    else:assert lab.store.job(jid)['status']==('canceled' if boundary=='cancel' else 'queued')
