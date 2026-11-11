"""Keep the independent account oracle; test Sharpe's formula on its identical saved inputs.
Retain the original1e-7 account-money and1e-10 derived-metric tolerances unchanged.
"""
from pathlib import Path
import json,os
source=Path('verification/runs/check-common-browser-accounts.py').read_text(encoding='utf-8')
before="   for k,v in metrics.items():close(report['metrics'][k],v,'1e-7' if k in ['net_profit','profit_without_ten_best_days'] else '1e-10')"
after="""   held_equity=[float(report['portfolio']['capital']),*[float(r['equity']) for r in report['equity']]]
   held_returns=[(b-a)/a for a,b in zip(held_equity,held_equity[1:])]
   metrics['marked_sharpe']=statistics.mean(held_returns)/statistics.stdev(held_returns)*math.sqrt(252) if len(held_returns)>1 and statistics.stdev(held_returns)>0 else None
   for a,b in zip(report['metrics']['daily_returns'],held_returns):assert a==b
   for k,v in metrics.items():
    try:close(report['metrics'][k],v,'1e-7' if k in ['net_profit','profit_without_ten_best_days'] else '1e-10')
    except AssertionError as error:raise AssertionError((jid,part,k,report['metrics'][k],str(v))) from error"""
assert source.count(before)==1
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'oracle-input-contract.json').write_text(json.dumps(dict(scope=__doc__,root_cause_receipt='verification/receipts/20261108T224527759385Z-common-sampling-same-equity-sharpe-original-tolerances-and-account-precision-root-cause.json',money_tolerance='1e-7',derived_metric_absolute_tolerance='1e-10',complete_independent_decimal_account_oracle_retained=True),indent=2),encoding='utf-8')
exec(compile(source.replace(before,after),'check-common-browser-accounts-v3-resolved.py','exec'))
