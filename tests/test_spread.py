"""Authored spread contracts: explicit independent score and proposal/qualification evidence."""
from copy import deepcopy
from fractions import Fraction
import hashlib,json,os,shutil
from pathlib import Path
import pytest
from backend.lab.config import FAMILIES,TIMEFRAMES,Strategy,identity

@pytest.fixture
def spread():
    from backend.lab import spread
    assert 'dev025' in str(Path(spread.__file__).resolve())
    return spread

def settings(module,**changes):
    return module.SpreadSettings(families=['break_of_structure'],timeframes=['1m','5m'],per_family=3,batch_size=8,max_batches_per_family=5,**changes)

def oracle(groups):
    result=Fraction(0)
    for g in groups:
        k=len(g['values']);n=sum(g['counts'])
        if k>1:result+=Fraction(k*sum(c*c for c in g['counts'])-n*n,k-1)-n
    return result

def context():
    return dict(dataset_id='a'*24,dataset_manifest_hash='b'*64,primary_symbol='SPY',start='2026-11-02',end='2026-11-06')

def evidence(count):return dict(signal_count=count,evidence_sha256=hashlib.sha256(str(count).encode()).hexdigest())

def receipt_artifact(name,value):
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value,indent=2),encoding='utf-8')

def test_host_defaults_and_explicit_distance_are_not_common_filter_quotas(spread):
    s=spread.SpreadSettings();assert s.per_family==4000 and s.batch_size==400 and s.minimum_signals==40
    assert s.families==list(FAMILIES) and s.timeframes==list(TIMEFRAMES)
    recipe=spread.recipe();assert recipe['source_video'].endswith('z97PnFIPoFg')
    assert recipe['metric']=='prior_centered_squared_counts' and recipe['filter_policy']=='independent_applicable_groups'
    assert set(recipe['public_fields'])==set(Strategy.model_fields)

