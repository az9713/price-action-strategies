from pathlib import Path
import hashlib,json,os,re,sys,urllib.request,xml.etree.ElementTree as ET
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);files=['STATUS.md','verification/evidence-index.md','verification/defects.json','verification/runs/runtime-ownership-root-cause.md','verification/runs/capacity-next-audit.md','verification/runs/runtime-managed-stop-tool-observation.json'];links=0
for name in files[:2]:
 p=root/name;s=p.read_text(encoding='utf-8');assert 'Current0.17' in s and '1468 passed' in s and '422 mandatory' in s and 'no_candidates' in s
 for target in re.findall(r'\]\(([^)]+)\)',s):
  if target.startswith(('http://','https://','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(name,target);links+=1
v=json.loads((root/'verification/defects.json').read_text(encoding='utf-8'));assert len(v['defects'])==len({d['id'] for d in v['defects']})
for d in v['defects'][-4:]:
 for key in ['initial_evidence','regression_receipt']:assert (root/d[key]).is_file()
full=json.loads((root/'verification/receipts/20261108T200633219291Z-runtime-capacity-current-full-regression-and-fifteen-module-coverage.json').read_text(encoding='utf-8'));assert full['command']['exit_code']==0
xml=next(a for a in full['artifacts'] if a['path'].endswith('runtime-capacity-full-junit.xml'));suites=list(ET.parse(root/xml['path']).iter('testsuite'));assert sum(int(s.attrib['tests']) for s in suites)==1468 and not any(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as response:health=json.load(response)
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
value=dict(scope='Current documentation/link/retained-failure/runtime consistency, not final acceptance.',local_links_checked=links,defect_records=len(v['defects']),full_tests=1468,main_current_and_ready=True,files=[dict(path=n,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in files])
(out/'documentation-check.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
