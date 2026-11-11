"""Move four actual external boundary probes into normal backend test discovery."""
from pathlib import Path
import hashlib,json,os
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);records=[]
specs=[('spread-read-repair-boundary-supplement.py','test_spread_saved_boundaries.py',[
 ('Actual saved-record corruption boundaries on unchanged0.25 numerical source.','Actual saved-record corruption boundaries; no new financial computations.'),
 ('import json,os,sys,pytest','import json,os,pytest'),
 ("sys.path.insert(0,str(Path.cwd()/'tests'))\n",''),
 ('def record(name,values):\n',"def record(name,values):\n if not os.environ.get('PA_EVIDENCE_RUN_DIR'):return\n")]),
 ('spread-empty-and-interrupted-boundaries.py','test_spread_transaction_boundaries.py',[
 ('from pathlib import Path\nimport sys,pytest\nsys.path.insert(0,str(Path.cwd()/\'tests\'))','import pytest')])]
for original,name,transforms in specs:
 p=root/'verification/runs'/original;raw=p.read_text(encoding='utf-8');digest=hashlib.sha256(p.read_bytes()).hexdigest()
 for before,after in transforms:
  assert raw.count(before)==1,(name,before,raw.count(before));raw=raw.replace(before,after,1)
 compile(raw,name,'exec')
 for folder in ['src','next-src']:
  dest=root/'data/dev026'/folder/'tests'/name;assert not dest.exists();dest.write_text(raw,encoding='utf-8')
  records.append(dict(path=dest.relative_to(root).as_posix(),original=p.relative_to(root).as_posix(),original_sha256=digest,installed_sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
(out/'boundary-test-installation.json').write_text(json.dumps(dict(scope=__doc__,tests=4,installed_files=records,production_source_changed=False,final_acceptance_certified=False),indent=2),encoding='utf-8');print(json.dumps(dict(actual_boundary_tests_installed=4,source_copies=2,production_source_changed=False)))
