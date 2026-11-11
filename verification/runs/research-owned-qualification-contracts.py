"""Next owned-workflow contracts; an absence check is not implementation proof."""
import importlib
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from backend.lab import service
from backend.lab.config import identity
from backend.lab.store import StateError
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('owned_qualification_registration_fixtures',Path(__file__).with_name('research-funnel-registration-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs;registration=fixtures.registration


def test_owned_original_funnel_qualification_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_funnel_jobs') is not None,'Owned qualification/control-dependency/candidate-freeze workflow is not implemented.'


@pytest.fixture
def flow():return importlib.import_module('backend.lab.research_funnel_jobs')


@pytest.fixture
def registered(inputs,registration):
    lab,request,*_=inputs
    return lab,registration.register_funnel(lab,request)


def test_original_reservation_is_concurrent_idempotent_complete_and_price_free(flow,registered,monkeypatch):
    lab,study=registered
    def forbidden(*args,**kwargs):raise AssertionError('Reservation must not decode prices or calculate accounts.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=list(pool.map(lambda _:flow.create_qualification(lab,study['id']),range(2)))
    assert jobs[0]['id']==jobs[1]['id'] and jobs[0]['kind']=='funnel_qualification'
    assert flow.create_qualification(lab,study['id'])['id']==jobs[0]['id']
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==6
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='search'").fetchone()[0]==5
        assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=?",(jobs[0]['id'],)).fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='funnel_qualification_reserved'",(study['id'],)).fetchone()[0]==1


def test_oldest_queued_qualification_cannot_starve_its_original_account_dependencies(flow,registered):
    lab,study=registered;parent=flow.create_qualification(lab,study['id'])
    with lab.store.db() as db:db.execute('UPDATE jobs SET created=0 WHERE id=?',(parent['id'],))
    claimed=lab.store.claim('authored-queue-order-owner')
    assert claimed is not None and claimed['kind']=='search' and claimed['id']!=parent['id']
    assert lab.store.job(parent['id'])['status']=='queued'


def test_actual_zero_candidate_completion_freezes_all_members_and_inspects_without_new_math(flow,registered,monkeypatch):
    lab,study=registered;job=flow.create_qualification(lab,study['id'])
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    for _ in range(6):assert Worker(lab).run_once()
    current=lab.store.job(job['id']);assert current['status']=='completed',current['error']
    def forbidden(*args,**kwargs):raise AssertionError('Saved inspection must not regenerate prices, accounts or qualification math.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    if hasattr(flow,'qualify'):monkeypatch.setattr(flow,'qualify',forbidden)
    saved=flow.inspect_qualification(lab,job['id']);report=saved['report'];freeze=saved['candidate_freeze']
    assert report['state']=='complete' and report['candidate_ids']==[] and len(report['rows'])==2
    assert freeze['study_id']==study['id'] and freeze['candidate_ids']==[]
    assert freeze['configuration_universe_hash']==study['spec']['configuration_universe_hash']
    assert freeze['family_members']=={'change_of_character':[identity(c) for c in study['spec']['configurations']]}
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==6
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='funnel_candidates_frozen'",(study['id'],)).fetchone()[0]==1
    assert lab.guard.study(study['id'])['status']=='registered'


def test_cancel_and_resume_keep_the_original_qualification_and_account_cohort(flow,registered,monkeypatch):
    lab,study=registered;job=flow.create_qualification(lab,study['id']);lab.store.cancel(job['id'])
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    for _ in range(5):assert Worker(lab).run_once()
    assert Worker(lab).run_once() is False
    assert flow.create_qualification(lab,study['id'])['id']==job['id']
    with lab.store.db() as db:
        before=[tuple(row) for row in db.execute("SELECT id,attempts FROM trial_plans WHERE role='strategy' ORDER BY id")]
    lab.store.resume(job['id']);assert Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed'
    with lab.store.db() as db:
        assert [tuple(row) for row in db.execute("SELECT id,attempts FROM trial_plans WHERE role='strategy' ORDER BY id")]==before
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==6


def test_actual_positive_preliminary_reserves_original_control_then_waits_without_starvation(flow,tmp_path,monkeypatch):
    fixture_spec=importlib.util.spec_from_file_location('owned_actual_positive_fixtures',Path(__file__).with_name('research-qualification-positive-accounts.py'))
    positive=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(positive)
    lab,study,arms=positive.build_positive_accounts(tmp_path,monkeypatch)
    job=flow.create_qualification(lab,study['id'])
    assert Worker(lab).run_once()
    current=lab.store.job(job['id']);assert current['status']=='queued' and current['owner'] is None
    assert not lab.output_path(job['id']).exists()
    with lab.store.db() as db:
        children=db.execute("SELECT id,payload,status FROM jobs WHERE kind='trade_twins'").fetchall()
        assert len(children)==1 and children[0]['status']=='queued'
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='funnel_candidates_frozen'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
    # The parent predates the control but must release its claim and yield to it.
    next_job=lab.store.claim('authored-control-scheduling-owner')
    assert next_job is not None and next_job['id']==children[0]['id'] and next_job['kind']=='trade_twins'


@pytest.mark.parametrize('fault',['missing_reservation','duplicate_reservation','changed_study'])
def test_damaged_original_qualification_reservation_cannot_be_replaced(flow,registered,fault):
    lab,study=registered;job=flow.create_qualification(lab,study['id'])
    with lab.store.db() as db:
        if fault=='missing_reservation':db.execute("DELETE FROM events WHERE entity_id=? AND kind='funnel_qualification_reserved'",(study['id'],))
        elif fault=='duplicate_reservation':
            import json
            details=json.loads(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='funnel_qualification_reserved'",(study['id'],)).fetchone()[0])
            lab.store.event('funnel_qualification_reserved',study['id'],details,db)
        else:db.execute("UPDATE studies SET spec=json_set(spec,'$.minimum_signals',1) WHERE id=?",(study['id'],))
    with pytest.raises(StateError):flow.create_qualification(lab,study['id'])
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==6
        assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==0
