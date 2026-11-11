"""Exact old/new heartbeat behavior and real covering-index query plans."""
from contextlib import contextmanager
from pathlib import Path
import hashlib
import importlib.util
import itertools
import json
import sqlite3
import pytest
from backend.lab.store import Store, StateError


def original_store():
    folder=Path(__file__).with_name('heartbeat-covering-before')
    raw=(folder/'store.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==json.loads((folder/'provenance.json').read_text())['sha256']
    spec=importlib.util.spec_from_file_location('backend.lab.heartbeat_original',folder/'store.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Store


def prepare(cls,folder):
    store=cls(folder);job=store.create_job('download',{'authored_synthetic':'x'*65536})
    assert store.claim('owner')['id']==job['id']
    store.heartbeat(job['id'],'owner',.35,'original checkpoint',7)
    return store,job


@pytest.mark.parametrize('progress,note,checkpoint',list(itertools.product(
    [None,-.5,0.,.75,1.5],[None,'','new checkpoint'],[None,0,9])))
def test_every_optional_field_matches_sha_bound_original(tmp_path,progress,note,checkpoint):
    observed=[]
    for cls,folder in [(original_store(),tmp_path/'before'),(Store,tmp_path/'after')]:
        store,job=prepare(cls,folder);payload=store.job(job['id'])['payload']
        assert store.heartbeat(job['id'],'owner',progress,note,checkpoint) is False
        result=store.job(job['id'])
        assert result['payload']==payload and result['owner']=='owner' and result['status']=='running'
        observed.append({k:result[k] for k in ['progress','note','checkpoint','cancel_requested']})
    assert observed[0]==observed[1]


def test_actual_heartbeat_ownership_read_is_covering_without_payload_fields(tmp_path,monkeypatch):
    store,job=prepare(Store,tmp_path);real=store.db;queries=[]
    class Proxy:
        def __init__(self,db):self.db=db
        def __getattr__(self,name):return getattr(self.db,name)
        def execute(self,sql,*args):
            if sql.lstrip().upper().startswith('SELECT'):
                queries.append((sql,[r[3] for r in self.db.execute('EXPLAIN QUERY PLAN '+sql,*args)]))
            return self.db.execute(sql,*args)
    @contextmanager
    def traced(*a,**k):
        with real(*a,**k) as db:yield Proxy(db)
    monkeypatch.setattr(store,'db',traced)
    assert store.heartbeat(job['id'],'owner',.5,'saved',8) is False
    assert len(queries)==1
    sql,plans=queries[0]
    assert any('COVERING INDEX jobs_live_control' in p for p in plans)
    assert all(field not in sql.lower() for field in ['payload','progress','note','checkpoint'])


@pytest.mark.parametrize('progress',['invalid',object()])
def test_invalid_progress_rolls_back_without_success_callback(tmp_path,progress):
    store,job=prepare(Store,tmp_path);before=store.job(job['id']);calls=[]
    with pytest.raises((TypeError,ValueError)):
        store.heartbeat(job['id'],'owner',progress,on_renewal=calls.append)
    assert store.job(job['id'])==before and calls==[]


@pytest.mark.parametrize('fault',['missing','wrong_owner','completed','canceled','update_aborted'])
def test_refused_and_canceled_writes_preserve_original_behavior(tmp_path,fault):
    outcomes=[]
    for cls,folder in [(original_store(),tmp_path/'before'),(Store,tmp_path/'after')]:
        store,job=prepare(cls,folder);jid=job['id'];owner='owner';calls=[]
        if fault=='missing':jid='absent'
        elif fault=='wrong_owner':owner='other'
        elif fault=='completed':store.finish(jid,owner,'completed')
        elif fault=='canceled':store.cancel(jid)
        else:
            with store.db() as db:
                db.execute("CREATE TRIGGER abort_renewal BEFORE UPDATE ON jobs BEGIN SELECT RAISE(ABORT,'authored refusal'); END")
        before=store.job(job['id'])
        try:outcome=store.heartbeat(jid,owner,.9,'changed',10,on_renewal=calls.append)
        except (ValueError,sqlite3.DatabaseError) as exc:outcome=type(exc).__name__
        after=store.job(job['id'])
        if fault!='canceled':assert after==before
        else:assert after['cancel_requested']==1 and after['progress']==.9
        assert calls==[]
        outcomes.append(outcome)
    assert outcomes[0]==outcomes[1]
