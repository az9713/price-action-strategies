"""Owned resume must preserve original paired publication authority, not repair it."""
import copy
import gzip
import json
from pathlib import Path
import os

import pytest
from backend.lab.config import canonical
from backend.lab.service import compressed_write
from backend.lab.worker import Worker
from test_trade_twin_view_recovery import empty_source, financial_forbidden
from trade_twin_view_death_child import install, original_state


@pytest.mark.parametrize('fault', ['missing_result_event','missing_manifest_event','duplicate_manifest_event','manifest_order','manifest_reference','root_bytes','wrapper_context','manifest_filename','manifest_bytes'])
def test_owned_resume_never_replaces_missing_or_changed_original_publication(empty_source,monkeypatch,fault):
    lab,parent,child,parent_hash = empty_source
    jid = child['id']
    worker = Worker(lab)
    with monkeypatch.context() as hooks:
        fired = install(hooks,lab,jid,'after_root_commit',worker.shutdown.set)
        assert worker.run_once() and fired == [True]
    assert lab.store.job(jid)['status'] == 'queued'
    before = original_state(lab,jid)
    assert sum(e['kind']=='result_saved' for e in before['events']) == 1
    root = lab.output_path(jid)
    wrapped = json.loads(gzip.decompress(root.read_bytes()))
    with lab.store.db() as db:
        if fault == 'missing_result_event': db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(jid,))
        elif fault == 'missing_manifest_event': db.execute("DELETE FROM events WHERE entity_id=? AND kind='twin_financial_manifest_saved'",(jid,))
        elif fault == 'duplicate_manifest_event':
            value = copy.deepcopy(next(e for e in before['events'] if e['kind']=='twin_financial_manifest_saved'))
            lab.store.event('twin_financial_manifest_saved',jid,json.loads(value['details']),db)
        elif fault == 'manifest_order':
            db.execute("UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE entity_id=? AND kind='twin_financial_manifest_saved'",(jid,))
        elif fault == 'manifest_reference':
            value = dict(wrapped['financial_manifest'],content_hash='0'*64)
            db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='twin_financial_manifest_saved'",(canonical(value),jid))
    if fault == 'root_bytes': root.write_bytes(root.read_bytes()+b'changed')
    elif fault in {'wrapper_context','manifest_filename'}:
        if fault == 'wrapper_context': wrapped['job_id'] = 'different-job'
        else: wrapped['financial_manifest']['filename'] = '../outside.manifest.json.gz'
        compressed_write(root,wrapped)
        with lab.store.db() as db:
            import hashlib
            db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(canonical(dict(sha256=hashlib.sha256(root.read_bytes()).hexdigest())),jid))
    elif fault == 'manifest_bytes':
        path = root.parent/'twins/results'/wrapped['financial_manifest']['filename']
        path.write_bytes(path.read_bytes()+b'changed')
    damaged = original_state(lab,jid)
    financial_forbidden(monkeypatch,lab)
    assert Worker(lab).run_once()
    job = lab.store.job(jid)
    after = original_state(lab,jid)
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('owned-original-'+fault+'.json')).write_text(json.dumps(dict(
            fault=fault,status=job['status'],error=job['error'],before=before,damaged=damaged,after=after,
            financial_sets_executed=0),indent=2),encoding='utf-8')
    assert job['status'] == 'failed', (fault,job['status'],job['error'])
    assert after['events'] == damaged['events'], 'Owned resume replaced/added original publication evidence.'
    assert after['root_sha256'] == damaged['root_sha256'], 'Owned resume rewrote the original root.'
