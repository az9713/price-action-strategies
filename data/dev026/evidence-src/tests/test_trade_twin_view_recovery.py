"""Actual deaths and original ownership controls through the full empty lifecycle.

These cases deliberately execute zero financial sets. Actual20k positive work is
verified separately; this suite exercises the same publication/recovery path.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import zipfile

import pytest
from conftest import minute_frame
from backend.lab import service, trade_twin_jobs as jobs
from backend.lab.data import save_dataset
from backend.lab.models import Experiment
from backend.lab.service import Lab
from backend.lab.store import StateError
from backend.lab.worker import Worker
from backend.lab.trade_twin_views import sets_page, export_archive
from trade_twin_view_death_child import BOUNDARIES, PUBLIC_BOUNDARIES, install, original_state


@pytest.fixture
def empty_source(tmp_path, monkeypatch):
    lab = Lab(tmp_path)
    dataset = save_dataset(lab.datasets_root, minute_frame('2026-11-04'),
        dict(input_kind='synthetic', provider='Authored view publication lifecycle', corporate_actions_complete=True))
    monkeypatch.setattr(service, 'generate_signals', lambda *a, **k: [])
    parent = lab.create_experiment(Experiment(dataset_id=dataset['id'], start='2026-11-04', end='2026-11-04'))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status'] == 'completed'
    parent_hash = hashlib.sha256(lab.output_path(parent['id']).read_bytes()).hexdigest()
    child = jobs.create(lab, parent['id'])
    return lab, parent, child, parent_hash


def financial_forbidden(monkeypatch, lab):
    def no_work(*args, **kwargs):
        raise AssertionError('Resumed empty source must not regenerate prices/signals or execute finance.')
    monkeypatch.setattr(service, 'generate_signals', no_work)
    monkeypatch.setattr(lab, '_evaluation_input', no_work)
    monkeypatch.setattr('backend.lab.trade_twin_parts.execute_twin', no_work)


def assert_boundary(marker, boundary):
    kinds = [e['kind'] for e in marker['events']]
    committed = boundary in {'after_root_commit', 'after_view_event', 'after_generic_view', 'inside_view_transaction'}
    assert kinds.count('result_saved') == int(committed)
    assert kinds.count('twin_financial_manifest_saved') == int(committed)
    assert kinds.count('trade_twin_view_saved') == int(boundary in {'after_view_event', 'after_generic_view'})
    assert kinds.count('twin_preparation_sealed') == 1
    assert bool(marker['root_sha256']) == (committed or boundary == 'inside_root_transaction')
    assert any(path.startswith('views/view-') and path.endswith('.sqlite3') for path in marker['files'])
    assert any(path.endswith('.result.json.gz') for path in marker['files']) == (boundary == 'after_root_temp')


def verify_completed(lab, parent, child, parent_hash, before):
    jid = child['id']
    assert lab.store.job(jid)['status'] == 'completed'
    assert jobs.create(lab, parent['id'])['id'] == jid
    state = original_state(lab, jid)
    assert sum(e['kind'] == 'result_saved' for e in state['events']) == 1
    assert sum(e['kind'] == 'twin_financial_manifest_saved' for e in state['events']) == 1
    assert sum(e['kind'] == 'twin_preparation_sealed' for e in state['events']) == 1
    for name, digest in before['files'].items():
        assert state['files'][name] == digest, ('Lost/overwritten original or orphan', name)
    if before['root_sha256']:
        if any(e['kind'] == 'result_saved' for e in before['events']):
            assert state['root_sha256'] == before['root_sha256']
        else:
            # A renamed file without the original committed event is an orphan.
            # Retry preserves those exact bytes, then publishes fresh authority.
            assert state['files']['orphans/result-'+before['root_sha256']+'.json.gz'] == before['root_sha256']
    assert hashlib.sha256(lab.output_path(parent['id']).read_bytes()).hexdigest() == parent_hash
    report = lab.report(jid)
    assert not report['comparison_eligible'] and report['financial_occurrences'] == 0
    assert all(s['state'] == 'ineligible' and s['observed_sets'] == 0 for s in report['summaries'].values())
    with lab.store.db() as db:
        row = dict(db.execute("SELECT attempts,reuses,state FROM trial_plans WHERE job_id=? AND window='prepare'", (jid,)).fetchone())
        assert row == dict(attempts=1, reuses=1, state='completed')
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='not_generated'", (jid,)).fetchone()[0] == 20000
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans p ON a.trial_id=p.id WHERE p.job_id=? AND p.role='trade_twin_set'", (jid,)).fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0] == 2
    for policy in ['barrier_capped_elapsed_v1', 'fixed_elapsed_v1']:
        page = sets_page(lab, jid, policy)
        assert page['rows'] == [] and page['pagination']['total'] == 0
    archive = export_archive(lab, jid)
    with zipfile.ZipFile(archive) as saved:
        assert saved.testzip() is None
        done = json.loads(saved.read('COMPLETE.json'))
        assert done['financial_occurrences'] == done['unique_books'] == 0
        assert done['original_trials'] == 20001
    assert state['root_sha256'] == original_state(lab, jid)['root_sha256']
    return dict(preparation=row, final_root_sha256=state['root_sha256'],
                original_and_orphan_files_preserved=len(before['files']),
                financial_sets_executed=0, frozen_not_generated_sets=20000,
                full_export_verified=True, main_application_touched=False)


def evidence(name, value):
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR']) / (name+'.json')).write_text(json.dumps(value, indent=2), encoding='utf-8')


@pytest.mark.parametrize('boundary,exit_code', list(BOUNDARIES.items()))
def test_actual_interpreter_death_recovers_original_publication_without_financial_rerun(empty_source, monkeypatch, boundary, exit_code):
    lab, parent, child, parent_hash = empty_source
    marker = lab.root / ('death-'+boundary+'.json')
    child_script = Path(__file__).with_name('trade_twin_view_death_child.py')
    result = subprocess.run([sys.executable, str(child_script), str(lab.root), child['id'], boundary, str(marker)],
                            capture_output=True, text=True, timeout=90)
    assert result.returncode == exit_code, (result.stdout, result.stderr)
    before = json.loads(marker.read_text(encoding='utf-8'))
    assert before['boundary'] == boundary and before['job_status'] == 'running'
    assert_boundary(before, boundary)
    # The process is now proven dead. Advance only its lease deadline; Store.claim
    # performs the real recovery transition and records lease_recovered.
    with lab.store.db() as db:
        db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (child['id'],))
    financial_forbidden(monkeypatch, lab)
    assert Worker(lab).run_once()
    verified = verify_completed(lab, parent, child, parent_hash, before)
    assert sum(e['kind'] == 'lease_recovered' for e in lab.store.events(child['id'])) == 1
    evidence('view-death-'+boundary, verified | dict(boundary=boundary, actual_subprocess_exit_code=result.returncode,
             lease_deadline_advanced_only_after_process_exit=True, boundary_state=before))


@pytest.mark.parametrize('boundary', PUBLIC_BOUNDARIES)
@pytest.mark.parametrize('control', ['cancel', 'shutdown', 'ownership_loss'])
def test_publication_cancel_shutdown_and_stale_owner_cannot_finish_or_publish_after_fence(empty_source, monkeypatch, boundary, control):
    lab, parent, child, parent_hash = empty_source
    worker = Worker(lab)
    recorded = []
    def interrupt():
        before = original_state(lab, child['id'])
        assert_boundary(before, boundary)
        recorded.append(before)
        if control == 'cancel':
            lab.store.cancel(child['id'])
        elif control == 'shutdown':
            worker.shutdown.set()
        else:
            with lab.store.db() as db:
                db.execute('UPDATE jobs SET lease_until=0 WHERE id=?', (child['id'],))
            claimed = lab.store.claim('authored-replacement-owner')
            assert claimed['id'] == child['id']
    with monkeypatch.context() as hooks:
        fired = install(hooks, lab, child['id'], boundary, interrupt)
        assert worker.run_once() and fired == [True] and len(recorded) == 1
    before = recorded[0]
    current = original_state(lab, child['id'])
    assert current['events'] == before['events'], 'Canceled/stale owner published additional evidence after the authored fence.'
    assert current['root_sha256'] == before['root_sha256']
    status = lab.store.job(child['id'])['status']
    assert status == {'cancel':'canceled', 'shutdown':'queued', 'ownership_loss':'running'}[control]
    with pytest.raises(StateError):
        sets_page(lab, child['id'], 'barrier_capped_elapsed_v1')
    if control == 'cancel':
        lab.store.resume(child['id'])
    elif control == 'ownership_loss':
        lab.store.release(child['id'], 'authored-replacement-owner')
    financial_forbidden(monkeypatch, lab)
    assert Worker(lab).run_once()
    verified = verify_completed(lab, parent, child, parent_hash, before)
    evidence('view-control-'+control+'-'+boundary, verified | dict(boundary=boundary, control=control,
             intermediate_status=status, no_publication_after_control=True, boundary_state=before))


@pytest.mark.parametrize('boundary', ['inside_root_transaction', 'inside_view_transaction'])
def test_shutdown_inside_publication_transaction_rolls_back_events_and_recovers_original_files(empty_source, monkeypatch, boundary):
    lab, parent, child, parent_hash = empty_source
    worker = Worker(lab)
    recorded = []
    def interrupt():
        recorded.append(original_state(lab, child['id']))
        assert_boundary(recorded[-1], boundary)
        # An asynchronous shutdown flag does not request a second SQLite writer
        # while the original worker owns this transaction.
        worker.shutdown.set()
    with monkeypatch.context() as hooks:
        fired = install(hooks, lab, child['id'], boundary, interrupt)
        assert worker.run_once() and fired == [True]
    assert lab.store.job(child['id'])['status'] == 'queued'
    before = recorded[0]
    assert original_state(lab, child['id']) == before
    financial_forbidden(monkeypatch, lab)
    assert Worker(lab).run_once()
    verified = verify_completed(lab, parent, child, parent_hash, before)
    evidence('view-transaction-shutdown-'+boundary, verified | dict(boundary=boundary,
             transaction_events_rolled_back=True, boundary_state=before))
