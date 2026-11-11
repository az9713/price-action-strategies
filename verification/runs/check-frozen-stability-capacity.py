"""Actual 1000/10000/100000-node arithmetic workload; no financial simulation.

A full single-coordinate family has N*(N-1) directed neighbors. Independent
integer moments verify every output without materializing that quadratic graph.
This is not the separate real-market search/financial resource acceptance gate.
"""
from pathlib import Path
import ctypes
from ctypes import wintypes
from fractions import Fraction
import gc
import hashlib
import json
import os
import sys
import time

root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
from backend.lab.config import Strategy,identity,canonical
from backend.lab.research import core_hash,require_current_source
from backend.lab.research_qualification import stability
sys.path.insert(0,str(root))
from verification.record_check import source_paths


def snapshot(folder):return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(folder)}


class Counters(ctypes.Structure):
    _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
              *[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
                 'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]]


def memory():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    value=Counters();value.cb=ctypes.sizeof(value)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(value),value.cb):raise ctypes.WinError(ctypes.get_last_error())
    return dict(working_set_bytes=value.WorkingSetSize,process_peak_working_set_bytes=value.PeakWorkingSetSize)


def rational(value):return Fraction(int(value['numerator']),int(value['denominator']))


before=snapshot(stage);frozen={name:snapshot(root/name) for name in ['data/dev026/src','data/dev026/next-src','data/dev026/evidence-src']}
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);measurements=[]
for count in [1000,10000,100000]:
    gc.collect();started=time.perf_counter();baseline=memory()
    configurations=[Strategy(family='sweep_reclaim',timeframe='1m',sweep_depth=i/count) for i in range(count)]
    ids=[identity(c) for c in configurations];observations={};available=positive=undefined=total=squares=0
    for i,cid in enumerate(ids):
        numerator=i-count//2
        if i%97==0:observations[cid]=None
        else:
            observations[cid]=dict(net_profit=numerator/8,marked_sharpe=None if i%2==0 else .5)
            available+=1;positive+=numerator>0;undefined+=i%2==0;total+=numerator;squares+=numerator*numerator
    preparation_seconds=time.perf_counter()-started;reduction_started=time.perf_counter()
    result=stability(configurations,observations);reduction_seconds=time.perf_counter()-reduction_started
    assert result['version_count']==count and len(result['rows'])==count
    for i,(cid,row) in enumerate(zip(ids,result['rows'])):
        known=i%97!=0;numerator=i-count//2;n=available-known
        mean=Fraction(total-numerator*known,8*n)
        square_sum=Fraction(squares-numerator*numerator*known,64)
        variance=(square_sum-n*mean*mean)/(n-1)
        assert row['config_id']==cid and row['neighbors']==count-1 and row['available']==n
        assert row['missing']==count-1-n and row['positive']==positive-(known and numerator>0)
        assert row['undefined_sharpe']==undefined-(known and i%2==0)
        assert row['coordinate_counts']=={'sweep_depth':count-1}
        assert rational(row['mean_net_profit'])==mean and rational(row['sample_variance_net_profit'])==variance
    require_current_source();peak=memory();digest=identity(result)
    measurements.append(dict(versions=count,directed_neighbors=count*(count-1),original_financial_accounts=0,
        input_hash=identity([c.model_dump(mode='json') for c in configurations]),output_hash=digest,
        preparation_seconds=preparation_seconds,reduction_seconds=reduction_seconds,
        verification_and_total_seconds=time.perf_counter()-started,baseline_memory=baseline,after_reduction_memory=peak,
        every_original_output_checked=True,independent_integer_moments=True))
    print(json.dumps(measurements[-1]),flush=True)
    del configurations,ids,observations,result
assert before==snapshot(stage)
assert all(previous==snapshot(root/name) for name,previous in frozen.items())
value=dict(scope=__doc__,source_root=stage.relative_to(root).as_posix(),core_hash=core_hash(),source_files=before,
    source_unchanged=True,earlier_financial_sources_unchanged=True,measurements=measurements,
    user_prices_credentials_or_main_database_read=False,global_search_or_final_acceptance=False)
(out/'frozen-stability-capacity.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
