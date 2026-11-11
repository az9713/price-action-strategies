"""Two lost parent-side records must not authorize a second financial cohort."""
import sys,json,pytest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from backend.lab.store import StateError
from backend.lab.config import canonical

@pytest.mark.parametrize('boundary',['status','continue'])
def test_both_parent_side_relationship_records_lost_still_preserve_original_child(owned,boundary):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
  db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
 with pytest.raises(StateError):
  if boundary=='status':lab.spread_status(parent['id'])
  else:lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==1

@pytest.mark.parametrize('fault',['missing','wrong_definition'])
def test_reverse_reservation_index_must_exist_and_restart_rebuilds_it(owned,fault):
 from backend.lab.store import Store
 from test_spread_worker import job_and_worker
 lab,parent,_=job_and_worker(owned)
 with lab.store.db() as db:
  db.execute('DROP INDEX spread_child_parent_index')
  if fault=='wrong_definition':db.execute('CREATE INDEX spread_child_parent_index ON job_input_index(job_id)')
 with pytest.raises(StateError):lab.spread_status(parent['id'])
 if fault=='wrong_definition':
  with lab.store.db() as db:db.execute('DROP INDEX spread_child_parent_index')
 Store(lab.root)
 assert lab.spread_status(parent['id'])['account_job'] is None

def test_reverse_reservation_lookup_uses_its_index_without_reading_original_payloads(owned,monkeypatch):
 from contextlib import contextmanager
 import sqlite3
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:
  db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
  db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
 original=lab.store.db
 @contextmanager
 def guarded(*a,**k):
  with original(*a,**k) as db:
   db.set_authorizer(lambda action,table,column,*rest:sqlite3.SQLITE_DENY if action==sqlite3.SQLITE_READ and table=='jobs' and column=='payload' else sqlite3.SQLITE_OK)
   yield db
 monkeypatch.setattr(lab.store,'db',guarded)
 with pytest.raises(StateError,match='original account child'):lab.spread_status(parent['id'])
