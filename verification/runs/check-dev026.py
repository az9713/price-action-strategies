"""Run tests only from the isolated D046 source and hash it before/after."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();source=root/'data/dev026/src';sys.path.insert(0,str(root))
from verification.record_check import source_paths
def snapshot():return {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
before=snapshot();run=Path(os.environ['PA_EVIDENCE_RUN_DIR']);env=os.environ.copy()
env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
if any(a.startswith('--cov') for a in sys.argv[1:]):
 private=root/'data/private-evidence/development-coverage'/run.name;private.mkdir(parents=True,exist_ok=False);env['COVERAGE_FILE']=str(private/'.coverage')
args=[a.replace('@RUN@',str(run)) for a in sys.argv[1:]]
if not any(a.startswith('--junitxml') for a in args):args.append('--junitxml='+str(run/'dev026-junit.xml'))
p=subprocess.run([sys.executable,'-m','pytest','-q',*args],cwd=source,env=env)
after=snapshot();changed=sorted(k for k in before.keys()|after.keys() if before.get(k)!=after.get(k))
(run/'dev026-source-subject.json').write_text(json.dumps(dict(source_root=source.relative_to(root).as_posix(),source_files=before,changed_during_check=changed,child_exit_code=p.returncode,main_app_source_not_replaced=True),indent=2),encoding='utf-8')
raise SystemExit(2 if changed else p.returncode)
