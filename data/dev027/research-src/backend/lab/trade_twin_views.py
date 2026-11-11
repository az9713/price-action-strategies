"""Saved-only inspection: derived seek storage, original financial authority.

Set rows are bound to original computation events. Book manifests are bound to
those original members; requested chunks are bound to the original manifest.
No price read, signal generation, matching draw or financial simulation occurs.
"""
from contextlib import contextmanager
from pathlib import Path
import gzip
import io
import json
import os
import re
import sqlite3
import uuid
import zipfile
from .config import canonical, identity
from .store import StateError
from .result_index import file_hash, input_bytes_hash
from .trade_twins import EXECUTION_POLICIES, TOTAL_SETS
from .trade_twin_results import CanonicalOutcome
from .trade_twin_parts import (MAX_PART_BYTES, PART_INDEX, PART_PREDICATE,
    TRIAL_INDEX, TRIAL_PREDICATE, EVENT_KEYS, _index, computation_event)
from .trade_twin_evidence import (ARRAYS, CHUNK_RECORDS, MAX_CHUNK_BYTES,
    MAX_MANIFEST_BYTES, book_manifest, verify_manifest, verify_chunk)

MAX_SET_BYTES = 64*1024*1024
MAX_RESPONSE_BYTES = 8*1024*1024
VIEW_EVENT = 'trade_twin_view_saved'


def _cancel(cancel):
    if cancel and cancel():
        raise InterruptedError('Saved trade-twin evidence canceled.')


def evidence_errors(function):
    from functools import wraps
    @wraps(function)
    def checked(*args,**kwargs):
        try:return function(*args,**kwargs)
        except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
            raise StateError('Original saved evidence is missing, corrupt or incompatible; no finance was recomputed.') from error
    return checked


