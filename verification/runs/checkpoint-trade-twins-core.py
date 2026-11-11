"""Recoverable D046 matching/entry-trace component, not a completed twin workflow."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET,zipfile
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ids=dict(
 baseline='20261109T180654800879Z-trade-twins-isolated-source-only-development-baseline-from-verified-025-archive',
 current='20261109T182720056824Z-trade-twins-current-entry-traces-original-wrapper-aware-split-and-independent-execution-parity',
 gate='20261109T183127747245Z-trade-twins-entry-trace-current-source-matching-core-unrounded-gate-and-actual-db-reconciliation',
 core_mutations='20261109T182047874386Z-trade-twins-ten-actual-cohort-time-geometry-randomness-denominator-and-gate-mutations',
 entry_mutations='20261109T183017262617Z-trade-twins-four-actual-original-entry-atr-stop-ledger-and-capture-mutations',
 plan='20261109T183307053948Z-trade-twins-stage-original-83-422-120-plan-inventory-remains-binding',
 runtime='20261109T183307203390Z-trade-twins-stage-live-025-single-managed-tree-and-all-owned-test-processes-retired')
def receipt(identifier,success=True):
 p=root/'verification/receipts'/(identifier+'.json');r=read(p)
 assert (r['command']['exit_code']==0)==success and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 files={}
 for a in r['artifacts']:
  q=root/a['path'];assert q.resolve().is_relative_to(root.resolve()) and q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path'];files[q.name]=q
 return r,files
records={name:receipt(identifier) for name,identifier in ids.items()}
current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
subject=read(records['current'][1]['dev026-source-subject.json'])
assert subject['source_files']==current and subject['changed_during_check']==[] and len(current)==215
suites=list(ET.parse(records['current'][1]['dev026-junit.xml']).iter('testsuite'))
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert counts==dict(tests=434,failures=0,errors=0,skipped=0)
gate=read(records['gate'][1]['trade-twins-current-core-gate.json'])
assert gate['gate_pass'] and gate['source_files_verified']==215 and gate['module_sha256']==current['backend/lab/trade_twins.py'] and gate['actual_db_matches_recorded_json']
draws=read(records['current'][1]['actual10000-matching-draws.json'])
assert draws['sets']==10000 and draws['matches']==20000 and draws['financial_sets_executed']==0 and draws['python_peak_traced_bytes']<4*1024*1024
mutation_proofs=[]
for key,name,expected,target in [('core_mutations','trade-twins-core-mutations.json',10,'backend/lab/trade_twins.py'),('entry_mutations','trade-twins-entry-trace-mutations.json',4,'backend/lab/engine.py')]:
 proof=read(records[key][1][name]);assert proof['all_assertion_killed'] and proof['original_development_source_unchanged'] and len(proof['mutants'])==expected
 assert proof['baseline']['exit_code']==0 and proof['baseline']['tests']>0 and proof['baseline']['failures']==proof['baseline']['errors']==proof['baseline']['skipped']==0
 for m in proof['mutants']:
  assert m['target']==target and m['original_sha256']==current[target] and m['exit_code']==1 and m['failures']>0 and m['errors']==m['skipped']==0
 mutation_proofs.append(dict(receipt=ids[key],target=target,mutants=expected,green_baseline_cases=proof['baseline']['tests']))
runtime=read(records['runtime'][1]['managed-runtime.json']);native=read(records['runtime'][1]['current-process-tree.json'])
assert runtime['health']['core_hash']=='9bfb4b13b15e0dff2d3548926a2310735dd931399fb30aa8b73bf98082aaba89' and runtime['pending_jobs']==0 and runtime['database_jobs_observed']==348
assert not native['separate_obsolete_project_python_detected'] and len(native['project_python_tree'])==3
assert (root/'verification/fixtures/trade-twins-contract.json').read_bytes()==(source/'verification/fixtures/trade-twins-contract.json').read_bytes()
failures=[]
for identifier,why in [
 ('20261109T181207112616Z-trade-twins-authored-complete-cohort-geometry-before-implementation-assertion-failure','Missing implementation assertion occurred during fixture setup; retained as an error, not a test-body assertion or mutation kill.'),
 ('20261109T181222271493Z-trade-twins-authored-missing-complete-cohort-implementation-test-body-assertion','Actual authored test-body missing-implementation assertion before code.'),
 ('20261109T182517310670Z-trade-twins-authored-original-entry-trace-red-against-unchanged-financial-oracle','Two actual missing entry-trace assertions after existing independent financial parity.'),
 ('20261109T182559468844Z-trade-twins-original-entry-traces-actual-reports-splits-and-unchanged-independent-execution-regression','Seven fixture/reader failures: attempted mutation of frozen Signals and saved wrapper read as inner report; corrected without a financial product-code change.')]:
 r,_=receipt(identifier,False);failures.append(dict(receipt=identifier,reason=why,exit_code=r['command']['exit_code']))
base=root/'verification/runs/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint'
receipt(base.name)
base_manifest=read(base/'integrated025-source-manifest.json')
files={item['path']:source/item['path'] for item in base_manifest}
files.update({name:source/name for name in current})
files['verification/fixtures/trade-twins-contract.json']=source/'verification/fixtures/trade-twins-contract.json'
files['STATUS.md']=root/'STATUS.md'
helpers=['prepare-dev026.py','check-dev026.py','trade-twins-core-mutations.py','trade-twins-entry-trace-mutations.py','check-current-trade-twins-core-gate.py','checkpoint-trade-twins-core.py','trade-twins-next-execution-plan.md']
files.update({'verification/runs/'+name:root/'verification/runs'/name for name in helpers})
manifest=[];archive=out/'trade-twins-source-checkpoint.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,p in sorted(files.items()):
  assert p.is_file() and not p.is_symlink() and not name.startswith(('data/','frontend/node_modules/')) and not any(part.lower().startswith('.env') for part in Path(name).parts)
  assert p.suffix.lower() not in {'.sqlite3','.db','.parquet','.gz','.mp4','.webm','.png','.jpg','.zip'}
  raw=p.read_bytes();z.writestr(name,raw);manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==len(manifest)
 for m in manifest:raw=z.read(m['path']);assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
(out/'trade-twins-source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
probe=subprocess.run([sys.executable,'-c','from backend.lab.research import core_hash,current_core_hash;import json;print(json.dumps(dict(loaded=core_hash(),current=current_core_hash())))'],cwd=source,env=env,capture_output=True,text=True,check=True)
core= json.loads(probe.stdout);assert core['loaded']==core['current']
assert current=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
value=dict(scope=__doc__,source_files=current,isolated_core=core,archive_files=len(manifest),archive_sha256=sha(archive),current_tests=counts,matching_draws=draws,mutation_proofs=mutation_proofs,numerical_gate=gate,
 receipts=ids,retained_failures=failures,main_app=runtime['health'],main_source_replaced=False,original_live_jobs_observed=348,financial_twin_sets_executed=0,all28_module_global_gate_certified=False,final_acceptance_certified=False,
 remaining='Verified original account/entry extractor; both independent financial twin execution interpretations; durable original plans/parts/trials/child/recovery; API/UI/exports; actual10000 financial sets/resources; then integration and remaining full research funnel plus final83/422/120 conformance.',
 recovery_limits='Source only, existing locked environment not installed dependencies. No credentials, cached prices, live DBs, original private coverage DBs/traces or video. Matching rows are not numerical financial accounts. Original receipts/artifacts remain in the workspace and are referenced, not fabricated inside the source archive.')
(out/'trade-twins-component-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(source_files=len(current),archive_files=len(manifest),core=core,tests=counts['tests'],actual_mutants=14,financial_twin_sets_executed=0,main_app_unchanged=True,final_acceptance_certified=False),indent=2))