@pytest.mark.parametrize('family',list(FAMILIES))
def test_seeded_all_chart_draws_valid_public_dials_and_conditional_universe(spread,family):
    s=spread.SpreadSettings(families=[family],seed=937,include_news=True)
    seen={};charts=set();groups={};multi=False
    for ordinal in range(500):
        value=spread.draw(s,family,ordinal//400,ordinal%400)
        assert value==spread.draw(s,family,ordinal//400,ordinal%400)
        cfg=Strategy(**value);assert cfg.model_dump()==value;charts.add(cfg.timeframe)
        multi=multi or len(__import__('backend.lab.sampling',fromlist=['active_filters']).active_filters(value))>2
        for g in spread.describe(value,s):
            key=(g['field'],json.dumps(g['context'],sort_keys=True),json.dumps(g['values']))
            groups[key]=g;seen.setdefault(key,set()).add(json.dumps(g['value']))
    assert charts==set(TIMEFRAMES) and multi
    universe=spread.Balance(s,family).groups()
    assert {(g['field'],json.dumps(g['context'],sort_keys=True),json.dumps(g['values'])) for g in universe}==set(groups)
    for key,g in groups.items():assert seen[key]=={json.dumps(v) for v in g['values']},(family,key,seen[key])
    assert any(g['exposures']==0 and g['shares'] is None for g in universe)

def test_fraction_oracle_every_delta_and_tie_priority(spread):
    s=settings(spread);b=spread.Balance(s,'break_of_structure');witness=[]
    for n in range(13):
        candidates=[spread.draw(s,'break_of_structure',n,j) for j in range(8)]
        before=oracle(b.groups());expected=[]
        for cfg in candidates:
            trial=deepcopy(b);trial.accept(cfg)
            delta=oracle(trial.groups())-before
            assert b.delta(cfg)==delta*60
            expected.append(delta)
        ranked=b.rank(candidates)
        assert ranked==sorted(range(8),key=lambda i:(expected[i],i))
        assert b.rank([candidates[0],candidates[0]])==[0,1]
        witness.append(dict(step=n,before_groups=b.groups(),candidate_configurations=candidates,independent_fraction_deltas=[str(v) for v in expected],actual_scaled_deltas=[b.delta(c) for c in candidates],ranked=ranked))
        b.accept(candidates[ranked[0]])
        assert b.score()==oracle(b.groups())*60
    receipt_artifact('spread-exact-fraction-reference.json',dict(scope='104 actual candidate deltas against an all-bin Fraction oracle; nonfinancial',steps=witness))

def test_canonical_axes_seed_and_frozen_file_bytes(spread,tmp_path):
    one=spread.SpreadSettings(families=['breakout','level_bounce'],timeframes=['5m','1m'],per_family=2,batch_size=4,max_batches_per_family=2)
    two=spread.SpreadSettings(families=list(reversed(one.families)),timeframes=list(reversed(one.timeframes)),per_family=2,batch_size=4,max_batches_per_family=2)
    p=spread.freeze_plan(tmp_path/'one',one);q=spread.freeze_plan(tmp_path/'two',two)
    assert p.plan_id==q.plan_id
    assert {f.name:f.read_bytes() for f in p.folder.iterdir()}=={f.name:f.read_bytes() for f in q.folder.iterdir()}
    assert p.manifest['planned_proposals']==16
    changed=one.model_copy(update={'seed':43});assert spread.draw(changed,'breakout',0,0)!=spread.draw(one,'breakout',0,0)
    with pytest.raises(FileExistsError):spread.freeze_plan(p.folder,one)

@pytest.mark.parametrize('fault',['same_length','missing','manifest','source','extra'])
def test_plan_integrity_precedes_callbacks(spread,tmp_path,fault):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));path=plan.folder/'break_of_structure.jsonl.gz'
    if fault=='same_length':raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
    elif fault=='missing':path.unlink()
    elif fault=='manifest':plan.manifest['settings']['seed']+=1
    elif fault=='source':plan.manifest['core_hash']='f'*64
    else:(plan.folder/'unplanned.jsonl.gz').write_bytes(b'extra')
    calls=[]
    with pytest.raises(spread.SpreadError):spread.select(plan,context(),lambda *a:calls.append('probe'),lambda e:calls.append('event'),authorize=lambda:calls.append('authorize'))
    assert 'probe' not in calls

def test_every_plan_batch_frozen_and_40_boundary_before_selected_manifest(spread,tmp_path):
    s=settings(spread);plan=spread.freeze_plan(tmp_path/'plan',s);events=[];observed=[]
    def probe(cfg):
        assert events[-1]['kind']=='probe_started'
        # Every bounded file already exists and verifies before any price-like callback.
        plan.verify();observed.append(identity(cfg));return evidence(39 if len(observed)==1 else 40)
    result=spread.select(plan,context(),probe,events.append,authorize=lambda:None)
    assert result['complete'] and len(result['selected'])==3 and result['probe_computations']==4
    assert result['selection_manifest_hash']==identity(result['selection_manifest'])
    assert result['selection_manifest']['context']==context()
    assert any(e['kind']=='probe_completed' and e['evidence']['signal_count']==39 for e in events)
    assert events[-1]['kind']=='selection_finished'
    assert len({identity(v) for v in result['selected']})==3
    assert result['planned_proposals']==40 and result['unprobed_proposals']>0

def test_no_eligible_exhaustion_keeps_failures_without_success_manifest(spread,tmp_path):
    s=settings(spread);plan=spread.freeze_plan(tmp_path/'plan',s);events=[]
    result=spread.select(plan,context(),lambda cfg:evidence(0),events.append,authorize=lambda:None)
    assert not result['complete'] and result['selected']==[]
    assert result['selection_manifest'] is None and result['selection_manifest_hash'] is None
    assert result['probe_computations']+result['duplicate_proposals']==40
    assert result['exhausted_families']==['break_of_structure']

