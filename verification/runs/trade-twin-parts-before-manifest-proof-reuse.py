"""Original paired financial parts, exact amounts and owned atomic publication."""
from collections import OrderedDict
from contextlib import contextmanager
from decimal import Decimal
import gzip
import json
import re
import sqlite3

from .config import canonical, identity
from .result_index import file_hash
from .service import compressed_write
from .store import StateError
from .trade_twin_amounts import canonical_amount, exact_total, read_amount
from .trade_twin_execution import execute_twin,TwinPreparationCache
from .trade_twin_results import CanonicalOutcome
from .trade_twins import EXECUTION_POLICIES, TOTAL_SETS, MAX_SOURCE_TRADES, draw_set, _cancel

MAX_PART_BYTES = 512 * 1024 * 1024
CACHE_BYTES = 64 * 1024 * 1024
CACHE_PARTS = 4
PART_PREDICATE = "kind='twin_part_committed' AND json_valid(details)"
PART_INDEX = "CREATE INDEX trade_twin_part_event_index ON events(entity_id,json_extract(details,'$.part'),id) WHERE " + PART_PREDICATE
TRIAL_PREDICATE = "kind IN ('trial_computation_started','trial_checkpoint_saved') AND json_valid(details)"
TRIAL_INDEX = "CREATE INDEX trade_twin_trial_event_index ON events(entity_id,kind,json_extract(details,'$.trial_id'),id) WHERE " + TRIAL_PREDICATE
COMPUTED_PREDICATE = "kind='trial_computation_recorded' AND json_valid(details)"
COMPUTED_INDEX = "CREATE INDEX trade_twin_computed_event_index ON events(entity_id,json_extract(details,'$.trial_id'),id) WHERE " + COMPUTED_PREDICATE
EVENT_KEYS = {'part','start','stop','attempt','filename','sha256','payload_hash','plan_hash','book_count','book_bindings_sha256'}


