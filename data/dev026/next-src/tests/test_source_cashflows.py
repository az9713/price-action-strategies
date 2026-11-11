"""Canonical actual-fill reconciliation contracts, authored before the auditor."""
import importlib,importlib.util
from decimal import Decimal
from fractions import Fraction
import pytest


def test_original_source_cashflow_auditor_is_implemented():
    assert importlib.util.find_spec('backend.lab.source_cashflows') is not None, 'Canonical original executed-cashflow audit is not implemented.'


@pytest.fixture
def audit():return importlib.import_module('backend.lab.source_cashflows')


@pytest.mark.parametrize('side,exit_price',[(1,99.9),(1,100.1),(-1,99.9),(-1,100.1)])
def test_actual_filled_prices_have_independent_exact_fraction_profit(audit,side,exit_price):
    from conftest import minute_frame
    from backend.lab.data import normalize,prepare
    from backend.lab.config import Costs
    regular=prepare(normalize(minute_frame('2026-11-04'))[0])
    at=regular.iloc[20].timestamp;until=regular.iloc[25].timestamp
    net=side*49*(exit_price-100.)
    trade=dict(id='source',symbol='SPY',side=side,entry_at=at.isoformat(),exit_at=until.isoformat(),entry_price=100.,exit_price=exit_price,entry_quantity=49,exit_quantity=49,fees=0.,borrow=0.,distributions=0.,gross_pnl=net,net_pnl=net)
    trace=dict(trade_id='source',entry_order_type='next_open')
    costs=Costs(commission_per_share=0,minimum_commission=0,fixed_fee_per_order=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
    result=audit.audit_fills(regular,[trade],[trace],costs,[], 'a'*64)
    expected=Fraction(side)*49*(Fraction(str(exit_price))-100)
    assert Decimal(result['net_profit'])==Decimal(expected.numerator)/Decimal(expected.denominator)
    assert Decimal(result['reported_net_profit'])==Decimal(str(net))
    assert len(result['trades'])==1


def observed(days=('2026-11-04',), side=1, order='next_open', costs=None, actions=(), start=20, stop=None):
    """Real original fills; expected amounts below are independently authored."""
    import pandas as pd
    from backend.lab.data import normalize,prepare
    from backend.lab.engine import simulate
    from test_reference_execution import CFG,ZERO,ACCOUNT,sig
    from conftest import minute_frame
    data=pd.concat([minute_frame(day) for day in days],ignore_index=True)
    data[['open','high','low','close']]=[100.,100.1,99.9,100.]
    if actions:
        for action in actions:
            if action.kind=='split':
                data.loc[data.timestamp.dt.strftime('%Y-%m-%d')>=action.ex_date,['open','high','low','close']]/=action.value
    regular=prepare(normalize(data)[0],actions)
    config=CFG.model_copy(update=dict(entry=order,flat_at_close=False,target='swing'))
    signal=sig(regular,side=side,at=start,stop=stop if stop is not None else 10. if side==1 else 190.,target=190. if side==1 else 10.)
    cost=costs or ZERO
    result=simulate(regular,[signal],config,cost,ACCOUNT,actions)
    assert len(result.trades)==1
    return regular,result,cost


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('order',['next_open','same_close','limit'])
def test_every_fee_reconciles_actual_original_observed_fills(audit,side,order):
    from backend.lab.config import Costs
    costs=Costs(commission_per_share=.017,minimum_commission=.031,fixed_fee_per_order=.027,sell_fee_per_dollar=.00013,spread_bps=3,slippage_bps=2,borrow_annual=0)
    data,original,cost=observed(side=side,order=order,costs=costs)
    result=audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'b'*64)
    t=original.trades[0]; q=Fraction(str(t['entry_quantity'])); p=Fraction(str(t['entry_price'])); x=Fraction(str(t['exit_price']))
    fees=max(Fraction('.031'),q*Fraction('.017'))*2+Fraction('.027')*2+q*(x if side==1 else p)*Fraction('.00013')
    expected=side*q*(x-p)-fees
    assert Fraction(result['trades'][0]['fees'])==fees
    assert Fraction(result['net_profit'])==expected
    assert original.trades[0]==t


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('ratio',[.5,2.])
def test_split_fractional_shares_and_unpaid_dividends_use_observed_entitlements(audit,side,ratio):
    from backend.lab.data import Action
    actions=[Action('SPY','2026-11-05','dividend',.37,'2026-11-10'),Action('SPY','2026-11-05','split',ratio)]
    data,original,cost=observed(days=('2026-11-04','2026-11-05'),side=side,actions=actions,start=389)
    result=audit.audit_fills(data,original.trades,original.entry_traces,cost,actions, 'c'*64)
    trade=original.trades[0];q=Fraction(str(trade['entry_quantity']))*Fraction(str(ratio))
    expected=side*q*Fraction('.37')
    assert Fraction(result['trades'][0]['exit_quantity'])==q
    assert Fraction(result['trades'][0]['distributions'])==expected
    assert Fraction(result['net_profit'])==expected


