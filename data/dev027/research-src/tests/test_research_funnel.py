"""Prespecified era/replica models and independent all-version family hand cases."""
import copy
from fractions import Fraction
import importlib
import importlib.util
import math

import pytest
from backend.lab.config import Strategy, Costs, Portfolio, identity


def test_research_funnel_kernel_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_funnel') is not None, 'Era/replication and complete all-version family kernel is not implemented.'


@pytest.fixture
def funnel():return importlib.import_module('backend.lab.research_funnel')


def specification():
    return dict(name='Prespecified synthetic funnel',dataset_id='a'*24,
        discovery=dict(start='2026-11-02',end='2026-11-05'),
        validation=dict(start='2026-11-06',end='2026-11-06'),holdout=dict(start='2026-11-09',end='2026-11-10'),
        configurations=[Strategy().model_dump()],primary_symbol='SPY',replication_symbol='QQQ',
        era_one=dict(start='2026-11-02',end='2026-11-03'),era_two=dict(start='2026-11-04',end='2026-11-05'))


def configs():return [Strategy(max_hold=hold) for hold in [0,24,96]]


def report(config, daily):
    capital=1000;value=capital;equity=[]
    for date,change in zip(['2026-11-02','2026-11-03','2026-11-04'],daily):
        value+=change;equity.append(dict(date=date,equity=value,cash=value,receivables=0,gross_exposure=0))
    return dict(report_type='single_strategy',config=config.model_dump(),config_id=identity(config),dataset_id='a'*24,
        dataset_manifest_hash='b'*64,core_hash='c'*64,start='2026-11-02',end='2026-11-04',
        costs=Costs().model_dump(),portfolio=Portfolio(capital=capital).model_dump(),equity=equity,
        signals=[],trades=[] if not sum(daily) else [dict(exit_at='2026-11-04T20:59:00+00:00',net_pnl=sum(daily))])


def rational(value):return Fraction(int(value['numerator']),int(value['denominator']))


def test_prespecified_eras_replica_and_final_are_distinct(funnel):
    value=funnel.FunnelStudy(**specification())
    frozen=funnel.freeze_specification(value)
    assert frozen['primary_symbol']=='SPY' and frozen['replication_symbol']=='QQQ'
    assert frozen['era_two']['end'] < frozen['validation']['start'] < frozen['holdout']['start']
    assert frozen['minimum_signals']==40 and frozen['replication_minimum_sharpe']==.3
    assert frozen['family_minimum_sharpe']==.5
    assert frozen['source_video']=='https://www.youtube.com/watch?v=z97PnFIPoFg'
    value.configurations[0].max_hold=0
    assert frozen['configurations'][0]['max_hold']==96,'Registration snapshot aliases caller configuration.'


@pytest.mark.parametrize('fault',['same_symbol','invalid_symbol','reversed_eras','overlap_eras','era_before_discovery','era_after_discovery','era_into_validation','bool_signals','float_signals','nonfinite_sharpe','portfolio_mode','numeric_date','unknown_field'])
def test_invalid_funnel_cannot_be_registered(funnel,fault):
    value=specification()
    if fault=='same_symbol':value['replication_symbol']='SPY'
    elif fault=='invalid_symbol':value['primary_symbol']='spy'
    elif fault=='reversed_eras':value['era_one'],value['era_two']=value['era_two'],value['era_one']
    elif fault=='overlap_eras':value['era_two']['start']='2026-11-03'
    elif fault=='era_before_discovery':value['era_one']['start']='2026-10-30'
    elif fault=='era_after_discovery':value['era_two']['end']='2026-11-06'
    elif fault=='era_into_validation':value['era_two']['start']=value['era_two']['end']='2026-11-06'
    elif fault=='bool_signals':value['minimum_signals']=True
    elif fault=='float_signals':value['minimum_signals']=40.0
    elif fault=='nonfinite_sharpe':value['replication_minimum_sharpe']=float('nan')
    elif fault=='portfolio_mode':value['study_mode']='portfolio'
    elif fault=='numeric_date':value['era_one']['start']=1793577600
    else:value['invented_gate']=True
    with pytest.raises(ValueError):funnel.FunnelStudy(**value)


