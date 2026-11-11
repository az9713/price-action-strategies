"""Original actual-DB preparation coverage and process-death evidence gate."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path.cwd();source = root / 'data/dev026/next-src'
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
identifier = '20261109T224135319592Z-trade-twins-owned-preparation-original-fault-boundaries-rehashed-plan-and-three-actual-interpreter-deaths'
receipt = json.loads((root / 'verification/receipts' / (identifier + '.json')).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(name):
    row = next(r for r in receipt['artifacts'] if r['path'].endswith('/' + name))
    path = root / row['path']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    return path


assert receipt['command']['exit_code'] == 0
assert not any(n.startswith(('Source changed', 'Missing requested')) for n in receipt['notes'])
subject = json.loads(artifact('next-stage-source-subject.json').read_text(encoding='utf-8'))
assert subject['child_exit_code'] == 0 and not subject['changed_during_check'] and subject['frozen_baseline_unchanged']
sys.path.insert(0, str(root))
from verification.record_check import source_paths
current = {p.relative_to(source).as_posix(): sha(p) for p in source_paths(source)}
assert current == subject['source_files']
suites = list(ET.parse(artifact('next-stage-junit.xml')).iter('testsuite'))
counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
assert counts == dict(tests=28, failures=0, errors=0, skipped=0)
recorded = json.loads(artifact('preparation-coverage.json').read_text(encoding='utf-8'))
database = root / 'data/private-evidence/development-coverage' / identifier / '.coverage'
digest = sha(database)
rendered = out / 'owned-preparation-coverage-rerender.json'
result = subprocess.run([sys.executable, '-m', 'coverage', 'json', '--data-file=' + str(database),
                         '--rcfile=' + str(source / 'pyproject.toml'), '-o', str(rendered)],
                        cwd=source, capture_output=True, text=True, timeout=60)
assert result.returncode == 0, result.stderr
actual = json.loads(rendered.read_text(encoding='utf-8'))
assert actual['files'] == recorded['files'] and digest == sha(database)
assert len(actual['files']) == 1
module, value = next(iter(actual['files'].items()))
assert module.replace('\\', '/') == 'backend/lab/trade_twin_preparation.py'
summary = value['summary']
assert summary['excluded_lines'] == 0
assert 100 * summary['covered_lines'] >= 95 * summary['num_statements']
assert 100 * summary['covered_branches'] >= 90 * summary['num_branches']
deaths = []
for boundary, code in [('after_file', 71), ('inside_checkpoint', 72), ('after_seal', 73)]:
    record = json.loads(artifact('preparation-death-' + boundary + '.json').read_text())
    assert record['boundary'] == boundary and record['actual_subprocess_exit_code'] == code
    assert record['original_attempt_bytes_preserved'] and record['financial_sets_executed'] == 0
    assert record['recovered_attempts'] == (1 if boundary == 'after_seal' else 2)
    assert record['recovered_reuses'] == (1 if boundary == 'after_seal' else 0)
    deaths.append(record)
report = dict(scope=__doc__, source_files=current, original_receipt=identifier,
              actual_database_sha256=digest, actual_database_unchanged=True,
              coverage_json_exactly_reconciled=True, summary=summary,
              minimum_statements=95, minimum_branches=90, exclusions=0,
              cases=counts, actual_interpreter_death_records=deaths,
              all35_global_modules_certified=False, final_product_acceptance=False)
(out / 'owned-preparation-gate.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in report.items() if k != 'source_files'}, indent=2))
