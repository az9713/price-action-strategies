"""Reconcile actual current reservation coverage; no global gate assertion."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys

root = Path.cwd()
source = root / 'data/dev026/next-src'
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
identifier = '20261109T222401368557Z-trade-twins-original-reservation-final-metadata-sidecar-amendment-and-unrounded-gate-cases'
receipt_path = root / 'verification/receipts' / (identifier + '.json')
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(suffix):
    row = next(a for a in receipt['artifacts'] if a['path'].endswith('/' + suffix))
    path = root / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    return path


assert receipt['command']['exit_code'] == 0
assert not any(n.startswith(('Source changed', 'Missing requested')) for n in receipt['notes'])
subject = json.loads(artifact('next-stage-source-subject.json').read_text(encoding='utf-8'))
assert subject['child_exit_code'] == 0 and not subject['changed_during_check'] and subject['frozen_baseline_unchanged']
for name, digest in subject['source_files'].items():
    assert sha(source / name) == digest, name

coverage_path = artifact('reservation-coverage.json')
recorded = json.loads(coverage_path.read_text(encoding='utf-8'))
database = root / 'data/private-evidence/development-coverage' / identifier / '.coverage'
database_sha = sha(database)
rendered_path = out / 'reservation-coverage-rerender.json'
command = [sys.executable, '-m', 'coverage', 'json', '--data-file=' + str(database),
           '--rcfile=' + str(source / 'pyproject.toml'), '-o', str(rendered_path)]
process = subprocess.run(command, cwd=source, capture_output=True, text=True, timeout=60)
assert process.returncode == 0, process.stderr
actual = json.loads(rendered_path.read_text(encoding='utf-8'))
assert actual['files'] == recorded['files'] and database_sha == sha(database)
assert len(actual['files']) == 1
module, result = next(iter(actual['files'].items()))
assert module.replace('\\', '/') == 'backend/lab/trade_twin_jobs.py'
summary = result['summary']
assert summary['excluded_lines'] == 0
assert 100 * summary['covered_lines'] >= 95 * summary['num_statements']
assert 100 * summary['covered_branches'] >= 90 * summary['num_branches']
value = dict(scope=__doc__, original_receipt=identifier, actual_database_sha256=database_sha,
             source_files=subject['source_files'], module=module, summary=summary,
             statement_minimum=95, branch_minimum=90, exclusions=0,
             coverage_json_exactly_reconciled=True, original_database_unchanged=True,
             all34_global_modules_certified=False, final_product_acceptance=False)
(out / 'reservation-gate.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in value.items() if k != 'source_files'}, indent=2))
