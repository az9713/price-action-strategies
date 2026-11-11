"""Exercise an explicitly recorded next-component prototype while stage stays frozen."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
before=snapshot();env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join([str(source),str(source/'tests')]),PYTHONNOUSERSITE='1',PA_FEATURE_PROTOTYPE_PATH=str(root/'verification/runs/trade_twin_features_draft.py'))
command=[sys.executable,'-m','pytest','-q','-c',str(source/'pyproject.toml'),str(root/'verification/runs/test_trade_twin_features_prototype.py'),'--junitxml='+str(out/'feature-prototype-junit.xml')]
p=subprocess.run(command,cwd=source,env=env);after=snapshot()
(out/'feature-prototype-subject.json').write_text(json.dumps(dict(staged_source_files=before,staged_source_unchanged=before==after,prototype_installed=False,child_exit_code=p.returncode),indent=2),encoding='utf-8')
assert before==after
raise SystemExit(p.returncode)
