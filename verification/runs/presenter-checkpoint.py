"""Current code/fixture/build recovery archive and bounded evidence integrity audit."""
from pathlib import Path
import hashlib,json,os,sys,zipfile
import httpx
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths
from backend.lab.research import current_core_hash
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ids=[
'20261108T141545788080Z-presenter-fixed-current-full-regression-and-coverage',
'20261108T141439588995Z-presenter-model-parent-and-signed-zero-focused-regression',
'20261108T141440189697Z-presenter-controls-current-typed-build',
'20261108T141439549029Z-presenter-signed-zero-and-expanded-controls-two-desktop-every-page',
'20261108T141942332748Z-presenter-post-download-independent-visible-fact-and-338-image-reconciliation',
'20261108T141655880161Z-presenter-fixed-current-real-research-two-desktop-regression',
'20261108T141731452146Z-presenter-fixed-current-historical-supplied-signal-independent-account',
'20261108T142629253659Z-historical-102-original-100-review-current-transform-and-artifact-continuity',
'20261108T142817359860Z-presenter-current-eleven-numerical-module-coverage-gate',
'20261108T142817360731Z-presenter-current-plan-inventory-and-links']
checks=[];artifacts=0
for rid in ids:
    p=root/'verification/receipts'/(rid+'.json');r=json.loads(p.read_text(encoding='utf-8'))
    assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
    for name,digest in r['subject']['source_files'].items():assert sha(root/name)==digest
    for a in r['artifacts']:
        q=(root/a['path']).resolve();q.relative_to(root.resolve());assert not q.is_relative_to(root/'data/private-evidence')
        assert not any(part.startswith('.env') for part in q.parts)
        assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts+=1
    checks.append(dict(receipt=rid,sha256=sha(p),artifacts=len(r['artifacts'])))
source=source_paths();full=json.loads((root/'verification/receipts'/(ids[0]+'.json')).read_text(encoding='utf-8'))
assert {p.relative_to(root).as_posix() for p in source}==set(full['subject']['source_files'])
paths=set(source)|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))
paths=sorted(p for p in paths if p.is_file())
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);manifest=[]
with zipfile.ZipFile(output/'source-checkpoint.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in paths:
        name=p.relative_to(root).as_posix()
        assert not any(part.startswith('.env') for part in p.parts)
        assert not p.is_relative_to(root/'data') and '/node_modules/' not in name
        raw=p.read_bytes();z.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
(output/'source-checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
health=httpx.get('http://127.0.0.1:8767/api/health',timeout=10).json()
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['core_hash']==current_core_hash()
result=dict(scope='Current implementation/evidence integrity and code/fixture/build recovery; not final acceptance, privacy certification or clean-install reproduction.',
    core_hash=health['core_hash'],selected_receipts=checks,artifact_files_checked=artifacts,source_archive_files=len(manifest),
    exclusions='Credentials, raw/sanitized traces, source-video media, cached market data and installed dependencies.',source_current=True)
(output/'checkpoint.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='selected_receipts'},indent=2))
