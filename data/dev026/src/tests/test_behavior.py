"""Independent behavior outcome/shift/uncertainty contracts and actual job paths."""
from pathlib import Path
from types import SimpleNamespace
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import minute_frame
from backend.lab import models,service
from backend.lab.api import create_app
from backend.lab.config import Strategy,identity
from backend.lab.data import normalize,prepare,DataError,save_dataset
from backend.lab.signals import contexts
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.worker import Worker
from verification.strategy_fixtures import SPEC

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/behavior-contract.json').read_text())


def path(future=None,count=50,touch_close=100,touch_high=100.1):
    rows=[dict(open=100,high=touch_high,low=min(99.9,touch_close),close=touch_close)]
    rows.extend(dict(open=100,high=100.5,low=99.9,close=100) for _ in range(count))
    if future:rows[1].update(future)
    return rows


def score(rows,side=1):
    from backend.lab.behavior import score_touch
    if side==-1:
        rows=[dict(open=200-r['open'],high=200-r['low'],low=200-r['high'],close=200-r['close']) for r in rows]
    return score_touch(rows,0,100,100,side,1,50)


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('future,outcome,after',[
    (dict(high=101,close=100.5),'hold',1),
    (dict(high=100.5,low=99,close=99.74),'break',1),
    (dict(high=101,low=99,close=99.7),'hold',1),
    (dict(high=100.5,low=99.75,close=99.75),'unresolved',None)])
def test_touch_scoring_exact_thresholds_mirror_and_close_order(future,outcome,after,side):
    result=score(path(future),side)
    assert result['outcome']==outcome and result['resolved_after_bars']==after and result['complete_horizon']


def test_touch_bar_favorable_extreme_is_not_a_future_bounce():
    assert score(path(touch_high=102))['outcome']=='unresolved'
    result=score(path(touch_close=99.7));assert result['outcome']=='break' and result['resolved_after_bars']==0


def test_right_edge_is_censored_even_if_partial_path_won():
    result=score(path(dict(high=101,close=100.5),count=3))
    assert result['outcome']=='censored' and result['observed_outcome']=='hold' and not result['complete_horizon']


def test_zone_near_and_far_boundaries_have_distinct_roles():
    from backend.lab.behavior import score_touch
    rows=path(dict(high=102,close=100.5))
    result=score_touch(rows,0,99,101,1,1,50)
    assert result['outcome']=='hold' and result['resolved_after_bars']==1
    assert result['max_favorable_atr']==1


def test_gap_fill_is_a_separate_complete_horizon_measure():
    from backend.lab.behavior import score_gap_fill
    rows=path(dict(low=98.9,close=99.5))
    assert score_gap_fill(rows,0,99,101,1,50)['filled'] is True
    result=score_gap_fill(rows[:4],0,99,101,1,50)
    assert result['filled'] is None and result['observed_fill'] is True


def test_seeded_shift_has_birth_distance_and_does_not_look_at_outcomes():
    from backend.lab.behavior import choose_shift
    feature=dict(id='known',lo=100.,hi=100.,atr=1.)
    first=choose_shift(feature,[(99,99),(100,100),(101,101)],42,0)
    assert first==choose_shift(feature|dict(future_profit=9999),[(99,99),(100,100),(101,101)],42,0)
    assert 1<=abs(first['offset'])<=3
    for level in [99,100,101]:assert abs(100+first['offset']-level)>=.5
    assert first['attempts']<=128
    assert choose_shift(feature,[(-1000,1000)],42,0) is None


def test_bootstrap_uses_whole_sessions_and_zero_denominator_is_honest():
    from backend.lab.behavior import session_contrast
    rows=[dict(session=d,group=g,value=1 if g=='real' else 0) for d in ['2026-10-05','2026-10-06'] for g in ['real','control']]
    result=session_contrast(rows,['2026-10-05','2026-10-06'],42)
    assert result['difference']==result['interval']['low']==result['interval']['high']==1
    assert result['valid_resamples']==2000
    missing=session_contrast(rows[:1],['2026-10-05','2026-10-06'],42)
    assert missing['difference'] is None and missing['interval'] is None


