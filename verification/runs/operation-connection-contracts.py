"""Actual scoped SQLite connections; transactions and authority stay fresh."""
from contextvars import copy_context
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import importlib.util,json,hashlib,sqlite3
import pytest
from backend.lab import store as module
from backend.lab.store import Store,StateError


def scalar(store,sql='SELECT 1'):
    with store.db() as db:return db.execute(sql).fetchone()[0]


def test_actual_connection_opens_fall_from_forty_to_one_with_equal_committed_rows(tmp_path,monkeypatch):
    folder=Path(__file__).with_name('large-account-unit-before')
    metadata=json.loads((folder/'provenance.json').read_text())
    original=folder/'store.py'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==next(x['sha256'] for x in metadata['files'] if x['path']=='backend/lab/store.py')
    spec=importlib.util.spec_from_file_location('backend.lab.before_operation_store',original)
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    before=prior.Store(tmp_path/'before');after=Store(tmp_path/'after')
    for store in [before,after]:
        with store.db() as db:db.execute('CREATE TABLE authored(v INTEGER PRIMARY KEY)')
    connect=sqlite3.connect;opens=[]
    def opened(*args,**kwargs):opens.append(str(args[0]));return connect(*args,**kwargs)
    monkeypatch.setattr(module.sqlite3,'connect',opened)
    def work(store):
        for i in range(20):
            with store.db() as db:
                db.execute('BEGIN IMMEDIATE');db.execute('INSERT INTO authored VALUES(?)',(i,));db.execute('COMMIT')
            assert scalar(store,'SELECT COUNT(*) FROM authored')==i+1
    work(before)
    with after.connection_reuse():work(after)
    assert opens.count(str(before.path))==40 and opens.count(str(after.path))==1
    for store in [before,after]:
        with store.db() as db:assert [r[0] for r in db.execute('SELECT v FROM authored ORDER BY v')]==list(range(20))


@pytest.mark.parametrize('mode',['normal','error','interrupt'])
def test_scope_closes_the_actual_handle_on_every_exit(tmp_path,mode):
    store=Store(tmp_path);connections=[]
    def run():
        with store.connection_reuse():
            with store.db() as db:connections.append(db);assert db.execute('SELECT 1').fetchone()[0]==1
            if mode=='error':raise ValueError('authored')
            if mode=='interrupt':raise KeyboardInterrupt()
    if mode=='normal':run()
    else:
        with pytest.raises(ValueError if mode=='error' else KeyboardInterrupt):run()
    with pytest.raises(sqlite3.ProgrammingError,match='closed'):connections[0].execute('SELECT 1')
    assert module._operation_connection.get() is None
    assert scalar(store)==1


@pytest.mark.parametrize('failure',['error','unfinished'])
def test_each_borrow_rolls_back_unfinished_writes_before_reuse(tmp_path,failure):
    store=Store(tmp_path)
    with store.db() as db:db.execute('CREATE TABLE authored(v)')
    with store.connection_reuse():
        try:
            with store.db() as first:
                first.execute('BEGIN IMMEDIATE');first.execute('INSERT INTO authored VALUES(1)')
                if failure=='error':raise ValueError('authored rollback')
        except ValueError:pass
        with store.db() as second:
            assert first is second and not second.in_transaction
            assert second.execute('SELECT COUNT(*) FROM authored').fetchone()[0]==0
            second.execute('BEGIN IMMEDIATE');second.execute('INSERT INTO authored VALUES(2)');second.execute('COMMIT')
        assert scalar(store,'SELECT SUM(v) FROM authored')==2


def test_nested_context_has_independent_transaction_and_outer_scope_reuses(tmp_path):
    store=Store(tmp_path)
    with store.db() as db:db.execute('CREATE TABLE authored(v)')
    with store.connection_reuse():
        with store.db() as outer:
            outer.execute('BEGIN IMMEDIATE');outer.execute('INSERT INTO authored VALUES(1)')
            with store.connection_reuse(),store.db() as inner:
                assert inner is not outer and inner.execute('SELECT COUNT(*) FROM authored').fetchone()[0]==0
            outer.execute('COMMIT')
        with store.db() as again:assert again is outer and again.execute('SELECT COUNT(*) FROM authored').fetchone()[0]==1


def test_timeout_and_durability_pragmas_remain_exact_per_borrow(tmp_path):
    store=Store(tmp_path)
    with store.connection_reuse():
        for timeout in [500,0,10000,250]:
            with store.db(busy_timeout_ms=timeout) as db:
                assert db.execute('PRAGMA busy_timeout').fetchone()[0]==timeout
                assert db.execute('PRAGMA foreign_keys').fetchone()[0]==1
                assert db.execute('PRAGMA journal_mode').fetchone()[0]=='wal'
                assert db.execute('PRAGMA synchronous').fetchone()[0]==2
        for timeout in [-1,10001,True,1.5]:
            with pytest.raises(ValueError):
                with store.db(busy_timeout_ms=timeout):pass


def test_external_commits_cancellation_and_ownership_are_fresh(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',{'strategy':{}});store.claim('first')
    with store.connection_reuse():
        assert not store.cancellation_requested(job['id'],'first')
        with closing(sqlite3.connect(store.path,isolation_level=None)) as external:
            external.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(job['id'],))
        assert store.cancellation_requested(job['id'],'first')
        with closing(sqlite3.connect(store.path,isolation_level=None)) as external:
            external.execute("UPDATE jobs SET owner='second' WHERE id=?",(job['id'],))
        with pytest.raises(StateError):store.cancellation_requested(job['id'],'first')


def test_other_store_thread_handoff_and_copied_thread_cannot_borrow_handle(tmp_path):
    one=Store(tmp_path/'one');two=Store(tmp_path/'two')
    with one.connection_reuse():
        with one.db() as retained:assert retained.execute('SELECT 1').fetchone()[0]==1
        with two.db() as other:assert other is not retained
        with one.db(thread_handoff=True) as handed:assert handed is not retained
        with pytest.raises(sqlite3.ProgrammingError):handed.execute('SELECT 1')
        def worker():
            with one.connection_reuse(),one.db() as db:assert db is not retained;return db.execute('SELECT 1').fetchone()[0]
        copied=copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:assert pool.submit(copied.run,worker).result(timeout=10)==1
        with one.db() as again:assert again is retained


def test_inactive_copied_context_does_not_resurrect_closed_connection(tmp_path):
    store=Store(tmp_path)
    with store.connection_reuse():
        with store.db() as retained:pass
        copied=copy_context()
    def later():
        with store.db() as db:assert db is not retained;return db.execute('SELECT 1').fetchone()[0]
    assert copied.run(later)==1


def test_actual_physical_database_replacement_is_refused(tmp_path):
    store=Store(tmp_path)
    with store.connection_reuse():
        with store.db() as db:assert db.execute('SELECT 1').fetchone()[0]==1
        # Release the Windows handle to permit an actual inode replacement.
        db.close();store.path.replace(store.path.with_name('preserved-original.sqlite3'))
        with closing(sqlite3.connect(store.path)) as replacement:replacement.execute('CREATE TABLE replacement(v)')
        with pytest.raises(StateError,match='database changed'):scalar(store)


def test_changed_store_path_is_refused_instead_of_using_cached_handle(tmp_path):
    store=Store(tmp_path)
    with store.connection_reuse():
        original=store.path;assert scalar(store)==1
        store.path=tmp_path/'other.sqlite3'
        try:
            with pytest.raises(StateError,match='database changed'):scalar(store)
        finally:store.path=original
