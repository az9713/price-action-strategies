"""Reviewable source-only promotion after immutable checks; never copies user data."""
from pathlib import Path
import hashlib,json,os,shutil,socket,sqlite3,sys,uuid
root=Path.cwd();dev=root/'data/dev025/src';sys.path.insert(0,str(root))
from verification.record_check import source_paths
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sources(folder):return {p.relative_to(folder).as_posix():sha(p) for p in source_paths(folder)}
def assets(folder):return {p.relative_to(folder).as_posix():sha(p) for p in (folder/'frontend/dist').rglob('*') if p.is_file()}
def load_receipt(name):
 p=root/name;r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return r
def artifact(r,name):return read(root/next(a['path'] for a in r['artifacts'] if a['path'].endswith('/'+name)))
def database():
 result={}
 with sqlite3.connect((root/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
  for table in ['jobs','events','trial_plans','trial_attempts','strategies','studies','viewed_windows']:
   digest=hashlib.sha256();count=0
   for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):
    values=[dict(blob_sha256=hashlib.sha256(v).hexdigest(),bytes=len(v)) if isinstance(v,bytes) else v for v in row]
    digest.update(json.dumps(values,separators=(',',':'),allow_nan=False).encode());digest.update(b'\n');count+=1
   result[table]=dict(rows=count,sha256=digest.hexdigest())
 return result
mode=sys.argv[1]
if mode=='prepare':
 run=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
 labels={
 'regression':'20261109T160028110170Z-spread-version025-current-full-backend-regression-and-twenty-seven-module-coverage',
 'browser':'20261109T170722106562Z-spread-version025-current-eighteen-browser-workflows-raw-json-original-accounts-and-wake-lease',
 'gates':'20261109T171444475008Z-spread-version025-current-source-checked-twenty-seven-module-unrounded-95-90-gate',
 'audit':'20261109T171240388145Z-spread-version025-browser-original-wrapper-aware-full-account-csv-and-presentation-fact-audit',
 'mutations':'20261109T165954715220Z-spread-version025-six-byte-preserved-selected-envelope-repair-and-reverse-reservation-mutations',
 'runtime':'20261109T171505614128Z-spread-version025-before-integration-current-managed-tree-idle-main-store-and-retired-test-workers',
 'reconstruction':'20261109T165822753690Z-spread-version025-actual-source-overlay-reconstruction-core-assets-and-schema-gate-smoke'}
 receipts={k:load_receipt('verification/receipts/'+v+'.json') for k,v in labels.items()}
 current=sources(dev);subject=artifact(receipts['regression'],'dev025-source-subject.json');assert subject['source_files']==current and subject['changed_during_check']==[]
 gates=artifact(receipts['gates'],'dev025-twenty-seven-module-gates.json');assert gates['ready'] and len(gates['modules'])==27 and all(r['required_statements']==95 and r['required_branches']==90 for r in gates['modules'])
 browser=artifact(receipts['browser'],'spread-browser-subject.json');assert browser['owned_http_and_worker_retired'] and browser['changed_during_check']==[] and all(current.get(n)==d for n,d in browser['source_files'].items() if not n.startswith('frontend/dist/'))
 audit=artifact(receipts['audit'],'spread-ui-independent-account-export-facts.json');assert len(audit['accounts'])==3 and all(a['loss_retained'] and a['trades']==110 for a in audit['accounts'])
 mutations=artifact(receipts['mutations'],'spread-selection-link-mutations.json');assert mutations['all_assertion_killed'] and len(mutations['mutants'])==6
 native=artifact(receipts['runtime'],'current-process-tree.json');assert not native['separate_obsolete_project_python_detected'] and native['duplicate_store_start_rejected']
 reconstructed=artifact(receipts['reconstruction'],'source-reconstruction.json');assert reconstructed['child_exit_code']==0 and reconstructed['source_files_verified']==len(current)
 before=sources(root);assert not set(before)-set(current)
 base=read(root/'verification/runs/20261109T100124899109Z-evaluation-cache-current-fifteen-receipt-source-fixture-build-and-capacity-recovery-checkpoint/source-checkpoint-manifest.json');known={v['path']:v['sha256'] for v in base}
 for name,digest in before.items():assert digest==(current[name] if name in {'PLAN.md','VERIFICATION_PLAN.md'} else known[name]),'Unexpected main-source change: '+name
 changes={n:d for n,d in current.items() if before.get(n)!=d}
 plan=dict(scope=__doc__,dev_source=current,main_before=before,changes=changes,assets_before=assets(root),assets_after=assets(dev),original_database=database(),expected_core=reconstructed['core_subjects'][0]['core_hash'],original_tree=native['project_python_tree'],prerequisites={k:dict(receipt='verification/receipts/'+labels[k]+'.json',sha256=sha(root/'verification/receipts'/(labels[k]+'.json'))) for k in labels},credentials_accessed=False,user_data_copied=False)
 (run/'integration-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');print(json.dumps(dict(source_files=len(current),changed_source_files=len(changes),expected_core=plan['expected_core'],original_jobs=plan['original_database']['jobs']['rows'],pending_jobs=0,user_data_copied=False)))
elif mode=='apply':
 receipt=load_receipt(sys.argv[2]);plan=artifact(receipt,'integration-plan.json')
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',8767))!=0,'Stop the managed idle server before replacing source'
 assert sources(root)==plan['main_before'] and sources(dev)==plan['dev_source'] and assets(root)==plan['assets_before'] and assets(dev)==plan['assets_after']
 assert database()==plan['original_database'],'Original store changed after the reviewed preparation'
 backup=root/'data/private-evidence/integration-sources'/uuid.uuid4().hex;backup.mkdir(parents=True,exist_ok=False)
 def safe(folder,name):
  p=folder/name;assert p.resolve().is_relative_to(folder.resolve()) and not p.is_symlink() and not any(v.lower().startswith('.env') for v in Path(name).parts);return p
 for name in [*plan['changes'],*plan['assets_before']]:
  old=safe(root,name)
  if old.exists():q=safe(backup,name);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,q)
 for name,digest in plan['changes'].items():
  p=safe(dev,name);assert sha(p)==digest;q=safe(root,name);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 dist=root/'frontend/dist';assert dist.resolve()==root.resolve()/'frontend/dist' and not dist.is_symlink();shutil.rmtree(dist)
 for name,digest in plan['assets_after'].items():
  p=safe(dev,name);assert sha(p)==digest;q=safe(root,name);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 assert sources(root)==plan['dev_source'] and assets(root)==plan['assets_after'] and database()==plan['original_database']
 value=dict(plan_receipt=sys.argv[2],plan=plan,source_backup=backup.relative_to(root).as_posix(),main_after=sources(root),assets_after=assets(root),original_database_after=database(),user_data_copied=False,credentials_accessed=False,service_must_restart=True)
 output=root/'verification/runs'/('applied-dev025-'+uuid.uuid4().hex+'.json');output.write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(applied_manifest=output.relative_to(root).as_posix(),source_files=len(value['main_after']),original_jobs=plan['original_database']['jobs']['rows'],database_values_unchanged=True,service_must_restart=True)))
elif mode=='verify':
 applied=read(root/sys.argv[2]);plan=applied['plan'];load_receipt(applied['plan_receipt'])
 assert sources(root)==plan['dev_source'] and assets(root)==plan['assets_after'] and database()==plan['original_database']
 import urllib.request
 with urllib.request.urlopen('http://127.0.0.1:8767/api/health',timeout=15) as response:health=json.load(response)
 assert health['core_hash']==plan['expected_core'] and all(health[k] for k in ['source_current','worker_ready','worker_alive','store_lease_held'])
 value=dict(scope=__doc__,applied_manifest=sys.argv[2],source_files_verified=len(plan['dev_source']),assets=plan['assets_after'],original_database_values_preserved=True,original_database=plan['original_database'],health=health,source_backup=applied['source_backup'],user_data_copied=False,credentials_accessed=False,final_acceptance_certified=False)
 (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'integrated-source-store-parity.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='original_database'},indent=2))
else:raise ValueError('Choose prepare, apply or verify')
