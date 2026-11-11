"""Supply the four explicit authored receipt dependencies omitted from source-only test copies."""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
folders=[root/'data/dev026/evidence-src',root/'data/dev027/research-src']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={str(folder.relative_to(root)):{p.relative_to(folder).as_posix():sha(p) for p in source_paths(folder)} for folder in folders}
names=['20261108T083402678603Z-full-backend-matched-controls-coverage.json','20261108T100203771424Z-utf8-restored-full-701-backend-coverage.json','20261108T141545788080Z-presenter-fixed-current-full-regression-and-coverage.json','20261108T153959895989Z-news-strict-recovery-and-release-artifact-current-full-regression.json']
copied=[]
for folder in folders:
 for name in names:
  original=root/'verification/receipts'/name;value=json.loads(original.read_text());assert 'catalog_sha256' in value['subject']
  target=folder/'verification/receipts'/name;target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():assert sha(target)==sha(original)
  else:shutil.copy2(original,target)
  copied.append(dict(path=target.relative_to(root).as_posix(),sha256=sha(target),source=original.relative_to(root).as_posix()))
assert before=={str(folder.relative_to(root)):{p.relative_to(folder).as_posix():sha(p) for p in source_paths(folder)} for folder in folders}
(out/'catalog-reference-restoration.json').write_text(json.dumps(dict(scope=__doc__,copied=copied,all_authored_sources_unchanged=True,market_data_or_credentials_copied=False,does_not_change_original_failed_regression=True),indent=2),encoding='utf-8')
