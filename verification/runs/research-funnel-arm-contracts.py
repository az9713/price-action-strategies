"""Actual five-arm accounts from one frozen original configuration universe."""
import importlib,importlib.util,json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from backend.lab import service
from backend.lab.worker import Worker
from backend.lab.research_family_source import read_saved_family
from backend.lab.store import StateError
from backend.lab.research import ResearchError

spec=importlib.util.spec_from_file_location('funnel_registration_fixtures',Path(__file__).with_name('research-funnel-registration-contracts.py'))
fixture_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture_module)
inputs=fixture_module.inputs;registration=fixture_module.registration


def test_funnel_owned_account_arms_are_implemented():
    assert importlib.util.find_spec('backend.lab.research_funnel_arms') is not None,'Original five-arm account orchestration is not implemented.'


@pytest.fixture
def flow():return importlib.import_module('backend.lab.research_funnel_arms')


@pytest.fixture
def planned(registration,inputs):
    lab,request,*_=inputs
    return lab,registration.register_funnel(lab,request)


def test_all_five_original_arms_freeze_before_prices_then_execute_actual_complete_accounts(flow,planned,monkeypatch):
    lab,study=planned
    def forbidden(*a,**k):raise AssertionError('Arm reservation must not read prices or run accounts.')
    with monkeypatch.context() as patch:
        patch.setattr(lab,'_evaluation_input',forbidden)
        reserved=flow.queue_arms(lab,study['id'])
    assert reserved['study_id']==study['id'] and set(reserved['arms'])==set(study['spec']['development_arms'])
    assert flow.queue_arms(lab,study['id'])['arms']==reserved['arms']
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==5
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]==5
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE state='planned' AND role='strategy' AND window='report'").fetchone()[0]==10
        assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='funnel_arms_frozen'",(study['id'],)).fetchone()[0]==1
    # Empty authored signal lists isolate actual financial-account and axis
    # integration from the separate price-pattern detector tests.
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    for _ in range(5):assert Worker(lab).run_once()
    assert Worker(lab).run_once() is False
    for key,jid in reserved['arms'].items():
        job=lab.store.job(jid);assert job['status']=='completed',job['error']
        binding=flow.verify_arm(lab,job);assert binding['arm_key']==key
        arm=study['spec']['development_arms'][key]
        assert job['payload']['evaluation_symbols']==[arm['symbol']]
        assert job['payload']['configurations']==study['spec']['configurations']
        result=lab.result(jid);assert result['funnel_arm']==job['payload']['funnel_arm'] and result['count']==2
        for part in range(2):
            report=lab.report(jid,part)
            assert report['start']==arm['start'] and report['end']==arm['end']
            assert report['dataset_id']==arm['dataset_context']['dataset_id']
            assert report['research_arm_context']['role']==arm['role']
            assert set(report['charts'])=={arm['symbol']}
        family=read_saved_family(lab,jid,'change_of_character')
        assert family['version_count']==2 and family['marked']['gate_pass'] is False
    with lab.store.db() as db:
        assert db.execute('SELECT MAX(end) FROM viewed_windows').fetchone()[0]<'2026-11-05'
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
    assert lab.guard.study(study['id'])['spec']==study['spec']
    assert flow.queue_arms(lab,study['id'])['arms']==reserved['arms']


def test_concurrent_arm_reservation_returns_one_original_five_job_map(flow,planned):
    lab,study=planned
    with ThreadPoolExecutor(max_workers=2) as executor:
        values=list(executor.map(lambda _:flow.queue_arms(lab,study['id']),range(2)))
    assert values[0]['arms']==values[1]['arms']
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==5
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='funnel_arms_frozen'",(study['id'],)).fetchone()[0]==1


