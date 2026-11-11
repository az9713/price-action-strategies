"""Separate account-equity reconciliation from the Sharpe formula's identical-input oracle."""
from pathlib import Path
from decimal import Decimal,localcontext
from statistics import mean,stdev
import json,math,os,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.data import read_manifest,load_window,prepare,Action
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
from types import SimpleNamespace
lab=Lab(root);jid='e41eba3a9a0e46bb8a8001fa0bbcc641';report=lab.report(jid,0)
manifest=read_manifest(lab.datasets_root,report['dataset_id']);warmup=report['provenance']['warmup_start']
lab.guard.access(manifest['quality']['symbols'],warmup,report['end'],'sharpe_identical_input_oracle_diagnostic')
frame,_=load_window(lab.datasets_root,report['dataset_id'],warmup,report['end']);actions=[Action(**a) for a in manifest['actions'] if warmup<=a['ex_date']<=report['end']]
expected=execute(primitive(prepare(frame,actions)),[s|dict(config_id=report['config_id']) for s in report['signals']],{report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end']);assert_parity(SimpleNamespace(**report),expected)
capital=report['portfolio']['capital'];actual=[float(capital),*[r['equity'] for r in report['equity']]];reference=[Decimal(str(capital)),*[r['equity'] for r in expected['equity']]]
def ratio(returns):return mean(returns)/stdev(returns)*math.sqrt(252)
original=ratio([float((b-a)/a) for a,b in zip(reference,reference[1:])])
with localcontext() as context:
 context.prec=80
 exact=[Decimal.from_float(float(v)) for v in actual]
 held_returns=[float((b-a)/a) for a,b in zip(exact,exact[1:])];held=ratio(held_returns)
 equity_difference=max(abs(a-b) for a,b in zip(exact,reference))
float_formula=ratio([(b-a)/a for a,b in zip(actual,actual[1:])])
saved=report['metrics']['marked_sharpe'];return_difference=max(abs(a-b) for a,b in zip(held_returns,report['metrics']['daily_returns']))
value=dict(job_id=jid,part=0,metric='marked_sharpe',saved=saved,oracle_on_distinct_reference_equity=original,oracle_on_identical_actual_binary_equity=held,stdlib_float_formula_on_identical_equity=float_formula,max_account_equity_difference_dollars=str(equity_difference),frozen_account_money_tolerance='1e-7',frozen_sharpe_absolute_tolerance='1e-10',original_oracle_difference=abs(saved-original),identical_input_oracle_difference=abs(saved-held),actual_return_formula_max_difference=return_difference,scope=__doc__,explanation='The first oracle computed Sharpe on the independently reconciled Decimal account rather than on the exact saved input equity. Permitted tiny account-input differences were amplified in this high-Sharpe synthetic series. The financial account oracle and the metric-formula oracle must be tested separately; neither tolerance is widened.')
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'sharpe-input-precision.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2));assert equity_difference<=Decimal('1e-7');assert abs(saved-original)>1e-10;assert abs(saved-held)<=1e-10;assert return_difference==0