def _number(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(label+' is outside its strict integer bounds.')
    return value


def _load(path, maximum, digest):
    if path.stat().st_size > maximum or file_hash(path) != digest:
        raise StateError('Original saved financial artifact is missing, changed or oversized.')
    with gzip.open(path,'rb') as stream:raw=stream.read(maximum+1)
    if len(raw)>maximum:
        raise StateError('Saved financial artifact expansion bound exceeded.')
    return json.loads(raw)


def _pack(value, maximum):
    raw=canonical(value).encode()
    if len(raw)>maximum:
        raise StateError('Saved evidence serialization bound exceeded; no subset retained.')
    return gzip.compress(raw,mtime=0)


def _unpack(value, maximum):
    if not isinstance(value,bytes) or len(value)>maximum+1024:
        raise StateError('Saved evidence chunk is malformed or oversized.')
    with gzip.GzipFile(fileobj=io.BytesIO(value),mode='rb') as stream:raw=stream.read(maximum+1)
    if len(raw)>maximum:
        raise StateError('Saved evidence chunk expansion bound exceeded.')
    return json.loads(raw)


def _bounded(value):
    if len(canonical(value).encode())>MAX_RESPONSE_BYTES:
        raise StateError('Saved evidence response bound exceeded; choose a smaller page.')
    return value


def _event(db,jid,kind):
    rows=db.execute('SELECT id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind=? ORDER BY id DESC LIMIT 2',(jid,kind)).fetchall()
    if len(rows)!=1 or rows[0]['bytes']>16384:
        raise StateError('Exactly one bounded original '+kind+' event is required.')
    return rows[0]['id'],json.loads(rows[0]['details'])


def original_preparation(original,db):
    from .trade_twin_source import _original_trial_event
    event_id,seal=_event(db,original.jid,'twin_preparation_sealed')
    trial=original.lab.store._trials.row(db,original.jid,0,'prepare')
    if (type(seal.get('attempt')) is not int or seal['attempt']!=trial['attempts']
            or seal.get('trial_id')!=trial['id'] or seal.get('payload_hash')!=original.payload_hash
            or seal.get('filename')!='attempt-'+str(trial['attempts']).zfill(6)+'.json.gz'
            or seal.get('plan_hash')!=original.report['plan_hash']
            or trial['state'] not in {'completed','checkpointed'} or trial['artifact_sha256']!=seal.get('sha256')):
        raise StateError('Original preparation seal or occurrence differs.')
    started=_original_trial_event(db,original.jid,'trial_computation_started',trial['id'],
        dict(trial_id=trial['id'],part=0,window='prepare',attempt=trial['attempts']))
    checkpoint=_original_trial_event(db,original.jid,'trial_checkpoint_saved',trial['id'],
        dict(trial_id=trial['id'],part=0,window='prepare',sha256=seal['sha256']),after_id=started)
    if checkpoint>=event_id:
        raise StateError('Original preparation checkpoint order differs.')
    attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
    path=original.folder/'preparation'/seal['filename'];value=_load(path,MAX_PART_BYTES,seal['sha256'])
    if (attempt is None or attempt['state']!='checkpointed' or attempt['artifact_sha256']!=seal['sha256']
            or attempt['computed_sha256']!=trial['computed_sha256'] or identity(value)!=trial['computed_sha256']):
        raise StateError('Original preparation computation differs.')
    plan=value['plan'];body={k:v for k,v in plan.items() if k!='plan_hash'}
    if plan['plan_hash']!=original.report['plan_hash'] or identity(body)!=plan['plan_hash'] or identity(plan['sources'])!=original.payload['source']['cohort_hash']:
        raise StateError('Original sealed plan or complete source cohort differs.')
    return path,value


class Originals:
    def __init__(self,lab,jid,building=None,owner=None,cancel=None):
        if not isinstance(jid,str) or re.fullmatch('[a-f0-9]{32}',jid) is None:
            raise ValueError('Choose an original saved comparison ID.')
        self.lab=lab;self.jid=jid;self.owner=owner;self.cancel=cancel;self.parts_used={};self.rows_used={}
        self.folder=lab.output_path(jid).parent/'twins';self.root_path=lab.output_path(jid)
        _cancel(cancel)
        with lab.store.db() as db:
            db.execute('BEGIN')
            job=db.execute('SELECT rowid AS input_rowid,id,status,kind,cancel_requested,substr(payload,1,?) payload,length(CAST(payload AS BLOB)) payload_bytes FROM jobs WHERE id=?',(MAX_MANIFEST_BYTES+1,jid)).fetchone()
            if job is not None and job['payload_bytes']>MAX_MANIFEST_BYTES:
                raise StateError('Original comparison input bound exceeded.')
            if job is None or job['kind']!='trade_twins':
                raise StateError('Choose an original trade-twin comparison.')
            self.payload=json.loads(job['payload']);self.input_hash=input_bytes_hash(db,job['input_rowid'])
            self.payload_hash=identity(self.payload)
            if building is None:
                if job['status']!='completed':
                    raise StateError('Complete saved financial evidence is available only after successful completion.')
                self.result_event_id,saved=_event(db,jid,'result_saved');self.root_sha=saved.get('sha256')
                wrapped=_load(self.root_path,MAX_MANIFEST_BYTES,self.root_sha)
                if (wrapped.get('job_id')!=jid or wrapped.get('kind')!='trade_twins' or wrapped.get('payload_hash')!=self.payload_hash
                        or wrapped.get('core_hash')!=self.payload.get('core_hash')):
                    raise StateError('Original comparison result/input identity differs.')
                self.report=wrapped['report'];reference=wrapped['financial_manifest']
                self.manifest_event_id,publication=_event(db,jid,'twin_financial_manifest_saved')
                if publication!=reference or self.manifest_event_id+1!=self.result_event_id:
                    raise StateError('Original financial manifest/result publication order differs.')
                filename=reference.get('filename','')
                if re.fullmatch('pub-[a-f0-9]{32}\\.manifest\\.json\\.gz',filename) is None:
                    raise StateError('Original financial manifest location differs.')
                self.manifest_path=self.folder/'results'/filename;self.manifest_sha=reference['sha256']
                self.manifest=_load(self.manifest_path,MAX_MANIFEST_BYTES,self.manifest_sha)
                if identity(self.manifest)!=reference['content_hash']:
                    raise StateError('Original financial manifest content differs.')
            else:
                lab.store._trials.owned(db,jid,owner)
                if job['cancel_requested']:
                    raise InterruptedError('Canceled before financial evidence view construction.')
                self.report,self.manifest=building;self.root_sha=None;self.manifest_path=None;self.manifest_sha=None
                self.result_event_id=self.manifest_event_id=None
            if (self.payload.get('twin_protocol',{}).get('book_evidence_version')!=1
                    or self.payload['twin_protocol'].get('version')!=2):
                raise StateError('Original bounded inspection evidence is unavailable. The saved summary remains readable; create a compatible new comparison.')
            self.report_hash=identity(self.report);self.manifest_hash=identity(self.manifest)
            if (self.report.get('report_type')!='trade_twins' or self.report.get('manifest_hash')!=self.manifest_hash
                    or self.manifest.get('job_id')!=jid or self.manifest.get('payload_hash')!=self.payload_hash
                    or self.manifest.get('plan_hash')!=self.report.get('plan_hash')
                    or self.manifest.get('source_authority_hash')!=self.payload['twin_parent']['authority_hash']
                    or self.manifest.get('work_partition')!=self.payload['work_partition']):
                raise StateError('Original financial manifest belongs to different frozen inputs.')
            self.headers=self.manifest['parts'];expected=0 if self.manifest['ineligible'] else self.payload['work_partition']['part_count']
            if not isinstance(self.headers,list) or len(self.headers)!=expected or expected>10000:
                raise StateError('Original financial manifest is incomplete.')
            for ordinal,header in enumerate(self.headers):
                if (not isinstance(header,dict) or set(header)!=EVENT_KEYS or type(header['part']) is not int or header['part']!=ordinal
                        or header['payload_hash']!=self.payload_hash or header['plan_hash']!=self.report['plan_hash']):
                    raise StateError('Original financial part sequence differs.')
            self.preparation_event_id,seal=_event(db,jid,'twin_preparation_sealed')
            if (type(seal.get('attempt')) is not int or seal['attempt']<1
                    or seal.get('filename')!='attempt-'+str(seal['attempt']).zfill(6)+'.json.gz'
                    or seal.get('payload_hash')!=self.payload_hash or seal.get('plan_hash')!=self.report['plan_hash']
                    or seal.get('trial_id')!=identity(dict(job_id=jid,part=0,window='prepare'))
                    or self.manifest_event_id is not None and self.preparation_event_id>=self.manifest_event_id):
                raise StateError('Original preparation must precede financial publication.')
            self.preparation_marker=identity(seal);self.preparation_sha=seal['sha256'];self.preparation_path=self.folder/'preparation'/seal['filename']
            if self.preparation_path.stat().st_size>MAX_PART_BYTES or file_hash(self.preparation_path)!=self.preparation_sha:
                raise StateError('Original preparation artifact is missing or changed.')
        self.header=dict(version=1,job_id=jid,payload_hash=self.payload_hash,input_raw_sha256=self.input_hash,
                         report_hash=self.report_hash,manifest_hash=self.manifest_hash,plan_hash=self.report['plan_hash'],
                         expected_sets=0 if self.manifest['ineligible'] else TOTAL_SETS,
                         source_count=self.payload['source']['source_count'],book_count=self.report['unique_committed_books'])

    def part(self,db,part,force=False):
        _number(part,0,len(self.headers)-1,'Financial part')
        _index(db,'trade_twin_part_event_index',PART_INDEX)
        rows=db.execute("SELECT id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY trade_twin_part_event_index WHERE "+PART_PREDICATE+" AND entity_id=? AND json_extract(details,'$.part')=? ORDER BY id LIMIT 2",(self.jid,part)).fetchall()
        if len(rows)!=1 or rows[0]['bytes']>16384:
            raise StateError('Original financial part event is missing or duplicated.')
        event=rows[0];header=json.loads(event['details'])
        if header!=self.headers[part]:
            raise StateError('Original financial part differs from its committed result manifest.')
        if self.manifest_event_id is not None and event['id']>=self.manifest_event_id:
            raise StateError('An original financial part must precede final manifest publication.')
        indexed=db.execute('SELECT event_id,details FROM trade_twin_part_index WHERE job_id=? AND part=?',(self.jid,part)).fetchone()
        if indexed is None or indexed['event_id']!=event['id'] or json.loads(indexed['details'])!=header:
            raise StateError('Financial part index differs from the original commit.')
        if part in self.parts_used and self.parts_used[part]!=event['id']:
            raise StateError('Original part event changed during inspection.')
        filename=header['filename']
        if re.fullmatch(r'part-\d{6}-attempt-\d{6,19}\.json\.gz',filename) is None:
            raise StateError('Original financial part location differs.')
        path=self.folder/'parts'/filename
        if (force or part not in self.parts_used) and (path.stat().st_size>MAX_PART_BYTES or file_hash(path)!=header['sha256']):
            raise StateError('Original financial part bytes changed.')
        self.parts_used[part]=event['id']
        return header,event['id'],path

    def row_original(self,db,ordinal,policy,digest,part,attempt):
        header,commit,_=self.part(db,part)
        trial=self.lab.store._trials.row(db,self.jid,ordinal,policy)
        if (trial['state'] not in {'checkpointed','completed'} or trial['attempts']!=attempt or attempt!=header['attempt']
                or trial['artifact_sha256']!=header['sha256'] or trial['computed_sha256']!=digest
                or not header['start']<=ordinal<header['stop']):
            raise StateError('Saved set differs from its original completed occurrence.')
        original_attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],attempt)).fetchone()
        if original_attempt is None or original_attempt['state']!='checkpointed' or original_attempt['computed_sha256']!=digest or original_attempt['artifact_sha256']!=header['sha256']:
            raise StateError('Original set computation attempt changed.')
        _index(db,'trade_twin_trial_event_index',TRIAL_INDEX)
        starts=db.execute("SELECT id,details FROM events INDEXED BY trade_twin_trial_event_index WHERE "+TRIAL_PREDICATE+" AND entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=? AND json_extract(details,'$.attempt')=? ORDER BY id LIMIT 2",(self.jid,trial['id'],attempt)).fetchall()
        expected=dict(trial_id=trial['id'],part=ordinal,window=policy,attempt=attempt)
        if len(starts)!=1 or json.loads(starts[0]['details'])!=expected or starts[0]['id']<=self.preparation_event_id:
            raise StateError('Original set start event or sealed-plan order changed.')
        computed=computation_event(db,self.jid,trial,starts[0]['id'])
        checkpoints=db.execute("SELECT id,details FROM events INDEXED BY trade_twin_trial_event_index WHERE "+TRIAL_PREDICATE+" AND entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.trial_id')=? AND id>? ORDER BY id LIMIT 2",(self.jid,trial['id'],computed)).fetchall()
        expected=dict(trial_id=trial['id'],part=ordinal,window=policy,sha256=header['sha256'])
        if len(checkpoints)!=1 or json.loads(checkpoints[0]['details'])!=expected or checkpoints[0]['id']>=commit:
            raise StateError('Original set checkpoint/part order changed.')
        self.rows_used[ordinal,policy]=(digest,part,attempt)

    def guard(self):
        _cancel(self.cancel)
        with self.lab.store.db() as db:
            db.execute('BEGIN')
            job=db.execute('SELECT rowid AS input_rowid,id,status,kind,cancel_requested,substr(payload,1,?) payload,length(CAST(payload AS BLOB)) payload_bytes FROM jobs WHERE id=?',(MAX_MANIFEST_BYTES+1,self.jid)).fetchone()
            if job is not None and job['payload_bytes']>MAX_MANIFEST_BYTES:
                raise StateError('Original comparison input bound exceeded.')
            if job is None or identity(json.loads(job['payload']))!=self.payload_hash or input_bytes_hash(db,job['input_rowid'])!=self.input_hash:
                raise StateError('Original comparison inputs changed during inspection.')
            if self.owner is not None:
                self.lab.store._trials.owned(db,self.jid,self.owner)
                if job['cancel_requested']:
                    raise InterruptedError('Canceled before financial evidence publication.')
            else:
                event_id,saved=_event(db,self.jid,'result_saved')
                manifest_id,publication=_event(db,self.jid,'twin_financial_manifest_saved')
                if (job['status']!='completed' or event_id!=self.result_event_id or manifest_id!=self.manifest_event_id
                        or publication.get('sha256')!=self.manifest_sha or publication.get('content_hash')!=self.manifest_hash
                        or saved.get('sha256')!=self.root_sha or file_hash(self.root_path)!=self.root_sha or file_hash(self.manifest_path)!=self.manifest_sha):
                    raise StateError('Original comparison publication changed during inspection.')
            preparation_id,seal=_event(db,self.jid,'twin_preparation_sealed')
            if preparation_id!=self.preparation_event_id or identity(seal)!=self.preparation_marker or file_hash(self.preparation_path)!=self.preparation_sha:
                raise StateError('Original preparation changed during saved inspection.')
            for part in list(self.parts_used):self.part(db,part,force=True)
            for (ordinal,policy),(digest,part,attempt) in list(self.rows_used.items()):self.row_original(db,ordinal,policy,digest,part,attempt)


