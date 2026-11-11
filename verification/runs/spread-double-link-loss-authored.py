"""Two lost parent-side records must not authorize a second financial cohort."""
import sys,json,pytest
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_account_handoff import qualified
from backend.lab.store import StateError

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
