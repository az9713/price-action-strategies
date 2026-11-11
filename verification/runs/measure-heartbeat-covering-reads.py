"""Owned synthetic-row query probe; neither financial nor capacity acceptance."""
from pathlib import Path
import hashlib,json,os,sqlite3,time
from backend.lab.store import Store

out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);store=Store(out/'synthetic-row')
payload={'authored_synthetic':'x'*8575241}
job=store.create_job('download',payload)
assert store.claim('owner')['id']==job['id']
old='SELECT status,owner,progress,note,checkpoint,cancel_requested FROM jobs WHERE id=?'
new='SELECT status,owner,cancel_requested FROM jobs INDEXED BY jobs_live_control WHERE id=?'
measurements=[]
with store.db() as db:
    before=db.execute('SELECT payload FROM jobs WHERE id=?',(job['id'],)).fetchone()[0]
    expected=hashlib.sha256(before.encode()).hexdigest()
    for iteration in range(4):
        for label,sql in ([('original',old),('covering',new)] if iteration%2==0 else [('covering',new),('original',old)]):
            plan=[r[3] for r in db.execute('EXPLAIN QUERY PLAN '+sql,(job['id'],))]
            if label=='covering':assert any('COVERING INDEX jobs_live_control' in r for r in plan)
            start=time.perf_counter()
            for _ in range(500):
                row=db.execute(sql,(job['id'],)).fetchone()
                assert row['status']=='running' and row['owner']=='owner' and row['cancel_requested']==0
            measurements.append(dict(iteration=iteration,query=label,reads=500,seconds=time.perf_counter()-start,plan=plan))
    after=db.execute('SELECT payload FROM jobs WHERE id=?',(job['id'],)).fetchone()[0]
    assert before==after and hashlib.sha256(after.encode()).hexdigest()==expected
result=dict(scope=__doc__,sqlite_version=sqlite3.sqlite_version,synthetic_payload_bytes=len(before.encode()),
            same_original_payload_sha256=expected,measurements=measurements,financial_capacity_certified=False)
(out/'heartbeat-covering-measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