def build_view(original):
    """Stream committed parts into a new derived seek view; originals stay intact."""
    folder=original.folder/'views';folder.mkdir(parents=True,exist_ok=True)
    filename='view-'+uuid.uuid4().hex+'.sqlite3';temporary=folder/(filename+'.tmp');destination=folder/filename
    with original.lab.store.db() as connection:
        connection.execute('BEGIN');original_preparation(original,connection)
    cache=sqlite3.connect(temporary);completed=False;rows=books=0
    try:
        cache.executescript('PRAGMA journal_mode=OFF; CREATE TABLE header(value TEXT NOT NULL); CREATE TABLE sets(policy TEXT NOT NULL,ordinal INTEGER NOT NULL,part INTEGER NOT NULL,attempt INTEGER NOT NULL,row_hash TEXT NOT NULL,value BLOB NOT NULL,PRIMARY KEY(policy,ordinal)); CREATE TABLE books(book_key TEXT PRIMARY KEY,part INTEGER NOT NULL,book_offset INTEGER NOT NULL,book_sha256 TEXT NOT NULL,evidence_sha256 TEXT NOT NULL,inputs TEXT NOT NULL,evidence BLOB NOT NULL); CREATE TABLE chunks(book_key TEXT NOT NULL,kind TEXT NOT NULL,ordinal INTEGER NOT NULL,value BLOB NOT NULL,PRIMARY KEY(book_key,kind,ordinal));')
        cache.execute('INSERT INTO header VALUES(?)',(canonical(original.header),))
        for part,header in enumerate(original.headers):
            _cancel(original.cancel)
            with original.lab.store.db() as db:
                db.execute('BEGIN');_,_,path=original.part(db,part)
                value=_load(path,MAX_PART_BYTES,header['sha256'])
                if (value.get('format')!=2 or value.get('job_id')!=original.jid or value.get('payload_hash')!=original.payload_hash
                        or any(value.get(k)!=header[k] for k in ['part','start','stop','attempt','plan_hash'])
                        or len(value.get('sets',[]))!=2*(header['stop']-header['start']) or len(value.get('books',[]))!=header['book_count']):
                    raise StateError('Original complete financial part shape differs.')
                for row in value['sets']:
                    _cancel(original.cancel);outcome=CanonicalOutcome.model_validate(row['outcome']);ordinal=outcome.set_index;policy=outcome.policy
                    if outcome.plan_hash!=original.header['plan_hash'] or outcome.seed!=original.payload['seed'] or outcome.trade_count!=original.header['source_count'] or len(row['members'])!=outcome.trade_count or len(row['draw']['matches'])!=outcome.trade_count:
                        raise StateError('Original financial cohort or assignment count differs.')
                    digest=identity(row);original.row_original(db,ordinal,policy,digest,part,header['attempt'])
                    cache.execute('INSERT INTO sets VALUES(?,?,?,?,?,?)',(policy,ordinal,part,header['attempt'],digest,_pack(row,MAX_SET_BYTES)));rows+=1
                bindings=[]
                for offset,entry in enumerate(value['books']):
                    _cancel(original.cancel)
                    if identity(entry['book'])!=entry['sha256'] or identity(entry['inputs'])!=entry['key'] or book_manifest(entry['book'],original.cancel)!=entry['evidence']:
                        raise StateError('Original book or complete inspection evidence differs.')
                    evidence=verify_manifest(entry['evidence'],entry['evidence_sha256'],entry['sha256'])
                    cache.execute('INSERT INTO books VALUES(?,?,?,?,?,?,?)',(entry['key'],part,offset,entry['sha256'],entry['evidence_sha256'],canonical(entry['inputs']),_pack(evidence,MAX_MANIFEST_BYTES)))
                    bindings.append(dict(book_key=entry['key'],book_offset=offset,book_sha256=entry['sha256']));books+=1
                    for kind in ARRAYS:
                        records=entry['book'][kind]
                        for index,start in enumerate(range(0,len(records),CHUNK_RECORDS)):
                            chunk=verify_chunk(evidence,kind,index,records[start:start+CHUNK_RECORDS])
                            cache.execute('INSERT INTO chunks VALUES(?,?,?,?)',(entry['key'],kind,index,_pack(chunk,MAX_CHUNK_BYTES)))
                if identity(sorted(bindings,key=lambda b:b['book_key']))!=header['book_bindings_sha256']:
                    raise StateError('Original book binding sequence changed.')
            # Retain the bounded20000 original digest bindings for the closing fence.
            cache.commit()
        if rows!=2*original.header['expected_sets'] or books!=original.header['book_count']:
            raise StateError('Saved evidence view is missing original sets or unique books.')
        cache.commit();original.guard();cache.close();cache=None
        temporary.replace(destination);completed=True
        return dict(filename=filename,sha256=file_hash(destination),metadata_sha256=identity(original.header),
                    report_hash=original.report_hash,manifest_hash=original.manifest_hash,payload_hash=original.payload_hash,
                    root_sha256=original.root_sha,set_rows=rows,book_rows=books,version=1)
    finally:
        if cache is not None:
            cache.close()
        if not completed and temporary.exists():
            assert temporary.resolve().is_relative_to(folder.resolve());temporary.unlink()


