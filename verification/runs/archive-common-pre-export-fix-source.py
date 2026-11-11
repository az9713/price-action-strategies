"""Preserve the first D039 browser subject before correcting its retained export-assumption defect."""
from pathlib import Path
import hashlib,json,os,sys,zipfile
root=Path.cwd();sys.path.insert(0,str(root));from verification.record_check import source_paths
receipt_path=root/'verification/receipts/20261108T222704829941Z-common-sampling-current-main-complete-grid-and-random-two-desktops-first-execution.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
for name,digest in receipt['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
paths=set(source_paths())|set((root/'verification/fixtures').rglob('*'))|set((root/'frontend/dist').rglob('*'))
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);manifest=[]
with zipfile.ZipFile(out/'pre-export-fix-source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
 for path in sorted(p for p in paths if p.is_file()):
  name=path.relative_to(root).as_posix();assert not any(p.startswith('.env') for p in path.parts) and not path.is_relative_to(root/'data') and '/node_modules/' not in name and '/runs/' not in name
  raw=path.read_bytes();archive.writestr(name,raw);manifest.append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
with zipfile.ZipFile(out/'pre-export-fix-source.zip') as archive:assert archive.testzip() is None
(out/'source-manifest.json').write_text(json.dumps(dict(scope=__doc__,browser_receipt=receipt_path.relative_to(root).as_posix(),files=manifest,known_failure='verification/receipts/20261108T223347459386Z-common-sampling-actual-saved-json-csv-offline-assumption-completeness-first-audit.json'),indent=2),encoding='utf-8')
print(json.dumps(dict(source_files=len(manifest),preserved_known_export_failure=True,final_acceptance=False)))
