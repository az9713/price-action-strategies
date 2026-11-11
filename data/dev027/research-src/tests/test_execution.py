from dataclasses import replace
from decimal import Decimal
import pandas as pd
import pytest
from backend.lab.config import Strategy,Costs,Portfolio
from backend.lab.data import normalize,prepare,Action
from backend.lab.signals import Signal
from backend.lab.engine import simulate
from conftest import minute_frame

ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=10000,risk_fraction=.01,symbol_exposure=1,total_exposure=1,participation=1)
CFG=Strategy(timeframe='1m',swing_strength=2,max_hold=0,stop_buffer=0)

def execution_rows(): return prepare(normalize(minute_frame().iloc[:4])[0])
def signal(rows,side=1,at=1,stop=None):
    return Signal('manual', 'SPY',rows.iloc[at].timestamp,side,100.,1.,stop if stop is not None else (98. if side==1 else 102.),None,1.,rows.iloc[at].timestamp,0)

def reconcile(result):
    # Independent cents-level financial identity, not a call back into engine accounting.
    pnl=sum(Decimal(str(t['net_pnl'])) for t in result.trades)
    final=Decimal(str(result.equity[-1]['equity']))
    assert abs(final-Decimal('10000')-pnl)<Decimal('0.000001')
    cash=Decimal('10000')
    for event in result.ledger:
        assert abs(cash-Decimal(str(event['cash_before'])))<Decimal('0.000001')
        cash+=Decimal(str(event['cash_change']))
        assert abs(cash-Decimal(str(event['cash_after'])))<Decimal('0.000001')

@pytest.mark.parametrize('side',[1,-1])
def test_target_and_mirrored_short(side):
    rows=execution_rows()
    rows.loc[2,'high']=102.02 if side==1 else 100.1
    rows.loc[2,'low']=99.9 if side==1 else 97.98
    actual=simulate(rows,[signal(rows,side)],CFG,ZERO,ACCOUNT)
    trade=actual.trades[0]
    assert trade['entry_quantity']==49 and trade['exit_reason']=='target'
    assert trade['net_pnl']==pytest.approx(98)
    assert trade['entry_at']==rows.iloc[1].timestamp.isoformat()
    reconcile(actual)

def test_ambiguous_bar_stop_first_and_risk_reserve():
    rows=execution_rows();rows.loc[2,['high','low']]=[103,97]
    actual=simulate(rows,[signal(rows)],CFG,ZERO,ACCOUNT)
    assert actual.trades[0]['exit_reason']=='stop'
    assert actual.trades[0]['net_pnl']==pytest.approx(-98.49)
    assert actual.trades[0]['net_pnl']>=-100
    reconcile(actual)

def test_gap_stop_fills_at_open_worse_not_stop():
    rows=execution_rows();rows.loc[2,['open','high','low','close']]=[95,96,94,95]
    actual=simulate(rows,[signal(rows)],CFG,ZERO,ACCOUNT)
    assert actual.trades[0]['exit_reason']=='gap_stop'
    assert actual.trades[0]['exit_price']==pytest.approx(94.99)
    assert actual.trades[0]['net_pnl']==pytest.approx(-245.49)
    reconcile(actual)

def test_limit_needs_trade_through_and_does_not_credit_ambiguous_target():
    rows=execution_rows();cfg=CFG.model_copy(update={'entry':'limit'})
    rows.loc[1,'low']=100.;rows.loc[1,'high']=100.1
    rows.loc[2,'low']=99.98;rows.loc[2,'high']=103
    actual=simulate(rows,[signal(rows)],cfg,ZERO,ACCOUNT)
    assert actual.trades[0]['entry_at']==rows.iloc[2].timestamp.isoformat()
    assert actual.trades[0]['exit_reason']=='end_of_window'
    reconcile(actual)

def test_same_close_cannot_use_earlier_intrabar_prices():
    rows=execution_rows();rows.loc[0,['high','low']]=[103,97]
    cfg=CFG.model_copy(update={'entry':'same_close'})
    actual=simulate(rows,[signal(rows)],cfg,ZERO,ACCOUNT)
    assert actual.trades[0]['exit_reason']=='end_of_window'
    assert actual.ledger[0]['timestamp']==rows.iloc[1].timestamp.isoformat()
    reconcile(actual)

def test_borrow_unavailable_rejects():
    rows=execution_rows()
    actual=simulate(rows,[signal(rows,-1)],CFG,ZERO.model_copy(update={'borrow_available':False}),ACCOUNT)
    assert not actual.trades and 'borrow unavailable' in actual.rejected[0]['reason']
    assert actual.equity[-1]['equity']==10000

def test_position_exclusivity_and_no_future_entry():
    rows=execution_rows();s=signal(rows)
    actual=simulate(rows,[s,replace(s,id='second',available_at=rows.iloc[2].timestamp)],CFG,ZERO,ACCOUNT)
    assert len(actual.trades)==1 and actual.rejected[0]['reason']=='Position already open'
    reconcile(actual)

def test_short_borrow_elapsed_time_independent_expected():
    rows=execution_rows();costs=ZERO.model_copy(update={'borrow_annual':.365})
    actual=simulate(rows,[signal(rows,-1)],CFG,costs,ACCOUNT)
    # Entry at 14:31, final exit at 14:34: three minutes of 49*$100 notional.
    expected=Decimal(49)*Decimal(100)*Decimal('.365')*Decimal(3)/(Decimal(365)*Decimal(1440))
    assert actual.trades[0]['borrow']==pytest.approx(float(expected))
    reconcile(actual)

@pytest.mark.parametrize('side',[1,-1])
def test_split_and_distribution_preserve_accounting(side):
    a=minute_frame('2026-11-04').iloc[:3]
    b=minute_frame('2026-11-05',close=[50]).iloc[:3]
    actions=[Action('SPY','2026-11-05','split',2),Action('SPY','2026-11-05','dividend',1,'2026-11-06')]
    rows=prepare(normalize(pd.concat([a,b]))[0],actions)
    actual=simulate(rows,[signal(rows,side)],CFG,ZERO,ACCOUNT,actions)
    assert actual.trades[0]['exit_quantity']==98
    assert actual.trades[0]['gross_pnl']==pytest.approx(0)
    assert actual.trades[0]['distributions']==side*98
    assert actual.equity[-1]['receivables']==side*98
    reconcile(actual)

def test_cancel_is_terminal_exception_not_fake_complete():
    with pytest.raises(InterruptedError): simulate(execution_rows(),[],CFG,ZERO,ACCOUNT,cancel=lambda:True)

def test_nonpositive_stop_and_target_are_rejected():
    rows=execution_rows()
    actual=simulate(rows,[signal(rows,stop=-1)],CFG,ZERO,ACCOUNT)
    assert not actual.trades and actual.rejected[0]['reason']=='Invalid stop after fill/gap'
    short=simulate(rows,[signal(rows,-1,stop=250)],CFG,ZERO,ACCOUNT)
    assert not short.trades and 'positive tradable price' in short.rejected[0]['reason']
