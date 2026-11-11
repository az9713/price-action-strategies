"""Qualification contracts: arithmetic fixtures are not original-store authority."""
import importlib
import importlib.util
from copy import deepcopy
from fractions import Fraction
import itertools
from pathlib import Path
import pytest
from backend.lab.config import Strategy,identity

fixture_spec=importlib.util.spec_from_file_location('qualification_original_registration',Path(__file__).with_name('research-funnel-registration-contracts.py'))
fixture_module=importlib.util.module_from_spec(fixture_spec);fixture_spec.loader.exec_module(fixture_module)
inputs=fixture_module.inputs;registration=fixture_module.registration


def test_complete_qualification_and_frozen_neighbor_components_exist():
    assert importlib.util.find_spec('backend.lab.research_qualification') is not None
    assert importlib.util.find_spec('backend.lab.research_qualification_source') is not None


@pytest.fixture
def kernel():return importlib.import_module('backend.lab.research_qualification')


def rational(value):return Fraction(int(value['numerator']),int(value['denominator']))


def test_stability_uses_actual_one_coordinate_neighbors_with_losses_zeros_and_missing(kernel):
    configs=[Strategy(timeframe='1m',target=t,direction=d) for t,d in itertools.product(['1R','2R'],['both','long'])]
    ids=[identity(c) for c in configs]
    observations={ids[0]:dict(net_profit=9,marked_sharpe=1),ids[1]:dict(net_profit=-3,marked_sharpe=None),
                  ids[2]:dict(net_profit=0,marked_sharpe=0),ids[3]:None}
    result=kernel.stability(configs,observations)
    assert result['descriptive_only'] is True and result['candidate_gate'] is False
    first=result['rows'][0]
    assert first['config_id']==ids[0] and first['neighbors']==2 and first['available']==2 and first['positive']==0
    assert rational(first['mean_net_profit'])==Fraction(-3,2)
    assert rational(first['sample_variance_net_profit'])==Fraction(9,2)
    assert first['undefined_sharpe']==1
    last=result['rows'][3]
    assert last['neighbors']==2 and last['available']==2
    assert rational(last['mean_net_profit'])==Fraction(-3,2)
    assert set(kernel.neighbor_ids(configs,ids[0]))=={ids[1],ids[2]}
    assert result['rows'][1]['missing']==1


def test_stability_does_not_invent_cross_family_chart_or_inactive_neighbors(kernel):
    configs=[Strategy(timeframe='1m'),Strategy(timeframe='5m'),Strategy(timeframe='1m',family='trend_line'),
             Strategy(timeframe='1m',confirmation_window=1),Strategy(timeframe='1m',target='2R')]
    values={identity(c):dict(net_profit=1,marked_sharpe=None) for c in configs}
    result=kernel.stability(configs,values)
    # Inactive confirmation-window changes are not evidence of parameter stability.
    assert kernel.neighbor_ids(configs,identity(configs[0]))==[identity(configs[-1])]
    assert result['rows'][1]['neighbors']==0 and result['rows'][1]['mean_net_profit'] is None


@pytest.mark.parametrize('fault',['duplicate','missing','extra','boolean_profit','nonfinite','cancel'])
def test_stability_refuses_changed_membership_or_nonfinite_outcomes(kernel,fault):
    configs=[Strategy(timeframe='1m'),Strategy(timeframe='1m',target='2R')]
    values={identity(c):dict(net_profit=1,marked_sharpe=.5) for c in configs}
    cancel=None
    if fault=='duplicate':configs.append(configs[0])
    elif fault=='missing':values.pop(identity(configs[0]))
    elif fault=='extra':values['extra']=None
    elif fault=='boolean_profit':values[identity(configs[0])]['net_profit']=True
    elif fault=='nonfinite':values[identity(configs[0])]['marked_sharpe']=float('nan')
    else:cancel=lambda:True
    with pytest.raises((ValueError,InterruptedError)):kernel.stability(configs,values,cancel=cancel)


@pytest.mark.parametrize('exceedances,passed',[(0,True),(499,True),(500,False),(501,False),(10000,False)])
def test_both_original_control_interpretations_require_strict_five_percent(kernel,exceedances,passed):
    from backend.lab.trade_twins import EXECUTION_POLICIES
    summaries={p:dict(state='completed',expected_sets=10000,observed_sets=10000,complete_sets=10000,failed_sets=0,exceedances=exceedances,adapted_pass=not passed) for p in EXECUTION_POLICIES}
    result=kernel.control_gate(dict(state='completed',summaries=summaries))
    assert result['passed'] is passed
    summaries[EXECUTION_POLICIES[-1]]['exceedances']=500
    assert kernel.control_gate(dict(state='completed',summaries=summaries))['passed'] is False


