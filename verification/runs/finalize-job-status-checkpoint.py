"""Finalize status from completed receipts, then snapshot every local receipt link and retained defect."""
from pathlib import Path
import hashlib,json,os,re,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];v=json.loads(p.read_text(encoding='utf-8'));assert v['command']['exit_code']==0
 assert not any(n.startswith(('Source changed','Missing requested')) for n in v['notes']);return p,v
labels=dict(full='bounded-job-monitoring-current-full-regression-and-nineteen-module-coverage',gate='bounded-job-monitoring-current-nineteen-module-coverage-gate',build='bounded-job-monitoring-current-typed-production-build',browser='bounded-job-monitoring-current-two-desktop-controls-and-result-ownership',capacity='bounded-job-monitoring-current-10-100-1000-100000-metadata-capacity',mutants='bounded-job-monitoring-current-seven-isolated-critical-mutations',audit='bounded-job-monitoring-current-independent-browser-inputs-and-complete-trials',runtime='bounded-job-monitoring-current-managed-owner-assets-and-duplicate-refusal',plan='bounded-job-monitoring-current-83-422-120-plan-inventory',checkpoint='bounded-job-monitoring-current-nine-receipt-source-fixture-build-recovery-checkpoint')
labels['boundary']='bounded-job-monitoring-honest-current-final-release-boundary'
receipts={k:latest(v) for k,v in labels.items()}
def artifact(key,suffix):
 values=[a for a in receipts[key][1]['artifacts'] if a['path'].endswith(suffix)];assert len(values)==1,(key,suffix)
 p=root/values[0]['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==values[0]['sha256'];return p
checkpoint=json.loads(artifact('checkpoint','/checkpoint.json').read_text(encoding='utf-8'))
gate=json.loads(artifact('gate','/numerical-coverage-gate.json').read_text(encoding='utf-8'));assert gate['ready'] and len(gate['modules'])==19
suites=list(ET.parse(artifact('full','junit.xml')).iter('testsuite'));tests=sum(int(s.attrib.get('tests',0)) for s in suites)
assert tests==checkpoint['full_current_regression_tests'] and tests>=1600
assert all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
capacity=json.loads(artifact('capacity','/indexed-status-capacity.json').read_text(encoding='utf-8'));assert capacity['complete']
assert [r['configurations'] for r in capacity['rows']]==[10,100,1000,100000]
assert all(r['status_bytes']<=65536 and r['sql_raw_payload_reads']==0 and r['input_export_bytes']>r['status_bytes'] and r['executed_accounts']==0 for r in capacity['rows'])
mutants=json.loads(artifact('mutants','/job-status-mutation-results.json').read_text(encoding='utf-8'));assert len(mutants['mutations'])==7 and mutants['original_source_unchanged']
assert all(m['result']['assertion_failures']>0 and m['result']['errors']==m['result']['skipped']==0 for m in mutants['mutations'])
audit=json.loads(artifact('audit','/independent-job-status-browser-evidence.json').read_text(encoding='utf-8'));assert len(audit['rows'])==2 and all(r['configurations']==1000 for r in audit['rows'])
runtime=json.loads(artifact('runtime','/managed-runtime.json').read_text(encoding='utf-8'));health=runtime['health'];assert health['core_hash']==audit['core_hash'] and health['source_current'] and health['store_lease_held']
boundary=json.loads(artifact('boundary','/release-boundary.json').read_text(encoding='utf-8'));assert boundary['ready'] is False and boundary['mandatory_cases']==422 and boundary['final_verified_cases']==0
ledger_path=root/'verification/defects.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
for defect in ledger['defects']:
 if defect['id']=='D-JOB-STATUS-BORROW-ARMS-001':
  defect.update(status='corrected_full_current_regression_and_nineteen_module_gates_passed',regression_receipt=receipts['full'][0].relative_to(root).as_posix())
 if defect['id']=='D-JOB-STATUS-RAW-MATERIALIZATION-001':
  defect.update(status='corrected_component_checkpoint_full_current_checks_passed_final_release_pending',current_regression_receipt=receipts['full'][0].relative_to(root).as_posix())
ledger_path.write_text(json.dumps(ledger,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def prefix(index=False):
 def link(key,label):return '['+label+']('+('' if index else 'verification/')+'receipts/'+receipts[key][0].name+')'
 largest=capacity['rows'][-1]
 return '\n\n'.join([
 '## Current0.21 - bounded job-monitoring component checkpoint',
 f"The managed app answers at http://127.0.0.1:8767. Core `{health['core_hash']}`, frontend `index-BEGO6Bgp.js`, managed session{runtime['managed_session']}, HTTP{health['server_pid']}/worker{health['worker_pid']}. The goal remains active and **not ready for final release**. This is a scoped component checkpoint, not final422-case acceptance.",
 'D041 retains full immutable plans and transactionally indexes bounded status/history metadata. Poll/list/cancel/resume/registry lookups avoid raw plan JSON; original lifecycle/trial states remain authoritative. Explicit input downloads and derived-cache repair verify the original frozen hash. Bad cache is visible. Malformed original inputs cannot be exported or repaired as verified; malformed queued claims fail without killing the worker loop. Old-schema reconstruction remains outside this startup certificate. Small borrowing-cost arms/rate policy remain in compatible responses; oversized contexts/documents are explicitly abbreviated with full inputs on demand.',
 link('full',f'{tests} full current regression checks')+' pass with zero failures/errors/skips. '+link('gate','All19 module coverage gates')+' meet the unchanged95% statement/90% branch requirements. Coverage is not a proof of every use case or financial accuracy. The first full1657-pass/one-failure run is retained with its original coverage/JUnit/logs; it found the omitted four-cost-arm compatibility case.',
 link('browser','Four actual desktop browser checks')+' pass at1920x1080 and1280x720 for complete input download, cancel/resume, visible test-owned cache corruption/repair and stale/current result ownership. '+link('audit','Independent saved-input and complete-trial reconciliation')+' verifies both1000-configuration payload fingerprints, all accepted proposals and all trial-export rows. Browser-normalized JSON is checked semantically; canonical original input bytes are downloaded and hashed separately. Screenshots and original failed audit remain.',
 link('capacity','Prespecified10/100/1000/100000 metadata and full HTTP input measurements')+f" pass. The100000-config status is{largest['status_bytes']}bytes, traced Python peak{largest['status_python_peak_bytes']}bytes, with zero raw-payload SQL reads while monitoring/controlling. Its actual full input export is{largest['input_export_bytes']}bytes. All original input hashes/planned counts are retained. **Zero numerical accounts ran in this measurement**; numerical10000/100000 throughput and full-history runtimes remain unverified.",
 link('mutants','Seven isolated critical mutations')+' are killed by assertion failures, with7 baseline checks passing and no collection errors/skips or original-source edits. '+link('build','Typed production build')+' passes; the large-bundle warning remains. '+link('runtime','Managed owner, actual assets and competing-store refusal')+' pass. Prior managed servers exited via Ctrl+C; no manual taskkill is needed. Native OS-wide process inventory remains uncertified.',
 link('checkpoint','Coherent recovery checkpoint')+f" verifies9 identical-source passing receipts/{checkpoint['artifact_files_checked']} artifacts, retains{len(checkpoint['historical_failures_retained'])} original failures and archives{checkpoint['source_archive_files']} source/fixture/build/input files. Credentials, raw traces, cached prices, video media and installed dependencies are excluded. This is not clean-install reproduction or global privacy certification.",
 link('plan','Planning inventory')+' remains83 requirements/422 mandatory cases/120 baseline combinations. '+link('boundary','The separate final release gate')+' currently certifies0/422 final acceptance cases: the frozen release subject, complete mappings and acceptance receipts remain unfinished. This is not a count of implemented features or passing software tests. Large study-list/result reads and old-schema trial reconstruction remain scaling gaps. Source-style balanced spread,10000 matched trade twins, era/instrument replication/stability/family ensembles, remaining detector/dial/lifecycle work, actual numerical operating limits, mobile/keyboard/accessibility/security/privacy/clean reproduction and coherent final conformance remain mandatory.',
 'Source: [AI Pathways/Brendan YouTube video](https://www.youtube.com/watch?v=z97PnFIPoFg). Ten setup families and visible dials have declared US-stock/ETF adaptations. Exact private engine/grid/six named recipes remain unknown. Automated30920-frame analysis,1031 visual samples,37 focused4K captures and15 prompt pages were not manual review of every frame. Futures, forex and crypto remain later options.',
 'See [retained defects]('+('defects.json' if index else 'verification/defects.json')+'). No strategy formula, profit selection threshold, cash tolerance, universe limit or protected-final policy was changed by D041.',
 ])+'\n\n'
for name,index in [('STATUS.md',False),('verification/evidence-index.md',True)]:
 p=root/name;s=p.read_text(encoding='utf-8');start=s.index('## Historical0.20');p.write_text(prefix(index)+s[start:],encoding='utf-8')
links=[]
for name in ['STATUS.md','verification/evidence-index.md']:
 p=root/name;text=p.read_text(encoding='utf-8')
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http:','https:','#')):continue
  q=(p.parent/target.split('#')[0]).resolve();q.relative_to(root);assert q.exists(),(name,target);links.append(dict(document=name,target=target))
 (out/Path(name).name).write_bytes(p.read_bytes())
(out/'defects.json').write_bytes(ledger_path.read_bytes())
value=dict(scope=__doc__,tests=tests,modules=19,receipt_links_checked=len(links),retained_defects=len(ledger['defects']),core_hash=health['core_hash'],final_acceptance_certified=False,receipts={k:p.relative_to(root).as_posix() for k,(p,_) in receipts.items()},links=links)
(out/'final-documentation-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['links','receipts']},indent=2))
