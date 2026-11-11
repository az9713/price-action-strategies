"""Check and snapshot completed D038 status/evidence/failure notes; not a release certificate."""
from pathlib import Path
import hashlib,json,os,re,shutil,sys,urllib.request,xml.etree.ElementTree as ET
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);links=0
files=['STATUS.md','verification/evidence-index.md','verification/defects.json','verification/runs/runtime-ownership-root-cause.md','verification/runs/search-statistics-next-acceptance-notes.md']
for name in files[:2]:
 p=root/name;text=p.read_text(encoding='utf-8');assert 'Current0.18' in text and '1517' in text and '422' in text
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http://','https://','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(name,target);links+=1
status=(root/'STATUS.md').read_text(encoding='utf-8');assert 'not ready for final release' in status and 'no_candidates' in status and 'not manual inspection of every frame' in status
defects=json.loads((root/'verification/defects.json').read_text(encoding='utf-8'))['defects'];assert len(defects)==len({d['id'] for d in defects})
for d in defects:
 for key,value in d.items():
  if isinstance(value,str) and value.startswith('verification/') and key.endswith(('_receipt','_evidence')):assert (root/value).exists(),(d['id'],key,value)
for d in defects:
 if d['id'].startswith(('D-DSR-','D-VERIFY-DSR-','D-VERIFY-RUNTIME-INVENTORY')):assert 'pending' not in d['status'],d['id']
full=sorted((root/'verification/receipts').glob('*-search-statistics-final-locator-source-full-regression-and-sixteen-module-coverage.json'))[-1]
receipt=json.loads(full.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
for name,digest in receipt['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
xml=root/next(a['path'] for a in receipt['artifacts'] if a['path'].endswith('junit.xml'));suites=list(ET.parse(xml).iter('testsuite'));assert sum(int(s.attrib['tests']) for s in suites)==1517 and not any(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as r:health=json.load(r)
assert health['source_current'] and health['worker_ready'] and health['worker_alive'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
manifest=[]
for name in files:
 source=root/name;destination=out/'documents'/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
 manifest.append(dict(path=name,sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
value=dict(scope=__doc__,local_links_checked=links,defect_records=len(defects),full_tests=1517,main_current_and_ready=True,files=manifest)
(out/'documentation-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
