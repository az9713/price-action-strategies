"""Independent supplied-signal execution/basic metrics for every saved account in the existing-workflow browser bundle.
This is scoped accounting evidence, not detector-omission, uncertainty-interval or trading-edge certification.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import hashlib,json,math,os,statistics,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import identity
from backend.lab.research import core_hash
from backend.lab.data import read_manifest,load_window,prepare,Action
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
browser=(root/sys.argv[1]).resolve();browser.relative_to(root);lab=Lab(root);entries=[];records=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
for folder in sorted((browser/'artifacts').iterdir()):
 if not folder.is_dir():continue
 for file in sorted(folder.glob('*.json')):
  role=None;part=None
  if file.name.startswith('account-') and file.stem[8:].isdigit():
   role='flat_borrow_rate';jid=read(folder/'sensitivity-observations.json')['job_id'];part=int(file.stem[8:])
  elif file.name=='downloaded-borrow-account.json':role='changing_borrow';jid=read(folder/'borrow-observations.json')['job_id']
  elif file.name=='downloaded-news-account.json':role='news';jid=read(folder/'news-observations.json')['job_id']
  elif file.name=='downloaded-report.json':role='shared_portfolio' if read(file)['report_type']=='shared_capital_portfolio' else 'ordinary_strategy';jid=read(folder/'observations.json')['job_id']
  if role:
   report=lab.report(jid,part);assert read(file)==report;entries.append((role,folder.name,jid,part,report))
 observations=folder/'result-ownership-observations.json'
 if observations.exists():
  for jid in read(observations)['jobs']:entries.append(('global_result_ownership',folder.name,jid,None,lab.report(jid)))
for role,profile,jid,part,report in entries:
 assert report['core_hash']==core_hash()
 manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert report['dataset_manifest_hash']==identity(manifest)
 start=report['provenance']['warmup_start'];lab.guard.access(manifest['quality']['symbols'],start,report['end'],'existing_ui_independent_account_reread')
 frame,_=load_window(lab.datasets_root,report['dataset_id'],start,report['end']);actions=[Action(**a) for a in manifest['actions'] if start<=a['ex_date']<=report['end']];regular=prepare(frame,actions)
 configs={r['config_id']:r['config'] for r in report['configurations']} if report['report_type']=='shared_capital_portfolio' else {report['config_id']:report['config']}
 signals=report['signals'] if report['report_type']=='shared_capital_portfolio' else [s|dict(config_id=report['config_id']) for s in report['signals']]
 expected=execute(primitive(regular),signals,configs,report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end']);assert_parity(SimpleNamespace(**report),expected)
 capital=Decimal(str(report['portfolio']['capital']));equities=[capital,*[r['equity'] for r in expected['equity']]];daily=[b-a for a,b in zip(equities,equities[1:])];returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])];profits=[t['net_pnl'] for t in expected['trades']];high=capital;drawdown=Decimal(0)
 for value in equities:high=max(high,value);drawdown=max(drawdown,(high-value)/high)
 metrics=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits) if profits else None,marked_sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252) if len(returns)>1 and statistics.stdev(returns)>0 else None,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
 for key,value in metrics.items():
  if value is None:assert report['metrics'][key] is None
  else:assert abs(Decimal(str(report['metrics'][key]))-Decimal(str(value)))<=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10'),(role,key)
 if report['report_type']=='shared_capital_portfolio':
  assert sum(a['trades'] for a in report['attribution'])==len(profits)
  assert abs(sum(Decimal(str(a['closed_trade_net_profit'])) for a in report['attribution'])-metrics['net_profit'])<=Decimal('1e-7')
 records.append(dict(role=role,profile=profile,job_id=jid,part=part,core_hash=report['core_hash'],signals=len(report['signals']),trades=len(profits),ledger_events=len(expected['ledger']),daily_marks=len(expected['equity']),independent_metrics={k:None if v is None else str(v) for k,v in metrics.items()}))
expected_counts={'flat_borrow_rate':8,'changing_borrow':2,'news':2,'ordinary_strategy':2,'shared_portfolio':2,'global_result_ownership':4}
counts={role:sum(r['role']==role for r in records) for role in expected_counts};assert counts==expected_counts and len(records)==20
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(output/'existing-browser-independent-accounts.json').write_text(json.dumps(dict(scope=__doc__,role_counts=counts,accounts=records),indent=2),encoding='utf-8')
print(json.dumps(dict(complete_accounts=len(records),role_counts=counts,scope=__doc__)))
