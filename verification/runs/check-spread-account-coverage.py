"""Unrounded95/90 gate for actual spread-account continuation coverage, not release acceptance."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);r=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'));assert r['command']['exit_code']==0
assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
name='data/dev025/src/backend/lab/spread_accounts.py';expected=next(i['sha256'] for i in r['subject']['input_manifests'] if i['path']==name)
assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
a=next(a for a in r['artifacts'] if a['path'].endswith('/spread-coverage.json'));p=root/a['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
c=json.loads(p.read_text(encoding='utf-8'));s=next(v for k,v in c['files'].items() if k.replace('\\','/').endswith('backend/lab/spread_accounts.py'))['summary']
statements=100*s['covered_lines']/s['num_statements'];branches=100*s['covered_branches']/s['num_branches'];ready=statements>=95 and branches>=90
value=dict(scope=__doc__,source_sha256=expected,coverage_artifact=a,statement_percent=statements,branch_percent=branches,minimum_statements=95,minimum_branches=90,ready=ready,final_acceptance_certified=False)
(out/'spread-account-coverage-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2));raise SystemExit(0 if ready else 1)