@pytest.mark.parametrize('bad',[True,-1,1.5,float('nan'),None,'40'])
def test_bad_probe_counts_never_select(spread,tmp_path,bad):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[]
    with pytest.raises(spread.SpreadError):spread.select(plan,context(),lambda cfg:evidence(bad),events.append,authorize=lambda:None)
    assert not any(e['kind']=='version_selected' for e in events)

@pytest.mark.parametrize('cut_kind',['probe_started','probe_completed','version_selected','batch_finished'])
def test_interruption_replays_exact_prefix_without_recomputing_completed_probe(spread,tmp_path,cut_kind):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[];calls=[];interrupted=[]
    def sink(e):
        events.append(e)
        if e['kind']==cut_kind and not interrupted:interrupted.append(True);raise InterruptedError('Owned durable-event interruption')
    def probe(cfg):calls.append(identity(cfg));return evidence(40)
    with pytest.raises(InterruptedError):spread.select(plan,context(),probe,sink,authorize=lambda:None)
    committed=sum(e['kind']=='probe_completed' for e in events)
    resumed=[];result=spread.select(plan,context(),probe,resumed.append,authorize=lambda:None,replay=events)
    assert result['complete'] and result['reused_probes']==committed
    assert len(calls)==3
    assert result['total_probe_attempts']==3+(cut_kind=='probe_started')
    baseline=[];fresh=spread.select(plan,context(),lambda cfg:evidence(40),baseline.append,authorize=lambda:None)
    assert result['selected']==fresh['selected'] and result['selection_manifest']==fresh['selection_manifest']
    if cut_kind!='probe_started':assert events+resumed==baseline
    else:
        starts=[e for e in events+resumed if e['kind']=='probe_started']
        assert [e['attempt'] for e in starts if e['config_id']==starts[0]['config_id']]==[1,2]

def test_replay_corruption_and_authorization_or_cancel_precede_new_or_reused_probe(spread,tmp_path):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[]
    spread.select(plan,context(),lambda cfg:evidence(40),events.append,authorize=lambda:None)
    bad=deepcopy(events);bad[1]['kind']='tampered';calls=[]
    with pytest.raises(spread.SpreadError):spread.select(plan,context(),lambda cfg:calls.append(1),lambda e:None,authorize=lambda:None,replay=bad)
    assert calls==[]
    for replay in [[],events]:
        with pytest.raises(InterruptedError):spread.select(plan,context(),lambda cfg:calls.append(1),lambda e:None,authorize=lambda:None,replay=replay,cancel=lambda:True)
        def forbidden():raise PermissionError('Owned protected-date or owner refusal')
        with pytest.raises(PermissionError):spread.select(plan,context(),lambda cfg:calls.append(1),lambda e:None,authorize=forbidden,replay=replay)
    assert calls==[]

def test_uncommitted_probe_result_retries_get_distinct_attempts(spread,tmp_path):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[];calls=[];first=[]
    def record(e):
        if e['kind']=='probe_completed' and not first:first.append(True);raise InterruptedError('Before result commit')
        events.append(e)
    def probe(cfg):calls.append(identity(cfg));return evidence(40)
    with pytest.raises(InterruptedError):spread.select(plan,context(),probe,record,authorize=lambda:None)
    following=[];result=spread.select(plan,context(),probe,following.append,authorize=lambda:None,replay=events)
    assert result['complete'] and len(calls)==4 and calls[0]==calls[1]
    starts=[e for e in events+following if e['kind']=='probe_started']
    assert result['total_probe_attempts']==len(starts)==4
    assert [e['attempt'] for e in starts if e['config_id']==calls[0]]==[1,2]
    assert len([e for e in events+following if e['kind']=='probe_completed'])==3

