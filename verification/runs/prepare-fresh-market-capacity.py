"""Acquire a new independent benchmark sample; never clone user data or credentials."""
from contextlib import contextmanager
from datetime import date,timedelta
from pathlib import Path
import json,os,sqlite3,sys,uuid

root=Path.cwd();stage=root/'data/dev027/research-src'
sys.path.insert(0,str(stage))
from backend.lab.provider import Alpaca,parse_actions
from backend.lab.data import save_dataset
from backend.lab.research import Guard,core_hash
from backend.lab.store import StateError
from backend.lab.study_index import StudyIndex

contract=json.loads((root/'verification/runs/capacity-real-sample-contract.json').read_text(encoding='utf-8'))
symbols=contract['symbols'];first=contract['selection']['start'];last=contract['selection']['end']

class ReadOnlyOriginalStore:
    @contextmanager
    def db(self):
        path=root/'data/lab.sqlite3'
        db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,isolation_level=None)
        db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
        try:yield db
        finally:db.close()

store=ReadOnlyOriginalStore()
index=object.__new__(StudyIndex);index.store=store;index.error=StateError
store._study_index=index
guard=Guard(store)
# Check the entire independently requested action-query interval as well.
guard.access(symbols,(date.fromisoformat(first)-timedelta(days=30)).isoformat(),
    (date.fromisoformat(last)+timedelta(days=120)).isoformat(),'external_capacity_benchmark',record=False)
folder=root/'data/dev027/capacity-market'/uuid.uuid4().hex
folder.mkdir(parents=True,exist_ok=False)
with Alpaca(root/'.env',folder/'data/downloads') as provider:
    frame,metadata=provider.bars(symbols,first,last)
    collected,action_source=provider.corporate_actions(symbols,first,last)
actions,issues=parse_actions(collected,first,last)
metadata.update(corporate_action_source=action_source,corporate_actions_raw=collected,
    corporate_action_issues=issues,corporate_actions_status='provider_query_completed_not_independently_certified',
    input_kind='historical_market_data',limitations=['One-session benchmark only; no point-in-time universe or lending history is inferred.'])
assert not issues
manifest=save_dataset(folder/'data/datasets',frame,metadata,actions,first,last)
assert manifest['quality']['eligible'] and manifest['quality']['symbols']==symbols
origin=dict(scope=__doc__,benchmark_root=folder.relative_to(root).as_posix(),dataset_id=manifest['id'],
    contract='verification/runs/capacity-real-sample-contract.json',original_user_store_opened_read_only=True,
    original_user_store_copied=False,user_market_cache_copied=False,credentials_copied_or_archived=False,
    source_core_at_acquisition=core_hash(),fresh_provider_acquisition=True,quality=manifest['quality'])
(folder/'origin.json').write_text(json.dumps(origin,indent=2),encoding='utf-8')
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'fresh-market-capacity-origin.json').write_text(json.dumps(origin,indent=2),encoding='utf-8')
print(json.dumps(origin,indent=2))
