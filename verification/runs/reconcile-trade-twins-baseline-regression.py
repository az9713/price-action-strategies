"""Reconcile actual baseline cases after one stronger portable fixture correction.

The original command remains failed. This records per-case lineage and combines
actual coverage only because every measured source byte is unchanged. It is
not a single all-green invocation or final product acceptance certificate.
"""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def receipt(identifier,code):
 r=read(root/'verification/receipts'/(identifier+'.json'));assert r['command']['exit_code']==code
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 artifacts={}
 for a in r['artifacts']:
  p=root/a['path'];assert p.resolve().is_relative_to(root.resolve()) and p.stat().st_size==a['bytes'] and sha(p)==a['sha256'];artifacts[p.name]=p
 return r,artifacts
first_id='20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage'
follow_id='20261109T212549227966Z-trade-twins-original-78-spread-case-followup-with-exact-current-source-isolation'
preimage_id='20261109T212547601751Z-trade-twins-original-failed-spread-isolation-fixture-byte-preimage'
first,fa=receipt(first_id,1);follow,sa=receipt(follow_id,0);preimage,pa=receipt(preimage_id,0)
supplement_id='20261109T213440262549Z-trade-twins-baseline-actual-four-original-journal-status-selection-and-repair-boundaries'
install_id='20261109T213438979415Z-spread-original-boundary-probes-added-to-normal-baseline-and-next-test-discovery'
supplement,ta=receipt(supplement_id,0);installed,ia=receipt(install_id,0)
old=read(fa['dev026-source-subject.json']);new=read(sa['dev026-source-subject.json']);assert old['changed_during_check']==new['changed_during_check']==[]
current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
supplement_subject=read(ta['dev026-source-subject.json']);assert not supplement_subject['changed_during_check']
assert current==supplement_subject['source_files'] and set(new['source_files'])==set(old['source_files']) and len(current)==222
changed=[k for k in old['source_files'] if current[k]!=old['source_files'][k]];assert changed==['tests/test_spread.py']
added=sorted(set(current)-set(old['source_files']));assert added==['tests/test_spread_saved_boundaries.py','tests/test_spread_transaction_boundaries.py']
assert all(current[k]==v for k,v in new['source_files'].items())
installation=read(ia['boundary-test-installation.json'])
for name in added:
 entry=next(e for e in installation['installed_files'] if e['path']=='data/dev026/src/'+name)
 assert current[name]==entry['installed_sha256']
raw=pa['original-test_spread.py'].read_bytes();assert hashlib.sha256(raw).hexdigest()==old['source_files']['tests/test_spread.py']
before='\n'.join(raw.decode('utf-8').splitlines());after='\n'.join((source/'tests/test_spread.py').read_text(encoding='utf-8').splitlines())
needle="assert 'dev025' in str(Path(spread.__file__).resolve())"
replacement="assert Path(spread.__file__).resolve() == (Path(__file__).resolve().parents[1]/'backend/lab/spread.py').resolve()"
assert before.count(needle)==1 and before.replace(needle,replacement,1)==after
def cases(path):
 result={}
 for case in ET.parse(path).iter('testcase'):
  key=case.get('classname')+'::'+case.get('name');assert key not in result
  result[key]=case
 return result
initial=cases(fa['dev026-junit.xml']);resolved=cases(sa['dev026-junit.xml']);assert len(initial)==2642 and len(resolved)==78
extra=cases(ta['dev026-junit.xml']);assert len(extra)==4 and not set(extra)&set(initial)
assert all(all(case.find(k) is None for k in ['failure','error','skipped']) for case in extra.values())
errors={key for key,case in initial.items() if case.find('error') is not None};assert len(errors)==78
assert all(case.find('failure') is None and case.find('skipped') is None for case in initial.values())
for key in errors:
 error=initial[key].find('error');assert error.get('message','').startswith('failed on setup with') and needle in (error.text or '')
 assert key.startswith(('tests.test_spread::','tests.test_spread_faults::')),key
