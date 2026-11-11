"""Bounded replay contracts; metadata fixture does not execute market signals/accounts."""
import tracemalloc
import pytest
from backend.lab.config import identity
from backend.lab.research import core_hash
from backend.lab.spread import SpreadSettings,SpreadError,freeze_plan,select
from backend.lab.spread_jobs import SpreadJournal
from backend.lab.store import Store

def context():return dict(dataset_id='a'*24,dataset_manifest_hash='b'*64,primary_symbol='SPY',start='2026-11-02',end='2026-11-06')

def test_invalid_replay_prefix_rejects_before_materializing_the_entire_iterator(tmp_path):
    settings=SpreadSettings(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=2,max_batches_per_family=1)
    plan=freeze_plan(tmp_path/'plan',settings);consumed=[]
    def history():
        consumed.append(1);yield dict(kind='selection_started',plan_id=plan.plan_id,context=context())
        for _ in range(100000):consumed.append(1);yield dict(kind='invalid_prefix')
    with pytest.raises(SpreadError):select(plan,context(),lambda cfg:pytest.fail('Invalid history reached a probe'),lambda e:None,authorize=lambda:None,replay=history())
    assert len(consumed)<=3

def test_large_metadata_only_journal_streams_with_bounded_python_heap(tmp_path):
    store=Store(tmp_path);settings=SpreadSettings(families=['break_of_structure'],timeframes=['1m'],per_family=128,batch_size=400,max_batches_per_family=128)
    payload=dict(core_hash=core_hash(),settings=settings.model_dump(),context=context(),name='Nonfinancial journal-memory fixture; zero actual signal/account computations')
    job=store.create_job('spread',payload);claimed=store.claim('owner');assert claimed['id']==job['id']
    journal=SpreadJournal(store,claimed,'owner',stream=True);journal.append(dict(kind='preparation_started',contract_hash='c'*64))
    for batch in range(128):journal.append(dict(kind='preparation_batch',record=dict(contract_hash='c'*64,core_hash=core_hash(),family='break_of_structure',batch=batch,relative_path=f'break_of_structure/{batch:06}.json.gz',bytes=20,sha256='e'*64,proposal_count=400,configurations_hash='f'*64)))
    journal.append(dict(kind='preparation_sealed',plan_id='d'*64));journal.append(dict(kind='selection_started',plan_id='d'*64,context=context()))
    for batch in range(128):
        journal.append(dict(kind='batch_started',family='break_of_structure',batch=batch,configuration_hash='f'*64))
        journal.append(dict(kind='batch_finished',family='break_of_structure',batch=batch,selected_ordinal=None,outcomes=[dict(ordinal=i,config_id=f'{batch*400+i:064x}',status='not_probed') for i in range(400)]))
    tracemalloc.start()
    restored=SpreadJournal(store,claimed,'owner',stream=True)
    count=sum(1 for e in restored.iter_envelopes(through_id=restored.replay_through))
    current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    assert count==journal.count and peak<8*1024*1024
    assert restored.status()['unprobed_proposals']==51200 and restored.status()['probe_attempts']==0
