from backend.lab.metrics import summary,block_interval,deflated_sharpe
from backend.lab.engine import Simulation
import numpy as np
import pytest

def test_marked_drawdown_and_no_trade_labels():
    sim=Simulation(equity=[{'equity':90},{'equity':95},{'equity':100}])
    result=summary(sim,100)
    assert result['max_drawdown']==pytest.approx(.1)
    assert result['net_profit']==0 and not result['positive_profit']
    assert result['win_rate'] is None and result['profit_factor'] is None
    assert len(result['undefined'])==2

def test_flat_equity_statistics_are_not_successes():
    result=summary(Simulation(equity=[{'equity':100},{'equity':100}]),100)
    assert result['marked_sharpe'] is None and result['total_return']==0

def test_finite_trade_metrics_and_excluding_best_days():
    sim=Simulation(equity=[{'equity':90},{'equity':110},{'equity':100}],trades=[{'net_pnl':20},{'net_pnl':-20}])
    result=summary(sim,100)
    assert result['win_rate']==.5 and result['profit_factor']==1
    assert result['profit_without_ten_best_days']==0

def test_blocks_reproducible_and_known_constant_interval():
    actual=block_interval([1,1,1,1],resamples=100,block=2)
    assert actual['low']==4 and actual['high']==4
    assert actual==block_interval([1,1,1,1],resamples=100,block=2)
    assert block_interval([1]) is None

def test_deflated_sharpe_degenerate_and_trial_sensitivity():
    assert deflated_sharpe([1,1,1,1],10,.1) is None
    returns=np.random.default_rng(12).normal(.001,.01,200)
    one=deflated_sharpe(returns,1,.2)
    many=deflated_sharpe(returns,1000,.2)
    assert 0<=many<one<=1
