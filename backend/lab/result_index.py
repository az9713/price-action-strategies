"""Content-addressed derived result views. Originals remain the financial evidence."""
from contextlib import contextmanager
from pathlib import Path
import gzip,hashlib,json,os,re,sqlite3,uuid
from .config import canonical,identity
from .job_index import small
from .store import StateError

CHUNK=65536
class ViewUnavailable(StateError):pass

def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(CHUNK):digest.update(chunk)
    return digest.hexdigest()

def original_hash(path):
    try:return file_hash(path)
    except OSError as error:raise StateError('Original saved result artifact is unavailable.') from error

def input_bytes_hash(db,rowid):
    digest=hashlib.sha256()
    with db.blobopen('jobs','payload',rowid,readonly=True) as blob:
        while chunk:=blob.read(CHUNK):digest.update(chunk)
    return digest.hexdigest()

def row_projection(row):
    if not isinstance(row,dict) or type(row.get('part')) is not int or row['part']<0:raise StateError('Saved result row has no supported part identity.')
    value={};omitted=[]
    for key,item in row.items():
        if small(item):value[key]=item
        else:omitted.append(key)
    if isinstance(row.get('configurations'),list):value.update(configuration_count=len(row['configurations']),is_portfolio=True)
    if omitted:value['omitted_fields']=omitted
    while len(canonical(value).encode())>16384:
        key=max((k for k in value if k not in {'part','config_id','report_sha256','omitted_fields'}),key=lambda k:len(canonical(value[k]).encode()))
        value.pop(key);omitted.append(key);value['omitted_fields']=omitted
    return value

def summary_projection(value,jid):
    meta={};omitted=[]
    for key,item in value.items():
        if key in {'rows','report','search_statistics','search_screen'}:continue
        if small(item):meta[key]=item
        else:omitted.append(key)
    report=value.get('report');meta.update(job_id=jid,has_report=isinstance(report,dict),row_count=len(value.get('rows',[])),projection_policy=1)
    if isinstance(report,dict):meta['report']=dict(report_type=report.get('report_type'))
    for key in ['search_statistics','search_screen']:
        item=value.get(key)
        if not isinstance(item,dict):continue
        projected={k:v for k,v in item.items() if k!='accounts' and (small(v) or (k=='groups' and isinstance(v,list) and len(v)<=128 and all(small(group) for group in v) and len(canonical(v).encode())<=24576))}
        excluded=[k for k in item if k!='accounts' and k not in projected]
        if excluded:projected['omitted_fields']=excluded
        projected.update(accounts=[],accounts_total=len(item.get('accounts',[])),accounts_complete=not item.get('accounts'),accounts_page_url='/api/jobs/'+jid+'/result-'+('statistics' if key=='search_statistics' else 'screen'))
        meta[key]=projected
    if omitted:meta['omitted_fields']=omitted
    while len(canonical(meta).encode())>49152:
        key=max((k for k in meta if k not in {'job_id','kind','has_report','row_count','report','omitted_fields','projection_policy'}),key=lambda k:len(canonical(meta[k]).encode()))
        meta.pop(key);omitted.append(key);meta['omitted_fields']=omitted
    return meta

