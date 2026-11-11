"""Actual current owned worker: 10000 paired financial sets, immutable source copy.

One flat synthetic session and an authored original signal. This proves neither
detector quality, market edge, full-history capacity, API/UI nor final acceptance.
All 20000 occurrences and every unique complete book are independently audited.
"""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import ctypes, gzip, hashlib, json, os, shutil, sys, time
from ctypes import wintypes

root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root))
from verification.record_check import source_paths

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
original=root/'data/dev026/next-src'
if len(sys.argv)>1:
    assert len(sys.argv)==3 and sys.argv[1]=='--source'
    original=(root/sys.argv[2]).resolve()
    assert original in {(root/'data/dev026/next-src').resolve(),(root/'data/dev026/evidence-src').resolve()}
owned=root/'data/dev026/full-owned'/out.name.split('-')[0]
source=owned/'src';source.mkdir(parents=True,exist_ok=False)
subject={p.relative_to(original).as_posix():sha(p) for p in source_paths(original)}
for relative in subject:
    destination=source/relative;destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(original/relative,destination)
assert subject=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
sys.path[:0]=[str(source),str(source/'tests')]
# Remove the root verification package so runtime/reference imports use the copy.
for name in list(sys.modules):
    if name=='verification' or name.startswith('verification.'):
        del sys.modules[name]
from conftest import minute_frame
from backend.lab import service
from backend.lab.service import Lab,compressed_read
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import save_dataset,prepare as prepare_data,normalize
from backend.lab.signals import Signal
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from backend.lab.trade_twin_jobs import create
from verification.trade_twin_reference import execute_reference

class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(k,ctypes.c_size_t) for k in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
def memory():
    value=Counters();value.cb=ctypes.sizeof(value)
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
    fn=ctypes.WinDLL('psapi').GetProcessMemoryInfo
    fn.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    assert fn(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb)
    return value.PeakWorkingSetSize

lab=Lab(owned/'store');frame=minute_frame('2026-11-04')
frame[['open','high','low','close']]=[100.,101.,99.,100.]
manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored current owned worker capacity fixture',corporate_actions_complete=True))
regular=prepare_data(normalize(frame)[0]);cfg=Strategy(timeframe='1m',max_hold=24)
costs=Costs(commission_per_share=0,minimum_commission=0,fixed_fee_per_order=0,sell_fee_per_dollar=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
account=Portfolio();at=regular.iloc[20].timestamp
signal=Signal('authored-original','SPY',at,1,100.,2.,98.,None,1.,at,20)
service.generate_signals=lambda *args,**kwargs:[signal]
parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=cfg,costs=costs,portfolio=account))
assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
parent_before=sha(lab.output_path(parent['id']))
child=create(lab,parent['id']);began=time.perf_counter();peak_before=memory()
try:
    assert Worker(lab).run_once()
finally:
    duration=time.perf_counter()-began
    (out/'worker-runtime-measurement.json').write_text(json.dumps(dict(
        worker_seconds=duration,absolute_process_peak_working_set_bytes=memory(),
        process_peak_before_worker_bytes=peak_before,job_status=lab.store.job(child['id'])['status'],
        source_snapshot=source.relative_to(root).as_posix(),child=child['id']),indent=2),encoding='utf-8')
job=lab.store.job(child['id']);assert job['status']=='completed',job.get('error')
assert sha(lab.output_path(parent['id']))==parent_before
saved=compressed_read(lab.output_path(child['id']));report=saved['report']
assert report['financial_occurrences']==20000 and report['comparison_eligible']
for value in report['summaries'].values():
    assert value['observed_sets']==value['complete_sets']==value['exceedances']==10000
    assert value['failed_sets']==0 and value['adapted_pass'] is False
    assert Decimal(value['real_profit'])==0 and value['raw_exceedance_fraction']==1
folder=lab.output_path(child['id']).parent/'twins'
prep=compressed_read(next((folder/'preparation').glob('*.json.gz')))
plan=prep['plan'];assert plan['plan_hash']==report['plan_hash']
parts=[];bank={};seen={p:set() for p in report['summaries']}
for path in sorted((folder/'parts').glob('*.json.gz')):
    value=compressed_read(path);parts.append(value)
    for entry in value['books']:
        assert entry['key'] not in bank and digest(entry['book'])==entry['sha256']
        assert digest(entry['inputs'])==entry['key'];bank[entry['key']]=entry
        if job['payload']['twin_protocol']['version']>=2:
            evidence=entry['evidence'];assert digest(evidence)==entry['evidence_sha256']
            assert evidence['book_sha256']==entry['sha256']
            for kind in ['ledger','equity','rejected','encounters']:
                records=entry['book'][kind]
                assert evidence['counts'][kind]==len(records)
                assert evidence['arrays'][kind]==[digest(records[i:i+25]) for i in range(0,len(records),25)]