def test_context_observer_cannot_change_detector_state():
    from backend.lab.data import aggregate
    raw=minute_frame('2026-10-05');cfg=Strategy(timeframe='1m',swing_strength=2)
    for i,value in enumerate(SPEC['common_closes']):raw.loc[i,['open','high','low','close']]=[value-.02,value+.1,value-.1,value]
    bars=aggregate(prepare(normalize(raw)[0]),'1m');plain=contexts(bars,cfg);observations=[]
    def observer(index,bar,row,state):
        observations.append((index,bar.copy(),state.copy()));row['atr']=999;state['levels']=();bar['close']=-1
    audited=contexts(bars,cfg,observer=observer)
    pd.testing.assert_frame_equal(plain,audited)
    assert len(observations)==len(bars) and any(s['levels'] for _,_,s in observations)


@pytest.fixture
def saved(tmp_path):
    raw=minute_frame('2026-10-05');raw[['open','high','low','close']]=[96.,96.1,95.9,96.]
    for i,value in enumerate(SPEC['common_closes']):raw.loc[i,['open','high','low','close']]=[value-.02,value+.1,value-.1,value]
    lab=service.Lab(tmp_path);m=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Authored behavior chart'},start='2026-10-05',end='2026-10-05')
    cls=getattr(models,'BehaviorExperiment',None);assert cls is not None
    request=cls(dataset_id=m['id'],start='2026-10-05',end='2026-10-05',timeframes=['1m'],shift_replicas=2)
    return lab,m,request


def test_actual_behavior_worker_has_all_tables_and_hashed_parts(saved):
    lab,_,request=saved;job=lab.create_behavior(request);Worker(lab).run_once()
    state=lab.store.job(job['id']);assert state['status']=='completed',state['error']
    report=lab.report(job['id']);assert report['report_type']=='price_behavior'
    assert set(report['tables'])==set(CONTRACT['tables']) and identity(report['numerical_contract'])==report['core_hash']
    part=lab.report(job['id'],0)
    assert part['touches'] and part['features'] and part['bars']['SPY']
    assert report['counts']['real_touches']>0 and any(t['group']=='control' for t in part['touches'])
    assert service.Lab(lab.root).report(job['id'])==report


def test_actual_api_behavior_json_table_csv_and_invalid_options(saved):
    lab,_,request=saved
    with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        created=client.post('/api/behavior',json=request.model_dump(mode='json'));assert created.status_code==202,created.text
        job=created.json();Worker(client.app.state.lab).run_once()
        report=client.get('/api/jobs/'+job['id']+'/report').json()
        assert client.get('/api/jobs/'+job['id']+'/export/json').json()==report
        result=client.get('/api/jobs/'+job['id']+'/export/csv?table=levels_vs_shifted')
        assert result.status_code==200 and 'real_n' in result.text
        assert client.get('/api/jobs/'+job['id']+'/export/csv').status_code==400
        for update in [dict(timeframes=['bad']),dict(timeframes=['1m','1m']),dict(shift_replicas=0),dict(costs={})]:
            assert client.post('/api/behavior',json=request.model_dump(mode='json')|update).status_code==422


def test_behavior_rejects_sealed_dates_before_raw_reads(tmp_path,monkeypatch):
    lab=service.Lab(tmp_path);days=['2026-10-05','2026-10-06','2026-10-07']
    m=save_dataset(lab.datasets_root,pd.concat([minute_frame(d) for d in days]),{'input_kind':'synthetic'},start=days[0],end=days[-1])
    lab.register_study(Study(name='Sealed',dataset_id=m['id'],discovery=dict(start=days[0],end=days[0]),validation=dict(start=days[1],end=days[1]),holdout=dict(start=days[2],end=days[2]),configurations=[Strategy()]))
    def forbidden(*args,**kwargs):raise AssertionError('Protected prices were read')
    monkeypatch.setattr(service,'load_window',forbidden)
    cls=getattr(models,'BehaviorExperiment',None);assert cls is not None
    request=cls(dataset_id=m['id'],start=days[0],end=days[-1],timeframes=['1h'])
    with pytest.raises(ResearchError):lab.create_behavior(request)
    with pytest.raises(ResearchError):lab.behavior_context(request.model_dump(mode='json'))
    assert not lab.store.jobs()


