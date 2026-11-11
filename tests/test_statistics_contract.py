"""Expected contracts precede metric corrections; rounded paper values stay frozen."""
import json
import math
from pathlib import Path
from statistics import mean, stdev

import numpy as np
import pytest

from backend.lab import metrics
from backend.lab.engine import Simulation
from verification.reference_statistics import dsr_from_moments, linear_quantile, sharpe_from_equity

FIXTURES=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/statistics-fixtures.json').read_text())


@pytest.mark.parametrize('path',FIXTURES['equity_paths'],ids=lambda p:p['name'])
def test_nonpositive_equity_is_a_loss_not_invalid_json_or_sharpe(path):
    result=metrics.summary(Simulation(equity=[dict(equity=x) for x in path['equity']]),path['capital'])
    for field in ['net_profit','total_return','max_drawdown','daily_pnl']:
        assert result[field]==pytest.approx(path[field],abs=1e-12)
    assert result['daily_returns']==path['daily_returns']
    assert result['marked_sharpe'] is None and not result['positive_profit']
    assert any('nonpositive equity' in note.lower() for note in result['undefined'])
    json.dumps(result,allow_nan=False)


def test_positive_equity_sharpe_matches_stdlib_and_hand_pnl():
    equity=[95,105,103,110,100]
    result=metrics.summary(Simulation(equity=[dict(equity=x) for x in equity]),100,.03)
    assert result['marked_sharpe']==pytest.approx(sharpe_from_equity(100,equity,.03),abs=1e-12)
    assert result['daily_pnl']==[-5,10,-2,7,-10]
    assert result['max_drawdown']==pytest.approx(1-100/110,abs=1e-12)


@pytest.mark.parametrize('capital',[0,-1,float('nan'),float('inf')])
def test_summary_requires_positive_finite_starting_capital(capital):
    with pytest.raises(ValueError): metrics.summary(Simulation(),capital)


@pytest.mark.parametrize('field',['equity','net_pnl','annual_risk_free'])
@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf')])
def test_summary_rejects_nonfinite_inputs(field,value):
    sim=Simulation(equity=[dict(equity=value if field=='equity' else 100)],
                   trades=[dict(net_pnl=value if field=='net_pnl' else 0)])
    with pytest.raises(ValueError): metrics.summary(sim,100,value if field=='annual_risk_free' else 0)


@pytest.mark.parametrize('example',FIXTURES['published_dsr']['examples'],ids=lambda e:str(e['trials']))
def test_dsr_primary_paper_worked_examples(example):
    contract=FIXTURES['published_dsr']
    sr=contract['annual_sharpe']/math.sqrt(contract['observations_per_year'])
    dispersion=math.sqrt(contract['annual_cross_trial_sharpe_variance']/contract['observations_per_year'])
    helper=getattr(metrics,'deflated_sharpe_from_moments',None)
    assert callable(helper),'A moments-level entry point is needed to reproduce the published example without fabricating returns.'
    args=(sr,contract['observations'],example['skewness'],example['raw_kurtosis'],example['trials'],dispersion)
    result=helper(*args)
    assert result==pytest.approx(example['probability'],abs=FIXTURES['tolerances']['published_rounded_probability_absolute'])
    assert result==pytest.approx(dsr_from_moments(*args),abs=1e-12)


def test_dsr_return_moment_convention_matches_independent_unbiased_estimators():
    returns=[-.03,.01,.02,-.015,.04,.005,-.01,.025]
    n=len(returns);avg=mean(returns);s=stdev(returns)
    skewness=n/((n-1)*(n-2))*sum(((r-avg)/s)**3 for r in returns)
    excess=n*(n+1)/((n-1)*(n-2)*(n-3))*sum(((r-avg)/s)**4 for r in returns)-3*(n-1)**2/((n-2)*(n-3))
    expected=dsr_from_moments(avg/s,n,skewness,excess+3,25,.1)
    assert metrics.deflated_sharpe(returns,25,.1)==pytest.approx(expected,abs=1e-12)


