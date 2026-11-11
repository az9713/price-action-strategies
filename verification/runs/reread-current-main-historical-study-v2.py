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
import urllib.request,urllib.error,time
replay=json.loads((root/'verification/runs/runtime-historical-replay-contract-v2.json').read_text(encoding='utf-8'))
original=root/'verification/runs/portfolio-historical-study-contract.json';assert hashlib.sha256(original.read_bytes()).hexdigest()==replay['original_contract_sha256']
contract=json.loads(original.read_text(encoding='utf-8'));lab=Lab(root);dataset_id=replay['dataset_id'];manifest=read_manifest(lab.datasets_root,dataset_id)
assert manifest['quality']['eligible'] and not manifest['metadata'].get('corporate_action_issues')
base='http://127.0.0.1:8767'
with urllib.request.urlopen(base+'/api/session',timeout=10) as response:token=json.load(response)['token']
def api(path,value=None):
 data=None if value is None else json.dumps(value).encode()
 req=urllib.request.Request(base+'/api'+path,data=data,headers={'Origin':base,'X-Lab-Token':token,'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as response:return json.load(response)
health=api('/health');assert health['source_current'] and health['worker_ready'] and health['store_lease_held']
study=next(s for s in api('/studies') if s['id']==replay['current_study_id']);sid=study['id'];lab.guard.verify_inputs(study);output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);checks=[]
(output/'registered-study.json').write_text(canonical(study),encoding='utf-8')
try:
 api('/datasets/'+dataset_id+'/preview?symbol=SPY&start='+study['spec']['holdout']['start']+'&end='+study['spec']['holdout']['end'])
 raise AssertionError('Protected final preview unexpectedly succeeded')
except urllib.error.HTTPError as exc:assert exc.code==409

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
screen=api('/jobs/'+replay['current_screen_job_id']);assert screen['payload']['study_id']==sid;deadline=time.monotonic()+replay['poll_budget_seconds']
while True:
 state=api('/jobs/'+screen['id'])
 if state['status'] in {'completed','failed','canceled'}:break
 assert time.monotonic()<deadline,('Actual main screening still running',screen['id']);time.sleep(.5)
assert state['status']=='completed',state
prior=Lab(root/replay['baseline_store']);equal=[]
for phase in ['discovery','validation']:
 report=api('/jobs/'+screen['id']+'/report?part=0&window='+phase);assert report['study_context']['study_id']==sid and report['core_hash']==health['core_hash'];reconcile(report,phase)
 before=prior.report(replay['baseline_screen_job_id'],0,phase)
 assert {k:v for k,v in before.items() if k not in replay['allowed_report_differences']}=={k:v for k,v in report.items() if k not in replay['allowed_report_differences']},phase
 assert all(before['study_context'][k]==report['study_context'][k] for k in replay['study_context_required_equal'])
 equal.append(phase)
current=next(s for s in api('/studies') if s['id']==sid);assert current['status']==replay['expected_state'] and not current['spec'].get('final_job_id')
try:api('/studies/'+sid+'/final',{});raise AssertionError('No-candidate final unexpectedly queued')
except urllib.error.HTTPError as exc:assert exc.code==409
assert not any(e['kind']=='final_unlock_consumed' for e in lab.store.events(sid))
value=dict(scope=replay['scope'],study_id=sid,screen_job_id=screen['id'],state=current['status'],final_job_id=None,final_unlocks=0,complete_old_new_accounts_equal=equal,source_hash=health['core_hash'],accounts=checks)
(output/'historical-current-main-replay.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
