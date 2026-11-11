"""Rebuild a missing derived relationship only from intact frozen originals."""
import json,pytest,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from test_spread_api import client
from backend.lab.store import StateError
from backend.lab.worker import Worker

def test_missing_cache_repair_is_offline_idempotent_and_preserves_original_child(owned,monkeypatch):
 assert callable(getattr(owned[0],'repair_spread_account_link',None)),'Explicit original-account link repair is not implemented'
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once()
 with lab.store.db() as db:
  db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
 def forbidden(*a,**k):raise AssertionError('Relationship repair executed qualification or opened prices')
 monkeypatch.setattr('backend.lab.spread_accounts.parent',forbidden);monkeypatch.setattr('backend.lab.service.load_window',forbidden);monkeypatch.setattr(lab,'result',forbidden)
 for _ in range(2):
  saved=lab.repair_spread_account_link(parent['id']);assert saved['account_job']['id']==child['id'] and saved['account_job']['status']=='completed'
 with lab.store.db() as db:
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==1
  assert db.execute("SELECT COUNT(*) FROM events WHERE kind='spread_accounts_frozen' AND entity_id=?",(parent['id'],)).fetchone()[0]==1
  repairs=list(db.execute("SELECT details FROM events WHERE kind='spread_account_link_repaired' AND entity_id=?",(parent['id'],)))
  assert len(repairs)==1 and json.loads(repairs[0]['details'])['child_id']==child['id']

@pytest.mark.parametrize('fault',['event_missing','event_changed','event_duplicate','event_oversize','child_input','child_index','parent_input','result_event','result_list','conflicting_cache','no_continuation'])
def test_repair_cannot_invent_originals_replace_accounts_or_hide_corruption(owned,fault):
 assert callable(getattr(owned[0],'repair_spread_account_link',None)),'Explicit original-account link repair is not implemented'
 lab,parent,result=qualified(owned);child=None if fault=='no_continuation' else lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  if fault!='no_continuation':db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
  if fault=='event_missing':db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
  elif fault=='event_changed':db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
  elif fault=='event_oversize':db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='spread_accounts_frozen'",('x'*4097,parent['id']))
  elif fault=='result_list':db.execute("UPDATE events SET details='[]' WHERE entity_id=? AND kind='result_saved'",(parent['id'],))
  elif fault=='result_event':db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='result_saved'",(parent['id'],))
  elif fault=='event_duplicate':
   raw=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],)).fetchone()[0];lab.store.event('spread_accounts_frozen',parent['id'],json.loads(raw),db)
  elif fault in {'child_input','parent_input'}:db.execute("UPDATE jobs SET payload='{}' WHERE id=?",(child['id'] if fault=='child_input' else parent['id'],))
  elif fault=='child_index':db.execute('DELETE FROM job_input_index WHERE job_id=?',(child['id'],))
  elif fault=='conflicting_cache':db.execute('INSERT INTO spread_account_links VALUES(?,?)',(parent['id'],parent['id']))
 with pytest.raises(StateError):lab.repair_spread_account_link(parent['id'])
 with lab.store.db() as db:
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==(0 if child is None else 1)
  assert db.execute("SELECT COUNT(*) FROM events WHERE kind='spread_account_link_repaired'").fetchone()[0]==0

def test_repair_api_returns_only_original_child_without_accepting_override(owned):
 assert callable(getattr(owned[0],'repair_spread_account_link',None)),'Explicit original-account link repair is not implemented'
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
 with client(lab) as c:
  bad=c.post('/api/spreads/'+parent['id']+'/repair-account-link',json={'primary_symbol':'QQQ'});assert bad.status_code==422
  response=c.post('/api/spreads/'+parent['id']+'/repair-account-link',json={});assert response.status_code==200,response.text
  assert response.json()['account_job']['id']==child['id']

def test_dropped_cache_table_concurrent_repair_reuses_one_original_relationship(owned):
 assert callable(getattr(owned[0],'repair_spread_account_link',None)),'Explicit original-account link repair is not implemented'
 from concurrent.futures import ThreadPoolExecutor
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:db.execute('DROP TABLE spread_account_links')
 with ThreadPoolExecutor(max_workers=2) as pool:
  saved=list(pool.map(lambda _:lab.repair_spread_account_link(parent['id']),range(2)))
 assert [s['account_job']['id'] for s in saved]==[child['id'],child['id']]
 with lab.store.db() as db:
  assert db.execute("SELECT COUNT(*) FROM events WHERE kind='spread_account_link_repaired'").fetchone()[0]==1