def test_current_plan_corruption_during_probe_cannot_publish_selected_manifest(spread,tmp_path):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[];calls=[]
    def probe(cfg):
        if not calls:
            p=plan.folder/'break_of_structure.jsonl.gz';raw=p.read_bytes();p.write_bytes(b'X'+raw[1:])
        calls.append(1);return evidence(40)
    with pytest.raises(spread.SpreadError):spread.select(plan,context(),probe,events.append,authorize=lambda:None)
    assert not any(e['kind']=='selection_finished' for e in events)

def test_reopen_requires_frozen_external_plan_identity(spread,tmp_path):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread))
    reopened=spread.ProposalPlan.open(plan.folder,plan.plan_id);assert reopened.plan_id==plan.plan_id
    with pytest.raises(spread.SpreadError):spread.ProposalPlan.open(plan.folder,'0'*64)

@pytest.mark.parametrize('enabled,attached',[(True,False),(False,True)])
def test_news_scope_must_match_the_frozen_spread_policy_before_callbacks(spread,tmp_path,enabled,attached):
    s=settings(spread,include_news=enabled);plan=spread.freeze_plan(tmp_path/'plan',s);scope=context()
    if attached:scope.update(news_calendar_id='c'*64,news_calendar_hash='d'*64)
    calls=[]
    with pytest.raises(spread.SpreadError):spread.select(plan,scope,lambda cfg:calls.append(1),lambda e:None,authorize=lambda:None)
    assert calls==[]

def test_recipe_publishes_every_public_field_domain_and_prerequisite(spread):
    rules=spread.recipe()['dial_rules'];assert set(rules)==set(Strategy.model_fields)
    assert rules['family']['mode']=='stratum' and rules['family']['values']==list(FAMILIES)
    assert rules['timeframe']['values']==list(TIMEFRAMES)
    assert rules['direction']['values']==['both','long','short']
    assert rules['entry']['values']==['next_open','same_close','limit']
    assert rules['trigger_timeframe']['by_setup']=={'1m':['1m'],'5m':['1m','5m'],'15m':['1m','5m','15m'],'1h':['5m','15m','1h'],'4h':['15m','1h','4h'],'1d':['1h']}
    assert rules['confirmation_window']['requires']=={'confirmation_not':'none'}
    assert rules['limit_expiry']['requires']=={'entry':'limit'}
    assert rules['news']['when_enabled']==['trade','skip','half'] and rules['news']['when_disabled']==['trade']
    assert rules['stop_reference']['by_family']['fair_value_gap']==['swing','level','wick','gap']
    assert rules['sweep_depth']['requires']=={'family_sweep_or_enabled_choch':True}
    assert rules['pullback_min']['paired_values']==rules['pullback_max']['paired_values']==[[0.,3.],[.25,1.5],[.5,2.]]
    assert rules['fresh_breakout']['families']==['breakout','flip_zone','break_of_structure','change_of_character']
    for name in Strategy.model_fields:assert rules[name]['mode'] in {'stratum','draw','conditional'}

def test_nonfinancial_default_400_proposal_files_are_complete_before_selection(spread,tmp_path):
    s=spread.SpreadSettings(per_family=1,max_batches_per_family=1)
    plan=spread.freeze_plan(tmp_path/'plan',s);assert plan.manifest['planned_proposals']==4000
    for family in FAMILIES:
        batches=list(plan.batches(family));assert len(batches)==1 and len(batches[0])==400
        assert all(Strategy(**c).family==family for c in batches[0])
    result=spread.select(plan,context(),lambda cfg:evidence(40),lambda e:None,authorize=lambda:None)
    assert result['complete'] and len(result['selected'])==10 and result['visited_proposals']==4000
    assert result['probe_computations']==10 and result['unprobed_proposals']+result['duplicate_proposals']==3990
    receipt_artifact('spread-nonfinancial-400-batch-selection.json',dict(scope='4000 frozen proposals/ten selections with explicit stubbed40 counts; zero actual signal/account execution in this fixture',result=result))
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        destination=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'spread-nonfinancial-frozen-plan';destination.mkdir()
        for p in plan.folder.iterdir():shutil.copyfile(p,destination/p.name)
