"""Current source/fixture/build recovery archive and bounded receipt integrity audit."""
from pathlib import Path
import hashlib,json,os,sys,zipfile,urllib.request
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths,review_artifact_allowed
from backend.lab.research import current_core_hash

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
labels=['runtime-capacity-current-full-regression-and-fifteen-module-coverage', 'runtime-capacity-current-fifteen-module-numerical-coverage-gate', 'runtime-capacity-current-typed-frontend-build', 'runtime-capacity-final-owner-replacement-real-parent-crash-and-sigint-regression', 'runtime-capacity-current-100-search-and-complete-baseline-account-equivalence', 'runtime-capacity-current-1000-search-and-all-complete-baseline-account-equivalence', 'runtime-main-after-clean-managed-restart-current-assets-and-duplicate-refusal', 'runtime-capacity-current-main-fourteen-desktop-workflow-journeys', 'runtime-capacity-main-six-joint-study-accounts-independent-decimal-csv-offline', 'runtime-capacity-main-twenty-existing-browser-accounts-independent-decimal', 'runtime-capacity-current-main-historical-saved-replay-after-registry-route-correction', 'runtime-capacity-eight-prescribed-source-mutation-domains', 'runtime-capacity-current-five-study-source-mutations', 'runtime-capacity-current-five-borrow-source-mutations', 'runtime-capacity-current-six-signal-preprice-source-mutations', 'runtime-capacity-current-four-sensitivity-source-mutations', 'runtime-capacity-current-422-plan-inventory', 'runtime-main-before-managed-stop-owned-process-objects', 'runtime-main-clean-managed-stop-all-owned-objects-exited-and-lease-released', 'runtime-ownership-actual-main-duplicate-other-port-refused-and-obsolete-instances-closed']
checks=[];artifacts=0;subjects=[]
for label in labels:
    path=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1]
    receipt=json.loads(path.read_text(encoding='utf-8'))
    assert receipt['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
    for name,digest in receipt['subject']['source_files'].items():assert sha(root/name)==digest
    subjects.append(receipt['subject']['source_files'])
    for item in receipt['artifacts']:
        p=(root/item['path']).resolve();p.relative_to(root)
        assert not any(part.startswith('.env') for part in p.parts) and review_artifact_allowed(p,root)
        assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes'];artifacts+=1
    checks.append(dict(receipt=receipt['receipt_id'],sha256=sha(path),artifacts=len(receipt['artifacts'])))
assert all(subject==subjects[0] for subject in subjects)
sources=source_paths();assert {p.relative_to(root).as_posix() for p in sources}==set(subjects[0])
paths=set(sources)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);manifest=[]
with zipfile.ZipFile(output/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in sorted(p for p in paths if p.is_file()):
        name=p.relative_to(root).as_posix();assert not any(part.startswith('.env') for part in p.parts)
        assert not p.is_relative_to(root/'data') and '/node_modules/' not in name and '/runs/' not in name
        raw=p.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(output/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(output/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as response:health=json.load(response)
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['store_lease_held'] and health['core_hash']==current_core_hash()
for path in (root/'frontend/dist').rglob('*'):
    if path.is_file():
        relative=path.relative_to(root/'frontend/dist').as_posix()
        url='http://127.0.0.1:8767'+('/' if relative=='index.html' else '/'+relative)
        with urllib.request.urlopen(url,timeout=10) as response:assert response.read()==path.read_bytes()
result=dict(verification_instance='http://127.0.0.1:8767',isolated_job_store=False,served_asset_parity=True,scope=__doc__+' Not final acceptance, global privacy certification or clean-install reproduction.',
    core_hash=health['core_hash'],selected_receipts=checks,artifact_files_checked=artifacts,source_archive_files=len(manifest),
    exclusions='Credentials, all traces, source-video media, cached market data and installed dependencies.')
(output/'checkpoint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='selected_receipts'},indent=2))
