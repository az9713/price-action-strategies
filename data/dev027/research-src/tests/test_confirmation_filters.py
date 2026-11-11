"""Authored selector boundaries plus actual minute/detector/account integration.

The unit layer injects completed context tables, explicitly bypassing detector
and aggregation math. Its expected clocks/decisions are authored, not harvested
from production. Real-price integration cases below do not mock those stages.
"""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import pytest
from backend.lab import signals as module
from backend.lab.config import Strategy,Costs,Portfolio
from backend.lab.data import DataError,aggregate
from backend.lab.engine import simulate
from verification.strategy_fixtures import SPEC,scenario
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/confirmation-filter-contract.json').read_text(encoding='utf-8'))
AT=pd.Timestamp('2026-10-05T14:30:00Z')

def candle(at,side=1,**values):
    row=dict(available_at=pd.Timestamp(at),session=pd.Timestamp(at).tz_convert('America/New_York').date().isoformat(),
        open=100.,high=101.,low=99.,close=100.,atr=2.,trend=1,trend_before=1,
        swing_low=98.,swing_high=104.,bos=0,choch=0,breakout=0,breakout_level=100.,
        flip=0,flip_level=100.,sweep=0,gap=0,gap_level=100.,gap_stop=98.,
        gap_active_long=False,gap_active_short=False,efficiency=.5,complete=True)
    row.update(values)
    if 'high' not in values:row['high']=max(row['high'],row['open'],row['close'])
    if 'low' not in values:row['low']=min(row['low'],row['open'],row['close'])
    if side<0:
        row.update(open=200-row['open'],close=200-row['close'],high=200-row['low'],low=200-row['high'],
            swing_low=200-row['swing_high'],swing_high=200-row['swing_low'],
            breakout_level=200-row['breakout_level'],flip_level=200-row['flip_level'],gap_stop=200-row['gap_stop'])
        for key in ['trend','trend_before','bos','choch','breakout','flip','sweep','gap']:row[key]*=-1
        row['gap_active_long'],row['gap_active_short']=row['gap_active_short'],row['gap_active_long']
    return row

def tables(side=1,at=AT):
    at=pd.Timestamp(at)
    return {'15m':[candle(at-pd.Timedelta(minutes=15),side,close=99.5),candle(at,side,breakout=1,close=100.5)],
        '5m':[candle(at-pd.Timedelta(minutes=5),side,close=100.5),candle(at,side),candle(at+pd.Timedelta(minutes=5),side,close=100.5)]}

def select(monkeypatch,charts,side=1,calendar=None,**changes):
    cfg=Strategy(**(dict(family='breakout',timeframe='15m',trigger_timeframe='5m',confirmation='close_back',confirmation_window=2,stop_buffer=0)|changes))
    def supplied(minutes,tf):return pd.DataFrame(deepcopy(charts.get(tf,[])),columns=list(candle(AT)))
    monkeypatch.setattr(module,'aggregate',supplied)
    monkeypatch.setattr(module,'contexts',lambda frame,*args,**kwargs:frame)
    return module.generate_signals(pd.DataFrame(dict(symbol=['SPY'])),cfg,calendar),cfg

