"""Research access guard: protects product routes, not the owner of this computer."""
from datetime import date,timedelta
from pathlib import Path
import hashlib
import json
import time
import uuid
import platform
import math
from importlib.metadata import version
from .store import Store,StateError
from .config import canonical,identity
from .models import Study
from .study_index import input_hash as study_input_hash

class ResearchError(StateError): pass


def passes_screen(metrics,minimum_trades,minimum_sharpe):
    """Both complete accounts must meet every prespecified gate."""
    if len(metrics)!=2:return False
    try:
        return all(type(m['trades']) is int and m['trades']>=minimum_trades and
            math.isfinite(m['net_profit']) and m['net_profit']>0 and
            m['marked_sharpe'] is not None and math.isfinite(m['marked_sharpe']) and m['marked_sharpe']>=minimum_sharpe
            for m in metrics)
    except (KeyError,TypeError,ValueError):return False

_RUNTIME={'python':platform.python_version(),**{name:version(name) for name in
    ['numpy','pandas','pyarrow','exchange_calendars','pydantic','scipy','numba','duckdb','httpx','fastapi','uvicorn','python-multipart']}}

def current_core_subject():
    folder=Path(__file__).resolve().parent
    root=folder.parents[1]
    files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')}
    for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock']:
        files[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    return {'source_files':files,'runtime':_RUNTIME.copy()}

def current_core_hash(): return identity(current_core_subject())

_LOADED_CORE_SUBJECT=current_core_subject()
_LOADED_CORE_HASH=identity(_LOADED_CORE_SUBJECT)

def core_hash():
    """Fingerprint loaded process code, not subsequently edited disk files."""
    return _LOADED_CORE_HASH

def core_subject(): return json.loads(json.dumps(_LOADED_CORE_SUBJECT))

def require_current_source():
    if core_hash()!=current_core_hash():
        raise ResearchError('Source files changed after this process started. Restart the local service before creating new research.')

class Guard:
    def __init__(self,store:Store): self.store=store

    def protected_scopes(self,db):
        try:yield from self.store._study_index.scopes(db)
        except StateError as error:raise ResearchError(str(error)) from error

    def check_access(self,db,symbols,start,end,study_id=None,final_job_id=None):
        """Check protected scopes in the caller's existing transaction; no writes."""
        if start>end:raise ResearchError('Read dates are reversed.')
        if not db.in_transaction:raise ResearchError('Protected scope checks require an active transaction.')
        for row,spec in self.protected_scopes(db):
            overlap=set(symbols)&set(spec['symbols']) and start<=spec['holdout']['end'] and end>=spec['holdout']['start']
            if not overlap:continue
            permitted=(row['id']==study_id and final_job_id and spec.get('final_job_id')==final_job_id and row['status'] in {'consumed','final_complete','final_failed'})
            if not permitted:raise ResearchError('Read would expose protected final data. Use the study final-test workflow.')

    def studies(self):
        with self.store.db() as db:
            return [self.store.decode(row) for row in db.execute('SELECT * FROM studies ORDER BY created DESC')]

    def study(self,study_id):
        with self.store.db() as db:
            row=db.execute('SELECT * FROM studies WHERE id=?',(study_id,)).fetchone()
        if row is None: raise ResearchError('Study does not exist.')
        return self.store.decode(row)

    def verify_inputs(self,study,db=None):
        if db is None:
            with self.store.db() as connection:return self.verify_inputs(study,connection)
        event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='study_registered' ORDER BY id LIMIT 1",(study['id'],)).fetchone()
        if event is None or json.loads(event['details']).get('spec_hash')!=study_input_hash(study['spec']):
            raise ResearchError('Frozen study registration input hash changed or is missing.')

    def verify_candidates(self,spec,db,study_id):
        candidates=spec.get('candidates',[])
        if spec.get('study_mode','independent')=='portfolio':
            valid=candidates==[spec['configurations']]
        else:
            known={identity(c) for c in spec['configurations']};ids=[identity(c) for c in candidates]
            valid=bool(ids) and len(ids)==len(set(ids)) and set(ids)<=known
        event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='candidates_frozen' ORDER BY id DESC LIMIT 1",(study_id,)).fetchone()
        frozen={} if event is None else json.loads(event['details'])
        if not valid or frozen.get('candidate_hash')!=spec.get('candidate_hash') or frozen.get('count')!=len(candidates):
            raise ResearchError('Frozen candidate event or complete selection unit changed.')

    def verify_final_reservation(self,spec,study_id,job_id,db=None):
        if spec.get('study_mode')!='portfolio':return
        if db is None:
            with self.store.db() as connection:return self.verify_final_reservation(spec,study_id,job_id,connection)
        event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='portfolio_final_reserved' ORDER BY id LIMIT 1",(study_id,)).fetchone()
        reserved={} if event is None else json.loads(event['details'])
        if (spec.get('reserved_final_job_id')!=job_id or reserved.get('job_id')!=job_id or
            reserved.get('candidate_hash')!=spec.get('candidate_hash')):
            raise ResearchError('Portfolio final job reservation changed or is missing.')

    def register(self,spec:Study,manifest,extra=None):
        require_current_source()
        payload=spec.model_dump(mode='json')
        payload.update(extra or {})
        symbols=manifest['quality']['symbols']
        if payload['discovery']['start']<manifest['quality']['start'] or payload['holdout']['end']>manifest['quality']['end']:
            raise ResearchError('Study dates must stay inside the dataset.')
        study_id=uuid.uuid4().hex
        payload.update(symbols=symbols,dataset_manifest_hash=identity(manifest),core_hash=core_hash())
        now=time.time()
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for symbol in symbols:
                seen=db.execute('SELECT 1 FROM viewed_windows WHERE symbol=? AND start<=? AND end>=? LIMIT 1',
                    (symbol,payload['holdout']['end'],payload['holdout']['start'])).fetchone()
                if seen:
                    db.execute('ROLLBACK')
                    raise ResearchError('Selected final dates have already been viewed/evaluated for '+symbol+'. Choose untouched dates.')
            for row,other in self.protected_scopes(db):
                if set(symbols)&set(other['symbols']) and payload['holdout']['start']<=other['holdout']['end'] and payload['holdout']['end']>=other['holdout']['start']:
                    db.execute('ROLLBACK');raise ResearchError('Final dates overlap another protected study.')
            db.execute('INSERT INTO studies(id,name,dataset_id,spec,status,created,updated) VALUES(?,?,?,?,?,?,?)',
                (study_id,spec.name,spec.dataset_id,canonical(payload),'registered',now,now))
            self.store.event('study_registered',study_id,{'spec_hash':identity(payload),'holdout':payload['holdout']},db)
            self.store._study_index.add(db,study_id,payload)
            db.execute('COMMIT')
        return self.study(study_id)

    def access(self,symbols,start,end,kind,study_id=None,final_job_id=None,record=True):
        if start>end: raise ResearchError('Read dates are reversed.')
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.check_access(db,symbols,start,end,study_id,final_job_id)
            if record:
                for symbol in symbols:
                    db.execute('INSERT INTO viewed_windows(symbol,start,end,kind,study_id,at) VALUES(?,?,?,?,?,?)',
                        (symbol,start,end,kind,study_id,time.time()))
                self.store.event('data_access',study_id or 'discovery',dict(symbols=symbols,start=start,end=end,kind=kind,final_job_id=final_job_id),db)
            db.execute('COMMIT')

    def screened(self,study_id,report_hash,candidates):
        study=self.study(study_id)
        self.verify_inputs(study)
        spec=study['spec']
        if spec['core_hash']!=core_hash(): raise ResearchError('Engine changed after registration; create a new study before final access.')
        if spec.get('study_mode','independent')=='portfolio':
            if candidates not in [[],[spec['configurations']]]:raise ResearchError('A portfolio candidate must retain the complete frozen rule set.')
        elif len({identity(c) for c in candidates})!=len(candidates) or any(c not in spec['configurations'] for c in candidates):
            raise ResearchError('Candidates must be distinct members of the registered study.')
        spec.update(screening_report_hash=report_hash,candidates=candidates,candidate_hash=identity(candidates))
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT status FROM studies WHERE id=?',(study_id,)).fetchone()
            if current is None or current['status']!='registered':
                db.execute('ROLLBACK');raise ResearchError('Study is not eligible for screening completion.')
            db.execute('UPDATE studies SET spec=?,status=?,updated=? WHERE id=?',
                (canonical(spec),'screened' if candidates else 'no_candidates',time.time(),study_id))
            self.store.event('candidates_frozen',study_id,{'candidate_hash':identity(candidates),'count':len(candidates),'screening_report_hash':report_hash},db)
            self.store._study_index.add(db,study_id,spec)
            db.execute('COMMIT')

    def begin_final(self,study_id,job_id,manifest):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studies WHERE id=?',(study_id,)).fetchone()
            if row is None:
                db.execute('ROLLBACK');raise ResearchError('Study not found.')
            spec=json.loads(row['spec'])
            if spec['core_hash']!=core_hash() or spec['dataset_manifest_hash']!=identity(manifest) or spec.get('candidate_hash')!=identity(spec.get('candidates',[])):
                db.execute('ROLLBACK');raise ResearchError('Frozen engine, dataset or candidate hash changed.')
            self.verify_inputs(dict(id=study_id,spec=spec),db)
            self.verify_candidates(spec,db,study_id)
            self.verify_final_reservation(spec,study_id,job_id,db)
            if row['status'] in {'consumed','final_failed'} and spec.get('final_job_id')==job_id:
                self.store.event('final_continuation',study_id,{'job_id':job_id},db)
                db.execute('COMMIT');return
            if row['status']!='screened' or not spec.get('candidates'):
                db.execute('ROLLBACK');raise ResearchError('Final data can be unlocked once, after screening yields candidates.')
            # Consume before the first data read, even if the process subsequently fails.
            spec['final_job_id']=job_id
            db.execute("UPDATE studies SET spec=?,status='consumed',updated=? WHERE id=?",(canonical(spec),time.time(),study_id))
            for symbol in spec['symbols']:
                db.execute('INSERT INTO viewed_windows(symbol,start,end,kind,study_id,at) VALUES(?,?,?,?,?,?)',
                    (symbol,spec['holdout']['start'],spec['holdout']['end'],'final_consumed',study_id,time.time()))
            self.store.event('final_unlock_consumed',study_id,{'job_id':job_id,'candidate_hash':spec['candidate_hash']},db)
            self.store._study_index.add(db,study_id,spec)
            db.execute('COMMIT')

    def finish_final(self,study_id,job_id,success):
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM studies WHERE id=?',(study_id,)).fetchone()
            if row is None or json.loads(row['spec']).get('final_job_id')!=job_id:
                db.execute('ROLLBACK');raise ResearchError('Final completion belongs to another job.')
            status='final_complete' if success else 'final_failed'
            db.execute('UPDATE studies SET status=?,updated=? WHERE id=?',(status,time.time(),study_id))
            self.store.event(status,study_id,{'job_id':job_id},db)
            db.execute('COMMIT')
