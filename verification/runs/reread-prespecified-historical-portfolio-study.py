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
dataset_id='01347b6ff897a8ff3dced036'
lab=Lab(root/'data/portfolio-historical-instance-v2');manifest=read_manifest(lab.datasets_root,dataset_id)
study=lab.guard.study('49cfe3c7cffb47419164e2af6dfa3904');sid=study['id']
assert study['status']=='no_candidates' and study['spec']['core_hash']==__import__('backend.lab.research',fromlist=['core_hash']).core_hash()
assert manifest['metadata']['feed']=='sip' and manifest['quality']['eligible']
output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
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
screen_id='289877d716c24bca957bdd10334ee1e8'
assert lab.store.job(screen_id)['status']=='completed'
for phase in ['discovery','validation']:reconcile(lab.report(screen_id,0,phase),phase)
assert lab.result(screen_id)['candidates']==[] and not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
main=Lab(root)
with main.store.db() as db:
 for symbol in contract['symbols']:
  assert db.execute('SELECT 1 FROM viewed_windows WHERE symbol=? AND start<=? AND end>=?',(symbol,contract['acquisition']['start'],contract['study']['validation']['end'])).fetchone()
value=dict(scope='Independent current-source reread of the prespecified historical joint accounts. No new strategy selection, final account, or market-data certification.',study_id=sid,dataset_id=dataset_id,status='no_candidates',screen_job=screen_id,accounts=checks,final_account_evaluated=False,exposure_present_in_main=True,acquisition_note='Full-period warehouse acquisition/quality checks preceded registration; no final-window account analysis or final unlock occurred.')
(output/'historical-current-reread.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
