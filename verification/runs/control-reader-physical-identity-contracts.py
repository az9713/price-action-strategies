"""Fresh SQLite control reads and physical identity with bounded path walking."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import pytest
from backend.lab.store import Store,StateError
from test_control_reader import running

def test_every_poll_checks_physical_identity_and_issues_fresh_sql_without_path_walk(running,monkeypatch):
    store,jid=running;resolve=Path.resolve;physical=store._control_identity;connect=sqlite3.connect
    counts=dict(resolve=0,identity=0);queries=[]
    def resolving(path,*a,**k):
        if path==store.path:counts['resolve']+=1
        return resolve(path,*a,**k)
    def identity(path):counts['identity']+=1;return physical(path)
    def connecting(*a,**k):
        db=connect(*a,**k);db.set_trace_callback(queries.append);return db
    monkeypatch.setattr(Path,'resolve',resolving);monkeypatch.setattr(store,'_control_identity',identity);monkeypatch.setattr(sqlite3,'connect',connecting)
    with store.control_reads():
        for _ in range(1000):assert store.cancellation_requested(jid,'owner') is False
    assert counts['identity']>=1002 and counts['resolve']==2
    assert len([q for q in queries if q.startswith('SELECT status,owner,cancel_requested FROM jobs')])==1000

def test_changed_file_identity_never_uses_the_prior_connection(running,monkeypatch):
    store,jid=running;physical=store._control_identity;connection=store.db;opens=[]
    @contextmanager
    def opened(*a,**k):
        opens.append(True)
        with connection(*a,**k) as db:yield db
    with store.control_reads():
        assert store.cancellation_requested(jid,'owner') is False
        old=physical(store.path)
        monkeypatch.setattr(store,'_control_identity',lambda path:(old[0],old[1]+1))
        monkeypatch.setattr(store,'db',opened)
        with connection() as db:db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(jid,))
        assert store.cancellation_requested(jid,'owner') is True and opens==[True]

def test_missing_or_unreadable_physical_identity_fails_closed(running,monkeypatch):
    store,jid=running
    with store.control_reads():
        stat=Path.stat
        def missing(path,*a,**k):
            if path==store.path:raise FileNotFoundError('Authored removed database')
            return stat(path,*a,**k)
        monkeypatch.setattr(Path,'stat',missing)
        with pytest.raises(StateError,match='identity is unavailable'):store.cancellation_requested(jid,'owner')

def test_filesystems_without_file_ids_keep_the_original_resolved_path_fallback(running,monkeypatch):
    store,jid=running;resolve=Path.resolve;calls=[]
    monkeypatch.setattr(store,'_control_identity',lambda path:(0,0))
    def observed(path,*a,**k):
        if path==store.path:calls.append(True)
        return resolve(path,*a,**k)
    monkeypatch.setattr(Path,'resolve',observed)
    with store.control_reads():
        assert store.cancellation_requested(jid,'owner') is False
        with store.db() as db:db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(jid,))
        assert store.cancellation_requested(jid,'owner') is True
    assert len(calls)>=4

def test_lexical_alias_to_same_physical_database_preserves_readonly_reuse(running,tmp_path,monkeypatch):
    store,jid=running;other=Store(tmp_path/'other')
    other.path=store.path.parent/'..'/'data'/'lab.sqlite3'
    assert other.path!=store.path and other.path.resolve()==store.path.resolve()
    connect=sqlite3.connect;connections=[]
    def observed(*a,**k):
        db=connect(*a,**k);connections.append(db);return db
    monkeypatch.setattr(sqlite3,'connect',observed)
    with store.control_reads():
        assert other.cancellation_requested(jid,'owner') is False and len(connections)==1
    with pytest.raises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')

def test_changed_store_path_uses_its_new_database_and_can_return_to_original(running,tmp_path):
    store,jid=running;other=Store(tmp_path/'other');job=other.create_job('experiment',dict(name='Other controls'));other.claim('other-owner')
    original=store.path
    with store.control_reads():
        store.path=other.path
        assert store.cancellation_requested(job['id'],'other-owner') is False
        with pytest.raises(StateError):store.cancellation_requested(jid,'owner')
        store.path=original
        assert store.cancellation_requested(jid,'owner') is False

def test_database_change_during_reader_open_is_refused_and_connection_closed(running,monkeypatch):
    store,jid=running;physical=store._control_identity;connect=sqlite3.connect;connections=[];changed=[]
    def identity(path):
        value=physical(path)
        return (value[0],value[1]+1) if changed else value
    def opened(*a,**k):
        db=connect(*a,**k);connections.append(db);changed.append(True);return db
    monkeypatch.setattr(store,'_control_identity',identity);monkeypatch.setattr(sqlite3,'connect',opened)
    with pytest.raises(StateError,match='changed while'):
        with store.control_reads():pytest.fail('Changed physical database was accepted')
    with pytest.raises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')
