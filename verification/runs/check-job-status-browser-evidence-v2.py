"""Preserve the first audit; distinguish browser-normalized JSON from canonical stored input."""
from pathlib import Path
source=Path('verification/runs/check-job-status-browser-evidence.py').read_text(encoding='utf-8')
old="jid=observation['job_id'];payload=original['payload'];sha=digest(payload)"
new="""jid=observation['job_id'];live_raw=get('/api/jobs/'+jid+'/inputs');live=json.loads(live_raw)
 assert original['payload']==live['payload']
 # JSON.stringify preserves numeric values but spells integral floats as integers.
 # Audit canonical Python input types from the actual current input download;
 # separately retain the browser artifact's semantic equality and original hash.
 (out/(jid+'-canonical-stored-inputs.json')).write_bytes(live_raw)
 payload=live['payload'];sha=digest(payload)"""
assert source.count(old)==1;source=source.replace(old,new)
source=source.replace("original_diagnostics_are_historical=True,","original_diagnostics_are_historical=True,browser_artifact_is_json_stringify_normalized=True,canonical_hash_source='Actual complete stored-input HTTP download; browser artifact separately equals its payload semantically',")
exec(compile(source,'job-status-independent-evidence-v2-resolved.py','exec'))
