"""Run exact financial grading prototype without editing staged source."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
before=snapshot();env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join([str(source),str(source/'tests')]),PYTHONNOUSERSITE='1',PA_GRADE_PROTOTYPE_PATH=str(root/'verification/runs/trade_twin_decimal_grading_draft.py'))
p=subprocess.run([sys.executable,'-m','pytest','-q','-c',str(source/'pyproject.toml'),str(root/'verification/runs/test_trade_twin_decimal_grading_prototype.py'),*sys.argv[1:],'--junitxml='+str(out/'decimal-grading-prototype-junit.xml')],cwd=source,env=env)
after=snapshot();(out/'decimal-grading-prototype-subject.json').write_text(json.dumps(dict(staged_source_files=before,staged_source_unchanged=before==after,prototype_installed=False,child_exit_code=p.returncode),indent=2),encoding='utf-8');assert before==after
raise SystemExit(p.returncode)
