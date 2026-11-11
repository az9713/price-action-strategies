"""Capture-helper preflight on a retained interrupted synthetic run; no UI pass claimed."""
from pathlib import Path
import hashlib,json,os,sys
root=Path.cwd();dev=root/'data/dev025/src';sys.path.insert(0,str(dev));sys.path.insert(0,str(dev/'tests'))
subject=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'))
assert subject['changed_during_check']==[] and subject['owned_http_and_worker_retired']
for name,digest in subject['source_files'].items():assert hashlib.sha256((dev/name).read_bytes()).hexdigest()==digest,name
from backend.lab.service import Lab
from spread_browser_originals import retain
value=retain(Lab(root/subject['store_relative']),subject['dataset'],Path(os.environ['PA_EVIDENCE_RUN_DIR']),root)
print(json.dumps(dict(scope=__doc__,captured_original_synthetic_accounts=value['actual_ui_accounts'],financial_work_executed=False,workflow_pass_claimed=False)))
