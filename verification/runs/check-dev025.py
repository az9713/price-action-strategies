"""Run only in the isolated development source with explicit import ownership."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev025/src';assert source.is_dir()
sys.path.insert(0,str(root))
from verification.record_check import source_paths
def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
before=snapshot()
environment=os.environ.copy();environment['PYTHONPATH']=str(source);environment['PYTHONNOUSERSITE']='1'
run=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
if any(arg.startswith('--cov') for arg in sys.argv[1:]):
    coverage=root/'data/private-evidence/development-coverage'/run.name;coverage.mkdir(parents=True,exist_ok=False)
    environment['COVERAGE_FILE']=str(coverage/'.coverage')
arguments=[arg.replace('@RUN@',str(run)) for arg in sys.argv[1:]]
command=[sys.executable,'-m','pytest','-q',*arguments]
if not any(a.startswith('--junitxml') for a in sys.argv[1:]):
    command.append('--junitxml='+str(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'dev025-junit.xml'))
result=subprocess.run(command,cwd=source,env=environment)
after=snapshot();changed=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k))
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'dev025-source-subject.json').write_text(json.dumps(dict(source_root=source.relative_to(root).as_posix(),source_files=before,changed_during_check=changed,child_exit_code=result.returncode,main_app_source_not_replaced=True),indent=2),encoding='utf-8')
if changed:raise SystemExit(2)
raise SystemExit(result.returncode)
