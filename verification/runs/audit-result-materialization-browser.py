"""Original input/root/all-part projection parity plus six independent supplied-signal Decimal accounts. No detector-omission or edge certificate."""
from pathlib import Path
from types import SimpleNamespace
from decimal import Decimal
import hashlib,json,math,os,statistics,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import identity
from backend.lab.data import read_manifest,load_window,prepare,Action
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
browser=root/sys.argv[1];lab=Lab(root);selected=[];roots=[]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
for observation in sorted((browser/'artifacts').glob('*/result-materialization-observations.json')):
 folder=observation.parent;info=read(observation);jid=info['job_id'];job=lab.store.job(jid);original=lab.result(jid);assert original==read(folder/'original-complete-result.json') and original['payload_hash']==identity(job['payload'])
 rows=[];stats=[];screen=[]
 for offset in range(0,len(original['rows']),20):
  rows+=lab.result_index.rows(jid,20,offset)['rows'];stats+=lab.result_index.auxiliary(jid,'statistics',20,offset)['accounts'];screen+=lab.result_index.auxiliary(jid,'screen',20,offset)['accounts']
 assert rows==original['rows'] and stats==original['search_statistics']['accounts'] and screen==original['search_screen']['accounts']
 fingerprints=[]
 for row in original['rows']:
  report=lab.report(jid,row['part']);assert report['config_id']==row['config_id']==identity(report['config']) and report['metrics']==row['metrics']
  path=lab.root/'data/jobs'/jid/'parts'/(str(row['part']).zfill(6)+'.json.gz');assert hashlib.sha256(path.read_bytes()).hexdigest()==row['report_sha256'];fingerprints.append(row['report_sha256'])
 part=info['selected_part'];report=lab.report(jid,part);assert report==read(folder/'selected-complete-report.json');selected.append((jid,part,report));roots.append(dict(job_id=jid,all_rows=len(rows),all_statistic_accounts=len(stats),all_screen_accounts=len(screen),all_original_parts=len(fingerprints),input_hash=identity(job['payload']),part_hashes=fingerprints))
for observation in sorted((browser/'artifacts').glob('*/result-ownership-observations.json')):
 for jid in read(observation)['jobs']:selected.append((jid,None,lab.report(jid)))
accounts=[]
for jid,part,report in selected:
 manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert report['dataset_manifest_hash']==identity(manifest)
 start=report['provenance']['warmup_start'];lab.guard.access(manifest['quality']['symbols'],start,report['end'],'result_view_independent_supplied_signal_audit')
 frame,_=load_window(lab.datasets_root,report['dataset_id'],start,report['end']);actions=[Action(**a) for a in manifest['actions'] if start<=a['ex_date']<=report['end']];regular=prepare(frame,actions)
 expected=execute(primitive(regular),[s|dict(config_id=report['config_id']) for s in report['signals']],{report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end']);assert_parity(SimpleNamespace(**report),expected)
 capital=Decimal(str(report['portfolio']['capital']));equities=[capital,*[e['equity'] for e in expected['equity']]];daily=[b-a for a,b in zip(equities,equities[1:])];returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])];profits=[t['net_pnl'] for t in expected['trades']];high=capital;drawdown=Decimal(0)
 for value in equities:high=max(high,value);drawdown=max(drawdown,(high-value)/high)
 deviation=statistics.stdev(returns) if len(returns)>1 else 0
 metrics=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits) if profits else None,marked_sharpe=statistics.mean(returns)/deviation*math.sqrt(252) if deviation>0 else None,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
 for key,value in metrics.items():
  if value is None:assert report['metrics'][key] is None,(key,report['metrics'][key])
  else:assert abs(Decimal(str(report['metrics'][key]))-Decimal(str(value)))<=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10'),(key,report['metrics'][key],str(value))
 accounts.append(dict(job_id=jid,part=part,trades=len(expected['trades']),ledger_rows=len(expected['ledger']),daily_marks=len(expected['equity']),metrics={k:None if v is None else str(v) for k,v in metrics.items()}))
assert len(roots)==2 and len(accounts)==6
value=dict(scope=__doc__,roots=roots,independent_accounts=accounts);out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(out/'result-view-original-and-independent-accounts.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(original_rows=sum(r['all_rows'] for r in roots),original_parts=sum(r['all_original_parts'] for r in roots),independent_supplied_signal_accounts=len(accounts),scope=__doc__)))
