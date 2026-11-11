"""D046 authored matching/stream/grading contracts, before implementation.

These are not execution, authority, API, lifecycle or 10000 financial-set proofs.
"""
import copy, hashlib, importlib, importlib.util, json
from decimal import Decimal
from fractions import Fraction
import numpy as np
import pandas as pd
import pytest
from backend.lab.data import schedule

PARENT='a'*64
START='2026-10-05';END='2026-10-07'

def test_trade_twin_module_exists_for_executable_contract():
    assert importlib.util.find_spec('backend.lab.trade_twins') is not None, 'D046 complete-cohort twin core has not been implemented.'

@pytest.fixture
def twins():
    assert importlib.util.find_spec('backend.lab.trade_twins') is not None, 'D046 complete-cohort twin core has not been implemented.'
    return importlib.import_module('backend.lab.trade_twins')

def clock(start=START,end=END,symbols=('SPY',)):
    values=[t.isoformat() for opened,closed in schedule(start,end).values() for t in pd.date_range(opened,closed,freq='min',inclusive='left')]
    return {symbol:values[:] for symbol in symbols}

def source(**changes):
    return dict(trade_id='real-a',symbol='SPY',side=1,entry_at='2026-10-07T14:30:00Z',exit_at='2026-10-07T14:35:00Z',
        exit_boundary='close',entry_price=100.,entry_atr=2.,atr_available_at='2026-10-07T14:30:00Z',
        entry_stop=98.,entry_target=106.,quantity=10,net_profit=25.)|changes

def moment(day='2026-10-05',**changes):
    return dict(symbol='SPY',entry_at=day+'T14:30:00Z',reference_price=200.,atr=4.,atr_available_at=day+'T14:29:00Z')|changes

def prepare(twins,sources=None,moments=None,minutes=None,start=START,end=END,**changes):
    return twins.prepare_plan([source()] if sources is None else sources,
        [moment(),moment('2026-10-06')] if moments is None else moments,
        clock(start,end) if minutes is None else minutes,start,end,PARENT,**changes)

def outcomes(plan,seed=42,policy='barrier_capped_elapsed_v1',count=10000,exceed=499):
    for i in range(count):
        yield dict(plan_hash=plan.plan_hash,seed=seed,policy=policy,set_index=i,trade_count=len(plan.sources),
            state='completed',net_profit=25. if i<exceed else -12.,error=None)

def test_source_cohort_plan_is_complete_sorted_and_geometry_matches_independent_fraction_oracle(twins):
    sources=[source(),source(trade_id='real-b',side=-1,entry_stop=102.,entry_target=94.)]
    plan=prepare(twins,sources=sources)
    assert plan.eligible and len(plan.sources)==2 and plan.pools==((0,1),(0,1))
    drawn=twins.draw_set(plan,42,0)
    assert len(drawn['matches'])==2 and drawn['plan_hash']==plan.plan_hash
    for row,s in zip(drawn['matches'],plan.sources):
        assert row['source_id']==s.trade_id and row['quantity']==10 and row['side']==s.side
        assert Fraction(row['stop'])==Fraction(200)-s.side*Fraction(str(s.side*(s.entry_price-s.entry_stop)))/Fraction(str(s.entry_atr))*Fraction(4)
        assert Fraction(row['target'])==Fraction(200)+s.side*Fraction(str(s.side*(s.entry_target-s.entry_price)))/Fraction(str(s.entry_atr))*Fraction(4)
        assert row['holding_minutes']==5 and row['cutoff_at']==(pd.Timestamp(row['entry_at'])+pd.Timedelta(minutes=5)).isoformat()

@pytest.mark.parametrize('field,value',[('side',True),('side',1.0),('side',0),('quantity',True),('quantity',1.5),('quantity',0),
    ('entry_price',float('nan')),('entry_price',True),('entry_atr',0.),('entry_atr',float('inf')),('entry_stop',0.),
    ('entry_target',float('-inf')),('entry_at','2026-10-07T14:30:00'),('entry_at','2026-10-07T14:30:01Z'),
    ('exit_at','2026-10-07T14:29:00Z'),('atr_available_at','2026-10-07T14:31:00Z'),('symbol','spy'),
    ('trade_id',''),('entry_stop',101.),('entry_target',99.),('net_profit',float('nan')),('exit_boundary','later'),('future_win',True)])
