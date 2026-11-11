"""Read known captured session values in memory only; never output their values/hashes."""
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import os
import zipfile

root=Path.cwd()
review=root/'verification/runs/20261108T132745002841Z-fresh-private-raw-and-sanitized-two-desktop-browser-journeys/browser'
meta=json.loads((review/'capture-metadata.json').read_text(encoding='utf-8'))
raw=root/'data/private-evidence/captures'/meta['private_capture_id']
assert raw.resolve().is_relative_to((root/'data/private-evidence/captures').resolve())
assert meta['child_exit_code']==0
known=set();headers=0;archives=0;unchanged_images=0;unchanged_financial=0
original_hashes={p.relative_to(raw).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.rglob('*') if p.is_file() and p.name!='.env'}
for p in raw.rglob('trace.zip'):
    archives+=1
    with zipfile.ZipFile(p) as z:
        for name in z.namelist():
            if name.endswith('.network'):
                for line in z.read(name).decode('utf-8').splitlines():
                    row=json.loads(line)
                    request=row.get('snapshot',{}).get('request',{})
                    for header in request.get('headers',[]):
                        if header.get('name','').lower()=='x-lab-token':
                            value=header['value'];assert len(value)>=8;known.add(value);headers+=1
assert archives==2 and headers>0 and known
variants={v.encode() for k in known for v in [k,quote(k,safe=''),json.dumps(k)[1:-1]]}
files=0
for p in review.rglob('*'):
    if not p.is_file():continue
    assert p.name!='.env';files+=1
    with zipfile.ZipFile(p) if p.suffix=='.zip' else open(os.devnull,'rb') as z:
        blocks=[z.read(n) for n in z.namelist()] if p.suffix=='.zip' else [p.read_bytes()]
        assert all(v not in block for v in variants for block in blocks),'Captured session credential survives derivation.'
    relative=p.relative_to(review);source=raw/relative
    if p.suffix=='.png' and source.is_file():
        assert p.read_bytes()==source.read_bytes();unchanged_images+=1
    if p.name.startswith('downloaded-') and p.suffix in {'.json','.csv'} and source.is_file():
        assert p.read_bytes()==source.read_bytes();unchanged_financial+=1
after={p.relative_to(raw).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in raw.rglob('*') if p.is_file() and p.name!='.env'}
assert after==original_hashes and unchanged_images>=16 and unchanged_financial>=2
result=dict(scope='Independent in-memory known-session-value scan of every uncompressed current review artifact; not an unknown-secret/image oracle.',
    raw_child_exit_code=meta['child_exit_code'],raw_archives=archives,credential_header_occurrences=headers,
    distinct_captured_session_values=len(known),review_files=files,known_values_absent=True,raw_files_unchanged=len(after),
    unchanged_images=unchanged_images,unchanged_financial_exports=unchanged_financial)
output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
(output/'independent-privacy-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
