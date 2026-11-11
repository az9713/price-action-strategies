"""Reconstructible D043 component source/evidence checkpoint; final acceptance remains pending."""
from pathlib import Path
import hashlib,json,os,sys,zipfile,xml.etree.ElementTree as ET
root=Path.cwd();sys.path.insert(0,str(root));from verification.record_check import source_paths,review_artifact_allowed
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
labels=['result-materialization-current-full-regression-and-twenty-one-module-coverage', 'result-materialization-current-twenty-one-module-coverage-gate', 'result-materialization-current-typed-production-build', 'result-materialization-current-fourteen-desktop-result-study-and-ownership-workflows', 'result-materialization-current-10-1000-100000-nonfinancial-storage-pages', 'result-materialization-current-eight-assertion-killed-guard-mutations', 'result-materialization-current-independent-original-parts-and-six-decimal-accounts', 'result-materialization-current-independent-study-inputs-and-joint-accounts', 'result-materialization-current-managed-owner-all-job-idleness-assets-and-duplicate-refusal', 'result-materialization-current-83-422-120-plan-inventory']
failed_labels=['result-materialization-authored-worker-bounded-pages-streaming-original-corruption-and-legacy-first-contract', 'result-materialization-authored-missing-artifact-malformed-derived-diagnostic-parity-and-publication-fault-contract', 'result-materialization-current-boundaries-and-complete-funnel-groups', 'result-materialization-first-two-desktop-actual-pages-and-history-ownership', 'result-materialization-current-eight-isolated-critical-mutations']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];return p,json.loads(p.read_text(encoding='utf-8'))
def verify_artifacts(r):
 for a in r['artifacts']:
  p=(root/a['path']).resolve();p.relative_to(root);assert review_artifact_allowed(p,root)
  assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'],a['path']
selected=[];subjects=[];inputs={Path(__file__).resolve(),root/'verification/runs/job-status-current-checkpoint.py'};artifacts=0;receipts={}
for label in labels:
 p,r=latest(label);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for name,digest in r['subject']['source_files'].items():assert sha(root/name)==digest,(label,name)
 subjects.append(r['subject']['source_files']);verify_artifacts(r);artifacts+=len(r['artifacts']);receipts[label]=r
 for i in r['subject']['input_manifests']:
  q=root/i['path'];assert sha(q)==i['sha256'];inputs.add(q)
 selected.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts'])))
assert all(s==subjects[0] for s in subjects)
sources=source_paths();assert {p.relative_to(root).as_posix() for p in sources}==set(subjects[0])
gate=receipts[labels[1]];gates=[a for a in gate['artifacts'] if a['path'].endswith('numerical-coverage-gate.json')];assert len(gates)==1
g=json.loads((root/gates[0]['path']).read_text(encoding='utf-8'));assert g['ready'] and len(g['modules'])==21
full=receipts[labels[0]];junit=[a for a in full['artifacts'] if a['path'].endswith('junit.xml')];assert len(junit)==1
suites=list(ET.parse(root/junit[0]['path']).iter('testsuite'));tests=sum(int(s.attrib.get('tests',0)) for s in suites)
assert tests>=1738 and all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
failures=[]
for label in failed_labels:
 p,r=latest(label);assert r['command']['exit_code']==1;verify_artifacts(r)
 failures.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts']),scope='Retained original historical failure; not current-source conformance.'))

paths=set(sources)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))|inputs;manifest=[]
with zipfile.ZipFile(out/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for p in sorted(q for q in paths if q.is_file()):
  name=p.relative_to(root).as_posix();assert not any(part.startswith('.env') for part in p.parts)
  assert not p.is_relative_to(root/'data') and '/node_modules/' not in name and not name.endswith('.zip')
  assert '/runs/' not in name or p in inputs
  raw=p.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(out/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(out/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
value=dict(scope=__doc__,selected_receipts=selected,artifact_files_checked=artifacts,historical_failures_retained=failures,source_archive_files=len(manifest),full_current_regression_tests=tests,full_current_regression_passed=True,twenty_one_module_coverage_passed=True,final_acceptance_certified=False,exclusions='Credentials, all traces, cached data, source-video media and installed dependencies; not a clean-install or global privacy certificate.')
(out/'checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['selected_receipts','historical_failures_retained']},indent=2))
