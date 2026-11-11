"""Independent unrounded95/90 coverage gate for each new spread persistence module."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);receipt=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'))
assert receipt['command']['exit_code']==0
subject_artifact=next(a for a in receipt['artifacts'] if a['path'].endswith('/dev025-source-subject.json'));subject_path=root/subject_artifact['path']
assert hashlib.sha256(subject_path.read_bytes()).hexdigest()==subject_artifact['sha256']
subject=json.loads(subject_path.read_text(encoding='utf-8'));assert not subject['changed_during_check'] and subject['child_exit_code']==0
artifact=next(a for a in receipt['artifacts'] if a['path'].endswith('/spread-coverage.json'));path=root/artifact['path']
assert hashlib.sha256(path.read_bytes()).hexdigest()==artifact['sha256']
coverage=json.loads(path.read_text(encoding='utf-8'));gates=[]
for module in ['spread','spread_preparation','spread_jobs','spread_worker']:
 name='data/dev025/src/backend/lab/'+module+'.py';expected=next(i['sha256'] for i in receipt['subject']['input_manifests'] if i['path']==name)
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
 entry=next(v for k,v in coverage['files'].items() if k.replace('\\','/').endswith('backend/lab/'+module+'.py'));s=entry['summary']
 statements=100*s['covered_lines']/s['num_statements'];branches=100*s['covered_branches']/s['num_branches']
 gates.append(dict(module=module,source_sha256=expected,statement_percent=statements,branch_percent=branches,minimum_statements=95,minimum_branches=90,ready=statements>=95 and branches>=90))
value=dict(scope=__doc__,coverage_artifact=artifact['path'],gates=gates,ready=all(g['ready'] for g in gates),final_acceptance_certified=False)
(out/'spread-durable-coverage-gates.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2));raise SystemExit(0 if value['ready'] else 1)