for part in parts:
    for row in part['sets']:
        outcome=row['outcome'];ordinal=outcome['set_index'];policy=outcome['policy']
        assert ordinal not in seen[policy];seen[policy].add(ordinal)
        assert outcome['state']=='completed' and outcome['trade_count']==len(plan['sources'])==1
        assert digest({k:v for k,v in row['draw'].items() if k!='draw_hash'})==row['draw']['draw_hash']
        total=Fraction(0)
        for original_trade,pool,match,member in zip(plan['sources'],plan['pools'],row['draw']['matches'],row['members']):
            coordinate=dict(policy=plan['draw_policy'],plan_hash=plan['plan_hash'],seed=job['payload']['seed'],set_index=ordinal,source_id=original_trade['trade_id'])
            domain=1<<256;ceiling=domain-domain%len(pool);counter=0
            while True:
                random=int(digest(coordinate|dict(counter=counter)),16)
                if random<ceiling:break
                counter+=1
            moment=plan['moments'][pool[random%len(pool)]]
            assert match['entry_at']==moment['entry_at'] and match['source_id']==original_trade['trade_id']
            assert member['source_id']==match['source_id']
            entry=bank[member['book_key']];assert member['book_sha256']==entry['sha256']
            if job['payload']['twin_protocol']['version']>=2:assert member['book_evidence_sha256']==entry['evidence_sha256']
            assert entry['inputs']['policy']==policy and entry['inputs']['match']==match
            total+=Fraction(entry['book']['net_profit'])
        assert Fraction(outcome['net_profit'])==total==0
assert all(values==set(range(10000)) for values in seen.values())

primitive=[{k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()} for row in regular.to_dict('records')]
def parity(actual,reference):
    if isinstance(reference,dict):
        assert set(actual)==set(reference)
        for key,value in reference.items():parity(actual[key],value)
    elif isinstance(reference,list):
        assert len(actual)==len(reference)
        for a,b in zip(actual,reference):parity(a,b)
    elif isinstance(reference,Decimal):assert abs(Decimal(str(actual))-reference)<=Decimal('1e-7')
    else:assert type(actual) is type(reference) and actual==reference
for entry in bank.values():
    inputs=entry['inputs']
    reference=execute_reference(primitive,inputs['match'],inputs['strategy'],inputs['costs'],inputs['portfolio'],[],inputs['policy'])
    parity(entry['book'],reference)
with lab.store.db() as db:
    states=dict(db.execute('SELECT state,COUNT(*) FROM trial_plans WHERE job_id=? GROUP BY state',(child['id'],)))
    assert states=={'completed':20001},states
    assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(child['id'],)).fetchone()[0]==20001
    commits=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(child['id'],)).fetchone()[0]
    assert commits==len(parts)==report['completed_parts']==job['payload']['work_partition']['part_count']
    assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(child['id'],)).fetchone()[0]==1
    assert db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(child['id'],)).fetchone()[0]==len(bank)
    if job['payload']['twin_protocol']['version']>=2:
        computations=[json.loads(r[0]) for r in db.execute("SELECT details FROM events WHERE entity_id=? AND kind='trial_computation_recorded'",(child['id'],))]
        recorded={(r['part'],r['window']):r for r in computations}
        assert len(computations)==len(recorded)==20000
        for part in parts:
            for row in part['sets']:
                outcome=row['outcome'];original=recorded[outcome['set_index'],outcome['policy']]
                assert original['sha256']==digest(row) and original['attempt']==part['attempt']
assert subject=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
artifacts=list((lab.output_path(child['id']).parent).rglob('*'))
result=dict(scope=__doc__,source_snapshot=source.relative_to(root).as_posix(),source_files=subject,source_unchanged=True,
    original_parent=parent['id'],child=child['id'],original_parent_unchanged=True,worker_seconds=duration,
    absolute_process_peak_working_set_bytes=memory(),process_peak_before_worker_bytes=peak_before,
    configured_sets_per_policy=10000,verified_occurrences=20000,verified_original_trial_checkpoints=20001,
    original_committed_parts=len(parts),independently_replayed_complete_books=len(bank),
    output_files=sum(p.is_file() for p in artifacts),output_bytes=sum(p.stat().st_size for p in artifacts if p.is_file()),
    summaries=report['summaries'],api_ui_verified=False,final_acceptance_certified=False)
(out/'owned-10000-financial-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in {'scope','source_files'}},indent=2))
