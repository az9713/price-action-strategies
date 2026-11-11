from pathlib import Path
import hashlib,json,re,sys,urllib.request
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.research import current_core_hash
for name in ['STATUS.md','verification/evidence-index.md']:
    p=root/name
    for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        if '://' in link or link.startswith('#'):continue
        target=(p.parent/link.split('#',1)[0]).resolve();target.relative_to(root);assert target.is_file(),link
labels=['current-main-application-four-rate-and-result-ownership-four-desktop-journeys','current-main-eight-rate-accounts-independent-decimal-csv-and-offline-reconciliation','current-main-application-ready-source-worker-and-served-assets','result-ownership-current-scoped-python-and-ui-recovery-checkpoint']
for label in labels:
    p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==0
    assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=10) as response:health=json.load(response)
assert health['source_current'] and health['worker_ready'] and health['worker_alive'] and health['core_hash']==current_core_hash()
print(json.dumps(dict(scope='Current status/evidence/retained-defect snapshot, local-link existence and actual-main readiness. Not all-case acceptance or provider authentication.',main_url='http://127.0.0.1:8767',source_current=True,worker_ready=True,mandatory_cases=422,final_certified_cases=0,snapshot_files=['STATUS.md','verification/evidence-index.md','verification/defects.json'])))
