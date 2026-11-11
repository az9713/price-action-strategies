"""Original reservation and frozen Monte Carlo occurrence contracts."""
import importlib
import importlib.util
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.lab.config import canonical, identity
from backend.lab.store import StateError
from test_trade_twin_source import original


def test_durable_trade_twin_reservation_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_jobs') is not None, 'Original trade-twin reservation is not implemented.'


@pytest.fixture
def jobs():
    return importlib.import_module('backend.lab.trade_twin_jobs')


def test_original_reservation_freezes_both_complete_policies_before_candidate_work(original, jobs, monkeypatch):
    lab, parent, report = original
    def forbidden(*args, **kwargs):
        raise AssertionError('Reservation cannot regenerate signals or financial accounts.')
    monkeypatch.setattr(lab, 'evaluate', forbidden)
    monkeypatch.setattr('backend.lab.service.generate_signals', forbidden)
    child = jobs.create(lab, parent['id'])
    payload = child['payload']
    assert child['kind'] == 'trade_twins' and child['status'] == 'queued'
    assert payload['seed'] == parent['payload']['seed']
    for key in ['dataset_id', 'dataset_manifest_hash', 'costs', 'portfolio', 'start', 'end']:
        assert payload[key] == parent['payload'][key]
    assert payload['strategy'] == parent['payload']['strategy']
    assert 'sampling' not in payload
    assert payload['twin_parent']['job_id'] == parent['id']
    assert payload['twin_parent']['part'] == 0
    assert payload['source']['report_hash'] == identity(report)
    assert payload['source']['source_count'] == len(report['trades'])
    assert payload['twin_protocol']['sets_per_policy'] == 10000
    assert payload['twin_protocol']['policies'] == ['barrier_capped_elapsed_v1', 'fixed_elapsed_v1']
    with lab.store.db() as db:
        rows = list(db.execute('SELECT part,window,role,state,attempts FROM trial_plans WHERE job_id=? ORDER BY part,window', (child['id'],)))
        assert len(rows) == 20001 and all(r['state'] == 'planned' and r['attempts'] == 0 for r in rows)
        for policy in payload['twin_protocol']['policies']:
            assert [r['part'] for r in rows if r['window'] == policy] == list(range(10000))
            assert {r['role'] for r in rows if r['window'] == policy} == {'trade_twin_set'}
        assert [(r['part'], r['role']) for r in rows if r['window'] == 'prepare'] == [(0, 'trade_twin_preparation')]
    lab.store.verify_trial_plan(child['id'])
    assert not lab.output_path(child['id']).exists()
    status = lab.store.job_status(child['id'])
    assert status['payload']['twin_parent'] == payload['twin_parent']
    assert len(canonical(status).encode()) < 24576


def test_original_reservation_is_atomic_across_concurrent_and_canceled_requests(original, jobs):
    lab, parent, _ = original
    with ThreadPoolExecutor(max_workers=2) as pool:
        children = list(pool.map(lambda _: jobs.create(lab, parent['id']), range(2)))
    assert children[0]['id'] == children[1]['id']
    child = children[0]
    lab.store.cancel(child['id'])
    assert jobs.create(lab, parent['id'])['id'] == child['id']
    assert len([e for e in lab.store.events(parent['id']) if e['kind'] == 'trade_twins_frozen']) == 1
    assert len([e for e in lab.store.events(child['id']) if e['kind'] == 'trial_plan_frozen']) == 1


@pytest.mark.parametrize('part', [True, False, -1, 0.0, '0', None, 1])
def test_selected_source_ordinal_is_strict_and_missing_accounts_create_no_child(original, jobs, part):
    lab, parent, _ = original
    with pytest.raises((StateError, ValueError)):
        jobs.create(lab, parent['id'], part)
    assert len(lab.store.jobs()) == 1


