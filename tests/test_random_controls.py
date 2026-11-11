"""Independently specified conditional matching, geometry, guards and recovery."""
from dataclasses import replace
from pathlib import Path
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import minute_frame
from backend.lab import models,service
from backend.lab.api import create_app
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import DataError,normalize,prepare,save_dataset
from backend.lab.signals import Signal
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.worker import Worker
from verification.strategy_fixtures import SPEC
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
from types import SimpleNamespace

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/random-controls-contract.json').read_text())
CFG=Strategy(family='change_of_character',timeframe='1h',target='swing')
ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=10000,risk_fraction=.01,symbol_exposure=1,total_exposure=1,participation=1)


def feature(day='2026-10-05',symbol='SPY',close=200.,atr=2.,clock='14:30',duration=60):
    return dict(symbol=symbol,available_at=day+'T'+clock+':00+00:00',close=close,atr=atr,duration_minutes=duration)


def signal(side=1,name='source',day='2026-10-07'):
    when=pd.Timestamp(day+'T14:30:00Z')
    return Signal(name,'SPY',when,side,99 if side==1 else 101,1.,98 if side==1 else 102,
                  104 if side==1 else 96,1.,when,20)


def plan(features=None,signals=None,replicas=3,seed=42,cfg=CFG):
    from backend.lab.controls import make_control_plan
    actual=[signal()] if signals is None else signals
    rows=[feature(),feature('2026-10-06',close=50,atr=.5),feature('2026-10-07',close=100,atr=1)] if features is None else features
    return make_control_plan(rows,actual,cfg,'2026-10-05','2026-10-09',seed,replicas)


@pytest.mark.parametrize('case',CONTRACT['geometry_examples'],ids=lambda x:str(x['side']))
def test_atr_geometry_is_transferred_without_using_future_prices(case):
    s=signal(case['side']);result=plan([feature(),feature('2026-10-07',close=100,atr=1)],[s])
    assert result['source_count']==result['matched_count']==1
    for replica in result['replicas']:
        row=replica['matches'][0];control=row['signal']
        assert row['source_id']==s.id and control['side']==s.side
        assert control['level']==case['expected_level'] and control['stop']==case['expected_stop']
        assert control['target_swing']==case['expected_target'] and control['atr']==2
        assert control['available_at']==feature()['available_at'] and control['setup_at']==control['available_at']


@pytest.mark.parametrize('change',[dict(symbol='QQQ'),dict(clock='15:00'),dict(atr=10),dict(duration=30)])
def test_incompatible_symbol_time_volatility_or_duration_is_not_a_match(change):
    bad=feature(**change)
    result=plan([bad,feature('2026-10-07',close=100,atr=1)])
    assert result['matched_count']==0 and len(result['unmatched'])==1
    assert all(not r['matches'] for r in result['replicas'])


def test_maximum_matching_keeps_the_same_real_subset_for_every_replica():
    signals=[signal(name='a'),signal(name='b',day='2026-10-08')]
    rows=[feature(),feature('2026-10-07',close=100,atr=1),feature('2026-10-08',close=100,atr=1)]
    result=plan(rows,signals,replicas=20)
    assert result['source_count']==2 and result['matched_count']==1 and len(result['unmatched'])==1
    source_ids={m['source_id'] for r in result['replicas'] for m in r['matches']}
    assert source_ids=={'a'}


def test_multiple_sources_receive_distinct_moments_and_order_stable_streams():
    signals=[signal(name='a'),signal(name='b',day='2026-10-08')]
    rows=[feature(),feature('2026-10-06'),feature('2026-10-07',close=100,atr=1),feature('2026-10-08',close=100,atr=1)]
    first=plan(rows,signals,replicas=20)
    assert first==plan(rows[::-1],signals[::-1],replicas=20)
    assert first['replicas']==plan(rows,signals,replicas=21)['replicas'][:20]
    for replica in first['replicas']:
        assert len(replica['matches'])==2
        assert len({r['candidate_key'] for r in replica['matches']})==2
    assert len({tuple(r['candidate_key'] for r in replica['matches']) for replica in first['replicas']})==2


def test_real_signal_moments_are_never_control_candidates():
    result=plan([feature('2026-10-07',close=100,atr=1)])
    assert result['matched_count']==0


def test_future_outcome_fields_and_outside_window_rows_do_not_change_matching():
    rows=[feature(),feature('2026-10-06'),feature('2026-10-07',close=100,atr=1)]
    first=plan(rows)
    changed=[r|dict(future_return=100000,forward_high=1e9) for r in rows]
    changed.append(feature('2027-01-04'))
    assert plan(changed)==first


