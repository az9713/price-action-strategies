"""Synthetic saved-account -> sealed features -> financial sets integration probe.

Uninstalled prototype, one flat390-minute session and one real executed synthetic
trade. This does not certify the durable child/API/UI workflow or realistic
market throughput. It runs concurrently with the full backend regression.
"""
from pathlib import Path
from decimal import Decimal
import ctypes,hashlib,importlib.util,json,os,sys,time
from ctypes import wintypes
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path[:0]=[str(source),str(source/'tests')]
from backend.lab import service
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import save_dataset,prepare,normalize
from backend.lab.models import Experiment
from backend.lab.service import Lab
from backend.lab.signals import Signal
from backend.lab.worker import Worker
from backend.lab.trade_twin_source import read_saved_source
from backend.lab.trade_twins import prepare_plan,draw_set,summarize,EXECUTION_POLICIES
from backend.lab.trade_twin_execution import execute_twin
from verification.trade_twin_reference import execute_reference
from conftest import minute_frame
sys.path.append(str(root));from verification.record_check import source_paths
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
before=snapshot();started=time.perf_counter()
spec=importlib.util.spec_from_file_location('uninstalled_feature_prototype',root/'verification/runs/trade_twin_features_draft.py');features=importlib.util.module_from_spec(spec);spec.loader.exec_module(features)
owned=root/'data/dev026/prototypes'/out.name;assert not owned.exists();owned.mkdir(parents=True)
lab=Lab(owned);day='2026-11-04';frame=minute_frame(day,'SPY');frame[['open','high','low','close']]=[100.,101.,99.,100.]
manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored flat D046 10000-set integration probe',corporate_actions_complete=True))
regular=prepare(normalize(frame)[0]);cfg=Strategy(timeframe='1m',max_hold=24)
costs=Costs(commission_per_share=0,minimum_commission=0,fixed_fee_per_order=0,sell_fee_per_dollar=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
account=Portfolio();at=regular.iloc[20].timestamp
signal=Signal('synthetic-original-source', 'SPY',at,1,100.,2.,98.,None,1.,at,20)
original_generator=service.generate_signals
try:
 service.generate_signals=lambda *a,**k:[signal]
 job=lab.create_experiment(Experiment(dataset_id=manifest['id'],start=day,end=day,strategy=cfg,costs=costs,portfolio=account))
 assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
finally:service.generate_signals=original_generator
original=read_saved_source(lab,job['id']);assert len(original['sources'])==1 and original['source_profit']=='0.0'
feature=features.candidate_features(regular,cfg,['SPY'],day,day)
plan=prepare_plan(original['sources'],feature['moments'],feature['clock'],day,day,original['authority_hash']);assert plan.eligible
def save(path,value):
 raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False,default=str).encode();path.write_bytes(raw);return hashlib.sha256(raw).hexdigest()
plan_path=out/'sealed-prototype-plan.json';plan_sha=save(plan_path,plan.json())
save(out/'original-source-authority.json',original);save(out/'candidate-features.json',feature)
save(out/'original-synthetic-account.json',lab.result(job['id']))
primitive=[{k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()} for row in regular.to_dict('records')]
def parity(actual,reference,where='book'):
 if isinstance(reference,dict):
  assert set(actual)==set(reference),where
  for k,v in reference.items():parity(actual[k],v,where+'.'+k)
 elif isinstance(reference,list):
  assert len(actual)==len(reference),where
  for i,v in enumerate(reference):parity(actual[i],v,where+f'[{i}]')
 elif isinstance(reference,Decimal):assert abs(Decimal(str(actual))-reference)<=Decimal('1e-7'),where
 else:assert actual==reference and type(actual) is type(reference),where
bank=out/'financial-bank';bank.mkdir();cache={};new_books=reused_books=0;authority_reads=1
context=dict(plan_hash=plan.plan_hash,original_authority_hash=original['authority_hash'],configuration=cfg.model_dump(mode='json'),costs=costs.model_dump(mode='json'),portfolio=account.model_dump(mode='json'),dataset_manifest_hash=identity(manifest),actions=[],precision='canonical-decimal-strings-v1')
def authorize():
 global authority_reads
 current=read_saved_source(lab,job['id']);authority_reads+=1
 assert current['authority_hash']==original['authority_hash'] and current['sources']==original['sources'] and sha(plan_path)==plan_sha
