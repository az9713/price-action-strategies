"""Publish D042 component facts only from completed receipts and retain the unissued final release boundary."""
from pathlib import Path
import hashlib,json,os,re,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
labels=dict(full='study-status-current-full-regression-and-twenty-module-coverage',gate='study-status-current-twenty-module-coverage-gate',build='study-status-current-typed-production-build',monitor='study-status-current-two-desktop-download-repair-history-ownership-and-current-errors',portfolio='study-status-current-two-desktop-portfolio-final-and-result-ownership',capacity='study-status-current-prespecified-10-1000-100000-registration-inputs-and-protected-scope',mutants='study-status-current-nine-isolated-critical-mutations',audit='study-status-current-independent-canonical-input-history-complete-account-csv-and-offline-audit',runtime='study-status-current-managed-owner-all-job-idleness-assets-and-duplicate-store-refusal',plan='study-status-current-83-422-120-plan-inventory',checkpoint='study-status-current-ten-receipt-source-fixture-build-recovery-checkpoint',boundary='study-status-current-honest-final-release-boundary')
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==0
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes']);return p,r
receipts={k:latest(label) for k,label in labels.items()}
def artifact(key,suffix):
 selected=[a for a in receipts[key][1]['artifacts'] if a['path'].endswith(suffix)];assert len(selected)==1,(key,suffix)
 p=root/selected[0]['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==selected[0]['sha256'];return p
checkpoint=json.loads(artifact('checkpoint','/checkpoint.json').read_text(encoding='utf-8'));assert len(checkpoint['selected_receipts'])==10
suites=list(ET.parse(artifact('full','junit.xml')).iter('testsuite'));tests=sum(int(s.attrib.get('tests',0)) for s in suites)
assert tests==checkpoint['full_current_regression_tests'] and all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
gate=json.loads(artifact('gate','/numerical-coverage-gate.json').read_text(encoding='utf-8'));assert gate['ready'] and len(gate['modules'])==20
capacity=json.loads(artifact('capacity','/study-status-capacity.json').read_text(encoding='utf-8'));assert capacity['complete'] and capacity['counts_prespecified']==[10,1000,100000]
assert all(r['raw_study_spec_reads']==0 and r['fully_resolved_configs_equal'] and r['protected_read_blocked_before_viewed_write'] and r['price_accounts_executed']==0 and r['request_bytes']<=65*1024*1024 and r['status_bytes']<=65536 and r['list_bytes']<=2097152 for r in capacity['rows'])
mutants=json.loads(artifact('mutants','/study-status-mutation-results.json').read_text(encoding='utf-8'));assert len(mutants['mutations'])==9 and mutants['baseline']['tests']==42 and mutants['original_source_unchanged']
assert all(m['result']['assertion_failures']>0 and m['result']['errors']==m['result']['skipped']==0 for m in mutants['mutations'])
monitor=json.loads(artifact('audit','/independent-study-status-browser-evidence.json').read_text(encoding='utf-8'));assert len(monitor['metadata_profiles'])==len(monitor['controlled_transport_profiles'])==2
assert all(p['configurations']==p['unique_configs']==1000 and p['original_bytes_equal_live_inputs'] for p in monitor['metadata_profiles'])
joint=json.loads(artifact('audit','/independent-browser-joint-studies.json').read_text(encoding='utf-8'));assert len(joint['profiles'])==2
accounts=sum(len(p['accounts']) for p in joint['profiles']);screenshots=sum(len(p['page_screenshots']) for p in joint['profiles']);assert accounts==6 and screenshots==72
runtime=json.loads(artifact('runtime','/managed-runtime.json').read_text(encoding='utf-8'));health=runtime['health'];assert health['core_hash']==monitor['core_hash'] and health['source_current'] and runtime['pending_jobs']==0
boundary=json.loads(artifact('boundary','/release-boundary.json').read_text(encoding='utf-8'));assert boundary['ready'] is False and boundary['final_verified_cases']==0 and boundary['mandatory_cases']==422
ledger_path=root/'verification/defects.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
for row in ledger['defects']:
 if row['id'] in ['D-STUDY-STATUS-RAW-SPEC-001','D-LEGACY-TRIAL-FAILURE-ISOLATION-001','D-STUDY-INDEX-EARLY-REJECTION-001','D-STUDY-INDEX-MALFORMED-SHAPE-001','D-LEGACY-ORIGINAL-BLOB-001']:
  row.update(status='corrected_current_full_regression_twenty_module_gates_component_checkpoint_passed',current_full_regression_receipt=receipts['full'][0].relative_to(root).as_posix())
ledger_path.write_text(json.dumps(ledger,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def prefix(index=False):
 def link(key,title):return '['+title+']('+('' if index else 'verification/')+'receipts/'+receipts[key][0].name+')'
 scale=capacity['rows'][-1]
 return '\n\n'.join([
 '## Current0.22 - verified study-monitoring and legacy-recovery component checkpoint',
 f"The managed app answers at http://127.0.0.1:8767. Core `{health['core_hash']}`, frontend `index-Cndn7EqH.js`, session {runtime['managed_session']}, HTTP {health['server_pid']}/worker {health['worker_pid']}. The goal remains active and **not ready for final release**. These are component checks, not final 422-case conformance.",
 'D042 adds bounded study summaries, complete original input downloads and derived-cache repair. Polling/protected-scope reads avoid raw study specs. Verified scopes preserve complete instruments, inclusive dates, live lifecycle and exact consumed-final ownership. Original registration/candidate/reservation/consumption events remain authority. Invalid scope fails closed; corrupted original inputs cannot be certified. Tampered candidates now reject before reservation, while already-queued work still revalidates before prices.',
 'Legacy reconstruction already used a streaming cursor. Per-job savepoints now isolate malformed JSON/nonobjects/arms/sampling/BLOBs and duplicate trial IDs; partial derived rows roll back, valid neighbors remain usable, original bytes survive and diagnostics remain explicitly unverified. No prespecified plan or computation attempt is invented. Earlier working-note fetchall wording was corrected before implementation.',
 link('full',f'{tests:,} full current regression tests')+' pass with zero failures/errors/skips. '+link('gate','All 20 module coverage gates')+' meet the unchanged 95% statement/90% branch thresholds. Coverage does not establish every use case or a profitable trading edge. First failures and their artifacts remain unchanged.',
 link('monitor','Four metadata/history desktop cases')+' pass at both sizes: actual 1,000-rule original-byte downloads/repair and controlled 500-record pagination with delayed success/failure, visible current error/retry and measured periodic serialization. The controlled transport IDs/names are explicitly not real registrations or financial evidence. Study paging has its own state; report/job selectors retain their original feed. Candidate counts are shown as unverified when the cache is unverified.',
 link('portfolio','Four actual joint-study/result-ownership desktop cases')+' pass for synthetic imports, whole-rule freezing, screening, reserved-final cancel/resume, consumed final evaluation, saved inspection, offline pages and reversed/stale/current report responses. '+link('audit','Independent canonical and supplied-signal accounting audit')+f' verifies 2,000 unique rules/original input bytes, {accounts} complete Decimal accounts/trade CSVs and {screenshots} offline page screenshots. This uses saved production signals and does not certify detector omission, every interval or a market edge.',
 link('capacity','Prespecified 10/1,000/100,000 registration and complete HTTP input measurements')+f" pass. The largest status is {scale['status_bytes']:,} bytes, complete export {scale['input_export_bytes']:,} bytes and traced status heap {scale['status_python_peak_bytes']:,} bytes. Supported compact requests fit the original 65 MiB envelope while every resolved field is retained in stored/exported configs. Monitoring/protection read zero raw specs; protected rejection writes no viewed window. These ASGI measurements execute zero numerical accounts and are not network SLOs or numerical 10,000/100,000 throughput certification.",
 link('mutants','Nine isolated critical mutations')+' are assertion-killed against a 42-case green baseline, with no collection errors/skips or original source edits. '+link('build','Typed production build')+' passes; the large-bundle warning remains. '+link('runtime','Managed owner, full-database idleness, actual assets and competing-store refusal')+f" pass across all {runtime['database_jobs_observed']} stored jobs, zero pending. Previous managed instances exited through Ctrl+C. No manual taskkill is needed; native OS-wide process absence remains uncertified.",
 link('checkpoint','Coherent recovery checkpoint')+f" binds 10 identical-source passing receipts/{checkpoint['artifact_files_checked']} checked artifacts, retains {len(checkpoint['historical_failures_retained'])} historical failure runs and archives {checkpoint['source_archive_files']} source/fixture/build/input files. Credentials, raw traces, cached prices, video media and installed dependencies are excluded. This is not clean-install reproduction or global privacy certification.",
 link('plan','Planning inventory')+' remains 83 requirements/422 mandatory cases/120 baseline combinations. '+link('boundary','The separate final-release gate')+' has 0/422 formally certified cases because the frozen release subject, complete mappings and acceptance receipts are unfinished; that is not a count of implemented features or passing software tests. Larger result loading/older job-result browsing, balanced spread, 10,000 matched trade twins, era/instrument replication/stability/family ensembles, remaining detector/dial/lifecycle work, actual numerical scale, mobile/keyboard/accessibility/security/privacy/clean reproduction and final conformance remain mandatory.',
 'Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). Ten families/visible dials use declared US-stock/ETF adaptations. Exact private engine/grid/six complete named recipes remain unknown. Automated 30,920-frame analysis, 1,031 visual samples, 37 focused 4K captures and 15 prompt pages were not manual inspection of every frame. Futures, forex and crypto remain later options.',
 'See [retained defects]('+('defects.json' if index else 'verification/defects.json')+'). The 0.21 checkpoint below is historical after the 0.22 rulebook/source change.',
 ])+'\n\n'
for name,index in [('STATUS.md',False),('verification/evidence-index.md',True)]:
 p=root/name;s=p.read_text(encoding='utf-8');start=s.index('## Historical0.21');p.write_text(prefix(index)+s[start:],encoding='utf-8')
links=[]
for name in ['STATUS.md','verification/evidence-index.md']:
 p=root/name;text=p.read_text(encoding='utf-8')
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http:','https:','#')):continue
  q=(p.parent/target.split('#')[0]).resolve();q.relative_to(root);assert q.exists(),(name,target);links.append(dict(document=name,target=target))
 (out/Path(name).name).write_bytes(p.read_bytes())
(out/'defects.json').write_bytes(ledger_path.read_bytes())
value=dict(scope=__doc__,full_regression_tests=tests,coverage_modules=20,receipt_links_checked=len(links),retained_defects=len(ledger['defects']),core_hash=health['core_hash'],final_acceptance_certified=False,receipts={k:p.relative_to(root).as_posix() for k,(p,_) in receipts.items()},links=links)
(out/'final-documentation-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['receipts','links']},indent=2))
