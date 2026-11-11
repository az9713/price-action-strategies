"""Production exact-money boundaries, separate from legacy float input contracts."""
from decimal import Decimal
import importlib.util,os
from pathlib import Path
import pandas as pd
import pytest
from backend.lab.trade_twins import prepare_plan,SourceTrade,TwinMoment
from backend.lab.data import schedule

from backend.lab import trade_twin_results as grade

@pytest.fixture
def plan():
    opened,closed=schedule('2026-11-04','2026-11-04')['2026-11-04']
    source=SourceTrade(trade_id='precision-boundary',symbol='SPY',side=1,entry_at='2026-11-04T14:45:00+00:00',exit_at='2026-11-04T14:47:00+00:00',exit_boundary='close',entry_price=100.,entry_atr=1.,atr_available_at='2026-11-04T14:44:00+00:00',entry_stop=99.,entry_target=102.,quantity=10,net_profit=10000000000.)
    moment=TwinMoment(symbol='SPY',entry_at='2026-11-04T14:46:00+00:00',reference_price=100.,atr=1.,atr_available_at='2026-11-04T14:45:00+00:00')
    return prepare_plan([source],[moment],dict(SPY=[t.isoformat() for t in pd.date_range(opened,closed,freq='min',inclusive='left')]),'2026-11-04','2026-11-04','a'*64)

def rows(plan,amount='9999999999.9999999',count=10000):
    for index in range(count):yield dict(plan_hash=plan.plan_hash,seed=42,policy='barrier_capped_elapsed_v1',set_index=index,trade_count=len(plan.sources),state='completed',net_profit=amount,error=None,amount_encoding='canonical-decimal-v1')

@pytest.mark.parametrize('amount,exceedances',[('9999999999.9999999',0),('10000000000.0000001',10000),('10000000000.0',10000),('-0',0),('1E-26',0)])
def test_exact_large_profit_comparison_keeps_sub_float_differences(plan,amount,exceedances):
    result=grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',rows(plan,amount))
    assert result['state']=='completed' and result['complete_sets']==10000 and result['exceedances']==exceedances
    assert result['adapted_pass'] is (exceedances==0)
    if amount.startswith('9999'):assert float(amount)==10000000000. and Decimal(amount)<Decimal('10000000000.0')

@pytest.mark.parametrize('bad',[0.,1,True,'NaN','Infinity','-Infinity',' 0','+0','1e0','not-money','9'*1025])
def test_noncanonical_or_numeric_shortcuts_cannot_erase_precision(plan,bad):
    with pytest.raises(ValueError):grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',rows(plan,bad,count=1))

@pytest.mark.parametrize('exceedances',[499,500])
def test_source_threshold_ties_and_conditional_interval_remain_exact(plan,exceedances):
    def outcomes():
        for row in rows(plan):
            if row['set_index']<exceedances:row['net_profit']='10000000000.0'
            yield row
    result=grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',outcomes())
    assert result['exceedances']==exceedances and result['adapted_pass'] is (exceedances==499)
    assert result['raw_exceedance_fraction']==exceedances/10000
    assert result['plus_one_diagnostic']==(exceedances+1)/10001
    assert result['monte_carlo_interval_95'][0]<exceedances/10000<result['monte_carlo_interval_95'][1]

@pytest.mark.parametrize('fault',['failed','duplicate','wrong_hash','wrong_seed','wrong_policy','wrong_cohort','bool_ordinal','missing_encoding'])
def test_original_identity_and_failure_denominators_are_not_weakened(plan,fault):
    def outcomes():
        for row in rows(plan):
            if row['set_index']==123:
                if fault=='failed':row.update(state='failed',net_profit=None,error='Original failed candidate; no redraw.')
                elif fault=='duplicate':row['set_index']=122
                elif fault=='wrong_hash':row['plan_hash']='0'*64
                elif fault=='wrong_seed':row['seed']=41
                elif fault=='wrong_policy':row['policy']='fixed_elapsed_v1'
                elif fault=='wrong_cohort':row['trade_count']=0
                elif fault=='bool_ordinal':row['set_index']=True
                else:del row['amount_encoding']
            yield row
    if fault=='failed':
        result=grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',outcomes())
        assert result['state']=='failed' and result['failed_sets']==1 and result['adapted_pass'] is None and result['raw_exceedance_fraction'] is None
    else:
        with pytest.raises(ValueError):grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',outcomes())

