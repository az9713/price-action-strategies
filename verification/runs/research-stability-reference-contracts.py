"""Independent pairwise coordinate reference, not the production bucket reducer."""
from fractions import Fraction
from itertools import product
import pytest
from backend.lab.config import Strategy,identity
from backend.lab.research_qualification import stability,neighbor_ids


def number(encoded):return Fraction(int(encoded['numerator']),int(encoded['denominator']))


def test_complete_432_node_grid_every_neighbor_and_exact_missing_profit_moment():
    # Five always-active axes; the remaining public settings stay fixed. The
    # reference explicitly compares every pair, rather than hashing slices.
    axes=['direction','swing_strength','target','stop_buffer','max_hold']
    configurations=[Strategy(timeframe='1m',**dict(zip(axes,values))) for values in
        product(['both','long','short'],[2,3,5,8],['1R','2R','3R','swing'],[0.,.1,.25],[0,24,96,])]
    ids=[identity(c) for c in configurations]
    observations={cid:None if i%13==0 else dict(net_profit=str(Fraction(i%19-9,8)),marked_sharpe=None if i%3==0 else .5)
                  for i,cid in enumerate(ids)}
    # Finite decimal input rather than fractional text: original numerical
    # serialization accepts 0.125, not an unevaluated expression such as 1/8.
    for value in observations.values():
        if value is not None:value['net_profit']=str(float(Fraction(value['net_profit'])))
    result=stability(configurations,observations)
    assert len(configurations)==432 and len(result['rows'])==432
    for i,(c,row) in enumerate(zip(configurations,result['rows'])):
        neighbors=[j for j,other in enumerate(configurations) if sum(getattr(c,k)!=getattr(other,k) for k in axes)==1]
        actual=[observations[ids[j]] for j in neighbors if observations[ids[j]] is not None]
        profits=[Fraction(value['net_profit']) for value in actual];count=len(profits)
        assert row['neighbors']==len(neighbors)==12
        assert row['available']==count and row['missing']==len(neighbors)-count
        assert row['positive']==sum(value>0 for value in profits)
        assert number(row['mean_net_profit'])==sum(profits)/count
        assert number(row['sample_variance_net_profit'])==sum((value-sum(profits)/count)**2 for value in profits)/(count-1)
        assert row['undefined_sharpe']==sum(value['marked_sharpe'] is None for value in actual)
        if i%37==0:assert set(neighbor_ids(configurations,ids[i]))=={ids[j] for j in neighbors}


def test_effective_trigger_aliases_are_not_changed_coordinates_or_duplicate_neighbors():
    configs=[Strategy(timeframe='1m'),Strategy(timeframe='1m',trigger_timeframe='1m'),
             Strategy(timeframe='1m',target='2R'),Strategy(timeframe='1m',trigger_timeframe='1m',target='2R')]
    ids=[identity(c) for c in configs]
    values={cid:dict(net_profit=i,marked_sharpe=None) for i,cid in enumerate(ids)}
    result=stability(configs,values)
    assert set(neighbor_ids(configs,ids[0]))=={ids[2],ids[3]}
    assert result['rows'][0]['neighbors']==2 and number(result['rows'][0]['mean_net_profit'])==Fraction(5,2)
    assert result['rows'][0]['coordinate_counts']=={'target':2}


def test_missing_singleton_and_unknown_identity_are_explicit():
    configs=[Strategy(timeframe='1m')];cid=identity(configs[0]);row=stability(configs,{cid:None})['rows'][0]
    assert row['neighbors']==0 and row['available']==0 and row['missing']==0
    assert row['mean_net_profit'] is None and row['sample_variance_net_profit'] is None
    with pytest.raises(ValueError):neighbor_ids(configs,'unknown')


def test_single_observed_neighbor_has_no_sample_variance_and_keeps_loss():
    configs=[Strategy(timeframe='1m'),Strategy(timeframe='1m',target='2R')];ids=[identity(c) for c in configs]
    result=stability(configs,{ids[0]:None,ids[1]:dict(net_profit=-.25,marked_sharpe=None)})
    assert number(result['rows'][0]['mean_net_profit'])==Fraction(-1,4)
    assert result['rows'][0]['sample_variance_net_profit'] is None
    assert result['rows'][1]['missing']==1 and result['rows'][1]['mean_net_profit'] is None
