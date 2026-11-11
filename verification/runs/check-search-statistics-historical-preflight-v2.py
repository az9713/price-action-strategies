"""Use the existing audit endpoint; preserve the first unsupported-route failure."""
from pathlib import Path
source=Path('verification/runs/check-search-statistics-historical-preflight.py').read_text(encoding='utf-8')
before="get('/api/datasets/'+fixture['dataset_id'])"
after="get('/api/datasets/'+fixture['dataset_id']+'/audit')"
assert source.count(before)==1
exec(compile(source.replace(before,after),'search-statistics-historical-preflight-v2-resolved.py','exec'))
