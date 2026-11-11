"""Keep the failed old-core benchmark original; prevent its queued continuation from taking a new run."""
from pathlib import Path
import json,os,sys
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
folder=root/'data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7'
store=Store(folder);jid='c3a7d7236a5343979ce1cfa9aefd1de1'
job=store.job(jid)
assert job['kind']=='search' and job['status']=='queued' and job['checkpoint']==106
assert len(job['payload']['configurations'])==10000
assert job['payload']['core_hash']=='3dc03bd1e2ce5f8ae2f16a50c64323d4aa8a43cb2e958516114d80ab73d44688'
with store.db() as db:
    before=[dict(r) for r in db.execute('SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? ORDER BY part,window',(jid,))]
store.cancel(jid)
assert store.job(jid)['status']=='canceled'
with store.db() as db:
    after=[dict(r) for r in db.execute('SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? ORDER BY part,window',(jid,))]
assert before==after
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'timed-out-original-capacity-cancellation.json').write_text(json.dumps(dict(
    scope=__doc__,job_id=jid,original_checkpoint=106,planned_original_configurations=10000,
    attempts_and_original_computation_and_artifact_digests_preserved=True,original_files_deleted=False,
    failed_original_run_relabelled_as_passed=False,new_source_must_use_new_benchmark_jobs=True),indent=2),encoding='utf-8')
