"""Owned, original preparation must seal before any twin financial computation."""
import importlib
import importlib.util
import pytest

from backend.lab import trade_twin_jobs as jobs
from backend.lab.store import StateError
from test_trade_twin_source import original


def test_owned_trade_twin_preparation_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_preparation') is not None, 'Durable original trade-twin preparation is not implemented.'


@pytest.fixture
def preparation():
    return importlib.import_module('backend.lab.trade_twin_preparation')


def claim(lab, child, owner):
    job = lab.store.claim(owner)
    assert job['id'] == child['id']
    return job


def test_original_plan_is_durably_sealed_before_any_candidate_finance_and_reused_on_resume(original, preparation, monkeypatch):
    lab, parent, report = original
    child = jobs.create(lab, parent['id'])
    owner = 'original-preparation-owner'
    claimed = claim(lab, child, owner)
    def forbidden(*args, **kwargs):
        raise AssertionError('Preparation cannot regenerate signals, accounts or twin P&L.')
    monkeypatch.setattr(lab, 'evaluate', forbidden)
    monkeypatch.setattr('backend.lab.service.generate_signals', forbidden)
    monkeypatch.setattr('backend.lab.trade_twin_execution.execute_twin', forbidden)
    first = preparation.prepare(lab, claimed, owner)
    assert len(first['plan'].sources) == len(report['trades'])
    assert first['sealed']['plan']['plan_hash'] == first['plan'].plan_hash
    assert first['sealed']['prospective_scope']['symbols'] == ['SPY']
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON t.id=a.trial_id WHERE t.job_id=? AND t.role='trade_twin_set'", (child['id'],)).fetchone()[0] == 0
    seals = [e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed']
    assert len(seals) == 1
    with lab.store.db() as db:
        saved = db.execute("SELECT state,artifact_sha256 FROM trial_plans WHERE job_id=? AND window='prepare'", (child['id'],)).fetchone()
        assert saved['state'] == 'checkpointed' and saved['artifact_sha256'] == seals[0]['details']['sha256']
    lab.store.release(child['id'], owner)
    second_owner = 'resumed-preparation-owner'
    second = preparation.prepare(lab, claim(lab, child, second_owner), second_owner)
    assert first['sealed'] == second['sealed']
    assert first['plan'].json() == second['plan'].json()
    assert len([e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed']) == 1
    with lab.store.db() as db:
        row = db.execute("SELECT attempts,reuses,state FROM trial_plans WHERE job_id=? AND window='prepare'", (child['id'],)).fetchone()
        assert row['attempts'] == 1 and row['reuses'] == 1 and row['state'] == 'checkpointed'
    lab.store.release(child['id'], second_owner)


@pytest.mark.parametrize('damage', ['missing_file', 'changed_file', 'missing_seal', 'changed_seal', 'missing_checkpoint', 'changed_trial'])
def test_sealed_original_preparation_corruption_cannot_be_repaired_or_replaced(original, preparation, damage):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'original'
    preparation.prepare(lab, claim(lab, child, owner), owner)
    seal = next(e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed')
    path = lab.output_path(child['id']).parent / 'twins/preparation' / seal['details']['filename']
    lab.store.release(child['id'], owner)
    if damage == 'missing_file':
        path.unlink()
    elif damage == 'changed_file':
        path.write_bytes(path.read_bytes() + b'changed')
    else:
        with lab.store.db() as db:
            if damage == 'missing_seal':
                db.execute("DELETE FROM events WHERE entity_id=? AND kind='twin_preparation_sealed'", (child['id'],))
            elif damage == 'changed_seal':
                db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='twin_preparation_sealed'", (child['id'],))
            elif damage == 'missing_checkpoint':
                db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'", (child['id'],))
            else:
                db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=? AND window='prepare'", ('f' * 64, child['id']))
    new_owner = 'resume'
    with pytest.raises(StateError):
        preparation.prepare(lab, claim(lab, child, new_owner), new_owner)
    assert len(list(path.parent.glob('attempt-*.json.gz'))) <= 1
    lab.store.release(child['id'], new_owner)


def test_nonowner_cannot_prepare_or_seal_a_plan(original, preparation):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'owner'
    claimed = claim(lab, child, owner)
    with pytest.raises(StateError):
        preparation.prepare(lab, claimed, 'stale-owner')
    assert not any(e['kind'] == 'twin_preparation_sealed' for e in lab.store.events(child['id']))
    lab.store.release(child['id'], owner)

def test_real_original_corporate_actions_are_bound_to_preparation(original, preparation):
    from dataclasses import asdict
    import pandas as pd
    from conftest import minute_frame
    from backend.lab.config import identity
    from backend.lab.data import Action, save_dataset
    from backend.lab.models import Experiment
    from backend.lab.worker import Worker
    from test_reference_execution import CFG, ZERO, ACCOUNT
    lab, _, _ = original
    actions = [Action('SPY', '2026-11-05', 'split', 2.)]
    frame = pd.concat([minute_frame('2026-11-04'), minute_frame('2026-11-05', close=[50.])], ignore_index=True)
    manifest = save_dataset(lab.datasets_root, frame, dict(input_kind='synthetic', provider='owned split preparation', corporate_actions_complete=True), actions)
    parent = lab.create_experiment(Experiment(dataset_id=manifest['id'], start='2026-11-04', end='2026-11-05', strategy=CFG, costs=ZERO, portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status'] == 'completed'
    child = jobs.create(lab, parent['id']);owner = 'action-owner'
    prepared = preparation.prepare(lab, claim(lab, child, owner), owner)
    assert prepared['sealed']['actions_hash'] == identity([asdict(a) for a in actions])
    assert prepared['actions'] == actions
    lab.store.release(child['id'], owner)


def test_closing_original_authority_failure_preserves_uncommitted_attempt_and_never_seals(original, preparation, monkeypatch):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'closing-failure'
    claimed = claim(lab, child, owner)
    verify = preparation.verify_child
    calls = []
    def changed(*args, **kwargs):
        calls.append(True)
        if len(calls) > 1:
            raise StateError('Injected closing original authority failure.')
        return verify(*args, **kwargs)
    monkeypatch.setattr(preparation, 'verify_child', changed)
    with pytest.raises(StateError, match='closing original'):
        preparation.prepare(lab, claimed, owner)
    assert not any(e['kind'] == 'twin_preparation_sealed' for e in lab.store.events(child['id']))
    assert len(list((lab.output_path(child['id']).parent / 'twins/preparation').glob('attempt-*.json.gz'))) == 1
    lab.store.release(child['id'], owner)
    with lab.store.db() as db:
        row = db.execute("SELECT state,artifact_sha256 FROM trial_plans WHERE job_id=? AND window='prepare'", (child['id'],)).fetchone()
        assert row['state'] == 'interrupted' and row['artifact_sha256'] is None

def test_atomic_seal_failure_retains_orphan_and_retry_uses_a_distinct_attempt(original, preparation, monkeypatch):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'before-seal'
    claimed = claim(lab, child, owner)
    event = lab.store.event
    def interrupted(kind, *args, **kwargs):
        if kind == 'twin_preparation_sealed':
            raise StateError('Injected atomic seal publication failure.')
        return event(kind, *args, **kwargs)
    monkeypatch.setattr(lab.store, 'event', interrupted)
    with pytest.raises(StateError, match='atomic seal'):
        preparation.prepare(lab, claimed, owner)
    assert not any(e['kind'] in {'twin_preparation_sealed', 'trial_checkpoint_saved'} for e in lab.store.events(child['id']))
    folder = lab.output_path(child['id']).parent / 'twins/preparation'
    original_orphan = (folder / 'attempt-000001.json.gz').read_bytes()
    lab.store.release(child['id'], owner)
    monkeypatch.setattr(lab.store, 'event', event)
    resumed = 'after-seal-failure'
    preparation.prepare(lab, claim(lab, child, resumed), resumed)
    assert (folder / 'attempt-000001.json.gz').read_bytes() == original_orphan
    assert (folder / 'attempt-000002.json.gz').is_file()
    seal = next(e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed')
    assert seal['details']['attempt'] == 2
    with lab.store.db() as db:
        attempts = list(db.execute("SELECT a.ordinal,a.state FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id WHERE t.job_id=? AND t.window='prepare' ORDER BY a.ordinal", (child['id'],)))
        assert [(a['ordinal'], a['state']) for a in attempts] == [(1, 'interrupted'), (2, 'checkpointed')]
    lab.store.release(child['id'], resumed)


def test_empty_original_cohort_has_explicit_ineligible_plan_and_no_candidate_read(original, preparation, monkeypatch):
    from backend.lab.models import Experiment
    from backend.lab.worker import Worker
    from test_reference_execution import CFG, ZERO, ACCOUNT
    lab, first, _ = original
    monkeypatch.setattr('backend.lab.service.generate_signals', lambda *a, **k: [])
    parent = lab.create_experiment(Experiment(dataset_id=first['payload']['dataset_id'], start=first['payload']['start'], end=first['payload']['end'], strategy=CFG, costs=ZERO, portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status'] == 'completed'
    child = jobs.create(lab, parent['id']);owner = 'empty'
    claimed = claim(lab, child, owner)
    def forbidden(*args, **kwargs):
        raise AssertionError('No candidate price window is needed for an empty whole cohort.')
    monkeypatch.setattr(lab, '_evaluation_input', forbidden)
    prepared = preparation.prepare(lab, claimed, owner)
    assert prepared['plan'].sources == () and not prepared['plan'].eligible
    assert prepared['sealed']['prospective_scope']['symbols'] == []
    assert prepared['regular'] is None
    lab.store.release(child['id'], owner)


def test_canceled_owner_and_unowned_checkpoint_transaction_cannot_publish(original, preparation):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'canceled'
    claimed = claim(lab, child, owner)
    lab.store.cancel(child['id'])
    with pytest.raises(InterruptedError):
        preparation.prepare(lab, claimed, owner)
    with lab.store.db() as db:
        with pytest.raises(StateError, match='transaction'):
            lab.store._trials.checkpoint_owned(db, child['id'], 0, 'prepare', owner, {}, 'f' * 64)
    assert not any(e['kind'] == 'twin_preparation_sealed' for e in lab.store.events(child['id']))
    lab.store.release(child['id'], owner)

@pytest.mark.parametrize('damage', ['duplicate_seal', 'oversized_seal', 'seal_before_checkpoint', 'attempt_record', 'compressed_limit', 'expanded_limit', 'content_digest', 'consistent_false_plan'])
def test_original_seal_bounds_order_attempt_and_rehashed_false_plan_are_refused(original, preparation, monkeypatch, damage):
    import gzip, json
    from backend.lab.config import canonical, identity
    from backend.lab.result_index import file_hash
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'seal-fault'
    preparation.prepare(lab, claim(lab, child, owner), owner)
    event = next(e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed')
    seal = event['details']
    path = lab.output_path(child['id']).parent / 'twins/preparation' / seal['filename']
    lab.store.release(child['id'], owner)
    with lab.store.db() as db:
        if damage == 'duplicate_seal':
            lab.store.event('twin_preparation_sealed', child['id'], seal, db)
        elif damage == 'oversized_seal':
            lab.store.event('oversized-marker', child['id'], {}, db)
            db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='twin_preparation_sealed'", (canonical(seal | {'padding': 'x' * 17000}), child['id']))
        elif damage == 'seal_before_checkpoint':
            db.execute("UPDATE events SET id=0 WHERE entity_id=? AND kind='twin_preparation_sealed'", (child['id'],))
        elif damage == 'attempt_record':
            db.execute("UPDATE trial_attempts SET state='failed' WHERE trial_id=?", (seal['trial_id'],))
        elif damage == 'compressed_limit':
            monkeypatch.setattr(preparation, 'MAX_PREPARED_BYTES', 1)
        elif damage == 'expanded_limit':
            monkeypatch.setattr(preparation, 'MAX_PREPARED_BYTES', path.stat().st_size + 1)
        else:
            value = json.loads(gzip.decompress(path.read_bytes()))
            value['plan']['moments'][0]['atr'] *= 2
            if damage == 'consistent_false_plan':
                value['plan']['plan_hash'] = identity({k: v for k, v in value['plan'].items() if k != 'plan_hash'})
            path.write_bytes(gzip.compress(canonical(value).encode(), mtime=0))
            changed = seal | dict(sha256=file_hash(path), plan_hash=value['plan']['plan_hash'])
            db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='twin_preparation_sealed'", (canonical(changed), child['id']))
            checkpoint = next(e for e in lab.store.events(child['id']) if e['kind'] == 'trial_checkpoint_saved')
            db.execute("UPDATE events SET details=? WHERE id=?", (canonical(checkpoint['details'] | {'sha256': changed['sha256']}), checkpoint['id']))
            db.execute('UPDATE trial_plans SET artifact_sha256=? WHERE id=?', (changed['sha256'], seal['trial_id']))
            db.execute('UPDATE trial_attempts SET artifact_sha256=? WHERE trial_id=?', (changed['sha256'], seal['trial_id']))
            if damage == 'consistent_false_plan':
                db.execute('UPDATE trial_plans SET computed_sha256=? WHERE id=?', (identity(value), seal['trial_id']))
                db.execute('UPDATE trial_attempts SET computed_sha256=? WHERE trial_id=?', (identity(value), seal['trial_id']))
    resumed = 'refused-seal'
    with pytest.raises(StateError):
        preparation.prepare(lab, claim(lab, child, resumed), resumed)
    lab.store.release(child['id'], resumed)


@pytest.mark.parametrize('boundary', ['warmup', 'serialization', 'existing_attempt'])
def test_preparation_scope_size_and_existing_attempt_never_produce_partial_seals(original, preparation, monkeypatch, boundary):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id']);owner = 'boundary'
    claimed = claim(lab, child, owner)
    if boundary == 'warmup':
        load = lab._evaluation_input
        def wrong(*args, **kwargs):
            manifest, regular, actions, _ = load(*args, **kwargs)
            return manifest, regular, actions, '1900-01-01'
        monkeypatch.setattr(lab, '_evaluation_input', wrong)
    elif boundary == 'serialization':
        monkeypatch.setattr(preparation, 'MAX_PREPARED_BYTES', 1)
    else:
        path = lab.output_path(child['id']).parent / 'twins/preparation/attempt-000001.json.gz'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'original uncommitted attempt')
    with pytest.raises(StateError):
        preparation.prepare(lab, claimed, owner)
    assert not any(e['kind'] == 'twin_preparation_sealed' for e in lab.store.events(child['id']))
    if boundary == 'existing_attempt':
        assert path.read_bytes() == b'original uncommitted attempt'
    lab.store.release(child['id'], owner)


@pytest.mark.parametrize('boundary,exit_code', [('after_file', 71), ('inside_checkpoint', 72), ('after_seal', 73)])
def test_actual_interpreter_death_preserves_original_attempts_and_committed_preparation(original, preparation, boundary, exit_code):
    import json, os, subprocess, sys
    from pathlib import Path
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    code = """
import os,sys
from pathlib import Path
from backend.lab.service import Lab
from backend.lab import trade_twin_preparation as p
lab=Lab(Path(sys.argv[1]));boundary=sys.argv[2];job=lab.store.claim('actual-death')
assert job['id']==sys.argv[3]
if boundary=='after_file':
    original=p.compressed_write
    def die(*a,**k):
        original(*a,**k);os._exit(71)
    p.compressed_write=die
elif boundary=='inside_checkpoint':
    original=lab.store._trials.checkpoint_owned
    def die(*a,**k):
        original(*a,**k);os._exit(72)
    lab.store._trials.checkpoint_owned=die
p.prepare(lab,job,'actual-death')
os._exit(73)
"""
    result = subprocess.run([sys.executable, '-c', code, str(lab.root), boundary, child['id']], capture_output=True, text=True, timeout=60)
    assert result.returncode == exit_code, result.stderr
    folder = lab.output_path(child['id']).parent / 'twins/preparation'
    orphan = (folder / 'attempt-000001.json.gz').read_bytes()
    before = [e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed']
    assert len(before) == (1 if boundary == 'after_seal' else 0)
    with lab.store.db() as db:
        db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (child['id'],))
    owner = 'actual-recovery'
    prepared = preparation.prepare(lab, claim(lab, child, owner), owner)
    assert prepared['plan'].sources
    assert (folder / 'attempt-000001.json.gz').read_bytes() == orphan
    with lab.store.db() as db:
        row = db.execute("SELECT attempts,reuses FROM trial_plans WHERE job_id=? AND window='prepare'", (child['id'],)).fetchone()
        assert row['attempts'] == (1 if boundary == 'after_seal' else 2)
        assert row['reuses'] == (1 if boundary == 'after_seal' else 0)
    assert len([e for e in lab.store.events(child['id']) if e['kind'] == 'twin_preparation_sealed']) == 1
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        evidence = dict(boundary=boundary, actual_subprocess_exit_code=result.returncode,
                        original_seal_survived=bool(before), recovered_attempts=row['attempts'],
                        recovered_reuses=row['reuses'], original_attempt_bytes_preserved=True,
                        financial_sets_executed=0, main_application_touched=False)
        (Path(os.environ['PA_EVIDENCE_RUN_DIR']) / ('preparation-death-' + boundary + '.json')).write_text(json.dumps(evidence, indent=2))
    lab.store.release(child['id'], owner)
