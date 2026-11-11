"""Cancel only the owned timed-out benchmark queue item; retain every completed original artifact."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.store import Store
before=json.loads((root/'verification/runs/numerical-10000-first-budget-stop-preserved.json').read_text(encoding='utf-8'));jid=before['job_id'];store=Store(root/'data/capacity-real-instance');job=store.job(jid)
assert jid=='b62b7022a50a4eb3b1f1501b3ed0398e' and job['status']=='queued' and job['payload']['count']==10000 and job['payload']['name']=='Frozen real-sample capacity 10000'
folder=store.root/'data/jobs'/jid/'parts';input_before=hashlib.sha256(__import__('backend.lab.config',fromlist=['canonical']).canonical(job['payload']).encode()).hexdigest()
assert {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.glob('*.json.gz')}==before['part_hashes']
store.cancel(jid);after=store.job(jid);assert after['status']=='canceled' and hashlib.sha256(__import__('backend.lab.config',fromlist=['canonical']).canonical(after['payload']).encode()).hexdigest()==input_before
assert {path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.glob('*.json.gz')}==before['part_hashes']
value=dict(scope=__doc__,job_id=jid,status='canceled',completed_parts_preserved=len(before['part_hashes']),inputs_unchanged=True,partial_run_passed=False,main_store_modified=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'owned-timed-out-job-retention.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value))
