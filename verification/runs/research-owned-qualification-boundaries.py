"""Actual owned-account originals and publication/source/queue fault boundaries.

Copies contain only this module's explicitly authored synthetic stores. They are
not user database/market-cache copies and contain no credential file.
"""
import importlib.util
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
from threading import Event
import pytest
from backend.lab import service
from backend.lab.service import Lab
from backend.lab.store import StateError
from backend.lab.worker import Worker
from backend.lab import research_funnel_jobs as flow
from backend.lab.research_qualification_source import verify_snapshot

spec=importlib.util.spec_from_file_location('owned_boundary_registration',Path(__file__).with_name('research-funnel-registration-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs;registration=fixtures.registration


def clone_authored(source,tmp_path):
    destination=tmp_path/'authored-copy';destination.mkdir(parents=True)
    shutil.copytree(source.root/'data',destination/'data',ignore=shutil.ignore_patterns('lab.sqlite3','lab.sqlite3-wal','lab.sqlite3-shm'))
    # SQLite backup captures the original committed SQL view, including WAL.
    with closing(sqlite3.connect(source.store.path)) as src,closing(sqlite3.connect(destination/'data/lab.sqlite3')) as dst:src.backup(dst)
    return Lab(destination)


@pytest.fixture(scope='module')
def originals(tmp_path_factory):
    root=tmp_path_factory.mktemp('authored-owned-qualification');parts={}
    with pytest.MonkeyPatch.context() as patch:
        lab,request,*_=fixtures.inputs.__wrapped__(root/'source')
        study=fixtures.registration.__wrapped__().register_funnel(lab,request);job=flow.create_qualification(lab,study['id'])
        patch.setattr(service,'generate_signals',lambda *a,**k:[])
        for _ in range(5):assert Worker(lab).run_once()
        ready=clone_authored(lab,root/'ready')
        assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    return dict(complete=lab,ready=ready,study_id=study['id'],job_id=job['id'])


@pytest.fixture(scope='module')
def positive_originals(tmp_path_factory):
    fixture_spec=importlib.util.spec_from_file_location('owned_boundary_positive',Path(__file__).with_name('research-qualification-positive-accounts.py'))
    positive=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(positive)
    with pytest.MonkeyPatch.context() as patch:
        lab,study,arms=positive.build_positive_accounts(tmp_path_factory.mktemp('authored-positive-owned'),patch)
        job=flow.create_qualification(lab,study['id'])
    return dict(ready=lab,study_id=study['id'],job_id=job['id'],arms=arms)


def forbidden(*args,**kwargs):raise AssertionError('Original saved qualification cannot regenerate financial accounts or qualification math.')


@pytest.mark.parametrize('fault',['preliminary_missing','preliminary_changed','preliminary_event_missing','preliminary_event_duplicate',
    'preliminary_start_missing','preliminary_computation_missing','preliminary_checkpoint_missing','preliminary_attempt_changed',
    'result_missing','result_changed','result_event_missing','result_event_duplicate','result_computation_missing',
    'freeze_missing','freeze_changed','freeze_event_missing','freeze_event_duplicate','dependency_missing','dependency_unknown','source_changed'])
def test_saved_inspection_refuses_original_damage_without_new_math(originals,tmp_path,monkeypatch,fault):
    lab=clone_authored(originals['complete'],tmp_path);jid=originals['job_id'];sid=originals['study_id']
    preliminary=flow._path(lab,jid,'preliminary');result=lab.output_path(jid)
    with lab.store.db() as db:
        if fault=='preliminary_missing':preliminary.unlink()
        elif fault=='preliminary_changed':preliminary.write_bytes(b'changed original')
        elif fault=='result_missing':result.unlink()
        elif fault=='result_changed':result.write_bytes(b'changed original')
        elif fault=='freeze_missing':db.execute('DELETE FROM funnel_candidate_freezes WHERE study_id=?',(sid,))
        elif fault=='freeze_changed':db.execute("UPDATE funnel_candidate_freezes SET freeze=json_set(freeze,'$.candidate_ids',json('[\"not-original\"]')) WHERE study_id=?",(sid,))
        elif fault=='dependency_missing':db.execute("DELETE FROM funnel_dependencies WHERE parent_id=? AND role='arm:era_two'",(jid,))
        elif fault=='dependency_unknown':db.execute('INSERT INTO funnel_dependencies VALUES(?,?,?)',(jid,'unknown',jid))
        elif fault=='source_changed':
            child=db.execute("SELECT child_id FROM funnel_dependencies WHERE parent_id=? AND role='arm:era_two'",(jid,)).fetchone()[0]
            (lab.output_path(child).parent/'parts'/'000000.json.gz').write_bytes(b'changed original source')
        elif fault=='preliminary_attempt_changed':
            db.execute("UPDATE trial_attempts SET computed_sha256=? WHERE trial_id=(SELECT id FROM trial_plans WHERE job_id=? AND window='preliminary')",('0'*64,jid))
        else:
            if fault.startswith('freeze_event'):entity=sid;kind='funnel_candidates_frozen'
            elif fault.startswith('result_event'):entity=jid;kind='result_saved'
            elif fault.startswith('preliminary_event'):entity=jid;kind='funnel_preliminary_saved'
            else:
                phase='preliminary' if fault.startswith('preliminary') else 'report'
                kind='trial_computation_started' if 'start' in fault else 'trial_checkpoint_saved' if 'checkpoint' in fault else 'trial_computation_recorded'
                db.execute("DELETE FROM events WHERE entity_id=? AND kind=? AND json_extract(details,'$.window')=?",(jid,kind,phase));entity=None
            if entity is not None:
                if fault.endswith('duplicate'):
                    value=json.loads(db.execute('SELECT details FROM events WHERE entity_id=? AND kind=?',(entity,kind)).fetchone()[0]);lab.store.event(kind,entity,value,db)
                else:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(entity,kind))
        before=db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]
    monkeypatch.setattr(lab,'evaluate',forbidden);monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    monkeypatch.setattr(flow,'qualification_snapshot',forbidden)
    with pytest.raises(StateError):flow.inspect_qualification(lab,jid)
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM trial_attempts').fetchone()[0]==before


