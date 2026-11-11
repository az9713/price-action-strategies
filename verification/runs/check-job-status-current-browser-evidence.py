"""Apply the canonical/semantic independent audit to the current recorded browser run."""
from pathlib import Path
import json
receipt=sorted(Path('verification/receipts').glob('*-bounded-job-monitoring-current-two-desktop-controls-and-result-ownership.json'))[-1]
value=json.loads(receipt.read_text(encoding='utf-8'));assert value['command']['exit_code']==0
old='verification/runs/20261109T031540293137Z-job-status-desktop-download-cancel-resume-and-derived-cache-repair-first-browser/browser'
new='verification/runs/'+value['receipt_id']+'/browser'
wrapper=Path('verification/runs/check-job-status-browser-evidence-v2.py').read_text(encoding='utf-8')
needle="source=Path('verification/runs/check-job-status-browser-evidence.py').read_text(encoding='utf-8')"
assert wrapper.count(needle)==1
wrapper=wrapper.replace(needle,needle+".replace("+repr(old)+","+repr(new)+")")
read_export="export=json.loads(get('/api/trial-registry/export/json?job_id='+jid))"
save_export="export_raw=get('/api/trial-registry/export/json?job_id='+jid);export=json.loads(export_raw)\n (out/(jid+'-complete-trial-export.json')).write_bytes(export_raw)"
hash_export="hashlib.sha256(get('/api/trial-registry/export/json?job_id='+jid)).hexdigest()"
transform="source=source.replace("+repr(read_export)+","+repr(save_export)+").replace("+repr(hash_export)+",'hashlib.sha256(export_raw).hexdigest()')\n"
assert wrapper.count('exec(compile(source,')==1
wrapper=wrapper.replace('exec(compile(source,',transform+'exec(compile(source,')
exec(compile(wrapper,'job-status-current-independent-evidence-resolved.py','exec'))
