from pathlib import Path
import hashlib,json,os,re,sys,urllib.request,urllib.error
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.research import current_core_hash
base='http://127.0.0.1:8767'
with urllib.request.urlopen(base+'/api/health',timeout=10) as response:health=json.load(response)
assert health['source_current'] and health['worker_alive'] and health['worker_ready'] and health['core_hash']==current_core_hash()
with urllib.request.urlopen(base+'/',timeout=10) as response:document=response.read()
assert document==(root/'frontend/dist/index.html').read_bytes()
files=[]
for asset in re.findall(rb'(?:src|href)="(/assets/[^"<>]+)"',document):
    path=asset.decode();local=root/'frontend/dist'/path.lstrip('/')
    with urllib.request.urlopen(base+path,timeout=10) as response:body=response.read()
    assert body==local.read_bytes();files.append(dict(path=path,sha256=hashlib.sha256(body).hexdigest()))
assert any(f['path'].endswith('.js') for f in files)
try:
    with urllib.request.urlopen('http://127.0.0.1:8768/api/health',timeout=2):raise AssertionError('Retired8768 server still responds.')
except (urllib.error.URLError,TimeoutError):pass
value=dict(scope='Actual restarted main localhost application and served asset identity. Readiness/configuration is not provider authentication or final product acceptance.',base_url=base,health=health,retired_8768_responds=False,assets=files)
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(out/'current-main-runtime.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
