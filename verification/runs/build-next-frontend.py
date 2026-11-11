"""Build staged UI with the existing identically locked local dependencies."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
root=Path.cwd();stage=root/'data/dev026/next-src'
if len(sys.argv)>1:
    assert len(sys.argv)==3 and sys.argv[1]=='--source'
    stage=(root/sys.argv[2]).resolve()
    assert stage in {(root/'data/dev026/next-src').resolve(),(root/'data/dev026/evidence-src').resolve()}
front=stage/'frontend';installed=root/'frontend/node_modules'
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['package.json','package-lock.json']:
    assert sha(front/name)==sha(root/'frontend'/name),'Dependency lock differs: '+name
assert (installed/'react/package.json').is_file()
link=front/'node_modules'
if not link.exists():
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',"New-Item -ItemType Junction -Path '"+str(link)+"' -Target '"+str(installed)+"' | Out-Null"],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
assert link.resolve()==installed.resolve()
sys.path.insert(0,str(root));from verification.record_check import source_paths
before={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
result=subprocess.run(['cmd.exe','/d','/c','npm.cmd run build'],cwd=front,capture_output=True,text=True)
(out/'frontend-build.stdout.txt').write_text(result.stdout,encoding='utf-8')
(out/'frontend-build.stderr.txt').write_text(result.stderr,encoding='utf-8')
print(result.stdout[-5000:]);print(result.stderr[-3000:],file=sys.stderr)
assert result.returncode==0
assert before=={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
value=dict(scope=__doc__,source_files=before,staged_source_unchanged=True,dependency_locks_match=True,
           dependency_directory_reused=True,live_application_assets_replaced=False,
           artifacts=[dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted((front/'dist').rglob('*')) if p.is_file()])
(out/'staged-frontend-build.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='source_files'},indent=2))
