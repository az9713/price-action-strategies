"""Reopen complete original synthetic financial artifacts and replay independent books.

This checks saved files rather than accepting pytest's passing case count. It
does not establish original parent authority, durable sets, UI or live-market
performance, and does not create or consume any user financial job.
"""
from pathlib import Path
from decimal import Decimal,localcontext
import hashlib,importlib.util,json,os,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/sys.argv[1]).resolve();assert p.is_relative_to((root/'verification/receipts').resolve())
r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256']
subject=read(root/next(a['path'] for a in r['artifacts'] if a['path'].endswith('dev026-source-subject.json')))
current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
assert current==subject['source_files'] and not subject['changed_during_check']
spec=importlib.util.spec_from_file_location('independent_saved_twin_reference',source/'verification/trade_twin_reference.py');reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
def compare(saved,expected,where):
 if isinstance(expected,dict):
  assert isinstance(saved,dict) and set(saved)==set(expected),where
  for k,v in expected.items():compare(saved[k],v,where+'.'+k)
 elif isinstance(expected,list):
  assert isinstance(saved,list) and len(saved)==len(expected),where
  for i,v in enumerate(expected):compare(saved[i],v,where+f'[{i}]')
 elif isinstance(expected,Decimal):
  actual=Decimal(saved);assert actual.is_finite() and abs(actual-expected)<=Decimal('1e-7'),(where,saved,str(expected))
 else:assert type(saved) is type(expected) and saved==expected,(where,saved,expected)
books=[root/a['path'] for a in r['artifacts'] if '/financial-books/' in a['path'] and a['path'].endswith('.json')]
assert len(books)>=70
records=[];complete=failed=losses=profits=0;ledger_rows=equity_rows=0;policies=set();directions=set()
with localcontext() as context:
 context.prec=80
 for p in books:
  value=read(p);i=value['inputs'];actual=value['actual'];assert value['all_fields_compared'] and value['unchanged_inputs']
  assert p.stem==hashlib.sha256(json.dumps(i,sort_keys=True,default=str).encode()).hexdigest()
  expected=reference.execute_reference(i['bars'],i['match'],i['configuration'],i['costs'],i['account'],i['actions'],i['policy'])
  compare(actual,expected,p.name);compare(value['independent_reference'],expected,p.name+' original reference')
  initial=Decimal(actual['financing']['initial_cash']);cash=initial;borrow=Decimal(0);fees=Decimal(0);entitlements=Decimal(0)
  for row in actual['ledger']:
   assert Decimal(row['cash_before'])==cash
   cash+=Decimal(row['cash_change']);assert Decimal(row['cash_after'])==cash
   if row['kind']=='borrow':borrow-=Decimal(row['cash_change'])
   if row['kind'] in {'entry','exit'}:fees+=Decimal(row['fee'])
   if row['kind']=='distribution_entitlement':entitlements+=Decimal(row['amount'])
  assert cash==Decimal(actual['final_cash'])
  if actual['trade'] is not None:
   trade=actual['trade'];q=Decimal(trade['exit_quantity']);gross=trade['side']*q*(Decimal(trade['exit_price'])-Decimal(trade['split_adjusted_entry']))
   net=gross+entitlements-borrow-fees
   assert abs(net-Decimal(trade['net_pnl']))<=Decimal('1e-7')
   assert borrow==Decimal(trade['borrow']) and fees==Decimal(trade['fees']) and entitlements==Decimal(trade['distributions'])
   assert abs(cash+Decimal(actual['final_receivables'])-initial-net)<=Decimal('1e-7')
   assert Decimal(trade['entry_quantity'])==Decimal(i['match']['quantity'])
   assert actual['equity'] and Decimal(actual['equity'][-1]['gross_exposure'])==0
   losses+=net<0;profits+=net>0
  else:assert actual['status']=='failed' and not actual['ledger'] and not actual['equity']
  if actual['status']=='complete':
   complete+=1;assert Decimal(actual['net_profit'])==Decimal(actual['trade']['net_pnl'])
  else:failed+=1;assert actual['net_profit'] is None and actual['failure'] and (actual['rejected'] or actual['trade']['exit_reason']=='borrow_recall')
  policies.add(i['policy']);directions.add(i['match']['side']);ledger_rows+=len(actual['ledger']);equity_rows+=len(actual['equity'])
  records.append(dict(path=p.relative_to(root).as_posix(),sha256=sha(p),status=actual['status'],ledger_rows=len(actual['ledger']),equity_rows=len(actual['equity'])))
assert policies=={'barrier_capped_elapsed_v1','fixed_elapsed_v1'} and directions=={-1,1} and min(failed,losses,profits)>0
assert current=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
value=dict(scope=__doc__,source_receipt=r['receipt_id'],source_files_verified=len(current),books=len(books),complete=complete,failed=failed,losing_books=losses,profitable_books=profits,ledger_rows=ledger_rows,equity_rows=equity_rows,all_saved_fields_replayed=True,original_sources_unchanged=True,records=records,financial_sets_executed=0,final_acceptance_certified=False)
(out/'financial-books-audit.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='records'},indent=2))
