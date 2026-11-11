"""Resolve an isolated development profiler without changing runtime dependencies."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile
root=Path.cwd();folder=root/'data/dev027/profiling-tools';wheels=folder/'wheels';wheels.mkdir(parents=True,exist_ok=True)
result=subprocess.run([sys.executable,'-m','pip','download','--no-deps','--only-binary=:all:','--dest',str(wheels),'py-spy'],capture_output=True,text=True)
assert result.returncode==0,result.stderr
choices=list(wheels.glob('py_spy-*-win_amd64.whl'));assert len(choices)==1,choices
wheel=choices[0]
with zipfile.ZipFile(wheel) as archive:
    names=[name for name in archive.namelist() if name.endswith('/scripts/py-spy.exe')];assert len(names)==1,names
    binary=archive.read(names[0])
    licenses=[name for name in archive.namelist() if name.endswith('/LICENSE') or name.endswith('/LICENSE.txt')]
    license_text=archive.read(licenses[0]).decode('utf-8') if licenses else None
target=folder/'py-spy.exe';target.write_bytes(binary)
if license_text:(folder/'PYSPY-LICENSE.txt').write_text(license_text,encoding='utf-8')
version=subprocess.run([str(target),'--version'],capture_output=True,text=True);assert version.returncode==0,version.stderr
value=dict(scope=__doc__,source='https://github.com/benfred/py-spy',distribution='https://pypi.org/project/py-spy/',
    wheel=wheel.name,wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary).hexdigest(),
    version=version.stdout.strip(),binary=target.relative_to(root).as_posix(),license_retained=license_text is not None,
    runtime_environment_or_locks_changed=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'isolated-profiler-manifest.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
