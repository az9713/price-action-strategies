"""Exact-book prototype of caching only equal-frame pure preparation transforms.

All original per-observation, match, geometry, clock, borrowing, action and
financial checks still run. No financial result cache or production change.
"""
from contextlib import ExitStack,closing
from pathlib import Path
from statistics import median
from unittest.mock import patch
import gzip,hashlib,json,os,sqlite3,sys,time
import pandas as pd
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.config import identity
from backend.lab.data import Action,load_window,prepare
from backend.lab import trade_twin_execution as execution
from backend.lab.trade_twin_parts import freeze
from backend.lab.trade_twins import EXECUTION_POLICIES
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
store=root/'data/dev027/funnel-positive/72bda7bd74694a9b82d3a8a9facd1c9d';jid='0bb4e66743e1473cb6c344f54fcfef8f'
with closing(sqlite3.connect((store/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    payload=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()[0])
    header=json.loads(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='twin_part_committed' AND json_extract(details,'$.part')=0",(jid,)).fetchone()[0])
path=store/'data/jobs'/jid/'twins/parts'/header['filename'];packed=path.read_bytes()
assert hashlib.sha256(packed).hexdigest()==header['sha256']
part=json.loads(gzip.decompress(packed));all_books=part['books'];books=[all_books[i*(len(all_books)-1)//15] for i in range(16)]
assert {b['inputs']['policy'] for b in books}==set(EXECUTION_POLICIES)
assert {b['inputs']['match']['side'] for b in books}=={-1,1}
frame,manifest=load_window(store/'data/datasets',payload['dataset_id'],payload['start'],payload['end'],symbols=['SPY'])
assert identity(manifest)==payload['dataset_manifest_hash']
actions=[Action(**a) for a in manifest['actions'] if payload['start']<=a['ex_date']<=payload['end'] and a['symbol']=='SPY']
regular=prepare(frame,actions);aggregate=execution.aggregate;to_dict=pd.DataFrame.to_dict;measurements=[]
for mode in ['original','equal_frame_transforms','equal_frame_transforms','original']:
    wall=time.perf_counter();cpu=time.process_time();aggregates={};records=[];counts=dict(aggregate_calls=0,aggregate_hits=0,records_calls=0,records_hits=0)
    def cached_aggregate(observations,timeframe):
        counts['aggregate_calls']+=1;cached=aggregates.get(timeframe)
        if cached is not None and observations.equals(cached[0]):
            counts['aggregate_hits']+=1;return cached[1].copy(deep=True)
        value=aggregate(observations,timeframe);aggregates[timeframe]=(observations.copy(deep=True),value.copy(deep=True));return value
    def cached_records(observations,orient='dict',*args,**kwargs):
        if orient=='records' and not args and not kwargs:
            counts['records_calls']+=1
            for snapshot,value in records:
                if observations.equals(snapshot):
                    counts['records_hits']+=1;return [row.copy() for row in value]
            value=to_dict(observations,orient)
            if len(records)<4:records.append((observations.copy(deep=True),[row.copy() for row in value]))
            return value
        return to_dict(observations,orient,*args,**kwargs)
    hashes=[]
    with ExitStack() as stack:
        if mode!='original':
            stack.enter_context(patch.object(execution,'aggregate',cached_aggregate))
            stack.enter_context(patch.object(pd.DataFrame,'to_dict',cached_records))
        for book in books:
            inputs=book['inputs'];assert identity(inputs)==book['key'] and identity(book['book'])==book['sha256']
            value=freeze(execution.execute_twin(regular,inputs['match'],inputs['strategy'],inputs['costs'],inputs['portfolio'],actions,policy=inputs['policy']))
            assert value==book['book'];hashes.append(identity(value))
    measurements.append(dict(mode=mode,wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
        complete_book_hashes=hashes,**counts))
assert len({identity(r['complete_book_hashes']) for r in measurements})==1
result=dict(scope=__doc__,original_part_sha256=header['sha256'],replayed_financial_books=64,distinct_original_books=16,
    both_policies_and_sides=True,all_complete_books_equal_originals=True,measurements=measurements,
    median_wall_seconds={m:median(r['wall_seconds'] for r in measurements if r['mode']==m) for m in ['original','equal_frame_transforms']},
    median_cpu_seconds={m:median(r['cpu_seconds'] for r in measurements if r['mode']==m) for m in ['original','equal_frame_transforms']},
    production_unchanged=True,new_saved_trials=0)
(out/'twin-pure-preparation-cache-prototype.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='measurements'},indent=2))