def test_one_session_cannot_supply_a_nominal_confidence_interval():
    from backend.lab.behavior import session_contrast
    result=session_contrast([dict(session='2026-10-05',group='real',value=1),dict(session='2026-10-05',group='control',value=0)],['2026-10-05'])
    assert result['difference']==1 and result['interval'] is None and result['attempted_resamples']==0


def test_prices_after_explicit_end_cannot_resolve_edge_observations(saved):
    from backend.lab.behavior import analyze_chart
    lab,m,request=saved;payload=request.model_dump(mode='json');context=lab.behavior_context(payload)
    original=context['regular'];later=prepare(normalize(minute_frame('2026-10-06',close=[80,120,90]))[0])
    first=analyze_chart(original,'1m',str(request.start),str(request.end),42,2)
    second=analyze_chart(pd.concat([original,later]),'1m',str(request.start),str(request.end),42,2)
    assert first==second


def test_all_seventeen_tables_have_distinct_discriminating_measurements():
    from backend.lab.behavior import build_tables
    touches=[];pairs=[];fills=[];days=['2026-10-05','2026-10-06']
    for day in days:
        for group in ['real','control']:
            base=dict(session=day,symbol='SPY',timeframe='1m',group=group,replica=None if group=='real' else 0,
                      complete_horizon=True,matchable=True,outcome='hold' if group=='real' else 'break',
                      max_favorable_atr=2.,max_adverse_atr=.5,visit=1,feature_id=day+group,index=1)
            for kind,shape in [('level','line'),('level','zone'),('flip','zone'),('trend_line','line'),('gap','zone'),('supply_demand','zone')]:
                touches.append(base|dict(kind=kind,shape=shape))
            touches.append(base|dict(kind='level',shape='line',visit=2,index=2,max_favorable_atr=1 if group=='real' else 3))
            fills.append(base|dict(filled=group=='real'))
            for kind in ['bos','choch','wick_break','close_break','sweep','pullback','engulfing','rejection']:
                for horizon in [10,20,50]:pairs.append(base|dict(kind=kind,horizon=horizon,value=.5 if group=='real' else .25,recent_sweep=True,depth_atr=1.5))
    chart=dict(touches=touches,moment_pairs=pairs,gap_fills=fills,sessions=days)
    tables,_=build_tables([chart],days[0],days[-1])
    assert set(tables)==set(CONTRACT['tables'])
    for key,table in tables.items():
        pooled=[r for r in table['rows'] if r['scope']=='pooled']
        assert pooled and all(r['real_n']>0 and r['control_n']>0 for r in pooled),key
        if key in {'bos_forward','choch_forward','wick_vs_close','sweep_vs_close','sweep_started_trends','pullback_depth','engulfing_at_levels','rejection_at_levels'}:
            assert {r['horizon'] for r in pooled}=={10,20,50}
            assert all(r['difference']==.25 and r['unit']=='ATR' for r in pooled)
    row=next(r for r in tables['shrinking_bounces']['rows'] if r['scope']=='pooled')
    assert row['real_mean']==-1 and row['control_mean']==1 and row['difference']==-2


