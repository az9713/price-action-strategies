"""Retire the expired owned benchmark after its process exited; preserve every original digest."""
from pathlib import Path
import json,os,sys,time
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
store=Store(root/'data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7')
jid='799e8a921b214f92bd5eeb345ef1a527';job=store.job(jid)
assert job['kind']=='search' and job['status']=='running' and job['checkpoint']==116
assert job['payload']['core_hash']=='c6a844e49cd3a44245512138eb7399748d08262092d31caf9d7a3b5fedcbcd71'
assert job['lease_until']<time.time()
with store.db() as db:
    assert [r[0] for r in db.execute("SELECT id FROM jobs WHERE status IN ('queued','running','canceling')")]==[jid]
    before=[dict(r) for r in db.execute('SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? ORDER BY part,window',(jid,))]
store.cancel(jid);assert store.claim('retire-expired-owned-capacity') is None
assert store.job(jid)['status']=='canceled'
with store.db() as db:
    after=[dict(r) for r in db.execute('SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? ORDER BY part,window',(jid,))]
assert before==after
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'retired-early-stopped-original-capacity.json').write_text(json.dumps(dict(
    job_id=jid,original_checkpoint=116,original_attempts_and_digests_preserved=True,expired_process_run_retired=True,
    original_files_deleted=False,completed_capacity=False),indent=2),encoding='utf-8')
