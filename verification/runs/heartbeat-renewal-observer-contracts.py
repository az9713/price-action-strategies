"""Observers receive only actual committed uncanceled owned renewals."""
import sqlite3,time
import pytest
from backend.lab.store import Store,StateError


def owned(tmp_path):
    store=Store(tmp_path);job=store.create_job('download',{})
    assert store.claim('renewal-observer')['id']==job['id']
    return store,job


def test_renewal_observer_can_independently_read_the_committed_lease(tmp_path):
    store,job=owned(tmp_path);observed=[]
    def committed(at):
        with store.db() as db:
            row=db.execute('SELECT lease_until,progress FROM jobs WHERE id=?',(job['id'],)).fetchone()
        assert row['lease_until']>time.time()+13 and row['progress']==.25
        assert at<=time.monotonic();observed.append(at)
    assert store.heartbeat(job['id'],'renewal-observer',.25,on_renewal=committed) is False
    assert len(observed)==1


@pytest.mark.parametrize('fault',['writer_lock','wrong_owner','canceled'])
def test_no_success_observation_after_failed_stale_or_canceled_renewal(tmp_path,fault):
    store,job=owned(tmp_path);observed=[]
    if fault=='writer_lock':
        with store.db() as writer:
            writer.execute('BEGIN IMMEDIATE')
            with pytest.raises(sqlite3.OperationalError):store.heartbeat(job['id'],'renewal-observer',on_renewal=observed.append)
            writer.execute('ROLLBACK')
    elif fault=='wrong_owner':
        with pytest.raises(StateError):store.heartbeat(job['id'],'stale-owner',on_renewal=observed.append)
    else:
        store.cancel(job['id'])
        assert store.heartbeat(job['id'],'renewal-observer',on_renewal=observed.append) is True
    assert observed==[]


def test_invalid_observer_is_rejected_without_changing_the_lease(tmp_path):
    store,job=owned(tmp_path);before=store.job(job['id'])['lease_until']
    with pytest.raises(ValueError):store.heartbeat(job['id'],'renewal-observer',on_renewal=True)
    assert store.job(job['id'])['lease_until']==before