@pytest.mark.parametrize('s',[replace(signal(),stop=101),replace(signal(),target_swing=99),replace(signal(),atr=0)])
def test_invalid_source_geometry_is_declared_unmatched(s):
    result=plan(signals=[s]);assert result['matched_count']==0 and result['unmatched']


def test_duplicate_features_or_source_identities_reject():
    with pytest.raises(DataError):plan([feature(),feature()])
    with pytest.raises(DataError):plan(signals=[signal(),signal()])


def test_fixed_volatility_band_boundaries_do_not_fit_future_quantiles():
    from backend.lab.controls import volatility_band
    assert [volatility_band(x,100) for x in [.249999,.25,.5,1,2,4]]==[0,1,2,3,4,5]


def test_aligned_comparison_does_not_require_a_favorable_profit_sign():
    from backend.lab.controls import comparison_statistics
    real=dict(net_profit=-10,trades=2,daily_pnl=[-5,-5])
    controls=[dict(net_profit=-20,trades=2,daily_pnl=[-10,-10]),dict(net_profit=0,trades=2,daily_pnl=[0,0])]
    result=comparison_statistics(real,controls,42)
    assert result['real_net_profit']==-10 and result['mean_control_net_profit']==-10
    assert result['net_difference']==0 and result['exceedance_fraction']==pytest.approx(2/3)
    assert result['paired_pnl_interval']['low']==result['paired_pnl_interval']['high']==0
    assert result['control_at_least_real']==1 and result['control_accounts']==2


def test_incompatible_daily_series_and_zero_execution_are_not_inferential_successes():
    from backend.lab.controls import comparison_statistics
    real=dict(net_profit=0,trades=0,daily_pnl=[0,0])
    result=comparison_statistics(real,[real,real],42)
    assert result['exceedance_fraction'] is None and result['paired_pnl_interval'] is None and result['limitations']
    with pytest.raises(DataError):comparison_statistics(real,[real|dict(daily_pnl=[0])],42)


@pytest.fixture
def saved(tmp_path):
    raw=minute_frame('2026-10-05');raw[['open','high','low','close']]=[96.,96.1,95.9,96.]
    for i,value in enumerate(SPEC['common_closes']):
        raw.loc[i,['open','high','low','close']]=[value-.02,value+.1,value-.1,value]
    lab=service.Lab(tmp_path);m=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Authored controls integration'},start='2026-10-05',end='2026-10-05')
    cls=getattr(models,'ControlsExperiment',None);assert cls is not None
    cfg=Strategy(family='break_of_structure',timeframe='1m',swing_strength=2,stop_reference='level',stop_buffer=0,max_hold=24)
    request=cls(dataset_id=m['id'],strategy=cfg,replicas=3,start='2026-10-05',end='2026-10-05',costs=ZERO,portfolio=ACCOUNT)
    return lab,m,request,prepare(normalize(raw)[0])


def complete(lab,request):
    job=lab.create_controls(request);Worker(lab).run_once()
    state=lab.store.job(job['id']);assert state['status']=='completed',state['error']
    return job,lab.report(job['id'])


def test_real_worker_accounts_match_independent_execution_and_saved_parts(saved):
    lab,m,request,frame=saved;job,report=complete(lab,request)
    assert report['report_type']=='matched_random_controls' and report['matching']['matched_count']>0
    assert identity(report['numerical_contract'])==report['core_hash']
    assert len(report['books'])==5 and report['matching']['source_count']>=report['matching']['matched_count']
    for row in report['books']:
        book=lab.report(job['id'],row['part']);assert book['role']==row['role']
        expected=execute(primitive(frame),[s|{'config_id':identity(request.strategy)} for s in book['signals']],
            {identity(request.strategy):request.strategy.model_dump()},request.costs.model_dump(),request.portfolio.model_dump(),start=str(request.start),end=str(request.end))
        assert_parity(SimpleNamespace(**book),expected)
    assert service.Lab(lab.root).report(job['id'])==report


