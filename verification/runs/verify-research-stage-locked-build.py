"""Rebuild the research stage from both locks in a new source-only directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


root = Path.cwd().resolve()
stage = root / 'data/dev027/research-src'
out = Path(os.environ['PA_EVIDENCE_RUN_DIR']).resolve()
parser = argparse.ArgumentParser()
parser.add_argument('--release-suite', action='store_true', help='Run the complete planned backend suite using the fresh interpreter.')
args = parser.parse_args()
sys.path.insert(0, str(root))
from verification.record_check import source_paths


owned = root / 'data/dev027/clean-builds' / out.name.split('-', 1)[0]
owned.mkdir(parents=True, exist_ok=False)
sources = {}
fixtures = sorted((stage / 'verification/fixtures').glob('*.json'))
assert (stage / 'verification/fixtures/strategy-baselines.json') in fixtures
for path in [*source_paths(stage), *fixtures]:
    relative = path.relative_to(stage)
    assert path.resolve().is_relative_to(stage)
    assert all(not part.lower().startswith('.env') for part in relative.parts)
    target = owned / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    contents = path.read_bytes()
    target.write_bytes(contents)
    sources[relative.as_posix()] = hashlib.sha256(contents).hexdigest()

for path in ['.env', '.venv', 'data', 'frontend/node_modules', 'frontend/dist']:
    assert not (owned / path).exists()

environment = os.environ.copy()
for key in ['PYTHONPATH', 'PYTHONHOME', 'ALPACA_API_KEY', 'ALPACA_SECRET_KEY', 'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY']:
    environment.pop(key, None)
environment.update(PYTHONNOUSERSITE='1', PIP_DISABLE_PIP_VERSION_CHECK='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
steps = []
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")


def run(label, args, cwd=owned, expected_error=None, *, extra_env=None):
    started = time.monotonic()
    child_env = environment | (extra_env or {})
    result = subprocess.run(args, cwd=cwd, env=child_env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    step = dict(name=label, exit_code=result.returncode, elapsed_seconds=time.monotonic()-started)
    steps.append(step)
    (out / 'locked-build-progress.json').write_text(
        json.dumps(dict(owned_source=owned.relative_to(root).as_posix(), steps=steps), indent=2) + '\n',
        encoding='utf-8',
    )
    print(json.dumps(step), flush=True)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    if expected_error is None:
        assert result.returncode == 0, label
    else:
        assert result.returncode != 0 and expected_error in result.stdout + result.stderr, label
    return result.stdout.strip()


powershell = shutil.which('powershell.exe')
node = shutil.which('node')
npm = shutil.which('npm.cmd')
assert powershell and node and npm
node_version = run('node-version', [node, '--version'])
assert node_version.startswith('v22.22.')
run('missing-python-prerequisite', [powershell, '-NoProfile', '-File', 'start.ps1'],
    expected_error='Install the locked Python environment first')
run('create-isolated-venv', [sys.executable, '-m', 'venv', '.venv'])
python = str(owned / '.venv/Scripts/python.exe')
assert 'include-system-site-packages = false' in (owned / '.venv/pyvenv.cfg').read_text(encoding='utf-8')
python_version = run('python-version', [python, '--version'])
assert python_version.startswith('Python 3.13.')
run('missing-frontend-prerequisite', [powershell, '-NoProfile', '-File', 'start.ps1'],
    expected_error='Build the frontend first')
run('locked-python-install', [python, '-m', 'pip', 'install', '--retries', '2', '--timeout', '30', '-r', 'requirements.lock'])
run('python-dependency-integrity', [python, '-m', 'pip', 'check'])
inventory = run('installed-locked-python-inventory', [python, '-c', '''
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
prefix = Path(sys.prefix).resolve()
assert prefix != Path(sys.base_prefix).resolve()
locks = dict(line.split('==', 1) for line in Path('requirements.lock').read_text().splitlines() if line.strip() and not line.startswith('#'))
licenses = {}
for name, version in locks.items():
    dist = metadata.distribution(name)
    assert dist.version == version
    assert Path(dist.locate_file('')).resolve().is_relative_to(prefix)
    documents = {}
    for entry in dist.files or ():
        if not any(part.endswith('.dist-info') for part in entry.parts):
            continue
        if not entry.name.lower().startswith(('license', 'copying', 'notice')) and 'licenses' not in entry.parts:
            continue
        document = Path(dist.locate_file(entry)).resolve()
        assert document.is_relative_to(prefix) and document.is_file()
        documents[entry.as_posix()] = hashlib.sha256(document.read_bytes()).hexdigest()
    license_field = dist.metadata.get('License')
    licenses[name] = {
        'expression': dist.metadata.get('License-Expression'),
        'classifiers': [item for item in dist.metadata.get_all('Classifier', []) if item.startswith('License ::')],
        'legacy_metadata_sha256': hashlib.sha256(license_field.encode('utf-8')).hexdigest() if license_field else None,
        'packaged_documents_sha256': documents,
    }
print(json.dumps({'versions': locks, 'license_metadata': licenses}, sort_keys=True))
'''])
python_inventory = json.loads(inventory)
run('locked-frontend-install', [npm, 'ci', '--ignore-scripts', '--fetch-retries', '2', '--fetch-timeout', '30000'], owned / 'frontend')
frontend = owned / 'frontend'
node_lock = json.loads((frontend / 'package-lock.json').read_text(encoding='utf-8'))['packages']
installed_node = {}
optional_node = []
for name, entry in node_lock.items():
    if not name:
        continue
    package = (frontend / name / 'package.json').resolve()
    assert package.is_relative_to(frontend / 'node_modules'), name
    if not package.is_file() and entry.get('optional'):
        optional_node.append(name)
        continue
    metadata = json.loads(package.read_text(encoding='utf-8'))
    assert metadata['version'] == entry['version'], name
    documents = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in package.parent.iterdir()
                 if p.is_file() and p.name.lower().startswith(('license', 'copying', 'notice'))}
    installed_node[name] = dict(version=metadata['version'], license=metadata.get('license'),
                                packaged_documents_sha256=documents)
run('frontend-production-build', [npm, 'run', 'build'], owned / 'frontend')
run('local-api-and-saved-export-smoke', [python, '-m', 'pytest', '-q', 'tests/test_api.py',
    '-k', 'test_health_schema_and_no_secret_echo or test_real_api_worker_result_and_exports',
    '--junitxml', str(out / 'locked-build-smoke.xml')])
assets = {}
for asset in (owned / 'frontend/dist').rglob('*'):
    if asset.is_file():
        assets[asset.relative_to(owned).as_posix()] = hashlib.sha256(asset.read_bytes()).hexdigest()
assert 'frontend/dist/index.html' in assets
hash_command = ['-c', 'from backend.lab.research import core_hash; print(core_hash())']
core_hash = run('fresh-core-hash', [python, *hash_command])
original_core_hash = run('current-stage-core-hash', [sys.executable, *hash_command], stage)
assert len(core_hash) == 64 and core_hash == original_core_hash

offline_scenario = root / 'verification/runs/clean-reproduction-offline-scenario.py'
scenario_hash = hashlib.sha256(offline_scenario.read_bytes()).hexdigest()
offline = {}
for label, runtime, source in [('stage', sys.executable, stage), ('clean', python, owned)]:
    destination = owned / ('offline-' + label)
    run(label + '-offline-account-restart', [
        runtime, str(offline_scenario), str(source), str(destination), core_hash,
    ], source)
    report_path = destination / 'scientific-reports.json'
    summary_path = destination / 'offline-summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    assert summary['core_hash'] == core_hash and summary['workers_exited']
    assert summary['original_exports_identical_after_restart']
    assert summary['external_attempts_during_saved_workflow'] == 0
    assert all(summary['trades']) and summary['long_and_short_executed']
    offline[label] = dict(scientific_sha256=hashlib.sha256(report_path.read_bytes()).hexdigest(), **summary)
    shutil.copyfile(report_path, out / (label + '-offline-scientific-reports.json'))
    shutil.copyfile(summary_path, out / (label + '-offline-summary.json'))
assert offline['stage']['scientific_sha256'] == offline['clean']['scientific_sha256']
assert hashlib.sha256(offline_scenario.read_bytes()).hexdigest() == scenario_hash

release_suite = None
if args.release_suite:
    launcher = root / 'verification/runs/launch-research-complete-regression.py'
    # External contracts resolve their fixtures from the regular stage layout.
    # That tree is byte-checked against the clean source copy before and after
    # the suite. All dependencies come from the new isolated interpreter.
    staged_sources = {
        path.relative_to(stage).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths(stage)
    }
    assert all(sources[name] == digest for name, digest in staged_sources.items())
    execution = run(
        'full-release-backend-regression-with-fresh-dependencies',
        [python, str(launcher)], root,
        extra_env={'PYTEST_PLUGINS': 'pytest_cov.plugin,hypothesis.extra.pytestplugin'},
    )
    result_line = json.loads(execution.splitlines()[-1])
    assert result_line['exit_code'] == 0 and result_line['coherent_subject']
    assert result_line['requested_artifacts_present']
    receipt = (root / result_line['receipt']).resolve()
    assert receipt.is_relative_to(root / 'verification/receipts')
    recorded = json.loads(receipt.read_text(encoding='utf-8'))
    manifest = {item['path']: item for item in recorded['artifacts']}
    subject_path = root / 'verification/runs' / recorded['receipt_id'] / 'research-stage-subject.json'
    subject_raw = subject_path.read_bytes()
    expected = manifest[subject_path.relative_to(root).as_posix()]
    assert hashlib.sha256(subject_raw).hexdigest() == expected['sha256'] and len(subject_raw) == expected['bytes']
    subject = json.loads(subject_raw)
    assert subject['source_files'] == staged_sources and subject['changed_during_check'] == []
    assert subject['child_exit_code'] == 0
    release_suite = dict(
        receipt=receipt.relative_to(root).as_posix(),
        receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
        interpreter='fresh isolated virtual environment',
        tests_executed_from_byte_checked_stage=True,
    )

assert all(
    hashlib.sha256((base / relative).read_bytes()).hexdigest() == digest
    for base in (stage, owned)
    for relative, digest in sources.items()
)
result = dict(owned_source=owned.relative_to(root).as_posix(), core_hash=core_hash, source_sha256=sources,
              asset_sha256=assets, python=python_version, node=node_version,
              locked_python_packages=python_inventory['versions'],
              locked_python_license_metadata=python_inventory['license_metadata'],
              locked_node_packages=installed_node,
              absent_optional_node_packages=optional_node, steps=steps,
              offline_scenario_sha256=scenario_hash, offline_reproduction=offline,
              fresh_environment_full_backend_suite=release_suite)
(out / 'locked-build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