def test_strict_source_contract_rejects_invalid_and_unknown_fields(twins,field,value):
    with pytest.raises(ValueError):prepare(twins,sources=[source(**{field:value})])

@pytest.mark.parametrize('field,value',[('reference_price',0.),('reference_price',True),('atr',-1.),('atr',float('inf')),
    ('entry_at','2026-10-05T14:30:01Z'),('atr_available_at','2026-10-05T14:31:00Z'),('future_high',500.),
    ('net_profit',1000.),('entry_at','2026-10-05T14:30:00'),('symbol','BAD SYMBOL')])
def test_candidate_schema_rejects_future_outcomes_and_invalid_features(twins,field,value):
    with pytest.raises(ValueError):prepare(twins,moments=[moment(**{field:value})])

@pytest.mark.parametrize('which',['source','moment','clock'])
def test_duplicate_original_identities_are_rejected(twins,which):
    s=[source()];m=[moment()];c=clock()
    if which=='source':s*=2
    if which=='moment':m*=2
    if which=='clock':c['SPY'].append(c['SPY'][0])
    with pytest.raises(ValueError):prepare(twins,sources=s,moments=m,minutes=c)

@pytest.mark.parametrize('change',['missing_minute','missing_session','extra_after_close','missing_symbol','extra_symbol','naive','reversed','bad_date','off_window_source','off_clock_source','off_clock_exit','off_clock_moment'])
def test_expected_exchange_clock_and_frozen_scope_are_enforced(twins,change):
    c=clock();s=source();m=moment();start=START;end=END
    if change=='missing_minute':c['SPY'].pop(15)
    if change=='missing_session':c['SPY']=[t for t in c['SPY'] if not t.startswith(START)]
    if change=='extra_after_close':c['SPY'].append(START+'T20:01:00+00:00')
    if change=='missing_symbol':c={}
    if change=='extra_symbol':c['QQQ']=c['SPY'][:]
    if change=='naive':c['SPY'][0]='2026-10-05T13:30:00'
    if change=='reversed':start,end=END,START
    if change=='bad_date':start='2026-10-5'
    if change=='off_window_source':s=source(entry_at='2026-10-08T14:30:00Z',exit_at='2026-10-08T14:35:00Z')
    if change=='off_clock_source':s=source(entry_at='2026-10-07T12:00:00Z',atr_available_at='2026-10-07T11:59:00Z')
    if change=='off_clock_exit':s=source(exit_at='2026-10-07T20:01:00Z')
    if change=='off_clock_moment':m=moment(entry_at='2026-10-05T12:00:00Z',atr_available_at='2026-10-05T11:59:00Z')
    with pytest.raises(ValueError):prepare(twins,sources=[s],moments=[m],minutes=c,start=start,end=end)

def test_bins_real_moments_and_positive_geometry_define_whole_cohort_eligibility(twins):
    rows=[moment(),moment('2026-10-06',entry_at='2026-10-06T14:59:00Z'),
        moment('2026-10-06',entry_at='2026-10-06T15:00:00Z'),moment('2026-10-07',reference_price=100.,atr=2.)]
    plan=prepare(twins,moments=rows)
    assert plan.pools==((0,1),)
    # One missing trade pool makes the entire experiment ineligible, retaining both trades.
    bad=source(trade_id='real-b',entry_at='2026-10-07T15:01:00Z',exit_at='2026-10-07T15:06:00Z')
    plan=prepare(twins,sources=[source(),bad],moments=[moment()])
    assert not plan.eligible and len(plan.sources)==2 and plan.pools[1]==()
    with pytest.raises(ValueError):twins.draw_set(plan,42,0)
    short=source(side=-1,entry_stop=102.,entry_target=94.)
    no_geometry=prepare(twins,sources=[short],moments=[moment(reference_price=1.,atr=4.)])
    assert not no_geometry.eligible

def test_request_order_normalization_snapshot_detachment_and_hash_binding(twins):
    s=[source(trade_id='b'),source(trade_id='a')];m=[moment('2026-10-06'),moment()];c=clock()
    plan=prepare(twins,sources=s,moments=m,minutes=c)
    reverse=prepare(twins,sources=s[::-1],moments=m[::-1],minutes={'SPY':c['SPY'][::-1]})
    assert plan.json()==reverse.json()
    before=plan.json();s[0]['entry_price']=999;m[0]['atr']=33;c['SPY'].clear()
    detached=plan.json();detached['sources'].clear()
    assert plan.json()==before
    with pytest.raises((ValueError,AttributeError,TypeError)):plan.sources[0].quantity=100
    with pytest.raises((ValueError,AttributeError,TypeError)):plan.pools=()
    assert prepare(twins,moments=[moment(atr=4.1),moment('2026-10-06')]).plan_hash!=prepare(twins).plan_hash
    assert prepare(twins,sources=[source(net_profit=26.)]).plan_hash!=prepare(twins).plan_hash

