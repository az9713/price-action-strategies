"""Recoverable pre-final0.25 source overlay; pending verification is not certified."""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def check(p):
 r=read(p);assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];assert q.resolve().is_relative_to(root.resolve()) and q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return r
base_id='20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint'
base_path=root/'verification/receipts'/(base_id+'.json');base=check(base_path);assert base['command']['exit_code']==0
a=next(a for a in base['artifacts'] if a['path'].endswith('/source-checkpoint-manifest.json'));known={v['path']:v['sha256'] for v in read(root/a['path'])}
before={p.relative_to(dev).as_posix():sha(p) for p in source_paths(dev)}
modules=['api','job_index','models','service','spread','spread_accounts','spread_jobs','spread_preparation','spread_worker','store','trials','worker']
allowed={'PLAN.md','VERIFICATION_PLAN.md','RULEBOOK.md','strategy.schema.json','verification/implementation-map.json','verification/check_numerical_coverage.py','tests/test_catalog_generation.py','frontend/src/App.tsx','frontend/src/SpreadFlow.tsx',*['backend/lab/'+n+'.py' for n in modules],*[p.relative_to(dev).as_posix() for p in (dev/'tests').glob('test_spread*.py')]}
delta={n:d for n,d in before.items() if known.get(n)!=d};assert set(delta)<=allowed,set(delta)-allowed
copied=[]
def copy(p,name):
 assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in Path(name).parts)
 target=out/'source-overlay'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target);assert sha(target)==sha(p)
 copied.append(dict(path=name,sha256=sha(target),bytes=target.stat().st_size))
for name in sorted(delta):copy(dev/name,name)
for path in sorted((dev/'frontend/dist').rglob('*')):
 if path.is_file():copy(path,path.relative_to(dev).as_posix())
for name in ['spread-selection-contract.json','spread-worker-contract.json','spread-account-handoff-contract.json','spread-ui-integration-contract.json','common-sampling-contract.json']:copy(root/'verification/fixtures'/name,'verification/fixtures/'+name)
helpers=['check-dev025.py','run-dev025-spread-browser.py','spread_browser_originals.py','verification_awake.py','hold-current-verification-awake.py','check-verification-standby-gap.ps1','spread-browser.config.ts','audit-spread-ui-accounts.py','check-dev025-twenty-seven-module-gates.py','combine-spread-durable-coverage.py','spread-selection-link-mutations.py','spread-ui-source-checkpoint.py']
helpers+=['spread-browser-tests/'+p.name for p in (root/'verification/runs/spread-browser-tests').glob('*.ts')]
for name in helpers:copy(root/'verification/runs'/name,'verification/runs/'+name)
for name in ['spread-next-integration-notes.md','spread-ui-next-plan.md','source-page12-next-research-gap.md']:copy(root/'verification/runs'/name,'verification/runs/'+name)
copy(root/'STATUS.md','STATUS.md')
receipts=[];artifacts=0
for name in sys.argv[1:]:
 p=root/name;r=check(p);artifacts+=len(r['artifacts']);receipts.append(dict(path=name,sha256=sha(p),exit_code=r['command']['exit_code'],scope='Retained component/history evidence; matching current source is not inferred'))
after={p.relative_to(dev).as_posix():sha(p) for p in source_paths(dev)};assert before==after
catalog=read(dev/'verification/catalog.json');assert len(catalog['requirements'])==83 and len(catalog['cases'])==422 and sum(c['id'].startswith('MATRIX-') for c in catalog['cases'])==120
value=dict(scope=__doc__,base_receipt=base_path.relative_to(root).as_posix(),base_receipt_sha256=sha(base_path),base_archive=next(a for a in base['artifacts'] if a['path'].endswith('/source-checkpoint.zip')),
 source_files=before,overlay=copied,retained_receipts=receipts,receipt_artifacts_checked=artifacts,main_source_replaced=False,
 full_current_backend_regression_finished=False,current_twenty_seven_module_gates_passed=False,current_post_contract_browser_passed=False,new_guard_mutations_executed=False,independent_current_account_audit_executed=False,final_acceptance_certified=False,
 recovery='Verify the base archive and overlay hashes; unpack into a NEW owned directory with path validation, replace only frontend/dist from the compiled overlay, then apply other source files. Reinstall locked dependencies separately. Do not overwrite user credentials/data. This is a work-in-progress source checkpoint, not a final release.',
 exclusions='Explicit source/tests/contracts/compiled assets/helpers only. No credentials, real cached prices, databases, raw private traces/coverage databases, downloaded video or installed dependencies.')
(out/'spread-ui-source-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(scope=__doc__,overlay_files=len(copied),source_files=len(before),receipt_artifacts_checked=artifacts,final_acceptance_certified=False)))