def check_signal(signal,cfg,setup_at,at,side,index=1,weight=1):
    assert signal.available_at==pd.Timestamp(at) and signal.setup_at==pd.Timestamp(setup_at)
    assert signal.side==side and signal.source_index==index and signal.weight==weight
    expected=hashlib.sha256(json.dumps(dict(symbol='SPY',setup_at=pd.Timestamp(setup_at).isoformat(),side=side,config=cfg.model_dump()),sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]
    assert signal.id==expected and signal.level==100 and signal.atr==2
    assert signal.stop==(98 if side>0 else 102) and signal.target_swing==(104 if side>0 else 96)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('window',range(1,25))
@pytest.mark.parametrize('inside',[True,False])
def test_every_waiting_window_admits_last_available_candle_but_not_the_next(monkeypatch,side,window,inside):
    charts=tables(side);trigger=[candle(AT-pd.Timedelta(minutes=5),side,close=101)]
    for i in range(window+1):trigger.append(candle(AT+pd.Timedelta(minutes=5*i),side,close=100.5 if i==(window-1 if inside else window) else 100))
    charts['5m']=trigger
    result,cfg=select(monkeypatch,charts,side,confirmation_window=window)
    if inside:
        assert len(result)==1;check_signal(result[0],cfg,AT,AT+pd.Timedelta(minutes=5*(window-1)),side)
    else:assert result==[]

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['none','close_back','rejection','engulfing','either','lower_bos'])
def test_all_modes_have_authored_first_confirmation_clock(monkeypatch,side,mode):
    charts=tables(side)
    if mode in {'rejection','either'}:charts['5m'][1]=candle(AT,side,open=100,close=101,low=99,high=101)
    if mode=='engulfing':
        charts['5m'][1]=candle(AT,side,open=101.1,close=100.1,high=101.2,low=100)
        charts['5m'][2]=candle(AT+pd.Timedelta(minutes=5),side,open=100.1,close=101.1,high=101.2,low=100)
    if mode=='lower_bos':charts['5m'][1]['bos']=-side;charts['5m'][2]['bos']=side
    result,cfg=select(monkeypatch,charts,side,confirmation=mode)
    expected=AT if mode in {'none','rejection','either'} else AT+pd.Timedelta(minutes=5)
    assert len(result)==1;check_signal(result[0],cfg,AT,expected,side)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode,geometry',[
    ('rejection',dict(open=100,close=101,low=99.01,high=101)),
    ('rejection',dict(open=100,close=100,low=100,high=100)),
    ('engulfing',dict(open=101.1,close=100.1,high=101.2,low=100)),
    ('engulfing',dict(open=100.01,close=101,high=101.1,low=99.9)),
    ('either',dict(open=101.1,close=100.1,high=101.2,low=100))])
def test_nonqualifying_wicks_bodies_and_zero_range_do_not_confirm(monkeypatch,side,mode,geometry):
    charts=tables(side);charts['5m'][0]=candle(AT-pd.Timedelta(minutes=5),side,open=100,close=101)
    charts['5m'][1]=candle(AT,side,**geometry)
    assert select(monkeypatch,charts,side,confirmation=mode,confirmation_window=1)[0]==[]

@pytest.mark.parametrize('side',[1,-1])
def test_either_accepts_engulfing_without_a_half_range_wick(monkeypatch,side):
    charts=tables(side);charts['5m'][0]=candle(AT-pd.Timedelta(minutes=5),side,open=100.1,close=101.1,high=101.2,low=100)
    charts['5m'][1]=candle(AT,side,open=100.1,close=101.1,high=101.2,low=100)
    result,_=select(monkeypatch,charts,side,confirmation='either',confirmation_window=1);assert len(result)==1 and result[0].available_at==AT