@contextmanager
def saved_view(lab,jid):
    cache=None
    try:
        original=Originals(lab,jid)
        with lab.store.db() as db:
            rows=db.execute('SELECT substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind=? ORDER BY id DESC LIMIT 1',(jid,VIEW_EVENT)).fetchall()
        if not rows or rows[0]['bytes']>16384:
            raise StateError('Build the saved inspection view from verified original financial evidence.')
        view=json.loads(rows[0]['details'])
        if (view.get('report_hash')!=original.report_hash or view.get('manifest_hash')!=original.manifest_hash
                or view.get('payload_hash')!=original.payload_hash or view.get('metadata_sha256')!=identity(original.header)
                or view.get('root_sha256')!=original.root_sha):
            raise StateError('Derived financial view belongs to a different original comparison.')
        filename=view.get('filename','')
        if re.fullmatch('view-[a-f0-9]{32}\\.sqlite3',filename) is None:
            raise StateError('Saved financial view location differs.')
        path=(original.folder/'views'/filename).resolve()
        # Each requested row/chunk is proved against originals. Hashing the whole
        # potentially large derived database on every page is unnecessary.
        cache=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);cache.row_factory=sqlite3.Row
        cache.execute('PRAGMA query_only=ON');cache.execute('BEGIN')
        header=cache.execute('SELECT substr(value,1,65537),length(CAST(value AS BLOB)) FROM header').fetchall()
        if len(header)!=1 or header[0][1]>65536 or json.loads(header[0][0])!=original.header:
            raise StateError('Saved financial view header differs from original evidence.')
        if cache.execute('SELECT COUNT(*) FROM sets').fetchone()[0]!=2*original.header['expected_sets']:
            raise StateError('Saved financial view has missing or surplus set rows.')
        yield original,cache
        original.guard()
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Saved financial inspection evidence is missing, corrupt or incompatible; no financial result was recomputed.') from error
    finally:
        if cache is not None:
            cache.close()


