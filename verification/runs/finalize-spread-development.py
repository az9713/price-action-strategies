"""Recoverable isolated spread-core checkpoint; worker/API/UI and final acceptance remain incomplete."""
from pathlib import Path
import hashlib,json,os,shutil,xml.etree.ElementTree as ET
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
identifiers={
 'focus':'20261109T112258358688Z-spread-isolated-current-97-case-complete-core-and-fault-branch-coverage',
 'gate':'20261109T112445415073Z-spread-isolated-current-97-case-unrounded-95-90-numerical-core-gate',
 'compatibility':'20261109T111059531299Z-spread-isolated-subset-loading-legacy-guard-cache-and-common-search-compatibility-regression',
 'mutations':'20261109T111700424122Z-spread-isolated-current-source-ten-critical-mutations-after-subset-compatibility',
 'runtime':'20261109T112445499707Z-spread-development-kept-verified-app-current-and-all-isolated-test-processes-retired',
}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipts={};artifacts=0
for key,identifier in identifiers.items():
 p=root/'verification/receipts'/(identifier+'.json');r=json.loads(p.read_text(encoding='utf-8'))
 assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];q.resolve().relative_to(root.resolve());assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts+=1
 for name in ['data/dev025/src/backend/lab/spread.py','data/dev025/src/backend/lab/service.py']:
  matches=[i for i in r['subject']['input_manifests'] if i['path']==name]
  if matches:assert sha(root/name)==matches[0]['sha256']
 receipts[key]=(p,r)
def read_artifact(key,name):
 a=next(a for a in receipts[key][1]['artifacts'] if a['path'].endswith('/'+name));return json.loads((root/a['path']).read_text(encoding='utf-8'))
def tests(key):
 a=next(a for a in receipts[key][1]['artifacts'] if a['path'].endswith('/dev025-junit.xml'))
 suites=list(ET.parse(root/a['path']).iter('testsuite'));assert all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
 return sum(int(s.attrib['tests']) for s in suites)
assert tests('focus')==97 and tests('compatibility')==268
gate=read_artifact('gate','spread-coverage-gate.json');assert gate['ready'] and gate['minimum_statements']==95 and gate['minimum_branches']==90
mutations=read_artifact('mutations','spread-mutations.json');assert mutations['baseline']['tests']==47 and len(mutations['mutants'])==10 and mutations['all_test_killed']
subject=read_artifact('focus','dev025-source-subject.json');assert subject['changed_during_check']==[]
for name,digest in subject['source_files'].items():assert sha(dev/name)==digest
primary=read_artifact('focus','primary-complete-signals.json');actual=read_artifact('focus','actual-qualified-selection-and-replay.json')
assert primary['signal_count']==350 and primary['excluded_warmup_signals']==349 and len(primary['signals'])==699
assert actual['result']['complete'] and actual['result']['probe_computations']==9 and actual['replayed']['probe_computations']==0
assert [e['evidence']['signal_count'] for e in actual['events'] if e['kind']=='probe_completed']==[0]*8+[110]
runtime=read_artifact('runtime','managed-runtime.json');assert runtime['pending_jobs']==0 and runtime['health']['core_hash']=='e25126a77ca89ae2c7301d50d4551cdadee9c43dd88f011b4bd4569f97ba395d'

# Explicit small source overlay over the already recorded0.24 source archive.
# Copy only the named code/tests/docs/contracts below, never data or dependencies.
base_id='20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint'
base=json.loads((root/'verification/receipts'/(base_id+'.json')).read_text(encoding='utf-8'))
base_manifest=next(a for a in base['artifacts'] if a['path'].endswith('/source-checkpoint-manifest.json'));p=root/base_manifest['path'];assert sha(p)==base_manifest['sha256']
known={v['path']:v['sha256'] for v in json.loads(p.read_text(encoding='utf-8'))}
allowed={'backend/lab/spread.py','backend/lab/service.py','tests/test_spread.py','tests/test_spread_probe.py','tests/test_spread_scope.py','tests/test_spread_faults.py','PLAN.md','VERIFICATION_PLAN.md'}
differences={name:digest for name,digest in subject['source_files'].items() if known.get(name)!=digest}
assert set(differences)<=allowed,set(differences)-allowed
names=set(differences)|{'verification/fixtures/spread-selection-contract.json','verification/fixtures/common-sampling-contract.json'};overlay=[]
for name in sorted(names):
 p=dev/name;q=out/'source-overlay'/name;assert not any(part.lower().startswith('.env') for part in p.parts);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 overlay.append(dict(path=name,sha256=sha(q),bytes=q.stat().st_size))
overlay_value=dict(base_receipt='verification/receipts/'+base_id+'.json',development_source_files=subject['source_files'],changed_or_added_source=overlay,scope='Source recovery overlay only; not an integrated runnable0.25 product or final release. No credentials, prices, databases, raw traces, coverage DBs or installed dependencies copied.')
(out/'source-overlay-manifest.json').write_text(json.dumps(overlay_value,indent=2),encoding='utf-8')

failure_ids=[
 '20261109T104029406130Z-spread-isolated-authored-exact-balance-freeze-qualification-replay-first-contract',
 '20261109T104952434255Z-spread-isolated-authored-distinct-retry-attempts-current-plan-and-external-identity-adversarial-contract',
 '20261109T105402570644Z-spread-isolated-authored-actual-primary-signal-evidence-warmup-and-preprice-guard-contract',
 '20261109T105652473592Z-spread-isolated-authored-primary-only-protection-cache-separation-and-news-scope-before-implementation',
 '20261109T110135609527Z-spread-isolated-authored-complete-public-recipe-and-default-400-proposal-batch-contract',
 '20261109T112033155557Z-spread-isolated-first-unrounded-95-90-core-coverage-gate',
]
failures=[]
for identifier in failure_ids:
 p=root/'verification/receipts'/(identifier+'.json');r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==1
 failures.append(dict(receipt=p.relative_to(root).as_posix(),sha256=sha(p)))
