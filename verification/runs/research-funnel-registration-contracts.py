"""Actual frozen two-instrument/era registration before any numerical outcomes."""
import importlib,importlib.util,json,time,uuid
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy,identity
from backend.lab.data import save_dataset
from backend.lab.research import ResearchError
from backend.lab.research_funnel import FunnelStudy
from backend.lab.service import Lab
from backend.lab.store import StateError
from backend.lab.worker import Worker
from backend.lab.research import core_hash


def test_funnel_registration_workflow_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_funnel_registration') is not None,'Complete two-instrument funnel registration is not implemented.'


@pytest.fixture
def registration():return importlib.import_module('backend.lab.research_funnel_registration')


@pytest.fixture
def inputs(tmp_path):
    lab=Lab(tmp_path)
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']],ignore_index=True)
    primary=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Funnel primary registration fixture',corporate_actions_complete=True))
    other=frame.copy();other['symbol']='QQQ'
    replica=save_dataset(lab.datasets_root,other,dict(input_kind='synthetic',provider='Funnel replica registration fixture',corporate_actions_complete=True))
    spec=FunnelStudy(name='Original multi-axis registration',dataset_id=primary['id'],replication_dataset_id=replica['id'],primary_symbol='SPY',replication_symbol='QQQ',
        discovery=dict(start='2026-11-02',end='2026-11-03'),era_one=dict(start='2026-11-02',end='2026-11-02'),era_two=dict(start='2026-11-03',end='2026-11-03'),
        validation=dict(start='2026-11-04',end='2026-11-04'),holdout=dict(start='2026-11-05',end='2026-11-06'),configurations=[Strategy(timeframe='1m'),Strategy(timeframe='5m')])
    return lab,spec,primary,replica