@pytest.mark.parametrize('damage', ['link', 'event', 'child', 'inputs', 'plan', 'reverse_index', 'original_index', 'event_index', 'event_details', 'child_payload'])
def test_damaged_original_reservations_refuse_replacement(original, jobs, damage):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    with lab.store.db() as db:
        if damage == 'link':
            db.execute('DELETE FROM trade_twin_links WHERE parent_id=?', (parent['id'],))
        elif damage == 'event':
            db.execute("DELETE FROM events WHERE entity_id=? AND kind='trade_twins_frozen'", (parent['id'],))
        elif damage == 'child':
            db.execute("UPDATE jobs SET kind='experiment' WHERE id=?", (child['id'],))
        elif damage == 'inputs':
            db.execute('DELETE FROM job_input_index WHERE job_id=?', (child['id'],))
        elif damage == 'plan':
            db.execute('DELETE FROM trial_plans WHERE job_id=? AND part=9999', (child['id'],))
        elif damage == 'reverse_index':
            db.execute('DROP INDEX trade_twin_child_parent_index')
        elif damage == 'original_index':
            db.execute('DROP INDEX trade_twin_original_parent_index')
        elif damage == 'event_index':
            db.execute('DROP INDEX trade_twin_parent_event_index')
        elif damage == 'event_details':
            db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='trade_twins_frozen'", (parent['id'],))
        else:
            payload = dict(child['payload'], seed=123456)
            db.execute('UPDATE jobs SET payload=? WHERE id=?', (canonical(payload), child['id']))
    before = len(lab.store.jobs())
    with pytest.raises(StateError):
        jobs.create(lab, parent['id'])
    assert len(lab.store.jobs()) == before


def test_parent_change_between_read_and_reservation_cannot_freeze_a_child(original, jobs, monkeypatch):
    lab, parent, _ = original
    reader = jobs.read_saved_source
    def changed(*args, **kwargs):
        result = reader(*args, **kwargs)
        with lab.store.db() as db:
            db.execute("UPDATE jobs SET status='failed' WHERE id=?", (parent['id'],))
        return result
    monkeypatch.setattr(jobs, 'read_saved_source', changed)
    with pytest.raises(StateError):
        jobs.create(lab, parent['id'])
    assert len(lab.store.jobs()) == 1


def test_cancel_before_reservation_and_raw_unbound_job_creation_are_refused(original, jobs):
    lab, parent, _ = original
    with pytest.raises(InterruptedError):
        jobs.create(lab, parent['id'], cancel=lambda: True)
    with pytest.raises(StateError):
        lab.store.create_job('trade_twins', {})
    assert len(lab.store.jobs()) == 1

@pytest.mark.parametrize('change', ['parent_status', 'protected_scope'])
def test_revalidation_rechecks_late_parent_state_and_protected_scope(original, jobs, monkeypatch, change):
    from backend.lab.research import ResearchError
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    reader = jobs.read_saved_source
    scopes = lab.guard.protected_scopes
    state = {'changed': False}
    def protected(db):
        yield from scopes(db)
        if state['changed'] and change == 'protected_scope':
            yield {'id': 'late', 'status': 'registered'}, dict(symbols=['SPY'], holdout={'start': parent['payload']['start'], 'end': parent['payload']['end']})
    def late(*args, **kwargs):
        result = reader(*args, **kwargs)
        if change == 'parent_status':
            with lab.store.db() as db:
                db.execute("UPDATE jobs SET status='failed' WHERE id=?", (parent['id'],))
        state['changed'] = True
        return result
    monkeypatch.setattr(lab.guard, 'protected_scopes', protected)
    monkeypatch.setattr(jobs, 'read_saved_source', late)
    with pytest.raises((StateError, ResearchError)):
        jobs.verify_child(lab, child)

def test_complete_original_child_revalidation_returns_unchanged_whole_source(original, jobs):
    lab, parent, report = original
    child = jobs.create(lab, parent['id'])
    before = len(lab.store.events(child['id']))
    source = jobs.verify_child(lab, child)
    assert source['source_count'] == len(report['trades'])
    assert source['authority_hash'] == child['payload']['twin_parent']['authority_hash']
    assert len(lab.store.events(child['id'])) == before
    assert jobs.create(lab, parent['id'])['id'] == child['id']