@pytest.mark.parametrize('state',['missing','queued','running','failed','canceled','ineligible','incomplete'])
def test_unfinished_or_unavailable_control_never_passes(kernel,state):
    assert kernel.control_gate(dict(state=state))['passed'] is False


@pytest.mark.parametrize('fault',['missing_policy','wrong_expected','short_count','failure','boolean','negative','surplus'])
def test_malformed_complete_control_cannot_certify(kernel,fault):
    from backend.lab.trade_twins import EXECUTION_POLICIES
    summaries={p:dict(state='completed',expected_sets=10000,observed_sets=10000,complete_sets=10000,failed_sets=0,exceedances=0) for p in EXECUTION_POLICIES}
    first=summaries[EXECUTION_POLICIES[0]]
    if fault=='missing_policy':summaries.pop(EXECUTION_POLICIES[0])
    elif fault=='wrong_expected':first['expected_sets']=9999
    elif fault=='short_count':first['complete_sets']=9999
    elif fault=='failure':first['failed_sets']=1
    elif fault=='boolean':first['exceedances']=False
    elif fault=='negative':first['exceedances']=-1
    else:summaries['invented_policy']=first
    with pytest.raises(ValueError):kernel.control_gate(dict(state='completed',summaries=summaries))


@pytest.fixture
def arithmetic_accounts(inputs,registration):
    """Explicit arithmetic-only reports: never used as original-store evidence."""
    lab,request,*_=inputs;saved=registration.register_funnel(lab,request);spec=saved['spec'];reports={}
    for key,arm in spec['development_arms'].items():
        days=[arm['start']] if arm['start']==arm['end'] else [arm['start'],arm['end']]
        reports[key]={}
        for configuration in spec['configurations']:
            cid=identity(configuration)
            reports[key][cid]=dict(report_type='single_strategy',config=configuration,config_id=cid,core_hash=spec['core_hash'],
                dataset_id=arm['dataset_context']['dataset_id'],dataset_manifest_hash=arm['dataset_context']['dataset_manifest_hash'],
                dataset_context=arm['dataset_context'],start=arm['start'],end=arm['end'],costs=spec['costs'],portfolio=spec['portfolio'],
                research_arm_context=dict(arm_key=key,arm_hash=identity(arm),role=arm['role'],configuration_universe_hash=spec['configuration_universe_hash']),
                charts={arm['symbol']:[]},signals=[dict(id=str(i),available_at=arm['start']+'T15:00:00+00:00') for i in range(40)],
                trades=[dict(id=str(i),net_pnl=.1,exit_at=arm['end']+'T20:00:00+00:00') for i in range(30)],
                equity=[dict(date=day,equity=100001 if i==0 else 100003) for i,day in enumerate(days)],
                metrics=dict(trades=30,net_profit=3,marked_sharpe=.5 if key!='instrument_replication' else .3))
    return spec,reports


def completed_controls(spec):
    from backend.lab.trade_twins import EXECUTION_POLICIES
    return {identity(c):dict(state='completed',summaries={p:dict(state='completed',expected_sets=10000,
            observed_sets=10000,complete_sets=10000,failed_sets=0,exceedances=499) for p in EXECUTION_POLICIES}) for c in spec['configurations']}


def test_all_source_gate_boundaries_full_family_and_separate_chronology(kernel,arithmetic_accounts):
    spec,reports=arithmetic_accounts;result=kernel.qualify(spec,reports,completed_controls(spec))
    assert result['state']=='complete' and len(result['candidate_ids'])==2 and len(result['rows'])==2
    assert all(item['removed']==0 and item['passing']==2 for item in result['attrition'])
    assert result['qualification_does_not_consume_final'] and result['host_engine_parity_verified'] is False
    family=result['families']['change_of_character']
    assert family['passed'] and len(family['members'])==2
    assert family['axes']['primary_discovery']['version_count']==2
    assert family['axes']['chronological_validation']['marked']['sharpe'] is None
    # Individual saved-account Sharpe and aggregate family Sharpe have distinct bases.
    assert result['rows'][0]['gates']['replication_sharpe']['threshold']==.3
    assert result['rows'][0]['gates']['discovery_sharpe']['threshold']==.5


