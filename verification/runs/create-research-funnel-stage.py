"""Source-only next-milestone branch; preserve the executing full-regression subject."""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();source=root/'data/dev026/evidence-src';target=root/'data/dev027/research-src'
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root))
from verification.record_check import source_paths
paths=source_paths(source)+[p for p in (source/'verification/fixtures').rglob('*') if p.is_file() and p.suffix in {'.json','.py','.md'}]
paths=list(dict.fromkeys(paths));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p) for p in paths}
assert all(not any(part.lower().startswith('.env') for part in Path(name).parts) and not name.startswith('data/') for name in before)
target.mkdir(parents=True,exist_ok=False)
for name in before:
    destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source/name,destination)
assert before=={name:sha(target/name) for name in before}
assert before=={name:sha(source/name) for name in before}
value=dict(scope=__doc__,source=source.relative_to(root).as_posix(),destination=target.relative_to(root).as_posix(),
    source_files=before,copied_files=len(before),all_copied_bytes_match=True,executing_subject_unchanged=True,
    user_data_or_credentials_copied=False,installed_app_source_not_replaced=True,final_acceptance_certified=False)
(out/'research-stage-origin.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
(root/'verification/runs/research-stage-origin.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='source_files'},indent=2))
