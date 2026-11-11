"""Current UI/source recovery archive with explicitly scoped unchanged Python evidence.
Not complete acceptance, clean-install reproduction, global privacy or financial-edge certification.
"""
from pathlib import Path
import hashlib,json,os,sys,urllib.request,zipfile,xml.etree.ElementTree as ET
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths,review_artifact_allowed
from backend.lab.research import current_core_hash

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def receipt(label):
    p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=json.loads(p.read_text(encoding='utf-8'))
    assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
    for a in r['artifacts']:
        path=(root/a['path']).resolve();path.relative_to(root);assert review_artifact_allowed(path,root)
        assert sha(path)==a['sha256'] and path.stat().st_size==a['bytes']
    return p,r
current={p.relative_to(root).as_posix():sha(p) for p in source_paths()};records=[];artifacts=0
labels=['result-ownership-atomic-current-source-typed-build','result-ownership-real-overlap-regression-after-atomic-commit','result-ownership-current-ten-desktop-journeys']
for label in labels:
    p,r=receipt(label);assert r['subject']['source_files']==current
    records.append(dict(receipt=r['receipt_id'],sha256=sha(p),scope='Exact current source inventory',artifacts=len(r['artifacts'])));artifacts+=len(r['artifacts'])
for label in ['four-rate-final-current-full-regression-and-fourteen-module-coverage','four-rate-final-current-fourteen-module-numerical-coverage-gate']:
    p,r=receipt(label)
    old=r['subject']['source_files'];unchanged={k:v for k,v in current.items() if not k.startswith('frontend/')}
    assert unchanged=={k:v for k,v in old.items() if not k.startswith('frontend/')}
    differences=sorted(k for k in set(current)|set(old) if current.get(k)!=old.get(k))
    assert differences==['frontend/src/App.tsx','frontend/tests/result-ownership.spec.ts']
    records.append(dict(receipt=r['receipt_id'],sha256=sha(p),scope='Unchanged Python/numerical/specification/test sources; frontend differences disclosed and verified separately',frontend_differences=differences,artifacts=len(r['artifacts'])));artifacts+=len(r['artifacts'])
for path in (root/'frontend/dist').rglob('*'):
    if path.is_file():assert sha(path)==sha(root/'data/sensitivity-browser-instance/frontend/dist'/path.relative_to(root/'frontend/dist'))
with urllib.request.urlopen('http://127.0.0.1:8769/api/health',timeout=10) as response:health=json.load(response)
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['core_hash']==current_core_hash()
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);paths=set(source_paths())|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'));manifest=[]
with zipfile.ZipFile(output/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for p in sorted(p for p in paths if p.is_file()):
        name=p.relative_to(root).as_posix();assert not any(part.lower().startswith('.env') for part in p.parts)
        assert not p.is_relative_to(root/'data') and '/node_modules/' not in name and '/runs/' not in name
        raw=p.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(output/'source-checkpoint.zip') as archive:assert archive.testzip() is None
(output/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
value=dict(scope=__doc__,numerical_core=health['core_hash'],verification_instance='http://127.0.0.1:8769',isolated_job_store=True,served_current_asset_parity=True,receipts=records,artifact_files_checked=artifacts,archive_files=len(manifest),exclusions='Credentials, all traces, source-video media, cached market data and installed dependencies.')
(output/'checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='receipts'},indent=2))
