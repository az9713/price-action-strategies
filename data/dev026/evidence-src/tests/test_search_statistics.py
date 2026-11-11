"""Independent daily-moment and search-sensitivity application contracts."""
import json,math
from statistics import mean,stdev
import pytest
from backend.lab.config import Strategy,identity
from verification.reference_statistics import dsr_from_moments

RETURNS=[[.01,-.02,.03,.015,-.005,.02,-.01,.025],[-.03,.01,-.02,.005,-.01,.01,-.025,.005],[.015,-.01,.025,-.005,.02,-.015,.03,.01]]

def row(index,returns,profit=100):
    cfg=Strategy(target=['1R','2R','3R'][index%3])
    return dict(part=index,config_id=identity(cfg),config=cfg.model_dump(),report_sha256=identity({'part':index}),
                metrics=dict(daily_returns=returns,net_profit=profit,trades=2))

def oracle(values,n,dispersion):
    count=len(values);center=mean(values);deviations=[x-center for x in values]
    m2=sum(d*d for d in deviations)/count;m3=sum(d**3 for d in deviations)/count;m4=sum(d**4 for d in deviations)/count
    skew=math.sqrt(count*(count-1))/(count-2)*m3/m2**1.5
    raw=3+(count-1)/((count-2)*(count-3))*((count+1)*(m4/m2**2-3)+6)
    return dsr_from_moments(center/stdev(values),count,skew,raw,n,dispersion)

def build(rows,**kwargs):
    from backend.lab.models import SearchStatistics
    from backend.lab.search_statistics import build_search_statistics
    return build_search_statistics(rows,SearchStatistics(**kwargs))

def test_complete_cohort_empirical_dispersion_and_independent_probabilities():
    values=[row(i,r,profit=100 if i!=1 else -200) for i,r in enumerate(RETURNS)]
    result=build(values,effective_trials=[3,1,2])
    expected=stdev([mean(r)/stdev(r) for r in RETURNS])
    assert result['trial_sharpe_std']==pytest.approx(expected,abs=1e-14)
    assert result['settings']['effective_trials']==[1,2,3]
    assert result['finite_sharpe_accounts']==3 and result['raw_configurations']==3
    for index,account in enumerate(result['accounts']):
        assert account['net_profit']==values[index]['metrics']['net_profit'] and account['source_part_sha256']==values[index]['report_sha256']
        assert [v['effective_trials'] for v in account['sensitivity']]==[1,2,3]
        for item in account['sensitivity']:
            assert item['score']==pytest.approx(oracle(RETURNS[index],item['effective_trials'],expected),abs=1e-12)
            assert item['undefined_reason'] is None
        scores=[v['score'] for v in account['sensitivity']];assert scores==sorted(scores,reverse=True)
        assert not any(k in account for k in ['pass','candidate','profitable'])
    assert 'independent' in ' '.join(result['limitations']).lower()

@pytest.mark.parametrize('returns,reason',[
    ([.01,.02,.03],'insufficient_observations'),([0]*8,'zero_return_variance'),
    ([None,.01,.02,.03],'invalid_returns'),([True,.01,.02,.03],'invalid_returns'),
    ([float('nan'),.01,.02,.03],'invalid_returns'),([float('inf'),.01,.02,.03],'invalid_returns'),
    ([1e308,-1e308,1e308,-1e308],'nonfinite_moments'),
])
def test_degenerate_returns_stay_undefined_without_zero_substitution(returns,reason):
    result=build([row(0,returns)],effective_trials=[1],dispersion_mode='assumed',trial_sharpe_std=.1)
    item=result['accounts'][0]['sensitivity'][0]
    assert item==dict(effective_trials=1,score=None,undefined_reason=reason)
    json.dumps(result,allow_nan=False)

def test_one_valid_account_can_compute_single_trial_without_invented_dispersion():
    result=build([row(0,RETURNS[0]),row(1,[0]*8)],effective_trials=[1,2])
    assert result['finite_sharpe_accounts']==1 and result['trial_sharpe_std'] is None
    a,b=result['accounts'][0]['sensitivity']
    assert a['score']==pytest.approx(oracle(RETURNS[0],1,0),abs=1e-12)
    assert b['score'] is None and b['undefined_reason']=='dispersion_unavailable'

