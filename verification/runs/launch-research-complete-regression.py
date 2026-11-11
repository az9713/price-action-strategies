"""Record the complete base suite and all current research contract suites."""
from pathlib import Path
import subprocess
import sys

root=Path.cwd()
names=[
    'operation-connection-contracts.py','large-account-unit-contracts.py',
    'large-account-unit-recovery-contracts.py',
    'news-release-acceptance-contracts.py','news-acquisition-death-contracts.py',
    'context-feature-cache-contracts.py',
    'provider-release-acceptance-contracts.py',
    'owned-death-probe-contracts.py',
    'research-arm-recovery-contracts.py',
    'research-family-api-contracts.py','research-family-boundary-contracts.py',
    'research-family-bounded-read-contracts.py','research-family-bounded-read-counterexample.py',
    'research-family-job-contracts.py','research-family-recovery-contracts.py',
    'research-funnel-arm-contracts.py','research-funnel-export-api-cancellation.py',
    'research-funnel-export-contracts.py','research-funnel-export-mixed-accounts.py',
    'research-funnel-final-boundaries.py','research-funnel-final-contracts.py',
    'research-funnel-final-deaths.py','research-funnel-final-trades.py',
    'research-funnel-public-api.py','research-funnel-public-generation-boundaries.py',
    'research-funnel-publication-fence-contracts.py','research-funnel-registration-contracts.py',
    'research-funnel-small-positive-controls.py','research-funnel-twin-bridge-contracts.py',
    'research-funnel-small-positive-full.py',
    'research-owned-qualification-api-guard.py','research-owned-qualification-boundaries.py',
    'research-owned-qualification-contracts.py','research-owned-qualification-deaths.py',
    'research-qualification-attrition-contracts.py','research-qualification-contracts.py',
    'research-qualification-positive-accounts.py','research-qualification-provenance-contracts.py',
    'research-saved-source-boundary-contracts.py','research-source-fingerprint-path-contracts.py',
    'research-stability-reference-contracts.py',
    'trade-twin-preparation-cache-contracts.py',
    'trade-twin-manifest-proof-contracts.py','control-reader-physical-identity-contracts.py',
    'trade-twin-part-projection-contracts.py','trade-twin-part-projection-late-faults.py',
    'trade-twin-complete-original-controls.py',
    'checkpoint-plan-lock-contracts.py','plan-projection-integrity-contracts.py',
    'checkpoint-worker-lease-boundary-contracts.py',
    'heartbeat-main-renewal-contracts.py','heartbeat-renewal-observer-contracts.py',
    'heartbeat-covering-contracts.py',
    'heartbeat-main-contention-contracts.py',
    'account-checkpoint-boundary-contracts.py',
    'account-publication-batch-contracts.py','account-batch-financial-contracts.py',
    'account-batch-recovery-contracts.py','account-batch-buffer-contracts.py',
    'evaluation-cache-legacy-report-contract-tests.py',
    'twin-evidence-manifest-boundary-cases.py','twin-owned-publication-authority-cases.py',
    'twin-publication-metadata-cases.py','twin-saved-evidence-serialization-cases.py',
]
inputs=[Path('verification/runs')/name for name in names]
inputs += [Path('verification/runs')/name for name in [
    'research-arm-death-child.py','research-family-death-child.py',
    'owned_death_probe.py',
    'large-account-unit-death-child.py',
    'news-acquisition-death-child.py',
    'large-account-unit-before/store.py','large-account-unit-before/worker.py',
    'large-account-unit-before/trials.py','large-account-unit-before/account_checkpoints.py',
    'large-account-unit-before/provenance.json',
    'check-research-funnel-full-stage.py','research_regression_progress.py',
    'launch-research-complete-regression.py',
    'trade-twin-execution-before-preparation-optimization.py',
    'trade-twin-parts-before-manifest-proof-reuse.py','store-before-control-identity-optimization.py',
    'trade-twin-parts-original-pre-projection-verified.py',
    'authored-original-twin-manifest-books.json',
    'verification_awake.py',
    'checkpoint-lock-before/trials.py','checkpoint-lock-before/store.py',
    'checkpoint-lock-before/worker.py','checkpoint-lock-before/provenance.json',
    'shared-lease-before/worker.py','shared-lease-before/store.py','shared-lease-before/provenance.json',
    'heartbeat-covering-before/store.py','heartbeat-covering-before/provenance.json',
    'main-progress-retry-before/worker.py','main-progress-retry-before/provenance.json',
    'account-batch-death-child.py','account-publication-batch-design.md',
    'account-publication-batch-before/worker.py','account-publication-batch-before/account_checkpoints.py',
    'account-publication-batch-before/provenance.json',
]]
for path in inputs:assert (root/path).is_file(),path
argv=[sys.executable,str(root/'verification/record_check.py'),'--label','current-complete-base-and-research-regression-all-51-numerical-modules']
for path in inputs:argv+=['--input',path.as_posix()]
argv+=['--',sys.executable,'verification/runs/check-research-funnel-full-stage.py','-c','pyproject.toml','tests']
argv+=['../../../verification/runs/'+name for name in names]
argv+=['--import-mode=importlib','--cov=backend.lab','--cov-branch','--cov-report=json:@RUN@/current-all-51-coverage.json',
    '-W','error::ResourceWarning','-W','error::pytest.PytestUnraisableExceptionWarning',
    '-W','error::pytest.PytestUnhandledThreadExceptionWarning']
raise SystemExit(subprocess.run(argv, cwd=root).returncode)