def obtain(match,policy):
 global new_books,reused_books
 inputs=context|dict(match=match,policy=policy);key=identity(inputs);path=bank/(key+'.json')
 if key not in cache:
  actual=execute_twin(regular,match,cfg,costs,account,policy=policy)
  reference=execute_reference(primitive,match,cfg.model_dump(mode='json'),costs.model_dump(mode='json'),account.model_dump(mode='json'),[],policy)
  parity(actual,reference);assert actual['status']=='complete' and actual['net_profit']==0
  digest=save(path,dict(inputs=inputs,actual=actual,reference=reference));cache[key]=digest;new_books+=1
 else:reused_books+=1
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==cache[key]
 saved=json.loads(raw);assert saved['inputs']==inputs
 amount=Decimal(saved['actual']['net_profit']);assert amount.is_finite()
 return dict(key=key,sha256=cache[key]),amount
paths={policy:out/(policy+'-sets.jsonl') for policy in EXECUTION_POLICIES}
writers={policy:path.open('w',encoding='utf-8') for policy,path in paths.items()}
try:
 for ordinal in range(10000):
  authorize();draw=draw_set(plan,42,ordinal)
  for policy in EXECUTION_POLICIES:
   references=[];total=Decimal(0)
   for match in draw['matches']:
    ref,amount=obtain(match,policy);references.append(ref);total+=amount
   row=dict(plan_hash=plan.plan_hash,seed=42,policy=policy,set_index=ordinal,trade_count=len(plan.sources),state='completed',net_profit=str(total),error=None,draw_hash=draw['draw_hash'],financial_books=references)
   writers[policy].write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
  if ordinal and ordinal%1000==0:print(json.dumps(dict(paired_sets=ordinal,new_financial_books=new_books,authority_reads=authority_reads)),flush=True)
finally:
 for writer in writers.values():writer.close()
authorize();summaries={};occurrences=0
for policy,path in paths.items():
 def audited_rows():
  global occurrences
  with path.open(encoding='utf-8') as f:
   for ordinal,line in enumerate(f):
    row=json.loads(line);draw=draw_set(plan,42,ordinal)
    assert row['set_index']==ordinal and row['draw_hash']==draw['draw_hash'] and len(row['financial_books'])==len(plan.sources)
    total=Decimal(0)
    for match,ref in zip(draw['matches'],row['financial_books']):
     p=bank/(ref['key']+'.json');assert sha(p)==ref['sha256']==cache[ref['key']]
     book=json.loads(p.read_text());assert book['inputs']==context|dict(match=match,policy=policy)
     total+=Decimal(book['actual']['net_profit']);occurrences+=1
    assert Decimal(row['net_profit'])==total and total==0
    # Existing grading input is float. This probe's prespecified flat profit is
    # exactly representable. General canonical-Decimal grading remains required.
    value=float(total);assert Decimal(str(value))==total
    yield {k:row[k] for k in ['plan_hash','seed','policy','set_index','trade_count','state','error']}|dict(net_profit=value)
 summaries[policy]=summarize(plan,42,policy,audited_rows())
 assert summaries[policy]['complete_sets']==10000 and summaries[policy]['exceedances']==10000 and summaries[policy]['adapted_pass'] is False
authorize();assert before==snapshot() and len(lab.store.jobs())==1
class Counters(ctypes.Structure):
 _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
counters=Counters();counters.cb=ctypes.sizeof(counters);kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=wintypes.HANDLE
psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
assert psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),ctypes.sizeof(counters))
value=dict(scope=__doc__,original_synthetic_job_id=job['id'],source_trades=len(plan.sources),matching_pool_sizes=list(map(len,plan.pools)),complete_sets_per_policy=10000,policies=list(EXECUTION_POLICIES),complete_financial_occurrences=occurrences,new_independently_verified_financial_books=new_books,verified_reuses=reused_books,original_authority_reads=authority_reads,summaries=summaries,
 elapsed_seconds=time.perf_counter()-started,absolute_process_peak_working_set_bytes=counters.PeakWorkingSetSize,artifact_bytes_before_summary=sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),staged_source_files=before,staged_source_unchanged=True,uninstalled_prototype=True,durable_product_workflow_verified=False,final_acceptance_certified=False,
 limits='One flat synthetic session and one executed source trade; all ties retained and both diagnostics fail. Memoized reachable books are reused with byte/input verification for each distinct occurrence. No realistic market throughput, durable child/API/UI, arbitrary Decimal-to-float grading, failure recovery or final acceptance claim.')
save(out/'prototype-financial-10000-summary.json',value)
print(json.dumps({k:v for k,v in value.items() if k!='staged_source_files'},indent=2))
