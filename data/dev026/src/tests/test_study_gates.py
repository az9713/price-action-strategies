"""Authored gate truth table only; these inputs are not fabricated trading accounts."""
from copy import deepcopy
import pytest
from backend.lab.research import passes_screen

GOOD={'trades':30,'net_profit':1.,'marked_sharpe':.5}


def test_both_windows_accept_exact_trade_sharpe_boundary_and_strictly_positive_profit():
    assert passes_screen([deepcopy(GOOD),deepcopy(GOOD)],30,.5)
    assert passes_screen([GOOD|{'net_profit':1e-12},GOOD],30,.5)


@pytest.mark.parametrize('window',[0,1])
@pytest.mark.parametrize('change',[
    {'trades':29},{'trades':0},{'trades':True},{'trades':30.5},
    {'net_profit':0.},{'net_profit':-1.},{'net_profit':float('nan')},{'net_profit':float('inf')},
    {'marked_sharpe':.4999999999},{'marked_sharpe':None},{'marked_sharpe':float('nan')},{'marked_sharpe':float('inf')},
    {'net_profit':'bad'},
])
def test_either_window_failing_any_frozen_gate_cannot_be_a_candidate(window,change):
    metrics=[deepcopy(GOOD),deepcopy(GOOD)];metrics[window].update(change)
    assert not passes_screen(metrics,30,.5)


@pytest.mark.parametrize('metrics',[[],[GOOD],[GOOD,GOOD,GOOD],[{},GOOD]])
def test_missing_extra_or_incomplete_window_is_not_a_passing_comparison(metrics):
    assert not passes_screen(metrics,30,.5)
