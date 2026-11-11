"""Current universe-preserving managed instance; preserve prior native-inventory limitations."""
from pathlib import Path
source=Path('verification/runs/check-dataset-context-managed-runtime.py').read_text(encoding='utf-8')
assert source.count("==31792")==1 and source.count('managed_session=19735')==1
source=source.replace('==31792','==47800').replace('managed_session=19735','managed_session=18377')
exec(compile(source,'dataset-context-current-runtime-resolved.py','exec'))
