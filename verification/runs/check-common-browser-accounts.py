"""Independent supplied-signal Decimal accounts, complete initial-gate CSVs and saved offline facts.
This audits the frozen accounts, not detector omissions, interval calibration, market edge or complete export-assumption coverage.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from collections import Counter
from itertools import product
import csv,hashlib,json,math,os,re,statistics,struct,sys,xml.etree.ElementTree as ET
import pandas as pd
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import identity
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
browser=(root/sys.argv[1]).resolve();browser.relative_to(root/'verification/runs');out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);lab=Lab(root)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def close(a,b,tolerance='1e-7'):
 if b is None:assert a is None
 else:assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal(tolerance),(a,str(b),tolerance)
suites=list(ET.parse(browser/'junit.xml').iter('testsuite'));assert sum(int(s.attrib['tests']) for s in suites)==2
assert not any(int(s.attrib.get(k,0)) for s in suites for k in ['errors','failures','skipped'])
observations=sorted((browser/'artifacts').glob('*/common-observations.json'));assert len(observations)==2
contexts={};profiles=[];images=[];complete=0
for observation in observations:
 folder=observation.parent;obs=read(observation);assert obs['networkRequests']==obs['consoleErrors']==[] and all(v['issues']==[] for v in obs['layouts'])
 records=[]
 for selected in obs['jobs']:
  jid=selected['id'];prefix=selected['prefix'];count=selected['count'];job=lab.store.job(jid);saved=lab.result(jid);screen=saved['search_screen']
  assert saved==read(folder/(prefix+'-summary.json')) and screen==read(folder/(prefix+'-screen.json'))
  assert len(saved['rows'])==len(screen['accounts'])==count and screen['settings']==job['payload']['sampling_policy']
  assert read(folder/(prefix+'-registry.json'))['totals']['planned_occurrences']==count
  proposals=job['payload']['sampling']['proposals'];accepted=[p for p in proposals if p['status']=='accepted']
  assert [p['config_id'] for p in accepted]==[r['config_id'] for r in saved['rows']]
  assert all(identity(p['configuration'])==p['config_id'] for p in proposals if p['status'] in ['accepted','duplicate'])
  if prefix=='grid':
   combinations={(c['config']['entry'],c['config']['confirmation'],c['config']['stop_reference'],c['config']['target'],c['config']['trend_filter'],c['config']['session_filter']) for c in saved['rows']}
   expected={(entry,'none',stop,target,trend,session) for entry,stop,target,(trend,session) in product(['next_open','limit'],['level','swing'],['1R','2R','3R','swing'],[('none','core'),('setup','core'),('none','open')])}
   assert combinations==expected and len(combinations)==48
  else:
   cardinalities=[]
   for row in saved['rows']:
    c=row['config'];cardinalities.append(sum([c['trend_filter']!='none',c['session_filter']!='core',c['news']!='trade',c['skip_run_days']!=0,c['skip_choppy'],c['fresh_breakout'],c['gap_confluence']]))
   assert Counter(cardinalities)=={0:3,1:2,2:1}
  html=(folder/(prefix+'-presentation.html')).read_text(encoding='utf-8');match=re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',html,re.S);assert match
  deck=json.loads(match.group(1));canonical=json.dumps(saved,sort_keys=True,separators=(',',':'),allow_nan=False).encode();audit=audit_deck({jid+'/report.json':canonical},deck)
  facts={tuple(f['path']):f['value'] for f in deck['facts'].values()};csvrows=list(csv.DictReader((folder/(prefix+'-screen.csv')).open(encoding='utf-8',newline='')));assert len(csvrows)==count
  counts=dict(generated=count,signal_qualified=0,enough_trades=0,profitable=0,sharpe_passed=0);accounts=[]
  for part,(row,account,csvrow) in enumerate(zip(saved['rows'],screen['accounts'],csvrows)):
   report=lab.report(jid,part);assert report==read(folder/(prefix+'-account-'+str(part)+'.json'))
   assert report['core_hash']==saved['core_hash'] and row['report_sha256']==account['source_part_sha256']
   for module in ['config','data','signals','engine','metrics','borrow','news','sampling']:
    name='backend/lab/'+module+'.py';assert report['numerical_contract']['source_files'][name]==hashlib.sha256((root/name).read_bytes()).hexdigest(),name
   manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert report['dataset_manifest_hash']==identity(manifest) and manifest['metadata']['input_kind']=='synthetic'
   warmup=report['provenance']['warmup_start'];key=(report['dataset_id'],warmup,report['end'])
   if key not in contexts:
    lab.guard.access(manifest['quality']['symbols'],warmup,report['end'],'common_browser_independent_reference')
    frame,_=load_window(lab.datasets_root,report['dataset_id'],warmup,report['end']);actions=[Action(**a) for a in manifest['actions'] if warmup<=a['ex_date']<=report['end']]
    contexts[key]=(primitive(prepare(frame,actions)),[a.__dict__ for a in actions])
   bars,actions=contexts[key]
   expected=execute([dict(b) for b in bars],[s|{'config_id':report['config_id']} for s in report['signals']],{report['config_id']:report['config']},report['costs'],report['portfolio'],actions,report['start'],report['end']);assert_parity(SimpleNamespace(**report),expected)
   equities=[Decimal(str(report['portfolio']['capital'])),*[r['equity'] for r in expected['equity']]];daily=[b-a for a,b in zip(equities,equities[1:])];returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])];profits=[t['net_pnl'] for t in expected['trades']];high=equities[0];drawdown=Decimal(0)
   for value in equities:high=max(high,value);drawdown=max(drawdown,(high-value)/high)
   positive=sum((p for p in profits if p>0),Decimal(0));loss=-sum((p for p in profits if p<0),Decimal(0))
   metrics=dict(net_profit=equities[-1]-equities[0],total_return=equities[-1]/equities[0]-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(p>0 for p in profits)/len(profits) if profits else None,profit_factor=positive/loss if loss else None,marked_sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252) if len(returns)>1 and statistics.stdev(returns)>0 else None,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
   for k,v in metrics.items():close(report['metrics'][k],v,'1e-7' if k in ['net_profit','profit_without_ten_best_days'] else '1e-10')
   for a,b in zip(report['metrics']['daily_returns'],returns):close(a,b,'1e-12')
   signal_count=sum(report['start']<=pd.Timestamp(s['available_at']).tz_convert('America/New_York').date().isoformat()<=report['end'] for s in report['signals'])
   assert account['signal_count']==row['signal_count']==signal_count and account['trades']==len(profits)
   gates=[signal_count>=screen['settings']['minimum_signals'],len(profits)>=screen['settings']['minimum_trades'],metrics['net_profit']>0,metrics['marked_sharpe'] is not None and metrics['marked_sharpe']>=screen['settings']['minimum_sharpe']]
   assert [account[k] for k in list(counts)[1:]]==gates and account['initial_gates_passed']==all(gates)
   for n,k in enumerate(list(counts)[1:]):counts[k]+=all(gates[:n+1])
   for k,v in account.items():assert csvrow[k]==('' if v is None else ';'.join(v) if k=='failures' else str(v)),(jid,part,k)
   for k in ['job_id','dataset_id','core_hash','start','end']:assert csvrow[k]==str(saved[k])
   trades=list(csv.DictReader((folder/(prefix+'-account-'+str(part)+'.csv')).open(encoding='utf-8',newline='')));assert len(trades)==len(report['trades'])
   for observed,trade in zip(trades,report['trades']):
    for k in ['id','symbol','entry_at','exit_at']:assert observed[k]==trade[k]
    for k in ['entry_price','exit_price','entry_quantity','exit_quantity','net_pnl','fees','borrow','distributions']:close(observed[k],trade[k],'1e-9' if k in ['entry_price','exit_price','entry_quantity','exit_quantity'] else '1e-7')
   accounts.append(dict(part=part,config_id=report['config_id'],signal_count=signal_count,trades=len(profits),ledger_events=len(expected['ledger']),daily_marks=len(expected['equity']),net_profit=str(metrics['net_profit'])));complete+=1
  assert counts==screen['counts'] and screen['groups'][0]['counts']==counts
  for k,v in counts.items():assert facts[('search_screen','counts',k)]==v and facts[('search_screen','groups',0,'counts',k)]==v
  for k in ['minimum_signals','minimum_trades','minimum_sharpe']:assert facts[('search_screen','settings',k)]==screen['settings'][k]
  for later,v in screen['later_stages'].items():assert v=='not_run' and facts[('search_screen','later_stages',later)]==v
  assert selected['pages']==len(deck['pages']);records.append(dict(job_id=jid,prefix=prefix,counts=counts,accounts=accounts,pages=len(deck['pages']),facts_checked=audit['facts_checked']))
  for file in [folder/(prefix+'-outcomes.png'),*[folder/(prefix+'-page-'+str(n+1)+'.png') for n in range(len(deck['pages']))]]:
   raw=file.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',raw[16:24]);assert w==obs['viewport']['width'] and h>=obs['viewport']['height'];images.append(dict(path=file.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),width=w,height=h))
 profiles.append(dict(profile=folder.name,viewport=obs['viewport'],jobs=records))
assert complete==108
value=dict(scope=__doc__,complete_accounts=complete,profiles=profiles,screenshots=images)
(out/'common-browser-independent-accounts.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(complete_accounts=complete,profiles=len(profiles),screenshots=len(images),scope=__doc__)))
