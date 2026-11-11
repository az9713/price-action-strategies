"""D039 coherent source/fixture/build checkpoint with retained failures; not final acceptance."""
from pathlib import Path
import hashlib,json,os,sys,urllib.request,zipfile
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths,review_artifact_allowed
from backend.lab.research import current_core_hash
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
labels=[
 'common-sampling-unchanged-source-serial-full-regression-and-seventeen-module-coverage',
 'common-sampling-current-seventeen-module-numerical-coverage-gate',
 'common-sampling-current-subject-typed-frontend-build',
 'common-sampling-twelve-isolated-critical-source-mutations',
 'common-sampling-complete-assumptions-grid-random-calendar-two-desktop-workflows',
 'common-sampling-current-120-browser-accounts-independent-decimal-and-complete-export-assumptions-project-runtime',
 'common-sampling-current-main-fourteen-existing-desktop-workflows',
 'common-sampling-current-twenty-existing-browser-accounts-independent-decimal',
 'common-sampling-current-six-joint-study-accounts-independent-decimal-csv-offline',
 'common-sampling-current-managed-main-duplicate-refusal-and-served-assets',
 'common-sampling-current-422-plan-inventory',
 'common-sampling-current-saved-json-csv-offline-assumption-completeness-regression',
 'common-sampling-current-calendar-bearing-search-json-csv-offline-frozen-assumptions',
 'common-sampling-startup-failure-unchanged-isolated-pass-and-concurrent-run-timeline',
]
selected=[];subjects=[];inputs=set();artifact_count=0
for label in labels:
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=json.loads(p.read_text(encoding='utf-8'))
 assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for name,digest in r['subject']['source_files'].items():assert sha(root/name)==digest,(r['receipt_id'],name)
 subjects.append(r['subject']['source_files'])
 for item in r['subject']['input_manifests']:
  path=(root/item['path']).resolve();path.relative_to(root);assert sha(path)==item['sha256'];inputs.add(path)
 for item in r['artifacts']:
  path=(root/item['path']).resolve();path.relative_to(root);assert review_artifact_allowed(path,root)
  assert sha(path)==item['sha256'] and path.stat().st_size==item['bytes'];artifact_count+=1
 selected.append(dict(receipt=r['receipt_id'],sha256=sha(p),artifacts=len(r['artifacts'])))
assert all(s==subjects[0] for s in subjects)
sources=source_paths();assert {p.relative_to(root).as_posix() for p in sources}==set(subjects[0])
# Keep the unchanged full-run timeout visible beside its separately recorded pass.
failed=sorted((root/'verification/receipts').glob('*-common-sampling-current-full-regression-and-seventeen-module-coverage.json'))[-1]
first=json.loads(failed.read_text(encoding='utf-8'));assert first['command']['exit_code']==1
assert first['subject']['source_files']==subjects[0]
retained=[]
for a in first['artifacts']:
 p=root/a['path'];assert sha(p)==a['sha256'] and p.stat().st_size==a['bytes']
 retained.append(a['path'])
archive_helpers={Path(__file__).resolve()}
paths=set(sources)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))|inputs|archive_helpers
manifest=[]
with zipfile.ZipFile(out/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for path in sorted(p for p in paths if p.is_file()):
  name=path.relative_to(root).as_posix();assert not any(p.startswith('.env') for p in path.parts)
  assert not path.is_relative_to(root/'data') and '/node_modules/' not in name and not name.endswith('.zip')
  assert '/runs/' not in name or path in inputs|archive_helpers
  raw=path.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(out/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(out/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
def get(path):
 with urllib.request.urlopen('http://127.0.0.1:8767'+path,timeout=10) as response:return response.read()
health=json.loads(get('/api/health'));assert health['source_current'] and health['worker_ready'] and health['worker_alive'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
for path in (root/'frontend/dist').rglob('*'):
 if path.is_file():
  relative=path.relative_to(root/'frontend/dist').as_posix();assert get('/' if relative=='index.html' else '/'+relative)==path.read_bytes()
value=dict(scope=__doc__,selected_receipts=selected,retained_failed_receipt=first['receipt_id'],retained_failed_artifacts=retained,artifact_files_checked=artifact_count,source_archive_files=len(manifest),explicit_input_files=len(inputs),served_asset_parity=True,core_hash=health['core_hash'],verification_instance='http://127.0.0.1:8767',isolated_job_store=False,exclusions='Credentials, all traces, source-video media, cached market data and installed dependencies. Not clean-install reproduction, global privacy certification or final acceptance.')
(out/'checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in {'selected_receipts','retained_failed_artifacts'}},indent=2))
