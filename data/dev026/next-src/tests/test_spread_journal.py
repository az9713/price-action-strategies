"""Actual owned SQLite journal: atomic head, original binding and staged attempts."""
from copy import deepcopy
import pytest
from backend.lab.store import Store,StateError
from backend.lab.config import Strategy,identity
from backend.lab.research import core_hash

@pytest.fixture
def journal_class():
    from backend.lab.spread_jobs import SpreadJournal
    return SpreadJournal

def owned(tmp_path,module):
    store=Store(tmp_path);payload=dict(core_hash=core_hash(),name='Owned staged spread',settings={'families':['break_of_structure'],'per_family':1,'batch_size':2,'max_batches_per_family':1},context=dict(dataset_id='a'*24,dataset_manifest_hash='b'*64,primary_symbol='SPY',start='2026-11-02',end='2026-11-06'))
    job=store.create_job('spread',payload);claimed=store.claim('owner');assert claimed['id']==job['id']
    return store,claimed,module(store,claimed,'owner')

def batch_record():return dict(contract_hash='c'*64,core_hash=core_hash(),family='break_of_structure',batch=0,relative_path='break_of_structure/000000.json.gz',bytes=20,sha256='e'*64,proposal_count=2,configurations_hash='f'*64)

def start_probe(journal,job):
    journal.append(dict(kind='preparation_started',contract_hash='c'*64));journal.append(dict(kind='preparation_batch',record=batch_record()));journal.append(dict(kind='preparation_sealed',plan_id='d'*64))
    journal.append(dict(kind='selection_started',plan_id='d'*64,context=job['payload']['context']))
    journal.append(dict(kind='batch_started',family='break_of_structure',batch=0,configuration_hash='f'*64))
    coordinate=dict(family='break_of_structure',batch=0,ordinal=1,config_id=identity(Strategy(family='break_of_structure')))
    journal.append(dict(kind='probe_planned',**coordinate));journal.append(dict(kind='probe_started',**coordinate,attempt=1));return coordinate

def test_empty_spread_has_zero_financial_occurrences_and_an_original_frozen_plan(tmp_path,journal_class):
    store,job,journal=owned(tmp_path,journal_class)
    assert store.registry(job_id=job['id'])['totals']['planned_occurrences']==0
    assert journal.load()==[] and journal.status()['event_count']==0
    store.verify_trial_plan(job['id'])
    assert len([e for e in store.events(job['id']) if e['kind']=='trial_plan_frozen'])==1

def test_journal_head_and_event_commit_are_one_owned_transaction(tmp_path,journal_class):
    store,job,journal=owned(tmp_path,journal_class);event=dict(kind='preparation_started',contract_hash='c'*64)
    journal.append(event);assert journal.load()==[event] and journal.status()['event_count']==1
    before=store.events(job['id'])
    with pytest.raises(StateError):journal.append(event,expected_count=0)
    assert journal.load()==[event] and store.events(job['id'])==before
    another=journal_class(store,job,'other-owner')
    with pytest.raises(StateError):another.append(dict(kind='not_owned'))
    assert journal.load()==[event]

@pytest.mark.parametrize('fault',['event','deleted_tail','head','count','payload','index_binding'])
def test_mutated_journal_or_binding_is_not_replayed(tmp_path,journal_class,fault):
    store,job,journal=owned(tmp_path,journal_class);journal.append(dict(kind='preparation_started',contract_hash='c'*64))
    with store.db() as db:
        if fault=='event':db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='spread_protocol'",(job['id'],))
        elif fault=='deleted_tail':db.execute("DELETE FROM events WHERE entity_id=? AND kind='spread_protocol'",(job['id'],))
        elif fault=='head':db.execute("UPDATE spread_state SET head_sha256=? WHERE job_id=?",('0'*64,job['id']))
        elif fault=='count':db.execute('UPDATE spread_state SET event_count=99 WHERE job_id=?',(job['id'],))
        elif fault=='payload':db.execute("UPDATE jobs SET payload='{}' WHERE id=?",(job['id'],))
        else:db.execute('UPDATE job_input_index SET payload_sha256=? WHERE job_id=?',('f'*64,job['id']))
    with pytest.raises(StateError):journal.load()

