"""Extend the preserved metadata measurement with actual complete HTTP input exports at every scale."""
from pathlib import Path
source=Path('verification/runs/measure-indexed-status-capacity.py').read_text(encoding='utf-8')
old="assert identity(store.job_inputs(jid)['payload'])==before_hash"
new="""begun=time.perf_counter();exported=client.get('/api/jobs/'+jid+'/inputs');export_seconds=time.perf_counter()-begun
   assert exported.status_code==200,exported.text[:200]
   full=exported.json();assert full['payload_sha256']==before_hash and identity(full['payload'])==before_hash
   assert len(full['payload']['configurations'])==count and len(full['payload']['sampling']['proposals'])==proposals
   del full"""
assert source.count(old)==1;source=source.replace(old,new)
needle='immutable_payload_sha256=before_hash'
assert source.count(needle)==1
source=source.replace(needle,'input_export_bytes=len(exported.content),input_export_seconds=export_seconds,'+needle)
exec(compile(source,'indexed-status-capacity-http-inputs-resolved.py','exec'))
