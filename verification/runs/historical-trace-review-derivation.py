"""Immutable legacy traces -> separate policy-scoped review copies, never in place."""
from pathlib import Path
from urllib.parse import quote
import hashlib
import json
import os
import sys
import zipfile
sys.path.insert(0,str(Path.cwd()))
from verification.trace_privacy import sanitize_archive,audit_archive,PrivacyError

root=Path.cwd();output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);inventory=[]
for path in sorted((root/'verification/runs').rglob('*.zip')):
    if path.is_relative_to(output):continue
    try:
        with zipfile.ZipFile(path) as z:
            if z.comment==b'PA_SANITIZED_TRACE_V1' or not any(n.endswith('.trace') for n in z.namelist()):continue
    except zipfile.BadZipFile:continue
    inventory.append(dict(path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
(output/'original-inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
by_hash={};rows=[];failures=[]
for number,item in enumerate(inventory):
    source=root/item['path'];digest=item['sha256']
    try:
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise PrivacyError('Historical original changed.')
        if digest not in by_hash:
            target=output/'review'/('trace-'+digest+'.zip')
            derived=sanitize_archive(source,target,[(str(root),'<workspace>'),(str(Path.home()),'<user-home>')])
            audit=audit_archive(target)
            if audit['unresolved_references']:raise PrivacyError('Unresolved derived resources.')
            # Independent extraction of actual captured session-header values.
            known=set()
            with zipfile.ZipFile(source) as z:
                for name in z.namelist():
                    if name.endswith('.network'):
                        for line in z.read(name).decode('utf-8').splitlines():
                            request=json.loads(line).get('snapshot',{}).get('request',{})
                            for h in request.get('headers',[]):
                                if h.get('name','').lower()=='x-lab-token' and len(h.get('value',''))>=8:known.add(h['value'])
            variants={v.encode() for k in known for v in [k,quote(k,safe=''),json.dumps(k)[1:-1]]}
            with zipfile.ZipFile(target) as z:
                for name in z.namelist():
                    raw=z.read(name)
                    if any(v in raw for v in variants):raise PrivacyError('Known historical session value remains.')
            by_hash[digest]=dict(path=target.relative_to(root).as_posix(),sha256=derived['sanitized_sha256'],
                counts=derived['counts'],audit=audit,independent_known_session_values_checked=len(known))
        if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise PrivacyError('Historical original changed during derivation.')
        rows.append(item|{'derived':by_hash[digest],'original_status':'Preserved unchanged local/private; excluded from release/review bundles.'})
    except (PrivacyError,ValueError,OSError,KeyError) as error:
        failures.append(dict(path=item['path'],error_type=type(error).__name__,reason='Historical trace derivation failed; original retained.'))
    if (number+1)%10==0:print(json.dumps(dict(originals_processed=number+1,unique_review_copies=len(by_hash),failures=len(failures))),flush=True)
result=dict(policy=1,scope='Recognized credential contexts and discovered long-value propagation; not arbitrary unknown image/file secrets.',
    original_count=len(inventory),unique_review_copies=len(by_hash),rows=rows,failures=failures,
    supersession='Derived review copies supplement immutable original receipts; original hashes/claims are not rewritten.')
(output/'historical-review-lineage.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(original_count=len(inventory),unique_review_copies=len(by_hash),failures=len(failures),originals_preserved=True)))
if failures:raise SystemExit(1)
