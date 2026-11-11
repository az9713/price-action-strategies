"""Prespecified fresh historical joint-study audit using actual production jobs.
Unseen means unviewed in recorded product history, not absence of general market knowledge.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
import hashlib,json,math,os,shutil,sqlite3,statistics,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.store import Store
from backend.lab.models import Study
from backend.lab.worker import Worker
from backend.lab.config import identity,canonical
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from backend.lab.presenter import build_deck,render_html
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
contract=json.loads((root/'verification/runs/portfolio-historical-study-contract.json').read_text(encoding='utf-8'))
main=Lab(root);dataset_id='01347b6ff897a8ff3dced036';manifest=read_manifest(main.datasets_root,dataset_id)
assert manifest['quality']['eligible'] and not manifest['metadata'].get('corporate_action_issues')
instance=root/'data/portfolio-historical-instance-v2';assert not instance.exists();store=Store(instance)
# Explicitly propagate exposure to the real product history as well as the audit
# store; a separate verification store cannot relabel these dates as unseen later.
main.guard.access(contract['symbols'],contract['acquisition']['start'],contract['study']['validation']['end'],'external_prespecified_portfolio_screening')
with main.store.db() as source,store.db() as target:
 for table in ['studies','viewed_windows','events']:
  fields=[r[1] for r in source.execute('PRAGMA table_info('+table+')')]
  target.executemany('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',source.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall())
lab=Lab(instance)
shutil.copytree(main.datasets_root/dataset_id,lab.datasets_root/dataset_id)
request=Study(**(contract['study']|dict(dataset_id=dataset_id)));study=lab.register_study(request);sid=study['id']
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(output/'registered-study.json').write_text(canonical(study),encoding='utf-8')
checks=[]
def reconcile(report,label):
 context=report['study_context'];phase='holdout' if context['phase']=='final' else context['phase'];window=study['spec'][phase]
 assert {'start':report['start'],'end':report['end']}==window
 assert [c['config'] for c in report['configurations']]==study['spec']['configurations']
 assert report['dataset_manifest_hash']==identity(manifest)
 lab.guard.access(contract['symbols'],report['provenance']['warmup_start'],report['end'],'independent_historical_joint_account',sid,lab.guard.study(sid)['spec'].get('final_job_id') if phase=='holdout' else None)
 prices,_=load_window(lab.datasets_root,dataset_id,report['provenance']['warmup_start'],report['end'])
 actions=[Action(**a) for a in manifest['actions'] if report['provenance']['warmup_start']<=a['ex_date']<=report['end']];regular=prepare(prices,actions)
 reference=execute(primitive(regular),report['signals'],{c['config_id']:c['config'] for c in report['configurations']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end'])
 assert_parity(SimpleNamespace(**report),reference)
 capital=Decimal(str(report['portfolio']['capital']));equities=[capital,*[r['equity'] for r in reference['equity']]];daily=[b-a for a,b in zip(equities,equities[1:])];returns=[float((b-a)/a) for a,b in zip(equities,equities[1:])]
 profits=[t['net_pnl'] for t in reference['trades']];high=capital;drawdown=Decimal(0)
 for value in equities:high=max(high,value);drawdown=max(drawdown,(high-value)/high)
 sharpe=statistics.mean(returns)/statistics.stdev(returns)*math.sqrt(252) if len(returns)>1 and statistics.stdev(returns)>0 else None
 metrics=dict(net_profit=equities[-1]-capital,total_return=equities[-1]/capital-1,max_drawdown=drawdown,trades=len(profits),win_rate=sum(v>0 for v in profits)/len(profits) if profits else None,marked_sharpe=sharpe,profit_without_ten_best_days=sum(daily)-sum(sorted(daily)[-min(10,len(daily)):]))
 for key,value in metrics.items():
  if value is None:assert report['metrics'][key] is None
  else:assert abs(Decimal(str(report['metrics'][key]))-Decimal(str(value)))<=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10'),key
 assert sum(r['trades'] for r in report['attribution'])==len(profits)
 assert abs(sum(Decimal(str(r['closed_trade_net_profit'])) for r in report['attribution'])-metrics['net_profit'])<=Decimal('1e-7')
 raw=canonical(report).encode();name=label+'.json';deck=build_deck([(name,raw)]);audit=audit_deck({name:raw},deck)
 (output/name).write_bytes(raw);(output/(label+'.html')).write_text(render_html(deck),encoding='utf-8')
 checks.append(dict(phase=context['phase'],signals=len(report['signals']),trades=len(profits),ledger_events=len(reference['ledger']),sessions=len(reference['equity']),metrics={k:None if v is None else str(v) for k,v in metrics.items()},presenter_audit=audit))
screen=lab.screen(sid);Worker(lab).run_once();assert lab.store.job(screen['id'])['status']=='completed',lab.store.job(screen['id'])['error']
for phase in ['discovery','validation']:reconcile(lab.report(screen['id'],0,phase),phase)
state=lab.guard.study(sid);final_id=None
if state['status']=='screened':
 # Conservative main-store exposure is recorded before any final job can read.
 window=state['spec']['holdout'];main.guard.access(contract['symbols'],window['start'],window['end'],'external_prespecified_portfolio_final_attempt')
 final=lab.final(sid);final_id=final['id'];Worker(lab).run_once();assert lab.store.job(final_id)['status']=='completed',lab.store.job(final_id)['error']
 reconcile(lab.report(final_id,0),'final');assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
else:
 assert state['status']=='no_candidates' and not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
result=dict(scope=__doc__,predeclared_contract_sha256=hashlib.sha256((root/'verification/runs/portfolio-historical-study-contract.json').read_bytes()).hexdigest(),dataset_id=dataset_id,dataset_manifest_hash=identity(manifest),study_id=sid,screen_job=screen['id'],final_job=final_id,status=lab.guard.study(sid)['status'],accounts=checks,exposure_propagated_to_main=True,final_dates_read=final_id is not None,limitations=manifest['metadata']['limitations'])
(output/'historical-joint-study-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
