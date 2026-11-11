"""Record bounded-publication and original checkpoint/store/lease integration."""
from pathlib import Path
import subprocess
import sys

root=Path.cwd()
names=['account-publication-batch-contracts.py','account-batch-buffer-contracts.py',
    'account-checkpoint-boundary-contracts.py','research-arm-recovery-contracts.py',
    'research-funnel-publication-fence-contracts.py',
    'heartbeat-main-contention-contracts.py','heartbeat-covering-contracts.py',
    'heartbeat-main-renewal-contracts.py','heartbeat-renewal-observer-contracts.py',
    'checkpoint-plan-lock-contracts.py','plan-projection-integrity-contracts.py',
    'checkpoint-worker-lease-boundary-contracts.py']
references=['account-batch-financial-contracts.py','account-publication-batch-design.md',
    'owned_death_probe.py','owned-death-probe-contracts.py',
    'account-publication-batch-before/worker.py','account-publication-batch-before/account_checkpoints.py',
    'account-publication-batch-before/provenance.json',
    'research-funnel-arm-contracts.py','research-funnel-registration-contracts.py','research-arm-death-child.py',
    'heartbeat-covering-before/store.py','heartbeat-covering-before/provenance.json',
    'main-progress-retry-before/worker.py','main-progress-retry-before/provenance.json',
    'checkpoint-lock-before/trials.py','checkpoint-lock-before/store.py','checkpoint-lock-before/worker.py',
    'checkpoint-lock-before/provenance.json','shared-lease-before/worker.py','shared-lease-before/store.py',
    'shared-lease-before/provenance.json','launch-account-publication-regression.py',
    'check-research-funnel-full-stage.py','research_regression_progress.py','verification_awake.py']
args=[sys.executable,'verification/record_check.py','--label','bounded-publication-original-checkpoint-arm-deaths-runtime-trials-and-lease-regression']
for name in names+references:
    path=Path('verification/runs')/name;assert (root/path).is_file(),path
    args+=['--input',path.as_posix()]
args+=['--',sys.executable,'verification/runs/check-research-funnel-full-stage.py','-c','pyproject.toml',
    'tests/test_store.py','tests/test_trial_registry.py','tests/test_runtime_ownership.py']
args+=['../../../verification/runs/'+name for name in names]
args+=['--import-mode=importlib','--cov=backend.lab.account_checkpoints','--cov=backend.lab.store',
    '--cov=backend.lab.worker','--cov=backend.lab.trials','--cov-branch',
    '--cov-report=json:@RUN@/account-batch-selected-coverage.json',
    '-W','error::ResourceWarning','-W','error::pytest.PytestUnhandledThreadExceptionWarning',
    '-W','error::pytest.PytestUnraisableExceptionWarning']
raise SystemExit(subprocess.run(args, cwd=root).returncode)
