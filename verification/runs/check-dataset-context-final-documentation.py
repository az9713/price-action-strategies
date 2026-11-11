"""Snapshot and validate corrected D040 evidence/status/failures; not final release certification."""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);links=0
files=['STATUS.md','verification/evidence-index.md','verification/defects.json','verification/runs/dataset-context-next-acceptance-notes.md','verification/runs/dataset-context-managed-restart-observation.json']
for name in files[:2]:
 p=root/name;text=p.read_text(encoding='utf-8');assert text.startswith('## Current0.20 — universe-preserving provenance checkpoint')
 for phrase in ['92 focused','Four desktop','84 offline','not ready for final release','422','10000 matched trade twins']:assert phrase in text,(name,phrase)
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http://','https://','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(name,target);links+=1
defects=json.loads((root/'verification/defects.json').read_text(encoding='utf-8'))['defects'];assert len(defects)==len({d['id'] for d in defects})==112
for d in defects:
 for key,value in d.items():
  if isinstance(value,str) and value.startswith('verification/'):assert (root/value).exists(),(d['id'],key,value)
assert next(d for d in defects if d['id']=='D-DATASET-UNIVERSE-CAP-001')['status'].startswith('fixed_')
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as r:health=json.load(r)
assert health['server_pid']==47800 and health['worker_ready'] and health['worker_alive'] and health['store_lease_held'] and health['source_current'] and health['core_hash']==current_core_hash()
manifest=[]
for name in files:
 p=root/name;q=out/'documents'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);manifest.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
value=dict(scope=__doc__,links_checked=links,defect_records=len(defects),current_main_ready=True,full_current_regression_certified=False,final_acceptance=False,files=manifest)
(out/'documentation-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
