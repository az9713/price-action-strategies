"""Actual complete-parent continuation contract; staged here before development edits."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import gzip,hashlib,json,sys,os,shutil
import pytest
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_worker import job_and_worker
from backend.lab.worker import Worker
from backend.lab.store import StateError
from backend.lab.config import identity

def qualified(owned,**updates):
 lab,parent,worker=job_and_worker(owned,**updates);assert worker.run_once()
 assert lab.store.job(parent['id'])['status']=='completed'
 return lab,parent,lab.result(parent['id'])

def test_complete_parent_freezes_all_selected_financial_trials_and_original_assumptions_before_pnl(owned,monkeypatch):
 lab,parent,selection=qualified(owned,costs=dict(borrow_annual=.17,spread_bps=2.5),portfolio=dict(capital=123456),minimum_trades=31,minimum_sharpe=.7)
 original=parent['payload'];child=lab.create_spread_accounts(parent['id']);p=child['payload']
 assert child['kind']=='spread_accounts' and child['status']=='queued'
 for key in ['dataset_id','dataset_manifest_hash','dataset_context','start','end','seed','costs','portfolio','statistics','minimum_trades','minimum_sharpe']:
  assert p[key]==original[key],key
 assert p['evaluation_symbols']==[original['primary_symbol']]
 assert p['configurations']==selection['selection_manifest']['configurations']
 assert p['spread_parent']['job_id']==parent['id'] and p['spread_parent']['payload_hash']==identity(original)
 assert p['spread_parent']['selection_manifest_hash']==selection['selection_manifest_hash']
 registry=lab.store.registry(job_id=child['id']);assert registry['totals']['planned_occurrences']==len(p['configurations']) and registry['totals']['computation_attempts']==0
 assert set(registry['totals']['roles'])=={'strategy'}
 from backend.lab import service
 simulate=service.simulate;calls=[]
 def observed(frame,*a,**k):
  assert set(frame.symbol)=={'SPY'}
  assert lab.store.registry(job_id=child['id'])['totals']['planned_occurrences']==len(p['configurations'])
  calls.append(True);return simulate(frame,*a,**k)
 monkeypatch.setattr(service,'simulate',observed);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='completed',lab.store.job(child['id'])['error']
 result=lab.result(child['id']);assert len(result['rows'])==len(p['configurations']) and len(calls)==len(p['configurations'])
 assert result['spread_parent']==p['spread_parent'] and result['selection_warning']
 assert result['search_statistics']['raw_configurations']==len(p['configurations'])
 for row in result['rows']:
  report=lab.report(child['id'],row['part']);assert report['costs']==original['costs'] and report['portfolio']==original['portfolio']
  assert set(report['charts'])=={'SPY'} and report['dataset_context']['symbols']==['QQQ','SPY'] and report['signal_scope']['symbols']==['SPY']
 assert lab.store.registry(job_id=parent['id'])['totals']['computation_attempts']==9
 if os.environ.get('PA_EVIDENCE_RUN_DIR'):
  destination=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-spread-account-handoff';destination.mkdir()
  from test_reference_execution import primitive
  _,regular,_,_=lab._evaluation_input(original['dataset_id'],original['start'],original['end'],expected_manifest=original['dataset_manifest_hash'],symbols=['SPY'])
  (destination/'synthetic-primary-bars.json').write_text(json.dumps(primitive(regular)),encoding='utf-8')
  for role,item in [('parent',parent),('child',child)]:
   base=destination/role;base.mkdir()
   for name,value in [('inputs',lab.store.job_inputs(item['id'])),('registry',lab.store.registry(job_id=item['id'])),('events',lab.store.events(item['id']))]:
    (base/(name+'.json')).write_text(json.dumps(value,indent=2),encoding='utf-8')
   folder=lab.output_path(item['id']).parent
   for p in folder.rglob('*'):
    if not p.is_file():continue
    relative=p.relative_to(folder)
    allowed={'result.json.gz','spread-proposals','spread-preparation','spread-signals'} if role=='parent' else {'result.json.gz','parts'}
    if relative.parts[0] not in allowed:continue
    assert not p.is_symlink();q=base/'artifacts'/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)

@pytest.mark.parametrize('fault',['queued','exhausted','root','signal','proposal','journal'])
def test_unqualified_or_corrupt_parent_creates_zero_financial_trials(owned,fault):
 if fault=='queued':lab,parent,worker=job_and_worker(owned)
 else:
  updates=dict(primary_symbol='QQQ',settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=2,max_batches_per_family=1)) if fault=='exhausted' else {}
  lab,parent,result=qualified(owned,**updates)
  folder=lab.output_path(parent['id']).parent
  if fault=='root':p=folder/'result.json.gz';p.write_bytes(b'changed root')
  elif fault=='signal':p=next((folder/'spread-signals').glob('*.gz'));p.write_bytes(b'changed committed signal')
  elif fault=='proposal':p=next((folder/'spread-proposals').glob('*.gz'));p.write_bytes(b'changed original proposal')
  elif fault=='journal':
   with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_protocol' AND id=(SELECT MAX(id) FROM events WHERE entity_id=? AND kind='spread_protocol')",(parent['id'],parent['id']))
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0

def test_repeated_and_concurrent_continuations_return_the_one_original_child(owned):
 lab,parent,result=qualified(owned)
 with ThreadPoolExecutor(max_workers=2) as pool:children=list(pool.map(lambda _:lab.create_spread_accounts(parent['id']),range(2)))
 assert children[0]['id']==children[1]['id']==lab.create_spread_accounts(parent['id'])['id']
 assert len([e for e in lab.store.events(children[0]['id']) if e['kind']=='trial_plan_frozen'])==1
 lab.store.cancel(children[0]['id']);assert lab.create_spread_accounts(parent['id'])['id']==children[0]['id']

def test_secondary_protected_dates_remain_unread_during_selected_accounts(owned):
 from backend.lab.data import load_dataset,save_dataset
 from backend.lab.models import Study
 lab,m,context,cfg=owned;raw,_=load_dataset(lab.datasets_root,m['id'])
 secondary=save_dataset(lab.datasets_root,raw.loc[raw.symbol=='QQQ'],dict(input_kind='synthetic',source='Owned separate secondary'),start='2026-10-05',end='2026-10-30')
 lab.register_study(Study(name='Untouched secondary final',dataset_id=secondary['id'],discovery=dict(start='2026-10-05',end='2026-10-09'),validation=dict(start='2026-10-12',end='2026-10-16'),holdout=dict(start='2026-10-19',end='2026-10-30'),configurations=[cfg],minimum_trades=1))
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='completed',lab.store.job(child['id'])['error']
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM viewed_windows WHERE symbol='QQQ'").fetchone()[0]==0
