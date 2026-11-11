"""Reconstructible D044 component source/evidence checkpoint; final acceptance remains pending."""
from pathlib import Path
import hashlib,json,os,sys,zipfile,xml.etree.ElementTree as ET
root=Path.cwd();sys.path.insert(0,str(root));from verification.record_check import source_paths,review_artifact_allowed
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
labels=['evaluation-cache-current-full-regression-and-twenty-two-module-coverage', 'evaluation-cache-current-twenty-two-module-combined-coverage-gate', 'evaluation-cache-current-four-legacy-direct-report-cases-and-provenance-checked-coverage-append', 'evaluation-cache-current-typed-production-build', 'evaluation-cache-current-fourteen-desktop-result-study-and-ownership-workflows', 'numerical-capacity-cached-100-real-one-session-repeat-pilot', 'numerical-capacity-cached-1000-real-one-session-execution', 'numerical-capacity-current-10000-real-one-session-execution', 'evaluation-cache-current-exact-1200-complete-cached-uncached-accounts', 'evaluation-cache-six-owned-worker-exits-and-durable-part-recovery', 'evaluation-cache-current-nine-isolated-critical-mutations', 'evaluation-cache-current-independent-original-parts-and-six-decimal-accounts', 'evaluation-cache-current-independent-study-inputs-and-joint-accounts', 'evaluation-cache-current-managed-owner-all-job-idleness-assets-and-duplicate-refusal', 'evaluation-cache-current-83-422-120-plan-inventory']
failed_labels=['evaluation-cache-authored-current-bytes-base-charts-context-protection-and-worker-first-contract', 'evaluation-cache-first-verified-preparation-base-charts-and-live-guard-regression', 'evaluation-cache-authored-120-discriminating-signal-account-parity-and-stream-cancel-manifest-race', 'live-control-reader-authored-fresh-owner-cancel-readonly-isolation-and-cleanup-first-contract', 'live-control-reader-first-readonly-fresh-authority-and-cache-reference-regression', 'live-control-covering-index-authored-old-store-original-byte-query-plan-and-missing-index-first-contract', 'numerical-capacity-owned-covering-control-index-and-update-scaling-probe', 'evaluation-cache-current-twenty-two-module-coverage-gate']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];return p,json.loads(p.read_text(encoding='utf-8'))
def verify_artifacts(r):
 for a in r['artifacts']:
  p=(root/a['path']).resolve();p.relative_to(root);assert review_artifact_allowed(p,root)
  assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'],a['path']
selected=[];subjects=[];inputs={Path(__file__).resolve(),root/'verification/runs/numerical-10000-first-budget-stop-preserved.json'};artifacts=0;receipts={}
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
g=json.loads((root/gates[0]['path']).read_text(encoding='utf-8'));assert g['ready'] and len(g['modules'])==22
full=receipts[labels[0]];junit=[a for a in full['artifacts'] if a['path'].endswith('junit.xml')];assert len(junit)==1
suites=list(ET.parse(root/junit[0]['path']).iter('testsuite'));tests=sum(int(s.attrib.get('tests',0)) for s in suites)
assert tests>=1893 and all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
failures=[]
for label in failed_labels:
 p,r=latest(label);assert r['command']['exit_code']==1;verify_artifacts(r)
 failures.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts']),scope='Retained original historical failure; not current-source conformance.'))

for receipt_id in ['20261109T084649710750Z-numerical-capacity-current-10000-real-one-session-execution']:
 p=root/'verification/receipts'/(receipt_id+'.json');r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==1;verify_artifacts(r)
 failures.append(dict(receipt=receipt_id,sha256=sha(p),artifacts=len(r['artifacts']),scope='Original actual10000 attempt:900s budget failed with4663 original completed parts; retained, not certified.'))
retained_path=root/'verification/receipts/20261109T091055580298Z-numerical-capacity-owned-timeout-queue-cancel-with-4663-original-parts-retained.json';retained=json.loads(retained_path.read_text(encoding='utf-8'));assert retained['command']['exit_code']==0;verify_artifacts(retained)
retention=dict(receipt=retained['receipt_id'],sha256=sha(retained_path),scope='Historical owned-queue cleanup and exact preservation; not current-source conformance.')
paths=set(sources)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))|inputs;manifest=[]
with zipfile.ZipFile(out/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for p in sorted(q for q in paths if q.is_file()):
  name=p.relative_to(root).as_posix();assert not any(part.startswith('.env') for part in p.parts)
  assert not p.is_relative_to(root/'data') and '/node_modules/' not in name and not name.endswith('.zip')
  assert '/runs/' not in name or p in inputs
  raw=p.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(out/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(out/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
value=dict(scope=__doc__,historical_partial_retention=retention,selected_receipts=selected,artifact_files_checked=artifacts,historical_failures_retained=failures,source_archive_files=len(manifest),full_current_regression_tests=tests,full_current_regression_passed=True,twenty_two_module_coverage_passed=True,final_acceptance_certified=False,exclusions='Credentials, all traces, cached data, source-video media and installed dependencies; not a clean-install or global privacy certificate.')
(out/'checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['selected_receipts','historical_failures_retained']},indent=2))
