"""Install explicitly recorded prototypes only into the uninstalled next stage."""
from pathlib import Path
import ast,hashlib,json,os,re,sys
root=Path.cwd();target=root/'data/dev026/next-src';baseline=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
def snap(folder):return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(folder)}
old=snap(baseline);records=[]
def create(name,original,transforms):
 path=root/original;raw=path.read_text(encoding='utf-8');original_sha=hashlib.sha256(path.read_bytes()).hexdigest()
 for before,after in transforms:
  assert raw.count(before)==1,(name,before,raw.count(before));raw=raw.replace(before,after,1)
 compile(raw,name,'exec');dest=target/name;assert not dest.exists();dest.write_text(raw,encoding='utf-8')
 records.append(dict(path=name,original=original,original_sha256=original_sha,installed_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),explicit_transforms=len(transforms)))
create('backend/lab/trade_twin_features.py','verification/runs/trade_twin_features_draft.py',[
 ('Prototype causal candidate features; not yet installed in the staged app.','Causal candidate features for an original frozen trade-twin plan.'),
 ('from backend.lab.config import Strategy','from .config import Strategy'),('from backend.lab.data import aggregate,schedule','from .data import aggregate,schedule'),
 ('from backend.lab.signals import prior_atr','from .signals import prior_atr'),('from backend.lab.trade_twins import TwinMoment,MAX_CLOCK_MINUTES,MAX_MOMENTS','from .trade_twins import TwinMoment,MAX_CLOCK_MINUTES,MAX_MOMENTS')])
grade=(root/'verification/runs/trade_twin_decimal_grading_draft.py').read_text(encoding='utf-8')
total=next(n for n in ast.parse(grade).body if isinstance(n,ast.FunctionDef) and n.name=='exact_total')
create('backend/lab/trade_twin_results.py','verification/runs/trade_twin_decimal_grading_draft.py',[
 ('Uninstalled exact-money grading extension; legacy float input stays separate.','Exact-money complete-cohort grading; original book authority is checked by the worker.'),
 ('from decimal import Decimal,InvalidOperation,localcontext','from decimal import Decimal'),
 ('from backend.lab.trade_twins import _SetOutcome,_integer,TOTAL_SETS,EXECUTION_POLICIES','from .trade_twins import _SetOutcome,_integer,TOTAL_SETS,EXECUTION_POLICIES\nfrom .trade_twin_amounts import exact_total,read_amount'),
 (ast.get_source_segment(grade,total),''),
 ("        if not isinstance(value,str) or len(value)>128:raise ValueError('Financial totals require bounded canonical Decimal strings.')\n        try:amount=Decimal(value)\n        except InvalidOperation as error:raise ValueError('Financial total is not a Decimal.') from error\n        if not amount.is_finite() or str(amount)!=value:raise ValueError('Financial total is not finite canonical Decimal text.')",'        read_amount(value)'),
 ("    if policy not in EXECUTION_POLICIES:raise ValueError('Choose a declared interpretation.')","    if policy not in EXECUTION_POLICIES:raise ValueError('Choose a declared interpretation.')\n    if cancel and cancel():raise InterruptedError('Exact financial grading canceled before work.')")])
create('tests/test_trade_twin_features.py','verification/runs/test_trade_twin_features_prototype.py',[
 ('Independent primitive-candle/Wilder checks for the next feature component.','Independent primitive-candle/Wilder checks for production preparation.'),
 ("path=Path(os.environ['PA_FEATURE_PROTOTYPE_PATH'])\nspec=importlib.util.spec_from_file_location('owned_candidate_prototype',path);prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)",'from backend.lab import trade_twin_features as prototype')])
create('tests/test_trade_twin_results.py','verification/runs/test_trade_twin_decimal_grading_prototype.py',[
 ('Exact-money boundaries, separate from legacy float input contracts.','Production exact-money boundaries, separate from legacy float input contracts.'),
 ("path=Path(os.environ['PA_GRADE_PROTOTYPE_PATH']);spec=importlib.util.spec_from_file_location('exact_financial_grade',path);grade=importlib.util.module_from_spec(spec);spec.loader.exec_module(grade)",'from backend.lab import trade_twin_results as grade'),
 ("'9'*129","'9'*1025")])
assert old==snap(baseline)
(out/'installed-preparation-source.json').write_text(json.dumps(dict(scope=__doc__,files=records,original_frozen_baseline_unchanged=True,main_app_source_replaced=False,final_acceptance_certified=False),indent=2),encoding='utf-8')
print(json.dumps(dict(installed_files=len(records),original_baseline_unchanged=True,main_app_source_replaced=False)))
