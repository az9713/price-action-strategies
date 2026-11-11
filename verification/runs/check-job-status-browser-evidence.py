"""Independent standard-library reconciliation of downloaded full plans and trial exports."""
from pathlib import Path
import hashlib,json,os,urllib.request
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
browser=root/'verification/runs/20261109T031540293137Z-job-status-desktop-download-cancel-resume-and-derived-cache-repair-first-browser/browser'
base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as response:return response.read()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
health=json.loads(get('/api/health'));assert health['source_current'] and health['worker_ready'] and health['store_lease_held']
observations=sorted(browser.rglob('job-status-observations.json'));assert len(observations)==2
rows=[]
for path in observations:
 observation=json.loads(path.read_text(encoding='utf-8'));download=path.with_name('downloaded-stored-inputs.json');original=json.loads(download.read_text(encoding='utf-8'))
 jid=observation['job_id'];payload=original['payload'];sha=digest(payload)
 assert sha==original['payload_sha256']==observation['payload_sha256']
 assert original['input_provenance']=='prespecified'
 live=json.loads(get('/api/jobs/'+jid+'/inputs'));assert live['payload']==payload and live['payload_sha256']==sha
 status=json.loads(get('/api/jobs/'+jid));assert status['status']=='canceled' and status['index_integrity']
 assert status['index_provenance']=='rebuilt_verified_inputs' and status['payload_sha256']==sha
 assert status['payload']['configuration_count']==1000 and 'configurations' not in status['payload']
 assert 'proposals' not in status['payload']['sampling'] and len(get('/api/jobs/'+jid))<=65536
 configurations=payload['configurations'];config_ids=[digest(c) for c in configurations]
 assert len(configurations)==len(set(config_ids))==1000
 proposals=payload['sampling']['proposals'];accepted=[p['config_id'] for p in proposals if p['status']=='accepted']
 assert accepted==config_ids and payload['sampling']['unique']==1000
 export=json.loads(get('/api/trial-registry/export/json?job_id='+jid))
 assert export['occurrences']==1000 and len(export['rows'])==1000
 assert [r['config_id'] for r in export['rows']]==config_ids
 assert all(r['job_id']==jid and r['provenance']=='prespecified' for r in export['rows'])
 assert observation['planned_occurrences']==1000 and observation['errors']==[]
 pngs=sorted(path.parent.glob('*.png'));assert len(pngs)>=3
 rows.append(dict(job_id=jid,viewport=observation['viewport'],payload_sha256=sha,configurations=1000,accepted_proposals=len(accepted),original_download_sha256=hashlib.sha256(download.read_bytes()).hexdigest(),trial_export_sha256=hashlib.sha256(get('/api/trial-registry/export/json?job_id='+jid)).hexdigest(),original_diagnostics_are_historical=True,screenshot_files=[p.relative_to(root).as_posix() for p in pngs]))
assert sorted(r['viewport']['width'] for r in rows)==[1280,1920]
value=dict(scope=__doc__,rows=rows,core_hash=health['core_hash'],runtime_source_current=True,financial_outcome_certified=False)
(out/'independent-job-status-browser-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
