"""Independent combinatorial/quota and discovery-gate expectations, authored before implementation."""
from collections import Counter
import math
import pytest
from backend.lab.config import Strategy,FAMILIES,TIMEFRAMES,identity
from backend.lab.models import Search

VARIANTS={'level_bounce':8,'breakout':8,'flip_zone':8,'trend_pullback':3,'trend_line':1,'break_of_structure':1,'change_of_character':2,'sweep_reclaim':4,'supply_demand':12,'fair_value_gap':1}
BREAKS={'breakout','break_of_structure','change_of_character'}

def request(count=100,mode='common_random',**kwargs):
    value=dict(dataset_id='a'*24,start='2022-01-03',end='2022-01-31',count=count,families=list(FAMILIES),timeframes=list(TIMEFRAMES),sampling_policy={'mode':mode});value.update(kwargs)
    return Search(**value)

def hamilton(total,weights):
    values=[total*w/sum(weights) for w in weights];result=[math.floor(v) for v in values]
    for i in sorted(range(len(weights)),key=lambda i:(-(values[i]-result[i]),i))[:total-sum(result)]:result[i]+=1
    return result

@pytest.mark.parametrize('news',[False,True])
def test_complete_grid_has_independently_counted_cells_validity_and_no_duplicates(news):
    from backend.lab.sampling import common_grid,preview_recipe
    expected={f:{tf:VARIANTS[f]*(2 if f in BREAKS else 4)*2*4*(4 if news else 3) for tf in TIMEFRAMES} for f in FAMILIES}
    preview=preview_recipe(list(reversed(FAMILIES)),list(reversed(TIMEFRAMES)),news)
    configs=list(common_grid(list(FAMILIES),list(TIMEFRAMES),news));counts=Counter((c['family'],c['timeframe']) for c in configs)
    assert preview['grid_count']==len(configs)==(32640 if news else 24480)
    assert counts==Counter({(f,tf):n for f,frames in expected.items() for tf,n in frames.items()})
    assert len({identity(Strategy(**c)) for c in configs})==len(configs)
    for c in configs:
        assert c['swing_strength']==3 and c['direction']=='both' and c['stop_kind']=='hard'
        assert c['stop_buffer']==.1 and c['max_hold']==96 and c['target'] in ['1R','2R','3R','swing']
        assert c['stop_reference'] in ['level','swing'] and not c['structure_exit'] and not c['flat_at_close']
        assert Strategy(**c).trigger==('1h' if c['timeframe']=='1d' else c['timeframe'])
    assert 'host' in preview['scope'].lower() and '14016' in preview['scope']

@pytest.mark.parametrize('count',[1,2,3,4,5,7,10,11,103,450])
def test_random_exact_accepted_family_and_filter_quotas_are_independent_of_input_order(count):
    from backend.lab.sampling import sample_common,active_filters
    one=request(count);two=request(count);two.families=list(reversed(two.families));two.timeframes=list(reversed(two.timeframes))
    configs,history=sample_common(one);assert (configs,history)==sample_common(two)
    assert len(configs)==len({identity(c) for c in configs})==count
    quotas=hamilton(count,[1]*10)
    for family,quota in zip(FAMILIES,quotas):
        rows=[c for c in configs if c['family']==family]
        assert len(rows)==quota
        assert [sum(len(active_filters(c))==n for c in rows) for n in range(3)]==hamilton(quota,[4,4,2])
        cells=Counter(c['timeframe'] for c in rows);values=[cells[tf] for tf in TIMEFRAMES];assert max(values)-min(values)<=1
    assert history['attempts']==len(history['proposals'])==history['unique']+history['duplicates']+history['rejected']
    for p in history['proposals']:
        assert identity(Strategy(**p['configuration']))==p['config_id'] and len(p['stream_key'])==64
        assert p['status'] in ['accepted','duplicate']

def test_stable_direct_slot_streams_and_changed_seed():
    from backend.lab.sampling import draw_configuration,sample_common
    a=draw_configuration(42,'change_of_character','15m',2,7,0,False)
    assert a==draw_configuration(42,'change_of_character','15m',2,7,0,False)
    one=request(80);two=request(80);two.seed=43
    assert sample_common(one)[0]!=sample_common(two)[0]

def test_explicit_news_opt_in_has_calendar_dependency_and_no_ignored_base_news():
    with pytest.raises(ValueError):request(10,sampling_policy={'mode':'common_random','include_news':True})
    with pytest.raises(ValueError):request(10,strategy=Strategy(news='skip'))

