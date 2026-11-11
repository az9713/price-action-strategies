"""Financial continuation faults, original-child authority and actual part recovery."""
from pathlib import Path
import json
import pytest
from backend.lab.config import identity
from backend.lab.store import StateError
from backend.lab.worker import Worker
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from test_spread_api import client

@pytest.mark.parametrize('fault',['signal','proposal','root','journal','price_bytes'])
def test_parent_corruption_after_child_queue_prevents_any_financial_attempt(owned,monkeypatch,fault):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);folder=lab.output_path(parent['id']).parent
 if fault=='signal':next((folder/'spread-signals').glob('*.gz')).write_bytes(b'changed original signal')
 elif fault=='proposal':next((folder/'spread-proposals').glob('*.gz')).write_bytes(b'changed original proposal')
 elif fault=='root':(folder/'result.json.gz').write_bytes(b'changed original root')
 elif fault=='price_bytes':
  p=lab.datasets_root/parent['payload']['dataset_id']/'minutes.parquet';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
 else:
  with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_protocol' AND id=(SELECT MAX(id) FROM events WHERE entity_id=? AND kind='spread_protocol')",(parent['id'],parent['id']))
 def forbidden(*a,**k):raise AssertionError('Corrupt parent reached account P&L')
 monkeypatch.setattr('backend.lab.service.simulate',forbidden);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='failed' and not lab.output_path(child['id']).exists()
 assert lab.store.registry(job_id=child['id'])['totals']['computation_attempts']==0

def test_failed_child_freeze_rolls_back_job_trials_and_continuation_link(owned,monkeypatch):
 lab,parent,result=qualified(owned);original=lab.store._input_index.add
 def fail(db,jid,payload,*a,**k):
  if 'spread_parent' in payload:raise StateError('Owned failure after trial freeze before link publication')
  return original(db,jid,payload,*a,**k)
 monkeypatch.setattr(lab.store._input_index,'add',fail)
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0
  assert db.execute('SELECT COUNT(*) FROM spread_account_links').fetchone()[0]==0
  assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE role='strategy'").fetchone()[0]==0
 monkeypatch.setattr(lab.store._input_index,'add',original);assert lab.create_spread_accounts(parent['id'])['status']=='queued'

def test_parent_changed_after_pnl_blocks_publication_then_reuses_exact_committed_part(owned,monkeypatch):
 from backend.lab import service
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);path=next((lab.output_path(parent['id']).parent/'spread-signals').glob('*.gz'));original_bytes=path.read_bytes();simulate=service.simulate;calls=[]
 def changed(*a,**k):
  account=simulate(*a,**k);calls.append(True);path.write_bytes(b'changed after actual P&L');return account
 monkeypatch.setattr(service,'simulate',changed);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='failed' and not lab.output_path(child['id']).exists() and calls==[True]
 part=lab.output_path(child['id']).parent/'parts/000000.json.gz';committed=part.read_bytes();path.write_bytes(original_bytes)
 def forbidden(*a,**k):raise AssertionError('Restart recomputed a committed complete financial account')
 monkeypatch.setattr(service,'simulate',forbidden);lab.store.resume(child['id']);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='completed',lab.store.job(child['id'])['error']
 assert part.read_bytes()==committed and lab.store.registry(job_id=child['id'])['totals']['computation_attempts']==1
 assert lab.store.registry(job_id=child['id'])['rows'][0]['reuses']>=1

def test_saved_child_report_does_not_reopen_source_prices_or_parent_artifacts(owned,monkeypatch):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once();report=lab.report(child['id'],0)
 def forbidden(*a,**k):raise AssertionError('Saved viewing reopened raw prices/qualification')
 monkeypatch.setattr('backend.lab.service.load_window',forbidden);monkeypatch.setattr(lab,'spread_signal_probe',forbidden)
 (lab.output_path(parent['id']).parent/'result.json.gz').write_bytes(b'parent unavailable for saved viewing')
 assert lab.report(child['id'],0)==report

@pytest.mark.parametrize('fault',['missing_event','changed_event','changed_link'])
def test_repeated_continuation_must_preserve_its_original_atomic_link(owned,fault):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  if fault=='missing_event':db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
  elif fault=='changed_event':db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
  else:db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==1

def test_actual_continuation_api_returns_original_child_and_complete_saved_account(owned):
 lab,parent,result=qualified(owned)
 with client(lab) as c:
  first=c.post('/api/spreads/'+parent['id']+'/accounts',json={});assert first.status_code==202,first.text
  child=first.json();second=c.post('/api/spreads/'+parent['id']+'/accounts',json={});assert second.status_code==202 and second.json()['id']==child['id']
  assert Worker(lab).run_once();response=c.get('/api/jobs/'+child['id']+'/result');assert response.status_code==200,response.text
  assert response.json()['spread_parent']['job_id']==parent['id'] and len(response.json()['rows'])==1

@pytest.mark.parametrize('replacement',[{'costs':{'borrow_annual':0}},{'configurations':[]},{'start':'2026-01-01'},{'minimum_sharpe':0}])
def test_api_accepts_no_override_between_qualification_and_accounts(owned,replacement):
 lab,parent,result=qualified(owned)
 with client(lab) as c:assert c.post('/api/spreads/'+parent['id']+'/accounts',json=replacement).status_code==422
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0
