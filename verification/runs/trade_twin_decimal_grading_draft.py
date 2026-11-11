"""Uninstalled exact-money grading extension; legacy float input stays separate."""
from decimal import Decimal,InvalidOperation,localcontext
from typing import Literal
from pydantic import field_validator
from scipy.stats import binomtest
from backend.lab.trade_twins import _SetOutcome,_integer,TOTAL_SETS,EXECUTION_POLICIES


class CanonicalOutcome(_SetOutcome):
    amount_encoding:Literal['canonical-decimal-v1']
    net_profit:str|None

    @field_validator('net_profit',mode='before')
    @classmethod
    def exact_money(cls,value):
        if value is None:return None
        if not isinstance(value,str) or len(value)>128:raise ValueError('Financial totals require bounded canonical Decimal strings.')
        try:amount=Decimal(value)
        except InvalidOperation as error:raise ValueError('Financial total is not a Decimal.') from error
        if not amount.is_finite() or str(amount)!=value:raise ValueError('Financial total is not finite canonical Decimal text.')
        return value


def exact_total(values):
    amounts=[Decimal(str(value)) for value in values]
    if any(not amount.is_finite() for amount in amounts):raise ValueError('Nonfinite financial amount.')
    if not amounts:return Decimal(0)
    # Cover the entire finite decimal exponent span plus carry digits. A fixed
    # global context can silently erase small trades next to large ones.
    precision=max(80,max(v.adjusted() for v in amounts)-min(v.as_tuple().exponent for v in amounts)+len(str(len(amounts)))+2)
    with localcontext() as context:
        context.prec=precision
        return sum(amounts,Decimal(0))


def summarize_financial(plan,seed,policy,results,cancel=None):
    _integer(seed,0,2**31-1,'Seed')
    if policy not in EXECUTION_POLICIES:raise ValueError('Choose a declared interpretation.')
    real=exact_total(s.net_profit for s in plan.sources)
    seen=bytearray(TOTAL_SETS);observed=complete=failed=exceedances=0
    for value in results:
        if cancel and cancel():raise InterruptedError('Exact financial grading canceled.')
        if not plan.eligible:raise ValueError('An ineligible original cohort cannot have financial outcomes.')
        row=CanonicalOutcome.model_validate(value)
        if (row.plan_hash,row.seed,row.policy,row.trade_count)!=(plan.plan_hash,seed,policy,len(plan.sources)):
            raise ValueError('Financial outcome differs from its frozen original cohort.')
        if seen[row.set_index]:raise ValueError('Duplicate financial set ordinal.')
        seen[row.set_index]=1;observed+=1
        if row.state=='failed':failed+=1
        else:complete+=1;exceedances+=Decimal(row.net_profit)>=real
    eligible=plan.eligible and complete==TOTAL_SETS and failed==0
    interval=None
    if eligible:
        ci=binomtest(exceedances,TOTAL_SETS).proportion_ci(confidence_level=.95,method='exact');interval=[float(ci.low),float(ci.high)]
    return dict(plan_hash=plan.plan_hash,seed=seed,policy=policy,amount_encoding='canonical-decimal-v1',
        state='completed' if eligible else 'ineligible' if not plan.eligible else 'failed' if failed else 'incomplete',
        expected_sets=TOTAL_SETS,observed_sets=observed,complete_sets=complete,failed_sets=failed,source_trades=len(plan.sources),real_profit=str(real),exceedances=exceedances,
        raw_exceedance_fraction=exceedances/TOTAL_SETS if eligible else None,plus_one_diagnostic=(1+exceedances)/(TOTAL_SETS+1) if eligible else None,
        monte_carlo_interval_95=interval,adapted_pass=20*exceedances<TOTAL_SETS if eligible else None,host_engine_parity_verified=False)
