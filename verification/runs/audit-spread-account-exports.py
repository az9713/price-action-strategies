"""Every saved CSV value and a second complete supplied-signal Decimal account.

This export-case capture contains saved JSON/CSV values, not compressed original
part bytes. Original-byte lineage is audited separately on the first account.
No detector, data-vendor, source-scale or trading-edge certification is made.
"""
from pathlib import Path
from decimal import Decimal
import csv,io,json,hashlib,math,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.reference_execution import execute
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def read(p):return json.loads(p.read_text(encoding='utf-8'))
receipts=[]
for arg in sys.argv[1:]:
 p=root/arg;r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q.read_bytes())==a['sha256']
 receipts.append(r)
base=root/'verification/runs'/receipts[0]['receipt_id']/'actual-spread-account-exports';bars=read(root/'verification/runs'/receipts[1]['receipt_id']/'actual-spread-account-handoff/synthetic-primary-bars.json')
account=read(base/'account.json');result=read(base/'complete-result.json');inputs=read(base/'frozen-inputs.json');payload=inputs['payload']
assert identity(payload)==inputs['payload_sha256']==result['payload_hash'] and result['job_id']==inputs['job_id'] and result['spread_parent']==payload['spread_parent']
assert account['config']==payload['configurations'][0] and account['costs']==payload['costs'] and account['portfolio']==payload['portfolio']
assert identity(account['numerical_contract'])==account['core_hash']==result['core_hash'] and account['signal_scope']['symbols']==payload['evaluation_symbols']
assert {b['symbol'] for b in bars}==set(payload['evaluation_symbols'])
assert result['rows'][0]['metrics']==account['metrics'] and result['rows'][0]['config_id']==identity(account['config'])
prices={'price','entry_price','split_adjusted_entry','exit_price','stop','target','entry_quantity','exit_quantity','quantity'}
def compare(a,b,path=''):
 if isinstance(b,dict):
  assert set(a)==set(b),path
  for k in b:compare(a[k],b[k],path+'/'+k)
 elif isinstance(b,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif isinstance(b,(Decimal,int,float)) and not isinstance(b,bool):
  assert math.isfinite(float(a)) and math.isfinite(float(b)),path
  assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal('1e-9' if path.rsplit('/',1)[-1] in prices else '1e-7'),path
 else:assert a==b,(path,a,b)
reference=execute(bars,[s|dict(config_id=account['config_id']) for s in account['signals']],{account['config_id']:account['config']},account['costs'],account['portfolio'],[],account['start'],account['end'])
compare({k:account[k] for k in ['trades','ledger','equity','rejected']},reference)
counts={}
for name in ['search-statistics','search-screen']:
 doc=read(base/(name+'.json'));assert doc==result[name.replace('-','_')]
 rows=list(csv.DictReader(io.StringIO((base/(name+'.csv')).read_text(encoding='utf-8'))));counts[name]=len(rows)
 expected=[]
 for item in doc['accounts']:
  if name=='search-statistics':expected.extend({k:v for k,v in item.items() if k!='sensitivity'}|scenario for scenario in item['sensitivity'])
  else:expected.append(item)
 assert len(rows)==len(expected)
 for actual,item in zip(rows,expected):
  for key,value in item.items():
   if key=='failures':assert actual[key]==';'.join(value)
   elif value is None:assert actual[key]==''
   elif isinstance(value,bool):assert actual[key]==str(value)
   elif isinstance(value,(float,int)):compare(float(actual[key]),value,'/'+key)
   else:assert actual[key]==str(value),(name,key)
  for key in ['job_id','dataset_id','core_hash','start','end']:assert actual[key]==str(result[key]),key
screen=result['search_screen'];assert screen['settings']==payload['sampling_policy'] and screen['settings']['mode']=='spread_selected'
for item,row in zip(screen['accounts'],result['rows']):
 m=row['metrics'];flags=dict(signal_qualified=row['signal_count']>=screen['settings']['minimum_signals'],enough_trades=m['trades']>=payload['minimum_trades'],profitable=m['net_profit']>0,sharpe_passed=m['marked_sharpe'] is not None and m['marked_sharpe']>=payload['minimum_sharpe'])
 assert all(item[k]==v for k,v in flags.items()) and item['initial_gates_passed']==all(flags.values())
rows=list(csv.DictReader(io.StringIO((base/'trades.csv').read_text(encoding='utf-8'))));assert len(rows)==len(account['trades'])>0
for row,trade in zip(rows,account['trades']):
 for key,value in trade.items():
  if value is None:assert row[key]==''
  elif isinstance(value,(int,float)):compare(float(row[key]),value,'/'+key)
  else:assert row[key]==str(value),key
 assert row['dataset_id']==account['dataset_id']
assert account['metrics']['net_profit']<0 and not screen['accounts'][0]['initial_gates_passed']
value=dict(scope=__doc__,account_job_id=result['job_id'],original_parent=result['spread_parent'],csv_rows=counts|dict(trades=len(rows)),independent_trades=len(reference['trades']),independent_ledger_rows=len(reference['ledger']),independent_daily_marks=len(reference['equity']),loss_retained=True,final_acceptance_certified=False)
(out/'spread-account-independent-exports.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
