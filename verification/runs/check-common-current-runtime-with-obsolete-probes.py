"""Recheck the managed main and bounded old HTTP endpoints; no OS-wide listener inference."""
from pathlib import Path
import json,os,runpy,urllib.request
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
runpy.run_path(str(root/'verification/runs/check-common-current-runtime.py'))
probes=[]
for port in [8768,8769,8770,8771]:
 try:
  with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=1) as response:
   # A response is enough to fail this retirement check; do not publish an
   # unrelated service's body or stop an unidentified process.
   status=response.status
 except Exception as error:probes.append(dict(port=port,health_response=False,error_type=type(error).__name__))
 else:probes.append(dict(port=port,health_response=True,status=status))
(out/'obsolete-http-probes.json').write_text(json.dumps(dict(scope=__doc__,probes=probes,os_wide_listener_inventory_certified=False),indent=2),encoding='utf-8')
assert not any(p['health_response'] for p in probes),probes
print(json.dumps(dict(obsolete_health_endpoints_answering=0,ports=[p['port'] for p in probes],os_wide_listener_inventory_certified=False)))
