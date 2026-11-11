"""Original empty status and interrupted/duplicate staged metadata transactions."""
import pytest
from test_spread_journal import owned,start_probe
from backend.lab.store import StateError
from backend.lab.spread_jobs import SpreadJournal,bounded_status,staged_freeze

def test_valid_empty_status_interrupted_batch_and_duplicate_trial_are_distinct(tmp_path):
 store,job,journal=owned(tmp_path,SpreadJournal)
 saved=bounded_status(store,job['id']);assert saved['spread']['event_count']==0 and saved['spread']['head_sha256'] is None and saved['account_job'] is None
 coordinate=start_probe(journal,job);before=store.events(job['id']);original=next(e for e in before if e['kind']=='trial_plan_frozen')
 event=dict(kind='batch_finished',family='break_of_structure',batch=0,selected_ordinal=None,outcomes=[dict(ordinal=0,config_id='a'*64,status='not_probed'),dict(ordinal=1,config_id=coordinate['config_id'],status='not_probed')])
 with pytest.raises(StateError,match='interrupted signal probe'):journal.append(event)
 assert store.events(job['id'])==before and journal.load()[-1]['kind']=='probe_started'
 with store.db() as db:
  db.execute('BEGIN IMMEDIATE');store._trials.owned(db,job['id'],'owner')
  with pytest.raises(StateError,match='already registered'):staged_freeze(store,db,job,journal.binding,'d'*64,journal.settings,dict(kind='probe_planned',**coordinate))
  db.execute('ROLLBACK')
 assert store.events(job['id'])==before
 registry=store.registry(job_id=job['id']);assert registry['totals']['planned_occurrences']==1 and registry['totals']['computation_attempts']==1
 assert next(e for e in store.events(job['id']) if e['kind']=='trial_plan_frozen')==original