def test_cancel_resume_reuses_only_hash_verified_completed_accounts(saved,monkeypatch):
    lab,_,request,_=saved;job=lab.create_controls(request);worker=Worker(lab);original=worker._progress
    def cancel_after_book(j,fraction,note,checkpoint=None):
        if checkpoint==3:lab.store.cancel(j['id'])
        return original(j,fraction,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',cancel_after_book);worker.run_once()
    assert lab.store.job(job['id'])['status']=='canceled' and not lab.output_path(job['id']).exists()
    parts=lab.root/'data/jobs'/job['id']/'parts'
    before={p.name:p.read_bytes() for p in parts.glob('*.json.gz')};assert len(before)==3
    lab.store.resume(job['id']);Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    for name,value in before.items():assert (parts/name).read_bytes()==value
    _,direct=complete(lab,request);assert lab.report(job['id'])==direct


def test_real_controls_api_exports_and_invalid_replicas(saved):
    lab,_,request,_=saved
    with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        result=client.post('/api/controls',json=request.model_dump(mode='json'));assert result.status_code==202,result.text
        job=result.json();Worker(client.app.state.lab).run_once()
        report=client.get('/api/jobs/'+job['id']+'/report').json()
        assert report==client.get('/api/jobs/'+job['id']+'/export/json').json()
        aggregate_csv=client.get('/api/jobs/'+job['id']+'/export/csv')
        assert aggregate_csv.status_code==400 and 'account' in aggregate_csv.json()['detail'].lower()
        for count in [0,1,201]:
            assert client.post('/api/controls',json=request.model_dump(mode='json')|dict(replicas=count)).status_code==422


def test_controls_cannot_read_sealed_dates_through_direct_or_queued_paths(tmp_path,monkeypatch):
    lab=service.Lab(tmp_path);days=['2026-10-05','2026-10-06','2026-10-07']
    m=save_dataset(lab.datasets_root,pd.concat([minute_frame(d) for d in days]),{'input_kind':'synthetic'},start=days[0],end=days[-1])
    lab.register_study(Study(name='Sealed',dataset_id=m['id'],discovery=dict(start=days[0],end=days[0]),validation=dict(start=days[1],end=days[1]),holdout=dict(start=days[-1],end=days[-1]),configurations=[Strategy()]))
    def forbidden(*args,**kwargs):raise AssertionError('Protected price read')
    monkeypatch.setattr(service,'load_window',forbidden)
    cls=getattr(models,'ControlsExperiment',None);assert cls is not None
    request=cls(dataset_id=m['id'],strategy=CFG,start=days[0],end=days[-1],replicas=2)
    with pytest.raises(ResearchError):lab.create_controls(request)
    with pytest.raises(ResearchError):lab.control_context(request.model_dump(mode='json'))
    assert not lab.store.jobs()


def test_lower_trigger_uses_only_the_last_completed_setup_atr():
    from backend.lab.controls import feature_table
    raw=minute_frame('2026-10-05');raw['high']=101.;raw['low']=99.
    cfg=Strategy(timeframe='5m',trigger_timeframe='1m')
    first=feature_table(prepare(normalize(raw)[0]),cfg)
    assert first[0]['available_at']==pd.Timestamp('2026-10-05T14:45:00Z').isoformat()
    assert first[0]['atr']==2 and first[0]['duration_minutes']==1
    cutoff=pd.Timestamp('2026-10-05T14:46:00Z')
    raw.loc[raw.timestamp>=cutoff,'high']=1000000
    second=feature_table(prepare(normalize(raw)[0]),cfg)
    assert [r for r in first if pd.Timestamp(r['available_at'])<=cutoff]==[r for r in second if pd.Timestamp(r['available_at'])<=cutoff]


@pytest.mark.parametrize('kwargs',[dict(replicas=0),dict(replicas=201),dict(replicas=2.5),dict(seed=-1)])
def test_invalid_randomization_controls_reject(kwargs):
    with pytest.raises(DataError):plan(**kwargs)


@pytest.mark.parametrize('field,value',[('available_at','2026-10-05T14:30:00'),('atr',0),('close',float('nan')),('duration_minutes',0)])
def test_invalid_feature_contract_rejects(field,value):
    with pytest.raises(DataError):plan([feature()|{field:value}])


@pytest.mark.parametrize('limit',['MAX_EDGES','MAX_STORED_CONTROLS'])
def test_actual_matching_work_bounds_fail_explicitly_without_silent_sampling(monkeypatch,limit):
    from backend.lab import controls
    monkeypatch.setattr(controls,limit,0)
    with pytest.raises(DataError):plan()


def test_controls_reject_unversioned_news_scenarios(saved):
    _,_,request,_=saved
    for value in [dict(news_dates=['2026-10-05']),dict(strategy=request.strategy.model_dump()|dict(news='half'))]:
        with pytest.raises(ValidationError):models.ControlsExperiment(**(request.model_dump(mode='json')|value))


def test_empty_real_signals_complete_as_insufficient_evidence(saved):
    lab,_,request,_=saved
    request.strategy=Strategy(family='fair_value_gap',timeframe='1d')
    job,report=complete(lab,request)
    assert report['matching']['source_count']==report['matching']['matched_count']==0
    assert len(report['books'])==2 and report['comparison']['exceedance_fraction'] is None

def test_no_match_control_cancel_resume_keeps_unused_replicas_explicit(saved,monkeypatch):
    lab,_,request,_=saved;request.strategy=Strategy(family='fair_value_gap',timeframe='1d')
    job=lab.create_controls(request);worker=Worker(lab);original=worker._progress
    def stop(j,fraction,note,checkpoint=None):
        if checkpoint==1:lab.store.cancel(j['id'])
        return original(j,fraction,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once();assert lab.store.job(job['id'])['status']=='canceled'
    unused=[r for r in lab.store.registry(job_id=job['id'])['rows'] if r['role']=='random_control']
    assert len(unused)==request.replicas and all(r['state']=='not_generated' and r['attempts']==0 for r in unused)
    lab.store.resume(job['id']);Worker(lab).run_once();state=lab.store.job(job['id'])
    assert state['status']=='completed',state['error']


def test_tampered_checkpoint_fails_instead_of_reusing_it(saved,monkeypatch):
    lab,_,request,_=saved;job=lab.create_controls(request);worker=Worker(lab);original=worker._progress
    def stop(j,fraction,note,checkpoint=None):
        if checkpoint==1:lab.store.cancel(j['id'])
        return original(j,fraction,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once()
    part=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz';assert part.exists()
    part.write_bytes(b'tampered')
    lab.store.resume(job['id']);Worker(lab).run_once()
    state=lab.store.job(job['id']);assert state['status']=='failed' and 'integrity' in state['error']
    assert not lab.output_path(job['id']).exists()


def test_augmented_matching_finds_a_full_assignment_where_greedy_fails():
    from backend.lab.controls import _maximum_matching
    # a can use x or y; b only x. Canonical greedy a->x would strand b.
    assert _maximum_matching(['a','b'],{'a':['x','y'],'b':['x']},lambda s,k:k)=={'a':'y','b':'x'}


def test_matching_cardinality_and_canonical_subset_match_independent_exhaustive_search():
    from itertools import combinations,permutations
    from random import Random
    from backend.lab.controls import _maximum_matching
    rng=Random(9281)
    for _ in range(100):
        sources=['a','b','c','d'];moments=['v','w','x','y','z']
        pools={s:[m for m in moments if rng.random()<.4] for s in sources}
        expected=()
        for count in range(len(sources),0,-1):
            feasible=[]
            for subset in combinations(sources,count):
                if any(all(moment in pools[source] for source,moment in zip(subset,assignment)) for assignment in permutations(moments,count)):
                    feasible.append(subset)
            if feasible:expected=min(feasible);break
        actual=_maximum_matching(sources,pools,lambda s,k:k)
        assert tuple(sorted(actual))==expected
        assert len(set(actual.values()))==len(actual)
        assert all(moment in pools[source] for source,moment in actual.items())


def test_single_source_hash_rank_matches_independent_stdlib_encoding():
    import hashlib
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    result=plan(replicas=20)
    cfg=digest(CFG.model_dump())
    keys=['SPY|'+feature(day)['available_at'] for day in ['2026-10-05','2026-10-06']]
    for i,replica in enumerate(result['replicas']):
        stream=dict(policy=1,seed=42,configuration=cfg,replica=i)
        expected=min(keys,key=lambda key:digest(stream|dict(source='source',candidate=key)))
        assert replica['stream_key']==digest(stream) and replica['matches'][0]['candidate_key']==expected


def test_part_corruption_is_detected_on_actual_export_read(saved):
    lab,_,request,_=saved;job,_=complete(lab,request)
    path=lab.root/'data/jobs'/job['id']/'parts/000002.json.gz';path.write_bytes(b'tampered')
    with pytest.raises(ValueError,match='integrity'):lab.report(job['id'],2)


def test_nonpositive_source_weight_cannot_become_a_matched_risk_budget():
    assert plan(signals=[replace(signal(),weight=0)])['matched_count']==0


def test_incomplete_setup_candles_and_cancellation_have_no_control_features():
    from backend.lab.controls import feature_table,_maximum_matching,make_control_plan
    regular=prepare(normalize(minute_frame('2026-10-05').iloc[:5])[0])
    assert feature_table(regular,CFG)==[]
    with pytest.raises(InterruptedError):feature_table(regular,CFG,cancel=lambda:True)
    with pytest.raises(InterruptedError):make_control_plan([feature()],[signal()],CFG,'2026-10-05','2026-10-09',cancel=lambda:True)
    calls=[]
    def nested_cancel():calls.append(1);return len(calls)==2
    with pytest.raises(InterruptedError):_maximum_matching(['a'],{'a':['x']},lambda s,k:k,nested_cancel)
