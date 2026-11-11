import pandas as pd
import pytest
from pydantic import ValidationError
from conftest import minute_frame
from backend.lab.config import Strategy
from backend.lab.data import normalize,prepare
from backend.lab.signals import generate_signals
from verification.strategy_fixtures import SPEC,scenario

def at(frame,family,index,side=1,**settings):
    parameters={**SPEC['config'],**settings,'family':family,'timeframe':'1m','direction':'long' if side>0 else 'short'}
    return [s for s in generate_signals(frame,Strategy(**parameters)) if s.source_index==index and s.side==side]

@pytest.mark.parametrize('fixture,positive,other,index,side',[
    ('level_bounce','level_bounce','flip_zone',21,1),
    ('break_of_structure','break_of_structure','breakout',19,1),
    ('flip_zone','flip_zone','breakout',20,1),
    ('trend_pullback','trend_pullback','trend_line',20,1),
    ('trend_line','trend_line','trend_pullback',17,1),
    ('break_of_structure','break_of_structure','change_of_character',19,1),
    ('change_of_character','change_of_character','break_of_structure',27,-1),
    ('fair_value_gap','fair_value_gap','supply_demand',16,1)])
def test_authored_families_are_distinct_detectors(fixture,positive,other,index,side):
    frame,_=scenario(fixture,'1m',side)
    assert at(frame,positive,index,side)
    assert not at(frame,other,index,side)

def test_demand_impulse_is_not_a_gap_alias():
    frame,_=scenario('supply_demand','1m',1)
    assert at(frame,'supply_demand',22)[0].level==pytest.approx(121.9)
    frame.loc[20,'open']=frame.loc[20,'close']
    assert not at(frame,'supply_demand',22)
    assert at(frame,'fair_value_gap',22)[0].level==pytest.approx(122.1)

def test_gap_requires_strict_three_candle_separation():
    frame,_=scenario('fair_value_gap','1m',1)
    assert at(frame,'fair_value_gap',16)
    frame.loc[15,'low']=frame.loc[13,'high']
    assert not at(frame,'fair_value_gap',16)

def test_sweep_requires_penetration_while_a_bounce_does_not():
    frame,_=scenario('sweep_reclaim','1m',1)
    assert at(frame,'sweep_reclaim',20)
    frame.loc[20,'low']=111.
    assert not at(frame,'sweep_reclaim',20)
    assert at(frame,'level_bounce',20)

def touch_path():
    original,_=scenario('level_bounce','1m',1)
    raw=minute_frame(SPEC['start_session']).iloc[:30].copy()
    fields=['open','high','low','close']
    raw.loc[:20,fields]=original.loc[:20,fields].to_numpy()
    for index in range(21,30):
        raw.loc[index,fields]=[113,113.1,110.95,112] if index%2 else [113.98,114.1,113.9,114]
    return prepare(normalize(raw)[0])

@pytest.mark.parametrize('touches,first',[(1,21),(2,23),(3,25),(4,27)])
def test_separated_visit_counts_gate_the_first_level_bounce(touches,first):
    frame=touch_path()
    cfg=Strategy(family='level_bounce',timeframe='1m',direction='long',swing_strength=2,min_touches=touches)
    signals=generate_signals(frame,cfg)
    assert signals and signals[0].source_index==first

def test_adjacent_overlap_candles_do_not_duplicate_one_bounce_visit():
    frame,_=scenario('level_bounce','1m',1)
    frame.loc[22,['open','high','low','close']]=[112.98,113.1,110.95,113]
    indices=[s.source_index for s in generate_signals(frame,Strategy(family='level_bounce',timeframe='1m',direction='long',swing_strength=2))]
    assert [i for i in indices if i in [21,22]]==[21]

def test_level_expiry_and_band_width_change_only_eligible_returns():
    frame=touch_path()
    assert at(frame,'level_bounce',21,level_age=2)
    assert not at(frame,'level_bounce',23,level_age=2)
    assert at(frame,'level_bounce',23,level_age=96)
    wide,_=scenario('level_bounce','1m',1)
    wide.loc[21,['open','high','low','close']]=[112.28,112.4,112.1,112.3]
    assert not at(wide,'level_bounce',21,level_tolerance=.1)
    assert at(wide,'level_bounce',21,level_tolerance=.5)

def test_line_break_and_zone_break_have_different_edges():
    frame,_=scenario('breakout','1m',1)
    frame.loc[19,['open','high','low','close']]=[120.18,120.3,119.9,120.2]
    assert at(frame,'breakout',19,level_shape='line')
    assert not at(frame,'breakout',19,level_shape='zone')