def test_failed_projection_or_lost_owner_does_not_append_partial_event(tmp_path,journal_class):
    store,job,journal=owned(tmp_path,journal_class)
    with pytest.raises(StateError):journal.append(dict(kind='probe_started',family='break_of_structure',batch=0,ordinal=0,config_id='c'*64,attempt=1))
    assert journal.load()==[] and journal.status()['event_count']==0
    store.release(job['id'],'owner')
    with pytest.raises(StateError):journal.append(dict(kind='preparation_started',contract_hash='c'*64))
    assert journal.status()['event_count']==0

def test_staged_occurrence_and_interrupted_attempts_preserve_the_original_plan(tmp_path,journal_class):
    store,job,journal=owned(tmp_path,journal_class);original=next(e for e in store.events(job['id']) if e['kind']=='trial_plan_frozen')
    journal.append(dict(kind='preparation_started',contract_hash='c'*64));journal.append(dict(kind='preparation_batch',record=batch_record()));journal.append(dict(kind='preparation_sealed',plan_id='d'*64))
    coordinate=dict(family='break_of_structure',batch=0,ordinal=1,config_id=identity(Strategy(family='break_of_structure')))
    journal.append(dict(kind='selection_started',plan_id='d'*64,context=job['payload']['context']))
    journal.append(dict(kind='batch_started',family='break_of_structure',batch=0,configuration_hash='f'*64))
    journal.append(dict(kind='probe_planned',**coordinate))
    journal.append(dict(kind='probe_started',**coordinate,attempt=1))
    store.release(job['id'],'owner');claimed=store.claim('second');assert claimed['id']==job['id']
    restarted=journal_class(store,claimed,'second');assert len(restarted.load())==7
    restarted.append(dict(kind='probe_started',**coordinate,attempt=2))
    registry=store.registry(job_id=job['id']);assert registry['totals']['roles']['signal_probe']==dict(occurrences=1,distinct_configurations=1)
    assert registry['totals']['computation_attempts']==2
    assert [a['state'] for a in registry['rows'][0]['attempt_history']]==['interrupted','running']
    assert next(e for e in store.events(job['id']) if e['kind']=='trial_plan_frozen')==original
    store.verify_trial_plan(job['id'])

def test_projection_tracks_distinct_proposals_probes_and_selection(tmp_path,journal_class):
    store,job,journal=owned(tmp_path,journal_class)
    journal.append(dict(kind='preparation_started',contract_hash='c'*64))
    journal.append(dict(kind='preparation_batch',record=batch_record()))
    journal.append(dict(kind='preparation_sealed',plan_id='d'*64))
    status=journal.status();assert status['frozen_proposals']==2 and status['frozen_batches']==1 and status['probe_attempts']==0 and status['selected_versions']==0

@pytest.mark.parametrize('fault',['invented_attempt','changed_attempt_owner','changed_parent_plan','malformed_projection'])
def test_registry_details_must_reconcile_to_original_protocol_not_just_self_hashes(tmp_path,journal_class,fault):
    import json
    store,job,journal=owned(tmp_path,journal_class);start_probe(journal,job)
    with store.db() as db:
        if fault=='invented_attempt':
            row=db.execute('SELECT id FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone()
            db.execute("INSERT INTO trial_attempts(trial_id,ordinal,owner,started,state) VALUES(?,2,'owner',1,'running')",(row['id'],));db.execute('UPDATE trial_plans SET attempts=2 WHERE id=?',(row['id'],))
        elif fault=='changed_attempt_owner':db.execute("UPDATE trial_attempts SET owner='invented-owner'")
        elif fault=='changed_parent_plan':
            row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='staged_trial_frozen'",(job['id'],)).fetchone();phase=json.loads(row['details']);phase['proposal_plan_id']='f'*64;phase['plan_hash']=identity({k:v for k,v in phase.items() if k not in {'trial_id','plan_hash'}})
            db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(phase),row['id']));db.execute('UPDATE trial_plans SET plan_hash=? WHERE job_id=?',(phase['plan_hash'],job['id']))
        else:db.execute("UPDATE spread_state SET projection='{' WHERE job_id=?",(job['id'],))
    with pytest.raises(StateError):journal.load()