@evidence_errors
def repair_view(lab,jid):
    original=Originals(lab,jid);view=build_view(original);original.guard()
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        current=db.execute('SELECT status,payload FROM jobs WHERE id=?',(jid,)).fetchone();_,saved=_event(db,jid,'result_saved')
        if current is None or current['status']!='completed' or identity(json.loads(current['payload']))!=original.payload_hash or saved.get('sha256')!=original.root_sha or file_hash(original.root_path)!=original.root_sha:
            raise StateError('Original publication changed before view repair.')
        lab.store.event(VIEW_EVENT,jid,view,db);db.execute('COMMIT')
    return dict(job_id=jid,view=view,financial_recomputations=0)


def _set(original,cache,policy,ordinal):
    if policy not in EXECUTION_POLICIES:
        raise ValueError('Choose a declared financial interpretation.')
    _number(ordinal,0,TOTAL_SETS-1,'Set ordinal')
    record=cache.execute('SELECT policy,ordinal,part,attempt,row_hash,substr(value,1,?) value,length(value) bytes FROM sets WHERE policy=? AND ordinal=?',(MAX_SET_BYTES+1025,policy,ordinal)).fetchone()
    if record is None:
        raise StateError('Original financial set is not present in this complete saved comparison.')
    if record['bytes']>MAX_SET_BYTES+1024:
        raise StateError('Saved set expansion bound exceeded.')
    value=_unpack(record['value'],MAX_SET_BYTES);digest=identity(value);outcome=CanonicalOutcome.model_validate(value['outcome'])
    if (digest!=record['row_hash'] or outcome.set_index!=ordinal or outcome.policy!=policy or outcome.plan_hash!=original.header['plan_hash']
            or outcome.seed!=original.payload['seed'] or outcome.trade_count!=original.header['source_count']
            or len(value['members'])!=outcome.trade_count or len(value['draw']['matches'])!=outcome.trade_count):
        raise StateError('Saved set content differs from its original complete cohort.')
    with original.lab.store.db() as db:
        db.execute('BEGIN');original.row_original(db,ordinal,policy,digest,record['part'],record['attempt'])
    return value,record['part']


