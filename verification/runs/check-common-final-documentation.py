"""Snapshot current D039 status/evidence and all retained defects; not final release certification."""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);links=0
files=['STATUS.md','verification/evidence-index.md','verification/defects.json','verification/runs/runtime-ownership-root-cause.md','verification/runs/common-sampling-next-acceptance-notes.md']
for name in files[:2]:
 p=root/name;text=p.read_text(encoding='utf-8');assert 'Current0.19 — verified common sampling component checkpoint' in text and '1579' in text and '422' in text and '438' in text
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http://','https://','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(name,target);links+=1
status=(root/'STATUS.md').read_text(encoding='utf-8')
assert all(s in status for s in ['not ready for final release','no_candidates','not manual inspection of every frame','root cause is unproved','10000 matched trade-twin'])
defects=json.loads((root/'verification/defects.json').read_text(encoding='utf-8'))['defects'];assert len(defects)==len({d['id'] for d in defects})==103
for d in defects:
 for key,value in d.items():
  if isinstance(value,str) and value.startswith('verification/') and key.endswith(('_receipt','_evidence')):assert (root/value).exists(),(d['id'],key,value)
startup=next(d for d in defects if d['id']=='D-VERIFY-COMMON-WORKER-STARTUP-001');assert startup['status']=='unchanged_isolated_and_full_serial_pass_root_cause_unproved_first_timeout_retained'
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as r:health=json.load(r)
assert health['source_current'] and health['worker_ready'] and health['worker_alive'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
manifest=[]
for name in files:
 source=root/name;destination=out/'documents'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 manifest.append(dict(path=name,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
value=dict(scope=__doc__,local_links_checked=links,defect_records=len(defects),full_tests=1579,main_current_and_ready=True,files=manifest)
(out/'documentation-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
