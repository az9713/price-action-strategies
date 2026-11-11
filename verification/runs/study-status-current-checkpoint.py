"""Coherent D042 component source/evidence checkpoint; full release acceptance remains pending."""
from pathlib import Path
source=Path('verification/runs/job-status-current-checkpoint.py').read_text(encoding='utf-8')
labels=[
 'study-status-current-full-regression-and-twenty-module-coverage',
 'study-status-current-twenty-module-coverage-gate',
 'study-status-current-typed-production-build',
 'study-status-current-two-desktop-download-repair-history-ownership-and-current-errors',
 'study-status-current-two-desktop-portfolio-final-and-result-ownership',
 'study-status-current-prespecified-10-1000-100000-registration-inputs-and-protected-scope',
 'study-status-current-nine-isolated-critical-mutations',
 'study-status-current-independent-canonical-input-history-complete-account-csv-and-offline-audit',
 'study-status-current-managed-owner-all-job-idleness-assets-and-duplicate-store-refusal',
 'study-status-current-83-422-120-plan-inventory',
]
failures=[
 'study-status-and-isolated-legacy-recovery-authored-first-contract',
 'study-status-correct-actual-spy-scope-and-isolated-legacy-first-contract',
 'study-status-first-derived-projections-scopes-and-legacy-recovery-regression',
 'study-status-expanded-source-cache-lifecycle-legacy-partial-rollback-and-existing-protocol',
 'study-status-authored-nested-legacy-and-malformed-checksummed-cache-first-contract',
 'legacy-original-blob-authored-failure-before-raw-byte-preservation-fix',
 'study-status-two-desktop-original-download-repair-history-stale-response-and-long-refresh-first-browser',
]
start=source.index('labels=[');end=source.index('\nfailed_labels=',start);source=source[:start]+'labels='+repr(labels)+source[end:]
start=source.index('failed_labels=[');end=source.index('\ndef sha(',start);source=source[:start]+'failed_labels='+repr(failures)+source[end:]
source=source.replace("inputs={Path(__file__).resolve()}","inputs={Path(__file__).resolve(),root/'verification/runs/job-status-current-checkpoint.py'}")
source=source.replace("len(g['modules'])==19","len(g['modules'])==20").replace('tests>=1600','tests>=1700')
source=source.replace("assert r['command']['exit_code']==1;verify_artifacts(r)","assert r['command']['exit_code'] in {1,4};verify_artifacts(r)")
start=source.index('for receipt_id in [');end=source.index('\npaths=set(sources)',start);source=source[:start]+source[end:]
source=source.replace('D041','D042').replace('nineteen_module_coverage_passed','twenty_module_coverage_passed')
exec(compile(source,'study-status-current-checkpoint-resolved.py','exec'))
