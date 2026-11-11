"""Additional actual-original and derived-view fault boundaries on synthetic copies."""
from contextlib import closing
from pathlib import Path
import gzip
import importlib.util
import json
import os
import sqlite3
import sys

import pytest
from backend.lab.config import canonical, identity
from backend.lab.service import Lab, compressed_write
from backend.lab.store import StateError
from backend.lab import trade_twin_views as views

ROOT = Path(__file__).resolve().parents[2]
RUN = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
spec = importlib.util.spec_from_file_location('saved_guard_source_fixture',Path(__file__).with_name('twin-saved-evidence-positive.py'))
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
JID = base.JID
client = base.client


@pytest.fixture(scope='module')
def golden():
    for path in (base.SOURCE/'data/datasets').glob('*/manifest.json'):
        assert json.loads(path.read_text())['metadata']['input_kind'] == 'synthetic'
    folder = ROOT/'data/dev026/view-checks'/(RUN.name.split('-')[0]+'_guards')/'golden'
    base.clone(base.SOURCE,folder)
    lab = Lab(folder)
    before = base.originals(lab)
    assert views.repair_view(lab,JID)['financial_recomputations'] == 0
    assert base.originals(lab) == before
    return folder,None,None,None


def event(lab, kind, change):
    with lab.store.db() as db:
        row = db.execute('SELECT id,details FROM events WHERE entity_id=? AND kind=? ORDER BY id DESC LIMIT 1',(JID,kind)).fetchone()
        value = json.loads(row['details'])
        change(value)
        db.execute('UPDATE events SET details=? WHERE id=?',(canonical(value),row['id']))


def root_change(lab, change):
    path = lab.output_path(JID)
    value = json.loads(gzip.decompress(path.read_bytes()))
    change(value)
    compressed_write(path,value)
    event(lab,'result_saved',lambda e:e.update(sha256=base.sha(path)))


def manifest_change(lab, change):
    path = lab.output_path(JID)
    value = json.loads(gzip.decompress(path.read_bytes()))
    reference = value['financial_manifest']
    manifest_path = path.parent/'twins/results'/reference['filename']
    manifest = json.loads(gzip.decompress(manifest_path.read_bytes()))
    change(manifest)
    compressed_write(manifest_path,manifest)
    reference.update(sha256=base.sha(manifest_path),content_hash=identity(manifest))
    value['report']['manifest_hash'] = identity(manifest)
    event(lab,'twin_financial_manifest_saved',lambda e:e.update(reference))
    root_change(lab,lambda root:root.update(value))


@pytest.mark.parametrize('fault', ['wrapper_job','manifest_filename','manifest_content','unsupported_protocol','report_binding','manifest_missing_parts','manifest_header','preparation_filename','preparation_bytes','manifest_bytes','preparation_trial','preparation_checkpoint_order','preparation_attempt','oversized_publication_event'])
def test_hash_consistent_original_metadata_and_preparation_faults_cannot_authorize_a_view(client,fault):
    browser,lab = client
    if fault == 'wrapper_job': root_change(lab,lambda root:root.update(job_id='another-job'))
    elif fault in {'manifest_filename','manifest_content'}:
        def change(root):
            root['financial_manifest']['filename' if fault=='manifest_filename' else 'content_hash'] = '../another.json.gz' if fault=='manifest_filename' else '0'*64
            event(lab,'twin_financial_manifest_saved',lambda e:e.update(root['financial_manifest']))
        root_change(lab,change)
    elif fault == 'unsupported_protocol':
        with lab.store.db() as db:
            payload = json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(JID,)).fetchone()[0])
            payload['twin_protocol']['version'] = 999
            db.execute('UPDATE jobs SET payload=? WHERE id=?',(canonical(payload),JID))
        root_change(lab,lambda root:root.update(payload_hash=identity(payload)))
    elif fault == 'report_binding': root_change(lab,lambda root:root['report'].update(manifest_hash='f'*64))
    elif fault == 'manifest_missing_parts': manifest_change(lab,lambda m:m.update(parts=[]))
    elif fault == 'manifest_header': manifest_change(lab,lambda m:m['parts'][0].update(part=True))
    elif fault == 'preparation_filename': event(lab,'twin_preparation_sealed',lambda e:e.update(filename='../preparation.json.gz'))
    elif fault in {'preparation_bytes','manifest_bytes'}:
        kind = 'twin_preparation_sealed' if fault=='preparation_bytes' else 'twin_financial_manifest_saved'
        details = next(e['details'] for e in lab.store.events(JID) if e['kind']==kind)
        path = lab.output_path(JID).parent/'twins'/('preparation' if fault=='preparation_bytes' else 'results')/details['filename']
        path.write_bytes(path.read_bytes()+b'changed')
    else:
        with lab.store.db() as db:
            if fault == 'preparation_trial':
                db.execute("UPDATE trial_plans SET artifact_sha256=? WHERE job_id=? AND window='prepare'",('0'*64,JID))
            elif fault == 'preparation_attempt':
                db.execute("UPDATE trial_attempts SET computed_sha256=? WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=? AND window='prepare')",('0'*64,JID))
            elif fault == 'preparation_checkpoint_order':
                trial = db.execute("SELECT id FROM trial_plans WHERE job_id=? AND window='prepare'",(JID,)).fetchone()[0]
                db.execute("UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.trial_id')=?",(JID,trial))
            else:
                db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",('x'*17000,JID))
    response = browser.post(f'/api/jobs/{JID}/trade-twins/repair-view',json={})
    assert response.status_code == 409,(fault,response.text[:1000])