def partition(source_count):
    if type(source_count) is not int or not 0 <= source_count <= MAX_SOURCE_TRADES:
        raise ValueError('A frozen bounded integer source cohort is required.')
    size = max(1, min(100, 1000 // max(1, source_count)))
    return dict(version=1, source_count=source_count, sets_per_part=size,
                part_count=(TOTAL_SETS + size - 1) // size, expected_sets=TOTAL_SETS)


def part_range(spec, ordinal):
    if not isinstance(spec,dict) or identity(spec) != identity(partition(spec.get('source_count'))):
        raise ValueError('The original deterministic work partition changed.')
    if type(ordinal) is not int or not 0 <= ordinal < spec['part_count']:
        raise ValueError('Unknown original financial part ordinal.')
    first = ordinal * spec['sets_per_part']
    return first, min(TOTAL_SETS, first + spec['sets_per_part'])


def initialize(store):
    with store.db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS trade_twin_part_index(
          job_id TEXT NOT NULL REFERENCES jobs(id),part INTEGER NOT NULL,
          event_id INTEGER NOT NULL,details TEXT NOT NULL,PRIMARY KEY(job_id,part));
        CREATE TABLE IF NOT EXISTS trade_twin_book_index(
          job_id TEXT NOT NULL REFERENCES jobs(id),book_key TEXT NOT NULL,
          part INTEGER NOT NULL,book_offset INTEGER NOT NULL,book_sha256 TEXT NOT NULL,
          PRIMARY KEY(job_id,book_key));
        CREATE INDEX IF NOT EXISTS trade_twin_books_by_part ON trade_twin_book_index(job_id,part,book_key);
        ''')
        for statement in (PART_INDEX, TRIAL_INDEX, COMPUTED_INDEX):
            db.execute(statement.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))


def freeze(value):
    if isinstance(value, Decimal):
        return canonical_amount(value)
    if isinstance(value, dict):
        return {k:freeze(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [freeze(v) for v in value]
    return value


def _index(db, name, expected):
    row = db.execute("SELECT substr(sql,1,4097) sql,length(CAST(sql AS BLOB)) bytes FROM sqlite_master WHERE type='index' AND name=?",(name,)).fetchone()
    if row is None or row['bytes']>4096 or ''.join(row['sql'].split()).lower()!=''.join(expected.split()).lower():
        raise StateError('Original financial event index is unavailable or changed.')


def computation_event(db,job_id,trial,after=-1):
    """Verify the original digest event independently of mutable trial/view rows."""
    _index(db,'trade_twin_computed_event_index',COMPUTED_INDEX)
    rows=db.execute("SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY trade_twin_computed_event_index WHERE "
        +COMPUTED_PREDICATE+" AND entity_id=? AND json_extract(details,'$.trial_id')=? AND id>? ORDER BY id LIMIT 2",(job_id,trial['id'],after)).fetchall()
    expected=dict(trial_id=trial['id'],part=trial['part'],window=trial['window'],attempt=trial['attempts'],sha256=trial['computed_sha256'])
    if len(rows)!=1 or rows[0]['bytes']>4096 or canonical(json.loads(rows[0]['details']))!=canonical(expected):
        raise StateError('Original financial computation digest is missing or changed; no derived view can replace it.')
    return rows[0]['id']


class FinancialParts:
    def __init__(self, lab, job, owner, prepared, cancel=None):
        from .trade_twin_jobs import verify_child
        from .trade_twin_preparation import _sealed
        self.lab=lab;self.job=job;self.owner=owner;self.prepared=prepared;self.cancel=cancel
        self.plan=prepared['plan'];self.source=prepared['source'];self.payload=job['payload']
        self.spec=partition(len(self.plan.sources));self.cache=OrderedDict();self.cache_bytes=0;self.unit=None
        self.execution_preparation=TwinPreparationCache()
        if identity(self.payload.get('work_partition'))!=identity(self.spec):
            raise StateError('Financial work units must be frozen with the original account.')
        self._control()
        if identity(verify_child(lab,job,self._control))!=identity(self.source):
            raise StateError('Prepared source differs from original account authority.')
        original=_sealed(lab,job,owner)
        if original is None or identity(original[1])!=identity(prepared['sealed']) or identity(original[1]['plan'])!=identity(self.plan.json()):
            raise StateError('Financial execution requires the original committed matching plan.')
        self.base=dict(job_id=job['id'],payload_hash=identity(self.payload),plan_hash=self.plan.plan_hash,
            parent_authority_hash=self.source['authority_hash'],core_hash=self.payload['core_hash'],
            dataset_manifest_hash=self.payload['dataset_manifest_hash'],actions_hash=prepared['sealed']['actions_hash'],
            news_hash=identity(self.payload.get('news_calendar')),strategy=self.payload['strategy'],
            costs=self.payload['costs'],portfolio=self.payload['portfolio'])
        self.folder=lab.output_path(job['id']).parent/'twins/parts'
        self._prefix()

    def _control(self):
        stopped=bool(self.cancel and self.cancel()) or self.lab.store.cancellation_requested(self.job['id'],self.owner)
        if stopped:
            raise InterruptedError('Paired financial work canceled.')
        return False

    def _owned(self,db):
        from .trade_twin_preparation import _owned
        _owned(self.lab,db,self.job,self.owner)

    @contextmanager
    def _unit(self):
        """Verify immutable consumed bytes within one before/after authority unit."""
        previous=self.unit;self.unit={}
        try:yield
        finally:self.unit=previous

    def _authority(self):
        from .trade_twin_jobs import verify_child
        from .trade_twin_preparation import _sealed
        self._control()
        if identity(verify_child(self.lab,self.job,self._control))!=identity(self.source):
            raise StateError('Original account changed during financial work.')
        original=_sealed(self.lab,self.job,self.owner)
        if original is None or identity(original[1])!=identity(self.prepared['sealed']):
            raise StateError('Original matching preparation changed during financial work.')

    def _event(self,db,part):
        _index(db,'trade_twin_part_event_index',PART_INDEX)
        rows=list(db.execute("SELECT id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY trade_twin_part_event_index WHERE "
            +PART_PREDICATE+" AND entity_id=? AND json_extract(details,'$.part')=? ORDER BY id LIMIT 2",(self.job['id'],part)))
        index=db.execute('SELECT event_id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM trade_twin_part_index WHERE job_id=? AND part=?',(self.job['id'],part)).fetchone()
        if not rows:
            first,stop=part_range(self.spec,part)
            done=db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND part>=? AND part<? AND artifact_sha256 IS NOT NULL LIMIT 1",(self.job['id'],first,stop)).fetchone()
            if index is not None or done is not None:
                raise StateError('Original committed financial part event is missing; no replacement is authorized.')
            return None
        if len(rows)!=1 or rows[0]['bytes']>16384 or index is None or index['bytes']>16384:
            raise StateError('Original financial part/index is missing, duplicated or oversized.')
        event=rows[0];value=json.loads(event['details']);first,stop=part_range(self.spec,part)
        if (not isinstance(value,dict) or set(value)!=EVENT_KEYS or index['event_id']!=event['id']
            or canonical(json.loads(index['details']))!=canonical(value) or type(value['attempt']) is not int or value['attempt']<1
            or any(type(value[k]) is not int for k in ['part','start','stop'])
            or value['part']!=part or (value['start'],value['stop'])!=(first,stop)
            or value['filename']!='part-'+str(part).zfill(6)+'-attempt-'+str(value['attempt']).zfill(6)+'.json.gz'
            or value['payload_hash']!=identity(self.payload) or value['plan_hash']!=self.plan.plan_hash
            or type(value['book_count']) is not int or value['book_count']<0
            or not isinstance(value['sha256'],str) or re.fullmatch('[a-f0-9]{64}',value['sha256']) is None):
            raise StateError('Original financial part identity differs from frozen inputs.')
        return event['id'],value

    def _bindings(self,db,part):
        return [dict(r) for r in db.execute('SELECT book_key,book_offset,book_sha256 FROM trade_twin_book_index INDEXED BY trade_twin_books_by_part WHERE job_id=? AND part=? ORDER BY book_key',(self.job['id'],part))]

    def _prefix(self):
        with self.lab.store.db() as db:
            db.execute('BEGIN');self._owned(db)
            _index(db,'trade_twin_part_event_index',PART_INDEX);_index(db,'trade_twin_trial_event_index',TRIAL_INDEX)
            indexed=[r[0] for r in db.execute('SELECT part FROM trade_twin_part_index WHERE job_id=? ORDER BY part',(self.job['id'],))]
            raw=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='twin_part_committed'",(self.job['id'],)).fetchone()[0]
            if indexed!=list(range(len(indexed))) or len(indexed)>self.spec['part_count'] or raw!=len(indexed):
                raise StateError('Original financial part prefix is incomplete or inconsistent.')
            total_books=0
            for part in indexed:
                _,event=self._event(db,part);bindings=self._bindings(db,part)
                total_books+=event['book_count']
                if len(bindings)!=event['book_count'] or identity(bindings)!=event['book_bindings_sha256']:
                    raise StateError('Financial book index differs from its original committed part.')
            if db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(self.job['id'],)).fetchone()[0]!=total_books:
                raise StateError('An original book reference has no matching committed financial part.')
            if len(indexed)<self.spec['part_count']:
                self._event(db,len(indexed))
        for part in indexed:self._load(part)
        return len(indexed)

    def _trial_event(self,db,kind,tid,expected,after=-1):
        rows=db.execute("SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY trade_twin_trial_event_index WHERE "
            +TRIAL_PREDICATE+" AND entity_id=? AND kind=? AND json_extract(details,'$.trial_id')=? AND id>? ORDER BY id LIMIT 2",(self.job['id'],kind,tid,after)).fetchall()
        if len(rows)!=1 or rows[0]['bytes']>4096 or canonical(json.loads(rows[0]['details']))!=canonical(expected):
            raise StateError('Original financial occurrence event is missing or changed.')
        return rows[0]['id']

    def _load(self,part):
        with self.lab.store.db() as db:
            db.execute('BEGIN');self._owned(db);original=self._event(db,part)
            if original is None:
                raise StateError('The original financial part is not committed.')
            event_id,event=original;path=self.folder/event['filename']
            authority=(event_id,identity(event),event['sha256'])
            if self.unit is not None and part in self.unit and self.unit[part]!=authority:
                raise StateError('Original financial authority changed within the verification unit.')
            if path.stat().st_size>MAX_PART_BYTES or file_hash(path)!=event['sha256']:
                raise StateError('Original financial part bytes changed or exceed their bound.')
            cached=self.cache.get(part)
            if cached is not None and cached[0]==event['sha256']:
                value=cached[1];self.cache.move_to_end(part)
            else:
                with gzip.open(path,'rb') as stream:raw=stream.read(MAX_PART_BYTES+1)
                if len(raw)>MAX_PART_BYTES:
                    raise StateError('Financial part expansion bound exceeded.')
                value=json.loads(raw)
                if len(raw)<=CACHE_BYTES:
                    if cached is not None:
                        self.cache_bytes-=cached[2];del self.cache[part]
                    self.cache[part]=(event['sha256'],value,len(raw));self.cache_bytes+=len(raw)
                    while len(self.cache)>CACHE_PARTS or self.cache_bytes>CACHE_BYTES:
                        _,old=self.cache.popitem(last=False);self.cache_bytes-=old[2]
            if (not isinstance(value,dict) or set(value)!={'format','job_id','payload_hash','plan_hash','part','start','stop','attempt','sets','books'}
                or type(value['format']) is not int or value['format']!=2 or value['job_id']!=self.job['id']
                or any(value[k]!=event[k] for k in ['payload_hash','plan_hash','part','start','stop','attempt'])
                or not isinstance(value['sets'],list) or len(value['sets'])!=2*(event['stop']-event['start'])
                or not isinstance(value['books'],list) or len(value['books'])!=event['book_count']):
                raise StateError('Original financial part content belongs to different inputs or cohort.')
            expected_bindings=[];keys=set()
            for offset,entry in enumerate(value['books']):
                self._book_shape(entry)
                if entry['key'] in keys:
                    raise StateError('Duplicate original book in a financial part.')
                keys.add(entry['key']);expected_bindings.append(dict(book_key=entry['key'],book_offset=offset,book_sha256=entry['sha256']))
            expected_bindings.sort(key=lambda x:x['book_key'])
            if self._bindings(db,part)!=expected_bindings or identity(expected_bindings)!=event['book_bindings_sha256']:
                raise StateError('Original book index cannot be replaced by rehashed derived metadata.')
            seen=set();_index(db,'trade_twin_trial_event_index',TRIAL_INDEX)
            for row in value['sets']:
                outcome=CanonicalOutcome.model_validate(row['outcome']);ordinal=outcome.set_index;policy=outcome.policy
                if (ordinal,policy) in seen or not event['start']<=ordinal<event['stop'] or outcome.seed!=self.payload['seed'] or outcome.plan_hash!=self.plan.plan_hash:
                    raise StateError('Original financial occurrence is duplicated or misbound.')
                seen.add((ordinal,policy))
                trial=self.lab.store._trials.row(db,self.job['id'],ordinal,policy)
                if trial['state'] not in {'checkpointed','completed'} or trial['attempts']!=event['attempt'] or trial['artifact_sha256']!=event['sha256'] or trial['computed_sha256']!=identity(row):
                    raise StateError('Original financial occurrence differs from its trial checkpoint.')
                attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
                if attempt is None or attempt['state']!='checkpointed' or attempt['computed_sha256']!=identity(row) or attempt['artifact_sha256']!=event['sha256']:
                    raise StateError('Original financial occurrence attempt is incomplete.')
                # Earlier interrupted attempts remain; select this attempt's start.
                starts=db.execute("SELECT id,details FROM events INDEXED BY trade_twin_trial_event_index WHERE "+TRIAL_PREDICATE+" AND entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=? AND json_extract(details,'$.attempt')=? ORDER BY id LIMIT 2",(self.job['id'],trial['id'],trial['attempts'])).fetchall()
                expected=dict(trial_id=trial['id'],part=ordinal,window=policy,attempt=trial['attempts'])
                if len(starts)!=1 or canonical(json.loads(starts[0]['details']))!=canonical(expected):
                    raise StateError('Original financial start attempt is missing or changed.')
                computed=computation_event(db,self.job['id'],trial,starts[0]['id'])
                checkpoint=self._trial_event(db,'trial_checkpoint_saved',trial['id'],dict(trial_id=trial['id'],part=ordinal,window=policy,sha256=event['sha256']),computed)
                if checkpoint>=event_id:
                    raise StateError('Original part commit must follow its occurrence checkpoints.')
            if self.unit is not None:
                self.unit[part]=authority
        return value

    def _descriptor(self,match,policy):return self.base|dict(match=match,policy=policy)

    def _book_shape(self,entry):
        if (not isinstance(entry,dict) or set(entry)!={'key','inputs','book','sha256','evidence','evidence_sha256'} or entry['key']!=identity(entry['inputs'])
            or entry['sha256']!=identity(entry['book']) or not isinstance(entry['book'],dict)
            or any(entry['inputs'].get(k)!=v for k,v in self.base.items()) or entry['inputs'].get('policy') not in EXECUTION_POLICIES):
            raise StateError('Original financial book input or complete-content binding changed.')
        from .trade_twin_evidence import book_manifest,verify_manifest
        verify_manifest(entry['evidence'],entry['evidence_sha256'],entry['sha256'])
        if identity(book_manifest(entry['book'],self._control))!=entry['evidence_sha256']:
            raise StateError('Original financial inspection manifest differs from its complete book.')
        book=entry['book']
        if book.get('status')=='complete':
            read_amount(book['net_profit'])
        elif book.get('status')!='failed' or book.get('net_profit') is not None or not book.get('failure'):
            raise StateError('A financial book cannot hide a failed outcome.')

    def _entry(self,key,sha=None,before_part=None):
        if not isinstance(key,str) or re.fullmatch('[a-f0-9]{64}',key) is None:
            raise StateError('Invalid original book key.')
        with self.lab.store.db() as db:
            row=db.execute('SELECT part,book_offset,book_sha256 FROM trade_twin_book_index WHERE job_id=? AND book_key=?',(self.job['id'],key)).fetchone()
        if row is None:
            return None
        if type(row['part']) is not int or type(row['book_offset']) is not int or row['book_offset']<0 or before_part is not None and row['part']>=before_part:
            raise StateError('A reusable book must belong to an earlier original part.')
        cached=self.cache.get(row['part']);verified=None if self.unit is None else self.unit.get(row['part'])
        if cached is not None and verified is not None and cached[0]==verified[2]:
            value=cached[1];self.cache.move_to_end(row['part'])
        else:value=self._load(row['part'])
        if row['book_offset']>=len(value['books']):
            raise StateError('Original book offset is outside its committed part.')
        entry=value['books'][row['book_offset']];self._book_shape(entry)
        if entry['key']!=key or entry['sha256']!=row['book_sha256'] or sha is not None and entry['sha256']!=sha:
            raise StateError('Reusable original book differs from its committed reference.')
        return entry

    def book(self,key,sha):
        self._control();entry=self._entry(key,sha)
        if entry is None:
            raise StateError('The original committed financial book is missing.')
        return json.loads(canonical(entry['book']))

    def _validate_values(self,value):
        local={b['key']:b for b in value['books']};used=set()
        for row in value['sets']:
            outcome=CanonicalOutcome.model_validate(row['outcome']);draw=draw_set(self.plan,self.payload['seed'],outcome.set_index,self._control)
            if canonical(row['draw'])!=canonical(draw) or len(row['members'])!=len(self.plan.sources):
                raise StateError('Original paired draw or whole membership changed.')
            books=[]
            for match,member in zip(draw['matches'],row['members']):
                inputs=self._descriptor(match,outcome.policy);key=identity(inputs)
                if member['source_id']!=match['source_id'] or member['book_key']!=key:
                    raise StateError('Financial member differs from its original deterministic assignment.')
                entry=local.get(key)
                if entry is not None:
                    used.add(key)
                else:entry=self._entry(key,member['book_sha256'],value['part'])
                if (entry is None or set(member)!={'source_id','book_key','book_sha256','book_evidence_sha256'}
                    or entry['sha256']!=member['book_sha256'] or entry['evidence_sha256']!=member['book_evidence_sha256'] or canonical(entry['inputs'])!=canonical(inputs)):
                    raise StateError('Original financial member input/hash is missing or changed.')
                books.append(entry['book'])
            failed=any(b['status']!='complete' for b in books)
            if outcome.trade_count!=len(books) or (outcome.state=='failed')!=failed:
                raise StateError('A failed or partial original cohort cannot become a complete set.')
            if not failed and read_amount(outcome.net_profit)!=exact_total([b['net_profit'] for b in books]):
                raise StateError('Original exact financial set total differs from all its books.')
        if used!=set(local):
            raise StateError('A financial part contains an unreferenced outcome book.')

    def _diagnostic(self,part,attempt,rows,books,active,error):
        value=dict(kind='uncommitted_twin_part_failure',job_id=self.job['id'],part=part,attempt=attempt,
            plan_hash=self.plan.plan_hash,payload_hash=identity(self.payload),error_type=type(error).__name__,
            error=str(error) if isinstance(error,(ValueError,ArithmeticError,StateError,InterruptedError)) else type(error).__name__,
            tentative_sets=rows,tentative_books=books,active_member=active)
        path=self.folder/'failures'/('part-'+str(part).zfill(6)+'-attempt-'+str(attempt).zfill(6)+'.json.gz')
        try:
            if not path.exists():
                compressed_write(path,value)
            with self.lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE');self.lab.store._trials.owned(db,self.job['id'],self.owner)
                self.lab.store.event('twin_part_failed',self.job['id'],dict(part=part,attempt=attempt,filename=path.name,sha256=file_hash(path),error_type=type(error).__name__,tentative_sets=len(rows),tentative_books=len(books)),db);db.execute('COMMIT')
        except (OSError,StateError,sqlite3.DatabaseError):pass

    def execute(self,part):
        rows=[];books=[];attempt=None;active=None
        try:
            with self.lab.store.control_reads(),self._unit():
                self._authority();prefix=self._prefix();first,stop=part_range(self.spec,part)
                if part>prefix:
                    raise StateError('Execute the next original contiguous financial part.')
                if part<prefix:
                    value=self._load(part);self._validate_values(value);self._authority()
                    from .trade_twin_jobs import _checked_source
                    with self.lab.store.db() as db:
                        db.execute('BEGIN IMMEDIATE');self._owned(db);_checked_source(self.lab,self.source,db,self._control)
                        for row in value['sets']:self.lab.store._trials.checkpoint_owned(db,self.job['id'],row['outcome']['set_index'],row['outcome']['policy'],self.owner,row,self._event(db,part)[1]['sha256'])
                        self.lab.store.event('twin_part_reused',self.job['id'],dict(part=part,plan_hash=self.plan.plan_hash),db)
                        self._control();db.execute('COMMIT')
                    return json.loads(canonical(value))
                if not self.plan.eligible:
                    raise StateError('An ineligible whole cohort cannot execute financial parts.')
                with self.lab.store.db() as db:
                    db.execute('BEGIN IMMEDIATE');self._owned(db)
                    attempts=[]
                    for ordinal in range(first,stop):
                        for policy in EXECUTION_POLICIES:attempts.append(self.lab.store._trials.start_owned(db,self.job['id'],ordinal,policy,self.owner))
                    if len(set(attempts))!=1:
                        raise StateError('Original paired part attempts have inconsistent histories.')
                    attempt=attempts[0];db.execute('COMMIT')
                local={}
                for ordinal in range(first,stop):
                    draw=draw_set(self.plan,self.payload['seed'],ordinal,self._control)
                    for policy in EXECUTION_POLICIES:
                        members=[];amounts=[];failures=0
                        for match in draw['matches']:
                            self._control();inputs=self._descriptor(match,policy);key=identity(inputs);active=dict(set_index=ordinal,policy=policy,match=match,book_key=key)
                            entry=local.get(key)
                            if entry is None:
                                entry=self._entry(key,before_part=part)
                            if entry is None:
                                book=freeze(execute_twin(self.prepared['regular'],match,self.payload['strategy'],self.payload['costs'],self.payload['portfolio'],self.prepared['actions'],policy=policy,cancel=self._control,preparation=self.execution_preparation))
                                from .trade_twin_evidence import book_manifest
                                evidence=book_manifest(book,self._control)
                                entry=dict(key=key,inputs=inputs,book=book,sha256=identity(book),evidence=evidence,evidence_sha256=identity(evidence));self._book_shape(entry);local[key]=entry;books.append(entry)
                            if canonical(entry['inputs'])!=canonical(inputs):
                                raise StateError('Cached original book inputs differ from the assignment.')
                            if entry['book']['status']=='complete':
                                amounts.append(entry['book']['net_profit'])
                            else:failures+=1
                            members.append(dict(source_id=match['source_id'],book_key=key,book_sha256=entry['sha256'],book_evidence_sha256=entry['evidence_sha256']))
                        outcome=CanonicalOutcome(plan_hash=self.plan.plan_hash,seed=self.payload['seed'],policy=policy,set_index=ordinal,trade_count=len(members),state='failed' if failures else 'completed',
                            net_profit=None if failures else canonical_amount(exact_total(amounts)),error='At least one original member failed; no partial total is graded.' if failures else None,amount_encoding='canonical-decimal-v1')
                        rows.append(dict(outcome=outcome.model_dump(),draw=draw,members=members))
                value=dict(format=2,job_id=self.job['id'],payload_hash=identity(self.payload),plan_hash=self.plan.plan_hash,part=part,start=first,stop=stop,attempt=attempt,sets=rows,books=books)
                if len(canonical(value).encode())>MAX_PART_BYTES:
                    raise StateError('Financial part serialization working bound exceeded; no subset retained.')
                filename='part-'+str(part).zfill(6)+'-attempt-'+str(attempt).zfill(6)+'.json.gz';path=self.folder/filename
                if path.exists():
                    raise StateError('Original financial attempt must not be overwritten.')
                self._control();compressed_write(path,value);digest=file_hash(path)
                with self.lab.store.db() as db:
                    db.execute('BEGIN IMMEDIATE');self._owned(db)
                    for row in rows:self.lab.store._trials.computed_owned(db,self.job['id'],row['outcome']['set_index'],row['outcome']['policy'],self.owner,row)
                    db.execute('COMMIT')
                self._authority();self._prefix()
                bindings=sorted([dict(book_key=b['key'],book_offset=n,book_sha256=b['sha256']) for n,b in enumerate(books)],key=lambda b:b['book_key'])
                event=dict(part=part,start=first,stop=stop,attempt=attempt,filename=filename,sha256=digest,payload_hash=identity(self.payload),plan_hash=self.plan.plan_hash,book_count=len(books),book_bindings_sha256=identity(bindings))
                from .trade_twin_jobs import _checked_source
                with self.lab.store.db() as db:
                    db.execute('BEGIN IMMEDIATE');self._owned(db);_checked_source(self.lab,self.source,db,self._control)
                    if self._event(db,part) is not None:
                        raise StateError('The original financial part is already committed.')
                    for row in rows:self.lab.store._trials.checkpoint_owned(db,self.job['id'],row['outcome']['set_index'],row['outcome']['policy'],self.owner,row,digest)
                    self.lab.store.event('twin_part_committed',self.job['id'],event,db)
                    event_id=db.execute('SELECT last_insert_rowid()').fetchone()[0]
                    db.execute('INSERT INTO trade_twin_part_index VALUES(?,?,?,?)',(self.job['id'],part,event_id,canonical(event)))
                    db.executemany('INSERT INTO trade_twin_book_index VALUES(?,?,?,?,?)',[(self.job['id'],b['book_key'],part,b['book_offset'],b['book_sha256']) for b in bindings])
                    self._control();db.execute('COMMIT')
                return json.loads(canonical(value))
        except Exception as error:
            if attempt is not None:
                self._diagnostic(part,attempt,rows,books,active,error)
            if isinstance(error,(OSError,sqlite3.DatabaseError,KeyError,TypeError)):
                raise StateError('Original financial part is missing, corrupt or incompatible; no replacement was authorized.') from error
            raise

    def mark_ineligible(self):
        """Record zero generated financial trials from the original sealed plan."""
        if self.plan.eligible:
            raise StateError('An eligible original cohort cannot skip its financial trials.')
        self._authority()
        expected=dict(plan_hash=self.plan.plan_hash,payload_hash=identity(self.payload),
            source_count=len(self.plan.sources),financial_sets_generated=0,ungenerated_occurrences=2*TOTAL_SETS)
        from .trade_twin_jobs import _checked_source
        with self.lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');self._owned(db);_checked_source(self.lab,self.source,db,self._control)
            originals=list(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='twin_financial_sets_not_generated' ORDER BY id LIMIT 2",(self.job['id'],)))
            bad=db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND (attempts!=0 OR state NOT IN ('planned','not_started','not_generated') OR artifact_sha256 IS NOT NULL OR computed_sha256 IS NOT NULL) LIMIT 1",(self.job['id'],)).fetchone()
            if bad is not None or len(originals)>1:
                raise StateError('Original ineligibility cannot erase generated financial work.')
            if originals:
                if canonical(json.loads(originals[0]['details']))!=canonical(expected):
                    raise StateError('Original ineligibility evidence changed.')
                if db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='not_generated'",(self.job['id'],)).fetchone()[0]!=2*TOTAL_SETS:
                    raise StateError('Original ungenerated financial cohort changed.')
            else:
                if db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='not_generated' LIMIT 1",(self.job['id'],)).fetchone():
                    raise StateError('Original ineligibility event is missing.')
                db.execute("UPDATE trial_plans SET state='not_generated',note='The complete original cohort is ineligible; no financial sets generated.' WHERE job_id=? AND role='trade_twin_set'",(self.job['id'],))
                self.lab.store.event('twin_financial_sets_not_generated',self.job['id'],expected,db)
            self._control();db.execute('COMMIT')

    def _finish(self):
        """Reopen every committed original occurrence before exact final grading."""
        from .trade_twin_results import summarize_financial
        self._authority();outcomes={policy:[] for policy in EXECUTION_POLICIES};headers=[]
        if not self.plan.eligible:
            self.mark_ineligible()
        else:
            if self._prefix()!=self.spec['part_count']:
                raise StateError('A partial financial prefix cannot publish a final comparison.')
            for part in range(self.spec['part_count']):
                self._control();value=self._load(part);self._validate_values(value)
                for row in value['sets']:outcomes[row['outcome']['policy']].append(row['outcome'])
                with self.lab.store.db() as db:
                    _,header=self._event(db,part);headers.append(header)
        summaries={policy:summarize_financial(self.plan,self.payload['seed'],policy,outcomes[policy],self._control) for policy in EXECUTION_POLICIES}
        if any(read_amount(summary['real_profit'])!=read_amount(self.source['source_profit']) for summary in summaries.values()):
            raise StateError('Exact original closed-profit baseline changed during grading.')
        with self.lab.store.db() as db:
            books=db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(self.job['id'],)).fetchone()[0]
        manifest=dict(version=1,job_id=self.job['id'],payload_hash=identity(self.payload),plan_hash=self.plan.plan_hash,
            source_authority_hash=self.source['authority_hash'],work_partition=self.spec,ineligible=not self.plan.eligible,parts=headers)
        report=dict(report_type='trade_twins',protocol=self.payload['twin_protocol'],plan_hash=self.plan.plan_hash,
            source_parent=self.payload['twin_parent'],source=self.payload['source'],comparison_eligible=self.plan.eligible,
            summaries=summaries,financial_occurrences=sum(len(v) for v in outcomes.values()),unique_committed_books=books,
            completed_parts=len(headers),manifest_hash=identity(manifest),amount_encoding='canonical-decimal-v1',
            assumptions={k:self.payload[k] for k in ['strategy','costs','portfolio','dataset_id','dataset_manifest_hash','start','end','seed']},
            interpretations=dict(primary='barrier_capped_elapsed_v1',sensitivity='fixed_elapsed_v1'),
            limitations=['Random entry at a modeled market open can differ from the original order type.',
                'Books retain original whole entry quantity and use independent diagnostic financing, not shared portfolio allocation.',
                'Both policies use identical replacement draws. Repeated occurrences and cached books are not additional independent strategies.',
                'Private host-engine parity and historical stock borrow availability remain unverified.'],
            host_engine_parity_verified=False)
        if self.plan.eligible:
            self._prefix()
        self._authority()
        return report,manifest

    def finish(self):
        with self.lab.store.control_reads(),self._unit():
            return self._finish()