@pytest.mark.parametrize('side',[1,-1])
def test_either_accepts_rejection_without_directional_engulfing(monkeypatch,side):
    charts=tables(side);charts['5m'][1]=candle(AT,side,open=101,close=100,low=98,high=102)
    assert select(monkeypatch,charts,side,confirmation='engulfing',confirmation_window=1)[0]==[]
    result,_=select(monkeypatch,charts,side,confirmation='either',confirmation_window=1)
    assert len(result)==1 and result[0].available_at==AT

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('efficiency,allowed',[(.3,True),(.3-1e-12,False),(0,False)])
def test_choppiness_boundary_is_discriminating(monkeypatch,side,efficiency,allowed):
    charts=tables(side);charts['15m'][1]['efficiency']=efficiency
    assert bool(select(monkeypatch,charts,side,skip_choppy=True)[0]) is allowed

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('trend_filter',['setup','higher','daily'])
@pytest.mark.parametrize('state',['same','opposite','unavailable'])
def test_trend_filter_uses_only_the_last_known_completed_state(monkeypatch,side,trend_filter,state):
    charts=tables(side);key={'setup':'15m','higher':'1h','daily':'1d'}[trend_filter]
    if trend_filter=='setup':
        charts[key][1]['trend']=side if state=='same' else (-side if state=='opposite' else 0)
    else:
        known=AT if trend_filter=='higher' else pd.Timestamp('2026-10-02T20:00:00Z')
        future=AT+pd.Timedelta(hours=1) if trend_filter=='higher' else pd.Timestamp('2026-10-05T20:00:00Z')
        charts[key]=([] if state=='unavailable' else [candle(known,side,trend=1 if state=='same' else -1)])+[candle(future,side,trend=-1 if state=='same' else 1)]
    result,_=select(monkeypatch,charts,side,confirmation='none',trend_filter=trend_filter)
    assert bool(result) is (state=='same')

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('at,allowed',[
    ('2026-10-30T13:30:00Z',True),('2026-10-30T14:59:59Z',True),('2026-10-30T15:00:00Z',False),
    ('2026-11-02T14:30:00Z',True),('2026-11-02T15:59:59Z',True),('2026-11-02T16:00:00Z',False),
    ('2026-11-02T14:29:59Z',False)])
def test_open_session_uses_new_york_clock_across_dst(monkeypatch,side,at,allowed):
    # Selector boundary clocks are supplied inputs, not an assertion that an
    # aggregated RTH candle can close at09:30 or at fractional-minute offsets.
    assert bool(select(monkeypatch,tables(side,pd.Timestamp(at)),side,confirmation='none',session_filter='open')[0]) is allowed

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('gap_kind,allowed',[('none',False),('opposite',False),('same',True),('both',True),('new',True)])
def test_gap_filter_preserves_direction_and_simultaneous_opposite_gap(monkeypatch,side,gap_kind,allowed):
    charts=tables(side);row=charts['15m'][1]
    row['gap_active_long']=gap_kind=='both' or gap_kind==('same' if side>0 else 'opposite')
    row['gap_active_short']=gap_kind=='both' or gap_kind==('same' if side<0 else 'opposite')
    row['gap']=side if gap_kind=='new' else 0
    assert bool(select(monkeypatch,charts,side,gap_confluence=True)[0]) is allowed

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('previous',[0,1,-1])
def test_fresh_flip_requires_immediately_preceding_same_direction_break(monkeypatch,side,previous):
    charts=tables(side);charts['15m'][0]['breakout']=previous;charts['15m'][1]['flip']=side
    assert bool(select(monkeypatch,charts,side,family='flip_zone',fresh_breakout=True)[0]) is (previous==side)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('n',[3,5])
@pytest.mark.parametrize('end_of_day',[False,True])
@pytest.mark.parametrize('delta',[-1,0,1])
def test_run_filter_uses_prior_sessions_excludes_same_day_and_admits_equality(monkeypatch,side,n,end_of_day,delta):
    at=pd.Timestamp('2026-10-05T20:00:00Z') if end_of_day else AT;charts=tables(side,at)
    days=['2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02'];close=95+(5-n)+delta
    charts['1d']=[candle(day+'T20:00:00Z',side,close=95+i) for i,day in enumerate(days)]
    if end_of_day:charts['1d'].append(candle(at,side,close=close))
    # Future daily state must never contribute to the reference close.
    charts['1d'].append(candle('2026-10-06T20:00:00Z',side,close=1000))
    current=close if side>0 else 200-close
    charts['15m'][1].update(open=current,high=current+.5,low=current-.5,close=current,breakout_level=90 if side>0 else 110)
    assert bool(select(monkeypatch,charts,side,confirmation='none',skip_run_days=n)[0]) is (delta<=0)

