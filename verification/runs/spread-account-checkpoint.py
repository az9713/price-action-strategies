"""Recoverable isolated account-continuation component checkpoint; UI/final integration remains pending."""
from pathlib import Path
import hashlib,json,os,shutil,xml.etree.ElementTree as ET
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
labels=dict(focus='spread-account-current-48-continuation-export-authority-and-process-cases',news='spread-account-frozen-news-identity-independent-from-calendar-date-coverage-supplement',
 direct='spread-account-original-link-direct-boundary-two-fault-branch-supplement',exports='spread-account-complete-saved-json-csv-original-cohort-and-account-evidence',
 audit='spread-account-current-48-original-lineage-and-complete-independent-decimal-account-audit',csv_audit='spread-account-complete-csv-fields-original-cohort-and-second-independent-decimal-account',
 account_gate='spread-account-current-source-checked-unrounded-95-90-passing-module-gate',regression='spread-account-current-existing-257-spread-regression-and-five-module-coverage',
 mutations='spread-account-byte-preserved-preflighted-seven-assertion-killed-guard-mutations',runtime='spread-account-current-managed-tree-and-all-test-workers-retired',
 inventory='spread-account-current-unchanged-83-422-120-planning-inventory',five_gates='spread-account-current-five-module-source-checked-95-90-passing-gate')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def latest(label):return sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1]
def load(p):
 r=json.loads(p.read_text(encoding='utf-8'));assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];q.resolve().relative_to(root);assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return r
receipts={};selected=[];subjects=[];counts={};artifacts=0
for key,label in labels.items():
 p=latest(label);r=load(p);assert r['command']['exit_code']==0;receipts[key]=(p,r);artifacts+=len(r['artifacts']);selected.append(dict(receipt=p.relative_to(root).as_posix(),sha256=sha(p),artifacts=len(r['artifacts'])))
 for i in r['subject']['input_manifests']:
  if i['path'].startswith('data/dev025/src/backend/'):assert sha(root/i['path'])==i['sha256']
 for a in r['artifacts']:
  if a['path'].endswith('/dev025-source-subject.json'):
   s=json.loads((root/a['path']).read_text(encoding='utf-8'));assert not s['changed_during_check'] and s['child_exit_code']==0;subjects.append(s['source_files'])
  if a['path'].endswith('/dev025-junit.xml'):
   suites=list(ET.parse(root/a['path']).iter('testsuite'));assert all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped']);counts[key]=sum(int(s.attrib['tests']) for s in suites)
assert counts['focus']==48 and counts['news']==1 and counts['direct']==2 and counts['regression']==257
current=subjects[-1]
for name,digest in current.items():assert sha(dev/name)==digest
for s in subjects:
 for name,digest in s.items():
  if name.startswith('backend/'):assert current[name]==digest
def artifact(key,name):return json.loads((root/next(a['path'] for a in receipts[key][1]['artifacts'] if a['path'].endswith('/'+name))).read_text(encoding='utf-8'))
gate=artifact('account_gate','spread-account-coverage-gate.json');assert gate['ready'] and gate['minimum_statements']==95 and gate['minimum_branches']==90
five_gates=artifact('five_gates','spread-five-module-coverage-gates.json');assert five_gates['ready'] and len(five_gates['gates'])==5 and all(g['minimum_statements']==95 and g['minimum_branches']==90 for g in five_gates['gates'])
mutations=artifact('mutations','spread-account-mutations.json');assert mutations['all_assertion_killed'] and len(mutations['mutants'])==7 and mutations['baseline']['tests']==19
native=artifact('runtime','current-process-tree.json');assert native['duplicate_store_start_rejected'] and not native['separate_obsolete_project_python_detected']
base_id='20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint';base=load(root/'verification/receipts'/(base_id+'.json'))
a=next(a for a in base['artifacts'] if a['path'].endswith('/source-checkpoint-manifest.json'));known={v['path']:v['sha256'] for v in json.loads((root/a['path']).read_text(encoding='utf-8'))}
modules=['spread','spread_preparation','spread_jobs','spread_worker','spread_accounts','service','models','store','trials','worker','api','job_index']
tests=['test_spread','test_spread_probe','test_spread_scope','test_spread_faults','test_spread_preparation','test_spread_journal','test_spread_worker','test_spread_api','test_spread_streaming','test_spread_process_recovery','test_spread_integrity_faults','test_spread_preparation_faults','test_spread_worker_faults','test_spread_account_handoff','test_spread_account_faults','test_spread_account_process_recovery','test_spread_account_exports','test_spread_account_authority']
allowed={'PLAN.md','VERIFICATION_PLAN.md',*['backend/lab/'+n+'.py' for n in modules],*['tests/'+n+'.py' for n in tests]}
diff={n:d for n,d in current.items() if known.get(n)!=d};assert set(diff)<=allowed,set(diff)-allowed
overlay=[]
def copy(p,name):
 assert not any(part.lower().startswith('.env') for part in Path(name).parts) and not p.is_symlink()
 q=out/'source-overlay'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);overlay.append(dict(path=name,sha256=sha(q),bytes=q.stat().st_size))
for name in sorted(diff):copy(dev/name,name)
for name in ['spread-selection-contract.json','spread-worker-contract.json','spread-account-handoff-contract.json','common-sampling-contract.json']:copy(root/'verification/fixtures'/name,'verification/fixtures/'+name)
for name in ['spread-next-integration-notes.md','spread-ui-next-plan.md']:copy(root/'verification/runs'/name,'verification/runs/'+name)
failure_labels=['spread-account-continuation-owned-development-first-unimplemented-contract','spread-account-authored-api-override-atomic-link-corruption-and-committed-part-recovery-contract',
 'spread-account-first-original-lineage-and-complete-independent-decimal-account-audit','spread-account-authored-strict-seed-forty-floor-and-complete-loss-statistics-screen-csv-exports',
 'spread-account-current-seven-isolated-original-guard-mutations','spread-account-corrected-junit-schema-seven-assertion-killed-guard-mutations','spread-account-current-first-unrounded-95-90-parent-module-gate']
failures=[]
for label in failure_labels:
 p=latest(label);r=load(p);assert r['command']['exit_code']!=0;failures.append(dict(receipt=p.relative_to(root).as_posix(),sha256=sha(p),artifacts=len(r['artifacts'])))
value=dict(scope=__doc__,base_receipt='verification/receipts/'+base_id+'.json',selected_receipts=selected,artifact_files_checked=artifacts,case_counts=counts,counts_overlap=True,
 development_source_files=current,source_overlay=overlay,historical_failures_retained=failures,account_module_gate=gate,
 main_app_source_replaced=False,account_continuation_api_implemented=True,selected_rule_paging_implemented=False,saved_child_link_status_implemented=False,ui_integrated=False,full_current_global_regression=False,global_numerical_gates_current=False,source_scale_executed=False,final_acceptance_certified=False,
 exclusions='Explicit code/tests/contracts/notes only. No credentials, real cached prices, databases, raw traces/coverage DBs, video media or installed dependencies copied. Actual synthetic proof artifacts remain in their original receipts.')
(out/'spread-account-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['development_source_files','source_overlay','historical_failures_retained','selected_receipts','account_module_gate']},indent=2))
