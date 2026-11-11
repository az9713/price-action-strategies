"""Preserve exact original failed fixture before portable exact-root correction."""
from pathlib import Path
import hashlib,json,os
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);p=root/'data/dev026/src/tests/test_spread.py'
original=p.read_bytes();before=json.loads((root/'verification/runs/20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage/dev026-source-subject.json').read_text())
assert hashlib.sha256(original).hexdigest()==before['source_files']['tests/test_spread.py']
assert original.count(b"assert 'dev025' in str(Path(spread.__file__).resolve())")==1
(out/'original-test_spread.py').write_bytes(original)
(out/'fixture-preimage.json').write_text(json.dumps(dict(path='tests/test_spread.py',sha256=hashlib.sha256(original).hexdigest(),original_global_source_matches=True,production_code_changed=False,final_acceptance_certified=False),indent=2),encoding='utf-8')
print('Preserved original global-run fixture bytes; no production or test source changed.')