@pytest.mark.parametrize('gate,arm,field,value',[
    ('discovery_signals','primary_discovery','signals',39),('discovery_trades','primary_discovery','trades',29),
    ('discovery_profit','primary_discovery','net_profit',0),('discovery_sharpe','primary_discovery','marked_sharpe',.499),
    ('discovery_sharpe','primary_discovery','marked_sharpe',None),('era_one_profit','era_one','net_profit',0),
    ('era_two_profit','era_two','net_profit',-1),('replication_profit','instrument_replication','net_profit',0),
    ('replication_sharpe','instrument_replication','marked_sharpe',.299),
    ('chronological_trades','chronological_validation','trades',29),('chronological_profit','chronological_validation','net_profit',0),
    ('chronological_sharpe','chronological_validation','marked_sharpe',.499)])
def test_each_source_or_explicit_adaptation_gate_removes_only_its_original_version(kernel,arithmetic_accounts,gate,arm,field,value):
    spec,reports=arithmetic_accounts;cid=identity(spec['configurations'][0]);report=reports[arm][cid]
    if field=='signals':report['signals']=report['signals'][:value]
    elif field=='trades':report['trades']=report['trades'][:value];report['metrics'][field]=value
    else:report['metrics'][field]=value
    result=kernel.qualify(spec,reports,completed_controls(spec))
    assert result['rows'][0]['gates'][gate]['passed'] is False
    assert result['rows'][0]['prequalified'] is False and result['rows'][0]['candidate'] is False
    assert len(result['candidate_ids'])==1 and len(result['rows'])==2


def test_missing_controls_pending_and_unavailable_accounts_never_become_zero(kernel,arithmetic_accounts):
    spec,reports=arithmetic_accounts;cid=identity(spec['configurations'][0])
    result=kernel.qualify(spec,reports)
    assert result['state']=='awaiting_controls' and len(result['pending_control_ids'])==2 and not result['candidate_ids']
    reports['era_two'][cid]=None
    result=kernel.qualify(spec,reports,completed_controls(spec))
    assert result['state']=='incomplete_accounts' and len(result['rows'])==2
    assert result['rows'][0]['accounts']['era_two'] is None
    assert result['families']['change_of_character']['passed'] is False
    assert result['families']['change_of_character']['axes']['era_two']['state']=='incomplete'


def test_family_is_not_replaced_by_profitable_subset_or_candidate_members(kernel,arithmetic_accounts):
    spec,reports=arithmetic_accounts;loser=identity(spec['configurations'][1])
    for axis in reports.values():
        report=axis[loser]
        report['metrics']['net_profit']=-10
        report['equity']=[dict(row,equity=99990-i) for i,row in enumerate(report['equity'])]
        for trade in report['trades']:trade['net_pnl']=-1
    result=kernel.qualify(spec,reports,completed_controls(spec));family=result['families']['change_of_character']
    assert len(result['candidate_ids'])==1 and len(family['members'])==2
    assert family['passed'] is False
    primary=family['axes']['primary_discovery']
    assert rational(primary['marked']['net_profit'])==-4
    assert rational(primary['realized_exit_day_compatibility']['net_profit'])==Fraction(-27,2)
    assert primary['version_count']==2 and result['rows'][0]['family_passed'] is False


@pytest.mark.parametrize('fault',['policy','cohort','axis','member','role','instrument','context','dates','core','costs','capital','config','trades','nonfinite','boolean','cancel'])
def test_qualification_refuses_substituted_assumptions_roles_membership_and_metrics(kernel,arithmetic_accounts,fault):
    spec,reports=arithmetic_accounts;cid=identity(spec['configurations'][0]);report=reports['primary_discovery'][cid];cancel=None
    if fault=='policy':spec['stability_policy']={}
    elif fault=='cohort':spec['configuration_universe_hash']='0'*64
    elif fault=='axis':reports.pop('era_two')
    elif fault=='member':reports['era_one'].pop(cid)
    elif fault=='role':report['research_arm_context']=dict(report['research_arm_context'],role='untouched_final')
    elif fault=='instrument':report['charts']={'QQQ':[]}
    elif fault=='context':report['dataset_context']={}
    elif fault=='dates':report['end']='2026-11-05'
    elif fault=='core':report['core_hash']='0'*64
    elif fault=='costs':report['costs']={}
    elif fault=='capital':report['portfolio']={}
    elif fault=='config':report['config_id']='0'*64
    elif fault=='trades':report['metrics']['trades']=29
    elif fault=='nonfinite':report['metrics']['marked_sharpe']=float('inf')
    elif fault=='boolean':report['metrics']['net_profit']=True
    else:cancel=lambda:True
    with pytest.raises((ValueError,InterruptedError)):kernel.qualify(spec,reports,cancel=cancel)


