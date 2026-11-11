"""Independent original lineage and full supplied-signal Decimal account reconciliation.

Synthetic supplied prices/signals are audited; detectors, market-data accuracy,
full source-scale throughput and a trading edge are not certified.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
import gzip,hashlib,json,math,os,statistics,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.reference_execution import execute
from verification.reference_statistics import dsr_from_moments
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def read(p):return json.loads(p.read_text(encoding='utf-8'))
receipt=read(root/sys.argv[1]);assert receipt['command']['exit_code']==0
assert not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
for a in receipt['artifacts']:
 p=root/a['path'];assert p.stat().st_size==a['bytes'] and sha(p.read_bytes())==a['sha256']
base=root/'verification/runs'/receipt['receipt_id']/'actual-spread-account-handoff'
inputs={role:read(base/role/'inputs.json') for role in ['parent','child']};payloads={role:value['payload'] for role,value in inputs.items()}
events={role:read(base/role/'events.json') for role in inputs};registry={role:read(base/role/'registry.json') for role in inputs}
results={};binding=None
for role in inputs:
 p=base/role/'artifacts/result.json.gz';raw=p.read_bytes();result=json.loads(gzip.decompress(raw));results[role]=result
 assert identity(payloads[role])==inputs[role]['payload_sha256']==result['payload_hash'] and result['job_id']==inputs[role]['job_id']
 assert sha(raw)==[e['details']['sha256'] for e in events[role] if e['kind']=='result_saved'][-1]
 if role=='parent':assert identity(result['numerical_contract'])==result['core_hash']
 else:assert result['core_hash']==results['parent']['core_hash']
 assert len([e for e in events[role] if e['kind']=='trial_plan_frozen'])==1
parent,child=results['parent'],results['child'];original=payloads['parent'];frozen=payloads['child'];binding=frozen['spread_parent']
assert binding==child['spread_parent']==dict(job_id=inputs['parent']['job_id'],payload_hash=identity(original),result_sha256=sha((base/'parent/artifacts/result.json.gz').read_bytes()),selection_manifest_hash=parent['selection_manifest_hash'])
assert identity(parent['selection_manifest'])==parent['selection_manifest_hash'] and parent['spread_selection']['complete']
assert frozen['configurations']==parent['selection_manifest']['configurations'] and frozen['evaluation_symbols']==[original['primary_symbol']]
for key in ['dataset_id','dataset_manifest_hash','dataset_context','start','end','seed','costs','portfolio','statistics','minimum_trades','minimum_sharpe','news_dates','news_calendar_id','news_calendar']:
 if key in original:assert frozen[key]==original[key],key
links=[e['details'] for e in events['parent'] if e['kind']=='spread_accounts_frozen'];assert links==[dict(child_id=inputs['child']['job_id'],**binding)]
head=None;selected=[];probe_counts=[];ny=ZoneInfo('America/New_York')
for number,envelope in enumerate(e['details'] for e in events['parent'] if e['kind']=='spread_protocol'):
 body={k:envelope[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']}
 assert body['sequence']==number and body['previous']==head and body['payload_sha256']==identity(original) and identity(body)==envelope['event_sha256'];head=envelope['event_sha256'];e=body['event']
 if e['kind']=='version_selected':selected.append(e['configuration'])
 if e['kind']=='probe_completed':
  evidence=e['evidence'];p=base/'parent/artifacts/spread-signals'/(evidence['evidence_sha256']+'.json.gz');raw=p.read_bytes();report=json.loads(gzip.decompress(raw))
  assert sha(raw)==body['artifact_sha256'] and identity(report)==evidence['evidence_sha256'] and report['config_id']==e['config_id']==identity(report['config'])
  count=sum(original['start']<=datetime.fromisoformat(s['available_at']).astimezone(ny).date().isoformat()<=original['end'] for s in report['signals'])
  assert report['signal_count']==evidence['signal_count']==count and report['excluded_warmup_signals']==len(report['signals'])-count
  assert all(s['symbol']==original['primary_symbol'] for s in report['signals']);probe_counts.append(count)
assert selected==frozen['configurations'] and registry['parent']['totals']['computation_attempts']==len(probe_counts)
bars=read(base/'synthetic-primary-bars.json');assert {b['symbol'] for b in bars}==set(frozen['evaluation_symbols'])
price_keys={'price','entry_price','split_adjusted_entry','exit_price','stop','target','entry_quantity','exit_quantity','quantity'}
def compare(actual,expected,path=''):
 if isinstance(expected,dict):
  assert set(actual)==set(expected),path
  for k in expected:compare(actual[k],expected[k],path+'/'+k)
 elif isinstance(expected,list):
  assert len(actual)==len(expected),(path,len(actual),len(expected))
  for i,(a,b) in enumerate(zip(actual,expected)):compare(a,b,path+'/'+str(i))
 elif isinstance(expected,(Decimal,float,int)) and not isinstance(expected,bool):
  assert math.isfinite(float(actual)) and math.isfinite(float(expected)),path
  tolerance=Decimal('1e-9' if path.rsplit('/',1)[-1] in price_keys else '1e-7')
  assert abs(Decimal(str(actual))-Decimal(str(expected)))<=tolerance,(path,actual,str(expected))
 else:assert actual==expected,(path,actual,expected)
accounts=[];assert len(child['rows'])==len(frozen['configurations'])
for index,(row,cfg) in enumerate(zip(child['rows'],frozen['configurations'])):
 p=base/'child/artifacts/parts'/(str(index).zfill(6)+'.json.gz');raw=p.read_bytes();value=json.loads(gzip.decompress(raw));report=value['report']
 assert row['part']==index and row['config']==cfg and row['config_id']==report['config_id']==identity(cfg) and sha(raw)==row['report_sha256']
 assert report['costs']==frozen['costs'] and report['portfolio']==frozen['portfolio'] and report['metrics']==row['metrics']
 assert identity(report['numerical_contract'])==report['core_hash']==child['core_hash']
 assert report['signal_scope']['symbols']==frozen['evaluation_symbols'] and report['dataset_context']==original['dataset_context'] and set(report['charts'])==set(frozen['evaluation_symbols'])
 expected=execute(bars,[s|dict(config_id=report['config_id']) for s in report['signals']],{report['config_id']:cfg},report['costs'],report['portfolio'],[],report['start'],report['end'])
 compare({k:report[k] for k in ['trades','ledger','equity','rejected']},expected)
 capital=Decimal(str(frozen['portfolio']['capital']));values=[capital,*[e['equity'] for e in expected['equity']]];daily=[b-a for a,b in zip(values,values[1:])];returns=[float((b-a)/a) for a,b in zip(values,values[1:])]
 high=capital;drawdown=Decimal(0)
 for v in values:high=max(high,v);drawdown=max(drawdown,(high-v)/high)
 profits=[t['net_pnl'] for t in expected['trades']];sigma=statistics.stdev(returns) if len(returns)>1 else 0
 metrics=dict(net_profit=values[-1]-capital,total_return=values[-1]/capital-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits) if profits else None,marked_sharpe=statistics.mean(returns)/sigma*math.sqrt(252) if sigma else None,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
 for key,v in metrics.items():
  if v is None:assert report['metrics'][key] is None
  else:assert abs(Decimal(str(report['metrics'][key]))-Decimal(str(v)))<=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10'),key
 compare(report['metrics']['daily_pnl'],daily);compare(report['metrics']['daily_returns'],returns)
 stats=child['search_statistics']['accounts'][index];assert stats['part']==index and stats['config_id']==row['config_id'] and stats['source_part_sha256']==row['report_sha256']
 if sigma and len(returns)>3:
  n=len(returns);mu=statistics.mean(returns);m2=sum((r-mu)**2 for r in returns)/n;m3=sum((r-mu)**3 for r in returns)/n;m4=sum((r-mu)**4 for r in returns)/n
  sr=mu/sigma;sk=math.sqrt(n*(n-1))/(n-2)*m3/m2**1.5;ku=(n-1)/((n-2)*(n-3))*((n+1)*(m4/m2**2-3)+6)+3
  for key,v in [('daily_sharpe',sr),('skewness',sk),('raw_kurtosis',ku)]:assert abs(stats[key]-v)<=1e-9,key
  for scenario in stats['sensitivity']:
   dispersion=child['search_statistics']['trial_sharpe_std'];trials=scenario['effective_trials']
   if trials>1 and dispersion is None:assert scenario['undefined_reason']=='dispersion_unavailable';continue
   score=dsr_from_moments(sr,n,sk,ku,trials,0 if trials==1 else dispersion)
   assert scenario['undefined_reason'] is None and abs(scenario['score']-score)<=1e-10
 accounts.append(dict(part=index,config_id=row['config_id'],supplied_signals=len(report['signals']),trades=len(expected['trades']),ledger_rows=len(expected['ledger']),daily_marks=len(expected['equity']),metrics={k:None if v is None else str(v) for k,v in metrics.items()}))
assert registry['child']['totals']['planned_occurrences']==registry['child']['totals']['computation_attempts']==len(accounts)
value=dict(scope=__doc__,original_parent_id=inputs['parent']['job_id'],child_id=inputs['child']['job_id'],parent_probe_counts=probe_counts,selected_accounts=len(accounts),complete_decimal_accounts=accounts,source_scale_executed=False,final_acceptance_certified=False)
(out/'independent-spread-account-audit.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