def test_selected_search_accounts_have_separate_original_reservations(original, jobs):
    from test_trade_twin_source import search_original
    lab, parent = search_original(original)
    first = jobs.create(lab, parent['id'], 0)
    second = jobs.create(lab, parent['id'], 1)
    assert first['id'] != second['id']
    for ordinal, child in enumerate((first, second)):
        assert child['payload']['strategy'] == parent['payload']['configurations'][ordinal]
        assert child['payload']['twin_parent']['part'] == ordinal
        assert jobs.verify_child(lab, child)['part'] == ordinal
        assert jobs.create(lab, parent['id'], ordinal)['id'] == child['id']


@pytest.mark.parametrize('boundary', ['after_freeze_cancel', 'before_link_event'])
def test_reservation_failure_rolls_back_job_occurrences_link_and_events(original, jobs, monkeypatch, boundary):
    lab, parent, _ = original
    state = {'cancel': False}
    freeze = lab.store._trials.freeze
    event = lab.store.event
    def freeze_then_cancel(*args, **kwargs):
        answer = freeze(*args, **kwargs)
        if boundary == 'after_freeze_cancel':
            state['cancel'] = True
        return answer
    def fail_event(kind, *args, **kwargs):
        if kind == 'trade_twins_frozen' and boundary == 'before_link_event':
            raise StateError('Injected original-link event failure.')
        return event(kind, *args, **kwargs)
    monkeypatch.setattr(lab.store._trials, 'freeze', freeze_then_cancel)
    monkeypatch.setattr(lab.store, 'event', fail_event)
    before = len(lab.store.events(parent['id']))
    with pytest.raises((InterruptedError, StateError)):
        jobs.create(lab, parent['id'], cancel=lambda: state['cancel'])
    assert len(lab.store.jobs()) == 1
    assert len(lab.store.events(parent['id'])) == before
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trade_twin_links').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM trial_plans').fetchone()[0] == 1


@pytest.mark.parametrize('damage', ['projection', 'projection_rehashed_parent', 'oversized_event', 'duplicate_event', 'erased_link_event_index', 'wrong_child_id', 'wrong_kind', 'wrong_payload', 'malformed_binding'])
def test_revalidation_refuses_original_and_rehashed_derived_metadata_faults(original, jobs, damage):
    from backend.lab.job_index import binding
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    with lab.store.db() as db:
        if damage == 'projection':
            db.execute("UPDATE job_input_index SET projection='{}' WHERE job_id=?", (child['id'],))
        elif damage == 'projection_rehashed_parent':
            row = dict(db.execute('SELECT * FROM job_input_index WHERE job_id=?', (child['id'],)).fetchone())
            projection = json.loads(row['projection'])
            projection['twin_parent']['authority_hash'] = 'f' * 64
            listed = json.loads(row['list_projection'])
            db.execute('UPDATE job_input_index SET projection=?,projection_sha256=? WHERE job_id=?',
                       (canonical(projection), binding(row['payload_sha256'], projection, listed, row['provenance']), child['id']))
        elif damage == 'oversized_event':
            details = dict(child_id=child['id'], **child['payload']['twin_parent'], padding='x' * 9000)
            db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='trade_twins_frozen'", (canonical(details), parent['id']))
        elif damage == 'duplicate_event':
            row = db.execute("SELECT * FROM events WHERE entity_id=? AND kind='trade_twins_frozen'", (parent['id'],)).fetchone()
            db.execute('INSERT INTO events(at,kind,entity_id,details) VALUES(?,?,?,?)', (row['at'], row['kind'], row['entity_id'], row['details']))
        elif damage == 'erased_link_event_index':
            db.execute('DELETE FROM trade_twin_links')
            db.execute("DELETE FROM events WHERE kind='trade_twins_frozen'")
            db.execute('DELETE FROM job_input_index WHERE job_id=?', (child['id'],))
        elif damage == 'wrong_child_id':
            child = dict(child, id='f' * 32)
        elif damage == 'wrong_kind':
            child = dict(child, kind='experiment')
        elif damage == 'wrong_payload':
            child = dict(child, payload=dict(child['payload'], seed=987))
        else:
            child = dict(child, payload={})
    with pytest.raises(StateError):
        jobs.verify_child(lab, child)
    if damage == 'erased_link_event_index':
        with pytest.raises(StateError):
            jobs.create(lab, parent['id'])
        assert len(lab.store.jobs()) == 2


