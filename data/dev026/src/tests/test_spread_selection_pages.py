"""Staged next-step contracts: not executed until copied into development tests.

Original-envelope pages certify requested saved facts, not a full journal prefix.
Actual account continuation retains its separate complete-original verification.
"""
from contextlib import contextmanager
from pathlib import Path
import json,sqlite3,sys
import pytest
sys.path.insert(0,str(Path.cwd()/'tests'))
from backend.lab.config import identity,canonical
from backend.lab.store import StateError
from backend.lab.worker import Worker
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from test_spread_api import client

def test_actual_saved_selection_page_is_complete_and_never_opens_prices_or_root(owned,monkeypatch):
 lab,parent,result=qualified(owned)
 def forbidden(*a,**k):raise AssertionError('A selection page opened raw prices or a complete root')
 monkeypatch.setattr(lab,'result',forbidden);monkeypatch.setattr('backend.lab.service.load_window',forbidden)
 page=lab.spread_selections(parent['id'],after=0,limit=1)
 assert page['selected_count']==1 and len(page['versions'])==1 and not page['has_more']
 row=page['versions'][0];assert row['configuration']==result['selection_manifest']['configurations'][0] and row['config_id']==identity(row['configuration']) and row['signal_count']>=40
 assert page['next_after']==row['event_id']>0 and len(canonical(page).encode())<=2*1024*1024
 last=lab.spread_selections(parent['id'],after=page['next_after'],limit=1);assert last['versions']==[] and not last['has_more'] and last['selected_count']==1

def test_selection_pages_do_not_read_raw_inputs_or_unrelated_large_journal_bodies(owned,monkeypatch):
 lab,parent,result=qualified(owned)
 with lab.store.db() as db:
  row=next(r for r in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_protocol'",(parent['id'],)) if json.loads(r['details'])['event']['kind']=='batch_finished')
  db.execute('UPDATE events SET details=? WHERE id=?',('x'*2*1024*1024,row['id']))
 original=lab.store.db
 @contextmanager
 def guarded(*a,**k):
  with original(*a,**k) as db:
   def authorizer(action,table,column,*rest):
    if action==sqlite3.SQLITE_READ and table=='jobs' and column=='payload':return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK
   db.set_authorizer(authorizer);yield db
 monkeypatch.setattr(lab.store,'db',guarded)
 page=lab.spread_selections(parent['id']);assert len(page['versions'])==1
 assert 'prefix' in page['integrity_scope'].lower()

@pytest.mark.parametrize('fault',['raw','envelope','configuration','deleted_selected'])
def test_changed_or_missing_selected_original_never_becomes_a_plausible_empty_page(owned,fault):
 lab,parent,result=qualified(owned)
 with lab.store.db() as db:
  row=next(r for r in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='spread_protocol'",(parent['id'],)) if json.loads(r['details'])['event']['kind']=='version_selected')
  value=json.loads(row['details'])
  if fault=='deleted_selected':db.execute('DELETE FROM events WHERE id=?',(row['id'],))
  else:
   if fault=='raw':raw='{'
   else:
    if fault=='envelope':value['owner']='changed owner'
    else:
     cfg=value['event']['configuration'];cfg['target']='1R' if cfg['target']!='1R' else '5R'
     value['event_sha256']=identity({k:v for k,v in value.items() if k!='event_sha256'})
    raw=canonical(value)
   db.execute('UPDATE events SET details=? WHERE id=?',(raw,row['id']))
 with pytest.raises(StateError):lab.spread_selections(parent['id'])

def test_selection_page_has_a_real_partial_seek_index_and_rejects_its_loss(owned):
 lab,parent,result=qualified(owned)
 with lab.store.db() as db:
  indexes={r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index'")};assert 'spread_selected_events' in indexes
  db.execute('DROP INDEX spread_selected_events')
 with pytest.raises(StateError):lab.spread_selections(parent['id'])

def test_selection_page_api_rejects_unbounded_requests(owned):
 lab,parent,result=qualified(owned)
 with client(lab) as c:
  response=c.get('/api/spreads/'+parent['id']+'/selections');assert response.status_code==200 and len(response.json()['versions'])==1
  for params in [dict(limit=0),dict(limit=101),dict(after=-1)]:assert c.get('/api/spreads/'+parent['id']+'/selections',params=params).status_code==422

def test_saved_parent_status_exposes_original_child_without_reverifying_prices(owned,monkeypatch):
 lab,parent,result=qualified(owned);assert lab.spread_status(parent['id'])['account_job'] is None
 child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once()
 def forbidden(*a,**k):raise AssertionError('Saved account-link status reran original price verification')
 monkeypatch.setattr(lab,'result',forbidden);monkeypatch.setattr('backend.lab.spread_accounts.parent',forbidden);monkeypatch.setattr('backend.lab.service.load_window',forbidden)
 saved=lab.spread_status(parent['id']);assert saved['account_job']['id']==child['id'] and saved['account_job']['status']=='completed' and len(canonical(saved).encode())<=65536

@pytest.mark.parametrize('fault',['cache','original'])
def test_parent_child_metadata_corruption_is_visible_and_cannot_offer_a_replacement(owned,fault):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  if fault=='cache':db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
  else:db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
 with pytest.raises(StateError):lab.spread_status(parent['id'])
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==1
