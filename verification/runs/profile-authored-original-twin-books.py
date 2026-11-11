"""Replay20 committed authored books for profiling, without new saved trials.

This is a diagnostic microprofile, not a completed comparison or capacity gate.
The ongoing original job/store is read-only to this helper.
"""
from contextlib import closing
from pathlib import Path
import cProfile,gzip,hashlib,json,os,pstats,sqlite3,sys,time
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.config import identity
from backend.lab.data import Action,load_window,prepare
from backend.lab.trade_twin_execution import execute_twin
from backend.lab.trade_twin_parts import freeze
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
store=root/'data/dev027/funnel-positive/72bda7bd74694a9b82d3a8a9facd1c9d'
jid='0bb4e66743e1473cb6c344f54fcfef8f'
with closing(sqlite3.connect((store/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    payload=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()[0])
    rows=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='twin_part_committed' AND json_extract(details,'$.part')=0",(jid,)).fetchall()
    assert len(rows)==1;header=json.loads(rows[0][0])
path=store/'data/jobs'/jid/'twins/parts'/header['filename'];packed=path.read_bytes()
assert hashlib.sha256(packed).hexdigest()==header['sha256']
part=json.loads(gzip.decompress(packed));del packed
frame,manifest=load_window(store/'data/datasets',payload['dataset_id'],payload['start'],payload['end'],symbols=['SPY'])
assert identity(manifest)==payload['dataset_manifest_hash']
actions=[Action(**a) for a in manifest['actions'] if payload['start']<=a['ex_date']<=payload['end'] and a['symbol']=='SPY']
regular=prepare(frame,actions)
books=part['books'][:20];assert len(books)==20
profile=cProfile.Profile();started=time.perf_counter();cpu=time.process_time()
def replay():
    for book in books:
        inputs=book['inputs']
        assert identity(inputs)==book['key'] and identity(book['book'])==book['sha256']
        value=freeze(execute_twin(regular,inputs['match'],inputs['strategy'],inputs['costs'],inputs['portfolio'],actions,policy=inputs['policy']))
        assert value==book['book'],'Current exact book differs from committed original.'
profile.runcall(replay)
rows=[]
for (filename,line,name),(primitive,calls,internal,cumulative,callers) in pstats.Stats(profile).stats.items():
    rows.append(dict(file=Path(filename).name,line=line,function=name,calls=calls,internal_seconds=internal,cumulative_seconds=cumulative))
rows.sort(key=lambda x:x['cumulative_seconds'],reverse=True)
value=dict(scope=__doc__,replayed_financial_books=20,all_exact_complete_books_equal_originals=True,
    wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,original_part_sha256=header['sha256'],
    observed_minutes=len(regular),new_saved_trials=0,top_cumulative=rows[:30],all_function_records=rows)
(out/'authored-original-twin-book-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='all_function_records'},indent=2))
