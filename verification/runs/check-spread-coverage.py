"""Unrounded95/90 gate for the isolated numerical spread module; not release certification."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);receipt_path=root/sys.argv[1]
receipt=json.loads(receipt_path.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
name='data/dev025/src/backend/lab/spread.py';expected=next(i['sha256'] for i in receipt['subject']['input_manifests'] if i['path']==name)
assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
artifact=next(a for a in receipt['artifacts'] if a['path'].endswith('/spread-coverage.json'));p=root/artifact['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==artifact['sha256']
data=json.loads(p.read_text(encoding='utf-8'));entry=next(v for k,v in data['files'].items() if k.replace('\\','/').endswith('backend/lab/spread.py'));s=entry['summary']
statements=100*s['covered_lines']/s['num_statements'];branches=100*s['covered_branches']/s['num_branches']
value=dict(scope=__doc__,source_sha256=expected,coverage_artifact=artifact['path'],statement_percent=statements,branch_percent=branches,minimum_statements=95,minimum_branches=90,ready=statements>=95 and branches>=90,final_acceptance_certified=False)
(out/'spread-coverage-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2));raise SystemExit(0 if value['ready'] else 1)