def test_registration_freezes_all_axes_and_two_all_version_final_arms_without_outcomes(registration,inputs,monkeypatch):
    lab,spec,primary,replica=inputs
    def forbidden(*a,**k):raise AssertionError('Registration must not read prices, generate signals or execute accounts.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    saved=registration.register_funnel(lab,spec);frozen=saved['spec']
    assert saved['status']=='registered' and frozen['funnel_version']==1
    assert frozen['source_video']=='https://www.youtube.com/watch?v=z97PnFIPoFg'
    assert frozen['symbols']==['QQQ','SPY']
    assert frozen['configuration_universe_hash']==identity([c.model_dump(mode='json') for c in spec.configurations])
    assert set(frozen['development_arms'])=={'primary_discovery','era_one','era_two','instrument_replication','chronological_validation'}
    assert frozen['development_arms']['instrument_replication']['role']=='instrument_discovery_replication_not_untouched_validation'
    assert frozen['development_arms']['instrument_replication']['dataset_context']['dataset_id']==replica['id']
    assert frozen['development_arms']['primary_discovery']['dataset_context']['dataset_id']==primary['id']
    assert set(frozen['final_arms'])=={'primary_final','replication_final'}
    assert all(a['configuration_scope']=='all_frozen_versions_with_candidate_and_family_flags' for a in frozen['final_arms'].values())
    assert all(a['start']=='2026-11-05' and a['end']=='2026-11-06' for a in frozen['final_arms'].values())
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM trial_plans').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==0
    for symbol in ['SPY','QQQ']:
        with pytest.raises(ResearchError,match='protected final'):lab.guard.access([symbol],'2026-11-05','2026-11-06','forbidden',record=False)
    spec.configurations[0].direction='long'
    assert lab.guard.study(saved['id'])['spec']==frozen
    with pytest.raises(ResearchError,match='funnel'):lab.screen(saved['id'])
    with pytest.raises(ResearchError,match='funnel'):lab.final(saved['id'])


@pytest.mark.parametrize('symbol',['SPY','QQQ'])
def test_either_previously_seen_final_instrument_refuses_registration(registration,inputs,symbol):
    lab,spec,*_=inputs
    lab.guard.access([symbol],'2026-11-05','2026-11-05','earlier_exploration')
    with pytest.raises(ResearchError,match='already been viewed'):registration.register_funnel(lab,spec)
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM studies').fetchone()[0]==0


@pytest.mark.parametrize('fault',['primary_absent','replica_absent','replica_short_history'])
def test_original_instrument_and_full_final_history_are_required_before_registration(registration,inputs,fault):
    lab,spec,primary,replica=inputs
    if fault=='primary_absent':spec.primary_symbol='IWM'
    elif fault=='replica_absent':spec.replication_symbol='IWM'
    else:
        frame=minute_frame('2026-11-02');frame['symbol']='QQQ'
        short=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored too-short replica',corporate_actions_complete=True))
        spec.replication_dataset_id=short['id']
    with pytest.raises((ResearchError,ValueError)):registration.register_funnel(lab,spec)
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM studies').fetchone()[0]==0


def test_registration_requires_complete_funnel_contract_not_a_basic_study_or_dict(registration,inputs):
    lab,spec,*_=inputs
    with pytest.raises(ResearchError,match='complete research-funnel'):registration.register_funnel(lab,spec.model_dump(mode='json'))


def test_shared_dataset_is_explicitly_resolved_and_modified_thresholds_are_labeled(registration,inputs):
    lab,spec,*_=inputs
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']],ignore_index=True)
    second=frame.copy();second['symbol']='QQQ'
    shared=save_dataset(lab.datasets_root,pd.concat([frame,second],ignore_index=True),dict(input_kind='synthetic',provider='Authored shared-instrument manifest',corporate_actions_complete=True))
    spec.dataset_id=shared['id'];spec.replication_dataset_id=None;spec.family_minimum_sharpe=.4
    frozen=registration.register_funnel(lab,spec)['spec']
    assert frozen['replication_dataset_id']==shared['id']
    assert frozen['dataset_context']==frozen['replication_dataset_context']
    assert frozen['source_thresholds_unmodified'] is False and frozen['qualification_policy']['family']['minimum_sharpe']==.4
    assert frozen['host_engine_parity_verified'] is False


def test_protected_registration_scope_cannot_shrink_original_manifest(inputs):
    lab,spec,primary,*_=inputs
    with pytest.raises(ResearchError,match='cannot omit'):lab.guard.register(spec,primary,protected_symbols=['QQQ'])
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM studies').fetchone()[0]==0


def test_replica_overlap_with_an_existing_basic_final_scope_refuses_funnel(registration,inputs):
    from backend.lab.models import Study
    lab,spec,primary,replica=inputs
    earlier=Study(name='Existing protected replica',dataset_id=replica['id'],discovery=spec.discovery,validation=spec.validation,holdout=spec.holdout,configurations=spec.configurations)
    lab.register_study(earlier)
    with pytest.raises(ResearchError,match='overlap'):registration.register_funnel(lab,spec)
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM studies').fetchone()[0]==1


@pytest.mark.parametrize('kind',['screen','final'])
def test_direct_basic_queue_and_injected_worker_cannot_unlock_a_funnel(registration,inputs,monkeypatch,kind):
    lab,spec,*_=inputs;study=registration.register_funnel(lab,spec);sid=study['id']
    with lab.store.db() as db:
        db.execute('UPDATE studies SET status=? WHERE id=?',('registered' if kind=='screen' else 'screened',sid))
    payload=dict(study_id=sid,core_hash=core_hash())
    with pytest.raises(StateError,match='funnel'):lab.store.create_job(kind,payload)
    # An authored negative control bypasses queue creation, not its worker fences.
    # No numeric outcome or final access is fabricated.
    jid=uuid.uuid4().hex;now=time.time()
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,kind,json.dumps(payload),now,now))
        lab.store._trials.freeze(dict(id=jid,kind=kind,payload=payload),db)
        lab.store._input_index.add(db,jid,payload);lab.store.event('job_created',jid,dict(kind=kind),db);db.execute('COMMIT')
    def forbidden(*a,**k):raise AssertionError('A basic-path bypass must not read funnel prices.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='failed'
    assert 'funnel' in lab.store.job(jid)['error']
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(sid,)).fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==0
