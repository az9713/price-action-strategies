"""Strict publication metadata/serialization kernel; not financial-set evidence."""
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace
import copy
import gzip
import hashlib
import json
import sqlite3

import pytest
from backend.lab import trade_twin_worker as worker
from backend.lab.store import StateError


@pytest.fixture
def db():
    with closing(sqlite3.connect(':memory:')) as db:
        db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE events(id INTEGER PRIMARY KEY,entity_id TEXT,kind TEXT,details TEXT)')
        yield db


def put(db,kind,value,job='authored',identifier=None):
    db.execute('INSERT INTO events(id,entity_id,kind,details) VALUES(?,?,?,?)',
               (identifier,job,kind,json.dumps(value)))


def pair(db,root_hash='b'*64):
    manifest = dict(filename='pub-'+'a'*32+'.manifest.json.gz',sha256='c'*64,content_hash='d'*64)
    put(db,'twin_financial_manifest_saved',manifest)
    put(db,'result_saved',dict(sha256=root_hash))
    return manifest


def test_empty_unpublished_state_and_other_jobs_do_not_fabricate_publication(db):
    assert worker._publication(db,'authored') is None
    pair(db)
    assert worker._publication(db,'another-job') is None
    marker = worker._publication(db,'authored')
    assert marker['manifest_event_id']+1 == marker['result_event_id']
    assert marker['manifest']['filename'] == 'pub-'+'a'*32+'.manifest.json.gz'


@pytest.mark.parametrize('fault',['missing_root','missing_manifest','duplicate','reversed','nonadjacent','oversized','invalid_json','saved_view_without_pair'])
def test_lost_atomic_publication_or_oversized_original_events_refuse_replacement(db,fault):
    pair(db)
    if fault == 'missing_root': db.execute("DELETE FROM events WHERE kind='result_saved'")
    elif fault == 'missing_manifest': db.execute("DELETE FROM events WHERE kind='twin_financial_manifest_saved'")
    elif fault == 'duplicate': put(db,'result_saved',dict(sha256='b'*64))
    elif fault == 'reversed': db.execute("UPDATE events SET id=3 WHERE id=1")
    elif fault == 'nonadjacent': db.execute("UPDATE events SET id=4 WHERE id=2")
    elif fault == 'oversized': db.execute("UPDATE events SET details=? WHERE id=1",('x'*17000,))
    elif fault == 'invalid_json': db.execute("UPDATE events SET details='{' WHERE id=1")
    else:
        db.execute('DELETE FROM events')
        put(db,'trade_twin_view_saved',dict(filename='derived.sqlite3'))
    with pytest.raises(StateError):worker._publication(db,'authored')


@pytest.mark.parametrize('fault',['manifest_list','manifest_extra','filename_type','filename_traversal','manifest_sha_type','manifest_sha_uppercase','manifest_content_hash','saved_list','saved_extra','saved_sha_type','saved_sha_length'])
def test_original_publication_shape_and_hashes_are_strict_and_not_coerced(db,fault):
    manifest = pair(db)
    saved = dict(sha256='b'*64)
    if fault == 'manifest_list': manifest=[]
    elif fault == 'manifest_extra': manifest['extra']=1
    elif fault == 'filename_type': manifest['filename']=None
    elif fault == 'filename_traversal': manifest['filename']='../outside.manifest.json.gz'
    elif fault == 'manifest_sha_type': manifest['sha256']=0
    elif fault == 'manifest_sha_uppercase': manifest['sha256']='C'*64
    elif fault == 'manifest_content_hash': manifest['content_hash']='f'*63
    elif fault == 'saved_list': saved=[]
    elif fault == 'saved_extra': saved['extra']=1
    elif fault == 'saved_sha_type': saved['sha256']=True
    else: saved['sha256']='b'*63
    db.execute('UPDATE events SET details=? WHERE id=1',(json.dumps(manifest),))
    db.execute('UPDATE events SET details=? WHERE id=2',(json.dumps(saved),))
    with pytest.raises(StateError):worker._publication(db,'authored')


def test_original_pair_and_file_are_both_checked_against_the_frozen_marker(db,tmp_path):
    path = tmp_path/'root.json.gz'
    path.write_bytes(gzip.compress(b'{"authored_metadata_only":true}',mtime=0))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    pair(db,digest)
    marker = worker._publication(db,'authored')
    lab = SimpleNamespace(output_path=lambda _:path)
    worker._same_publication(lab,db,'authored',marker)
    changed = copy.deepcopy(marker);changed['result_event_id']+=1
    with pytest.raises(StateError):worker._same_publication(lab,db,'authored',changed)
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(StateError):worker._same_publication(lab,db,'authored',marker)


def test_original_root_serialization_guard_checks_disk_and_expansion_before_json(tmp_path,monkeypatch):
    path = tmp_path/'original.json.gz'
    path.write_bytes(gzip.compress(json.dumps({'value':'x'*1000}).encode(),mtime=0))
    # Exercise the same configurable serialization guard with a small authored
    # bound; this is not a512MiB resource or RSS measurement.
    monkeypatch.setattr(worker,'MAX_PART_BYTES',100)
    assert path.stat().st_size<100
    with pytest.raises(StateError,match='expansion'):worker._read(path)
    path.write_bytes(b'x'*101)
    with pytest.raises(StateError,match='serialization'):worker._read(path)
    path.write_bytes(gzip.compress(b'{"complete":true}',mtime=0))
    assert worker._read(path)=={'complete':True}