def test_partial_and_cancelled_financial_results_cannot_pass(plan):
    result=grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',rows(plan,count=9999))
    assert result['state']=='incomplete' and result['adapted_pass'] is None
    with pytest.raises(InterruptedError):grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',rows(plan),lambda:True)

def test_cohort_baseline_sum_does_not_depend_on_default_decimal_context(plan):
    second=plan.sources[0].model_copy(update=dict(trade_id='tiny-source',net_profit=1e-30))
    exact=prepare_plan([*plan.sources,second],plan.moments,dict(plan.clocks),plan.start,plan.end,plan.parent_identity)
    result=grade.summarize_financial(exact,42,'barrier_capped_elapsed_v1',rows(exact,'10000000000.0'))
    assert result['exceedances']==0 and result['adapted_pass'] is True
    assert Decimal(result['real_profit'])==Decimal('10000000000.000000000000000000000000000001')

@pytest.mark.parametrize('values,expected',[([], '0'),(['1E+100','1E-100','-1E+100'],'1E-100'),(['1E-100','-1E+100','1E+100'],'1E-100'),(['10000000000.0','1E-30'],'10000000000.000000000000000000000000000001')])
def test_exact_finite_sum_retains_small_trades_and_cancellation(values,expected):
    assert grade.exact_total(values)==Decimal(expected)

@pytest.mark.parametrize('value',['NaN','Infinity','-Infinity'])
def test_nonfinite_amount_cannot_enter_a_complete_sum(value):
    with pytest.raises(ValueError):grade.exact_total([value])


def test_empty_original_cohort_and_unknown_policy_cannot_be_graded(plan):
    empty=prepare_plan([],[],{},plan.start,plan.end,plan.parent_identity)
    result=grade.summarize_financial(empty,42,'barrier_capped_elapsed_v1',[])
    assert result['state']=='ineligible' and result['adapted_pass'] is None
    with pytest.raises(ValueError):grade.summarize_financial(empty,42,'barrier_capped_elapsed_v1',rows(empty,count=1))
    with pytest.raises(ValueError):grade.summarize_financial(plan,42,'unknown-host-policy',[])


def test_cancel_during_grading_and_at_empty_result_return(plan):
    signaled=False;seen=0
    def outcomes():
        nonlocal signaled,seen
        for row in rows(plan):
            seen+=1
            if row['set_index']==123:signaled=True
            yield row
    with pytest.raises(InterruptedError):grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',outcomes(),lambda:signaled)
    assert seen==124
    calls=0
    def cancel():
        nonlocal calls
        calls+=1;return calls==2
    with pytest.raises(InterruptedError):grade.summarize_financial(plan,42,'barrier_capped_elapsed_v1',[],cancel)


def test_canonical_original_baseline_overrides_legacy_float_without_grading_epsilon(plan):
    from dataclasses import replace
    source=plan.sources[0].model_copy(update=dict(net_profit=-4.8999999999997215,net_profit_exact='-4.900'))
    exact=replace(plan,sources=(source,))
    result=grade.summarize_financial(exact,42,'barrier_capped_elapsed_v1',rows(exact,amount='-4.900'))
    assert result['real_profit']=='-4.900' and result['exceedances']==10000 and not result['adapted_pass']
    result=grade.summarize_financial(exact,42,'barrier_capped_elapsed_v1',rows(exact,amount='-4.900000000000000000000001'))
    assert result['exceedances']==0 and result['adapted_pass']


def test_mixed_source_precision_and_noncanonical_original_amounts_cannot_be_graded(plan):
    from dataclasses import replace
    from pydantic import ValidationError
    bad=plan.sources[0].model_dump()|dict(net_profit_exact=1.)
    with pytest.raises((ValueError,ValidationError)):SourceTrade(**bad)
    bad['net_profit_exact']='NaN'
    with pytest.raises(ValueError):SourceTrade(**bad)
    source=plan.sources[0].model_copy(update=dict(trade_id='other',net_profit_exact='0'))
    with pytest.raises(ValueError,match='precision'):
        grade.summarize_financial(replace(plan,sources=plan.sources+(source,)),42,'barrier_capped_elapsed_v1',[])
