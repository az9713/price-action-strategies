"""Current staged complete backend source and thirty numerical module coverage.

Re-render the actual coverage database; never merge a prior source's hits or
promote this check to the original 422-case acceptance certificate.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/sys.argv[1]).resolve();assert p.is_relative_to((root/'verification/receipts').resolve())
r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
artifacts={}
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts[q.name]=q
subject=read(artifacts['dev026-source-subject.json']);current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert current==subject['source_files'] and subject['changed_during_check']==[]
private=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert private.is_file()
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
rendered=out/'rerendered-coverage.json'
subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(private),'-o',str(rendered)],cwd=source,env=env,capture_output=True,text=True,check=True)
recorded=read(artifacts['coverage.json']);actual=read(rendered)
assert recorded['files']==actual['files'] and recorded['totals']==actual['totals']
spec=importlib.util.spec_from_file_location('actual_staged_gate',source/'verification/check_numerical_coverage.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
assert len(gate.MODULES)==30
files={k.replace('\\','/'):v for k,v in recorded['files'].items()};modules=[]
for name in gate.MODULES:
 row=files[name];s=row['summary'];assert not row['excluded_lines'] and s['num_statements']>0 and s['num_branches']>0
 passed=100*s['covered_lines']/s['num_statements']>=95 and 100*s['covered_branches']/s['num_branches']>=90
 modules.append(dict(module=name,sha256=current[name],statements=dict(covered=s['covered_lines'],total=s['num_statements'],required_percent=95),branches=dict(covered=s['covered_branches'],total=s['num_branches'],required_percent=90),exclusions=[],gate_pass=passed))
suites=list(ET.parse(artifacts['dev026-junit.xml']).iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert counts['tests']>2600 and counts['failures']==counts['errors']==counts['skipped']==0
value=dict(scope=__doc__,receipt=p.relative_to(root).as_posix(),source_files_verified=len(current),modules=modules,tests=counts,actual_coverage_db_sha256=sha(private),actual_db_matches_recorded_json=True,all30_module_gate_pass=all(m['gate_pass'] for m in modules),financial_sets_executed=0,final_acceptance_certified=False)
(out/'trade-twins-current-full-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2));assert value['all30_module_gate_pass']