assert set(resolved)==errors and all(all(case.find(k) is None for k in ['failure','error','skipped']) for case in resolved.values())
lineage=[dict(case=key,status='passed',actual_receipt=follow_id if key in errors else first_id,origin='corrected-fixture-followup' if key in errors else 'original-passing-test-body',actual_junit='dev026-junit.xml') for key in sorted(initial)]
lineage+=[dict(case=key,status='passed',actual_receipt=supplement_id,origin='new-normal-discovery-original-boundary-probe',actual_junit='dev026-junit.xml') for key in sorted(extra)]
(out/'case-lineage.json').write_text(json.dumps(dict(scope=__doc__,cases=lineage,counts=dict(tests=2646,passed=2646,unresolved=0),original_global_command_exit_code=1,original_setup_errors=78,followup_passed=78,normal_discovery_boundary_cases=4,single_all_green_invocation=False),indent=2),encoding='utf-8')
fixtures=[]
base=read(root/'verification/runs/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint/integrated025-source-manifest.json')
for item in base:
 if item['path'].startswith('verification/fixtures/'):
  p=source/item['path'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'];fixtures.append(item)
for item in first['subject']['input_manifests']:
 if item['path'].startswith('verification/fixtures/'):
  assert sha(source/item['path'])==item['sha256'];fixtures.append(item)
private=root/'data/private-evidence/development-coverage'/out.name;private.mkdir(parents=True,exist_ok=False)
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1');dbs=[];original_hashes=[]
for label,r,a in [('original',first,fa),('followup',follow,sa),('boundary',supplement,ta)]:
 db=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert db.is_file();original_hashes.append((db,sha(db)))
 rendered=out/(label+'-actual-db-coverage.json')
 subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(db),'-o',str(rendered)],cwd=source,env=env,capture_output=True,text=True,check=True)
 actual=read(rendered);recorded=read(a['coverage.json']);assert actual['files']==recorded['files'] and actual['totals']==recorded['totals']
 copy_path=private/(label+'.coverage');shutil.copyfile(db,copy_path);assert sha(copy_path)==sha(db);dbs.append(copy_path)
combined=private/'.coverage'
merged=subprocess.run([sys.executable,'-m','coverage','combine','--keep','--data-file='+str(combined),*[str(p) for p in dbs]],cwd=source,env=env,capture_output=True,text=True,check=True)
subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(combined),'-o',str(out/'coverage.json')],cwd=source,env=env,capture_output=True,text=True,check=True)
for p,digest in original_hashes:assert sha(p)==digest
coverage=read(out/'coverage.json');files={k.replace('\\','/'):v for k,v in coverage['files'].items()}
spec=importlib.util.spec_from_file_location('actual_baseline_gate',source/'verification/check_numerical_coverage.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);assert len(gate.MODULES)==30
modules=[]
for name in gate.MODULES:
 assert current[name]==old['source_files'][name]
 row=files[name];s=row['summary'];assert not row['excluded_lines'] and s['num_statements']>0 and s['num_branches']>0
 passed=100*s['covered_lines']/s['num_statements']>=95 and 100*s['covered_branches']/s['num_branches']>=90
 modules.append(dict(module=name,sha256=current[name],statements=dict(covered=s['covered_lines'],total=s['num_statements'],required_percent=95),branches=dict(covered=s['covered_branches'],total=s['num_branches'],required_percent=90),exclusions=[],gate_pass=passed))
assert current=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
value=dict(scope=__doc__,original_receipt=first_id,followup_receipt=follow_id,preimage_receipt=preimage_id,boundary_receipt=supplement_id,boundary_installation_receipt=install_id,original_global_command_exit_code=1,single_all_green_invocation=False,tests=dict(tests=2646,passed=2646,unresolved=0),original_passing_bodies=2564,corrected_fixture_cases=78,normal_discovery_boundary_cases=4,
 original_source_files=old['source_files'],current_source_files=current,source_files_verified=len(current),only_modified_existing_file=changed[0],added_test_files=added,exact_guard_correction_verified=True,original_fixture_sha256=old['source_files'][changed[0]],current_fixture_sha256=current[changed[0]],fixture_bindings_verified=len(fixtures),
 modules=modules,actual_coverage_db_sha256=sha(combined),actual_databases_reconcile_with_original_json=True,all30_module_gate_pass=all(m['gate_pass'] for m in modules),final_single_all_green_invocation_still_required=True,final_acceptance_certified=False)
(out/'baseline-regression-reconciliation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
(out/'trade-twins-current-full-gate.json').write_text(json.dumps({k:v for k,v in value.items() if k not in {'original_source_files','current_source_files'}},indent=2),encoding='utf-8')
(out/'baseline-source-subject.json').write_text(json.dumps(dict(source_files=current,changed_during_check=[],source_root='data/dev026/src'),indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'original_source_files','current_source_files','modules'}},indent=2))
assert value['all30_module_gate_pass'],[m for m in modules if not m['gate_pass']]