@pytest.mark.parametrize('mode',['skip','half'])
def test_news_requires_explicit_calendar_before_any_context_calculation(monkeypatch,mode):
    def forbidden(*args,**kwargs):pytest.fail('No context reads without calendar')
    monkeypatch.setattr(module,'aggregate',forbidden)
    with pytest.raises(DataError):module.generate_signals(pd.DataFrame(dict(symbol=['SPY'])),Strategy(news=mode))

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['trade','skip','half'])
@pytest.mark.parametrize('news_day',['2026-10-05','2026-10-06'])
def test_overnight_confirmation_news_policy_uses_the_signal_known_day(monkeypatch,side,mode,news_day):
    setup=pd.Timestamp('2026-10-05T20:00:00Z');at=pd.Timestamp('2026-10-06T14:00:00Z');charts=tables(side,setup)
    charts['5m']=[candle(at,side,close=101)]
    result,_=select(monkeypatch,charts,side,calendar={news_day},news=mode,confirmation_window=1)
    if mode=='skip' and news_day=='2026-10-06':assert result==[]
    else:assert len(result)==1 and result[0].available_at==at and result[0].weight==(.5 if mode=='half' and news_day=='2026-10-06' else 1)

@pytest.mark.parametrize('side',[1,-1])
def test_overnight_run_filter_counts_prior_sessions_relative_to_confirmation_day(monkeypatch,side):
    setup=pd.Timestamp('2026-10-05T20:00:00Z');at=pd.Timestamp('2026-10-06T14:00:00Z');charts=tables(side,setup)
    charts['15m'][1]['breakout_level']=98 if side>0 else 102
    charts['5m']=[candle(at,side,close=99)]
    charts['1d']=[candle(day+'T20:00:00Z',side,close=100+i) for i,day in enumerate(['2026-10-01','2026-10-02','2026-10-05'])]
    result,_=select(monkeypatch,charts,side,skip_run_days=3,confirmation_window=1)
    assert len(result)==1 and result[0].available_at==at

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['close_back','rejection','engulfing','either'])
def test_real_minute_detector_and_confirmation_geometry(side,mode):
    frame,event=scenario('break_of_structure','1m',side);mirror=float(SPEC['mirror_about'])
    if mode in {'rejection','either'}:frame.loc[19,'low' if side>0 else 'high']=121.5 if side>0 else mirror-121.5
    if mode=='engulfing':
        frame.loc[19,'open']=114.9 if side>0 else mirror-114.9
        frame.loc[19,'low' if side>0 else 'high']=114.8 if side>0 else mirror-114.8
    cfg=Strategy(**(SPEC['config']|dict(family='break_of_structure',timeframe='1m',confirmation=mode,confirmation_window=1)))
    selected=[s for s in module.generate_signals(frame,cfg) if s.source_index==19 and s.side==side]
    assert len(selected)==1 and selected[0].available_at==event['available_at']
    mutated=frame.copy();mutated.loc[20:,'high']+=1000
    assert [s.json() for s in module.generate_signals(mutated,cfg) if s.available_at<=event['available_at']]==[s.json() for s in module.generate_signals(frame,cfg) if s.available_at<=event['available_at']]

