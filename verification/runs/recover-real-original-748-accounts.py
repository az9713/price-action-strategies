"""Recover the genuine interrupted account search; preserve committed originals, not a capacity pass."""
from pathlib import Path
from threading import Event,Timer
import hashlib,json,os,sys,time
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.service import Lab,compressed_read
from backend.lab.worker import Worker
from backend.lab.config import identity
from backend.lab.research import core_hash
folder=root/'data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7'
lab=Lab(folder);jid='eda4e80c7e794d2fa8f858b8582c385b';job=lab.store.job(jid)
assert job['status']=='canceled' and job['checkpoint']==748 and job['payload']['core_hash']==core_hash()
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);started=time.perf_counter()
with lab.store.db() as db:
    assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('running','queued','canceling')").fetchone()[0]==0
    before=[dict(r) for r in db.execute('SELECT id,part,window,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL ORDER BY part,window',(jid,))]
assert len(before)>=748
paths={row['id']:folder/'data/jobs'/jid/'parts'/(str(row['part']).zfill(6)+'.json.gz') for row in before}
for row in before:assert hashlib.sha256(paths[row['id']].read_bytes()).hexdigest()==row['artifact_sha256']
lab.store.resume(jid);stop=Event();timer=Timer(600,stop.set);timer.daemon=True;timer.start();worker=Worker(lab,stop)
progress=worker._progress;guards=[]
def observed(*a,**k):
    result=progress(*a,**k)
    (out/'original-recovery-progress.json').write_text(json.dumps(dict(job_id=jid,elapsed_seconds=time.perf_counter()-started,
        note=a[2],checkpoint=a[3] if len(a)>3 else k.get('checkpoint')),indent=2),encoding='utf-8')
    return result
worker._progress=observed
try:
    while not stop.is_set():
        state=lab.store.job_status(jid)
        if state['status'] in {'completed','failed','canceled'}:break
        worked=worker.run_once()
        if worked and worker.last_lease_failure:guards.append(worker.last_lease_failure)
        if not worked:stop.wait(.1)
finally:timer.cancel()
state=lab.store.job(jid)
assert state['status']=='completed',(state['status'],state['error'],state['checkpoint'],guards)
with lab.store.db() as db:
    for old in before:
        current=dict(db.execute('SELECT id,part,window,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE id=?',(old['id'],)).fetchone())
        assert current==old
    assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND state='completed'",(jid,)).fetchone()[0]==1000
    attempts=db.execute('SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans p ON p.id=a.trial_id WHERE p.job_id=?',(jid,)).fetchone()[0]
for row in before:assert hashlib.sha256(paths[row['id']].read_bytes()).hexdigest()==row['artifact_sha256']
result=lab.result(jid);assert result['count']==len(result['rows'])==1000
payload_hash=identity(job['payload']);subject_core=core_hash()
for row in result['rows']:
    path=folder/'data/jobs'/jid/'parts'/(str(row['part']).zfill(6)+'.json.gz');raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['report_sha256']
    saved=compressed_read(path)
    assert saved['config_id']==row['config_id']==identity(job['payload']['configurations'][row['part']])
    assert saved['payload_hash']==payload_hash and saved['core_hash']==subject_core
(out/'recovered-original-real-search.json').write_text(json.dumps(dict(scope=__doc__,job_id=jid,core_hash=core_hash(),
    complete_original_configurations=1000,committed_originals_before_recovery=len(before),
    every_prior_attempt_digest_and_file_preserved=True,total_actual_attempts=attempts,
    elapsed_recovery_seconds=time.perf_counter()-started,observed_guard_diagnostics=guards,
    all1000_original_parts_reread=True,capacity_budget_certified=False),indent=2),encoding='utf-8')
print(json.dumps(dict(originals_preserved=len(before),completed=1000,attempts=attempts,recovery_seconds=time.perf_counter()-started)))
