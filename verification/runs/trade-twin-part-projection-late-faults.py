"""Warm immutable projections never authorize changed originals at publication."""
import json
import pytest
from backend.lab import trade_twin_parts as parts
from backend.lab.config import canonical
from backend.lab.store import StateError
from test_trade_twin_source import original
from test_trade_twin_parts import owned


def test_warm_projection_refuses_coherently_rebound_publication_identity(original):
    lab,job,owner,prepared,journal=owned(original,parts)
    journal.execute(0);journal._prefix()
    with lab.store.db() as db:
        row=db.execute('SELECT event_id FROM trade_twin_part_index WHERE job_id=? AND part=0',(job['id'],)).fetchone()
        old=row['event_id'];replacement=db.execute('SELECT MAX(id)+100 FROM events').fetchone()[0]
        db.execute('UPDATE events SET id=? WHERE id=?',(replacement,old))
        db.execute('UPDATE trade_twin_part_index SET event_id=? WHERE job_id=? AND part=0',(replacement,job['id']))
    try:
        with pytest.raises(StateError,match='publication changed'):journal._prefix()
    finally:
        with lab.store.db() as db:
            db.execute('UPDATE events SET id=? WHERE id=?',(old,replacement))
            db.execute('UPDATE trade_twin_part_index SET event_id=? WHERE job_id=? AND part=0',(old,job['id']))
    assert journal._prefix()==1
    lab.store.release(job['id'],owner)


def test_original_bytes_changed_after_warm_opening_cannot_publish_and_retry_keeps_committed_part(original,monkeypatch):
    lab,job,owner,prepared,journal=owned(original,parts)
    first=journal.execute(0);journal._prefix()
    event=next(e for e in lab.store.events(job['id']) if e['kind']=='twin_part_committed')
    path=journal.folder/event['details']['filename'];raw=path.read_bytes();check=journal._authority;calls=[]
    def changed_at_close():
        calls.append(True);result=check()
        if len(calls)==2:path.write_bytes(raw+b'authored late change')
        return result
    monkeypatch.setattr(journal,'_authority',changed_at_close)
    try:
        with pytest.raises(StateError,match='bytes changed'):journal.execute(1)
        assert len([e for e in lab.store.events(job['id']) if e['kind']=='twin_part_committed'])==1
        assert any(e['kind']=='twin_part_failed' for e in lab.store.events(job['id']))
    finally:path.write_bytes(raw)
    monkeypatch.setattr(journal,'_authority',check)
    second=journal.execute(1)
    assert second['attempt']==2 and path.read_bytes()==raw and journal.execute(0)==first
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trade_twin_part_index WHERE job_id=?',(job['id'],)).fetchone()[0]==2
        assert db.execute("SELECT MAX(attempts) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND part<100",(job['id'],)).fetchone()[0]==1
    lab.store.release(job['id'],owner)
