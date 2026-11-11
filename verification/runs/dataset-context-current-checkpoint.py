"""Coherent D040 component recovery checkpoint; full regression/final422-case certification remains pending."""
from pathlib import Path
import hashlib,json,os,sys,zipfile
root=Path.cwd();sys.path.insert(0,str(root));from verification.record_check import source_paths,review_artifact_allowed
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1]
 return p,json.loads(p.read_text(encoding='utf-8'))
labels=[
 'dataset-context-final-positive-and-zero-account-csv-responsive-import-focused-regression',
 'dataset-context-current-positive-csv-subject-two-desktop-regression',
 'dataset-context-current-positive-csv-subject-seven-isolated-mutations',
 'dataset-context-current-positive-csv-subject-independent-browser-account-csv-and-offline-audit',
 'dataset-context-current-positive-csv-subject-original-authored-contract',
 'dataset-context-current-positive-csv-subject-typed-build',
 'dataset-context-current-managed-owner-exact-assets-and-duplicate-refusal',
 'dataset-context-current-83-422-120-planning-inventory',
]
selected=[];subjects=[];inputs={Path(__file__).resolve()};artifacts=0
def verify_artifacts(r):
 for a in r['artifacts']:
  p=(root/a['path']).resolve();p.relative_to(root);assert review_artifact_allowed(p,root)
  assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256']
for label in labels:
 p,r=latest(label);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for name,digest in r['subject']['source_files'].items():assert sha(root/name)==digest,(label,name)
 subjects.append(r['subject']['source_files']);verify_artifacts(r);artifacts+=len(r['artifacts'])
 for i in r['subject']['input_manifests']:
  q=root/i['path'];assert sha(q)==i['sha256'];inputs.add(q)
 selected.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts'])))
assert all(s==subjects[0] for s in subjects)
sources=source_paths();assert {p.relative_to(root).as_posix() for p in sources}==set(subjects[0])
failures=[]
for label in [
 'aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract',
 'dataset-context-authored-all-analysis-worker-study-whitelist-corruption-first-contract',
 'dataset-context-first-complete-backend-all-analysis-workers-studies-csv-offline',
 'dataset-context-correct-digit-free-fact-label-complete-backend-regression',
 'dataset-context-original-fresh-job-api-csv-offline-contract-regression',
 'dataset-context-two-desktop-saved-label-switch-legacy-and-all-offline-pages-first-execution',
 'import-http-event-loop-authored-held-normalization-and-concurrent-publication-first-contract',
 'dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence',
]:
 p,r=latest(label);assert r['command']['exit_code']==1;verify_artifacts(r)
 failures.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts']),scope='Historical failure, not asserted to match current source.'))
paths=set(sources)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))|inputs
manifest=[]
with zipfile.ZipFile(out/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for p in sorted(q for q in paths if q.is_file()):
  name=p.relative_to(root).as_posix();assert not any(part.startswith('.env') for part in p.parts)
  assert not p.is_relative_to(root/'data') and '/node_modules/' not in name and not name.endswith('.zip')
  assert '/runs/' not in name or p in inputs
  raw=p.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(out/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(out/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
value=dict(scope=__doc__,selected_receipts=selected,artifact_files_checked=artifacts,historical_failures_retained=failures,source_archive_files=len(manifest),full_current_regression_certified=False,final_acceptance_certified=False,exclusions='Credentials, all traces, cached data, source-video media and installed dependencies. This is not clean-install reproduction or global privacy certification.')
(out/'checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in {'selected_receipts','historical_failures_retained'}},indent=2))
