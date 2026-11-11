"""Verify the managed D041 owner, actual served assets and competing-store refusal."""
from pathlib import Path
source=Path('verification/runs/check-dataset-context-managed-runtime.py').read_text(encoding='utf-8')
assert source.count('==31792')==1 and source.count('managed_session=19735')==1
source=source.replace('==31792','==5696').replace('managed_session=19735','managed_session=38270')
source=source.replace(",stop_observation='verification/runs/dataset-context-managed-restart-observation.json'",'')
exec(compile(source,'job-status-managed-runtime-resolved.py','exec'))
