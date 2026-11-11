"""Exact cached/uncached complete scientific payload parity; validate every expected source-version difference separately."""
from pathlib import Path
import gzip,hashlib,json,os,sys
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.service import Lab
from backend.lab.config import identity
lab=Lab(root/'data/capacity-real-instance');out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);records=[]
def result(label):
 path=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];receipt=json.loads(path.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
 matches=[a for a in receipt['artifacts'] if a['path'].endswith('capacity-summary.json')];assert len(matches)==1
 artifact=matches[0];raw=(root/artifact['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==artifact['sha256'];return json.loads(raw)
def normalized_report(report,core):
 value=dict(report);assert value.pop('core_hash')==core;contract=value.pop('numerical_contract');assert identity(contract)==core
 return value
for count,label,old_jid in [(100,'numerical-capacity-cached-100-real-one-session-repeat-pilot','648920baa0654d6b8931777932c7da14'),(1000,'numerical-capacity-cached-1000-real-one-session-execution','887ff833ae2343e5b8e35a67fcb3b9d8')]:
 measured=result(label);old_job=lab.store.job(old_jid);old_root=lab.result(old_jid);old_payload=old_job['payload'];old_core=old_payload['core_hash'];assert old_core=='ca8fb84ac836438ca06565078bad9ae0392b06baf4916c5951c52e2ffb5be933'
 for measurement in measured['measurements']:
  jid=measurement['job_id'];job=lab.store.job(jid);saved=lab.result(jid);new_payload=job['payload'];core=new_payload['core_hash'];assert core==measured['core_hash'] and core!=old_core
  old_inputs=dict(old_payload);new_inputs=dict(new_payload);assert old_inputs.pop('core_hash')==old_core and new_inputs.pop('core_hash')==core;assert old_inputs==new_inputs
  new_payload_hash=identity(new_payload);old_payload_hash=identity(old_payload)
  assert saved['payload_hash']==new_payload_hash and old_root['payload_hash']==old_payload_hash
  assert len(saved['rows'])==len(old_root['rows'])==count;parts=[]
  for before,after in zip(old_root['rows'],saved['rows']):
   a=dict(before);b=dict(after);old_sha=a.pop('report_sha256');new_sha=b.pop('report_sha256');assert a==b
   containers=[]
   for job_id,row,sha,payload_hash,expected_core in [(old_jid,before,old_sha,old_payload_hash,old_core),(jid,after,new_sha,new_payload_hash,core)]:
    path=lab.root/'data/jobs'/job_id/'parts'/(str(row['part']).zfill(6)+'.json.gz');raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
    container=json.loads(gzip.decompress(raw));assert container['config_id']==row['config_id'] and container['payload_hash']==payload_hash and container['core_hash']==expected_core
    normalized=dict(container);assert normalized.pop('core_hash')==expected_core;assert normalized.pop('payload_hash')==payload_hash;normalized['report']=normalized_report(normalized['report'],expected_core);containers.append(normalized)
   assert containers[0]==containers[1],(count,jid,before['part'])
   parts.append(dict(part=before['part'],config_id=before['config_id'],uncached_sha256=old_sha,cached_sha256=new_sha,scientific_payload_sha256=identity(containers[0])))
  records.append(dict(count=count,replica=measurement['replica'],uncached_job_id=old_jid,cached_job_id=jid,uncached_core=old_core,cached_core=core,complete_account_parts=count,financial_fields_omitted=0,source_provenance_validated=True,parts=parts))
assert sum(r['complete_account_parts'] for r in records)==1200
value=dict(scope=__doc__,comparisons=records,exact_complete_scientific_accounts=1200,financial_fields_omitted=0,excluded_fields='Only separately validated core_hash, numerical_contract and payload_hash. Complete inputs differ only in core_hash. All scientific/accounting/chart/assumption values compare exactly.');(out/'cached-uncached-complete-accounts.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(exact_complete_scientific_accounts=1200,financial_fields_omitted=0,source_versions_separately_validated=True,scope=__doc__)))
