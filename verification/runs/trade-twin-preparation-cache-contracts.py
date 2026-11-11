"""Pure preparation reuse must preserve the complete original execution kernel."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util
import pandas as pd
import pytest
from backend.lab import trade_twin_execution as execution
from backend.lab.config import Costs
from test_trade_twin_execution import frame,match_for,CFG,ZERO,ACCOUNT,reference,parity

spec=importlib.util.spec_from_file_location('backend.lab._original_twin_execution',Path(__file__).with_name('trade-twin-execution-before-preparation-optimization.py'))
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)

def compare(data,match,cfg=CFG,costs=ZERO,account=ACCOUNT,actions=(),policy='barrier_capped_elapsed_v1',cache=None):
    cache=cache or execution.TwinPreparationCache()
    expected=original.execute_twin(data,match,cfg,costs,account,actions,policy=policy)
    for _ in range(2):
        actual=execution.execute_twin(data,match,cfg,costs,account,actions,policy=policy,preparation=cache)
        assert actual==expected
    parity(actual,reference(data,match,cfg,costs,account,actions,policy))
    return actual,cache

@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('stop',['hard','close'])
@pytest.mark.parametrize('timeframe',['1m','5m'])
@pytest.mark.parametrize('costs',[ZERO,Costs()])
def test_warm_reuse_preserves_every_field_against_original_and_independent_account(policy,side,stop,timeframe,costs):
    data=frame();match=match_for(data,side,end=9)
    cfg=CFG.model_copy(update=dict(stop_kind=stop,timeframe=timeframe))
    result,cache=compare(data,match,cfg,costs=costs,policy=policy)
    assert result['status']=='complete' and len(cache.entries)==2

@pytest.mark.parametrize('column,value',[('low',float('nan')),('high',float('inf')),('open',-1.),('close',0.),('volume',-1.),('low',110.)])
def test_changed_invalid_observations_outside_trade_window_are_never_hidden_by_warm_reuse(column,value):
    data=frame();match=match_for(data);_,cache=compare(data,match)
    data.loc[len(data)-1,column]=value
    with pytest.raises(ValueError) as old:original.execute_twin(data,match,CFG,ZERO,ACCOUNT)
    with pytest.raises(type(old.value),match=str(old.value)):
        execution.execute_twin(data,match,CFG,ZERO,ACCOUNT,preparation=cache)

def test_changed_valid_prices_recompute_transforms_and_financial_result():
    data=frame();match=match_for(data);before,cache=compare(data,match)
    data.loc[2,'low']=97.
    after,_=compare(data,match,cache=cache)
    assert before['net_profit']!=after['net_profit']

def test_changed_timestamp_after_warmup_is_revalidated_even_outside_trade_window():
    data=frame();match=match_for(data);_,cache=compare(data,match)
    data.loc[len(data)-1,'timestamp']+=pd.Timedelta(seconds=1)
    for function in [original.execute_twin,lambda *a,**k:execution.execute_twin(*a,**k,preparation=cache)]:
        with pytest.raises(ValueError,match='aware minute'):function(data,match,CFG,ZERO,ACCOUNT)

def test_changed_borrow_costs_and_match_are_not_financial_result_cache_keys():
    data=frame();match=match_for(data,-1);before,cache=compare(data,match)
    unavailable=ZERO.model_copy(update=dict(borrow_available=False))
    after,_=compare(data,match,costs=unavailable,cache=cache)
    assert before['status']=='complete' and after['status']=='failed'
    altered=match|dict(quantity=100000)
    limited,_=compare(data,altered,cache=cache)
    assert limited['status']=='failed'

def test_returned_records_aggregates_and_source_snapshots_are_detached():
    data=frame();cache=execution.TwinPreparationCache();expected=data.to_dict('records')
    first=cache.records(data);first[0]['low']=-1;first.clear()
    assert cache.records(data)==expected
    bars=cache.aggregated(data,'5m');expected_bars=bars.copy(deep=True);bars.iloc[0,bars.columns.get_loc('low')]=-1
    pd.testing.assert_frame_equal(cache.aggregated(data,'5m'),expected_bars)
    data.loc[0,'volume']=12345.
    assert cache.records(data)==data.to_dict('records')

def test_byte_limit_and_entry_limit_bound_retention_without_truncating_transforms():
    data=frame();tiny=execution.TwinPreparationCache(max_bytes=1)
    assert tiny.records(data)==data.to_dict('records') and not tiny.entries and tiny.retained_bytes==0
    pd.testing.assert_frame_equal(tiny.aggregated(data,'1m'),execution.aggregate(data,'1m'))
    assert not tiny.entries
    one=execution.TwinPreparationCache(max_entries=1)
    for operation in [lambda:one.records(data),lambda:one.aggregated(data,'5m'),lambda:one.records(data)]:
        operation();assert len(one.entries)==1 and 0<one.retained_bytes<=one.max_bytes

def test_combined_byte_budget_evicts_prior_snapshot_and_returns_complete_changed_records():
    data=frame();probe=execution.TwinPreparationCache();probe.records(data)
    budget=probe.retained_bytes+1;cache=execution.TwinPreparationCache(max_bytes=budget)
    cache.records(data);changed=data.copy();changed.loc[0,'volume']+=100
    assert cache.records(changed)==changed.to_dict('records')
    assert len(cache.entries)==1 and cache.retained_bytes<=budget

@pytest.mark.parametrize('limit,entries',[(0,4),(True,4),(64*1024*1024+1,4),(1.,4),(1,0),(1,5),(1,True)])
def test_invalid_or_implicit_retention_limits_are_refused(limit,entries):
    with pytest.raises(ValueError,match='bounded integer'):execution.TwinPreparationCache(max_bytes=limit,max_entries=entries)

def test_unknown_mutable_columns_and_nonstandard_known_objects_use_uncached_original_transforms():
    data=frame();cache=execution.TwinPreparationCache();data['extra']=[[1] for _ in range(len(data))]
    assert cache.records(data)==data.to_dict('records') and not cache.entries
    data.loc[0,'extra'].append(2)
    assert cache.records(data)[0]['extra']==[1,2]
    data=frame();data['factor']=data.factor.astype(object)
    assert cache.records(data)==data.to_dict('records') and not cache.entries
    pd.testing.assert_frame_equal(cache.aggregated(data,'5m'),execution.aggregate(data,'5m'))
    assert not cache.entries

def test_dtype_index_and_timeframe_changes_cannot_reuse_incompatible_transforms():
    data=frame();cache=execution.TwinPreparationCache();cache.records(data)
    changed=data.copy();changed['volume']=changed.volume.astype('int64')
    records=cache.records(changed);assert type(records[0]['volume']) is int
    changed.index=changed.index+1000
    assert cache.records(changed)==changed.to_dict('records')
    for timeframe in ['1m','5m','15m']:
        pd.testing.assert_frame_equal(cache.aggregated(data,timeframe),execution.aggregate(data,timeframe))
        assert len(cache.entries)<=4 and cache.retained_bytes<=cache.max_bytes
    with pytest.raises(ValueError):cache.aggregated(data,'unsupported')

def test_preparation_cache_is_owned_by_one_thread():
    data=frame();cache=execution.TwinPreparationCache();cache.records(data)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(ValueError,match='one execution thread'):pool.submit(cache.records,data).result()

def test_warm_preparation_never_hides_cancellation_or_accepts_arbitrary_cache_objects():
    data=frame();match=match_for(data);_,cache=compare(data,match)
    with pytest.raises(InterruptedError):execution.execute_twin(data,match,CFG,ZERO,ACCOUNT,preparation=cache,cancel=lambda:True)
    with pytest.raises(ValueError,match='owned bounded'):execution.execute_twin(data,match,CFG,ZERO,ACCOUNT,preparation={})
    compare(data,match,cache=cache)