@pytest.mark.parametrize('fault', ['view_identity','view_filename','view_missing','header_missing','header_duplicate','header_changed','set_missing_with_equal_count','set_wrong_assignment','chunk_missing'])
def test_derived_views_and_requested_rows_cannot_replace_the_complete_original(client,fault):
    browser,lab = client
    details = next(e['details'] for e in reversed(lab.store.events(JID)) if e['kind']==views.VIEW_EVENT)
    path = lab.output_path(JID).parent/'twins/views'/details['filename']
    endpoint = f'/api/jobs/{JID}/trade-twins/sets/0/members'
    if fault == 'view_identity': event(lab,views.VIEW_EVENT,lambda e:e.update(root_sha256='0'*64))
    elif fault == 'view_filename': event(lab,views.VIEW_EVENT,lambda e:e.update(filename='../view.sqlite3'))
    elif fault == 'view_missing': path.unlink()
    else:
        with closing(sqlite3.connect(path)) as db:
            if fault == 'header_missing': db.execute('DELETE FROM header')
            elif fault == 'header_duplicate': db.execute('INSERT INTO header SELECT value FROM header')
            elif fault == 'header_changed':
                value = json.loads(db.execute('SELECT value FROM header').fetchone()[0]);value['source_count']+=1
                db.execute('UPDATE header SET value=?',(canonical(value),))
            elif fault == 'set_missing_with_equal_count':
                db.execute('UPDATE sets SET ordinal=10000 WHERE ordinal=0 AND policy=?',('barrier_capped_elapsed_v1',))
            elif fault == 'set_wrong_assignment':
                row = db.execute('SELECT value FROM sets WHERE ordinal=0 AND policy=?',('barrier_capped_elapsed_v1',)).fetchone()
                value = json.loads(gzip.decompress(row[0]));value['outcome']['seed']+=1
                db.execute('UPDATE sets SET value=?,row_hash=? WHERE ordinal=0 AND policy=?',
                    (gzip.compress(canonical(value).encode(),mtime=0),identity(value),'barrier_capped_elapsed_v1'))
            else:
                db.execute("DELETE FROM chunks WHERE kind='ledger'")
                endpoint = f'/api/jobs/{JID}/trade-twins/sets/0/books/0'
            db.commit()
    response = browser.get(endpoint,params={'policy':'barrier_capped_elapsed_v1'})
    assert response.status_code == 409,(fault,response.text[:1000])


@pytest.mark.parametrize('fault', ['input','root','preparation','part','trial'])
def test_closing_guard_rejects_originals_changed_after_the_requested_row_was_verified(client,monkeypatch,fault):
    browser,lab = client
    original = views._set
    fired = []
    def change_after_read(*args,**kwargs):
        value = original(*args,**kwargs)
        if not fired:
            fired.append(True)
            if fault in {'input','trial'}:
                with lab.store.db() as db:
                    if fault == 'input':
                        payload = json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(JID,)).fetchone()[0]);payload['seed']+=1
                        db.execute('UPDATE jobs SET payload=? WHERE id=?',(canonical(payload),JID))
                    else:
                        db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=? AND part=0 AND window='barrier_capped_elapsed_v1'",('0'*64,JID))
            elif fault == 'root': lab.output_path(JID).write_bytes(lab.output_path(JID).read_bytes()+b'changed')
            elif fault == 'preparation':
                path = next((lab.output_path(JID).parent/'twins/preparation').glob('*.json.gz'));path.write_bytes(path.read_bytes()+b'changed')
            else:
                path = next((lab.output_path(JID).parent/'twins/parts').glob('part-000000-*.json.gz'));path.write_bytes(path.read_bytes()+b'changed')
        return value
    monkeypatch.setattr(views,'_set',change_after_read)
    response = browser.get(f'/api/jobs/{JID}/trade-twins/sets/0/members',params={'policy':'barrier_capped_elapsed_v1'})
    assert fired == [True]
    assert response.status_code == 409,(fault,response.text[:1000])


def test_unknown_policy_and_array_refuse_before_any_original_or_cached_access():
    with pytest.raises(ValueError):views._set(None,None,'invented',0)
    with pytest.raises(ValueError):views.book_page(None,'absent','fixed_elapsed_v1',0,0,kind='invented')
