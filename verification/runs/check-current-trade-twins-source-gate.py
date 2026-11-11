"""Source-checked actual coverage gate for matching and original-account reader only."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/sys.argv[1]).resolve()
assert p.is_relative_to((root/'verification/receipts').resolve()) and p.suffix=='.json'
r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
artifacts={}
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts[q.name]=q
subject=read(artifacts['dev026-source-subject.json']);current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert current==subject['source_files'] and subject['changed_during_check']==[]
private=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert private.is_file()
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
rendered=out/'rerendered-source-coverage.json'
subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(private),'-o',str(rendered)],cwd=source,env=env,capture_output=True,text=True,check=True)
recorded=read(artifacts['source-coverage.json']);actual=read(rendered)
assert recorded['files']==actual['files'] and recorded['totals']==actual['totals']
files={k.replace('\\','/'):v for k,v in recorded['files'].items()};modules=[]
for name in ['backend/lab/trade_twins.py','backend/lab/trade_twin_source.py']:
 row=files[name];s=row['summary'];assert not row['excluded_lines'] and s['num_statements']>0 and s['num_branches']>0
 assert 100*s['covered_lines']/s['num_statements']>=95 and 100*s['covered_branches']/s['num_branches']>=90
 modules.append(dict(module=name,sha256=current[name],statements=dict(covered=s['covered_lines'],total=s['num_statements'],required_percent=95),branches=dict(covered=s['covered_branches'],total=s['num_branches'],required_percent=90),exclusions=[]))
value=dict(scope=__doc__,receipt=p.relative_to(root).as_posix(),source_files_verified=len(current),modules=modules,actual_coverage_db_sha256=sha(private),actual_db_matches_recorded_json=True,gate_pass=True,all29_modules_global_regression_certified=False,financial_sets_executed=0,final_acceptance_certified=False)
(out/'trade-twins-current-source-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