def test_complete_losing_family_cannot_be_replaced_by_its_profitable_subset(funnel):
    first,second,_=configs();reports={identity(first):report(first,[10,0,-2]),identity(second):report(second,[-20,0,0])}
    before=copy.deepcopy(reports)
    value=funnel.family_average([first,second],reports)
    assert value['version_count']==2 and value['members']==sorted(reports)
    assert [rational(row['mean_pnl']) for row in value['marked']['daily']]==[Fraction(-5),Fraction(0),Fraction(-1)]
    assert rational(value['marked']['net_profit'])==Fraction(-6)
    assert value['marked']['annualized_profit']==-504
    assert value['marked']['gate_pass'] is False
    assert [rational(row['mean_pnl']) for row in value['realized_exit_day_compatibility']['daily']]==[Fraction(0),Fraction(0),Fraction(-6)]
    assert value['aggregation_kind']=='equal_weight_research_average_not_shared_capital_execution'
    assert reports==before
    with pytest.raises(ValueError):funnel.family_average([first,second],{identity(first):reports[identity(first)]})


def test_every_version_has_equal_weight_even_for_a_repeating_rational_mean(funnel):
    versions=configs();reports={identity(c):report(c,[int(i==0),0,0]) for i,c in enumerate(versions)}
    value=funnel.family_average(versions,reports)
    assert rational(value['marked']['daily'][0]['mean_pnl'])==Fraction(1,3)
    assert rational(value['marked']['net_profit'])==Fraction(1,3)
    assert value['version_count']==3


def test_failed_member_and_no_trade_family_never_produce_a_fake_pass(funnel):
    first,second,_=configs();reports={identity(first):report(first,[0,0,0]),identity(second):None}
    incomplete=funnel.family_average([first,second],reports)
    assert incomplete['state']=='incomplete' and incomplete['failed_members']==[identity(second)]
    assert incomplete['marked'] is None
    reports[identity(second)]=report(second,[0,0,0])
    value=funnel.family_average([first,second],reports)
    assert value['state']=='complete' and value['marked']['sharpe'] is None and not value['marked']['gate_pass']


@pytest.mark.parametrize('fault',['calendar_missing','calendar_reordered','weekend_date','capital','costs','manifest','core','config','nonfinite_equity','naive_exit','exit_outside_calendar','duplicate_version','different_family'])
def test_incomparable_accounts_or_calendar_faults_are_not_zero_padded(funnel,fault):
    versions=configs()[:2];reports={identity(c):report(c,[1,-2,3]) for c in versions};second=reports[identity(versions[1])]
    if fault=='calendar_missing':second['equity'].pop(1)
    elif fault=='calendar_reordered':second['equity'].reverse()
    elif fault=='weekend_date':
        for r in reports.values():r['equity'][1]['date']='2026-11-07'
    elif fault=='capital':second['portfolio']['capital']=2000
    elif fault=='costs':second['costs']['slippage_bps']+=1
    elif fault=='manifest':second['dataset_manifest_hash']='d'*64
    elif fault=='core':second['core_hash']='e'*64
    elif fault=='config':second['config']['max_hold']=96
    elif fault=='nonfinite_equity':second['equity'][0]['equity']=float('inf')
    elif fault=='naive_exit':second['trades'][0]['exit_at']='2026-11-04T15:59:00'
    elif fault=='exit_outside_calendar':second['trades'][0]['exit_at']='2026-11-07T15:59:00+00:00'
    elif fault=='duplicate_version':versions=[versions[0],versions[0]]
    else:versions[1]=Strategy(family='breakout')
    with pytest.raises(ValueError):funnel.family_average(versions,reports)


def test_family_sharpe_matches_independent_sample_return_calculation_and_cancels(funnel):
    versions=configs()[:2];reports={identity(c):report(c,[2,-1,4]) for c in versions}
    expected_returns=[2/1000,-1/1002,4/1001]
    mean=sum(expected_returns)/3
    deviation=math.sqrt(sum((x-mean)**2 for x in expected_returns)/2)
    value=funnel.family_average(versions,reports)
    assert math.isclose(value['marked']['sharpe'],mean/deviation*math.sqrt(252),rel_tol=1e-12)
    with pytest.raises(InterruptedError):funnel.family_average(versions,reports,cancel=lambda:True)
