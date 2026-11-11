"""Authored borrowing expectations; no production-generated golden outputs."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from decimal import Decimal,localcontext
import pandas as pd
import pytest
from backend.lab.config import Costs,Strategy,Portfolio,identity
from backend.lab.data import Action,prepare,normalize
from backend.lab.engine import simulate
from test_reference_execution import rows,sig,run_both,assert_parity,primitive,ZERO,ACCOUNT,CFG
from conftest import minute_frame


def scenario(**updates):
    return dict(name='Authored borrowing',start='2026-11-04',end='2026-11-04',symbols=['SPY'],
        complete=True,mode='synthetic',events=[])|updates


def event(at,rate=.365,available=True,recall=False,symbol='SPY'):
    return dict(symbol=symbol,effective_at=at,annual_rate=rate,available=available,recall=recall)


@pytest.mark.parametrize('change',[
    dict(name=' '),dict(name='bad\x00name'),dict(start=1793746800),dict(end='2026-11-03'),
    dict(symbols=[]),dict(symbols=['SPY','SPY']),dict(symbols=['spy']),dict(mode='historical_proven'),
    dict(events=[event('2026-11-04T14:31:00')]),dict(events=[event('2026-11-04T14:31:01Z')]),
    dict(events=[event('2026-11-04T14:31:00Z',rate=float('inf'))]),
    dict(events=[event('2026-11-04T14:31:00Z',rate=-.1)]),dict(events=[event('2026-11-04T14:31:00Z',available='false')]),
    dict(events=[event('2026-11-04T14:31:00Z',rate=True)]),dict(events=[event('2026-11-04T14:31:00Z',rate='0.03')]),
    dict(events=[event('2026-11-04T14:31:00Z',recall=True)]),
    dict(events=[event('2026-11-04T14:31:00Z',symbol='QQQ')]),
    dict(events=[event('2026-11-03T14:31:00Z')]),
    dict(events=[event('2026-11-04T14:31:00Z'),event('2026-11-04T09:31:00-05:00')]),
])
def test_invalid_borrow_schema(change):
    from backend.lab.borrow import BorrowScenario
    with pytest.raises(ValueError):BorrowScenario(**scenario(**change))


def test_clock_bounds_exact_state_future_prefix_and_rate_seconds():
    from backend.lab.borrow import BorrowScenario,BorrowSchedule
    spec=BorrowScenario(**scenario(events=[event('2026-11-04T14:32:00Z',rate=.73)]))
    clock=BorrowSchedule(spec,.365,True);clock.validate(['SPY'],'2026-11-04','2026-11-04')
    assert clock.state('SPY',datetime.fromisoformat('2026-11-04T14:31:00+00:00'))==(True,.365,False)
    assert clock.state('SPY',datetime.fromisoformat('2026-11-04T14:32:00+00:00'))==(True,.73,False)
    first=datetime.fromisoformat('2026-11-04T14:31:00+00:00');end=datetime.fromisoformat('2026-11-04T14:34:00+00:00')
    assert clock.rate_seconds('SPY',first,end)==pytest.approx(.365*60+.73*120)
    for symbols,coverage_start,coverage_end in [(['QQQ'],'2026-11-04','2026-11-04'),(['SPY'],'2026-11-03','2026-11-04')]:
        with pytest.raises(ValueError):clock.validate(symbols,coverage_start,coverage_end)
    with pytest.raises(ValueError):BorrowSchedule(BorrowScenario(**scenario(complete=False)),0,True).validate(['SPY'],'2026-11-04','2026-11-04')
    with pytest.raises(ValueError):clock.state('SPY',datetime(2026,11,4,14,31))
    later=BorrowSchedule(BorrowScenario(**scenario(events=spec.model_dump()['events']+[event('2026-11-04T14:34:00Z',rate=5)])),.365,True)
    assert later.rate_seconds('SPY',first,end)==clock.rate_seconds('SPY',first,end)


def test_hand_authored_49_share_piecewise_minute_financing_and_reference():
    frame=rows(4);short=sig(frame,-1,stop=102)
    costs=ZERO.model_copy(update={}).model_dump()|dict(borrow_scenario=scenario(events=[event('2026-11-04T14:31:00Z'),event('2026-11-04T14:32:00Z',rate=.73)]))
    actual,expected=run_both(frame,[short],costs=Costs(**costs))
    assert len(actual.trades)==1 and actual.trades[0]['entry_quantity']==49
    with localcontext() as context:
        context.prec=50
        charge=Decimal(4900)*(Decimal('.365')*60+Decimal('.73')*120)/Decimal(365*86400)
    assert abs(expected['trades'][0]['borrow']-charge)<Decimal('1e-30')
    assert abs(Decimal(str(actual.trades[0]['net_pnl']))+charge)<Decimal('1e-7')
    assert_parity(actual,expected)


@pytest.mark.parametrize('entry',['next_open','same_close','limit'])
@pytest.mark.parametrize('side',[-1,1])
def test_entry_stage_availability_and_unaffected_longs(entry,side):
    frame=rows(4);cfg=CFG.model_copy(update=dict(entry=entry))
    rule=scenario(events=[event('2026-11-04T14:31:00Z',available=False)])
    actual,expected=run_both(frame,[sig(frame,side)],cfg,costs=Costs(**(ZERO.model_dump()|dict(borrow_scenario=rule))))
    if side<0:assert actual.trades==[] and actual.rejected==[dict(id='known',reason='Short borrow unavailable')]
    elif entry!='limit':assert actual.trades and actual.trades[0]['borrow']==0
    assert_parity(actual,expected)


def test_recall_market_exit_precedes_gap_stop_and_availability_alone_keeps_loan():
    frame=rows(4);frame.loc[2,['open','high','low','close']]=[105,105.1,104.9,105]
    short=sig(frame,-1,stop=102)
    for recalled in [False,True]:
        rule=scenario(events=[event('2026-11-04T14:32:00Z',available=False,recall=recalled)])
        actual,expected=run_both(frame,[short],costs=Costs(**(ZERO.model_dump()|dict(borrow_scenario=rule))))
        assert actual.trades[0]['exit_reason']==('borrow_recall' if recalled else 'gap_stop')
        assert actual.trades[0]['exit_price']==(105 if recalled else 105.01)
        assert_parity(actual,expected)


@pytest.mark.parametrize('with_actions',[False,True])
def test_weekend_rate_integral_and_recall_latch_after_clearance(with_actions):
    fri=minute_frame('2026-11-06').iloc[-2:].copy();mon=minute_frame('2026-11-09').iloc[:2].copy()
    for part in [fri,mon]:part[['open','close']]=100.;part['high']=100.1;part['low']=99.9
    if with_actions:mon[['open','close']]=52.5;mon['high']=52.6;mon['low']=52.4
    else:mon[['open','close']]=105.;mon['high']=105.1;mon['low']=104.9
    actions=[Action('SPY','2026-11-09','split',2),Action('SPY','2026-11-09','dividend',.5)] if with_actions else []
    frame=prepare(normalize(pd.concat([fri,mon],ignore_index=True))[0],actions)
    rule=scenario(start='2026-11-06',end='2026-11-09',events=[
        event('2026-11-07T00:00:00Z',rate=.73),
        event('2026-11-08T12:00:00Z',rate=.73,available=False,recall=True),
        event('2026-11-09T14:29:00Z',rate=.73)])
    costs=Costs(**(ZERO.model_dump()|dict(borrow_annual=.365,borrow_scenario=rule)))
    actual,expected=run_both(frame,[sig(frame,-1,stop=110)],costs=costs,actions=actions)
    # Risk is100 /10.01 =>9 shares, independently specified before either implementation.
    with localcontext() as context:
        context.prec=50
        charge=Decimal(900)*(Decimal('.365')*10860+Decimal('.73')*225000)/Decimal(365*86400)
    trade=actual.trades[0];assert trade['entry_quantity']==9 and trade['exit_reason']=='borrow_recall'
    assert trade['exit_at']=='2026-11-09T14:30:00+00:00'
    assert trade['exit_quantity']==(18 if with_actions else 9)
    assert trade['distributions']==(-9 if with_actions else 0)
    assert abs(expected['trades'][0]['borrow']-charge)<Decimal('1e-30')
    assert_parity(actual,expected)


def test_availability_loss_without_recall_and_future_event_do_not_rewrite_existing_loan():
    frame=rows(4);short=sig(frame,-1,stop=110)
    a=scenario(events=[event('2026-11-04T14:32:00Z',available=False)])
    b=deepcopy(a);b['events'].append(event('2026-11-04T15:00:00Z',available=False,recall=True,rate=5))
    books=[]
    for rule in [a,b]:
        actual,expected=run_both(frame,[short],costs=Costs(**(ZERO.model_dump()|dict(borrow_annual=.365,borrow_scenario=rule))))
        assert_parity(actual,expected);assert actual.trades[0]['exit_reason']=='end_of_window';books.append(actual)
    assert books[0].trades==books[1].trades and books[0].ledger==books[1].ledger


def test_shared_symbols_and_rules_recall_each_short_but_preserve_long_accounts():
    spy=rows(5);qqq=rows(5,symbol='QQQ');frame=pd.concat([spy,qqq],ignore_index=True)
    cfg2=CFG.model_copy(update={'target':'3R'});signals=[];mapping={}
    for symbol,part,side,stop in [('SPY',spy,-1,103),('QQQ',qqq,1,98)]:
        for i,cfg in enumerate([CFG,cfg2]):
            s=sig(part,side,stop=stop,name=symbol+str(i));signals.append(s);mapping[s.id]=cfg
    rule=scenario(symbols=['SPY','QQQ'],events=[event('2026-11-04T14:32:00Z',rate=.73,available=False,recall=True),event('2026-11-04T14:32:00Z',symbol='QQQ',available=False)])
    costs=Costs(**(ZERO.model_dump()|dict(borrow_annual=.365,borrow_scenario=rule)))
    account=ACCOUNT.model_copy(update=dict(risk_fraction=.005,symbol_exposure=.5))
    actual,expected=run_both(frame,signals,costs=costs,account=account,strategy_map=mapping)
    assert len(actual.trades)==4 and {t['side'] for t in actual.trades}=={-1,1}
    assert all(t['exit_reason']=='borrow_recall' for t in actual.trades if t['side']<0)
    assert all(t['exit_reason']=='end_of_window' and t['borrow']==0 for t in actual.trades if t['side']>0)
    assert sum(t['borrow'] for t in actual.trades)>0
    assert_parity(actual,expected)


def test_clock_error_and_declared_input_bounds():
    from backend.lab.borrow import BorrowScenario,BorrowSchedule
    clock=BorrowSchedule(scenario(),.03,True)
    at=datetime.fromisoformat('2026-11-04T14:30:00+00:00')
    with pytest.raises(ValueError):clock.state('QQQ',at)
    with pytest.raises(ValueError):clock.recalled('QQQ',at,at)
    with pytest.raises(ValueError):clock.recalled('SPY',at,at-pd.Timedelta(minutes=1))
    with pytest.raises(ValueError):clock.rate_seconds('SPY',at,at-pd.Timedelta(minutes=1))
    assert clock.rate_seconds('SPY',at,at)==0 and not clock.recalled('SPY',at,at)
    for changes in [dict(start='2026-13-01'),dict(start='2026-1-01'),dict(end='2038-01-01'),dict(events=[event('2026-11-04T14:30:00Z')]*10001)]:
        with pytest.raises(ValueError):BorrowScenario(**scenario(**changes))
