"""Create an explicit source/fixture-only development copy; no app data or installed packages."""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();sys.path.insert(0,str(root))
from verification.record_check import source_paths
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);destination=root/'data/dev025/src'
assert not destination.exists();destination.mkdir(parents=True)
paths=source_paths()+[p for p in (root/'verification/fixtures').rglob('*') if p.is_file()]
manifest=[]
for source in paths:
 relative=source.relative_to(root)
 assert relative.parts[0] in {'backend','tests','frontend','verification'} or len(relative.parts)==1
 assert not any(part.lower().startswith('.env') or part in {'node_modules','.venv'} for part in relative.parts)
 assert not source.is_symlink()
 target=destination/relative;target.resolve().relative_to(destination.resolve());target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(source,target);digest=hashlib.sha256(source.read_bytes()).hexdigest();assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
 manifest.append(dict(path=relative.as_posix(),sha256=digest,bytes=target.stat().st_size))
assert not (destination/'.env').exists() and not (destination/'data').exists()
(out/'development-source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(root/'data/dev025/initial-source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(scope=__doc__,destination=destination.relative_to(root).as_posix(),files=len(manifest),main_store_unchanged=True)))