class ResultIndex:
    def __init__(self,lab):self.lab=lab;self.store=lab.store

    def folder(self,jid):
        base=(self.lab.root/'data/jobs').resolve();folder=(base/jid).resolve()
        if not folder.is_relative_to(base) or folder==base:raise StateError('Invalid saved result location.')
        return folder

    def event(self,db,jid,kind):
        row=db.execute('SELECT details FROM events WHERE entity_id=? AND kind=? ORDER BY id DESC LIMIT 1',(jid,kind)).fetchone()
        if row is None:return None
        try:
            value=json.loads(row['details'])
            if not isinstance(value,dict):raise ValueError()
            return value
        except (ValueError,TypeError) as error:raise StateError('Saved result event is malformed.') from error

    def build(self,jid,value,cancel=None):
        folder=self.folder(jid);folder.mkdir(parents=True,exist_ok=True);root=folder/'result.json.gz'
        with self.store.db() as db:
            db.execute('BEGIN')
            job=db.execute('SELECT rowid AS input_rowid,id,payload FROM jobs WHERE id=?',(jid,)).fetchone()
            saved=self.event(db,jid,'result_saved')
            if job is None or saved is None:raise StateError('Original saved result evidence is missing.')
            try:payload=json.loads(job['payload']);payload_hash=identity(payload)
            except (ValueError,TypeError) as error:raise StateError('Original saved inputs are malformed.') from error
            if value.get('job_id')!=jid or value.get('payload_hash')!=payload_hash or original_hash(root)!=saved.get('sha256'):raise StateError('Original saved result/input identity differs.')
            raw_hash=input_bytes_hash(db,job['input_rowid']);root_hash=saved['sha256']
        meta=summary_projection(value,jid);temporary=folder/('.view-'+uuid.uuid4().hex+'.tmp');db=None
        try:
            db=sqlite3.connect(temporary)
            db.executescript('PRAGMA journal_mode=OFF; CREATE TABLE header(value TEXT NOT NULL); CREATE TABLE rows(part INTEGER PRIMARY KEY,value TEXT NOT NULL,config_id TEXT,report_sha256 TEXT); CREATE TABLE auxiliary(kind TEXT NOT NULL,part INTEGER NOT NULL,value TEXT NOT NULL,PRIMARY KEY(kind,part));')
            db.execute('INSERT INTO header VALUES(?)',(canonical(meta),))
            for ordinal,row in enumerate(value.get('rows',[])):
                if cancel and ordinal%64==0 and cancel():raise InterruptedError('Canceled while building the saved result view.')
                projected=row_projection(row)
                db.execute('INSERT INTO rows VALUES(?,?,?,?)',(row['part'],canonical(projected),row.get('config_id'),row.get('report_sha256')))
            for kind,key in [('statistics','search_statistics'),('screen','search_screen')]:
                item=value.get(key)
                if isinstance(item,dict):
                    for ordinal,account in enumerate(item.get('accounts',[])):
                        if cancel and ordinal%64==0 and cancel():raise InterruptedError('Canceled while indexing saved diagnostics.')
                        db.execute('INSERT INTO auxiliary VALUES(?,?,?)',(kind,account['part'],canonical(account)))
            db.commit();db.close();db=None;digest=file_hash(temporary);filename=digest+'.view.sqlite3';destination=folder/filename
            os.replace(temporary,destination)
            with self.store.db() as connection:
                connection.execute('BEGIN IMMEDIATE')
                current=connection.execute('SELECT rowid AS input_rowid FROM jobs WHERE id=?',(jid,)).fetchone();event=self.event(connection,jid,'result_saved')
                if current is None or event is None or event.get('sha256')!=root_hash or input_bytes_hash(connection,current['input_rowid'])!=raw_hash or original_hash(root)!=root_hash:raise StateError('Original result/input changed during view construction.')
                self.store.event('result_view_saved',jid,dict(filename=filename,sha256=digest,root_sha256=root_hash,payload_hash=payload_hash,input_raw_sha256=raw_hash,metadata_sha256=identity(meta),row_count=meta['row_count'],policy_version=1),connection)
                connection.execute('COMMIT')
        finally:
            if db is not None:db.close()
            if temporary.exists():
                assert temporary.resolve().is_relative_to(folder)
                temporary.unlink()

    @contextmanager
    def snapshot(self,jid):
        folder=self.folder(jid);cache=None
        try:
            with self.store.db() as db:
                db.execute('BEGIN')
                job=db.execute('SELECT rowid AS input_rowid,id,status,kind FROM jobs WHERE id=?',(jid,)).fetchone()
                if job is None or job['status']!='completed':raise StateError('Results are available only after successful completion.')
                original=self.event(db,jid,'result_saved')
                if original is None or original_hash(folder/'result.json.gz')!=original.get('sha256'):raise StateError('Saved result integrity check failed.')
                view=self.event(db,jid,'result_view_saved')
                if view is None:raise ViewUnavailable('Build a saved result view from the original verified evidence.')
                if input_bytes_hash(db,job['input_rowid'])!=view.get('input_raw_sha256'):raise StateError('Original input bytes differ from the verified saved result view.')
                if view.get('root_sha256')!=original['sha256']:raise ViewUnavailable('Saved result view refers to an earlier original artifact.')
                filename=view.get('filename','')
                if not isinstance(filename,str) or re.fullmatch(r'[a-f0-9]{64}\.view\.sqlite3',filename) is None:raise ViewUnavailable('Saved result view location is invalid.')
                path=folder/filename
                try:valid=path.is_file() and file_hash(path)==view.get('sha256')
                except OSError:valid=False
                if not valid:raise ViewUnavailable('Saved result view integrity failed; rebuild it from verified originals.')
                try:
                    cache=sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True);cache.row_factory=sqlite3.Row;cache.execute('PRAGMA query_only=ON');cache.execute('BEGIN')
                    header=cache.execute('SELECT value FROM header').fetchone()
                    if header is None:raise ViewUnavailable('Saved result view header is missing.')
                    meta=json.loads(header[0])
                    if not isinstance(meta,dict):raise ViewUnavailable('Saved result view header is malformed.')
                    if identity(meta)!=view.get('metadata_sha256') or meta.get('job_id')!=jid or meta.get('payload_hash')!=view.get('payload_hash') or cache.execute('SELECT COUNT(*) FROM rows').fetchone()[0]!=view.get('row_count'):raise ViewUnavailable('Saved result view metadata differs.')
                except (sqlite3.DatabaseError,ValueError,TypeError,KeyError) as error:raise ViewUnavailable('Saved result view cannot be verified.') from error
                yield cache,meta,view
        finally:
            if cache is not None:cache.close()

    def summary(self,jid):
        try:
            with self.snapshot(jid) as (_,meta,view):
                return meta|dict(index_integrity=True,root_sha256=view['root_sha256'],complete_result_url='/api/jobs/'+jid+'/result',inputs_url='/api/jobs/'+jid+'/inputs',rows_url='/api/jobs/'+jid+'/result-rows')
        except ViewUnavailable as error:
            job=self.store.job_status(jid)
            return dict(job_id=jid,kind=job['kind'],index_integrity=False,requires_index=True,index_error=str(error),repair_url='/api/jobs/'+jid+'/result-view/repair',complete_result_url='/api/jobs/'+jid+'/result')

    def rows(self,jid,limit=50,offset=0):
        if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:raise StateError('Invalid saved result page.')
        with self.snapshot(jid) as (db,meta,view):
            rows=[json.loads(r[0]) for r in db.execute('SELECT value FROM rows ORDER BY part LIMIT ? OFFSET ?',(limit,offset))]
            return dict(job_id=jid,rows=rows,pagination=dict(limit=limit,offset=offset,total=meta['row_count']),index_integrity=True,root_sha256=view['root_sha256'])

    def auxiliary(self,jid,kind,limit=20,offset=0):
        if kind not in {'statistics','screen'} or type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:raise StateError('Invalid saved diagnostic page.')
        key='search_statistics' if kind=='statistics' else 'search_screen'
        with self.snapshot(jid) as (db,meta,view):
            if key not in meta:raise StateError('This original has no supported saved diagnostic.')
            values=[json.loads(r[0]) for r in db.execute('SELECT value FROM auxiliary WHERE kind=? ORDER BY part LIMIT ? OFFSET ?',(kind,limit,offset))]
            total=db.execute('SELECT COUNT(*) FROM auxiliary WHERE kind=?',(kind,)).fetchone()[0]
            return meta[key]|dict(accounts=values,accounts_complete=offset==0 and len(values)==total,pagination=dict(limit=limit,offset=offset,total=total),job_id=jid,index_integrity=True)

    def part(self,jid,part,window='report'):
        if type(part) is not int or part<0 or window not in {'report','discovery','validation'}:raise StateError('Choose a supported saved part/window.')
        with self.snapshot(jid) as (db,_,view):
            row=db.execute('SELECT config_id,report_sha256 FROM rows WHERE part=?',(part,)).fetchone()
            if row is None:raise StateError('Unknown configuration part.')
            path=self.folder(jid)/'parts'/(str(part).zfill(6)+'.json.gz')
            try:raw=path.read_bytes()
            except OSError as error:raise StateError('Original configuration report is unavailable.') from error
            if hashlib.sha256(raw).hexdigest()!=row['report_sha256']:raise StateError('Configuration report integrity check failed.')
            try:
                saved=json.loads(gzip.decompress(raw))
                if not isinstance(saved,dict):raise ValueError()
            except (OSError,ValueError,TypeError,EOFError) as error:raise StateError('Original configuration report is malformed.') from error
            if saved.get('config_id')!=row['config_id'] or saved.get('payload_hash')!=view['payload_hash'] or window not in saved:raise StateError('Configuration identity or saved report window differs.')
            return saved[window]
