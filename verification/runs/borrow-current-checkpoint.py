"""Current source/fixture/build recovery archive and bounded receipt integrity audit."""
from pathlib import Path
import hashlib,json,os,sys,zipfile,urllib.request
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths,review_artifact_allowed
from backend.lab.research import current_core_hash

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
labels=['borrowing-current-full-regression-and-thirteen-module-coverage', 'borrowing-current-news-research-six-desktop-journeys', 'borrowing-current-two-historical-accounts-independent-decimal-and-offline-reread', 'borrowing-current-news-account-and-offline-independent-regression', 'borrowing-current-basic-browser-books-match-independent-constant-cost-account', 'borrowing-current-constant-cost-historical-reference-regression', 'borrowing-current-422-plan-inventory', 'borrowing-current-thirteen-module-numerical-coverage-gate', 'borrowing-five-isolated-critical-source-mutations', 'borrowing-current-six-signal-and-preprice-source-mutations', 'borrowing-current-final-editor-typed-build']
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
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['core_hash']==current_core_hash()
result=dict(scope=__doc__+' Not final acceptance, global privacy certification or clean-install reproduction.',
    core_hash=health['core_hash'],selected_receipts=checks,artifact_files_checked=artifacts,source_archive_files=len(manifest),
    exclusions='Credentials, all traces, source-video media, cached market data and installed dependencies.')
(output/'checkpoint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='selected_receipts'},indent=2))