def test_actual_coordinate_hash_and_unbiased_rejection_match_independent_oracle(twins,monkeypatch):
    plan=prepare(twins)
    coordinate=dict(policy=twins.DRAW_POLICY,plan_hash=plan.plan_hash,seed=42,set_index=19,source_id='real-a')
    limit=(1<<256)-((1<<256)%3);counter=0
    while True:
        raw=json.dumps(coordinate|dict(counter=counter),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        integer=int.from_bytes(hashlib.sha256(raw).digest(),'big')
        if integer<limit:break
        counter+=1
    assert twins.sample_index(plan.plan_hash,42,19,'real-a',3)==integer%3
    calls=[]
    def digest(value):
        calls.append(value);return (1<<256)-1 if len(calls)==1 else 5
    monkeypatch.setattr(twins,'_hash_integer',digest)
    assert twins.sample_index(plan.plan_hash,42,19,'real-a',3)==2
    assert [v['counter'] for v in calls]==[0,1]

@pytest.mark.parametrize('field,value',[('seed',True),('seed',1.1),('seed',-1),('seed',2**31),('set_index',True),('set_index',-1),('set_index',10000),('size',0),('size',True)])
def test_strict_draw_coordinates(twins,field,value):
    args=dict(plan_hash=PARENT,seed=42,set_index=0,source_id='a',size=2);args[field]=value
    with pytest.raises(ValueError):twins.sample_index(**args)

def test_stream_prefix_resume_changed_seed_and_collisions_preserve_every_trade(twins):
    plan=prepare(twins,sources=[source(trade_id='a'),source(trade_id='b')],moments=[moment()])
    first=list(twins.stream_sets(plan,42,start=0,stop=5))
    assert first==list(twins.stream_sets(plan,42,start=0,stop=8))[:5]
    assert first[2:]==list(twins.stream_sets(plan,42,start=2,stop=5))
    assert all(len(r['matches'])==2 and len({m['candidate_key'] for m in r['matches']})==1 for r in first)
    varied=prepare(twins)
    assert [r['matches'][0]['candidate_key'] for r in twins.stream_sets(varied,42,stop=30)]!=[r['matches'][0]['candidate_key'] for r in twins.stream_sets(varied,43,stop=30)]

@pytest.mark.parametrize('args',[dict(start=-1),dict(stop=10001),dict(start=True),dict(stop=1.5),dict(start=5,stop=4)])
def test_stream_slice_bounds(twins,args):
    with pytest.raises(ValueError):list(twins.stream_sets(prepare(twins),42,**args))

def test_zero_duration_empty_cohort_missing_pool_and_complete_clock_dont_produce_partial_success(twins):
    zero=prepare(twins,sources=[source(exit_at=source()['entry_at'])])
    assert not zero.eligible and 'Zero' in zero.reasons[0]
    empty=prepare(twins,sources=[],moments=[],minutes={})
    assert not empty.eligible and len(empty.sources)==0
    assert not prepare(twins,moments=[]).eligible

def test_dst_same_new_york_bin_and_early_close_cutoff_are_preserved(twins):
    s=source(entry_at='2026-11-02T15:30:00Z',exit_at='2026-11-02T15:35:00Z',atr_available_at='2026-11-02T15:30:00Z')
    rows=[moment('2026-10-30'),moment('2026-10-30',entry_at='2026-10-30T15:30:00Z')]
    p=prepare(twins,sources=[s],moments=rows,start='2026-10-30',end='2026-11-02')
    assert p.pools==((0,),)
    early=source(entry_at='2026-11-30T17:55:00Z',exit_at='2026-11-30T18:05:00Z',atr_available_at='2026-11-30T17:54:00Z')
    p=prepare(twins,sources=[early],moments=[moment('2026-11-27',entry_at='2026-11-27T17:55:00Z',atr_available_at='2026-11-27T17:54:00Z')],start='2026-11-27',end='2026-11-30')
    assert not p.eligible  # Friday closes18:00 UTC; no favorable cutoff sliding.

def test_gap_opening_boundary_and_weekend_elapsed_duration_are_not_changed(twins):
    s=source(entry_at='2026-10-12T14:30:00Z',exit_at='2026-10-13T13:30:00Z',atr_available_at='2026-10-12T14:30:00Z',exit_boundary='open')
    rows=[moment('2026-10-08'),moment('2026-10-09')]
    p=prepare(twins,sources=[s],moments=rows,start='2026-10-08',end='2026-10-13')
    assert p.pools==((0,),)  # Friday+23h ends Saturday, which is not an execution boundary.
    row=twins.draw_set(p,42,0)['matches'][0]
    assert row['cutoff_at']=='2026-10-09T13:30:00+00:00' and row['exit_boundary']=='open'

def test_preparation_and_stream_cancellation_are_observed(twins):
    with pytest.raises(InterruptedError):prepare(twins,cancel=lambda:True)
    plan=prepare(twins);state={'stop':False}
    gen=twins.stream_sets(plan,42,stop=4,cancel=lambda:state['stop'])
    next(gen);state['stop']=True
    with pytest.raises(InterruptedError):next(gen)

def test_visible_working_bounds_reject_instead_of_subsampling(twins,monkeypatch):
    monkeypatch.setattr(twins,'MAX_SOURCE_TRADES',1)
    with pytest.raises(ValueError):prepare(twins,sources=[source(trade_id='a'),source(trade_id='b')])
    monkeypatch.setattr(twins,'MAX_EDGES',1)
    with pytest.raises(ValueError):prepare(twins)

@pytest.mark.parametrize('exceed,expected',[(0,True),(499,True),(500,False),(10000,False)])
def test_exact10000_source_fraction_ties_and_strict_boundary(twins,exceed,expected):
    plan=prepare(twins);r=twins.summarize(plan,42,'barrier_capped_elapsed_v1',outcomes(plan,exceed=exceed))
    assert r['complete_sets']==10000 and r['exceedances']==exceed and r['adapted_pass'] is expected
    assert r['raw_exceedance_fraction']==exceed/10000 and r['plus_one_diagnostic']==(1+exceed)/10001
    assert r['host_engine_parity_verified'] is False
    assert 0<=r['monte_carlo_interval_95'][0]<=exceed/10000<=r['monte_carlo_interval_95'][1]<=1

@pytest.mark.parametrize('change',['missing','extra','duplicate','failed','wrong_count','wrong_parent','wrong_seed','wrong_policy','bool_index','infinite','unknown_field'])
def test_no_partial_failed_or_corrupt_denominator_can_pass(twins,change):
    plan=prepare(twins);values=list(outcomes(plan))
    if change=='missing':values.pop()
    if change=='extra':values.append(values[0])
    if change=='duplicate':values[1]=copy.deepcopy(values[0])
    if change=='failed':values[0]|=dict(state='failed',net_profit=None,error='Unavailable short; not redrawn.')
    if change=='wrong_count':values[0]['trade_count']=0
    if change=='wrong_parent':values[0]['plan_hash']='b'*64
    if change=='wrong_seed':values[0]['seed']=43
    if change=='wrong_policy':values[0]['policy']='fixed_elapsed_v1'
    if change=='bool_index':values[0]['set_index']=True
    if change=='infinite':values[0]['net_profit']=float('inf')
    if change=='unknown_field':values[0]['ignore_me']=True
    if change in {'missing','failed'}:
        r=twins.summarize(plan,42,'barrier_capped_elapsed_v1',iter(values))
        assert r['adapted_pass'] is None and r['raw_exceedance_fraction'] is None and r['plus_one_diagnostic'] is None
        assert r['state'] in {'incomplete','failed'}
    else:
        with pytest.raises(ValueError):twins.summarize(plan,42,'barrier_capped_elapsed_v1',iter(values))

def test_summary_zero_source_and_independent_binomial_tail_interval_oracle(twins):
    from scipy.stats import binom
    p=prepare(twins);r=twins.summarize(p,42,'fixed_elapsed_v1',outcomes(p,policy='fixed_elapsed_v1',exceed=499))
    lo,hi=r['monte_carlo_interval_95']
    assert binom.sf(498,10000,lo)==pytest.approx(.025,abs=1e-10)
    assert binom.cdf(499,10000,hi)==pytest.approx(.025,abs=1e-10)
    empty=prepare(twins,sources=[],moments=[],minutes={})
    r=twins.summarize(empty,42,'fixed_elapsed_v1',iter(()))
    assert r['state']=='ineligible' and r['adapted_pass'] is None

def test_full_pool_membership_and_nonterminating_rational_geometry_have_independent_oracle(twins):
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    c=clock();rows=[]
    for i,at in enumerate(c['SPY']):
        rows.append(moment(entry_at=at,atr_available_at=(pd.Timestamp(at)-pd.Timedelta(minutes=1)).isoformat(),
            reference_price=40.+i/37,atr=.1+(i%7)/11))
    sources=[]
    for i in range(12):
        side=1 if i%2 else -1;at=pd.Timestamp(END+'T14:30:00Z')+pd.Timedelta(minutes=i)
        sources.append(source(trade_id='real-'+str(i).zfill(2),entry_at=at.isoformat(),exit_at=(at+pd.Timedelta(minutes=i+1)).isoformat(),
            atr_available_at=at.isoformat(),side=side,entry_atr=3.,entry_stop=100.-side*.7,entry_target=100.+side*1.1))
    plan=prepare(twins,sources=sources,moments=rows,minutes=c)
    zone=ZoneInfo('America/New_York');opening={datetime.fromisoformat(t) for t in c['SPY']}
    closing={t+timedelta(minutes=1) for t in opening};real_entries={(s['symbol'],datetime.fromisoformat(s['entry_at'])) for s in sources}
    def bucket(t):
        local=t.astimezone(zone);return (local.hour*60+local.minute-570)//30
    for s,pool in zip(sources,plan.pools):
        expected=[];at=datetime.fromisoformat(s['entry_at']);duration=datetime.fromisoformat(s['exit_at'])-at
        for i,m in enumerate(rows):
            entry=datetime.fromisoformat(m['entry_at'])
            if m['symbol']!=s['symbol'] or (m['symbol'],entry) in real_entries or bucket(entry)!=bucket(at) or entry+duration not in closing:continue
            stop=Fraction(str(m['reference_price']))-(Fraction(str(s['entry_price']))-Fraction(str(s['entry_stop'])))/Fraction(str(s['entry_atr']))*Fraction(str(m['atr']))
            target=Fraction(str(m['reference_price']))+(Fraction(str(s['entry_target']))-Fraction(str(s['entry_price'])))/Fraction(str(s['entry_atr']))*Fraction(str(m['atr']))
            if min(stop,target)>0:expected.append(i)
        assert list(pool)==expected
    draw=twins.draw_set(plan,42,0)
    for s,row in zip(sources,draw['matches']):
        m=next(m for m in rows if m['symbol']+'|'+pd.Timestamp(m['entry_at']).isoformat()==row['candidate_key'])
        assert Fraction(row['stop'])==Fraction(str(m['reference_price']))-(Fraction(str(s['entry_price']))-Fraction(str(s['entry_stop'])))/Fraction(3)*Fraction(str(m['atr']))
        assert Fraction(row['target'])==Fraction(str(m['reference_price']))+(Fraction(str(s['entry_target']))-Fraction(str(s['entry_price'])))/Fraction(3)*Fraction(str(m['atr']))

@pytest.mark.parametrize('bound',['MAX_MOMENTS','MAX_CLOCK_MINUTES','MAX_ASSESSMENTS'])
def test_all_preparation_work_is_explicitly_bounded_including_ineligible_candidates(twins,monkeypatch,bound):
    monkeypatch.setattr(twins,bound,1)
    with pytest.raises(ValueError):prepare(twins)

@pytest.mark.parametrize('value',[None,3,'not-a-time','NaT','2026-10-05T14:30:00.000000001Z'])
def test_raw_clock_invalid_timestamp_cases(twins,value):
    c=clock();c['SPY'][0]=value
    with pytest.raises(ValueError):prepare(twins,minutes=c)

@pytest.mark.parametrize('value',[None,'a'*63,'g'*64,42])
def test_original_parent_digest_is_required(twins,value):
    with pytest.raises(ValueError):twins.prepare_plan([source()],[moment()],clock(),START,END,value)

@pytest.mark.parametrize('value',[None,42,'bad id',''])
def test_direct_draw_source_identity_is_strict(twins,value):
    with pytest.raises(ValueError):twins.sample_index(PARENT,42,0,value,2)

def test_wrong_direct_plan_digest_unequal_clock_and_clock_sequence_types(twins):
    with pytest.raises(ValueError):twins.sample_index('g'*64,42,0,'a',2)
    with pytest.raises(ValueError):prepare(twins,minutes={'SPY':iter(clock()['SPY'])})
    sources=[source(),source(trade_id='qqq',symbol='QQQ')];c=clock(symbols=('SPY','QQQ'));c['QQQ'].pop()
    with pytest.raises(ValueError):prepare(twins,sources=sources,minutes=c)

@pytest.mark.parametrize('changes',[dict(net_profit=None),dict(error='hidden failure'),dict(state='failed',net_profit=1.,error='failure'),dict(state='failed',net_profit=None,error=' '),dict(state='failed',net_profit=None,error=None)])
def test_completed_and_failed_outcome_state_fields_cannot_hide_failures(twins,changes):
    p=prepare(twins);row=next(outcomes(p))|changes
    with pytest.raises(ValueError):twins.summarize(p,42,'fixed_elapsed_v1',iter([row|dict(policy='fixed_elapsed_v1')]))

def test_summary_policy_ineligible_outcomes_and_cancellation_are_not_ignored(twins):
    p=prepare(twins)
    with pytest.raises(ValueError):twins.summarize(p,42,'unknown',iter(()))
    bad=prepare(twins,moments=[])
    with pytest.raises(ValueError):twins.summarize(bad,42,'fixed_elapsed_v1',iter([next(outcomes(bad,policy='fixed_elapsed_v1'))]))
    with pytest.raises(InterruptedError):twins.summarize(p,42,'fixed_elapsed_v1',outcomes(p,policy='fixed_elapsed_v1'),cancel=lambda:True)

def test_actual10000_matching_draws_stream_with_bounded_retained_heap(twins,tmp_path):
    import time,tracemalloc
    plan=prepare(twins,sources=[source(trade_id='a'),source(trade_id='b')]);digest=hashlib.sha256();count=0
    tracemalloc.start();started=time.perf_counter()
    try:
        for row in twins.stream_sets(plan,42):
            assert row['set_index']==count and len(row['matches'])==2
            digest.update(json.dumps(row,sort_keys=True,separators=(',',':')).encode());count+=1
        _,peak=tracemalloc.get_traced_memory()
    finally:tracemalloc.stop()
    elapsed=time.perf_counter()-started
    assert count==10000 and peak<4*1024*1024
    # This is matching-plan evidence only; no financial trade or set was executed.
    import os
    evidence=os.environ.get('PA_EVIDENCE_RUN_DIR')
    if evidence:
        from pathlib import Path
        (Path(evidence)/'actual10000-matching-draws.json').write_text(json.dumps(dict(sets=count,matches=count*2,sha256=digest.hexdigest(),python_peak_traced_bytes=peak,elapsed_seconds=elapsed,financial_sets_executed=0,scope='Streamed matching rows, not accounts or whole-process RSS.'),indent=2),encoding='utf-8')


def test_trade_twin_core_joins_the_unchanged_numerical_gate():
    from verification.check_numerical_coverage import MODULES
    assert len(MODULES) == 38 and MODULES[-11:] == ['backend/lab/trade_twins.py', 'backend/lab/trade_twin_source.py', 'backend/lab/trade_twin_execution.py', 'backend/lab/trade_twin_features.py', 'backend/lab/trade_twin_amounts.py', 'backend/lab/trade_twin_results.py', 'backend/lab/trade_twin_jobs.py', 'backend/lab/trade_twin_preparation.py', 'backend/lab/trade_twin_parts.py', 'backend/lab/trade_twin_worker.py', 'backend/lab/source_cashflows.py']


def test_complete_losses_and_out_of_order_sets_remain_in_exact_full_cohort(twins):
    sources=[source(trade_id='a',net_profit=-50.),source(trade_id='b',net_profit=100.),source(trade_id='c',net_profit=-25.)]
    plan=prepare(twins,sources=sources)
    rows=list(outcomes(plan,exceed=499));rows.reverse()
    result=twins.summarize(plan,42,'barrier_capped_elapsed_v1',iter(rows))
    assert result['real_profit']=='25.0' and result['exceedances']==499 and result['adapted_pass']
    losses=prepare(twins,sources=[source(net_profit=-25.)])
    result=twins.summarize(losses,42,'barrier_capped_elapsed_v1',outcomes(losses,exceed=0))
    assert result['real_profit']=='-25.0' and result['exceedances']==10000 and result['adapted_pass'] is False
