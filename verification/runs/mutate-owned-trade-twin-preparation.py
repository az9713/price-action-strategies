"""Six actual preparation mutations; only clean test-body assertions count."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
private=root/'data/private-evidence/owned-preparation-mutations'/out.name
private.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(root))
from verification.record_check import source_paths

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def snapshot():return {p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}

target='backend/lab/trade_twin_preparation.py';test='tests/test_trade_twin_durable_preparation.py::'
specs=[
 ('missing-original-seal-repair',"            if trial['artifact_sha256'] is not None or trial['state'] in {'checkpointed', 'completed'}:",
  '            if False:',test+'test_sealed_original_preparation_corruption_cannot_be_repaired_or_replaced[missing_seal]'),
 ('drop-original-cohort',"plan = prepare_plan(source['sources'], features['moments']", "plan = prepare_plan([], features['moments']",
  test+'test_original_plan_is_durably_sealed_before_any_candidate_finance_and_reused_on_resume'),
 ('ignore-authoritative-actions',"actions_hash=identity([asdict(a) for a in actions])",'actions_hash=identity([])',
  test+'test_real_original_corporate_actions_are_bound_to_preparation'),
 ('adopt-self-consistent-false-plan',"            value = prepared['sealed']", "            value = prior[1] if prior is not None else prepared['sealed']",
  test+'test_original_seal_bounds_order_attempt_and_rehashed_false_plan_are_refused[consistent_false_plan]'),
 ('omit-closing-authority',"            closing = verify_child(lab, job, controlled)", '            closing = source',
  test+'test_closing_original_authority_failure_preserves_uncommitted_attempt_and_never_seals'),
 ('seal-without-original-checkpoint',"                lab.store._trials.checkpoint_owned(db, job['id'], 0, 'prepare', owner, value, seal['sha256'])",
  '                pass  # mutation: publish a seal without a trial checkpoint',
  test+'test_original_plan_is_durably_sealed_before_any_candidate_finance_and_reused_on_resume')]
before=snapshot();original=(source/target).read_bytes();newline=b'\r\n' if b'\r\n' in original else b'\n'
for name,old,new,selected in specs:assert original.count(old.encode().replace(b'\n',newline))==1,name

def clone(name):
 folder=root/'data/dev026/opm'/out.name.split('-')[0]/name;folder.mkdir(parents=True,exist_ok=False)
 paths=list((source/'backend').rglob('*.py'))+list((source/'tests').rglob('*.py'))+list((source/'verification').glob('*.py'))+list((source/'verification/fixtures').rglob('*.json'))
 paths += [source/p for p in ['pyproject.toml','requirements.lock','RULEBOOK.md','strategy.schema.json','verification/catalog.json']]
 for path in paths:
  dest=folder/path.relative_to(source);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
 return folder

def run(folder,name,selected):
 dest=out/name;dest.mkdir();junit=dest/'junit.xml';env=os.environ.copy()
 env.update(PYTHONPATH=str(folder),PYTHONNOUSERSITE='1',PA_EVIDENCE_RUN_DIR=str(dest))
 process=subprocess.run([sys.executable,'-m','pytest','-q',*selected,'--junitxml='+str(junit)],cwd=folder,env=env,capture_output=True,timeout=300)
 (private/(name+'-stdout.log')).write_bytes(process.stdout);(private/(name+'-stderr.log')).write_bytes(process.stderr)
 suites=list(ET.parse(junit).iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
 failures=list(ET.parse(junit).iter('failure'));assertions=bool(failures) and all('AssertionError' in (f.text or '') or 'DID NOT RAISE' in (f.text or '') or f.attrib.get('message','').startswith('assert ') for f in failures)
 return dict(name=name,exit_code=process.returncode,counts=counts,assertion_only=assertions,selected_tests=selected,raw_stdout_sha256=sha(private/(name+'-stdout.log')),raw_stderr_sha256=sha(private/(name+'-stderr.log')))

selected=list(dict.fromkeys(s[3] for s in specs));baseline=run(clone('baseline'),'baseline',selected)
assert baseline['exit_code']==0 and baseline['counts']==dict(tests=len(selected),failures=0,errors=0,skipped=0),baseline
rows=[]
for name,old,new,selected in specs:
 folder=clone(name);mutated=original.replace(old.encode().replace(b'\n',newline),new.encode().replace(b'\n',newline),1);(folder/target).write_bytes(mutated)
 assert sha(folder/target)==hashlib.sha256(mutated).hexdigest()
 result=run(folder,name,[selected]);result.update(original_sha256=hashlib.sha256(original).hexdigest(),mutated_sha256=sha(folder/target));rows.append(result)
 assert result['exit_code']==1 and result['counts']['failures']>0 and result['counts']['errors']==result['counts']['skipped']==0 and result['assertion_only'],result
 print(json.dumps(dict(name=name,assertion_killed=True,counts=result['counts'])),flush=True)
assert before==snapshot(),'Actual development source changed during mutations.'
(out/'owned-preparation-mutations.json').write_text(json.dumps(dict(scope=__doc__,baseline=baseline,mutations=rows,source_files=before,source_unchanged=True,assertion_kills=len(rows),financial_sets_executed=0,final_product_acceptance=False),indent=2),encoding='utf-8')
print(json.dumps(dict(assertion_kills=len(rows),source_unchanged=True)),flush=True)
