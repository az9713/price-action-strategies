"""Unknown or unneeded controls must not be described as statistical failures."""
import importlib.util
from pathlib import Path
import pytest
from backend.lab.config import identity

spec=importlib.util.spec_from_file_location('qualification_attrition_fixtures',Path(__file__).with_name('research-qualification-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs;registration=fixtures.registration;kernel=fixtures.kernel;arithmetic_accounts=fixtures.arithmetic_accounts


def test_pending_and_not_required_controls_are_not_failed_strategy_tests(kernel,arithmetic_accounts):
    frozen,reports=arithmetic_accounts;cid=identity(frozen['configurations'][0]);report=reports['era_two'][cid]
    report['metrics']['net_profit']=0;report['equity']=[dict(row,equity=100000) for row in report['equity']]
    for trade in report['trades']:trade['net_pnl']=0
    result=kernel.qualify(frozen,reports);rows={row['gate']:row for row in result['attrition']}
    matched=rows['matched_entries']
    assert matched.get('cohort')==dict(passing=0,failed=0,unavailable=1,not_required=1,ineligible=0)
    assert matched['entering']==2 and matched['passing']==0 and matched['removed']==0
    assert matched['unavailable']==1 and matched['not_required']==1
    assert rows['era_two_profit']['cohort']==dict(passing=1,failed=1,unavailable=0,not_required=0,ineligible=0)
    assert result['state']=='awaiting_controls' and len(result['pending_control_ids'])==1


def test_completed_negative_control_is_a_failure_and_pending_control_is_unavailable(kernel,arithmetic_accounts):
    frozen,reports=arithmetic_accounts;controls=fixtures.completed_controls(frozen)
    first=identity(frozen['configurations'][0]);second=identity(frozen['configurations'][1])
    for summary in controls[first]['summaries'].values():summary['exceedances']=500
    controls[second]=dict(state='queued')
    result=kernel.qualify(frozen,reports,controls)
    matched=next(row for row in result['attrition'] if row['gate']=='matched_entries')
    assert matched.get('cohort')==dict(passing=0,failed=1,unavailable=1,not_required=0,ineligible=0)
    assert matched['removed']==1 and matched['unavailable']==1
    assert result['candidate_ids']==[] and result['state']=='awaiting_controls'


def test_original_ineligible_matching_plan_finishes_assessment_without_passing_or_waiting_forever(kernel,arithmetic_accounts):
    frozen,reports=arithmetic_accounts;ids=[identity(c) for c in frozen['configurations']]
    result=kernel.qualify(frozen,reports,{cid:dict(state='ineligible') for cid in ids})
    assert result['state']=='complete'
    assert result['candidate_ids']==[] and result['pending_control_ids']==[]
    assert result['ineligible_control_ids']==ids
    matched=next(row for row in result['attrition'] if row['gate']=='matched_entries')
    assert matched['cohort']['ineligible']==2 and matched['cohort']['failed']==0


@pytest.mark.parametrize('state',['failed','canceled','missing','incomplete'])
def test_unavailable_control_requires_original_recovery_and_never_becomes_terminal_ineligible(kernel,arithmetic_accounts,state):
    frozen,reports=arithmetic_accounts;ids=[identity(c) for c in frozen['configurations']]
    result=kernel.qualify(frozen,reports,{cid:dict(state=state) for cid in ids})
    assert result['state']=='awaiting_controls' and result['pending_control_ids']==ids
    assert result.get('ineligible_control_ids')==[] and result['candidate_ids']==[]