def test_grid_request_must_match_complete_preview_without_truncation():
    from backend.lab.sampling import sample_common,CommonSamplingError
    req=Search(dataset_id='a'*24,start='2022-01-03',end='2022-01-31',count=48,families=['break_of_structure'],timeframes=['1m'],sampling_policy={'mode':'common_grid'})
    configs,history=sample_common(req);assert len(configs)==48 and history['attempts']==history['unique']==48
    from backend.lab.sampling import active_filters
    assert all(p['filter_count']==len(active_filters(p['configuration'])) for p in history['proposals'])
    req=Search(**(req.model_dump(mode='json')|{'count':47,'statistics':{'effective_trials':[1]}}))
    with pytest.raises(CommonSamplingError,match='48'):sample_common(req)

@pytest.mark.parametrize('invalid',[False,True])
def test_exhaustion_preserves_all_draws_and_never_returns_partial_success(monkeypatch,invalid):
    from backend.lab import sampling
    monkeypatch.setattr(sampling,'MAX_PROPOSALS',3)
    value={'family':'unknown'} if invalid else Strategy(family='level_bounce',timeframe='1m').model_dump()
    monkeypatch.setattr(sampling,'draw_configuration',lambda *a,**kw:value.copy())
    with pytest.raises(sampling.CommonSamplingError) as caught:sampling.sample_common(request(100))
    error=caught.value;assert error.sampling['attempts']==3 and len(error.sampling['proposals'])==3
    assert error.sampling['unique']==(0 if invalid else 1) and error.sampling['rejected']==(3 if invalid else 0)
    assert error.sampling['duplicates']==(0 if invalid else 2)

def row(i,signals=40,trades=30,profit=1,sharpe=.5):
    cfg=Strategy(family='break_of_structure',level_age=96+i);return dict(part=i,config_id=identity(cfg),report_sha256=identity({'report':i}),config=cfg.model_dump(),signal_count=signals,metrics={'trades':trades,'net_profit':profit,'marked_sharpe':sharpe})

def test_initial_funnel_boundaries_denominators_and_pending_later_stages():
    from backend.lab.models import SearchSampling
    from backend.lab.sampling import initial_screen
    rows=[row(0),row(1,signals=39),row(2,trades=29),row(3,profit=0),row(4,sharpe=.499999),row(5,sharpe=None),row(6,profit=-100)]
    result=initial_screen(rows,SearchSampling(mode='common_random'))
    assert result['counts']==dict(generated=7,signal_qualified=6,enough_trades=5,profitable=3,sharpe_passed=1)
    assert len(result['accounts'])==7 and result['groups'][0]['counts']==result['counts']
    assert result['accounts'][0]['initial_gates_passed'] is True and not any(a['initial_gates_passed'] for a in result['accounts'][1:])
    assert result['accounts'][5]['failures']==['undefined_sharpe']
    assert all(v=='not_run' for v in result['later_stages'].values())
    assert all(a['source_part_sha256']==r['report_sha256'] for a,r in zip(result['accounts'],rows))

@pytest.mark.parametrize('change',[{'signal_count':True},{'signal_count':-1},{'metrics':{'trades':True,'net_profit':1,'marked_sharpe':.5}},{'metrics':{'trades':30,'net_profit':float('nan'),'marked_sharpe':.5}},{'metrics':{'trades':30,'net_profit':1,'marked_sharpe':float('inf')}}])
def test_malformed_initial_screen_never_invents_outcomes(change):
    from backend.lab.models import SearchSampling
    from backend.lab.sampling import initial_screen
    with pytest.raises(ValueError):initial_screen([row(0)|change],SearchSampling(mode='common_random'))


def test_saved_signal_count_excludes_warmup_in_new_york_dates_and_retains_close():
    from backend.lab.sampling import count_discovery_signals
    timestamps=['2022-03-14T00:30:00+00:00','2022-03-14T13:30:00+00:00','2022-03-14T20:00:00+00:00','2022-03-15T13:30:00+00:00']
    assert count_discovery_signals([{'available_at':t} for t in timestamps],'2022-03-14','2022-03-14')==2
    assert count_discovery_signals([],'2022-03-14','2022-03-14')==0

