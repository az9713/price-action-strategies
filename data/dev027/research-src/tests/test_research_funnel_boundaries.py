"""Undefined, insolvent, malformed and finite-extreme research summaries."""
from datetime import date,datetime
from decimal import Decimal
import copy, math
import pytest
from test_research_funnel import configs,report,specification,rational
from backend.lab.config import identity
from backend.lab.research_funnel import FunnelStudy,freeze_specification,family_average,_dates,_stats
from fractions import Fraction


def test_exact_date_objects_are_allowed_but_timestamps_and_nonmodels_are_not():
    spec=specification();spec['era_one']['start']=date(2026,11,2)
    assert freeze_specification(FunnelStudy(**spec))['era_one']['start']=='2026-11-02'
    spec['era_one']['start']=datetime(2026,11,2)
    with pytest.raises(ValueError):FunnelStudy(**spec)
    with pytest.raises(ValueError):freeze_specification({})


@pytest.mark.parametrize('fault',['empty_family','not_strategies','not_reports','nonpositive_capital','missing_assumption','missing_capital','not_equity_list','not_trade_list','not_equity_record','invalid_dates','reversed_dates','threshold_negative','threshold_too_large'])
def test_whole_family_undefined_or_malformed_contracts_refuse_partial_results(fault):
    versions=configs()[:2];reports={identity(c):report(c,[1,0,-2]) for c in versions};first=reports[identity(versions[0])]
    kwargs={}
    if fault=='empty_family':versions=[]
    elif fault=='not_strategies':versions=['pretend-version']
    elif fault=='not_reports':reports=[]
    elif fault=='nonpositive_capital':first['portfolio']['capital']=0
    elif fault=='missing_assumption':del first['costs']
    elif fault=='missing_capital':del first['portfolio']['capital']
    elif fault=='not_equity_list':first['equity']={}
    elif fault=='not_trade_list':first['trades']={}
    elif fault=='not_equity_record':first['equity'][0]=None
    elif fault=='invalid_dates':first['start']='November2'
    elif fault=='reversed_dates':first['start']='2026-11-05'
    elif fault=='threshold_negative':kwargs['minimum_sharpe']=-1
    else:kwargs['minimum_sharpe']=11
    with pytest.raises(ValueError):family_average(versions,reports,**kwargs)


def test_no_eligible_sessions_remains_insufficient_and_never_becomes_three_zero_days():
    versions=configs()[:2];reports={identity(c):report(c,[0,0,0]) for c in versions}
    for value in reports.values():value.update(start='2026-11-07',end='2026-11-08',equity=[])
    result=family_average(versions,reports)
    assert result['state']=='insufficient'
    assert result['marked']['sessions']==0 and result['marked']['daily']==[]
    assert result['marked']['annualized_profit'] is None and result['marked']['sharpe'] is None
    assert not result['marked']['gate_pass']


def test_insolvent_marked_capital_is_not_given_a_percentage_sharpe():
    versions=configs()[:2];reports={identity(c):report(c,[-1100,50,40]) for c in versions}
    result=family_average(versions,reports)
    assert result['marked']['sharpe'] is None and not result['marked']['gate_pass']
    assert rational(result['marked']['net_profit'])==-1010


def test_cancellation_during_a_complete_family_does_not_publish_a_prefix():
    versions=configs();reports={identity(c):report(c,[1,0,-2]) for c in versions};seen=[]
    def cancel():
        seen.append(True)
        return len(seen)>=4
    with pytest.raises(InterruptedError):family_average(versions,reports,cancel=cancel)
    assert len(seen)==4


def test_large_finite_dollar_observations_use_scaled_mean_and_sample_deviation():
    # Independent scaled reference: dollar units cancel from the Sharpe ratio.
    pnl=[Fraction(10**306),Fraction(-10**306),Fraction(10**306)]
    stats=_stats(['2026-11-02','2026-11-03','2026-11-04'],pnl,Fraction(10**307),.5,compatibility=True)
    independent=(1/3)/math.sqrt(((1-1/3)**2+(-1-1/3)**2+(1-1/3)**2)/2)*math.sqrt(252)
    assert math.isclose(stats['sharpe'],independent,rel_tol=1e-12)
    assert math.isfinite(stats['annualized_profit'])
    with pytest.raises(ValueError,match='finite statistical'):
        _stats(['2026-11-02','2026-11-03','2026-11-04'],[v*10 for v in pnl],Fraction(10**308),.5,compatibility=True)
