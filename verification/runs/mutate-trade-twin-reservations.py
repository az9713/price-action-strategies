"""Actual current-source reservation mutations; assertion failures only count.

No server, credentials, installed dependencies, prices or original database is
copied. Every test constructs a fresh owned synthetic original account.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path.cwd()
source = root / 'data/dev026/next-src'
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
private = root / 'data/private-evidence/trade-twin-reservation-mutations' / out.name
private.mkdir(parents=True, exist_ok=False)
sys.path.insert(0, str(root))
from verification.record_check import source_paths


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {p.relative_to(source).as_posix(): sha(p) for p in source_paths(source)}


before = snapshot()
target = 'backend/lab/trade_twin_jobs.py'
test = 'tests/test_trade_twin_jobs.py::'
specs = [
    ('short-policy-cohort', '    for ordinal in range(TOTAL_SETS):',
     '    for ordinal in range(TOTAL_SETS - 1):',
     test + 'test_original_reservation_freezes_both_complete_policies_before_candidate_work'),
    ('boolean-protocol-version', "    if identity(payload.get('twin_protocol')) != identity(PROTOCOL):",
     "    if payload.get('twin_protocol') != PROTOCOL:",
     test + 'test_protocol_cannot_shrink_policy_cohort_or_use_boolean_version'),
    ('late-original-binding', "    if binding != source['authority'] or configuration != source['assumptions']['configuration']:",
     "    if False:",
     test + 'test_late_source_bytes_or_binding_changes_abort_reservation[binding]'),
    ('late-protected-scope', "    lab.guard.check_access(db,symbols,warmup,p['end'])",
     '    pass  # mutation: ignore newly protected dates',
     test + 'test_revalidation_rechecks_late_parent_state_and_protected_scope[protected_scope]'),
    ('amended-original-inputs', "    if child['kind'] != 'trade_twins' or provenance != 'prespecified' or digest != identity(payload):",
     "    if child['kind'] != 'trade_twins' or provenance != 'prespecified':",
     test + 'test_original_child_cannot_authorize_amended_expected_payload'),
    ('unchecked-derived-summary', "        projection, _ = store._input_index.checked(dict(cached))",
     "        projection = json.loads(cached['projection'])",
     test + 'test_bounded_reservation_metadata_checks_refuse_without_decoding_large_jobs[invalid_index_hash]'),
    ('erased-original-reservation', "    if any(r['bytes']!=32 or not isinstance(r['job_id'],str) or re.fullmatch('[a-f0-9]{32}',r['job_id']) is None for r in originals) or [r['job_id'] for r in originals]!=ids:",
     '    if False:',
     test + 'test_revalidation_refuses_original_and_rehashed_derived_metadata_faults[erased_link_event_index]'),
    ('cancel-before-commit', "            _cancel(cancel);db.execute('COMMIT')\n        return store.job(child_id)",
     "            db.execute('COMMIT')\n        return store.job(child_id)",
     test + 'test_reservation_failure_rolls_back_job_occurrences_link_and_events[after_freeze_cancel]'),
]

# Preflight exact bytes, including the actual source file's newline convention.
original = (source / target).read_bytes()
newline = b'\r\n' if b'\r\n' in original else b'\n'
for name, old, new, selected in specs:
    needle = old.encode().replace(b'\n', newline)
    assert original.count(needle) == 1, (name, 'nonunique or absent mutation target')


def clone(name):
    folder = root / 'data/dev026/reservation-mutations' / out.name / name
    folder.mkdir(parents=True, exist_ok=False)
    paths = list((source / 'backend').rglob('*.py')) + list((source / 'tests').rglob('*.py'))
    paths += list((source / 'verification').glob('*.py'))
    paths += list((source / 'verification/fixtures').rglob('*.json'))
    paths += [source / p for p in ('pyproject.toml', 'requirements.lock', 'RULEBOOK.md',
                                   'strategy.schema.json', 'verification/catalog.json')]
    for path in paths:
        dest = folder / path.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    return folder


def run(folder, name, selectors):
    result_dir = out / name
    result_dir.mkdir()
    junit = result_dir / 'junit.xml'
    env = os.environ.copy()
    env.update(PYTHONPATH=str(folder), PYTHONNOUSERSITE='1', PA_EVIDENCE_RUN_DIR=str(result_dir))
    started = datetime.now(timezone.utc).isoformat()
    command = [sys.executable, '-m', 'pytest', '-q', *selectors, '--junitxml=' + str(junit)]
    process = subprocess.run(command, cwd=folder, env=env, capture_output=True, timeout=300)
    (private / (name + '-stdout.log')).write_bytes(process.stdout)
    (private / (name + '-stderr.log')).write_bytes(process.stderr)
    # Only count metadata and assertion types are public; no raw trace copying.
    suites = list(ET.parse(junit).iter('testsuite'))
    counts = {k: sum(int(s.attrib.get(k, 0)) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    failures = list(ET.parse(junit).iter('failure'))
    assertion_only = bool(failures) and all(
        'AssertionError' in (f.text or '') or 'DID NOT RAISE' in (f.text or '')
        or f.attrib.get('message', '').startswith('assert ') for f in failures)
    return dict(name=name, started_at_utc=started, exit_code=process.returncode,
                counts=counts, assertion_only=assertion_only,
                selected_tests=selectors, raw_stdout_sha256=sha(private / (name + '-stdout.log')),
                raw_stderr_sha256=sha(private / (name + '-stderr.log')))


baseline = run(clone('baseline'), 'baseline', list(dict.fromkeys(s[3] for s in specs)))
assert baseline['exit_code'] == 0 and baseline['counts'] == dict(tests=8, failures=0, errors=0, skipped=0), baseline
rows = []
for name, old, new, selected in specs:
    folder = clone(name)
    needle = old.encode().replace(b'\n', newline)
    replacement = new.encode().replace(b'\n', newline)
    mutated = original.replace(needle, replacement, 1)
    (folder / target).write_bytes(mutated)
    assert sha(folder / target) == hashlib.sha256(mutated).hexdigest()
    result = run(folder, name, [selected])
    result.update(original_sha256=hashlib.sha256(original).hexdigest(), mutated_sha256=sha(folder / target))
    rows.append(result)
    assert result['exit_code'] == 1 and result['counts']['failures'] > 0 and result['counts']['errors'] == result['counts']['skipped'] == 0 and result['assertion_only'], result
    print(json.dumps(dict(name=name, assertion_killed=True, counts=result['counts'])), flush=True)

assert before == snapshot(), 'Actual development source changed during mutation execution.'
summary = dict(scope=__doc__, baseline=baseline, mutations=rows, assertion_kills=len(rows),
               source_files=before, source_unchanged=True, final_product_acceptance=False)
(out / 'reservation-mutations.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps(dict(assertion_kills=len(rows), source_unchanged=True)), flush=True)
