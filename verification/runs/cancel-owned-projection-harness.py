"""Cancel only the identified synthetic first projection harness, preserving evidence."""
from pathlib import Path
import json,os,sqlite3,sys,tempfile
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
folder=Path(tempfile.gettempdir())/'pytest-of-user/pytest-598/test_six_actual_parts_evicted_0'
dbpath=folder/'data/lab.sqlite3';jid='0814f84cddf04207ae37d77c27e51ab9'
with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    job=dict(db.execute('SELECT id,kind,status,owner FROM jobs WHERE id=?',(jid,)).fetchone())
    assert job==dict(id=jid,kind='trade_twins',status='running',owner='paired-part-owner')
    parts=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(jid,)).fetchone()[0]
    assert parts==6
store=Store(folder);store.cancel(jid)
with store.db() as db:
    assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(jid,)).fetchone()[0]==6
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'owned-projection-harness-cancellation.json').write_text(json.dumps(dict(
    job_id=jid,reason='Harness performed all-account book verification as isolated outside-unit reads; rerun the same complete totals inside the actual production control/unit scope.',
    original_parts_preserved=6,normal_cancellation_requested=True,full_control_proof=False,source_changed=False),indent=2),encoding='utf-8')
