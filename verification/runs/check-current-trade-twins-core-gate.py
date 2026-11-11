"""Current isolated matching/summary source and actual-coverage numerical gate only."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/(sys.argv[1] if len(sys.argv)>1 else 'verification/receipts/20261109T182720056824Z-trade-twins-current-entry-traces-original-wrapper-aware-split-and-independent-execution-parity.json')).resolve()
assert p.is_relative_to((root/'verification/receipts').resolve()) and p.suffix=='.json'
r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
artifacts={}
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts[q.name]=q
subject=read(artifacts['dev026-source-subject.json']);current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert current==subject['source_files'] and subject['changed_during_check']==[]
private=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert private.is_file()
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
rendered=out/'rerendered-twins-coverage.json'
result=subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(private),'-o',str(rendered)],cwd=source,env=env,capture_output=True,text=True,check=True)
recorded=read(artifacts['twins-coverage.json']);actual=read(rendered)
assert recorded['files']==actual['files'] and recorded['totals']==actual['totals']
files={k.replace('\\','/'):v for k,v in recorded['files'].items()};name='backend/lab/trade_twins.py';row=files[name]
summary=row['summary'];statements=summary['num_statements'];branches=summary['num_branches']
assert not row['excluded_lines'] and 0<statements and 0<branches
assert 100*summary['covered_lines']/statements>=95 and 100*summary['covered_branches']/branches>=90
assert row['missing_lines']==[] and row['missing_branches']==[]
value=dict(scope=__doc__,receipt=p.relative_to(root).as_posix(),source_files_verified=len(current),module=name,module_sha256=current[name],actual_coverage_db_sha256=sha(private),actual_db_matches_recorded_json=True,
 statements=dict(covered=summary['covered_lines'],total=statements,required_percent=95),branches=dict(covered=summary['covered_branches'],total=branches,required_percent=90),
 gate_pass=True,exclusions=[],all28_modules_global_regression_certified=False,financial_sets_executed=0,final_acceptance_certified=False)
(out/'trade-twins-current-core-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
