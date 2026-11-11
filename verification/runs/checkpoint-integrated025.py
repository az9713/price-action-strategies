"""Coherent integrated0.25 component evidence and credential-free source recovery archive.

This is not certification of the remaining research funnel or final422 cases.
"""
from pathlib import Path
import hashlib,json,os,sys,xml.etree.ElementTree as ET,zipfile
root=Path.cwd();run=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
labels={
 'full':'spread-version025-current-full-backend-regression-and-twenty-seven-module-coverage',
 'boundaries':'spread-version025-original-status-selected-record-and-repair-boundary-supplement',
 'empty':'spread-version025-original-prefix-empty-interrupted-and-duplicate-plan-boundaries',
 'gates':'spread-version025-current-source-checked-twenty-seven-module-unrounded-95-90-gate',
 'browser':'spread-version025-current-eighteen-browser-workflows-raw-json-original-accounts-and-wake-lease',
 'audit':'spread-version025-browser-original-wrapper-aware-full-account-csv-and-presentation-fact-audit',
 'mutations6':'spread-version025-six-byte-preserved-selected-envelope-repair-and-reverse-reservation-mutations',
 'mutations7':'integrated-version025-seven-original-account-authority-primary-scope-and-strict-contract-mutations',
 'integration':'integrated-version025-source-assets-original-store-and-healthy-managed-worker-parity',
 'compatibility':'integrated-version025-twelve-correctly-scoped-synthetic-desktop-compatibility-workflows',
 'saved':'integrated-version025-live-saved-context-historical-selection-and-original-legacy-preservation',
 'build':'integrated-version025-canonical-typed-build-byte-identical-to-served-assets',
 'runtime':'integrated-version025-final-single-managed-tree-retired-verification-workers-and-idle-store',
 'inventory':'integrated-version025-unchanged-83-requirement-422-case-120-combination-plan-inventory',
 'reconstruction':'spread-version025-actual-source-overlay-reconstruction-core-assets-and-schema-gate-smoke'}
receipts={};lineage=[];checked=0
def load(label,success=True):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=read(p)
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 assert (r['command']['exit_code']==0)==success
 for a in r['artifacts']:
  q=root/a['path'];assert q.resolve().is_relative_to(root.resolve()) and q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return p,r
for key,label in labels.items():
 p,r=load(label);receipts[key]=r;checked+=len(r['artifacts']);lineage.append(dict(role=key,path=p.relative_to(root).as_posix(),sha256=sha(p),artifacts=len(r['artifacts'])))
def artifact(key,name):return read(root/next(a['path'] for a in receipts[key]['artifacts'] if a['path'].endswith('/'+name)))
def tests(key):
 a=next(a for a in receipts[key]['artifacts'] if a['path'].endswith(('/dev025-junit.xml','/junit.xml')))
 nodes=list(ET.parse(root/a['path']).iter('testsuite'));counts={k:sum(int(n.attrib.get(k,0)) for n in nodes) for k in ['tests','failures','errors','skipped']}
 assert counts['failures']==counts['errors']==counts['skipped']==0;return counts['tests']
assert tests('full')==2239 and tests('boundaries')==3 and tests('empty')==1 and tests('browser')==18 and tests('compatibility')==12 and tests('saved')==2
current={p.relative_to(root).as_posix():sha(p) for p in source_paths(root)}
subject=artifact('full','dev025-source-subject.json');assert subject['source_files']==current and subject['changed_during_check']==[]
gates=artifact('gates','dev025-twenty-seven-module-gates.json');assert gates['ready'] and len(gates['modules'])==27
assert all(g['required_statements']==95 and g['required_branches']==90 and g['ready'] and sha(root/g['path'])==g['source_sha256'] for g in gates['modules'])
for key,count,baseline,name in [('mutations6',6,6,'spread-selection-link-mutations.json'),('mutations7',7,19,'spread-account-mutations.json')]:
 v=artifact(key,name);assert v['all_assertion_killed'] and v['original_development_source_unchanged'] and len(v['mutants'])==count and v['baseline']['tests']==baseline
 assert all(m['exit_code']==1 and m['failures']>0 and m['errors']==m['skipped']==0 for m in v['mutants'])
audit=artifact('audit','spread-ui-independent-account-export-facts.json');assert len(audit['accounts'])==3 and all(a['trades']==110 and a['ledger_rows']==220 and a['daily_marks']==10 and a['presentation']['facts_checked']==81 and a['loss_retained'] for a in audit['accounts'])
integration=artifact('integration','integrated-source-store-parity.json');assert integration['source_files_verified']==len(current) and integration['original_database_values_preserved']
saved=artifact('saved','saved-live-original-preservation.json');assert saved['source_unchanged'] and saved['no_financial_jobs_created'] and not saved['price_cache_copied'] and all(n==0 for table,n in saved['additions'].items() if table!='events')
assert set(saved['new_event_kinds'])<={'result_view_saved'}
native=artifact('runtime','current-process-tree.json');runtime=artifact('runtime','managed-runtime.json');assert not native['separate_obsolete_project_python_detected'] and native['duplicate_store_start_rejected'] and runtime['pending_jobs']==0 and runtime['database_jobs_observed']==348
assert runtime['managed_session']==51750 and runtime['health']['core_hash']==integration['health']['core_hash'] and runtime['health']['source_current']
build=artifact('build','canonical-build-parity.json');assert build['byte_identical_to_served']
catalog=read(root/'verification/catalog.json');assert len(catalog['requirements'])==83 and len(catalog['cases'])==422 and sum(c['id'].startswith('MATRIX-') for c in catalog['cases'])==120
failure_labels=['spread-original-child-orphan-double-parent-record-loss-authored-refusal-contract','spread-version025-first-current-twenty-seven-module-unrounded-numerical-gate',
 'spread-version025-current-eighteen-browser-workflows-public-schema-and-owned-lifecycle','spread-version025-current-browser-original-bytes-complete-decimal-accounts-csv-and-presentation-fact-audit',
 'spread-version025-valid-empty-interrupted-batch-and-duplicate-staged-plan-boundaries','spread-version025-current-twenty-seven-module-unchanged-95-90-passing-gate',
 'integrated-version025-twelve-existing-synthetic-desktop-compatibility-workflows','spread-isolated-version025-rulebook-public-schema-and-partial-implementation-map-update']
