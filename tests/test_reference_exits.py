from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.data import normalize,prepare
from test_reference_execution import CFG,rows,sig,run_both,assert_parity
from test_rules import path_frame

EXPECTED=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/reference-exits-contract.json').read_text())['expected']

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('equal_first',[False,True])
def test_independent_completed_trigger_close_and_strict_equality(side,equal_first):
    frame=rows(10)
    first=98 if side>0 else 102;last=97 if side>0 else 103
    frame.loc[1,'low' if side>0 else 'high']=97 if side>0 else 103
    frame.loc[4,['high','low','close']]=[104,96,first if equal_first else last]
    frame.loc[5:,['open','high','low','close']]=[first,max(first,last)+1,min(first,last)-1,first]
    frame.loc[9,'close']=last
    cfg=CFG.model_copy(update={'timeframe':'5m','trigger_timeframe':'5m','stop_kind':'close','target':'5R'})
    actual,expected=run_both(frame,[sig(frame,side)],cfg)
    trade=expected['trades'][0]
    assert trade['exit_reason']=='close_stop'
    assert trade['exit_at']==EXPECTED['strict_equal_then_beyond_close_stop' if equal_first else 'five_minute_close_stop']
    assert_parity(actual,expected)

@pytest.mark.parametrize('day,key',[('2026-11-04','normal_session_flat'),('2026-11-27','early_session_flat')])
def test_independent_actual_session_flat_before_boundary_exit(day,key):
    raw=minute_frame(day).iloc[-4:]
    frame=prepare(normalize(raw)[0]);cfg=CFG.model_copy(update={'target':'5R','flat_at_close':True})
    actual,expected=run_both(frame,[sig(frame)],cfg)
    assert expected['trades'][0]['exit_reason']=='session_close'
    assert expected['trades'][0]['exit_at']==EXPECTED[key]
    assert_parity(actual,expected)

@pytest.mark.parametrize('overnight',[False,True])
def test_independent_timeout_counts_completed_trading_candles(overnight):
    frame=rows(30)
    if overnight:
        frame=prepare(normalize(pd.concat([minute_frame('2026-11-04').iloc[-10:],minute_frame('2026-11-05').iloc[:20]],ignore_index=True))[0])
    actual,expected=run_both(frame,[sig(frame)],CFG.model_copy(update={'target':'5R','max_hold':24}))
    assert expected['trades'][0]['exit_reason']=='timeout'
    assert expected['trades'][0]['exit_at']==EXPECTED['twenty_four_trading_minutes_over_overnight' if overnight else 'twenty_four_completed_minutes']
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
def test_independent_structure_reversal_exit_on_documented_pivot_geometry(side):
    frame=path_frame()
    if side<0:
        original=frame.copy()
        for to,source in [('open','open'),('close','close'),('high','low'),('low','high')]:
            frame[to]=original[source].map(lambda v:float(Decimal(300)-Decimal(str(v))))
    signal=sig(frame,side,at=24,stop=90 if side>0 else 210,target=200 if side>0 else 100)
    cfg=CFG.model_copy(update={'structure_exit':True,'target':'swing'})
    actual,expected=run_both(frame,[signal],cfg)
    assert expected['trades'][0]['exit_reason']=='structure'
    assert expected['trades'][0]['exit_at']==(frame.iloc[27].timestamp+pd.Timedelta(minutes=1)).isoformat()
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('target',[None,'wrong_side','valid'])
def test_independent_known_swing_target_validation_and_fill(side,target):
    frame=rows()
    value=None if target is None else ((99 if side>0 else 101) if target=='wrong_side' else (103 if side>0 else 97))
    if target=='valid': frame.loc[2,'high' if side>0 else 'low']=103.01 if side>0 else 96.99
    actual,expected=run_both(frame,[sig(frame,side,target=value)],CFG.model_copy(update={'target':'swing'}))
    if target=='valid': assert expected['trades'][0]['exit_reason']=='target'
    else: assert not expected['trades'] and expected['rejected'][0]['reason']=='No valid known swing target'
    assert_parity(actual,expected)

@pytest.mark.parametrize('expiry',[1,2])
def test_independent_limit_expiry_checked_before_fill(expiry):
    frame=rows();frame[['open','high','low','close']]=[100.2,100.3,100.1,100.2]
    frame.loc[2,'low']=99.98
    cfg=CFG.model_copy(update={'timeframe':'5m','trigger_timeframe':'1m','entry':'limit','limit_expiry':expiry})
    actual,expected=run_both(frame,[sig(frame)],cfg)
    if expiry==1: assert not expected['trades'] and expected['rejected'][0]['reason']=='Limit expired'
    else: assert expected['trades'][0]['entry_at']==frame.iloc[2].timestamp.isoformat()
    assert_parity(actual,expected)

def test_independent_limit_expiry_includes_a_weekend():
    frame=prepare(normalize(pd.concat([minute_frame('2026-11-06').iloc[-3:],minute_frame('2026-11-09').iloc[:3]],ignore_index=True))[0])
    frame[['open','high','low','close']]=[100.2,100.3,100.1,100.2]
    frame.loc[3:,'low']=99.98
    cfg=CFG.model_copy(update={'timeframe':'1d','entry':'limit','limit_expiry':3})
    actual,expected=run_both(frame,[sig(frame)],cfg)
    assert not expected['trades'] and expected['rejected'][0]['reason']=='Limit expired'
    assert_parity(actual,expected)
