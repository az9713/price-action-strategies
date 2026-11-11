"""Run current numerical/recovery gates, then original capacities and clean release checks."""
from pathlib import Path
import hashlib,json,subprocess,sys,time

root=Path.cwd();stage=root/'data/dev027/research-src';checks=Path('verification/runs')
first,core=sys.argv[1:]


def wait_first():
    path=root/'verification/receipts'/(first+'.json');deadline=time.monotonic()+1800
    while not path.exists():
        if time.monotonic()>deadline:raise TimeoutError('Focused receipt unavailable; preserve its original handle.')
        time.sleep(5)
    receipt=json.loads(path.read_text(encoding='utf-8'))
    assert receipt['command']['exit_code']==0 and not any('Source changed during command' in x for x in receipt['notes'])
    subject_path=root/checks/first/'research-stage-subject.json'
    artifact=next(x for x in receipt['artifacts'] if x['path']==subject_path.relative_to(root).as_posix())
    assert hashlib.sha256(subject_path.read_bytes()).hexdigest()==artifact['sha256']
    subject=json.loads(subject_path.read_text(encoding='utf-8'))
    assert subject['child_exit_code']==0 and not subject['changed_during_check']
    assert all(hashlib.sha256((stage/name).read_bytes()).hexdigest()==sha for name,sha in subject['source_files'].items())
    return path


def run(command):
    result=subprocess.run(command,cwd=root,capture_output=True,text=True,encoding='utf-8')
    print(result.stdout,end='',flush=True)
    if result.stderr:print(result.stderr,end='',file=sys.stderr,flush=True)
    if result.returncode:raise SystemExit(result.returncode)
    return result.stdout


prerequisite=wait_first()
print(json.dumps({'focused_prerequisite_passed':first,'expected_core':core}),flush=True)
names=[
    'context-feature-cache-contracts.py',
    'large-account-unit-recovery-contracts.py','owned-death-probe-contracts.py',
    'account-batch-recovery-contracts.py','research-arm-recovery-contracts.py',
    'account-checkpoint-boundary-contracts.py','research-funnel-publication-fence-contracts.py',
    'heartbeat-main-contention-contracts.py','heartbeat-covering-contracts.py',
    'heartbeat-main-renewal-contracts.py','heartbeat-renewal-observer-contracts.py',
    'checkpoint-plan-lock-contracts.py','checkpoint-worker-lease-boundary-contracts.py',
]
helpers=[
    'large-account-unit-death-child.py','account-batch-death-child.py','research-arm-death-child.py',
    'owned_death_probe.py','account-batch-financial-contracts.py',
    'launch-large-unit-verification-capacity.py','check-research-funnel-full-stage.py',
    'research_regression_progress.py','verification_awake.py',
]
argv=[sys.executable,'verification/record_check.py','--label','large-unit-complete-numerical-owned-deaths-and-lease-regression',
      '--input',prerequisite.relative_to(root).as_posix()]
for name in names+helpers:argv+=['--input',(checks/name).as_posix()]
argv+=['--',sys.executable,'verification/runs/check-research-funnel-full-stage.py','-c','pyproject.toml',
       'tests/test_strategy_matrix.py','tests/test_reference_execution.py','tests/test_reference_exits.py',
       'tests/test_reference_properties.py','tests/test_confirmation_filters.py','tests/test_evaluation_cache.py',
       'tests/test_trial_registry.py','tests/test_runtime_ownership.py']
argv+=['../../../verification/runs/'+name for name in names]
argv+=['--import-mode=importlib','-W','error::ResourceWarning',
       '-W','error::pytest.PytestUnraisableExceptionWarning','-W','error::pytest.PytestUnhandledThreadExceptionWarning']
stdout=run(argv)
record=json.loads(stdout.splitlines()[-1]);assert record['exit_code']==0 and record['coherent_subject'] and record['requested_artifacts_present']
numerical=Path(record['receipt']).stem
print(json.dumps({'numerical_and_recovery_passed':numerical}),flush=True)
stdout=run([sys.executable,'verification/runs/launch-context-cache-capacity.py',numerical,core])
capacity=None
for line in stdout.splitlines():
    try:item=json.loads(line)
    except json.JSONDecodeError:continue
    if not isinstance(item,dict) or not item.get('receipt'):continue
    path=Path(item['receipt']);identifier=path.stem
    if identifier.endswith('-adopted-numerical-real-market-10000-capacity'):
        assert item['exit_code']==0 and item['coherent_subject'];capacity=identifier
assert capacity,'No passing actual 10,000 capacity receipt was produced.'
raise SystemExit(subprocess.run([sys.executable,'verification/runs/launch-clean-release-after-capacity.py',capacity,core],cwd=root).returncode)
