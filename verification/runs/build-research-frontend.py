"""Build the isolated research UI; never replace installed application assets."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def snapshot(folder):return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(folder)}
before=snapshot(stage);frozen=snapshot(root/'data/dev026/evidence-src')
result=subprocess.run(['npm.cmd','run','build'],cwd=stage/'frontend')
after=snapshot(stage)
assets={p.relative_to(stage).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in (stage/'frontend/dist').rglob('*') if p.is_file()}
unchanged=before==after and frozen==snapshot(root/'data/dev026/evidence-src')
(out/'research-frontend-build.json').write_text(json.dumps(dict(source_files=before,source_unchanged=unchanged,child_exit_code=result.returncode,assets=assets,installed_assets_not_replaced=True),indent=2),encoding='utf-8')
raise SystemExit(result.returncode if unchanged else 2)
