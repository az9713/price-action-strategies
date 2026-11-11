"""Actually restore the complete integrated source archive and test its catalog/schema.

Uses the existing locked environment. No dependency installation, credentials,
cached prices, original databases, public publication or final certification.
"""
from pathlib import Path, PurePosixPath
import hashlib, json, os, stat, subprocess, sys, uuid, zipfile

root = Path.cwd()
run = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
receipt_path = root / 'verification/receipts/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

receipt = read(receipt_path)
assert receipt['command']['exit_code'] == 0
assert not any(n.startswith(('Source changed', 'Missing requested')) for n in receipt['notes'])
artifacts = {}
for item in receipt['artifacts']:
    path = root / item['path']
    assert path.resolve().is_relative_to(root.resolve())
    assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    artifacts[path.name] = path
checkpoint = read(artifacts['integrated025-component-checkpoint.json'])
manifest = read(artifacts['integrated025-source-manifest.json'])
expected = {item['path']: item for item in manifest}
assert len(expected) == len(manifest) == checkpoint['archive_files']
assert sha(artifacts['integrated025-source-checkpoint.zip']) == checkpoint['archive_sha256']
owned_base = root / 'data/dev025/reconstructions'
owned = owned_base / uuid.uuid4().hex
owned.mkdir(parents=True, exist_ok=False)
assert owned.resolve().is_relative_to(owned_base.resolve())

with zipfile.ZipFile(artifacts['integrated025-source-checkpoint.zip']) as archive:
    assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected)
    for info in archive.infolist():
        name = info.filename
        path = PurePosixPath(name)
        assert not path.is_absolute() and ':' not in name and '..' not in path.parts and '\\' not in name
        assert not any(p.lower().startswith('.env') for p in path.parts)
        assert not name.startswith(('data/', 'frontend/node_modules/'))
        assert not info.is_dir() and not stat.S_ISLNK(info.external_attr >> 16)
        raw = archive.read(info)
        meta = expected[name]
        assert len(raw) == meta['bytes'] and hashlib.sha256(raw).hexdigest() == meta['sha256']
        target = owned.joinpath(*path.parts)
        assert target.resolve().is_relative_to(owned.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

def verify_files():
    for name, meta in expected.items():
        target = owned / name
        assert target.stat().st_size == meta['bytes'] and sha(target) == meta['sha256'], name
    for name, digest in checkpoint['source_files'].items():
        assert sha(owned / name) == digest, name

verify_files()
environment = os.environ.copy()
environment.update(PYTHONPATH=str(owned), PYTHONNOUSERSITE='1')
probe = 'from backend.lab.research import core_hash,current_core_hash;import json;print(json.dumps(dict(core_hash=core_hash(),current_core_hash=current_core_hash())))'
observed = subprocess.run([sys.executable, '-c', probe], cwd=owned, env=environment, capture_output=True, text=True, check=True)
core = json.loads(observed.stdout)
assert core['core_hash'] == core['current_core_hash'] == checkpoint['core_hash']
command = [sys.executable, '-m', 'pytest', '-q', '-c', 'pyproject.toml',
           'tests/test_spread_public_schema.py', 'tests/test_coverage_gate.py',
           'tests/test_catalog_generation.py', '--junitxml=' + str(run / 'restored-source-junit.xml')]
result = subprocess.run(command, cwd=owned, env=environment, capture_output=True)
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
verify_files()
catalog = read(owned / 'verification/catalog.json')
assert len(catalog['requirements']) == 83 and len(catalog['cases']) == 422
assert sum(c['id'].startswith('MATRIX-') for c in catalog['cases']) == 120
value = dict(scope=__doc__, checkpoint_receipt=receipt_path.relative_to(root).as_posix(),
             archive_files_verified=len(expected), source_files_verified=len(checkpoint['source_files']),
             owned_reconstruction=owned.relative_to(root).as_posix(), core=core,
             child_exit_code=result.returncode, dependency_install_performed=False,
             credentials_or_user_data_restored=False, final_acceptance_certified=False)
(run / 'integrated-source-reconstruction.json').write_text(json.dumps(value, indent=2), encoding='utf-8')
print(json.dumps(value, indent=2))
raise SystemExit(result.returncode)
