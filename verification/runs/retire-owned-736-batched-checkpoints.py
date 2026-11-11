"""Cancel only the terminal benchmark's queued continuation; preserve originals."""
from pathlib import Path
import hashlib,json,os,sys

root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
folder=root/'data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7'
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);store=Store(folder);jid='859b7e4092f34c0cbf271b989de4a00c'
job=store.job(jid)
assert job['kind']=='search' and job['status']=='queued' and job['checkpoint']==736 and job['owner'] is None
def originals():
    with store.db() as db:
        rows=[dict(r) for r in db.execute('SELECT id,part,window,state,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL ORDER BY part,window',(jid,))]
    assert len(rows)==736
    for row in rows:
        path=folder/'data/jobs'/jid/'parts'/f"{row['part']:06d}.json.gz"
        row['actual_file_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
        assert row['actual_file_sha256']==row['artifact_sha256']
    return rows
with store.db() as db:
    assert [r[0] for r in db.execute("SELECT id FROM jobs WHERE status IN ('queued','running','canceling')")]==[jid]
before=originals();store.cancel(jid);after=originals();assert before==after
assert store.job(jid)['status']=='canceled'
with store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
value=dict(scope=__doc__,job_id=jid,original_checkpoint_accounts=len(after),all_committed_rows_and_file_bytes_preserved=True,
    original_record_digest=hashlib.sha256(json.dumps(after,sort_keys=True).encode()).hexdigest(),final_state='canceled',
    worker_process_confirmed_terminal_by_tool_before_execution=True,no_user_store_or_cache_or_credentials_copied=True)
(out/'owned-original-736-preservation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
