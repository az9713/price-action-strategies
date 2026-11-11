"""Source-only foundation archive and actual fresh-directory restoration.

Existing locked dependencies are reused. This is not release/final acceptance.
No environment file, price cache, user database or installed dependency is read.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root))
from verification.record_check import source_paths


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def snapshot():return {p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}


before=snapshot()
references=[
 '20261109T223427973904Z-trade-twins-owned-preparation-actions-closing-authority-atomic-seal-resume-and-trial-compatibility',
 '20261109T224135319592Z-trade-twins-owned-preparation-original-fault-boundaries-rehashed-plan-and-three-actual-interpreter-deaths',
 '20261109T224555920288Z-trade-twins-owned-preparation-actual-database-95-90-and-three-death-recovery-gate',
 '20261109T222605687886Z-trade-twins-eight-actual-current-original-reservation-and-rollback-mutations']
receipts=[]
for identifier in references:
 path=root/'verification/receipts'/(identifier+'.json');receipt=read(path)
 assert receipt['command']['exit_code']==0
 assert not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
 receipts.append(dict(receipt=identifier,sha256=sha(path)))
# The production code remains identical to the passing28-case source subject.
# One stricter checkpoint-state assertion was added afterward; mutation baseline
# and the actual restored checks execute that current test body.
original=read(root/'verification/runs'/references[1]/'next-stage-source-subject.json')
for name,digest in original['source_files'].items():
 if not name.startswith('tests/'):assert before.get(name)==digest,name
test_differences=[name for name in before if name.startswith('tests/') and before[name]!=original['source_files'].get(name)]
assert test_differences==['tests/test_trade_twin_durable_preparation.py'],test_differences

paths=source_paths(source)+list((source/'verification/fixtures').rglob('*.json'))+list((source/'frontend/dist').rglob('*'))
paths=sorted(set(p for p in paths if p.is_file()),key=lambda p:p.relative_to(source).as_posix())
entries=[]
for path in paths:
 relative=path.relative_to(source).as_posix()
 assert all(not part.lower().startswith('.env') for part in Path(relative).parts)
 assert not any(part in {'node_modules','.venv','private-evidence','__pycache__'} for part in Path(relative).parts)
 assert path.suffix.lower() not in {'.sqlite3','.parquet','.db','.coverage','.trace','.mp4'}
 entries.append(dict(path=relative,sha256=sha(path),bytes=path.stat().st_size))
archive=out/'owned-trade-twin-foundation-source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
 for entry in entries:bundle.write(source/entry['path'],entry['path'])

restored=root/'data/dev026/reconstructions'/out.name
restored.mkdir(parents=True,exist_ok=False)
with zipfile.ZipFile(archive) as bundle:
 assert sorted(bundle.namelist())==sorted(e['path'] for e in entries)
 for entry in entries:
  target=(restored/entry['path']).resolve();assert target.is_relative_to(restored.resolve())
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(bundle.read(entry['path']))
for entry in entries:assert sha(restored/entry['path'])==entry['sha256']


def core(folder):
 env=os.environ.copy();env.update(PYTHONPATH=str(folder),PYTHONNOUSERSITE='1')
 result=subprocess.run([sys.executable,'-c',"from backend.lab.research import core_hash,current_core_hash;assert core_hash()==current_core_hash();print(core_hash())"],cwd=folder,env=env,capture_output=True,text=True,timeout=30)
 assert result.returncode==0,result.stderr
 value=result.stdout.strip();assert len(value)==64 and all(c in '0123456789abcdef' for c in value)
 return value


source_core=core(source);restored_core=core(restored);assert source_core==restored_core
env=os.environ.copy();env.update(PYTHONPATH=str(restored),PYTHONNOUSERSITE='1',PA_EVIDENCE_RUN_DIR=str(out))
selected=[
 'tests/test_trade_twin_jobs.py::test_original_reservation_freezes_both_complete_policies_before_candidate_work',
 'tests/test_trade_twin_jobs.py::test_original_reservation_is_atomic_across_concurrent_and_canceled_requests',
 'tests/test_trade_twin_durable_preparation.py::test_original_plan_is_durably_sealed_before_any_candidate_finance_and_reused_on_resume',
 'tests/test_trade_twin_durable_preparation.py::test_atomic_seal_failure_retains_orphan_and_retry_uses_a_distinct_attempt',
 'tests/test_trade_twin_durable_preparation.py::test_real_original_corporate_actions_are_bound_to_preparation',
 'tests/test_trade_twin_durable_preparation.py::test_actual_interpreter_death_preserves_original_attempts_and_committed_preparation',
 'tests/test_trade_twin_preparation.py',
 'tests/test_trade_twins.py::test_trade_twin_core_joins_the_unchanged_numerical_gate',
 'tests/test_coverage_gate.py']
junit=out/'restored-foundation-junit.xml'
process=subprocess.run([sys.executable,'-m','pytest','-q',*selected,'--junitxml='+str(junit)],cwd=restored,env=env,capture_output=True,timeout=300)
print(process.stdout.decode('utf-8',errors='replace'),flush=True)
print(process.stderr.decode('utf-8',errors='replace'),file=sys.stderr,flush=True)
assert process.returncode==0
suites=list(ET.parse(junit).iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert counts['tests']>=15 and counts['failures']==counts['errors']==counts['skipped']==0,counts
for entry in entries:assert sha(restored/entry['path'])==entry['sha256']
assert before==snapshot(),'Development source changed during checkpoint/restore.'
value=dict(scope=__doc__,archive=archive.relative_to(root).as_posix(),archive_sha256=sha(archive),files=entries,
 source_files=before,source_core=source_core,restored_core=restored_core,
 restored_directory=restored.relative_to(root).as_posix(),restored_actual_cases=counts,
 dependency_environment='Existing locked environment reused; no fresh installation claim.',
 source_unchanged=True,restored_archived_bytes_unchanged=True,original_receipts=receipts,
 stricter_current_test_file=test_differences,financial_sets_executed=0,
 complete_financial_worker_api_ui=False,all35_global_gates_certified=False,final_product_acceptance=False)
(out/'owned-foundation-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'files','source_files'}},indent=2),flush=True)
