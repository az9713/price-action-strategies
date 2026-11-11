"""Actual product worker dispatch and all-or-none final publication contracts."""
import importlib.util
import pytest

from backend.lab import trade_twin_jobs as jobs
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from test_reference_execution import CFG,ZERO,ACCOUNT
from test_trade_twin_source import original


def test_complete_paired_trade_twin_worker_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_worker') is not None, 'Complete original trade-twin worker is not implemented.'


def test_actual_empty_original_completes_explicitly_without_fabricated_financial_sets(original,monkeypatch):
    lab,first,_=original
    monkeypatch.setattr('backend.lab.service.generate_signals',lambda *a,**k:[])
    parent=lab.create_experiment(Experiment(dataset_id=first['payload']['dataset_id'],start=first['payload']['start'],end=first['payload']['end'],strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    child=jobs.create(lab,parent['id'])
    assert Worker(lab).run_once()
    assert lab.store.job(child['id'])['status']=='completed'
    report=lab.report(child['id'])
    assert report['report_type']=='trade_twins' and report['financial_occurrences']==0
    assert report['comparison_eligible'] is False
    assert all(s['state']=='ineligible' and s['observed_sets']==0 and s['adapted_pass'] is None for s in report['summaries'].values())
    assert len([e for e in lab.store.events(child['id']) if e['kind']=='result_saved'])==1
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='not_generated'",(child['id'],)).fetchone()[0]==20000
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id WHERE t.job_id=? AND t.role='trade_twin_set'",(child['id'],)).fetchone()[0]==0


def test_actual_worker_shutdown_after_one_part_retains_originals_without_final_result(original,monkeypatch):
    lab,parent,_=original;child=jobs.create(lab,parent['id']);worker=Worker(lab)
    progress=worker._progress
    def stop(job,fraction,note,checkpoint=None):
        progress(job,fraction,note,checkpoint)
        if checkpoint==1:worker.shutdown.set()
    monkeypatch.setattr(worker,'_progress',stop)
    assert worker.run_once()
    assert lab.store.job(child['id'])['status']=='queued'
    assert len([e for e in lab.store.events(child['id']) if e['kind']=='twin_part_committed'])==1
    assert not any(e['kind']=='result_saved' for e in lab.store.events(child['id']))
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='checkpointed'",(child['id'],)).fetchone()[0]==200