@pytest.mark.parametrize('order',['next_open','same_close'])
def test_weekend_dst_piecewise_borrow_has_independent_calendar_total(audit,order):
    from backend.lab.config import Costs
    from decimal import localcontext
    import pandas as pd
    scenario=dict(name='Independent calendar total',mode='synthetic',start='2026-10-30',end='2026-11-02',symbols=['SPY'],complete=True,
        events=[dict(symbol='SPY',effective_at='2026-11-01T00:00:00+00:00',available=True,annual_rate=.2,recall=False)])
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=.1,borrow_scenario=scenario)
    data,original,cost=observed(days=('2026-10-30','2026-11-02'),side=-1,order=order,costs=costs,start=389)
    result=audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'd'*64)
    trade=original.trades[0];at=pd.Timestamp(trade['entry_at']);end=pd.Timestamp(trade['exit_at']);changed=pd.Timestamp('2026-11-01T00:00:00Z')
    expected=Fraction(str(trade['entry_quantity']))*100*(Fraction('.1')*int((changed-at).total_seconds())+Fraction('.2')*int((end-changed).total_seconds()))/(365*86400)
    with localcontext() as context:
        context.prec=100
        hand=Decimal(expected.numerator)/Decimal(expected.denominator)
        # Decimal80 per-accrual rounding is separate from the original float reconciliation.
        assert abs(Decimal(result['trades'][0]['borrow'])-hand)<Decimal('1e-72')
    assert Decimal(result['net_profit'])<0


def test_same_close_uses_observed_closing_mark_for_first_borrow_interval(audit):
    from backend.lab.config import Costs
    from backend.lab.engine import simulate
    from test_reference_execution import CFG,ACCOUNT,sig
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=.12)
    data,_,_=observed(side=-1,costs=costs)
    data.loc[19,'close']=103.
    cfg=CFG.model_copy(update=dict(entry='same_close',target='swing',flat_at_close=False))
    original=simulate(data,[sig(data,side=-1,at=20,stop=190.,target=10.)],cfg,costs,ACCOUNT)
    result=audit.audit_fills(data,original.trades,original.entry_traces,costs,[], 'e'*64)
    assert abs(Decimal(result['trades'][0]['borrow'])-Decimal(str(original.trades[0]['borrow'])))<Decimal('1e-7')


@pytest.mark.parametrize('fault',['missing','hash','input','policy','cohort','numeric','arithmetic','total','raw','difference'])
def test_saved_audit_corruption_and_self_rehashed_arithmetic_are_refused(audit,fault):
    import copy
    from backend.lab.config import identity
    data,original,cost=observed()
    value=audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'f'*64)
    bad=copy.deepcopy(value)
    if fault=='missing':bad=None
    elif fault=='hash':bad['audit_sha256']='0'*64
    elif fault=='input':bad['input_hash']='0'*64
    elif fault=='policy':bad['policy']='inferred'
    elif fault=='cohort':bad['trades']=[]
    elif fault=='numeric':bad['trades'][0]['net_pnl']=0
    elif fault=='arithmetic':bad['trades'][0]['net_pnl']='1E-8'
    elif fault=='total':bad['net_profit']='1E-8'
    elif fault=='raw':bad['reported_net_profit']='1E-8'
    else:bad['difference']='1E-8'
    if isinstance(bad,dict) and fault!='hash':bad['audit_sha256']=identity({k:v for k,v in bad.items() if k!='audit_sha256'})
    with pytest.raises(ValueError):
        audit.validate_audit(bad,original.trades,original.entry_traces,cost.model_dump(),'f'*64)


def test_empty_audit_and_zero_duration_do_not_load_market_rows(audit):
    from backend.lab.config import Costs
    class NoPrices:
        def __getattr__(self,name):raise AssertionError('No candidate price read is permitted.')
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
    value=audit.audit_fills(NoPrices(),[],[],costs,[], 'a'*64)
    assert value['trades']==[] and Decimal(value['net_profit'])==0
    at='2026-11-04T14:30:00+00:00'
    trade=dict(id='instant',symbol='SPY',side=1,entry_at=at,exit_at=at,entry_price=100.,exit_price=100.,entry_quantity=1,exit_quantity=1,gross_pnl=0.,net_pnl=0.,fees=0.,borrow=0.,distributions=0.)
    assert Decimal(audit.audit_fills(NoPrices(),[trade],[dict(trade_id='instant',entry_order_type='next_open')],costs,[], 'a'*64)['net_profit'])==0


