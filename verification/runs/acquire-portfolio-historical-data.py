from pathlib import Path
import json,sys,os
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.service import Lab
from backend.lab.ingest import ingest
from backend.lab.provider import ProviderError
contract=json.loads((root/'verification/runs/portfolio-historical-study-contract.json').read_text(encoding='utf-8'))
lab=Lab(root);symbols=contract['symbols'];window=contract['acquisition']
lab.guard.access(symbols,window['start'],window['end'],'portfolio_historical_acquisition_preflight',record=False)
with lab.store.db() as db:
 prior=db.execute('SELECT 1 FROM viewed_windows WHERE symbol IN (?,?) AND start<=? AND end>=? LIMIT 1',(*symbols,window['end'],window['start'])).fetchone()
assert prior is None,'Predeclared dates are not untouched in the recorded product history.'
manifest=ingest(root,symbols,window['start'],window['end'])
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(output/'acquired-historical-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(scope='Actual free historical acquisition and metadata quality only; no price analysis or final access.',dataset_id=manifest['id'],symbols=manifest['quality']['symbols'],eligible=manifest['quality']['eligible'],rows=manifest['quality']['rows'],missing_minutes=manifest['quality']['missing_minutes'],corporate_action_issues=manifest['metadata']['corporate_action_issues'])))
