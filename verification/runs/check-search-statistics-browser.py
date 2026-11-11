"""Reread every D038 browser account with independent Decimal accounting and stdlib DSR moments.
Supplied signals are the execution oracle's inputs; detector completeness and strategy edge are separate gates.
"""
from pathlib import Path
from decimal import Decimal
from statistics import mean,stdev
from types import SimpleNamespace
import csv,hashlib,json,math,os,re,struct,sys,xml.etree.ElementTree as ET
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import canonical,identity
from backend.lab.research import current_core_hash
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from verification.reference_statistics import dsr_from_moments
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
browser=(root/sys.argv[1]).resolve();browser.relative_to(root/'verification/runs');lab=Lab(root);out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def close(actual,expected,tolerance=1e-12):
 if expected is None:assert actual is None,(actual,expected)
 else:assert actual is not None and abs(actual-expected)<=tolerance,(actual,expected,tolerance)
suites=list(ET.parse(browser/'junit.xml').iter('testsuite'));assert sum(int(s.attrib['tests']) for s in suites)==2
assert not any(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
observations=sorted((browser/'artifacts').glob('*/statistics-observations.json'));assert len(observations)==2
records=[];pictures=[]
for observation in observations:
 folder=observation.parent;obs=read(observation);jid=obs['job_id'];saved=lab.result(jid);stats=saved['search_statistics'];assert saved==read(folder/'summary.json')
 assert saved['core_hash']==current_core_hash() and stats==read(folder/'statistics.json')
 assert stats['settings']==dict(effective_trials=[1,2,4],dispersion_mode='assumed',trial_sharpe_std=.25)
 assert stats['raw_configurations']==6 and stats['raw_generation']=={k:saved['sampling'][k] for k in ['attempts','unique','duplicates','rejected']}
 registry=read(folder/'trial-registry.json');assert registry['totals']['planned_occurrences']==6
 csvrows=list(csv.DictReader((folder/'statistics.csv').open(encoding='utf-8',newline='')));assert len(csvrows)==18
 html=(folder/'presentation.html').read_text(encoding='utf-8');match=re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',html,re.S);assert match
 deck=json.loads(match.group(1));assert len(deck['sources'])==1
 audit=audit_deck({jid+'/report.json':canonical(saved).encode()},deck);facts={tuple(v['path']):v for v in deck['facts'].values()}
 ndefined=nundefined=negative=trades=0;account_records=[]
 for i,(account,row) in enumerate(zip(stats['accounts'],saved['rows'])):
  report=lab.report(jid,i);assert report==read(folder/('account-'+str(i)+'.json'))
  assert account['source_part_sha256']==row['report_sha256'] and account['config_id']==report['config_id']
  assert row['metrics']==report['metrics'] and account['net_profit']==report['metrics']['net_profit']
  manifest=read_manifest(lab.datasets_root,report['dataset_id']);assert identity(manifest)==report['dataset_manifest_hash']
  warmup=report['provenance']['warmup_start'];lab.guard.access(manifest['quality']['symbols'],warmup,report['end'],'dsr_browser_independent_account_reread')
  frame,_=load_window(lab.datasets_root,report['dataset_id'],warmup,report['end']);actions=[Action(**a) for a in manifest['actions'] if warmup<=a['ex_date']<=report['end']]
  expected=execute(primitive(prepare(frame,actions)),[s|dict(config_id=report['config_id']) for s in report['signals']],{report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end'])
  assert_parity(SimpleNamespace(**report),expected)
  equities=[Decimal(str(report['portfolio']['capital'])),*[r['equity'] for r in expected['equity']]]
  independent_returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])];returns=report['metrics']['daily_returns']
  assert len(independent_returns)==len(returns)==account['observations']
  for a,b in zip(returns,independent_returns):close(a,b)
  profit=equities[-1]-equities[0];assert abs(Decimal(str(account['net_profit']))-profit)<=Decimal('1e-7')
  values=dict(daily_sharpe=None,skewness=None,raw_kurtosis=None);reason=None
  if len(returns)<4:reason='insufficient_observations'
  elif stdev(returns)==0:reason='zero_return_variance'
  else:
   n=len(returns);center=mean(returns);d=[x-center for x in returns];m2=sum(x*x for x in d)/n;m3=sum(x**3 for x in d)/n;m4=sum(x**4 for x in d)/n
   values=dict(daily_sharpe=center/stdev(returns),skewness=math.sqrt(n*(n-1))/(n-2)*m3/m2**1.5,raw_kurtosis=3+(n-1)/((n-2)*(n-3))*((n+1)*(m4/m2**2-3)+6))
  for k,v in values.items():close(account[k],v)
  for k in ['net_profit','observations','daily_sharpe','skewness','raw_kurtosis','source_part_sha256']:
   assert facts[('search_statistics','accounts',i,k)]['value']==account[k]
  for j,scenario in enumerate(account['sensitivity']):
   assert scenario['effective_trials']==[1,2,4][j]
   score=None if reason else dsr_from_moments(values['daily_sharpe'],len(returns),values['skewness'],values['raw_kurtosis'],scenario['effective_trials'],.25)
   close(scenario['score'],score);assert scenario['undefined_reason']==reason
   nundefined+=score is None;ndefined+=score is not None
   assert facts[('search_statistics','accounts',i,'sensitivity',j,'score')]['value']==scenario['score']
   csvrow=csvrows[i*3+j];expectedcsv={k:saved[k] for k in ['job_id','dataset_id','core_hash','start','end']}
   expectedcsv.update({k:stats[k] for k in ['trial_sharpe_std','raw_configurations','finite_sharpe_accounts']});expectedcsv['dispersion_mode']='assumed'
   expectedcsv.update({'generation_'+k:v for k,v in stats['raw_generation'].items()});expectedcsv.update({k:v for k,v in account.items() if k!='sensitivity'});expectedcsv.update(scenario)
   assert csvrow=={k:'' if v is None else str(v) for k,v in expectedcsv.items()}
  exported=list(csv.DictReader((folder/('account-'+str(i)+'.csv')).open(encoding='utf-8',newline='')));assert len(exported)==len(report['trades'])
  for r,t in zip(exported,report['trades']):
   for k in ['id','symbol','entry_at','exit_at']:assert r[k]==t[k]
   for k in ['entry_price','exit_price','entry_quantity','exit_quantity','net_pnl','fees','borrow','distributions']:assert abs(Decimal(r[k])-Decimal(str(t[k])))<=Decimal('1e-9' if k in ['entry_price','exit_price','entry_quantity','exit_quantity'] else '1e-7')
  trades+=len(report['trades']);negative+=account['net_profit']<0
  account_records.append(dict(part=i,config_id=account['config_id'],source_part_sha256=account['source_part_sha256'],net_profit=account['net_profit'],signals=len(report['signals']),trades=len(report['trades']),ledger_events=len(expected['ledger']),daily_marks=len(expected['equity']),daily_moments=values))
 assert trades>0 and ndefined>0 and len(account_records)==6
 assert obs['networkRequests']==obs['consoleErrors']==[] and len(obs['layouts'])==len(deck['pages']) and all(v==[] for v in obs['layouts'])
 for file in [folder/'search-statistics.png',*[folder/('presentation-'+str(n+1)+'.png') for n in range(len(deck['pages']))]]:
  raw=file.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';width,height=struct.unpack('>II',raw[16:24]);assert width==obs['viewport']['width'] and height>=obs['viewport']['height'];pictures.append(dict(path=file.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),width=width,height=height))
 records.append(dict(job_id=jid,viewport=obs['viewport'],accounts=account_records,pages=len(deck['pages']),facts_checked=audit['facts_checked'],defined_scores=ndefined,undefined_scores=nundefined,negative_accounts=negative))
value=dict(scope=__doc__,profiles=records,screenshots=pictures,complete_accounts=sum(len(p['accounts']) for p in records),core_hash=current_core_hash())
(out/'search-statistics-independent-audit.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(complete_accounts=value['complete_accounts'],profiles=len(records),screenshots=len(pictures),defined_scores=sum(p['defined_scores'] for p in records),undefined_scores=sum(p['undefined_scores'] for p in records),negative_accounts=sum(p['negative_accounts'] for p in records),scope=__doc__)))