@pytest.mark.parametrize('phase',['preliminary','report'])
def test_real_shutdown_inside_publication_transaction_rolls_back_original_events_and_freeze(originals,tmp_path,monkeypatch,phase):
    lab=clone_authored(originals['ready'],tmp_path);jid=originals['job_id'];stop=Event();worker=Worker(lab,shutdown=stop);event=lab.store.event
    kind='funnel_preliminary_saved' if phase=='preliminary' else 'funnel_candidates_frozen'
    def stop_inside(kind_now,entity,details,db=None):
        value=event(kind_now,entity,details,db)
        if kind_now==kind:stop.set()
        return value
    monkeypatch.setattr(lab.store,'event',stop_inside)
    assert worker.run_once() and lab.store.job(jid)['status']=='queued'
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM events WHERE entity_id=? AND kind=?',(jid,'funnel_preliminary_saved' if phase=='preliminary' else 'result_saved')).fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM funnel_candidate_freezes').fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='funnel_candidates_frozen'").fetchone()[0]==0


def test_source_changed_during_derived_view_build_cannot_complete_qualification(originals,tmp_path,monkeypatch):
    lab=clone_authored(originals['ready'],tmp_path);jid=originals['job_id'];build=lab.result_index.build
    with lab.store.db() as db:child=db.execute("SELECT child_id FROM funnel_dependencies WHERE parent_id=? AND role='arm:era_two'",(jid,)).fetchone()[0]
    def mutate_after_view(*args,**kwargs):
        value=build(*args,**kwargs);(lab.output_path(child).parent/'parts'/'000000.json.gz').write_bytes(b'changed source after view build');return value
    monkeypatch.setattr(lab.result_index,'build',mutate_after_view)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='failed'
    with pytest.raises(StateError):flow.inspect_qualification(lab,jid)


def test_preliminary_committed_shutdown_reuses_original_reduction_without_new_accounts(originals,tmp_path,monkeypatch):
    lab=clone_authored(originals['ready'],tmp_path);jid=originals['job_id'];stop=Event();worker=Worker(lab,shutdown=stop);publish=flow._publish
    def after_commit(*args,**kwargs):
        digest=publish(*args,**kwargs)
        if args[2]=='preliminary':stop.set()
        return digest
    with monkeypatch.context() as patch:
        patch.setattr(flow,'_publish',after_commit)
        assert worker.run_once() and lab.store.job(jid)['status']=='queued'
    preliminary=flow._path(lab,jid,'preliminary').read_bytes()
    monkeypatch.setattr(lab,'evaluate',forbidden)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
    assert flow._path(lab,jid,'preliminary').read_bytes()==preliminary
    with lab.store.db() as db:
        assert db.execute("SELECT attempts FROM trial_plans WHERE job_id=? AND window='preliminary'",(jid,)).fetchone()[0]==1
        assert db.execute("SELECT MAX(attempts) FROM trial_plans WHERE role='strategy'").fetchone()[0]==1


@pytest.mark.parametrize('action',['cancel','reclaim','source_change'])
def test_child_reservation_guard_refuses_late_cancel_reclaimed_owner_or_changed_other_arm(positive_originals,tmp_path,monkeypatch,action):
    from backend.lab import trade_twin_jobs
    lab=clone_authored(positive_originals['ready'],tmp_path);jid=positive_originals['job_id'];worker=Worker(lab);read=trade_twin_jobs.read_saved_source
    def after_source(*args,**kwargs):
        result=read(*args,**kwargs)
        if action=='cancel':lab.store.cancel(jid)
        elif action=='reclaim':
            lab.store.release(jid,worker.owner);claimed=lab.store.claim('new-authored-owner');assert claimed['id']==jid
        else:
            child=positive_originals['arms']['era_two'];(lab.output_path(child).parent/'parts'/'000000.json.gz').write_bytes(b'changed other original arm')
        return result
    monkeypatch.setattr(trade_twin_jobs,'read_saved_source',after_source)
    assert worker.run_once()
    current=lab.store.job(jid)
    assert current['status']==('canceled' if action=='cancel' else 'running' if action=='reclaim' else 'failed')
    if action=='reclaim':assert current['owner']=='new-authored-owner'
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='trade_twins'").fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM funnel_candidate_freezes').fetchone()[0]==0


def test_saved_source_witnesses_are_complete_and_do_not_authorize_a_supplied_certificate(originals,tmp_path,monkeypatch):
    lab=clone_authored(originals['complete'],tmp_path);saved=flow.inspect_qualification(lab,originals['job_id']);report=saved['report']
    monkeypatch.setattr(lab,'evaluate',forbidden)
    first=report['source_authority']['arms']['primary_discovery'];first['parts']=first['parts'][:1]
    with pytest.raises(StateError):verify_snapshot(lab,report)