def test_behavior_bootstrap_matches_independent_session_loop():
    import numpy as np
    from verification.reference_statistics import linear_quantile
    from backend.lab.behavior import session_contrast
    days=['2026-10-05','2026-10-06']
    values=[[(1,2),(2,1)],[(3,4,5),(0,1)]]
    records=[dict(session=day,group=group,value=value) for day,day_values in zip(days,values) for group,nums in zip(['real','control'],day_values) for value in nums]
    expected=[]
    for draw in np.random.default_rng(13).integers(0,2,size=(2000,2)):
        real=[];control=[]
        for index in draw:real.extend(values[int(index)][0]);control.extend(values[int(index)][1])
        expected.append(sum(real)/len(real)-sum(control)/len(control))
    actual=session_contrast(records,days,13)
    assert actual['interval']['low']==pytest.approx(linear_quantile(expected,.025),abs=1e-10)
    assert actual['interval']['high']==pytest.approx(linear_quantile(expected,.975),abs=1e-10)


def test_birth_shift_draws_do_not_depend_on_later_prices(saved):
    from backend.lab.behavior import analyze_chart
    lab,_,request=saved;regular=lab.behavior_context(request.model_dump(mode='json'))['regular']
    changed=regular.copy();cutoff=regular.timestamp.iloc[60]
    changed.loc[changed.timestamp>=cutoff,['high','low','close','open']]=[200.,1.,100.,100.]
    a=analyze_chart(regular,'1m',str(request.start),str(request.end),42,2)
    b=analyze_chart(changed,'1m',str(request.start),str(request.end),42,2)
    first=lambda chart:[f for f in chart['features'] if pd.Timestamp(f['available_at'])<=cutoff]
    assert first(a)==first(b)


def test_shifted_geometry_already_invalid_at_birth_never_reopens(saved):
    from backend.lab.behavior import analyze_chart
    lab,_,request=saved;regular=lab.behavior_context(request.model_dump(mode='json'))['regular']
    chart=analyze_chart(regular,'1m',str(request.start),str(request.end),42,2)
    prices={pd.Timestamp(b['available_at']):b['close'] for b in chart['bars']['SPY']}
    forbidden=[]
    for f in chart['features']:
        if not f['matchable']:continue
        for replica,draw in enumerate(f['shift_draws']):
            for shape in (['line','zone'] if f['kind']=='level' else ['line'] if f['kind']=='trend_line' else ['zone']):
                pad=.25*f['atr'] if f['kind']=='level' and shape=='zone' else 0
                far=f['lo']-pad+draw['offset'] if f['side']==1 else f['hi']+pad+draw['offset']
                if f['side']*(prices[pd.Timestamp(f['available_at'])]-far)<-.25*f['atr']:forbidden.append((f['id'],replica,shape))
    assert forbidden,'Authored path must exercise a shifted geometry born on its invalid side.'
    assert not [t for t in chart['touches'] if t['group']=='control' and (t['feature_id'],t['replica'],t['shape']) in forbidden]
    # Construct a recovery followed by a separated retouch. Birth geometry and
    # seed are unchanged; this cannot resurrect an already invalid stand-in.
    candidates=[(f,replica,shape) for fid,replica,shape in forbidden for f in chart['features']
                if f['id']==fid and f['kind'] in {'gap','supply_demand'} and f['born']+53<len(regular)]
    assert candidates
    f,replica,shape=candidates[0];offset=f['shift_draws'][replica]['offset'];side=f['side'];a=f['atr'];i=f['born']
    near=(f['hi'] if side==1 else f['lo'])+offset
    changed=regular.copy()
    for j in [i+1,i+2]:
        opened=float(changed.iloc[i].close) if j==i+1 else near+side*2*a
        closed=near+side*2*a
        changed.loc[changed.index[j],['open','high','low','close']]=[opened,max(opened,closed)+.1*a,min(opened,closed)-.1*a,closed]
    closed=near+side*.1*a
    changed.loc[changed.index[i+3],['open','high','low','close']]=[closed,max(closed,near+.05*a),min(closed,near-.05*a),closed]
    replay=analyze_chart(changed,'1m',str(request.start),str(request.end),42,2)
    assert not [t for t in replay['touches'] if t['group']=='control' and (t['feature_id'],t['replica'],t['shape'])==(f['id'],replica,shape)]