def test_choch_sweep_prerequisite_depth_and_age():
    frame,_=scenario('change_of_character','1m',-1)
    assert at(frame,'change_of_character',27,-1)
    assert not at(frame,'change_of_character',27,-1,sweep_required=True)
    frame.loc[26,'high']=128.5
    assert at(frame,'change_of_character',27,-1,sweep_required=True)
    assert not at(frame,'change_of_character',27,-1,sweep_required=True,sweep_depth=3)
    older,_=scenario('change_of_character','1m',-1);older.loc[25,'high']=128.5
    assert at(older,'change_of_character',27,-1,sweep_required=True,reclaim_bars=3)
    assert not at(older,'change_of_character',27,-1,sweep_required=True,reclaim_bars=1)

def test_gap_confluence_is_an_additional_choch_requirement():
    frame,_=scenario('change_of_character','1m',-1)
    frame.loc[26,'high']=126;frame.loc[27,'high']=126
    assert at(frame,'change_of_character',27,-1)
    assert not at(frame,'change_of_character',27,-1,gap_confluence=True)

def test_redundant_own_gap_confluence_is_rejected():
    with pytest.raises(ValidationError,match='gap_confluence'):
        Strategy(family='fair_value_gap',gap_confluence=True)

def test_unsuccessful_first_flip_return_is_consumed():
    frame,_=scenario('flip_zone','1m',1)
    frame.loc[20,['open','high','low','close']]=[121.98,122.2,119.7,119.8]
    frame.loc[21,['open','high','low','close']]=[121.98,122.2,119.9,122]
    assert not at(frame,'flip_zone',20)
    assert not at(frame,'flip_zone',21)

def delayed_flip():
    frame,_=scenario('flip_zone','1m',1)
    frame.loc[20,['open','high','low','close']]=[123.98,124.2,123.9,124]
    frame.loc[21,['open','high','low','close']]=[121.98,122.2,119.9,122]
    return frame

def test_flip_retest_window_and_fresh_breakout_filter_are_discriminating():
    frame=delayed_flip()
    assert at(frame,'flip_zone',21,retest_window=24)
    assert not at(frame,'flip_zone',21,retest_window=1)
    assert not at(frame,'flip_zone',21,fresh_breakout=True)
    immediate,_=scenario('flip_zone','1m',1)
    assert at(immediate,'flip_zone',20,fresh_breakout=True)

@pytest.mark.parametrize('family,event,invalid,returning',[
    ('supply_demand',22,[123,124.2,121.7,121.8],[123.98,124.2,122,124]),
    ('fair_value_gap',16,[115.98,116.1,113.9,114],[115.98,116.1,115.9,116])])
def test_closed_through_zone_cannot_revive_on_a_later_return(family,event,invalid,returning):
    frame,_=scenario(family,'1m',1)
    assert at(frame,family,event)
    frame.loc[event,['open','high','low','close']]=invalid
    frame.loc[event+1,['open','high','low','close']]=returning
    assert not at(frame,family,event)
    assert not at(frame,family,event+1)

@pytest.mark.parametrize('family,event,away,returning',[
    ('supply_demand',22,[134,134.1,133.9,134],[123.98,124.2,122,124]),
    ('fair_value_gap',16,[120.98,121.1,120.9,121],[114.98,115.1,114.9,115])])
def test_zone_age_expires_before_a_delayed_first_return(family,event,away,returning):
    # A zero-body away candle must not create an extending demand impulse.
    # The original zone is born at21 (gap15), so its age at24 (18) is3.
    frame,_=scenario(family,'1m',1)
    frame.loc[event,['open','high','low','close']]=away
    frame.loc[event+1,['open','high','low','close']]=away
    frame.loc[event+2,['open','high','low','close']]=returning
    assert at(frame,family,event+2,level_age=96)
    assert not at(frame,family,event+2,level_age=2)

@pytest.mark.parametrize('family,event,returning',[
    ('supply_demand',22,[123.98,124.2,122,124]),
    ('fair_value_gap',16,[115.98,116.1,115.9,116])])
def test_zone_first_successful_return_is_not_repeated(family,event,returning):
    frame,_=scenario(family,'1m',1)
    assert at(frame,family,event)
    frame.loc[event+1,['open','high','low','close']]=returning
    assert not at(frame,family,event+1)

@pytest.mark.parametrize('side',[1,-1])
def test_gap_middle_stop_uses_the_middle_extreme_and_can_be_invalid_after_fill(side):
    from backend.lab.config import Costs,Portfolio
    from backend.lab.engine import simulate
    frame,_=scenario('fair_value_gap','1m',side)
    cfg=Strategy(family='fair_value_gap',timeframe='1m',direction='long' if side>0 else 'short',swing_strength=2,stop_reference='gap',stop_buffer=0)
    wanted=[s for s in generate_signals(frame,cfg) if s.source_index==16][0]
    assert wanted.stop==pytest.approx(117.9 if side>0 else 182.1)
    result=simulate(frame,[wanted],cfg,Costs(),Portfolio())
    assert not result.trades and result.rejected[0]['reason']=='Invalid stop after fill/gap'
