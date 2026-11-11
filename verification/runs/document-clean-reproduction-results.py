"""Record bounded clean-install/offline evidence without archiving additional source or data."""
from pathlib import Path
import hashlib,json,os

root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
ids={
 'install':'20261109T101405014361Z-current-clean-locked-install-frontend-byte-rebuild-and-full-backend-reproduction',
 'offline':'20261109T102347475991Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial',
 'runtime':'20261109T102535948662Z-current-server-after-clean-reproduction-single-tree-and-retired-test-workers',
}
evidence=[]
for key,identifier in ids.items():
 path=root/'verification/receipts'/(identifier+'.json')
 raw=path.read_bytes();receipt=json.loads(raw)
 assert receipt['command']['exit_code']==0
 assert not any(note.startswith(('Source changed','Missing requested')) for note in receipt['notes'])
 evidence.append(dict(role=key,path=path.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))

def prefix(index):
 relative='receipts/' if index else 'verification/receipts/'
 def link(key,title):return '['+title+']('+relative+ids[key]+'.json)'
 return '\n\n'.join([
  '## Current0.24 — clean-install and offline reproduction supplement',
  link('runtime','Current native process-tree and duplicate-start check')+' observes one healthy managed app tree at http://127.0.0.1:8767: launcher34720, HTTP40760 and worker20832. All348 main-store jobs are idle. The bounded project-path/descendant inventory finds no obsolete server or remaining test worker. No process was killed. A second start against the same store is rejected even on another port. Manual taskkill is unnecessary. The project remains active and not ready for final release.',
  link('install','Fresh locked installation and full regression')+' passes on Python3.13.5/Node22.22.0/npm9.9.4. A new venv excludes system site-packages, installs every locked distribution and passes pip check. Its numerical core fingerprint matches unchanged e25126a77ca89ae2c7301d50d4551cdadee9c43dd88f011b4bd4569f97ba395d. A fresh npm ci --ignore-scripts installation rebuilds every frontend asset byte identically. All1893 backend cases pass with zero failures/errors/skips; the four earlier supplementary legacy-report cases remain separate. Credentials, real prices, the live database and installed dependencies were not copied. Download caches may be warm. npm cache retry warnings and the large-bundle warning are retained.',
  link('offline','Original/fresh offline saved-account and restart comparison')+' executes13 signals/nine trades for each of long and short in each environment on clearly synthetic complete sessions. Actual workers stop, release the lease and restart. Saved datasets/strategies/reports reopen; complete manifests/reports match across environments without excluded financial or provenance fields. JSON/CSV/HTML/presentation exports remain byte-identical after restart. Positive controls prove the process-local Python socket guard rejects external resolution and connection. The saved workflow makes zero external attempts; an explicitly nonsecret-fixture uncached provider request fails clearly. This is API/process fault injection, not an OS firewall or graphical offline-browser check.',
  'The first native audit failure and first offline positive-fixture failure remain retained. The former counted its own recorder tree; the latter generated no primary signals. The corrected audit excludes only its identified process tree. The corrected fixture uses existing authored strict-pivot geometry and a reflected second instrument. No production formulas, source, thresholds or costs changed.',
  'The83 requirements/422 mandatory cases/120 baseline combinations and final-release gate remain unchanged and unready. Balanced spread,10000 matched trade twins,era/instrument replication/stability/family ensembles,bounded100000 numerical stress,remaining detector/dial/lifecycle cases,mobile/keyboard/accessibility/security/privacy and coherent final acceptance remain mandatory. This supplement narrows installation/API-offline reproduction gaps; it does not certify those remaining requirements.',
  'Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). US-stock/ETF adaptations and unavailable private recipes/grid remain disclosed. Futures,forex and crypto remain later options. Earlier checkpoint entries follow as retained history.',
 ])+'\n\n'

for name,index in [('STATUS.md',False),('verification/evidence-index.md',True)]:
 path=root/name;old=path.read_text(encoding='utf-8')
 assert not old.startswith('## Current0.24 — clean-install')
 path.write_text(prefix(index)+old,encoding='utf-8')
 (out/path.name).write_bytes(path.read_bytes())

ledger_path=root/'verification/defects.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
identifier='D-VERIFY-OFFLINE-POSITIVE-GEOMETRY-001'
if not any(d['id']==identifier for d in ledger['defects']):
 ledger['defects'].append(dict(id=identifier,status='corrected_original_fresh_accounts_and_offline_restarts_passed',area='Offline positive-case fixture',observed='Initial random/shared-open path generated no primary strict-pivot signals; the mandatory positive-account assertion failed.',fix='Use existing authored strict-pivot geometry plus its reflection, completed to whole sessions. No production detector/account formula or gate changed.',initial_evidence='verification/receipts/20261109T102237014227Z-current-clean-original-and-fresh-complete-offline-account-restart-and-uncached-provider-denial.json',regression_evidence='verification/receipts/'+ids['offline']+'.json'))
ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
(out/'defects.json').write_bytes(ledger_path.read_bytes())
value=dict(scope=__doc__,receipts=evidence,retained_defects=len(ledger['defects']),fresh_full_regression_passed=1893,offline_complete_reports_equal=True,main_server_only_at_observed_check=True,production_source_changed=False,final_acceptance_certified=False)
(out/'documentation-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