@pytest.mark.parametrize('signals',[[{}],[{'available_at':True}],[{'available_at':'not a date'}],[{'available_at':'2022-01-03T10:00:00'}],None])
def test_malformed_saved_signal_timestamps_do_not_become_qualified(signals):
    from backend.lab.sampling import count_discovery_signals
    with pytest.raises(ValueError):count_discovery_signals(signals,'2022-01-03','2022-01-31')

def test_zero_generated_cells_remain_visible_and_unknown_cells_reject():
    from backend.lab.sampling import initial_screen
    from backend.lab.models import SearchSampling
    policy=SearchSampling(mode='common_random');cells=[{'family':'break_of_structure','timeframe':'1m'},{'family':'break_of_structure','timeframe':'1h'}]
    result=initial_screen([row(0)],policy,strata=cells)
    assert len(result['groups'])==2
    assert next(g for g in result['groups'] if g['timeframe']=='1m')['counts']==dict.fromkeys(result['counts'],0)
    for bad in [[],[{}],cells+cells,[{'family':'breakout','timeframe':'1m'}]]:
        with pytest.raises(ValueError):initial_screen([row(0)],policy,strata=bad)
    with pytest.raises(InterruptedError):initial_screen([row(0)],policy,cancel=lambda:True)

def test_complete_finite_random_catalog_is_reachable_and_conditionally_valid():
    from backend.lab.sampling import DOMAINS,FILTERS,draw_configuration,active_filters
    seen={k:set() for k in DOMAINS};filtered={k:set() for k in FILTERS}
    for family in FAMILIES:
        for timeframe in TIMEFRAMES:
            for slot in range(50):
                value=draw_configuration(42,family,timeframe,2,slot,0,True);Strategy(**value)
                assert len(active_filters(value))==2
                for key in seen:
                    seen[key].add((value['pullback_min'],value['pullback_max']) if key=='pullback_ranges' else value[key])
                for key,v in active_filters(value).items():filtered[key].add(v)
    for key,values in DOMAINS.items():assert set(values)<=seen[key],(key,set(values)-seen[key])
    for key,values in FILTERS.items():assert set(values)<=filtered[key],(key,set(values)-filtered[key])

@pytest.mark.parametrize('policy',[{'mode':'unknown'},{'include_news':1},{'minimum_signals':True},{'minimum_trades':1.5},{'minimum_sharpe':float('inf')},{'minimum_sharpe':True},{'mode':'legacy','minimum_signals':1}])
def test_strict_sampling_policy_rejects_invalid_or_ignored_settings(policy):
    from backend.lab.models import SearchSampling
    with pytest.raises(ValueError):SearchSampling(**policy)

@pytest.mark.parametrize('change',[None,{'metrics':None},{'part':True},{'part':-1},{'config_id':'bad'},{'report_sha256':'bad'},{'config':None},{'config':{}},{'config_id':'a'*64}])
def test_malformed_identity_configuration_and_cohort_reject(change):
    from backend.lab.sampling import initial_screen
    from backend.lab.models import SearchSampling
    policy=SearchSampling(mode='common_random')
    with pytest.raises(ValueError):initial_screen([None if change is None else row(0)|change],policy)
    with pytest.raises(ValueError):initial_screen([],policy)
    with pytest.raises(ValueError):initial_screen([row(0),row(0)],policy)
    with pytest.raises(ValueError):initial_screen([row(0),row(0)|{'part':1}],policy)

@pytest.mark.parametrize('start,end',[(None,'2022-01-03'),('bad','2022-01-03'),('2022-01-04','2022-01-03'),('20220103','2022-01-03')])
def test_invalid_signal_windows_reject(start,end):
    from backend.lab.sampling import count_discovery_signals
    with pytest.raises(ValueError):count_discovery_signals([],start,end)

def test_direct_preview_and_sampler_mode_guards_and_late_cancellation():
    from backend.lab.sampling import preview_recipe,sample_common,initial_screen
    from backend.lab.models import SearchSampling
    for families,frames,news in [([],['1m'],False),(['unknown'],['1m'],False),(['breakout'],['7m'],False),(['breakout'],['1m'],1),(['breakout','breakout'],['1m'],False),([True],['1m'],False)]:
        with pytest.raises(ValueError):preview_recipe(families,frames,news)
    with pytest.raises(ValueError):sample_common(request(2,mode='legacy'))
    calls=[]
    def cancel():calls.append(1);return len(calls)==2
    with pytest.raises(InterruptedError):initial_screen([row(i) for i in range(65)],SearchSampling(mode='common_random'),cancel=cancel)
