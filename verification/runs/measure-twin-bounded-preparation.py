"""Isolated original/current exact-book timings and native peak working sets.

An authored48-book workload is replayed in four fresh processes. This does not
complete the required20000-set comparison or certify market-scale capacity.
"""
from contextlib import closing
from pathlib import Path
from statistics import median
import gc,gzip,hashlib,importlib.util,json,os,sqlite3,subprocess,sys,time

root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
store=root/'data/dev027/funnel-positive/72bda7bd74694a9b82d3a8a9facd1c9d';jid='0bb4e66743e1473cb6c344f54fcfef8f'

def counts():
    with closing(sqlite3.connect((store/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        return {t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}

def child(mode):
    from backend.lab.config import identity
    from backend.lab.data import Action,load_window,prepare
    from backend.lab.trade_twin_execution import execute_twin,TwinPreparationCache
    from backend.lab.trade_twin_parts import freeze
    from backend.lab.trade_twins import EXECUTION_POLICIES
    spec=importlib.util.spec_from_file_location('backend.lab._original_twin_execution',Path(__file__).with_name('trade-twin-execution-before-preparation-optimization.py'))
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    with closing(sqlite3.connect((store/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        payload=json.loads(db.execute('SELECT payload FROM jobs WHERE id=?',(jid,)).fetchone()[0])
        headers=[json.loads(row[0]) for row in db.execute("SELECT details FROM events WHERE entity_id=? AND kind='twin_part_committed' ORDER BY id",(jid,))]
    assert len(headers)==3
    books=[];parts=[]
    for header in headers:
        path=store/'data/jobs'/jid/'twins/parts'/header['filename'];packed=path.read_bytes()
        assert hashlib.sha256(packed).hexdigest()==header['sha256']
        part=json.loads(gzip.decompress(packed));available=part['books']
        books.extend(available[i*(len(available)-1)//15] for i in range(16))
        parts.append(dict(sha256=header['sha256'],bytes=len(packed),part=header['part']))
        del part,available,packed
    assert len(books)==len({book['key'] for book in books})==48
    assert {b['inputs']['policy'] for b in books}==set(EXECUTION_POLICIES)
    assert {b['inputs']['match']['side'] for b in books}=={-1,1}
    frame,manifest=load_window(store/'data/datasets',payload['dataset_id'],payload['start'],payload['end'],symbols=['SPY'])
    assert identity(manifest)==payload['dataset_manifest_hash']
    actions=[Action(**a) for a in manifest['actions'] if payload['start']<=a['ex_date']<=payload['end'] and a['symbol']=='SPY']
    regular=prepare(frame,actions);gc.collect();cache=None if mode=='preserved_original' else TwinPreparationCache()
    function=original.execute_twin if cache is None else execute_twin
    wall=time.perf_counter();cpu=time.process_time();hashes=[]
    for book in books:
        inputs=book['inputs'];assert identity(inputs)==book['key'] and identity(book['book'])==book['sha256']
        extra={} if cache is None else dict(preparation=cache)
        value=freeze(function(regular,inputs['match'],inputs['strategy'],inputs['costs'],inputs['portfolio'],actions,policy=inputs['policy'],**extra))
        assert value==book['book'];hashes.append(identity(value))
    elapsed=time.perf_counter()-wall;used=time.process_time()-cpu
    import ctypes
    from ctypes import wintypes
    class Memory(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),
            ('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
            ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
            ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi=ctypes.WinDLL('psapi',use_last_error=True);psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Memory),wintypes.DWORD]
    memory=Memory();memory.cb=ctypes.sizeof(memory)
    assert psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
    return dict(mode=mode,wall_seconds=elapsed,cpu_seconds=used,peak_working_set_bytes=memory.PeakWorkingSetSize,
        working_set_bytes=memory.WorkingSetSize,distinct_books=48,original_part_digests=parts,
        complete_book_hashes=hashes,all_original_complete_books_equal=True,
        retained_cache_estimate_bytes=cache.retained_bytes if cache is not None else 0,
        retained_cache_entries=len(cache.entries) if cache is not None else 0)

if len(sys.argv)==3 and sys.argv[1]=='--mode':
    print(json.dumps(child(sys.argv[2])))
else:
    before=counts();results=[]
    for mode in ['preserved_original','bounded_preparation','bounded_preparation','preserved_original']:
        completed=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--mode',mode],capture_output=True,text=True,encoding='utf-8')
        assert completed.returncode==0,completed.stderr
        value=json.loads(completed.stdout);results.append(value)
        assert value['retained_cache_estimate_bytes']<=64*1024*1024 and value['retained_cache_entries']<=4
    assert before==counts()
    assert all(r['complete_book_hashes']==results[0]['complete_book_hashes'] for r in results)
    value=dict(scope=__doc__,measurements=results,actual_replayed_financial_books=192,distinct_original_books=48,
        both_policies_and_sides=True,all_complete_original_books_equal=True,original_store_counts_unchanged=True,new_saved_trials=0,
        median_wall_seconds={m:median(r['wall_seconds'] for r in results if r['mode']==m) for m in ['preserved_original','bounded_preparation']},
        median_cpu_seconds={m:median(r['cpu_seconds'] for r in results if r['mode']==m) for m in ['preserved_original','bounded_preparation']},
        observed_peak_working_set_bytes={m:[r['peak_working_set_bytes'] for r in results if r['mode']==m] for m in ['preserved_original','bounded_preparation']})
    (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'bounded-preparation-isolated-measurements.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in value.items() if k!='measurements'},indent=2))
