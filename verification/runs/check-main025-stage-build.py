"""Type/build canonical source into a fresh private output; never replace served assets."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,uuid
root=Path.cwd();run=Path(os.environ['PA_EVIDENCE_RUN_DIR']);stage=root/'data/private-evidence/main025-builds'/uuid.uuid4().hex
stage.mkdir(parents=True,exist_ok=False);assert stage.resolve().is_relative_to((root/'data/private-evidence/main025-builds').resolve()) and not list(stage.iterdir())
result=subprocess.run(['npm.cmd','run','build','--','--outDir',str(stage)],cwd=root/'frontend',capture_output=True)
sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
if result.returncode:raise SystemExit(result.returncode)
def inventory(folder):return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}
actual=inventory(stage);served=inventory(root/'frontend/dist');assert actual==served,'Canonical build differs from the installed tested assets'
for p in stage.rglob('*'):
 if p.is_file():q=run/'canonical-build'/p.relative_to(stage);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
(run/'canonical-build-parity.json').write_text(json.dumps(dict(scope=__doc__,files=actual,byte_identical_to_served=True,source_and_served_assets_replaced=False),indent=2),encoding='utf-8')
