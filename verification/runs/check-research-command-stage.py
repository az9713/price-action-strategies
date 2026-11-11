"""Run an owned non-pytest stage check with source snapshots and scoped wake request."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root))
from verification.record_check import source_paths
from verification_awake import verification_awake

def snapshot(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(folder)}

before=snapshot(stage)
frozen={p:snapshot(root/p) for p in ['data/dev026/src','data/dev026/next-src','data/dev026/evidence-src']}
env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join([str(stage),str(root/'verification/runs')]),PYTHONNOUSERSITE='1')
with verification_awake(out):result=subprocess.run(sys.argv[1:],cwd=root,env=env)
after=snapshot(stage);changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
unchanged=all(value==snapshot(root/p) for p,value in frozen.items())
(out/'research-stage-subject.json').write_text(json.dumps(dict(source_root=stage.relative_to(root).as_posix(),
    source_files=before,changed_during_check=changed,earlier_financial_sources_unchanged=unchanged,
    child_exit_code=result.returncode,installed_app_source_not_replaced=True),indent=2),encoding='utf-8')
raise SystemExit(2 if changed or not unchanged else result.returncode)
