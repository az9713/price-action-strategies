"""Explicit positive capability assertions for real original-account audits.

Rejection of these valid accounts is a semantic failure, not a mutation-harness
error. These probes do not permit malformed accounts or weaken reconciliation.
"""
import pytest
from backend.lab.config import Costs
from backend.lab.data import Action
from backend.lab.source_cashflows import audit_fills
from test_source_cashflows import observed


@pytest.mark.parametrize('scenario',['plain','fees','borrow','split','dividend'])
def test_known_valid_original_financial_account_is_auditable(scenario):
    cost=Costs(commission_per_share=.017 if scenario=='fees' else 0,spread_bps=0,slippage_bps=0,
               borrow_annual=.12 if scenario=='borrow' else 0)
    actions=[Action('SPY','2026-11-05','split',.5)] if scenario=='split' else [Action('SPY','2026-11-05','dividend',.37)] if scenario=='dividend' else []
    days=('2026-11-04','2026-11-05') if actions else ('2026-11-04',)
    data,original,cost=observed(days=days,side=-1 if scenario=='borrow' else 1,costs=cost,actions=actions)
    rejected=None;value=None
    try:value=audit_fills(data,original.trades,original.entry_traces,cost,actions,'a'*64)
    except ValueError as error:rejected=str(error)
    assert rejected is None,'A valid observed original account was rejected: '+str(rejected)
    assert value is not None and len(value['trades'])==1
