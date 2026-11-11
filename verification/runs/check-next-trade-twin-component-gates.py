"""Actual current-source gates for six trade-twin modules, not all33 modules."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/sys.argv[1]).resolve();assert p.is_relative_to((root/'verification/receipts').resolve());r=read(p)
assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
artifacts={}
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts[q.name]=q
for a in r['subject']['input_manifests']:assert sha(root/a['path'])==a['sha256']
subject=read(artifacts['next-stage-source-subject.json']);current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert current==subject['source_files'] and not subject['changed_during_check'] and subject['frozen_baseline_unchanged']
private=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert private.is_file()
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(private),'-o',str(out/'rerendered-coverage.json')],cwd=source,env=env,capture_output=True,text=True,check=True)
recorded=read(artifacts['coverage.json']);actual=read(out/'rerendered-coverage.json');assert recorded['files']==actual['files'] and recorded['totals']==actual['totals']
files={k.replace('\\','/'):v for k,v in actual['files'].items()};modules=[]
for module in ['trade_twins','trade_twin_source','trade_twin_execution','trade_twin_features','trade_twin_amounts','trade_twin_results']:
 name='backend/lab/'+module+'.py';row=files[name];s=row['summary'];assert not row['excluded_lines'] and s['num_statements']>0 and s['num_branches']>0
 passed=100*s['covered_lines']/s['num_statements']>=95 and 100*s['covered_branches']/s['num_branches']>=90
 modules.append(dict(module=name,sha256=current[name],statements=dict(covered=s['covered_lines'],total=s['num_statements'],required_percent=95),branches=dict(covered=s['covered_branches'],total=s['num_branches'],required_percent=90),exclusions=[],gate_pass=passed))
suites=list(ET.parse(artifacts['next-stage-junit.xml']).iter('testsuite'));counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert counts==dict(tests=849,failures=0,errors=0,skipped=0)
value=dict(scope=__doc__,receipt=r['receipt_id'],source_files_verified=len(current),tests=counts,modules=modules,actual_coverage_db_sha256=sha(private),actual_db_matches_recorded_json=True,all_six_component_gates_pass=all(m['gate_pass'] for m in modules),all33_module_global_gate_certified=False,final_acceptance_certified=False)
(out/'next-six-component-gates.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2));assert value['all_six_component_gates_pass']
