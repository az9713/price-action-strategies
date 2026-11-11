"""Explicit source overlay and retained durable-spread evidence; no final-release promotion."""
from pathlib import Path
import hashlib,json,os,shutil,sys,xml.etree.ElementTree as ET
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(identifier):
 p=root/'verification/receipts'/(identifier+'.json');r=json.loads(p.read_text(encoding='utf-8'))
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];q.resolve().relative_to(root);assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return p,r
def latest(label):return sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1].stem
labels=['spread-durable-backend-current-full-isolated-regression-and-four-module-coverage',
 'spread-durable-original-artifacts-independent-protocol-signal-and-registry-audit',
 'spread-worker-actual-owned-interpreter-death-at-three-durable-boundaries',
 'spread-expanded-current-focused-corruption-recovery-and-four-module-coverage',
 'spread-worker-final-21-current-cancel-contract-manifest-and-artifact-faults',
 'spread-durable-corrected-manifest-boundary-eight-isolated-guard-mutations',
 'spread-durable-current-successful-254-and-21-source-checked-coverage-union',
 'spread-durable-current-four-module-unrounded-95-90-passing-gate']
selected=[];subjects=[];case_counts={}
for label in labels:
 p,r=load(latest(label));assert r['command']['exit_code']==0
 for i in r['subject']['input_manifests']:
  if i['path'].startswith('data/dev025/src/backend/'):assert sha(root/i['path'])==i['sha256']
 selected.append(dict(receipt=p.relative_to(root).as_posix(),sha256=sha(p),artifacts=len(r['artifacts'])))
 matches=[a for a in r['artifacts'] if a['path'].endswith('/dev025-junit.xml')]
 if matches:
  suites=list(ET.parse(root/matches[0]['path']).iter('testsuite'));assert all(int(s.attrib.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
  case_counts[label]=sum(int(s.attrib['tests']) for s in suites)
 for a in r['artifacts']:
  if a['path'].endswith('/dev025-source-subject.json'):
   subject=json.loads((root/a['path']).read_text(encoding='utf-8'));assert subject['changed_during_check']==[];subjects.append(subject['source_files'])
assert case_counts[labels[0]]==2036
current=subjects[-1]
for name,digest in current.items():assert sha(dev/name)==digest
for subject in subjects:
 for name,digest in subject.items():
  if name.startswith('backend/'):assert current[name]==digest
base_id='20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint'
_,base=load(base_id);a=next(a for a in base['artifacts'] if a['path'].endswith('/source-checkpoint-manifest.json'));known={v['path']:v['sha256'] for v in json.loads((root/a['path']).read_text(encoding='utf-8'))}
allowed={'PLAN.md','VERIFICATION_PLAN.md','backend/lab/spread.py','backend/lab/spread_preparation.py','backend/lab/spread_jobs.py','backend/lab/spread_worker.py','backend/lab/service.py','backend/lab/models.py','backend/lab/store.py','backend/lab/trials.py','backend/lab/worker.py','backend/lab/api.py','backend/lab/job_index.py',
 *['tests/'+n for n in ['test_spread.py','test_spread_probe.py','test_spread_scope.py','test_spread_faults.py','test_spread_preparation.py','test_spread_journal.py','test_spread_worker.py','test_spread_api.py','test_spread_streaming.py','test_spread_process_recovery.py','test_spread_integrity_faults.py','test_spread_preparation_faults.py','test_spread_worker_faults.py','test_spread_account_handoff.py']]}
differences={name:digest for name,digest in current.items() if known.get(name)!=digest};assert set(differences)<=allowed,set(differences)-allowed
overlay=[]
for name in sorted(differences):
 p=dev/name;q=out/'source-overlay'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);overlay.append(dict(path=name,sha256=sha(q),bytes=q.stat().st_size))
for name in ['spread-selection-contract.json','spread-worker-contract.json','common-sampling-contract.json','spread-account-handoff-contract.json']:
 p=root/'verification/fixtures'/name;q=out/'source-overlay/verification/fixtures'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);overlay.append(dict(path=q.relative_to(out/'source-overlay').as_posix(),sha256=sha(q),bytes=q.stat().st_size))
failures=[]
failed_labels=['spread-preparation-authored-real-batch-crash-recovery-byte-integrity-and-no-redraw-contract','spread-preparation-authored-current-batch-bytes-before-final-seal',
 'spread-journal-authored-owned-chain-tail-corruption-staged-registry-and-attempt-contract','spread-journal-authored-no-invented-attempts-owner-or-self-rehashed-parent-provenance',
 'spread-worker-authored-actual-qualification-cancel-attempt-reuse-and-corruption-contract','spread-worker-authored-late-evidence-publication-and-single-master-seed',
 'spread-api-authored-data-free-preview-bounded-status-event-pages-and-actual-worker-result','spread-api-preview-authored-corrected-header-harness-before-route-implementation',
 'spread-streaming-authored-lazy-invalid-prefix-and-large-nonfinancial-journal-heap-contract','spread-durable-four-module-first-unrounded-95-90-gate',
 'spread-durable-four-module-corrected-schema-unrounded-95-90-gate','spread-worker-expanded-new-signal-validation-orphans-root-recovery-news-and-source-faults',
 'spread-expanded-current-four-module-unrounded-gate','spread-expanded-current-final-257-focused-fault-cases-and-four-module-coverage',
 'spread-durable-current-eight-isolated-original-guard-mutations','spread-account-continuation-authored-complete-parent-frozen-assumptions-corruption-primary-and-concurrency-contract',
 'spread-account-continuation-owned-development-first-unimplemented-contract']
for label in failed_labels:
 p,r=load(latest(label));assert r['command']['exit_code']!=0;failures.append(dict(receipt=p.relative_to(root).as_posix(),sha256=sha(p),artifacts=len(r['artifacts'])))
value=dict(scope=__doc__,base_receipt='verification/receipts/'+base_id+'.json',selected_receipts=selected,case_counts=case_counts,counts_overlap=True,
 source_overlay=overlay,development_source_files=current,historical_failures_retained=failures,
 main_app_source_replaced=False,selected_account_pnl_implemented=False,ui_integrated=False,source_scale_executed=False,final_acceptance_certified=False,
 exclusions='Explicit named synthetic development source and contracts only. No credentials, cached market prices, databases, raw traces, coverage DBs or installed dependencies copied.')
(out/'spread-durable-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k not in ['development_source_files','source_overlay','historical_failures_retained','selected_receipts']},indent=2))
