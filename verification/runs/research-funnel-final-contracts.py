"""Protected all-version final evaluation on BOTH frozen instruments.

Zero candidates do not shrink the host layer4 final cohort. Actual empty-signal
accounts isolate account/scope/consumption behavior, not pattern correctness.
"""
import importlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from backend.lab import service
from backend.lab.config import identity
from backend.lab.research import ResearchError
from backend.lab.store import StateError
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('funnel_final_qualified_originals',Path(__file__).with_name('research-owned-qualification-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;clone_authored=fixtures.clone_authored


def test_both_instrument_all_version_final_workflow_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_funnel_final') is not None,'One-time all-version two-instrument final workflow is not implemented.'


@pytest.fixture
def flow():return importlib.import_module('backend.lab.research_funnel_final')


@pytest.fixture
def qualified(originals,tmp_path):
    lab=clone_authored(originals['complete'],tmp_path)
    return lab,lab.guard.study(originals['study_id']),originals['job_id']


def test_final_reservation_is_concurrent_idempotent_all_versions_and_price_free(flow,qualified,monkeypatch):
    lab,study,qualification=qualified
    def forbidden(*args,**kwargs):raise AssertionError('Final reservation must not decode final prices or consume final access.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    with ThreadPoolExecutor(max_workers=2) as pool:jobs=list(pool.map(lambda _:flow.create_final(lab,study['id']),range(2)))
    assert jobs[0]['id']==jobs[1]['id'] and jobs[0]['kind']=='funnel_final'
    assert flow.create_final(lab,study['id'])['id']==jobs[0]['id']
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='strategy'",(jobs[0]['id'],)).fetchone()[0]==4
        assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=?',(jobs[0]['id'],)).fetchone()[0]==5
        assert db.execute('SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON t.id=a.trial_id WHERE t.job_id=?',(jobs[0]['id'],)).fetchone()[0]==0
    for arm in study['spec']['final_arms'].values():
        with pytest.raises(ResearchError):lab.guard.access([arm['symbol']],arm['start'],arm['end'],'forbidden',record=False)


def test_actual_final_evaluates_every_version_on_both_instruments_after_one_consumption(flow,qualified,monkeypatch):
    lab,study,qualification=qualified;job=flow.create_final(lab,study['id']);load=lab._evaluation_input;reads=[]
    def observed(*args,**kwargs):
        with lab.store.db() as db:
            events=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(study['id'],)).fetchall()
            assert len(events)==1
        reads.append((args[0],tuple(kwargs['symbols'])))
        return load(*args,**kwargs)
    monkeypatch.setattr(lab,'_evaluation_input',observed);monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    assert lab.guard.study(study['id'])['status']=='final_complete' and len(reads)==4
    saved=flow.inspect_final(lab,job['id']);report=saved['report'];configurations=study['spec']['configurations']
    assert report['version_count']==2 and report['instrument_count']==2 and len(saved['rows'])==2
    assert report['source_video']=='https://www.youtube.com/watch?v=z97PnFIPoFg'
    assert [row['config_id'] for row in saved['rows']]==[identity(c) for c in configurations]
    assert all(row['candidate'] is False and set(row['reports'])==set(study['spec']['final_arms']) for row in saved['rows'])
    for part,configuration in enumerate(configurations):
        for key,arm in study['spec']['final_arms'].items():
            account=flow.read_final_account(lab,job['id'],part,key)
            assert account['config_id']==identity(configuration) and account['config']==configuration
            assert account['dataset_id']==arm['dataset_context']['dataset_id'] and set(account['charts'])=={arm['symbol']}
            assert account['start']==arm['start'] and account['end']==arm['end']
    assert flow.create_final(lab,study['id'])['id']==job['id'] and Worker(lab).run_once() is False
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='funnel_final'").fetchone()[0]==1
        assert db.execute("SELECT MAX(attempts) FROM trial_plans WHERE job_id=? AND role='strategy'",(job['id'],)).fetchone()[0]==1


def test_first_final_price_failure_still_consumes_once_and_same_job_recovers(flow,qualified,monkeypatch):
    lab,study,qualification=qualified;job=flow.create_final(lab,study['id']);load=lab._evaluation_input
    def failed_read(*args,**kwargs):
        with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(study['id'],)).fetchone()[0]==1
        raise StateError('Authored failure on the first final price read after consumption.')
    with monkeypatch.context() as patch:
        patch.setattr(lab,'_evaluation_input',failed_read)
        assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='failed'
    assert lab.guard.study(study['id'])['status']=='final_failed'
    assert flow.create_final(lab,study['id'])['id']==job['id']
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    lab.store.resume(job['id']);assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='funnel_final'").fetchone()[0]==1


def test_damaged_original_candidate_freeze_cannot_reserve_or_unlock_final(flow,qualified):
    lab,study,qualification=qualified
    with lab.store.db() as db:db.execute('DELETE FROM funnel_candidate_freezes WHERE study_id=?',(study['id'],))
    with pytest.raises(StateError):flow.create_final(lab,study['id'])
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='funnel_final'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