def sets_page(lab,jid,policy,offset=0,limit=25):
    _number(offset,0,TOTAL_SETS,'Set offset');_number(limit,1,100,'Set page size')
    if policy not in EXECUTION_POLICIES:
        raise ValueError('Choose a declared financial interpretation.')
    with saved_view(lab,jid) as (original,cache):
        total=original.header['expected_sets'];rows=[]
        for ordinal in range(offset,min(total,offset+limit)):
            value,part=_set(original,cache,policy,ordinal)
            rows.append(dict(outcome=value['outcome'],draw_hash=value['draw']['draw_hash'],member_count=len(value['members']),part=part))
        return _bounded(dict(job_id=jid,policy=policy,rows=rows,pagination=dict(offset=offset,limit=limit,total=total,next_offset=offset+len(rows) if offset+len(rows)<total else None)))


def members_page(lab,jid,policy,ordinal,offset=0,limit=25):
    _number(offset,0,20000,'Member offset');_number(limit,1,100,'Member page size')
    with saved_view(lab,jid) as (original,cache):
        value,_=_set(original,cache,policy,ordinal);total=len(value['members'])
        rows=[dict(index=index,member=value['members'][index],assignment=value['draw']['matches'][index]) for index in range(offset,min(total,offset+limit))]
        return _bounded(dict(job_id=jid,policy=policy,set_index=ordinal,outcome=value['outcome'],rows=rows,
            pagination=dict(offset=offset,limit=limit,total=total,next_offset=offset+len(rows) if offset+len(rows)<total else None)))


def _book(original,cache,policy,ordinal,member_index):
    value,part=_set(original,cache,policy,ordinal);_number(member_index,0,len(value['members'])-1,'Original member')
    member=value['members'][member_index];match=value['draw']['matches'][member_index]
    record=cache.execute('SELECT book_key,part,book_offset,book_sha256,evidence_sha256,substr(inputs,1,?) inputs,length(CAST(inputs AS BLOB)) input_bytes,substr(evidence,1,?) evidence,length(evidence) bytes FROM books WHERE book_key=?',(MAX_MANIFEST_BYTES+1,MAX_MANIFEST_BYTES+1025,member['book_key'])).fetchone()
    if (record is None or record['part']>part or record['book_sha256']!=member['book_sha256'] or record['evidence_sha256']!=member['book_evidence_sha256']
            or record['input_bytes']>MAX_MANIFEST_BYTES or record['bytes']>MAX_MANIFEST_BYTES+1024):
        raise StateError('Requested original book or inspection binding is unavailable.')
    inputs=json.loads(record['inputs']);evidence=verify_manifest(_unpack(record['evidence'],MAX_MANIFEST_BYTES),member['book_evidence_sha256'],member['book_sha256'])
    if identity(inputs)!=member['book_key'] or inputs.get('match')!=match or inputs.get('policy')!=policy or member['source_id']!=match['source_id']:
        raise StateError('Saved book belongs to another original assignment or interpretation.')
    with original.lab.store.db() as db:
        db.execute('BEGIN');header,_,_=original.part(db,record['part'])
        bindings=[dict(row) for row in db.execute('SELECT book_key,book_offset,book_sha256 FROM trade_twin_book_index WHERE job_id=? AND part=? ORDER BY book_key',(original.jid,record['part']))]
        if len(bindings)!=header['book_count'] or identity(bindings)!=header['book_bindings_sha256'] or dict(book_key=member['book_key'],book_offset=record['book_offset'],book_sha256=member['book_sha256']) not in bindings:
            raise StateError('Original book index differs from its committed part binding.')
    return member,match,evidence


