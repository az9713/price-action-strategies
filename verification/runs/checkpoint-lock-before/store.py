"""SQLite experiment registry and transactional, leased, resumable job queue."""
from contextlib import contextmanager
from contextvars import ContextVar
from threading import get_ident
from pathlib import Path
import json
import re
import sqlite3
import time
import uuid
from .config import canonical
from .trials import TrialLedger
from .job_index import JobIndex
from .study_index import StudyIndex

class StateError(ValueError): pass

SPREAD_SELECTION_PREDICATE="kind='spread_protocol' AND CASE WHEN json_valid(details) THEN json_extract(details,'$.event.kind') END='version_selected'"
SPREAD_SELECTION_INDEX_SQL='CREATE INDEX spread_selected_events ON events(entity_id,id) WHERE '+SPREAD_SELECTION_PREDICATE
SPREAD_CHILD_PARENT_EXPR="CASE WHEN json_valid(projection) THEN json_extract(projection,'$.spread_parent.job_id') END"
SPREAD_CHILD_PARENT_PREDICATE='('+SPREAD_CHILD_PARENT_EXPR+') IS NOT NULL'
SPREAD_CHILD_PARENT_INDEX_SQL='CREATE INDEX spread_child_parent_index ON job_input_index(('+SPREAD_CHILD_PARENT_EXPR+'),job_id) WHERE '+SPREAD_CHILD_PARENT_PREDICATE

_control_reader=ContextVar('price_action_live_control_reader',default=None)

