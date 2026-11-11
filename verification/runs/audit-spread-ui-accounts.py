"""Independent original-byte, every-CSV-field, supplied-signal Decimal and deck audit.

The three viewport accounts repeat the same synthetic scenario. They are not
independent market replications, independent detectors or evidence of an edge.
"""
from pathlib import Path
from decimal import Decimal
import csv,gzip,hashlib,importlib.util,io,json,math,os,re,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.reference_execution import execute
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def identity(v):return sha(canonical(v).encode())
receipt_path=root/sys.argv[1];receipt=read(receipt_path)
assert receipt['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
for a in receipt['artifacts']:
 p=root/a['path'];assert p.stat().st_size==a['bytes'] and sha(p.read_bytes())==a['sha256'],a['path']
run=root/'verification/runs'/receipt['receipt_id'];subject=read(run/'spread-browser-subject.json')
assert subject['changed_during_check']==[] and subject['owned_http_and_worker_retired'] and subject['child_exit_code']==0
for name,digest in subject['source_files'].items():assert sha((root/'data/dev025/src'/name).read_bytes())==digest,name
spec=importlib.util.spec_from_file_location('independent_presentation_reader',root/'data/dev025/src/backend/lab/presentation_audit.py');audit_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit_module)
authority=run/'original-browser-accounts';manifest=read(authority/'manifest.json');assert manifest['actual_ui_accounts']==3 and not manifest['financial_work_executed_by_capture']
for account in manifest['accounts']:
 for f in account['files']:
  p=run/f['path'];assert p.stat().st_size==f['bytes'] and sha(p.read_bytes())==f['sha256']