@pytest.mark.parametrize('damage', ['manifest', 'prices', 'root', 'binding'])
def test_late_source_bytes_or_binding_changes_abort_reservation(original, jobs, monkeypatch, damage):
    lab, parent, _ = original
    reader = jobs.read_saved_source
    def changed(*args, **kwargs):
        source = reader(*args, **kwargs)
        if damage == 'manifest':
            path = lab.datasets_root / parent['payload']['dataset_id'] / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest['metadata']['late_change'] = True
            path.write_text(json.dumps(manifest))
        elif damage == 'binding':
            source['authority'] = dict(source['authority'], computed_sha256='f' * 64)
        else:
            path = (lab.datasets_root / parent['payload']['dataset_id'] / 'minutes.parquet') if damage == 'prices' else lab.output_path(parent['id'])
            path.write_bytes(path.read_bytes() + b'changed')
        return source
    monkeypatch.setattr(jobs, 'read_saved_source', changed)
    with pytest.raises(StateError):
        jobs.create(lab, parent['id'])
    assert len(lab.store.jobs()) == 1


def test_protocol_cannot_shrink_policy_cohort_or_use_boolean_version(original, jobs):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    for override in [dict(version=True), dict(sets_per_policy=9999), dict(policies=['fixed_elapsed_v1'])]:
        payload = dict(child['payload'], twin_protocol=child['payload']['twin_protocol'] | override)
        with pytest.raises(StateError):
            list(jobs.occurrences(payload))


def test_scope_and_original_state_transaction_helpers_refuse_unowned_reads(original):
    from backend.lab.research import ResearchError
    from backend.lab.trade_twin_source import _saved_state
    lab, parent, _ = original
    with lab.store.db() as db:
        with pytest.raises(ResearchError, match='transaction'):
            lab.guard.check_access(db, ['SPY'], parent['payload']['start'], parent['payload']['end'])
        with pytest.raises(StateError, match='transaction'):
            _saved_state(lab, parent['id'], 0, db=db)
        db.execute('BEGIN')
        with pytest.raises(ResearchError, match='reversed'):
            lab.guard.check_access(db, ['SPY'], '2026-11-05', '2026-11-04')

@pytest.mark.parametrize('damage', ['invalid_index_hash', 'invalid_list_projection', 'malformed_child_identity'])
def test_bounded_reservation_metadata_checks_refuse_without_decoding_large_jobs(original, jobs, damage):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    with lab.store.db() as db:
        if damage == 'invalid_index_hash':
            db.execute("UPDATE job_input_index SET projection_sha256=? WHERE job_id=?", ('f' * 64, child['id']))
        elif damage == 'invalid_list_projection':
            db.execute("UPDATE job_input_index SET list_projection='[]' WHERE job_id=?", (child['id'],))
        else:
            bad_id = 'G' * 32
            db.execute("INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)",
                       (bad_id, 'trade_twins', canonical(child['payload']), 1, 1))
            lab.store._input_index.add(db, bad_id, child['payload'])
    count = len(lab.store.jobs())
    with pytest.raises(StateError):
        jobs.create(lab, parent['id'])
    assert len(lab.store.jobs()) == count


def test_original_child_cannot_authorize_amended_expected_payload(original, jobs):
    lab, parent, _ = original
    child = jobs.create(lab, parent['id'])
    amended = dict(child['payload'], seed=999)
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        with pytest.raises(StateError, match='inputs changed'):
            jobs._existing(lab.store, db, amended)


def test_late_selected_original_sidecar_change_cannot_freeze_source(original, jobs, monkeypatch):
    from test_trade_twin_source import search_original
    lab, parent = search_original(original)
    reader = jobs.read_saved_source
    def late(*args, **kwargs):
        source = reader(*args, **kwargs)
        sidecar = (lab.output_path(parent['id']).parent / 'parts' / '000000.json.gz').with_suffix('.sha256.json')
        sidecar.write_text(canonical({'sha256': 'f' * 64}))
        return source
    monkeypatch.setattr(jobs, 'read_saved_source', late)
    with pytest.raises(StateError):
        jobs.create(lab, parent['id'])
    assert len(lab.store.jobs()) == 2
