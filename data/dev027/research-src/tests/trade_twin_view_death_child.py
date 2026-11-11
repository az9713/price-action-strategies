"""Controlled real interpreter death at original worker publication boundaries."""
from pathlib import Path
import hashlib
import json
import os
import sys

BOUNDARIES = {
    'after_view_file': 81,
    'after_root_temp': 82,
    'after_root_commit': 83,
    'after_view_event': 84,
    'after_generic_view': 85,
    'inside_root_transaction': 86,
    'inside_view_transaction': 87,
}
PUBLIC_BOUNDARIES = tuple(k for k in BOUNDARIES if not k.startswith('inside_'))


def original_state(lab, jid):
    folder = lab.output_path(jid).parent / 'twins'
    files = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in folder.rglob('*') if p.is_file()}
    with lab.store.db() as db:
        events = [dict(row) for row in db.execute(
            "SELECT id,kind,details FROM events WHERE entity_id=? AND kind IN ('result_saved','twin_financial_manifest_saved','trade_twin_view_saved','twin_preparation_sealed') ORDER BY id", (jid,))]
    root = lab.output_path(jid)
    return dict(files=files, events=events,
                root_sha256=hashlib.sha256(root.read_bytes()).hexdigest() if root.exists() else None)


def install(monkeypatch, lab, jid, boundary, callback):
    """Install a single post-boundary fault; never fabricate original outcomes."""
    from backend.lab import trade_twin_views as views
    from backend.lab import trade_twin_worker as worker
    fired = []
    def once():
        if not fired:
            fired.append(True)
            callback()
    if boundary == 'after_view_file':
        old = views.build_view
        def build(*args, **kwargs):
            result = old(*args, **kwargs)
            once()
            return result
        monkeypatch.setattr(views, 'build_view', build)
    elif boundary == 'after_root_temp':
        old = worker.compressed_write
        def write(path, *args, **kwargs):
            old(path, *args, **kwargs)
            if path.name.startswith('pub-') and path.name.endswith('.result.json.gz'):
                once()
        monkeypatch.setattr(worker, 'compressed_write', write)
    elif boundary == 'after_root_commit':
        old = views.Originals.guard
        def guard(self):
            old(self)
            with lab.store.db() as db:
                committed = db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='result_saved' LIMIT 1", (jid,)).fetchone()
            if self.jid == jid and committed:
                once()
        monkeypatch.setattr(views.Originals, 'guard', guard)
    elif boundary in {'inside_root_transaction', 'inside_view_transaction'}:
        old = lab.store.event
        target = 'twin_financial_manifest_saved' if boundary == 'inside_root_transaction' else views.VIEW_EVENT
        def event(kind, entity_id, *args, **kwargs):
            result = old(kind, entity_id, *args, **kwargs)
            if entity_id == jid and kind == target:
                once()
            return result
        monkeypatch.setattr(lab.store, 'event', event)
    elif boundary in {'after_view_event', 'after_generic_view'}:
        old = lab.result_index.build
        def build(job_id, *args, **kwargs):
            if job_id == jid and boundary == 'after_view_event':
                once()
            result = old(job_id, *args, **kwargs)
            if job_id == jid and boundary == 'after_generic_view':
                once()
            return result
        monkeypatch.setattr(lab.result_index, 'build', build)
    else:
        raise AssertionError('Unknown authored publication boundary.')
    return fired


def main():
    from pytest import MonkeyPatch
    from backend.lab.service import Lab
    from backend.lab.worker import Worker
    import backend
    assert Path(backend.__file__).resolve().parents[1] == Path(__file__).resolve().parents[1]
    store, jid, boundary, marker = sys.argv[1:]
    lab = Lab(Path(store))
    def die():
        value = original_state(lab, jid)
        value.update(boundary=boundary, exit_code=BOUNDARIES[boundary], job_id=jid,
                     job_status=lab.store.job(jid)['status'], financial_sets_executed=0)
        Path(marker).write_text(json.dumps(value, indent=2), encoding='utf-8')
        os._exit(BOUNDARIES[boundary])
    install(MonkeyPatch(), lab, jid, boundary, die)
    Worker(lab).run_once()
    raise AssertionError('Worker did not reach the authored death boundary.')


if __name__ == '__main__':
    main()
