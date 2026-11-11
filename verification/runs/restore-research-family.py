"""Restore explicit authored source and a verified synthetic store; never user data or credentials."""
from pathlib import Path
from contextlib import closing
import hashlib,json,os,shutil,sqlite3,subprocess,sys,zipfile
root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
receipt_id='20261110T044754002079Z-research-family-actual-isolated-desktop-mobile-ui-complete-downloads-reload-and-response-ownership'
receipt=json.loads((root/'verification/receipts'/(receipt_id+'.json')).read_text());assert receipt['command']['exit_code']==0
item=next(a for a in receipt['artifacts'] if a['path'].endswith('/family-browser-subject.json'))
assert sha(root/item['path'])==item['sha256']
subject=json.loads((root/item['path']).read_text());assert subject['source_unchanged'] and subject['owned_http_and_worker_retired']
original=(root/subject['store']).resolve();assert original.is_relative_to((root/'data/dev027/family-browser').resolve())
for path in (original/'data/datasets').glob('*/manifest.json'):
 assert json.loads(path.read_text())['metadata']['input_kind']=='synthetic'
home=root/'data/dev027/family-restoration'/out.name.split('-')[0];source=home/'source';store=home/'store'
home.mkdir(parents=True,exist_ok=False);archive=out/'authored-source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as saved:
 for relative in before:
  assert not any(part.startswith('.env') for part in Path(relative).parts)
  saved.write(stage/relative,relative)
with zipfile.ZipFile(archive) as saved:
 assert saved.testzip() is None and set(saved.namelist())==set(before)
 for name in saved.namelist():assert not Path(name).is_absolute() and '..' not in Path(name).parts
 saved.extractall(source)
assert all(sha(source/name)==digest for name,digest in before.items())
shutil.copytree(original/'data',store/'data',ignore=shutil.ignore_patterns('lab.sqlite3','lab.sqlite3-wal','lab.sqlite3-shm'))
with closing(sqlite3.connect((original/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as old,closing(sqlite3.connect(store/'data/lab.sqlite3')) as new:old.backup(new)
with closing(sqlite3.connect(store/'data/lab.sqlite3')) as db:
 children=db.execute("SELECT id,payload FROM jobs WHERE kind='family_analysis'").fetchall()
 jid=next(jid for jid,payload in children if json.loads(payload)['family_parent']['original_job_id']==subject['original_parent'])
 payload=json.loads(next(payload for child,payload in children if child==jid));expected_core=payload['core_hash']
removed=[]
for path in (store/'data/jobs').glob('*/*.view.sqlite3'):
 assert path.resolve().is_relative_to(store.resolve());removed.append(path.relative_to(store).as_posix());path.unlink()
assert removed
env=os.environ.copy();env.update(PYTHONPATH=str(source)+os.pathsep+str(source/'tests'),PYTHONNOUSERSITE='1')
result=subprocess.run([sys.executable,str(root/'verification/runs/restore-research-family-child.py'),str(source),str(store),jid,subject['original_parent'],expected_core,str(out/'fresh-restoration-checks.json')],cwd=source,env=env,capture_output=True,text=True,timeout=120)
print(result.stdout);print(result.stderr,file=sys.stderr)
assert result.returncode==0
assert before=={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
(out/'family-restoration-subject.json').write_text(json.dumps(dict(scope=__doc__,source_files=before,current_source_unchanged=True,archive_sha256=sha(archive),authored_files=len(before),synthetic_store_origin_receipt=receipt_id,derived_files_removed_in_restored_copy=removed,child_exit_code=result.returncode,dependency_environment_reused=True,fresh_machine_install_tested=False,credentials_or_actual_user_store_copied=False,global_gate=False,final_product_acceptance=False),indent=2),encoding='utf-8')