@pytest.fixture
def original_accounts(inputs,registration,monkeypatch):
    from backend.lab import service
    from backend.lab.research_funnel_arms import queue_arms
    from backend.lab.worker import Worker
    lab,request,*_=inputs;study=registration.register_funnel(lab,request);arms=queue_arms(lab,study['id'])['arms']
    # Actual five-axis financial accounts with explicitly authored empty signals;
    # this fixture verifies authority and zero-candidate behavior, not detectors.
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    for _ in range(5):assert Worker(lab).run_once()
    assert all(lab.store.job(jid)['status']=='completed' for jid in arms.values())
    return lab,study,arms


def db_counts(lab):
    with lab.store.db() as db:
        return [db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ['jobs','trial_plans','trial_attempts','events','viewed_windows']]


def test_read_only_complete_original_five_arm_qualification_creates_no_work_or_final_access(original_accounts,monkeypatch):
    from backend.lab.research_qualification_source import qualification_snapshot
    lab,study,arms=original_accounts;before=db_counts(lab)
    def forbidden(*a,**k):raise AssertionError('Saved qualification may not regenerate market/financial accounts.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    result=qualification_snapshot(lab,study['id'])
    assert result['state']=='complete' and result['candidate_ids']==[] and len(result['rows'])==2
    assert all(not row['prequalified'] and not row['candidate'] for row in result['rows'])
    assert result['controls']=={} and len(result['attrition'])==12
    assert result['attrition'][0]==dict(gate='discovery_signals',entering=2,passing=0,removed=2,
        unavailable=0,not_required=0,ineligible=0,cohort=dict(passing=0,failed=2,unavailable=0,not_required=0,ineligible=0),confirmed_passing_prefix=True)
    authority=result['source_authority']
    assert authority['original_saved_accounts_verified'] and authority['all_frozen_versions_included']
    assert all(value['verified_parts']==2 for value in authority['arms'].values())
    assert {key:value['job_id'] for key,value in authority['arms'].items()}==arms
    assert db_counts(lab)==before and lab.guard.study(study['id'])['status']=='registered'


def test_unreserved_and_unfinished_original_arms_cannot_qualify(inputs,registration):
    from backend.lab.research_funnel_arms import queue_arms
    from backend.lab.research_qualification_source import qualification_snapshot
    lab,request,*_=inputs;study=registration.register_funnel(lab,request)
    assert qualification_snapshot(lab,study['id'])['state']=='awaiting_arm_reservation'
    queue_arms(lab,study['id']);result=qualification_snapshot(lab,study['id'])
    assert result['state']=='incomplete_accounts' and result['candidate_ids']==[]
    assert all(arm['status']=='queued' for arm in result['arms'].values())


@pytest.mark.parametrize('fault',['missing_part','changed_part','missing_root_event','changed_checkpoint','closing_part','cancel'])
def test_missing_corrupt_or_mid_read_changed_originals_never_certify(original_accounts,monkeypatch,fault):
    from backend.lab import research_qualification_source as source
    from backend.lab.store import StateError
    lab,study,arms=original_accounts;parent=arms['era_two'];path=lab.output_path(parent).parent/'parts'/'000000.json.gz';cancel=None
    if fault=='missing_part':path.unlink()
    elif fault=='changed_part':path.write_bytes(b'changed original')
    elif fault=='missing_root_event':
        with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(parent,))
    elif fault=='changed_checkpoint':
        with lab.store.db() as db:db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=? AND part=0",('0'*64,parent))
    elif fault=='closing_part':
        original=source.qualify
        def change_after_read(*args,**kwargs):
            result=original(*args,**kwargs);path.write_bytes(b'changed during qualification');return result
        monkeypatch.setattr(source,'qualify',change_after_read)
    else:cancel=lambda:True
    with pytest.raises((StateError,InterruptedError)):source.qualification_snapshot(lab,study['id'],cancel)


def test_original_diagnostic_absent_queued_and_actual_ineligible_states_are_not_passes(original_accounts):
    from backend.lab.research_qualification_source import _control
    from backend.lab.worker import Worker
    lab,study,arms=original_accounts;parent=lab.store.job(arms['primary_discovery'])
    assert _control(lab,parent,0,None)==(dict(state='missing'),None)
    child=lab.create_trade_twins(parent['id'],0)
    value,original=_control(lab,parent,0,None)
    assert value['state']=='queued' and value['job_id']==child['id'] and original is None
    assert Worker(lab).run_once() and lab.store.job(child['id'])['status']=='completed'
    value,original=_control(lab,parent,0,None)
    assert value['state']=='ineligible' and original is not None
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON t.id=a.trial_id WHERE t.job_id=? AND t.window!='prepare'",(child['id'],)).fetchone()[0]==0
