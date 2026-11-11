"""Ledger lifecycle and complete-history counters, without any market reads."""
from pathlib import Path
import json
import pytest
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.store import Store,StateError

def payload():
    return dict(dataset_id='a'*24,strategy=Strategy().model_dump(),costs=Costs().model_dump(),portfolio=Portfolio().model_dump(),
        start='2026-10-05',end='2026-10-06',seed=42,core_hash='b'*64,dataset_manifest_hash='c'*64)

def test_trial_plans_are_atomic_and_frozen_before_execution(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());ledger=store.registry(job_id=job['id'])
    assert len(ledger['rows'])==1 and ledger['rows'][0]['state']=='planned' and ledger['rows'][0]['attempts']==0
    assert ledger['rows'][0]['provenance']=='prespecified'
    assert any(e['kind']=='trial_plan_frozen' for e in store.events(job['id']))
    store.verify_trial_plan(job['id'])

def test_repeats_and_controls_do_not_turn_into_independent_strategy_counts(tmp_path):
    store=Store(tmp_path);store.create_job('experiment',payload());store.create_job('experiment',payload())
    store.create_job('controls',payload()|dict(replicas=3));store.create_job('benchmark',payload())
    totals=store.registry()['totals'];assert totals['planned_occurrences']==9
    assert totals['roles']['strategy']['distinct_configurations']==1
    assert totals['roles']['random_control']['occurrences']==3
    assert totals['roles']['benchmark']['occurrences']==2
    assert 'independent' in totals['interpretation'].lower()

