"""Restore verified source only for isolated D046 development; never user data."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,stat,zipfile
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
checkpoint=root/'verification/runs/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint'
receipt=json.loads((root/'verification/receipts'/(checkpoint.name+'.json')).read_text(encoding='utf-8'))
assert receipt['command']['exit_code']==0
for a in receipt['artifacts']:
 p=root/a['path'];assert p.stat().st_size==a['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
manifest=json.loads((checkpoint/'integrated025-source-manifest.json').read_text(encoding='utf-8'));expected={a['path']:a for a in manifest}
target=root/'data/dev026/src';assert not target.exists();target.mkdir(parents=True,exist_ok=False)
assert target.resolve().is_relative_to((root/'data/dev026').resolve())
with zipfile.ZipFile(checkpoint/'integrated025-source-checkpoint.zip') as archive:
 assert set(archive.namelist())==set(expected) and len(archive.namelist())==len(expected)
 for info in archive.infolist():
  name=info.filename;p=PurePosixPath(name)
  assert not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16)
  assert not any(part.lower().startswith('.env') for part in p.parts) and not name.startswith(('data/','frontend/node_modules/'))
  raw=archive.read(info);meta=expected[name];assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
  dest=target.joinpath(*p.parts);assert dest.resolve().is_relative_to(target.resolve());dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
(out/'dev026-source-baseline.json').write_text(json.dumps(dict(scope=__doc__,target=target.relative_to(root).as_posix(),archive_files=len(expected),source_files=manifest,credentials_user_data_dependencies_copied=False,main_source_replaced=False),indent=2),encoding='utf-8')
print(json.dumps(dict(target=target.relative_to(root).as_posix(),archive_files=len(expected),main_source_replaced=False)))