prices={'price','entry_price','split_adjusted_entry','exit_price','stop','target','entry_quantity','exit_quantity','quantity'}
def compare(a,b,path=''):
 if isinstance(b,dict):
  assert set(a)==set(b),path
  for k in b:compare(a[k],b[k],path+'/'+k)
 elif isinstance(b,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif isinstance(b,(Decimal,int,float)) and not isinstance(b,bool):
  assert not isinstance(a,bool) and math.isfinite(float(a)) and math.isfinite(float(b)),path
  assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal('1e-9' if path.rsplit('/',1)[-1] in prices else '1e-7'),path
 else:assert a==b,(path,a,b)
def cell(actual,value,key):
 if key=='failures':assert actual==';'.join(value)
 elif value is None:assert actual==''
 elif isinstance(value,bool):assert actual==str(value)
 elif isinstance(value,(float,int)):compare(float(actual),value,'/'+key)
 else:assert actual==str(value),(key,actual,value)
observations=[]
browser_accounts=sorted((run/'browser/artifacts').glob('spread-workflow-real-prima*/complete-account-result.json'))
assert len(browser_accounts)==3
for browser_result in browser_accounts:
 base=browser_result.parent;result=read(browser_result);child_id=result['job_id'];original=authority/child_id
 parent_inputs=read(original/'parent/inputs.json');inputs=read(original/'child/inputs.json');payload=inputs['payload'];parent=parent_inputs['payload']
 assert identity(payload)==inputs['payload_sha256']==result['payload_hash'] and identity(parent)==parent_inputs['payload_sha256']
 for role,original_inputs in [('parent',parent_inputs),('child',inputs)]:
  ui=read(base/(role+'-original-inputs.json'));assert ui==original_inputs and identity(ui['payload'])==ui['payload_sha256']
  events=read(original/role/'events.json');anchors=[e['details'] for e in events if e['kind']=='trial_plan_frozen']
  assert len(anchors)==1 and anchors[0]['payload_hash']==original_inputs['payload_sha256']
  saved=[e['details'] for e in events if e['kind']=='result_saved'];assert saved and saved[-1]['sha256']==sha((original/role/'artifacts/result.json.gz').read_bytes())
 root_raw=gzip.decompress((original/'child/artifacts/result.json.gz').read_bytes());assert json.loads(root_raw)==result
 selection=json.loads(gzip.decompress((original/'parent/artifacts/result.json.gz').read_bytes()))
 assert selection['account_phase']=='not_started' and selection['spread_selection']['complete']
 assert identity(selection['selection_manifest'])==selection['selection_manifest_hash']==payload['spread_parent']['selection_manifest_hash']
 assert payload['configurations']==selection['selection_manifest']['configurations']
 for field in ['dataset_id','dataset_manifest_hash','dataset_context','start','end','seed','costs','portfolio','statistics','minimum_trades','minimum_sharpe','news_calendar_id','news_calendar']:
  if field in parent:assert payload[field]==parent[field],field
 assert payload['evaluation_symbols']==[parent['primary_symbol']]==['SPY']
 parent_events=read(original/'parent/events.json');links=[e['details'] for e in parent_events if e['kind']=='spread_accounts_frozen']
 assert links==[dict(child_id=child_id,**payload['spread_parent'])]
 previous=None;probes=0
 for ordinal,event in enumerate(e for e in parent_events if e['kind']=='spread_protocol'):
  envelope=event['details'];body={k:v for k,v in envelope.items() if k!='event_sha256'}
  assert identity(body)==envelope['event_sha256'] and body['previous']==previous and body['sequence']==ordinal and body['payload_sha256']==parent_inputs['payload_sha256'];previous=envelope['event_sha256']
  value=body['event']
  if value['kind']=='probe_completed':
   probes+=1;evidence=value['evidence'];path=original/'parent/artifacts/spread-signals'/(evidence['evidence_sha256']+'.json.gz');raw=path.read_bytes()
   assert sha(raw)==body['artifact_sha256'];signals=json.loads(gzip.decompress(raw));assert identity(signals)==evidence['evidence_sha256']
   assert signals['signal_count']==evidence['signal_count'] and all(s['symbol']=='SPY' for s in signals['signals'])
 registry=read(original/'parent/registry.json');assert registry['totals']['computation_attempts']==probes and set(registry['totals']['roles'])=={'signal_probe'}
 part_paths=list((original/'child/artifacts/parts').glob('*.json.gz'));assert len(part_paths)==1
 part=json.loads(gzip.decompress(part_paths[0].read_bytes()));account=read(base/'complete-part-account.json')
 assert part['payload_hash']==inputs['payload_sha256'] and part['core_hash']==result['core_hash'] and part['config_id']==result['rows'][0]['config_id']
 assert account==part['report']
 part_digest=sha(part_paths[0].read_bytes());assert read(part_paths[0].with_suffix('.sha256.json'))['sha256']==part_digest
 for name in ['search_screen','search_statistics']:assert result[name]['accounts'][0]['source_part_sha256']==part_digest
 assert account['costs']==payload['costs'] and account['portfolio']==payload['portfolio'] and account['config']==payload['configurations'][0]
 assert identity(account['numerical_contract'])==account['core_hash']==result['core_hash'] and identity(account['config'])==account['config_id']
 assert result['rows'][0]['metrics']==account['metrics'] and account['metrics']['net_profit']<0
 screen=result['search_screen'];metrics=account['metrics'];flags=dict(signal_qualified=result['rows'][0]['signal_count']>=screen['settings']['minimum_signals'],enough_trades=metrics['trades']>=payload['minimum_trades'],profitable=metrics['net_profit']>0,sharpe_passed=metrics['marked_sharpe'] is not None and metrics['marked_sharpe']>=payload['minimum_sharpe'])
 assert screen['settings']==payload['sampling_policy'] and screen['settings']['mode']=='spread_selected'
 assert all(screen['accounts'][0][k]==v for k,v in flags.items()) and screen['accounts'][0]['initial_gates_passed']==all(flags.values())
 bars=read(original/'synthetic-primary-bars.json');assert {b['symbol'] for b in bars}=={'SPY'}
 reference=execute(bars,[s|dict(config_id=account['config_id']) for s in account['signals']],{account['config_id']:account['config']},account['costs'],account['portfolio'],[],account['start'],account['end'])
 compare({k:account[k] for k in ['trades','ledger','equity','rejected']},reference)
 counts={}
 for name in ['search-statistics','search-screen']:
  document=read(base/(name+'.json'));assert document==result[name.replace('-','_')]
  expected=[]
  for item in document['accounts']:
   expected.extend(({k:v for k,v in item.items() if k!='sensitivity'}|scenario for scenario in item['sensitivity']) if name=='search-statistics' else [item])
  rows=list(csv.DictReader(io.StringIO((base/(name+'.csv')).read_text(encoding='utf-8'))));assert len(rows)==len(expected)>0;counts[name]=len(rows)
  for actual,item in zip(rows,expected):
   for key,value in item.items():cell(actual[key],value,key)
   for key in ['job_id','dataset_id','core_hash','start','end']:assert actual[key]==str(result[key]),key
 rows=list(csv.DictReader(io.StringIO((base/'complete-trades.csv').read_text(encoding='utf-8'))));assert len(rows)==len(account['trades'])>0
 for actual,trade in zip(rows,account['trades']):
  for key,value in trade.items():cell(actual[key],value,key)
  assert actual['dataset_id']==account['dataset_id']
 html=(base/'spread-search-presentation.html').read_text(encoding='utf-8');deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',html,re.S).group(1))
 assert len(deck['sources'])==1;audit=audit_module.audit_deck({deck['sources'][0]['name']:root_raw},deck)
 observations.append(dict(viewport=base.name,child_id=child_id,parent_id=payload['spread_parent']['job_id'],qualification_probes=probes,trades=len(rows),ledger_rows=len(reference['ledger']),daily_marks=len(reference['equity']),csv_rows=counts,presentation=audit,loss_retained=True))
value=dict(scope=__doc__,browser_receipt=sys.argv[1],browser_receipt_sha256=sha(receipt_path.read_bytes()),accounts=observations,final_acceptance_certified=False)
(out/'spread-ui-independent-account-export-facts.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
