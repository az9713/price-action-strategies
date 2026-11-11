import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from backend.lab.config import Strategy,Costs,Portfolio,FAMILIES
from backend.lab.data import normalize,prepare,aggregate
from backend.lab.signals import contexts,generate_signals,prior_atr
from conftest import minute_frame

@pytest.mark.parametrize('kwargs',[{'unknown':1},{'confirmation':'lower_bos'},
    {'family':'breakout','stop_reference':'gap'},{'family':'level_bounce','fresh_breakout':True},
    {'timeframe':'1h','trigger_timeframe':'1d'},{'timeframe':'1d','trigger_timeframe':'1d'},
    {'timeframe':'4h','flat_at_close':True},{'pullback_min':4,'pullback_max':2}])
def test_invalid_combinations_are_not_ignored(kwargs):
    with pytest.raises(ValidationError): Strategy(**kwargs)

def test_daily_trigger_special_case(): assert Strategy(timeframe='1d').trigger=='1h'

@pytest.mark.parametrize('kwargs',[{'min_touches':2},{'family':'breakout','impulse_bars':3},
    {'family':'fair_value_gap','retest_window':12},{'family':'change_of_character','sweep_depth':.5}])
def test_nonapplicable_nondefault_dials_rejected(kwargs):
    with pytest.raises(ValidationError): Strategy(**kwargs)

def test_prior_atr_is_not_current_bar_dependent():
    c=np.arange(30,dtype=float)+100
    old=prior_atr(c+1,c-1,c)
    h=c+1;h[20]=10000
    new=prior_atr(h,c-1,c)
    assert old[20]==new[20] and old[21]!=new[21]

def path_frame():
    close=[100,101,103,105,102,100,103,106,110,112,108,105,108,114,118,120,116,111,115,122,126,128,123,116,120,125,119,110,100,96]
    raw=minute_frame().iloc[:len(close)].copy()
    raw['close']=close;raw['open']=np.asarray(close)-.02
    raw['high']=np.asarray(close)+.1
    raw['low']=np.asarray(close)-.1
    return prepare(normalize(raw)[0])

def test_explicit_bearish_structure_reversal():
    bars=aggregate(path_frame(),'1m')
    result=contexts(bars,Strategy(timeframe='1m',swing_strength=2))
    # Unique lows: index17=110.9 confirms19, index23=115.9 confirms25.
    # High index21=128.1 confirms23; the first close below 115.9 is index27=110.
    reversal=result.index[result.choch==-1].tolist()
    assert reversal==[27]
    assert result.loc[27,'trend_before']==1 and result.loc[27,'trend']==-1

@pytest.mark.parametrize('family',list(FAMILIES))
def test_context_and_signal_prefix_causality(family):
    regular=path_frame()
    cfg=Strategy(family=family,timeframe='1m',swing_strength=2)
    full=contexts(aggregate(regular,'1m'),cfg)
    prefix=contexts(aggregate(regular.iloc[:26],'1m'),cfg)
    pd.testing.assert_frame_equal(full.iloc[:26].reset_index(drop=True),prefix,check_dtype=False)
    a=generate_signals(regular,cfg)
    b=generate_signals(regular.iloc[:26],cfg)
    cutoff=regular.iloc[25].timestamp+pd.Timedelta(minutes=1)
    assert [s.json() for s in a if s.available_at<=cutoff]==[s.json() for s in b]

def test_unknown_costs_and_nonfinite_rejected():
    with pytest.raises(ValidationError): Costs(free_money=True)
    with pytest.raises(ValidationError): Portfolio(capital=float('nan'))