def test_primary_and_resolved_only_denominators_remain_distinct():
    from backend.lab.behavior import build_tables
    rows=[]
    for group in ['real','control']:
        for i,outcome in enumerate(['hold','unresolved']):
            rows.append(dict(session='2026-10-05',symbol='SPY',timeframe='1m',group=group,replica=None if group=='real' else 0,
                feature_id=str(i),index=i,kind='level',shape='line',visit=1,matchable=True,complete_horizon=True,
                outcome=outcome,max_adverse_atr=0,max_favorable_atr=1))
    tables,_=build_tables([dict(touches=rows,moment_pairs=[],gap_fills=[],sessions=['2026-10-05'])],'2026-10-05','2026-10-05')
    pooled={r['metric']:r for r in tables['levels_vs_shifted']['rows'] if r['scope']=='pooled'}
    assert pooled['hold_fraction']['real_mean']==.5 and pooled['hold_fraction']['real_n']==2
    assert pooled['hold_fraction_resolved_only']['real_mean']==1 and pooled['hold_fraction_resolved_only']['real_n']==1
    assert all(r['real_unresolved']==1 and r['real_full_sample_n']==2 for r in pooled.values())


def cancel_after_first_part(lab,request,monkeypatch):
    request.timeframes=['1m','5m'];job=lab.create_behavior(request);worker=Worker(lab);original=worker._progress
    def stop(j,fraction,note,checkpoint=None):
        if checkpoint==1:lab.store.cancel(j['id'])
        return original(j,fraction,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once()
    assert lab.store.job(job['id'])['status']=='canceled'
    assert not lab.output_path(job['id']).exists()
    part=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz';assert part.exists()
    return job,part


def test_behavior_cancel_resume_reuses_content_bound_complete_chart(saved,monkeypatch):
    lab,_,request=saved;job,part=cancel_after_first_part(lab,request,monkeypatch);before=part.read_bytes()
    original=lab.behavior_chart;seen=[]
    def observe(context,payload,timeframe,cancel):
        seen.append(timeframe);assert timeframe!='1m','Saved chart must be reused'
        return original(context,payload,timeframe,cancel)
    monkeypatch.setattr(lab,'behavior_chart',observe)
    lab.store.resume(job['id']);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed' and part.read_bytes()==before and seen==['5m']
    assert len(lab.result(job['id'])['rows'])==2


def test_behavior_corrupt_checkpoint_is_not_reused(saved,monkeypatch):
    lab,_,request=saved;job,part=cancel_after_first_part(lab,request,monkeypatch);part.write_bytes(b'corrupt')
    lab.store.resume(job['id']);Worker(lab).run_once();state=lab.store.job(job['id'])
    assert state['status']=='failed' and 'integrity' in state['error'] and not lab.output_path(job['id']).exists()


def test_behavior_untrusted_orphan_recomputes(saved,monkeypatch):
    lab,_,request=saved;job=lab.create_behavior(request);destination=lab.root/'data/jobs'/job['id']/'parts'
    destination.mkdir(parents=True);(destination/'000000.json.gz').write_bytes(b'untrusted orphan')
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    assert lab.report(job['id'],0)['features']


@pytest.mark.parametrize('field,value',[
    ('swing_strength',2),('level_tolerance',.5),('touch_horizon',49),('bootstrap_resamples',1999),
    ('timeframes',[]),('shift_replicas',21),('seed',-1),('news_dates',[])])
def test_behavior_fixed_source_contract_rejects_unsupported_options(field,value):
    with pytest.raises(ValidationError):models.BehaviorExperiment(dataset_id='a'*24,start='2026-10-05',end='2026-10-06',**{field:value})


@pytest.mark.parametrize('update',[dict(index=-1),dict(side=0),dict(lo=101,hi=100),dict(atr=0),dict(atr=float('nan')),dict(horizon=0),dict(horizon=True),dict(horizon=501)])
def test_behavior_invalid_outcome_geometry_rejects(update):
    from backend.lab.behavior import score_touch
    values=dict(rows=path(),index=0,lo=100,hi=100,side=1,atr=1,horizon=50)|update
    with pytest.raises(DataError):score_touch(**values)


@pytest.mark.parametrize('feature',[dict(id='bad',lo=2,hi=1,atr=1),dict(id='bad',lo=1,hi=1,atr=0),dict(id='bad',lo=1,hi=float('inf'),atr=1)])
def test_shift_invalid_birth_geometry_rejects(feature):
    from backend.lab.behavior import choose_shift
    with pytest.raises(DataError):choose_shift(feature,[],42,0)


def test_nonpositive_shifted_prices_are_rejected_before_accepting_a_draw():
    from backend.lab.behavior import choose_shift
    feature=dict(id='near-zero',lo=.01,hi=.01,atr=1)
    for seed in range(10):
        draw=choose_shift(feature,[],seed,0)
        assert feature['lo']+draw['offset']>0
    # This chosen independent hash stream initially proposes a negative price.
    from verification.behavior_reference_run import digest
    rejected=[seed for seed in range(10) if not (int(digest(dict(seed=seed,feature='near-zero',replica=0,attempt=0,policy=1)),16)>>24)&1]
    assert rejected and all(choose_shift(feature,[],seed,0)['attempts']>1 for seed in rejected)


@pytest.mark.parametrize('rows,days,resamples',[
    ([],[],2000),([],['2026-10-05']*2,2000),([],['2026-10-05'],1),
    ([dict(session='other',group='real',value=1)],['2026-10-05'],2000),
    ([dict(session='2026-10-05',group='bad',value=1)],['2026-10-05'],2000),
    ([dict(session='2026-10-05',group='real',value=float('nan'))],['2026-10-05'],2000)])
def test_behavior_invalid_session_observations_reject(rows,days,resamples):
    from backend.lab.behavior import session_contrast
    with pytest.raises(DataError):session_contrast(rows,days,resamples=resamples)


def test_behavior_cancellation_reaches_each_numerical_phase(saved):
    from backend.lab.behavior import analyze_chart,build_tables
    lab,_,request=saved;regular=lab.behavior_context(request.model_dump(mode='json'))['regular']
    with pytest.raises(InterruptedError,match='analysis canceled'):analyze_chart(regular,'1m',str(request.start),str(request.end),cancel=lambda:True)
    with pytest.raises(InterruptedError,match='tables canceled'):build_tables([dict(sessions=['2026-10-05'],touches=[{}])],'2026-10-05','2026-10-05',cancel=lambda:True)
    event=dict(session='2026-10-05',symbol='SPY',timeframe='1m',group='real',kind='bos',horizon=10,value=1)
    with pytest.raises(InterruptedError,match='uncertainty canceled'):
        build_tables([dict(sessions=['2026-10-05'],touches=[],gap_fills=[],moment_pairs=[event])],'2026-10-05','2026-10-05',cancel=lambda:True)
    assert analyze_chart(regular.iloc[:1],'5m',str(request.start),str(request.end),replicas=2)['features']==[]
    with pytest.raises(DataError):analyze_chart(regular,'1m',str(request.start),str(request.end),replicas=True)


@pytest.mark.parametrize('side',[1,-1])
def test_actual_pullback_and_all_censored_forward_records(side):
    from verification.strategy_fixtures import scenario
    from backend.lab.behavior import analyze_chart
    regular,expected=scenario('trend_pullback','1m',side)
    # The supplied authored chart ends just after the candidate, so every
    # observation needs to remain explicitly censored at all three horizons.
    chart=analyze_chart(regular,'1m',str(regular.session.min()),str(regular.session.max()),replicas=2)
    pullbacks=[e for e in chart['moments'] if e['kind']=='pullback']
    assert pullbacks and any(e['side']==side and e['depth_atr']>0 for e in pullbacks)
    for event in pullbacks:
        measures=[m for m in chart['moment_assessments'] if m['id']==event['id']]
        assert {m['horizon'] for m in measures}=={10,20,50}
        assert all(m['status']=='censored' and m['value'] is None for m in measures)