def book_page(lab,jid,policy,ordinal,member_index,kind='ledger',offset=0,limit=25):
    if kind not in ARRAYS:
        raise ValueError('Choose ledger, equity, rejected or encounters evidence.')
    _number(offset,0,2**31-1,'Financial record offset');_number(limit,1,100,'Financial record page size')
    with saved_view(lab,jid) as (original,cache):
        member,match,evidence=_book(original,cache,policy,ordinal,member_index);total=evidence['counts'][kind];rows=[]
        end=min(total,offset+limit)
        for index in range(offset//CHUNK_RECORDS,(end+CHUNK_RECORDS-1)//CHUNK_RECORDS):
            record=cache.execute('SELECT substr(value,1,?) value,length(value) bytes FROM chunks WHERE book_key=? AND kind=? AND ordinal=?',(MAX_CHUNK_BYTES+1025,member['book_key'],kind,index)).fetchone()
            if record is None or record['bytes']>MAX_CHUNK_BYTES+1024:
                raise StateError('Original financial evidence chunk is missing or oversized.')
            chunk=verify_chunk(evidence,kind,index,_unpack(record['value'],MAX_CHUNK_BYTES))
            rows.extend(chunk[max(0,offset-index*CHUNK_RECORDS):min(len(chunk),end-index*CHUNK_RECORDS)])
        return _bounded(dict(job_id=jid,policy=policy,set_index=ordinal,member_index=member_index,member=member,assignment=match,
            book=evidence['scalar_fields'],kind=kind,rows=rows,counts=evidence['counts'],
            pagination=dict(offset=offset,limit=limit,total=total,next_offset=offset+len(rows) if offset+len(rows)<total else None)))


def _tabular_exports(original,archive):
    import csv
    import html
    folder=original.folder/'exports'/('tables-'+uuid.uuid4().hex);folder.mkdir(parents=True)
    names=['sets.csv','members.csv','books.csv','financial-records.csv'];handles=[];writers={}
    try:
        for name in names:
            handle=(folder/name).open('w',encoding='utf-8',newline='');handles.append(handle);writers[name]=csv.writer(handle)
        writers['sets.csv'].writerow(['policy','set_index','state','net_profit','trade_count','error','draw_hash','original_part'])
        writers['members.csv'].writerow(['policy','set_index','member_index','source_id','book_key','book_sha256','book_evidence_sha256','symbol','side','quantity','entry_at','cutoff_at','exact_assignment_json'])
        writers['books.csv'].writerow(['book_key','book_sha256','policy','source_id','status','net_profit','original_part','exact_scalar_fields_json'])
        writers['financial-records.csv'].writerow(['book_key','policy','source_id','kind','record_index','timestamp','event','exact_record_json'])
        set_rows=member_rows=book_rows=record_rows=0
        for part in range(len(original.headers)):
            _cancel(original.cancel)
            with original.lab.store.db() as db:
                db.execute('BEGIN');header,_,path=original.part(db,part)
            value=_load(path,MAX_PART_BYTES,header['sha256'])
            for row in value['sets']:
                outcome=row['outcome'];policy=outcome['policy'];ordinal=outcome['set_index']
                writers['sets.csv'].writerow([policy,ordinal,outcome['state'],outcome['net_profit'],outcome['trade_count'],outcome['error'],row['draw']['draw_hash'],part]);set_rows+=1
                for index,(member,match) in enumerate(zip(row['members'],row['draw']['matches'])):
                    writers['members.csv'].writerow([policy,ordinal,index,member['source_id'],member['book_key'],member['book_sha256'],member['book_evidence_sha256'],match['symbol'],match['side'],match['quantity'],match['entry_at'],match['cutoff_at'],canonical(match)]);member_rows+=1
            for entry in value['books']:
                inputs=entry['inputs'];book=entry['book'];source=inputs['match']['source_id'];policy=inputs['policy']
                writers['books.csv'].writerow([entry['key'],entry['sha256'],policy,source,book['status'],book['net_profit'],part,canonical(entry['evidence']['scalar_fields'])]);book_rows+=1
                for kind in ARRAYS:
                    for index,record in enumerate(book[kind]):
                        if index%100==0:
                            _cancel(original.cancel)
                        writers['financial-records.csv'].writerow([entry['key'],policy,source,kind,index,record.get('timestamp',record.get('date','')),record.get('kind',kind),canonical(record)]);record_rows+=1
        for handle in handles:handle.close()
        handles.clear()
        for name in names:archive.write(folder/name,name)
        escape=lambda value:html.escape(str(value))
        rows=[]
        for policy,summary in original.report['summaries'].items():
            fields=[policy,summary['state'],str(summary['complete_sets'])+' / '+str(summary['expected_sets']),summary['exceedances'],summary['real_profit'],
                summary['raw_exceedance_fraction'],summary['plus_one_diagnostic'],summary['monte_carlo_interval_95'],'Unavailable' if summary['adapted_pass'] is None else 'Pass' if summary['adapted_pass'] else 'Fail']
            rows.append('<tr>'+''.join('<td>'+escape(value)+'</td>' for value in fields)+'</tr>')
        document='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Saved trade-twin comparison</title><style>html{color-scheme:dark}body{background:#0c1322;color:#e0e7f3;font:16px/1.6 system-ui,sans-serif;max-width:1200px;margin:2rem auto;padding:1rem}a{color:#62d8e9}table{border-collapse:collapse}td,th{border:1px solid #36475f;padding:.6rem;text-align:left}section{overflow:auto}code{overflow-wrap:anywhere}</style><h1>Original saved trade-twin comparison</h1>'
        document+='<p>Original comparison <code>'+escape(original.jid)+'</code>. Canonical original profit: <code>'+escape(original.payload['source']['source_profit'])+'</code>. Original reported profit: <code>'+escape(original.payload['source']['reported_source_profit'])+'</code>.</p>'
        document+='<section><table><thead><tr>'+''.join('<th>'+title+'</th>' for title in ['Interpretation','State','Complete / required','Ties or better','Exact source profit','Raw fraction','Plus-one diagnostic','Conditional95% interval','Adapted gate'])+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></section>'
        document+='<p>Strict grading counts ties. Fewer than500 of10000 complete random sets must tie or beat the original. These diagnostics use independently financed books, not a shared tradable portfolio. Conditional Monte Carlo uncertainty does not correct strategy selection or establish future profitability.</p>'
        document+='<p><a href="sets.csv">Every financial set</a> · <a href="members.csv">Every source member</a> · <a href="books.csv">Every unique book</a> · <a href="financial-records.csv">Every financial event</a> · <a href="frozen-inputs.json">All frozen assumptions</a> · <a href="original-source-account.json">Original source account</a></p>'
        document+='<p>The original compressed parts retain all sets, assignments, manifests and complete/failed books. Amounts are canonical saved strings; spreadsheet software may round CSV numbers. Original JSON is authoritative. This standalone report uses no network dependency.</p>'
        document+='<p>Source: <a href="https://www.youtube.com/watch?v=z97PnFIPoFg">AI Pathways / Brendan video</a>. This is an explicit US-stock/ETF adaptation; private host-engine parity and historical short availability remain unverified.</p></html>'
        archive.writestr('standalone-report.html',document)
        return dict(sets=set_rows,members=member_rows,books=book_rows,financial_records=record_rows)
    finally:
        for handle in handles:handle.close()
        for name in names:
            path=folder/name
            if path.exists():
                assert path.resolve().parent==folder.resolve();path.unlink()
        folder.rmdir()


@evidence_errors
def export_archive(lab,jid):
    """Create a complete verified ZIP on disk, then let HTTP stream that file."""
    original=Originals(lab,jid);lab.store.verify_trial_plan(jid)
    folder=original.folder/'exports';folder.mkdir(parents=True,exist_ok=True)
    temporary=folder/('export-'+uuid.uuid4().hex+'.tmp');destination=temporary.with_suffix('.zip')
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
            archive.writestr('frozen-inputs.json',canonical(original.payload))
            archive.write(original.root_path,'original-result.json.gz');archive.write(original.manifest_path,'financial-manifest.json.gz')
            with lab.store.db() as db:
                db.execute('BEGIN');prep,prepared=original_preparation(original,db)
                archive.write(prep,'original-preparation.json.gz')
            trial_count=0
            with archive.open('original-trials.jsonl','w',force_zip64=True) as stream:
                with lab.store.db() as db:
                    db.execute('BEGIN')
                    for row in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part,window',(jid,)):
                        stream.write((canonical(dict(row))+'\n').encode());trial_count+=1
            if trial_count!=2*TOTAL_SETS+1:
                raise StateError('Original exported occurrence cohort is incomplete.')
            with archive.open('original-attempts.jsonl','w',force_zip64=True) as stream:
                with lab.store.db() as db:
                    for row in db.execute('SELECT a.* FROM trial_attempts a JOIN trial_plans p ON p.id=a.trial_id WHERE p.job_id=? ORDER BY a.trial_id,a.ordinal',(jid,)):stream.write((canonical(dict(row))+'\n').encode())
            with archive.open('original-journal.jsonl','w',force_zip64=True) as stream:
                with lab.store.db() as db:
                    for row in db.execute('SELECT * FROM events WHERE entity_id=? ORDER BY id',(jid,)):stream.write((canonical(dict(row))+'\n').encode())
            for part in range(len(original.headers)):
                with lab.store.db() as db:
                    db.execute('BEGIN');header,_,path=original.part(db,part)
                    value=_load(path,MAX_PART_BYTES,header['sha256'])
                    for row in value['sets']:
                        outcome=row['outcome'];original.row_original(db,outcome['set_index'],outcome['policy'],identity(row),part,header['attempt'])
                archive.write(path,'original-parts/'+path.name)
            parent=original.payload['twin_parent'];parent_job=lab.store.job(parent['job_id'])
            source=lab.report(parent['job_id'],None if parent_job['kind']=='experiment' else parent['part'])
            if identity(source)!=original.payload['source']['report_hash']:
                raise StateError('Original selected source account differs from the exported baseline.')
            archive.writestr('original-source-account.json',canonical(source))
            tabular=_tabular_exports(original,archive)
            original.guard()
            archive.writestr('COMPLETE.json',canonical(dict(version=1,job_id=jid,report_hash=original.report_hash,manifest_hash=original.manifest_hash,
                payload_hash=original.payload_hash,parts=len(original.headers),financial_occurrences=original.report['financial_occurrences'],
                original_trials=trial_count,unique_books=original.report['unique_committed_books'],tabular_rows=tabular,financial_recomputations=0,
                interpretation='Original compressed parts retain every set/draw/member and every unique complete or failed book. No summary/page truncation.')))
        original.guard();temporary.replace(destination)
        return destination
    finally:
        if temporary.exists():
            assert temporary.resolve().is_relative_to(folder.resolve());temporary.unlink()
