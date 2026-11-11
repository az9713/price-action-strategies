"""Independently authored four-rate policy and nonlinear whole-share expectations."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal,localcontext
from types import SimpleNamespace
import pytest
from backend.lab.config import Costs,identity
from backend.lab.data import DataError
from backend.lab.engine import simulate
from backend.lab.metrics import summary
from backend.lab.research import core_hash,core_subject
from test_borrow import scenario,event
from test_reference_execution import rows,sig,primitive,assert_parity,ZERO,ACCOUNT,CFG
from verification.reference_execution import execute

RATES=[0,.03,.1,.3]


def nonlinear_inputs():
    frame=rows(5)
    frame.loc[3,['open','high','low','close']]=[100,101.1,99.9,101]
    frame.loc[4,['open','high','low','close']]=[101,101.1,100.9,101]
    signals=[sig(frame,-1,at=1,stop=102,name='first-short'),sig(frame,1,at=2,stop=98,name='later-long')]
    costs=Costs(**(ZERO.model_dump()|dict(borrow_scenario=scenario(events=[event('2026-11-04T14:32:00Z',rate=.2,available=False,recall=True)]))))
    account=ACCOUNT.model_copy(update={'capital':10050})
    return frame,signals,costs,account


def accounts():
    from backend.lab.sensitivity import cost_arms
    frame,signals,base,account=nonlinear_inputs();reports=[]
    for arm in cost_arms(base,CFG):
        costs=Costs(**arm['costs']);actual=simulate(frame,signals,CFG,costs,account,start='2026-11-04',end='2026-11-04')
        expected=execute(primitive(frame),[s.json()|dict(config_id=identity(CFG)) for s in signals],{identity(CFG):CFG.model_dump()},costs.model_dump(),account.model_dump(),start='2026-11-04',end='2026-11-04')
        assert_parity(actual,expected)
        rate=Decimal(str(arm['annual_rate']))
        with localcontext() as context:
            context.prec=50;charge=Decimal(5000)*rate*60/Decimal(365*86400)
        assert expected['trades'][0]['entry_quantity']==50
        assert expected['trades'][1]['entry_quantity']==(50 if not rate else 49)
        assert abs(expected['trades'][0]['borrow']-charge)<Decimal('1e-30')
        assert abs(sum(t['net_pnl'] for t in expected['trades'])-(Decimal(50 if not rate else 49)-charge))<Decimal('1e-30')
        reports.append(dict(report_type='single_strategy',config=CFG.model_dump(),config_id=identity(CFG),
            costs=costs.model_dump(),portfolio=account.model_dump(),core_hash=core_hash(),numerical_contract=core_subject(),
            dataset_id='a'*24,dataset_manifest_hash='b'*64,start='2026-11-04',end='2026-11-04',seed=42,
            news_dates=None,news_calendar=None,signals=actual.signals,trades=actual.trades,ledger=actual.ledger,equity=actual.equity,
            rejected=actual.rejected,metrics=summary(actual,account.capital),assumptions=actual.assumptions,
            provenance=dict(input_kind='synthetic',warmup_start='2026-11-04')))
    return base,reports


def strip_rates(value):
    result=deepcopy(value);result.pop('borrow_annual')
    if result['borrow_scenario']:
        for e in result['borrow_scenario']['events']:e.pop('annual_rate')
    return result


@pytest.mark.parametrize('with_scenario',[False,True])
def test_fixed_four_cost_arms_preserve_every_nonrate_input_and_original(with_scenario):
    from backend.lab.sensitivity import cost_arms
    spec=scenario(events=[event('2026-11-04T14:31:00Z',rate=1.2)]) if with_scenario else None
    original=Costs(borrow_annual=.7,borrow_available=False,borrow_scenario=spec);before=deepcopy(original.model_dump())
    arms=cost_arms(original,CFG)
    assert [a['annual_rate'] for a in arms]==RATES and [a['part'] for a in arms]==list(range(4))
    assert original.model_dump()==before
    for arm in arms:
        assert arm['costs']['borrow_annual']==arm['annual_rate']
        assert strip_rates(arm['costs'])==strip_rates(before)
        assert arm['costs_id']==identity(arm['costs'])
        assert arm['account_id']==identity(dict(strategy=CFG.model_dump(),costs=arm['costs']))
        if spec:assert all(e['annual_rate']==arm['annual_rate'] for e in arm['costs']['borrow_scenario']['events'])
    assert len({a['account_id'] for a in arms})==4
    arms[0]['costs']['minimum_commission']=9
    assert original.model_dump()==before and arms[1]['costs']['minimum_commission']==0


def test_independent_nonlinear_accounts_and_complete_daily_differences():
    from backend.lab.sensitivity import summarize_accounts
    base,reports=accounts();result=summarize_accounts(reports,base,CFG)
    assert len(result['arms'])==len(result['comparison_rows'])==4
    assert [r['annual_rate'] for r in result['comparison_rows']]==RATES
    assert result['comparison_rows'][0]['net_profit']==50
    for i,(row,report) in enumerate(zip(result['comparison_rows'],reports)):
        assert row['trades']==2 and row['short_trades']==1 and row['signals']==2
        assert row['net_profit']==report['metrics']['net_profit']
        assert row['borrow_paid']==pytest.approx(report['trades'][0]['borrow'],abs=1e-7)
        assert row['delta_from_zero']==pytest.approx(row['net_profit']-50,abs=1e-7)
        assert len(result['daily_differences'][i]['rows'])==1
        assert result['daily_differences'][i]['rows'][0]['difference']==pytest.approx(row['delta_from_zero'],abs=1e-7)
        if i:assert row['net_profit']<49 and abs(row['net_profit']-(50-row['borrow_paid']))>.99
    assert 'descriptive' in result['comparison_interpretation'].lower()


@pytest.mark.parametrize('fault',['count','cost','rate_order','config','dataset','calendar','seed','news','profit','equity','borrow_trade','borrow_ledger','nonfinite','signals','nonfinite_metric','missing_metric','nonnumeric_fee'])
def test_corrupt_or_incompatible_accounts_cannot_publish_comparison(fault):
    from backend.lab.sensitivity import summarize_accounts
    base,reports=accounts()
    if fault=='count':reports.pop()
    elif fault=='cost':reports[1]['costs']['slippage_bps']=1
    elif fault=='rate_order':reports[1],reports[2]=reports[2],reports[1]
    elif fault=='config':reports[1]['config']['target']='3R'
    elif fault=='dataset':reports[1]['dataset_manifest_hash']='c'*64
    elif fault=='calendar':reports[1]['equity'][0]['date']='2026-11-05'
    elif fault=='seed':reports[1]['seed']=99
    elif fault=='news':reports[1]['news_calendar']={'id':'d'*64}
    elif fault=='profit':reports[1]['metrics']['net_profit']+=1
    elif fault=='equity':reports[1]['equity'][0]['equity']+=1
    elif fault=='borrow_trade':reports[1]['trades'][0]['borrow']+=1
    elif fault=='borrow_ledger':next(e for e in reports[1]['ledger'] if e['kind']=='borrow')['cash_change']-=1
    elif fault=='nonfinite':reports[1]['trades'][0]['borrow']=float('nan')
    elif fault=='signals':reports[1]['signals'][0]['weight']=.5
    elif fault=='nonfinite_metric':reports[1]['metrics']['marked_sharpe']=float('inf')
    elif fault=='missing_metric':del reports[1]['metrics']['marked_sharpe']
    else:reports[1]['trades'][0]['fees']='not a finite charge'
    with pytest.raises(DataError):summarize_accounts(reports,base,CFG)


@pytest.mark.parametrize('kind',['empty','long_only','loss'])
def test_empty_no_short_and_losing_accounts_remain_visible(kind):
    from backend.lab.sensitivity import cost_arms,summarize_accounts
    frame,signals,base,account=nonlinear_inputs();reports=[]
    if kind=='empty':signals=[]
    elif kind=='long_only':signals=signals[1:]
    else:frame.loc[3:,['open','high','low','close']]=[99,99.1,98.9,99]
    for arm in cost_arms(base,CFG):
        book=simulate(frame,signals,CFG,Costs(**arm['costs']),account,start='2026-11-04',end='2026-11-04')
        reports.append(dict(config=CFG.model_dump(),config_id=identity(CFG),costs=arm['costs'],portfolio=account.model_dump(),core_hash=core_hash(),
            dataset_id='a'*24,dataset_manifest_hash='b'*64,start='2026-11-04',end='2026-11-04',seed=42,news_dates=None,news_calendar=None,
            signals=book.signals,trades=book.trades,ledger=book.ledger,equity=book.equity,metrics=summary(book,account.capital)))
    result=summarize_accounts(reports,base,CFG);assert len(result['comparison_rows'])==4
    if kind=='empty':assert all(r['trades']==r['net_profit']==0 and r['no_short_trades'] for r in result['comparison_rows'])
    elif kind=='long_only':assert all(r['short_trades']==r['borrow_paid']==0 and r['no_short_trades'] for r in result['comparison_rows'])
    else:assert all(r['net_profit']<0 for r in result['comparison_rows'])