def test_failed_canceled_retried_and_cached_attempts_have_distinct_counts(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('one')
    store.start_trial(job['id'],0,'report','one');store.finish(job['id'],'one','failed','Authored failure')
    row=store.registry(job_id=job['id'])['rows'][0];assert row['state']=='failed' and row['attempts']==1
    store.resume(job['id']);store.claim('two');store.start_trial(job['id'],0,'report','two')
    value=dict(answer=1);store.computed_trial(job['id'],0,'report','two',value)
    store.checkpoint_trial(job['id'],0,'report','two',value,'d'*64);store.finish(job['id'],'two','completed')
    ledger=store.registry(job_id=job['id']);assert ledger['rows'][0]['state']=='completed' and ledger['rows'][0]['attempts']==2
    assert [a['state'] for a in ledger['rows'][0]['attempt_history']]==['failed','checkpointed']

def test_never_started_cancellation_is_not_a_completed_trial(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.cancel(job['id'])
    row=store.registry(job_id=job['id'])['rows'][0];assert row['state']=='not_started' and row['attempts']==0

def test_registry_pagination_is_not_limited_to_latest500_jobs(tmp_path):
    store=Store(tmp_path)
    for _ in range(505):store.create_job('experiment',payload())
    result=store.registry(limit=10,offset=500)
    assert result['totals']['planned_occurrences']==505 and len(result['rows'])==5
    assert Store(tmp_path).registry()['totals']['planned_occurrences']==505

def test_legacy_migration_is_explicitly_posthoc_not_prespecified(tmp_path):
    store=Store(tmp_path)
    with store.db() as db:db.execute('INSERT INTO jobs(id,kind,payload,status,created,updated) VALUES(?,?,?,?,?,?)',('legacy','experiment',json.dumps(payload()),'completed',1,2))
    reopened=Store(tmp_path);row=reopened.registry(job_id='legacy')['rows'][0]
    assert row['provenance']=='legacy_posthoc' and row['state']=='legacy_unverified' and row['attempts']==0

def test_a_computed_but_unpublished_numeric_trial_cannot_complete_its_job(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('one')
    store.start_trial(job['id'],0,'report','one');store.computed_trial(job['id'],0,'report','one',dict(answer=1))
    with pytest.raises(StateError):store.finish(job['id'],'one','completed')
    assert store.job(job['id'])['status']=='running'

def test_atomic_plan_failure_does_not_leave_an_unregistered_job(tmp_path,monkeypatch):
    store=Store(tmp_path)
    def fail(*args,**kwargs):raise StateError('Injected plan registration failure')
    monkeypatch.setattr(store._trials,'freeze',fail)
    with pytest.raises(StateError):store.create_job('experiment',payload())
    assert store.jobs()==[] and store.registry()['totals']['planned_occurrences']==0

def test_lease_recovery_and_verified_cache_reuse_do_not_invent_another_execution(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('dead',lease_seconds=-1)
    store.start_trial(job['id'],0,'report','dead');value=dict(answer=1)
    store.computed_trial(job['id'],0,'report','dead',value)
    # Restore the expired lease after start, which itself does not renew it.
    store.claim('new');row=store.registry(job_id=job['id'])['rows'][0]
    assert row['state']=='interrupted' and row['attempt_history'][0]['state']=='interrupted'
    store.checkpoint_trial(job['id'],0,'report','new',value,'d'*64);store.finish(job['id'],'new','completed')
    row=store.registry(job_id=job['id'])['rows'][0]
    assert row['attempts']==1 and row['reuses']==1 and row['state']=='completed'

@pytest.mark.parametrize('mode',['payload','role','config','plan_hash','provenance'])
def test_frozen_payload_or_plan_row_tampering_rejects(mode,tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload())
    with store.db() as db:
        if mode=='payload':db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(payload()|dict(seed=7)),job['id']))
        else:db.execute('UPDATE trial_plans SET '+('config_id' if mode=='config' else mode)+'=? WHERE job_id=?',('changed',job['id']))
    with pytest.raises(StateError,match='Frozen'):store.verify_trial_plan(job['id'])

def test_wrong_worker_duplicate_start_and_changed_output_are_refused(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('owner')
    with pytest.raises(StateError):store.start_trial(job['id'],0,'report','other')
    with pytest.raises(StateError):store.computed_trial(job['id'],0,'report','owner',{})
    store.start_trial(job['id'],0,'report','owner')
    with pytest.raises(StateError):store.start_trial(job['id'],0,'report','owner')
    store.computed_trial(job['id'],0,'report','owner',dict(answer=1))
    with pytest.raises(StateError):store.checkpoint_trial(job['id'],0,'report','owner',dict(answer=2),'d'*64)

def test_full_job_export_preserves_more_than_one_page_and_proposal_history(tmp_path):
    store=Store(tmp_path);configs=[Strategy(level_age=n).model_dump() for n in range(2,207)]
    proposals=[dict(attempt=i+1,status='accepted',config_id=identity(c)) for i,c in enumerate(configs)]
    proposals += [dict(attempt=206,status='duplicate',config_id=identity(configs[0])),
                  dict(attempt=207,status='invalid',configuration=dict(family='invalid'),reason='Invalid family')]
    job=store.create_job('search',payload()|dict(configurations=configs,sampling=dict(attempts=207,unique=205,duplicates=1,rejected=1,proposals=proposals)))
    assert len(store.registry(limit=200,job_id=job['id'])['rows'])==200
    exported=json.loads(''.join(store.export_trials(job['id'],'json')))
    assert exported['occurrences']==205 and len(exported['rows'])==205 and exported['generation']['proposals']==proposals
    import csv,io
    assert len(list(csv.DictReader(io.StringIO(''.join(store.export_trials(job['id'],'csv'))))))==205
    assert store.registry()['totals']['generation']['proposals']==207

def test_streamed_export_can_handoff_threads_and_keeps_one_read_snapshot(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    store=Store(tmp_path);job=store.create_job('search',payload()|dict(configurations=[Strategy().model_dump(),Strategy(target='2R').model_dump()]))
    stream=store.export_trials(job['id'],'json')
    with ThreadPoolExecutor(max_workers=1) as first,ThreadPoolExecutor(max_workers=1) as second:
        prefix=first.submit(next,stream).result(timeout=10)
        store.cancel(job['id'])
        suffix=second.submit(lambda:''.join(stream)).result(timeout=10)
    exported=json.loads(prefix+suffix)
    assert all(r['state']=='planned' for r in exported['rows'])
    assert all(r['state']=='not_started' for r in store.registry(job_id=job['id'])['rows'])

@pytest.mark.parametrize('bad',[
    dict(attempts=1,unique=1,duplicates=0,rejected=0),
    dict(attempts=1,unique=1,duplicates=0,rejected=0,proposals=[dict(attempt=2,status='accepted',config_id='wrong')]),
    dict(attempts=1,unique=0,duplicates=1,rejected=0,proposals=[dict(attempt=1,status='duplicate',config_id='missing')]),
    dict(attempts=1,unique=0,duplicates=0,rejected=1,proposals=[dict(attempt=1,status='invalid',configuration=Strategy().model_dump(),reason='Not actually invalid')]),
    dict(attempts=1,unique=0,duplicates=0,rejected=1,proposals=[dict(attempt=1,status='invalid',configuration=dict(family='invalid'))]),
    dict(attempts=1,unique=1,duplicates=0,rejected=0,proposals=[dict(attempt=1,status='unknown')])])
def test_incomplete_or_false_generation_records_reject_atomically(tmp_path,bad):
    store=Store(tmp_path)
    with pytest.raises(StateError):store.create_job('search',payload()|dict(configurations=[Strategy().model_dump()],sampling=bad))
    assert store.jobs()==[] and store.registry()['totals']['planned_occurrences']==0

@pytest.mark.parametrize('proposal',[None,dict(attempt=1,status='accepted'),dict(attempt=1,status='invalid',configuration=[]),dict(attempt=1,status='invalid',configuration=dict(family='invalid'),reason='Authored invalid proposal')])
def test_malformed_and_false_sampler_identity_records_do_not_register_trials(tmp_path,proposal):
    store=Store(tmp_path)
    sampling=dict(attempts=1,unique=1,duplicates=0,rejected=0,proposals=[proposal])
    with pytest.raises(StateError):store.create_job('search',payload()|dict(configurations=[Strategy().model_dump()],sampling=sampling))
    assert store.jobs()==[]

def test_duplicate_accepted_configuration_cannot_inflate_the_trial_count(tmp_path):
    store=Store(tmp_path);cfg=Strategy().model_dump();cid=identity(cfg)
    sampling=dict(attempts=2,unique=2,duplicates=0,rejected=0,proposals=[dict(attempt=i,status='accepted',config_id=cid) for i in [1,2]])
    with pytest.raises(StateError):store.create_job('search',payload()|dict(configurations=[cfg,cfg],sampling=sampling))
    assert store.registry()['totals']['planned_occurrences']==0

def test_missing_original_plan_changed_occurrence_and_unknown_row_fail_closed(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('owner')
    with pytest.raises(StateError):store.verify_trial_plan('absent')
    with pytest.raises(StateError):store.start_trial(job['id'],99,'report','owner')
    with store.db() as db:db.execute('UPDATE trial_plans SET id=? WHERE job_id=?',('changed',job['id']))
    with pytest.raises(StateError):store.verify_trial_plan(job['id'])
    with store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_plan_frozen'",(job['id'],))
    with pytest.raises(StateError):store.verify_trial_plan(job['id'])

@pytest.mark.parametrize('value',[None,'','short','g'*64])
def test_incomplete_or_nonhex_output_digest_is_not_a_durable_checkpoint(tmp_path,value):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('owner')
    with pytest.raises(StateError):store.checkpoint_trial(job['id'],0,'report','owner',{},value)
    assert store.registry(job_id=job['id'])['rows'][0]['state']=='planned'

def test_changed_saved_digest_and_skipping_an_ordinary_account_are_refused(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload());store.claim('owner');report=dict(answer=1)
    store.start_trial(job['id'],0,'report','owner');store.computed_trial(job['id'],0,'report','owner',report)
    store.checkpoint_trial(job['id'],0,'report','owner',report,'d'*64)
    with pytest.raises(StateError):store.checkpoint_trial(job['id'],0,'report','owner',report,'e'*64)
    with pytest.raises(StateError):store.skip_trial(job['id'],0,'report','owner','Not a control')

def test_legacy_study_windows_are_reconstructed_without_fabricating_attempts(tmp_path):
    store=Store(tmp_path)
    with store.db() as db:
        db.execute('INSERT INTO jobs(id,kind,payload,status,created,updated) VALUES(?,?,?,?,?,?)',('legacy-screen','screen',json.dumps(dict(study_id='missing')),'failed',1,2))
    row=Store(tmp_path).registry(job_id='legacy-screen')['rows'][0]
    assert row['role']=='unclassified' and row['provenance']=='legacy_posthoc' and row['attempts']==0
