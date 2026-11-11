"""Separate saved-signal Decimal execution and source-fact audit of the browser's joint study.
Synthetic UI controls establish software behavior, not a financial edge or unseen market outcome.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import csv,hashlib,json,math,os,re,statistics,struct,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.config import canonical,identity
from backend.lab.research import core_hash,study_input_hash
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
browser=(root/sys.argv[1]).resolve();browser.relative_to(root);lab=Lab(root);records=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def close(a,b,tolerance='1e-7'):assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal(tolerance),(a,str(b))
for observation in sorted((browser/'artifacts').glob('*/portfolio-study-observations.json')):
 folder=observation.parent;observed=read(observation);study=lab.guard.study(observed['study_id']);spec=study['spec']
 assert study['status']=='final_complete' and spec['study_mode']=='portfolio'
 assert spec['reserved_final_job_id']==spec['final_job_id']==observed['final_job']
 assert [c['timeframe'] for c in spec['configurations']].count('1m')==1 and [c['timeframe'] for c in spec['configurations']].count('1h')==1
 assert len([e for e in observed['events'] if e['kind']=='final_unlock_consumed'])==len([e for e in observed['events'] if e['kind']=='portfolio_final_reserved'])==1
 manifest=read_manifest(lab.datasets_root,observed['dataset_id']);assert manifest['metadata']['input_kind']=='synthetic' and manifest['quality']['eligible']
 assert manifest['quality']['symbols']==sorted(observed['symbols']) and len(observed['symbols'])==20
 outcomes=[]
 for phase,job,window in [('discovery',observed['screen_job'],'discovery'),('validation',observed['screen_job'],'validation'),('final',observed['final_job'],'report')]:
  report=lab.report(job,0,window);download=read(folder/(window+'-account.json'));assert report==download
  expected_window=spec['holdout' if phase=='final' else phase];assert {'start':report['start'],'end':report['end']}==expected_window
  assert report['core_hash']==core_hash() and report['dataset_manifest_hash']==identity(manifest)
  assert report['study_context']['study_input_hash']==study_input_hash(spec) and report['study_context']['phase']==phase
  assert [c['config'] for c in report['configurations']]==spec['configurations'] and report['config_id']==report['study_context']['selection_unit_id']
  start=report['provenance']['warmup_start'];lab.guard.access(observed['symbols'],start,report['end'],'browser_joint_independent_reference',study['id'],observed['final_job'] if phase=='final' else None)
  prices,_=load_window(lab.datasets_root,report['dataset_id'],start,report['end']);actions=[Action(**a) for a in manifest['actions'] if start<=a['ex_date']<=report['end']];regular=prepare(prices,actions)
  expected=execute(primitive(regular),report['signals'],{c['config_id']:c['config'] for c in report['configurations']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end'])
  assert_parity(SimpleNamespace(**report),expected);assert expected['trades']
  capital=Decimal(str(report['portfolio']['capital']));equities=[capital,*[e['equity'] for e in expected['equity']]];daily=[b-a for a,b in zip(equities,equities[1:])];returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])]
  profits=[t['net_pnl'] for t in expected['trades']];high=capital;drawdown=Decimal(0)
  for value in equities:high=max(high,value);drawdown=max(drawdown,(high-value)/high)
  metrics=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits),marked_sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252) if statistics.stdev(returns)>0 else None,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
  for key,value in metrics.items():
   if value is None:assert report['metrics'][key] is None
   else:close(report['metrics'][key],value,'1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10')
  assert sum(a['trades'] for a in report['attribution'])==len(profits)
  close(sum(Decimal(str(a['closed_trade_net_profit'])) for a in report['attribution']),metrics['net_profit'])
  with (folder/(window+'-trades.csv')).open(encoding='utf-8',newline='') as f:csvrows=list(csv.DictReader(f))
  assert len(csvrows)==len(report['trades'])
  for a,b in zip(csvrows,report['trades']):assert a['id']==b['id'] and a['strategy_id']==b['strategy_id'];close(a['net_pnl'],b['net_pnl'])
  outcomes.append(dict(phase=phase,job=job,signals=len(report['signals']),trades=len(expected['trades']),ledger_events=len(expected['ledger']),sessions=len(expected['equity']),independent_metrics={k:None if v is None else str(v) for k,v in metrics.items()}))
 final=lab.report(observed['final_job'],0);document=(folder/'portfolio-study-presentation.html').read_text(encoding='utf-8');deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',document,re.S).group(1))
 assert len(deck['sources'])==1;audit=audit_deck({deck['sources'][0]['name']:canonical(final).encode()},deck)
 assert len(deck['pages'])==observed['pages']==len(observed['layouts']) and all(v==[] for v in observed['layouts'])
 assert observed['networkRequests']==observed['consoleErrors']==[]
 images=[]
 for i in range(len(deck['pages'])):
  p=folder/('portfolio-study-page-'+str(i+1)+'.png');raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',raw[16:24]);assert dict(width=w,height=h)==observed['viewport'];images.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
 records.append(dict(profile=folder.name,study_id=study['id'],accounts=outcomes,presenter_audit=audit,page_screenshots=images))
assert len(records)==2 and {r['profile'].split('-')[-1] for r in records}=={'desktop1920','desktop1280'}
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(output/'independent-browser-joint-studies.json').write_text(json.dumps(dict(scope=__doc__,profiles=records),indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=2,independent_complete_accounts=sum(len(r['accounts']) for r in records),page_screenshots=sum(len(r['page_screenshots']) for r in records),presenter_audits=[r['presenter_audit'] for r in records],scope=__doc__)))