def test_audit_cancellation_duplicate_cohort_and_unreconciled_original_refuse(audit):
    from backend.lab.config import identity
    data,original,cost=observed()
    with pytest.raises(InterruptedError):audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64,lambda:True)
    with pytest.raises(ValueError):audit.audit_fills(data,original.trades*2,original.entry_traces*2,cost,[], 'a'*64)
    original.trades[0]['net_pnl']=1.
    with pytest.raises(ValueError,match='reconcile'):audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64)


@pytest.mark.parametrize('field,value',[('side',True),('entry_quantity',0),('entry_quantity',1.5),('entry_price',0),('exit_price',0),('entry_price',True),('exit_price',float('inf')),('entry_at','2026-11-04T14:30:00'),('exit_at','2026-11-03T14:30:00Z')])
def test_invalid_observed_cashflow_inputs_cannot_be_certified(audit,field,value):
    data,original,cost=observed()
    original.trades[0][field]=value
    with pytest.raises(ValueError):audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64)


def test_required_borrow_market_clock_refuses_missing_entry_and_duplicates(audit):
    import pandas as pd
    from backend.lab.config import Costs
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=.12)
    data,original,cost=observed(side=-1,costs=costs)
    with pytest.raises(ValueError,match='mark'):
        audit.audit_fills(data.iloc[21:],original.trades,original.entry_traces,cost,[], 'a'*64)
    with pytest.raises(ValueError,match='duplicate'):
        audit.audit_fills(pd.concat([data,data.iloc[[20]]]),original.trades,original.entry_traces,cost,[], 'a'*64)
    original.trades[0]['entry_at']='2026-11-04T14:30:00Z'
    original.entry_traces[0]['entry_order_type']='same_close'
    with pytest.raises(ValueError,match='mark'):
        audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64)


@pytest.mark.parametrize('fault',['record_shape','gross','fees','borrow','trade_id','duplicate_trace'])
def test_saved_cashflow_components_must_reconcile_and_recompute(audit,fault):
    from backend.lab.config import identity
    data,original,cost=observed()
    value=audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64)
    if fault=='record_shape':value['trades'][0]['extra']='0'
    elif fault=='trade_id':value['trades'][0]['id']='other'
    elif fault=='duplicate_trace':
        with pytest.raises(ValueError):audit.audit_fills(data,original.trades,original.entry_traces*2,cost,[], 'a'*64)
        return
    else:value['trades'][0][fault if fault!='gross' else 'gross_pnl']='1E-8'
    value['audit_sha256']=identity({k:v for k,v in value.items() if k!='audit_sha256'})
    with pytest.raises(ValueError):audit.validate_audit(value,original.trades,original.entry_traces,cost.model_dump(),'a'*64)


def test_open_boundary_after_overnight_split_is_audited_before_exit(audit):
    from backend.lab.config import Costs
    from backend.lab.data import Action
    from backend.lab.engine import simulate
    from test_reference_execution import CFG,ACCOUNT,sig
    actions=[Action('SPY','2026-11-05','split',2.)]
    cost=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=.12)
    data,_,_=observed(days=('2026-11-04','2026-11-05'),side=-1,costs=cost,actions=actions,start=389)
    data.loc[390:,['open','high','low','close']]=[60.,60.1,59.9,60.]
    cfg=CFG.model_copy(update=dict(flat_at_close=False,target='swing'))
    original=simulate(data,[sig(data,side=-1,at=389,stop=110.,target=10.)],cfg,cost,ACCOUNT,actions)
    assert original.trades[0]['exit_reason']=='gap_stop'
    result=audit.audit_fills(data,original.trades,original.entry_traces,cost,actions,'a'*64)
    assert Decimal(result['trades'][0]['exit_quantity'])==2*Decimal(str(original.trades[0]['entry_quantity']))


def test_cancellation_during_observed_minute_audit_does_not_return_partial_baseline(audit):
    from backend.lab.config import Costs
    cost=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=.1)
    data,original,cost=observed(side=-1,costs=cost)
    calls=[]
    def cancel():
        calls.append(1)
        return len(calls)>=4
    with pytest.raises(InterruptedError):audit.audit_fills(data,original.trades,original.entry_traces,cost,[], 'a'*64,cancel)
    assert len(calls)==4
