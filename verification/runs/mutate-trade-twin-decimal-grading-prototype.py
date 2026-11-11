"""Actual exact-money prototype mutations using the recorded assertion-only harness."""
from pathlib import Path
import re
root=Path.cwd();code=(root/'verification/runs/mutate-trade-twin-feature-prototype.py').read_text(encoding='utf-8')
specs=[
 ('float-roundtrip',"exceedances+=Decimal(row.net_profit)>=real","exceedances+=Decimal(str(float(row.net_profit)))>=real",'exact_large and 9999'),
 ('default-sum-context','context.prec=precision','context.prec=28','cohort_baseline_sum'),
 ('ties-count','exceedances+=Decimal(row.net_profit)>=real','exceedances+=Decimal(row.net_profit)>real','exact_large and 10000000000.0'),
 ('strict-five-percent','adapted_pass=20*exceedances<TOTAL_SETS','adapted_pass=20*exceedances<=TOTAL_SETS','threshold and 500'),
 ('complete-denominator','eligible=plan.eligible and complete==TOTAL_SETS and failed==0','eligible=plan.eligible and complete>0 and failed==0','partial_and_cancelled'),
 ('original-identity',"if (row.plan_hash,row.seed,row.policy,row.trade_count)!=(plan.plan_hash,seed,policy,len(plan.sources)):",'if False:','wrong_hash or wrong_seed or wrong_policy or wrong_cohort')]
pattern=r'specs=\[.*?\]\nfor name,before,after,_ in specs:'
assert len(re.findall(pattern,code,re.DOTALL))==1
code=re.sub(pattern,lambda _:'specs='+repr(specs)+'\nfor name,before,after,_ in specs:',code,count=1,flags=re.DOTALL)
for before,after in [
 ('trade_twin_features_draft.py','trade_twin_decimal_grading_draft.py'),
 ('test_trade_twin_features_prototype.py','test_trade_twin_decimal_grading_prototype.py'),
 ('PA_FEATURE_PROTOTYPE_PATH','PA_GRADE_PROTOTYPE_PATH'),
 ('feature-prototype-mutations','decimal-grading-prototype-mutations'),
 ('owned-feature','owned-grade')]:
 assert before in code,before
 code=code.replace(before,after)
exec(compile(code,'recorded-exact-money-prototype-mutation-harness','exec'))
