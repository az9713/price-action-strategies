"""Unrounded95/90 gate for all five isolated spread modules on identical current sources."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);r=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'));assert r['command']['exit_code']==0
assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
a=next(a for a in r['artifacts'] if a['path'].endswith('/spread-coverage.json'));p=root/a['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'];coverage=json.loads(p.read_text(encoding='utf-8'));gates=[]
for module in ['spread','spread_preparation','spread_jobs','spread_worker','spread_accounts']:
 name='data/dev025/src/backend/lab/'+module+'.py';expected=next(i['sha256'] for i in r['subject']['input_manifests'] if i['path']==name)
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
 s=next(v for k,v in coverage['files'].items() if k.replace('\\','/').endswith('backend/lab/'+module+'.py'))['summary']
 statements=100*s['covered_lines']/s['num_statements'];branches=100*s['covered_branches']/s['num_branches']
 gates.append(dict(module=module,source_sha256=expected,statement_percent=statements,branch_percent=branches,minimum_statements=95,minimum_branches=90,ready=statements>=95 and branches>=90))
value=dict(scope=__doc__,coverage_artifact=a,gates=gates,ready=all(g['ready'] for g in gates),final_acceptance_certified=False)
(out/'spread-five-module-coverage-gates.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2));raise SystemExit(0 if value['ready'] else 1)