@pytest.mark.parametrize('side',[1,-1])
def test_real_minute_news_weight_risk_and_exposure_match_independent_account(side):
    frame,event=scenario('break_of_structure','1m',side);accounts=[]
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
    portfolio=Portfolio(capital=10000,risk_fraction=.01,symbol_exposure=1,total_exposure=1,participation=1)
    for mode in ['trade','half','skip']:
        cfg=Strategy(**(SPEC['config']|dict(family='break_of_structure',timeframe='1m',news=mode)))
        candidates=module.generate_signals(frame,cfg,{event['start']})
        own=[s for s in candidates if s.source_index==19 and s.side==side]
        if mode=='skip':assert own==[];continue
        assert len(own)==1 and own[0].weight==(1 if mode=='trade' else .5)
        requests=[s.json()|dict(config_id=hashlib.sha256(json.dumps(cfg.model_dump(),sort_keys=True,separators=(',',':')).encode()).hexdigest()) for s in own]
        expected=execute(primitive(frame),requests,{requests[0]['config_id']:cfg.model_dump()},costs.model_dump(),portfolio.model_dump(),[],event['start'],event['end'])
        actual=simulate(frame,own,cfg,costs,portfolio,[],event['start'],event['end']);assert_parity(actual,expected)
        assert actual.trades;accounts.append(actual.trades[0]['entry_quantity'])
    assert 0<accounts[1]<accounts[0]

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('n',[3,5])
def test_insufficient_run_history_cannot_be_filled_with_future_sessions(monkeypatch,side,n):
    charts=tables(side);charts['1d']=[candle(pd.Timestamp('2026-10-01T20:00:00Z')+pd.Timedelta(days=i),side) for i in range(n-1)]
    charts['1d']=[r for r in charts['1d'] if r['available_at']<AT]
    charts['1d'].append(candle('2026-10-06T20:00:00Z',side))
    assert select(monkeypatch,charts,side,skip_run_days=n)[0]==[]

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('direction',['long','short','both'])
def test_direction_is_applied_to_the_authored_candidate(monkeypatch,side,direction):
    assert bool(select(monkeypatch,tables(side),side,direction=direction)[0]) is (direction=='both' or direction==('long' if side>0 else 'short'))

@pytest.mark.parametrize('which',['setup','trigger'])
def test_empty_completed_chart_is_a_valid_no_signal_result(monkeypatch,which):
    charts=tables();charts['15m' if which=='setup' else '5m']=[]
    assert select(monkeypatch,charts)[0]==[]

def test_engulfing_without_a_preceding_completed_body_cannot_confirm(monkeypatch):
    charts=tables();charts['5m']=[candle(AT,open=99,close=101,high=101,low=99)]
    assert select(monkeypatch,charts,confirmation='engulfing',confirmation_window=1)[0]==[]

@pytest.mark.parametrize('atr',[float('nan'),0,-1])
def test_undefined_or_nonpositive_atr_does_not_create_a_signal(monkeypatch,atr):
    charts=tables();charts['15m'][1]['atr']=atr
    assert select(monkeypatch,charts)[0]==[]

def test_nonfinite_stop_rejects_but_unknown_opposing_swing_stays_null(monkeypatch):
    charts=tables();charts['15m'][1]['swing_low']=float('nan')
    assert select(monkeypatch,charts)[0]==[]
    charts=tables();charts['15m'][1]['swing_high']=float('nan')
    result,_=select(monkeypatch,charts);assert len(result)==1 and result[0].target_swing is None

@pytest.mark.parametrize('side',[1,-1])
def test_real_daily_setup_confirmation_uses_the_last_completed_hour(side):
    frame,event=scenario('break_of_structure','1d',side)
    cfg=Strategy(**(SPEC['config']|dict(family='break_of_structure',timeframe='1d',confirmation='close_back',confirmation_window=1)))
    result=[s for s in module.generate_signals(frame,cfg) if s.source_index==19 and s.side==side]
    assert cfg.trigger=='1h' and len(result)==1 and result[0].available_at==event['available_at']

@pytest.mark.parametrize('closes,expected',[(np.ones(16)*100,0),(np.arange(16)+100,1)])
def test_real_context_efficiency_has_authored_flat_and_straight_path_values(closes,expected):
    bars=pd.DataFrame(dict(available_at=pd.date_range(AT,periods=len(closes),freq='min'),session='2026-10-05',open=closes,high=closes+.1,low=closes-.1,close=closes))
    actual=module.contexts(bars,Strategy(timeframe='1m'))
    assert actual.iloc[10:].efficiency.tolist()==[expected]*6
