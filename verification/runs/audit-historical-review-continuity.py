"""Fresh subject audit of immutable originals and unchanged privacy-transform evidence.

Unrelated app edits made the derivation's broad inventory incoherent. This check
does not erase that fact or recertify the app; it verifies the owning privacy code,
policy, executed derivation program and every derived/original artifact instead.
"""
from pathlib import Path
import hashlib,json,os,sys,zipfile
root=Path.cwd();run='20261108T140515886461Z-historical-raw-trace-immutable-derived-review-migration'
folder=root/'verification/runs'/run
receipt=json.loads((root/'verification/receipts'/(run+'.json')).read_text(encoding='utf-8'))
lineage=json.loads((folder/'historical-review-lineage.json').read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert receipt['command']['exit_code']==0 and lineage['failures']==[]
dependencies=['verification/trace_privacy.py','verification/record_check.py']
for name in dependencies:assert sha(root/name)==receipt['subject']['source_files'][name]
inputs={v['path']:v['sha256'] for v in receipt['subject']['input_manifests']}
for name in ['verification/fixtures/trace-privacy-contract.json','verification/runs/historical-trace-review-derivation.py']:
    assert sha(root/name)==inputs[name]
recorded={a['path']:a for a in receipt['artifacts']}
assert sha(folder/'historical-review-lineage.json')==recorded[(folder/'historical-review-lineage.json').relative_to(root).as_posix()]['sha256']
assert len(lineage['rows'])==lineage['original_count']==102
seen=set();rows=[]
for row in lineage['rows']:
    p=(root/row['path']).resolve();p.relative_to(root.resolve());assert '.env' not in p.parts
    assert sha(p)==row['sha256']
    derived=row['derived'];q=(root/derived['path']).resolve();q.relative_to(folder.resolve())
    assert sha(q)==derived['sha256']==recorded[derived['path']]['sha256']
    if derived['path'] not in seen:
        with zipfile.ZipFile(q) as z:
            assert z.comment==b'PA_SANITIZED_TRACE_V1' and z.testzip() is None
            meta=json.loads(z.read('pa-redaction.json'))
            assert meta['source_sha256']==row['sha256'] and meta['policy_version']==1 and meta['trace_schema']==10
            assert meta['unresolved_references']==0 and derived['audit']['privacy_clean'] is True
        seen.add(derived['path'])
    rows.append(dict(original=row['path'],original_sha256=row['sha256'],derived=derived['path'],derived_sha256=derived['sha256']))
assert len(seen)==lineage['unique_review_copies']
result=dict(scope='Current immutable artifact/CRC/manifest and unchanged owning-transform/policy continuity. Prior independently scanned derivation is reused explicitly; no new app/global privacy certification.',
    original_count=len(rows),unique_review_copies=len(seen),owning_transform_current=True,policy_current=True,
    original_files_unchanged=True,derived_files_unchanged=True,all_zip_crc_and_source_manifests_valid=True,
    prior_derivation_receipt=run,prior_broad_inventory_incoherent=True,rows=rows)
output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
(output/'historical-review-current-continuity.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
