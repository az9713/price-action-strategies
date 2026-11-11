"""Verify that component checks have not been promoted to a final acceptance certificate."""
from pathlib import Path
import json,os,subprocess,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
p=subprocess.run([sys.executable,'verification/check_evidence.py','release'],cwd=root,capture_output=True,text=True,encoding='utf-8',errors='replace')
for name,value in [('stdout',p.stdout),('stderr',p.stderr)]:
 (out/('release-gate-'+name+'.log')).write_text(value.replace(str(root),'<workspace>').replace(str(Path.home()),'<user-home>'),encoding='utf-8')
value=json.loads(p.stdout);assert p.returncode==1 and value['ready'] is False
assert value['mandatory_cases']==422 and value['verified_cases']<422 and value['unverified_cases']>0
summary=dict(scope=__doc__,release_gate_exit_code=p.returncode,ready=False,mandatory_cases=value['mandatory_cases'],final_verified_cases=value['verified_cases'],unverified_cases=value['unverified_cases'],errors=value['errors'],interpretation='Final acceptance evidence only; a zero certified count does not mean zero implementation or software tests.')
(out/'release-boundary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))