ledger_path=root/'verification/defects.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
areas=['Authored missing spread core','Distinct retry attempts and current-plan publication','Authored missing actual signal probe','Primary-only protection/cache/news inclusion','Complete published dial catalog','Unrounded new-core branch coverage']
for index,(failure,area) in enumerate(zip(failures,areas),1):
 identifier='D-SPREAD-DEVELOPMENT-'+str(index).zfill(3)
 if not any(d['id']==identifier for d in ledger['defects']):ledger['defects'].append(dict(id=identifier,status='isolated_component_checks_passed_pending_worker_api_ui_integration',area=area,initial_evidence=failure['receipt'],regression_evidence=receipts['focus'][0].relative_to(root).as_posix(),gate_evidence=receipts['gate'][0].relative_to(root).as_posix()))
ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8');(out/'defects.json').write_bytes(ledger_path.read_bytes())

def prefix(index):
 relative='receipts/' if index else 'verification/receipts/'
 def link(key,label):return '['+label+']('+relative+identifiers[key]+'.json)'
 notes='runs/spread-next-integration-notes.md' if index else 'verification/runs/spread-next-integration-notes.md'
 return '\n\n'.join([
  '## D045 in progress — isolated balanced-spread core',
  'The project remains active and not ready for final release. The verified0.24 app remains available at http://127.0.0.1:8767. The new spread implementation is isolated in data/dev025/src and has not been integrated into its worker/API/UI. No credentials, real cached prices, main database or installed dependencies were copied.',
  'Source prompt page10 specifies40000 selected versions,4000 per setup and400 proposals at each greedy choice, with at least40 primary discovery signals. The new core freezes and hashes every bounded proposal file before signals; uses a complete conditional dial catalog and exact prior-centered squared-count discrepancy; records failed/duplicate/unprobed versions and distinct interrupted/retried probes; and hashes a successful selected set before any subsequent account P&L. Its distance/ties/budget are explicit equities choices because the host private details are unknown. The old common-contract scope wording has been corrected to the40000/4000/400 interpretation; no numerical behavior changed from that text correction.',
  link('focus','97 focused core/actual-signal/fault cases')+' pass with zero failures/errors/skips. '+link('gate','The unchanged95% statement/90% branch gate')+' passes at100% statements and96.71% branches for the new spread module. The earlier83.55% branch failure remains retained; no threshold or source exclusion changed. The earlier measurement receipt name mistakenly says58 cases; its actual JUnit count is57, superseded by this97-case run.',
  'Actual synthetic evidence preserves699 complete primary signals:350 within discovery and349 excluded warm-up signals. A small explicitly configured selection keeps the real40-signal threshold: eight zero-signal proposals fail, then one110-signal version is selected; replay performs zero new probes. Full signal documents and hashes remain in the receipt. Tests also keep an unrelated instrument sealed/unread, separate instrument-subset caches, check full parent-file bytes and frozen news hashes, and refuse P&L during signal qualification. This is one selected synthetic version, not40000 source-qualified execution or market-edge evidence.',
  'A separate nonfinancial file fixture actually freezes4000 proposals,400 for each of ten families, and uses explicit stub counts. It does not execute trading accounts. The Fraction oracle independently checks104 candidate deltas. '+link('compatibility','268 compatibility checks')+' pass on the same numerical code, including existing cache/data/guard/common-search flows. '+link('mutations','Ten isolated source mutations')+' are test-killed with zero collection errors/skips against a47-case green baseline; original development and main-app source remain unchanged. The97 and268 counts overlap and must not be added.',
  link('runtime','Post-development native ownership/asset/duplicate-start check')+' observes the one existing managed app tree and348 idle main-store jobs. Separate test processes have retired in the bounded project-path inventory. No manual taskkill is needed.',
  'Next mandatory work is in [the integration notes]('+notes+'): restartable proposal preparation; durable ownership, signal artifacts and attempt registry; full selected-manifest-to-account lifecycle; API/UI/progress/cancel/resume/export; integrated rulebook/schema/mapping/regression and resource evidence. The configured default32million-proposal preparation allowance is not an executed operating envelope or ETA. No partial exhausted pool may become a successful partial search.',
  'The original83 requirements/422 mandatory cases/120 baseline combinations remain binding.10000 trade twins,era/instrument replication/stability/family ensembles,bounded100000 numerical stress,remaining detector/dial/lifecycle cases,mobile/accessibility/security/privacy and coherent final conformance remain mandatory. Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). Exact private recipes/grid/engine are not claimed. Futures,forex and crypto remain later options. Earlier0.24 entries below describe the still-running app.'
 ])+'\n\n'
for name,index in [('STATUS.md',False),('verification/evidence-index.md',True)]:
 p=root/name;old=p.read_text(encoding='utf-8');assert not old.startswith('## D045 in progress');p.write_text(prefix(index)+old,encoding='utf-8');(out/p.name).write_bytes(p.read_bytes())
value=dict(scope=__doc__,receipts={k:p.relative_to(root).as_posix() for k,(p,r) in receipts.items()},artifact_files_checked=artifacts,focused_cases=97,compatibility_cases=268,counts_overlap=True,source_mutations_killed=10,coverage=gate,historical_failures_retained=failures,source_overlay_files=len(overlay),main_app_core=runtime['health']['core_hash'],main_store_pending_jobs=0,worker_api_ui_integrated=False,final_acceptance_certified=False)
(out/'spread-development-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['receipts','historical_failures_retained']},indent=2))