class Store:
    def __init__(self,root:Path):
        self.root=root
        (root/'data').mkdir(parents=True,exist_ok=True)
        self.path=root/'data'/'lab.sqlite3'
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs(
              id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'queued',created REAL NOT NULL,updated REAL NOT NULL,
              owner TEXT,lease_until REAL,progress REAL NOT NULL DEFAULT 0,
              checkpoint INTEGER NOT NULL DEFAULT 0,note TEXT NOT NULL DEFAULT '',
              error TEXT,cancel_requested INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS jobs_pending ON jobs(status,created);
            CREATE INDEX IF NOT EXISTS jobs_live_control ON jobs(id,status,owner,cancel_requested);
            CREATE TABLE IF NOT EXISTS strategies(
              id TEXT PRIMARY KEY,name TEXT NOT NULL,config TEXT NOT NULL,created REAL NOT NULL,parent_id TEXT);
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,at REAL NOT NULL,kind TEXT NOT NULL,
              entity_id TEXT NOT NULL,details TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_entity ON events(entity_id,id);
            CREATE INDEX IF NOT EXISTS events_kind ON events(kind,entity_id);
            CREATE TABLE IF NOT EXISTS studies(
              id TEXT PRIMARY KEY,name TEXT NOT NULL,dataset_id TEXT NOT NULL,spec TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft',created REAL NOT NULL,updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS viewed_windows(
              id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT NOT NULL,start TEXT NOT NULL,
              end TEXT NOT NULL,kind TEXT NOT NULL,study_id TEXT,at REAL NOT NULL);
            ''')
            db.execute(SPREAD_SELECTION_INDEX_SQL.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))
        self._trials=TrialLedger(self,StateError)
        self._input_index=JobIndex(self,StateError)
        with self.db() as db:db.execute(SPREAD_CHILD_PARENT_INDEX_SQL.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))
        self._study_index=StudyIndex(self,StateError)
        from .trade_twin_jobs import initialize
        initialize(self)
        from .research_family_source import initialize as initialize_family
        initialize_family(self)
        from .research_family_jobs import initialize as initialize_family_jobs
        initialize_family_jobs(self)
        from .research_funnel_arms import initialize as initialize_funnel_arms
        initialize_funnel_arms(self)
        from .research_funnel_jobs import initialize as initialize_qualification
        initialize_qualification(self)
        from .research_funnel_final import initialize as initialize_funnel_final
        initialize_funnel_final(self)

    @contextmanager
    def db(self,thread_handoff=False):
        db=sqlite3.connect(self.path,timeout=10,isolation_level=None,check_same_thread=not thread_handoff)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=10000')
        try: yield db
        finally: db.close()

    @contextmanager
    def control_reads(self):
        """Reuse a read-only connection, with a fresh autocommit query each time."""
        source_path=self.path;key=(source_path.resolve(),get_ident());active=_control_reader.get()
        if active is not None and active[:2]==key:
            yield
            return
        file_id=self._control_identity(key[0])
        db=sqlite3.connect(key[0].as_uri()+'?mode=ro',uri=True,timeout=10,isolation_level=None)
        token=None
        try:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            if self.path!=source_path or self.path.resolve()!=key[0] or self._control_identity(self.path)!=file_id:
                raise StateError('Live control database changed while its reader was opened.')
            token=_control_reader.set((*key,db,source_path,file_id))
            yield
        finally:
            if token is not None:_control_reader.reset(token)
            db.close()

    @staticmethod
    def _control_identity(path):
        try:
            state=path.stat()
            return state.st_dev,state.st_ino
        except OSError as error:
            raise StateError('Live control database identity is unavailable.') from error

    @contextmanager
    def _control_db(self):
        active=_control_reader.get()
        if active is not None and active[1]==get_ident():
            # A fresh physical-file identity check avoids repeatedly walking
            # every Windows path component for each live cancellation query.
            if self.path==active[3] and active[4][1]:
                reuse=self._control_identity(self.path)==active[4]
            else:
                reuse=(self.path.resolve()==active[0] and
                    (not active[4][1] or self._control_identity(self.path)==active[4]))
            if reuse:
                yield active[2]
                return
        with self.db() as db:yield db

    @staticmethod
    def decode(row):
        if row is None: return None
        result=dict(row)
        for field in ['payload','config','spec','details']:
            if field in result: result[field]=json.loads(result[field])
        return result

    def event(self,kind,entity_id,details,db=None):
        if db is None:
            with self.db() as connection: self.event(kind,entity_id,details,connection)
        else:
            db.execute('INSERT INTO events(at,kind,entity_id,details) VALUES(?,?,?,?)',
                       (time.time(),kind,entity_id,canonical(details)))

    def create_job(self,kind,payload,*,spread_parent=None):
        if kind not in {'download','news_download','experiment','search','screen','final','behavior','portfolio','benchmark','controls','ablation','borrow_sensitivity','spread','spread_accounts'}:
            raise StateError('Unknown job type.')
        if (kind=='spread_accounts')!=(spread_parent is not None):raise StateError('Spread accounts require their original parent continuation binding.')
        job_id=uuid.uuid4().hex
        now=time.time()
        with self.db() as db:
            if spread_parent is not None:db.execute('CREATE TABLE IF NOT EXISTS spread_account_links(parent_id TEXT PRIMARY KEY REFERENCES jobs(id),child_id TEXT NOT NULL UNIQUE REFERENCES jobs(id))')
            db.execute('BEGIN IMMEDIATE')
            if spread_parent is not None:
                from .config import identity
                parent_id=spread_parent['job_id'];parent=db.execute('SELECT * FROM jobs WHERE id=?',(parent_id,)).fetchone()
                event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id DESC LIMIT 1",(parent_id,)).fetchone()
                if parent is None or parent['kind']!='spread' or parent['status']!='completed' or identity(json.loads(parent['payload']))!=spread_parent['payload_hash'] or event is None or json.loads(event['details']).get('sha256')!=spread_parent['result_sha256']:
                    raise StateError('Original spread parent changed before the account plan could freeze.')
                self._trials.verify(parent_id,db)
                existing=db.execute('SELECT child_id FROM spread_account_links WHERE parent_id=?',(parent_id,)).fetchone()
                children=self.spread_children(parent_id,db)
                if (existing is None and children) or (existing is not None and children!=[existing['child_id']]):raise StateError('An original child reservation exists or is inconsistent; a replacement account is not authorized.')
                originals=list(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen' ORDER BY id",(parent_id,)))
                if len(originals)>1 or bool(originals)!=(existing is not None):raise StateError('Original spread account link is missing or inconsistent; do not create a replacement.')
                if existing is not None:
                    if json.loads(originals[0]['details'])!=dict(child_id=existing['child_id'],**spread_parent):raise StateError('Original spread account continuation event changed.')
                    child=db.execute('SELECT * FROM jobs WHERE id=?',(existing['child_id'],)).fetchone()
                    if child is None or child['kind']!='spread_accounts' or identity(json.loads(child['payload']))!=identity(payload):raise StateError('Original linked spread account inputs changed.')
                    self._trials.verify(child['id'],db);db.execute('COMMIT');return self.decode(child)
            if kind in {'screen','final'}:
                study_id=payload.get('study_id')
                study=db.execute('SELECT status,spec FROM studies WHERE id=?',(study_id,)).fetchone()
                expected='registered' if kind=='screen' else 'screened'
                if study is None or study['status']!=expected:
                    db.execute('ROLLBACK');raise StateError('Study state does not permit this job.')
                if self._input_index.pending_study(kind,study_id,db):
                    db.execute('ROLLBACK');raise StateError('This study job is already queued or running.')
                spec=json.loads(study['spec'])
                if spec.get('funnel_version'):
                    raise StateError('Research funnel jobs require their complete original arm/control/family qualification; the basic study path is refused.')
                if kind=='final' and spec.get('study_mode')=='portfolio':
                    if spec.get('reserved_final_job_id'):
                        db.execute('ROLLBACK');raise StateError('Portfolio final job is already reserved; resume the original job.')
                    spec['reserved_final_job_id']=job_id
                    db.execute('UPDATE studies SET spec=?,updated=? WHERE id=?',(canonical(spec),now,study_id))
                    self.event('portfolio_final_reserved',study_id,dict(job_id=job_id,candidate_hash=spec.get('candidate_hash')),db)
                    self._study_index.add(db,study_id,spec)
            db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',
                       (job_id,kind,canonical(payload),now,now))
            self._trials.freeze(dict(id=job_id,kind=kind,payload=payload),db)
            self._input_index.add(db,job_id,payload)
            self.event('job_created',job_id,{'kind':kind},db)
            if spread_parent is not None:
                db.execute('INSERT INTO spread_account_links VALUES(?,?)',(spread_parent['job_id'],job_id))
                self.event('spread_accounts_frozen',spread_parent['job_id'],dict(child_id=job_id,**spread_parent),db)
            db.execute('COMMIT')
        return self.job(job_id)

    def job(self,job_id):
        with self.db() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
        if row is None: raise StateError('Job does not exist.')
        return self.decode(row)

    def study_status(self,sid):return self._study_index.statuses(sid)
    def study_statuses(self,limit=500,offset=0):return self._study_index.statuses(limit=limit,offset=offset)
    def study_inputs(self,sid):return self._study_index.inputs(sid)
    def repair_study_index(self,sid):return self._study_index.repair(sid)

    def job_status(self,job_id):return self._input_index.statuses(job_id)
    def job_statuses(self,limit=500,offset=0):return self._input_index.statuses(limit=limit,offset=offset)
    def job_inputs(self,job_id):return self._input_index.inputs(job_id)
    def repair_job_index(self,job_id):return self._input_index.repair(job_id)
    def spread_children(self,parent_id,db):
        """Bounded reverse reservation lookup; never decode original account plans."""
        schema=db.execute("SELECT substr(sql,1,4097) sql,length(CAST(sql AS BLOB)) bytes FROM sqlite_master WHERE type='index' AND name='spread_child_parent_index'").fetchone()
        if schema is None or schema['bytes']>4096 or ''.join(schema['sql'].split()).lower()!=''.join(SPREAD_CHILD_PARENT_INDEX_SQL.split()).lower():raise StateError('Original child reservation index is unavailable; no replacement account is authorized.')
        rows=list(db.execute('SELECT substr(job_id,1,33) job_id,length(CAST(job_id AS BLOB)) bytes FROM job_input_index INDEXED BY spread_child_parent_index WHERE '+SPREAD_CHILD_PARENT_PREDICATE+' AND ('+SPREAD_CHILD_PARENT_EXPR+')=? ORDER BY job_id LIMIT 2',(parent_id,)))
        if any(r['bytes']!=32 or not isinstance(r['job_id'],str) or not re.fullmatch('[a-f0-9]{32}',r['job_id']) for r in rows):raise StateError('Original child reservation metadata is malformed; no replacement account is authorized.')
        return [r['job_id'] for r in rows]
    def pending_study_job(self,kind,study_id):
        with self.db() as db:return self._input_index.pending_study(kind,study_id,db)

    def cancellation_requested(self,job_id,owner):
        """Read live worker control state without loading a potentially huge plan."""
        with self._control_db() as db:
            cursor=db.execute('SELECT status,owner,cancel_requested FROM jobs INDEXED BY jobs_live_control WHERE id=?',(job_id,))
            try:row=cursor.fetchone()
            finally:cursor.close()
        if row is None or row['owner']!=owner or row['status'] not in {'running','canceling'}:
            raise StateError('Worker no longer owns this job.')
        return bool(row['cancel_requested'])

    def jobs(self):
        with self.db() as db:
            return [self.decode(r) for r in db.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 500')]

    def claim(self,owner,lease_seconds=15):
        now=time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            stale=db.execute("SELECT id,cancel_requested FROM jobs WHERE status IN ('running','canceling') AND lease_until<?",(now,)).fetchall()
            for row in stale:
                state='canceled' if row['cancel_requested'] else 'queued'
                db.execute('UPDATE jobs SET status=?,owner=NULL,lease_until=NULL,updated=? WHERE id=?',(state,now,row['id']))
                self._trials.terminal(db,row['id'],state,'Worker lease expired before completion.')
                self.event('lease_recovered',row['id'],{'new_state':state},db)
            row=db.execute("SELECT j.id FROM jobs j WHERE j.status='queued' AND j.cancel_requested=0 AND (j.kind!='funnel_qualification' OR NOT EXISTS(SELECT 1 FROM funnel_dependencies d JOIN jobs child ON child.id=d.child_id WHERE d.parent_id=j.id AND child.status NOT IN ('completed','failed','canceled'))) ORDER BY j.created,j.id LIMIT 1").fetchone()
            if row is None:
                db.execute('COMMIT');return None
            db.execute("UPDATE jobs SET status='running',owner=?,lease_until=?,updated=? WHERE id=?",
                       (owner,now+lease_seconds,now,row['id']))
            self.event('job_claimed',row['id'],{'owner':owner},db)
            db.execute('COMMIT')
        try:return self.job(row['id'])
        except (ValueError,TypeError):
            self.finish(row['id'],owner,'failed','Stored job inputs are malformed. Restore the original inputs before resuming.',public=True)
            return None

    def heartbeat(self,job_id,owner,progress=None,note=None,checkpoint=None):
        now=time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT status,owner,progress,note,checkpoint,cancel_requested FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None or row['owner']!=owner or row['status'] not in {'running','canceling'}:
                db.execute('ROLLBACK');raise StateError('Worker no longer owns this job.')
            value=row['progress'] if progress is None else min(1.,max(0.,float(progress)))
            db.execute('UPDATE jobs SET progress=?,note=?,checkpoint=?,lease_until=?,updated=? WHERE id=?',
                       (value,row['note'] if note is None else note,row['checkpoint'] if checkpoint is None else checkpoint,now+15,now,job_id))
            canceled=bool(row['cancel_requested'])
            db.execute('COMMIT')
        return canceled

    def finish(self,job_id,owner,status,error=None,*,public=False):
        if status not in {'completed','failed','canceled'}: raise StateError('Invalid terminal state.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None or row['owner']!=owner or row['status'] not in {'running','canceling'}:
                db.execute('ROLLBACK');raise StateError('Terminal update from nonowning worker.')
            if row['cancel_requested'] and status=='completed': status='canceled'
            db.execute('UPDATE jobs SET status=?,error=?,progress=?,owner=NULL,lease_until=NULL,updated=? WHERE id=?',
                       (status,error,1 if status=='completed' else row['progress'],time.time(),job_id))
            self._trials.terminal(db,job_id,status,error)
            self.event('job_'+status,job_id,{'error':error},db)
            db.execute('COMMIT')
        return self.job_status(job_id) if public else self.job(job_id)

    def release(self,job_id,owner):
        """Graceful worker shutdown preserves queued work and its checkpoint."""
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None or row['owner']!=owner or row['status'] not in {'running','canceling'}:
                db.execute('ROLLBACK');raise StateError('Shutdown from nonowning worker.')
            state='canceled' if row['cancel_requested'] else 'queued'
            db.execute('UPDATE jobs SET status=?,owner=NULL,lease_until=NULL,updated=? WHERE id=?',(state,time.time(),job_id))
            self._trials.terminal(db,job_id,state,'Worker stopped before durable completion.')
            self.event('worker_shutdown_checkpoint',job_id,{'new_state':state,'checkpoint':row['checkpoint']},db)
            db.execute('COMMIT')

    def cancel(self,job_id,*,public=False):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT status FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None:
                db.execute('ROLLBACK');raise StateError('Job does not exist.')
            if row['status'] not in {'queued','running','canceling'}:
                db.execute('ROLLBACK');raise StateError('Only pending/running jobs can be canceled.')
            state='canceled' if row['status']=='queued' else 'canceling'
            db.execute('UPDATE jobs SET status=?,cancel_requested=1,updated=? WHERE id=?',(state,time.time(),job_id))
            if state=='canceled':self._trials.terminal(db,job_id,state,'Canceled before computation started.')
            self.event('job_cancel_requested',job_id,{},db)
            db.execute('COMMIT')
        return self.job_status(job_id) if public else self.job(job_id)

    def resume(self,job_id,*,public=False):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT status FROM jobs WHERE id=?',(job_id,)).fetchone()
            if row is None or row['status'] not in {'canceled','failed'}:
                db.execute('ROLLBACK');raise StateError('Only failed/canceled jobs can resume.')
            db.execute("UPDATE jobs SET status='queued',cancel_requested=0,error=NULL,owner=NULL,lease_until=NULL,updated=? WHERE id=?",(time.time(),job_id))
            self.event('job_resumed',job_id,{},db)
            db.execute('COMMIT')
        return self.job_status(job_id) if public else self.job(job_id)

    def save_strategy(self,name,config,parent_id=None):
        if not name.strip() or len(name)>100: raise StateError('Strategy name must have 1–100 characters.')
        strategy_id=uuid.uuid4().hex
        with self.db() as db:
            if parent_id and not db.execute('SELECT 1 FROM strategies WHERE id=?',(parent_id,)).fetchone():
                raise StateError('Parent strategy does not exist.')
            db.execute('INSERT INTO strategies(id,name,config,created,parent_id) VALUES(?,?,?,?,?)',
                       (strategy_id,name.strip(),canonical(config),time.time(),parent_id))
        self.event('strategy_saved',strategy_id,{'parent_id':parent_id})
        return strategy_id

    def strategies(self):
        with self.db() as db:
            return [self.decode(row) for row in db.execute('SELECT * FROM strategies ORDER BY created DESC')]

    def events(self,entity_id):
        with self.db() as db:
            return [self.decode(row) for row in db.execute('SELECT * FROM events WHERE entity_id=? ORDER BY id',(entity_id,))]

    def registry(self,limit=20,offset=0,job_id=None):return self._trials.listing(limit,offset,job_id)
    def verify_trial_plan(self,job_id):return self._trials.verify(job_id)
    def start_trial(self,job_id,part,window,owner):return self._trials.start(job_id,part,window,owner)
    def computed_trial(self,job_id,part,window,owner,report):return self._trials.computed(job_id,part,window,owner,report)
    def checkpoint_trial(self,job_id,part,window,owner,report,artifact):return self._trials.checkpoint(job_id,part,window,owner,report,artifact)
    def bind_trial_result(self,job_id,owner,digest):return self._trials.bind_result(job_id,owner,digest)
    def export_trials(self,job_id,format):return self._trials.export(job_id,format)
    def skip_trial(self,job_id,part,window,owner,reason):return self._trials.skip(job_id,part,window,owner,reason)
