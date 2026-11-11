"""Record the observed server resolution, including the retained audit-self-match failure."""
from pathlib import Path
import json,os,shutil
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);passing='20261109T101052486797Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal';failed='20261109T101032684832Z-current-server-native-tree-root-cause-and-live-duplicate-start-refusal'
p=json.loads((root/'verification/receipts'/(passing+'.json')).read_text(encoding='utf-8'));f=json.loads((root/'verification/receipts'/(failed+'.json')).read_text(encoding='utf-8'));assert p['command']['exit_code']==0 and f['command']['exit_code']==1
prefix='''## Server lifecycle resolution — current observed state

Earlier repeated verification launches left obsolete servers running. Windows virtual-environment launchers, the HTTP interpreter and spawned numerical workers made each instance appear as multiple PIDs. The current implementation uses a managed foreground session and an OS-held single-store lease; another port cannot bypass it. No more manual taskkill is required.

The [native process-tree and live duplicate-start receipt](RECEIPT) observes exactly one current app tree after excluding the positively identified audit process tree: launcher34720 → HTTP40760 → worker20832. The app is healthy at http://127.0.0.1:8767, all348 stored jobs are idle, and an attempted second start fails with exit3 before starting a competing worker. No obsolete project process was found in that bounded inventory; no process was killed. This is a point-in-time project-path/descendant check, not a claim about inaccessible or unrelated processes.

The [first audit failure](FAILED) is retained: its initial expected-tree assertion accidentally included its own recording/audit interpreters. The corrected audit excludes only its identified ancestor/descendant tree. This was an audit fixture error, not evidence of another obsolete server.

The project remains in progress; this operational resolution does not certify the final422-case release.

'''
for name in ['STATUS.md','verification/evidence-index.md']:
 path=root/name;prefix_path='verification/receipts/' if name=='STATUS.md' else 'receipts/'
 text=path.read_text(encoding='utf-8');heading='## Server lifecycle resolution'
 if not text.startswith(heading):path.write_text(prefix.replace('RECEIPT',prefix_path+passing+'.json').replace('FAILED',prefix_path+failed+'.json')+text,encoding='utf-8')
 shutil.copyfile(path,out/path.name)
ledger=root/'verification/defects.json';value=json.loads(ledger.read_text(encoding='utf-8'));identifier='D-VERIFY-PROCESS-SELF-MATCH-001'
if not any(d['id']==identifier for d in value['defects']):value['defects'].append(dict(id=identifier,status='corrected_native_inventory_and_live_duplicate_refusal_passed',area='Native audit process identity',observed='First bounded tree assertion counted its own recorder/audit venv launchers as unexpected project processes.',fix='Exclude only the positively identified current audit Python ancestry and descendants; retain all other project matches for assertion.',initial_evidence='verification/receipts/'+failed+'.json',regression_evidence='verification/receipts/'+passing+'.json'))
ledger.write_text(json.dumps(value,indent=2),encoding='utf-8');shutil.copyfile(ledger,out/'defects.json')
print(json.dumps(dict(server_issue_resolved_at_observed_check=True,manual_taskkill_needed=False,production_source_changed=False,first_failed_audit_retained=True,final_release_certified=False)))