@pytest.mark.parametrize('trials,dispersion',[(float('nan'),.1),(float('inf'),.1),(0,.1),
    (1,float('nan')),(1,float('inf')),(1,-.1)])
def test_dsr_invalid_assumptions_are_explicitly_undefined(trials,dispersion):
    assert metrics.deflated_sharpe([.01,-.02,.03,.04],trials,dispersion) is None


def test_dsr_nonpositive_estimated_variance_is_undefined():
    # The unbiased excess-kurtosis estimate for [1,1,3,3] is -6;
    # raw=-3, skew=0 and SR=sqrt(3) give denominator 1-SR^2=-2.
    assert metrics.deflated_sharpe([1,1,3,3],10,.1) is None


def test_circular_bootstrap_matches_independent_loop_and_quantiles():
    values=[-4,2,7,-1,3];seed=12;resamples=101;block=3
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,len(values),size=(resamples,math.ceil(len(values)/block)))
    totals=[]
    for row in starts:
        sampled=[]
        for start in row:
            sampled.extend(values[(int(start)+offset)%len(values)] for offset in range(block))
        totals.append(sum(sampled[:len(values)]))
    result=metrics.block_interval(values,seed,resamples,block)
    assert result['low']==pytest.approx(linear_quantile(totals,.025),abs=1e-12)
    assert result['high']==pytest.approx(linear_quantile(totals,.975),abs=1e-12)
    assert result['resamples']==resamples and result['block_sessions']==block and result['seed']==seed


@pytest.mark.parametrize('kwargs',[dict(resamples=0),dict(resamples=1),dict(resamples=2.5),dict(block=0),
    dict(block=-1),dict(block=1.5),dict(seed=-1)])
def test_bootstrap_invalid_controls_reject(kwargs):
    with pytest.raises(ValueError): metrics.block_interval([1,2,3],**kwargs)


@pytest.mark.parametrize('values',[[1,float('nan')],[1,float('inf')],[[1,2],[3,4]]])
def test_bootstrap_nonfinite_or_matrix_input_rejects(values):
    with pytest.raises(ValueError): metrics.block_interval(values)


def test_extreme_finite_inputs_cannot_overflow_into_an_infinite_badge():
    with pytest.raises(ValueError):
        metrics.summary(Simulation(equity=[dict(equity=1e308),dict(equity=1e-308)]),1e-308)


@pytest.mark.parametrize('kwargs',[dict(observations=3),dict(observations=4.5),dict(observations=True),
    dict(sharpe=float('inf')),dict(skewness=float('nan')),dict(raw_kurtosis=float('inf')),
    dict(trials=0),dict(trial_sharpe_std=-1),dict(raw_kurtosis=-100)])
def test_invalid_moment_statistics_remain_undefined(kwargs):
    args=dict(sharpe=.2,observations=100,skewness=0,raw_kurtosis=3,trials=10,trial_sharpe_std=.1)
    args.update(kwargs)
    assert metrics.deflated_sharpe_from_moments(**args) is None


def test_empty_summary_and_insufficient_dsr_are_json_safe():
    result=metrics.summary(Simulation(),100)
    assert result['net_profit']==0 and result['best_day_profit'] is None and result['daily_returns']==[]
    json.dumps(result,allow_nan=False)
    assert metrics.deflated_sharpe([1,2,3],10,.1) is None
    assert metrics.deflated_sharpe([[1,2],[3,4]],10,.1) is None


def test_bootstrap_chunk_boundary_and_long_blocks_preserve_exact_seed_results():
    # The batch size128 crosses twice; block>=n rotates all observations, so
    # every resample has the exact same total regardless of start or batching.
    result=metrics.block_interval([-4,2,7,-1,3],seed=91,resamples=301,block=100000)
    assert result['low']==result['high']==7