def test_zero_dispersion_and_nonphysical_corrected_moment_variance_are_explicit():
    result=build([row(0,RETURNS[0]),row(1,RETURNS[0])],effective_trials=[1,2])
    assert result['trial_sharpe_std']==0 and any('zero' in s.lower() for s in result['limitations'])
    scores=result['accounts'][0]['sensitivity'];assert scores[0]['score']==scores[1]['score']
    result=build([row(0,[1.,1.,2.,2.])],effective_trials=[1],dispersion_mode='assumed',trial_sharpe_std=0)
    assert result['accounts'][0]['sensitivity'][0]['undefined_reason']=='invalid_model_variance'

def test_assumed_dispersion_is_per_observation_and_losses_remain_losses():
    # Positive arithmetic mean can coexist with a geometric account loss.
    returns=[.5,-.4]*4;profit=10000*(math.prod(1+r for r in returns)-1)
    assert profit<0 and mean(returns)>0
    result=build([row(0,returns,profit=profit),row(1,RETURNS[1])],effective_trials=[1,2],dispersion_mode='assumed',trial_sharpe_std=.25)
    assert result['trial_sharpe_std']==.25 and result['accounts'][0]['net_profit']==profit
    assert result['accounts'][0]['sensitivity'][1]['score']==pytest.approx(oracle(returns,2,.25),abs=1e-12)

@pytest.mark.parametrize('policy',[
    {'effective_trials':[True]},{'effective_trials':[1.5]},{'effective_trials':['2']},
    {'effective_trials':[]},{'effective_trials':[1,1]},{'effective_trials':[0]},
    {'dispersion_mode':'assumed'},{'trial_sharpe_std':.1},
    {'dispersion_mode':'assumed','trial_sharpe_std':True},
    {'dispersion_mode':'assumed','trial_sharpe_std':float('inf')},
])
def test_strict_policy_rejects_implicit_or_ignored_assumptions(policy):
    from backend.lab.models import SearchStatistics
    with pytest.raises(ValueError):SearchStatistics(**policy)

def test_default_grid_resolves_before_payload_and_invalid_counts_reject():
    from backend.lab.models import Search
    for count,expected in [(1,[1]),(3,[1,3]),(10,[1,10]),(111,[1,10,100,111])]:
        request=Search(dataset_id='a'*24,start='2022-01-03',end='2022-01-31',count=count)
        assert request.model_dump(mode='json')['statistics']['effective_trials']==expected
    with pytest.raises(ValueError):Search(dataset_id='a'*24,start='2022-01-03',end='2022-01-31',count=2,statistics={'effective_trials':[3]})

@pytest.mark.parametrize('change',[
    {'part':True},{'part':-1},{'config_id':'bad'},{'report_sha256':''},{'metrics':None},
    {'metrics':{'net_profit':True,'daily_returns':RETURNS[0]}},
    {'metrics':{'net_profit':float('inf'),'daily_returns':RETURNS[0]}},
])
def test_malformed_saved_rows_fail_without_a_partial_summary(change):
    with pytest.raises(ValueError):build([row(0,RETURNS[0])|change])

def test_empty_and_duplicate_part_or_configuration_reject():
    with pytest.raises(ValueError):build([])
    a=row(0,RETURNS[0]);b=row(1,RETURNS[1])
    for changed in [b|{'part':0},b|{'config_id':a['config_id']}]:
        with pytest.raises(ValueError):build([a,changed])

@pytest.mark.parametrize('phase',[1,2])
def test_cancellation_between_saved_metric_read_and_score_publication(phase):
    from backend.lab.models import SearchStatistics
    from backend.lab.search_statistics import build_search_statistics
    calls=[]
    def cancel():calls.append(1);return len(calls)==phase
    with pytest.raises(InterruptedError):build_search_statistics([row(0,RETURNS[0])],SearchStatistics(),cancel=cancel)

def test_nonfinite_computed_dispersion_stays_undefined(monkeypatch):
    from backend.lab import search_statistics
    monkeypatch.setattr(search_statistics.np,'std',lambda *a,**kw:float('inf'))
    result=build([row(0,RETURNS[0]),row(1,RETURNS[1])],effective_trials=[1,2])
    assert result['trial_sharpe_std'] is None
    assert result['accounts'][0]['sensitivity'][1]['undefined_reason']=='dispersion_unavailable'

def test_nonlist_and_precision_unstable_saved_returns_do_not_get_scores():
    from backend.lab.search_statistics import moments
    assert moments('not an array')[1]=='invalid_returns'
    assert moments([1.,1.,1.+2e-16,1.+4e-16])[1]=='nonfinite_moments'
