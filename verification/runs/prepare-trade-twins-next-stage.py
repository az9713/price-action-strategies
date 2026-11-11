"""Copy source-only baseline for next D046 integration while original check stays frozen.

This is an uninstalled development branch, not a verified release or database
backup. Baseline global verification continues on the unchanged original tree.
"""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();source=root/'data/dev026/src';target=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
expected=json.loads((root/'verification/runs/20261109T200841194002Z-trade-twins-financial-complete-books-corrected-opening-mark-hand-total-and-exact-30-module-gate-declaration/dev026-source-subject.json').read_text())
assert before==expected['source_files'] and not expected['changed_during_check'] and len(before)==220
assert not target.exists();target.mkdir(parents=True)
base=json.loads((root/'verification/runs/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint/integrated025-source-manifest.json').read_text())
files={item['path'] for item in base}|set(before)|{'verification/fixtures/trade-twins-contract.json','verification/fixtures/trade-twin-financial-contract.json'}
manifest=[]
for name in sorted(files):
 p=source/name;relative=Path(name);dest=(target/relative).resolve()
 assert p.is_file() and not p.is_symlink() and dest.is_relative_to(target.resolve())
 assert not any(part.lower().startswith('.env') for part in relative.parts) and not name.startswith(('data/','frontend/node_modules/'))
 assert p.suffix.lower() not in {'.db','.sqlite3','.parquet','.gz','.mp4','.webm','.png','.jpg','.zip'}
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 assert sha(dest)==sha(p);manifest.append(dict(path=name,bytes=p.stat().st_size,sha256=sha(p)))
assert before=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert before=={p.relative_to(target).as_posix():sha(p) for p in source_paths(target)}
value=dict(scope=__doc__,source=source.relative_to(root).as_posix(),target=target.relative_to(root).as_posix(),files=manifest,source_files=before,original_frozen_source_unchanged=True,credentials_prices_databases_dependencies_copied=False,main_app_source_replaced=False,baseline_global_verification_still_required=True,final_acceptance_certified=False)
(out/'next-stage-source-baseline.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k not in {'files','source_files'}},indent=2))