@pytest.mark.parametrize('fault',['missing_map','duplicate_map','missing_link','wrong_link','changed_study','changed_current_payload'])
def test_broken_original_arm_reservation_never_replaces_or_executes_accounts(flow,planned,monkeypatch,fault):
    lab,study=planned;reserved=flow.queue_arms(lab,study['id']);sid=study['id']
    with lab.store.db() as db:
        first=db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()[0]
        if fault=='missing_map':db.execute("DELETE FROM events WHERE entity_id=? AND kind='funnel_arms_frozen'",(sid,))
        elif fault=='duplicate_map':
            value=json.loads(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='funnel_arms_frozen'",(sid,)).fetchone()[0]);lab.store.event('funnel_arms_frozen',sid,value,db)
        elif fault=='missing_link':db.execute('DELETE FROM funnel_arm_links WHERE study_id=? AND job_id=?',(sid,first))
        elif fault=='wrong_link':db.execute("UPDATE funnel_arm_links SET arm_key='wrong_axis' WHERE study_id=? AND job_id=?",(sid,first))
        elif fault=='changed_study':
            value=dict(study['spec']);value['minimum_signals']=1;db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(value),sid))
        else:
            value=lab.store.job(first)['payload'];value['evaluation_symbols']=['IWM'];db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(value),first))
    with pytest.raises((StateError,ResearchError)):flow.queue_arms(lab,sid)
    def forbidden(*a,**k):raise AssertionError('Corrupt original arm identity must be refused before prices.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    assert Worker(lab).run_once() and lab.store.job(first)['status']=='failed'
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==5
        assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==0


def test_unknown_and_basic_studies_cannot_reserve_research_arms(flow,inputs):
    from backend.lab.models import Study
    lab,request,*_=inputs
    with pytest.raises(StateError,match='original registered'):flow.queue_arms(lab,'0'*32)
    basic=Study(**{name:getattr(request,name) for name in Study.model_fields})
    saved=lab.register_study(basic)
    with pytest.raises(StateError,match='registration or original engine'):flow.queue_arms(lab,saved['id'])


def test_changed_manifest_metadata_cannot_redefine_original_arm_context(flow,planned):
    lab,study=planned
    path=lab.datasets_root/study['spec']['replication_dataset_id']/'manifest.json'
    value=json.loads(path.read_text(encoding='utf-8'));value['metadata']['provider']='Changed after original registration'
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(StateError):flow.queue_arms(lab,study['id'])


def test_hash_consistent_wrong_era_instrument_is_not_a_valid_frozen_arm(flow,planned):
    from backend.lab.config import identity
    lab,study=planned;changed=json.loads(json.dumps(study['spec']))
    changed['development_arms']['era_one']['symbol']='QQQ'
    with lab.store.db() as db:
        db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(changed),study['id']))
        row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='study_registered'",(study['id'],)).fetchone()
        event=json.loads(row['details']);event['spec_hash']=identity(changed)
        db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(event),row['id']))
    with pytest.raises(StateError,match='arm definitions'):flow.queue_arms(lab,study['id'])


def test_reanchored_arm_map_and_changed_claimed_input_are_not_accepted(flow,planned):
    import copy
    lab,study=planned;reserved=flow.queue_arms(lab,study['id']);jid=next(iter(reserved['arms'].values()))
    changed=copy.deepcopy(lab.store.job(jid));changed['payload']['name']='Changed claimed worker input'
    with pytest.raises(StateError,match='inputs or reservation'):flow.verify_arm(lab,changed)
    with lab.store.db() as db:
        row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='funnel_arms_frozen'",(study['id'],)).fetchone()
        value=json.loads(row['details']);value['configuration_universe_hash']='0'*64
        db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(value),row['id']))
    with pytest.raises(StateError,match='complete frozen study'):flow.queue_arms(lab,study['id'])


def test_closing_cancellation_and_missing_original_manifest_are_domain_refusals(flow,planned):
    lab,study=planned;reserved=flow.queue_arms(lab,study['id']);job=lab.store.job(next(iter(reserved['arms'].values())));calls=[]
    def cancel():calls.append(True);return len(calls)==2
    with pytest.raises(InterruptedError):flow.verify_arm(lab,job,cancel=cancel)
    path=lab.datasets_root/study['spec']['replication_dataset_id']/'manifest.json';path.unlink()
    with pytest.raises(StateError,match='reservation is unavailable'):flow.queue_arms(lab,study['id'])
    with pytest.raises(StateError,match='identity is missing'):flow.verify_arm(lab,job)