failures=[]
for label in failure_labels:
 p,r=load(label,False);checked+=len(r['artifacts']);failures.append(dict(path=p.relative_to(root).as_posix(),sha256=sha(p),exit_code=r['command']['exit_code'],artifacts=len(r['artifacts'])))
base=read(root/'verification/runs/20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint/source-checkpoint-manifest.json')
paths=list(source_paths(root))+[root/v['path'] for v in base if not v['path'].startswith('frontend/dist/') and (root/v['path']).is_file()]
paths+=list((root/'frontend/dist').rglob('*'))
for name in ['STATUS.md','VIDEO_REVIEW.md','SCREENSHOT_FINDINGS.md','research/source-manifest.json','research/screenshots/README.md']:
 if (root/name).is_file():paths.append(root/name)
for name in ['spread-selection-contract.json','spread-worker-contract.json','spread-account-handoff-contract.json','spread-ui-integration-contract.json','common-sampling-contract.json']:paths.append(root/'verification/fixtures'/name)
historical=['20261108T083402678603Z-full-backend-matched-controls-coverage.json','20261108T100203771424Z-utf8-restored-full-701-backend-coverage.json','20261108T141545788080Z-presenter-fixed-current-full-regression-and-coverage.json','20261108T153959895989Z-news-strict-recovery-and-release-artifact-current-full-regression.json']
paths+=[root/'verification/receipts'/n for n in historical]
helpers=['check-dev025.py','run-dev025-spread-browser.py','run-main025-synthetic-browser.py','run-live025-saved-browser.py','spread_browser_originals.py','verification_awake.py','run-with-verification-wake.py','spread-browser.config.ts','legacy025-browser.config.ts','live025-saved-browser.config.ts','audit-spread-ui-accounts.py','check-dev025-twenty-seven-module-gates.py','combine-spread-durable-coverage.py','spread-selection-link-mutations.py','spread-account-mutations.py','spread-read-repair-boundary-supplement.py','spread-empty-and-interrupted-boundaries.py','integrate-dev025.py','check-managed-version025-runtime.py','verify-current025-single-server-tree.py','check-main025-stage-build.py','checkpoint-integrated025.py','source-page12-next-research-gap.md','spread-ui-next-plan.md','spread-next-integration-notes.md']
paths+=[root/'verification/runs'/n for n in helpers]
for folder in ['spread-browser-tests','legacy025-browser-tests','live025-saved-browser-tests']:paths+=list((root/'verification/runs'/folder).glob('*.ts'))
files={p.relative_to(root).as_posix():p for p in paths if p.is_file()};manifest=[]
archive=run/'integrated025-source-checkpoint.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,p in sorted(files.items()):
  assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in Path(name).parts) and not name.startswith(('data/','frontend/node_modules/'))
  assert p.suffix.lower() not in {'.sqlite3','.db','.parquet','.gz','.mp4','.webm','.png','.jpg','.zip'}
  raw=p.read_bytes();z.writestr(name,raw);manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
with zipfile.ZipFile(archive) as z:
 for entry in manifest:raw=z.read(entry['path']);assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
assert {p.relative_to(root).as_posix():sha(p) for p in source_paths(root)}==current
(run/'integrated025-source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
value=dict(scope=__doc__,core_hash=runtime['health']['core_hash'],source_files=current,archive_files=len(manifest),archive_sha256=sha(archive),checked_receipt_artifacts=checked,receipts=lineage,retained_failures=failures,
 full_backend_cases=2239,additional_original_boundary_cases=4,current_spread_browser_cases=18,owned_compatibility_cases=12,in_place_saved_legacy_cases=2,actual_assertion_killed_mutants=13,counts_are_not_independent_market_replications=True,
 numerical_gates=gates['modules'],native_runtime=runtime,original_rows_preserved=True,allowed_saved_view_event_additions=saved['additions']['events'],main_source_integrated=True,final_acceptance_certified=False,
 remaining='Source-style10000 trade twins; era/instrument replication, stability, equal-family ensembles; actual bounded100000 numerical stress; remaining detector/dial/input/lifecycle/security/privacy/accessibility/clean-reproduction use cases; and one final83/422/120 conformance certificate.',
 recovery_limits='Source-only archive. No credentials, price cache, live databases, private raw traces/coverage DBs, downloaded video/media or installed dependencies. In-place historical legacy checks require their original private saved records; they are not reconstructed as fabricated historical data. Backend test fixtures and the four historical catalog-receipt metadata files are included. Existing-environment reconstruction is not a new dependency installation.')
(run/'integrated025-component-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k in ['scope','core_hash','archive_files','checked_receipt_artifacts','full_backend_cases','additional_original_boundary_cases','current_spread_browser_cases','owned_compatibility_cases','in_place_saved_legacy_cases','actual_assertion_killed_mutants','main_source_integrated','final_acceptance_certified']},indent=2))
