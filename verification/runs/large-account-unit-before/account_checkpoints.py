"""Owned account-part publication; uncommitted files never authorize reuse."""
import json,os,shutil,uuid
from .config import identity,canonical
from .research import require_current_source
from .research_family_source import PREDICATE,_schema,_trial_events,_load
from .result_index import file_hash
from .store import StateError


def preflight(lab,jid):
    with lab.store.db() as db:
        _schema(db)
        bad=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind IN ('trial_computation_started','trial_checkpoint_saved') AND (NOT json_valid(details) OR length(CAST(details AS BLOB))>4096) LIMIT 1",(jid,)).fetchone()
        if bad is not None:
            raise StateError('Original account checkpoint metadata is malformed or oversized.')


def _events(db,jid,trial,kind,attempt=None):
    query='SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY research_family_trial_events WHERE '+PREDICATE+" AND entity_id=? AND kind=? AND json_extract(details,'$.trial_id')=?"
    args=[jid,kind,trial['id']]
    if attempt is not None:
        query+=" AND json_type(details,'$.attempt')='integer' AND json_extract(details,'$.attempt')=?";args.append(attempt)
    return db.execute(query+' ORDER BY id LIMIT 2',args).fetchall()


def _committed(lab,db,jid,part,windows,value,digest):
    _schema(db);committed=set()
    for window in windows:
        row=lab.store._trials.row(db,jid,part,window)
        saved=_events(db,jid,row,'trial_checkpoint_saved')
        claimed=row['artifact_sha256'] is not None or bool(saved) or row['state'] in {'checkpointed','completed'}
        if not claimed:continue
        if (value is None or value.get('config_id')!=row['config_id'] or not isinstance(value.get(window),dict) or row['state'] not in {'checkpointed','completed'}
                or row['artifact_sha256']!=digest or row['computed_sha256']!=identity(value[window]) or row['attempts']<1):
            raise StateError('Original committed account checkpoint is missing or changed.')
        attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(row['id'],row['attempts'])).fetchone()
        if (attempt is None or attempt['state']!='checkpointed' or attempt['artifact_sha256']!=digest
                or attempt['computed_sha256']!=row['computed_sha256']):
            raise StateError('Original committed account attempt changed.')
        _trial_events(db,jid,row,digest,2**63-1,window)
        committed.add(window)
    return committed


def load_checkpoint(lab,jid,part,path,receipt,context,windows):
    require_current_source();value=None;digest=None
    try:
        if path.exists():
            digest=file_hash(path)
            if receipt.exists():
                if receipt.stat().st_size>4096:raise StateError('Original account receipt is oversized.')
                declared=json.loads(receipt.read_text(encoding='utf-8'))
                if declared!={'sha256':digest}:raise StateError('Original account checkpoint was modified: receipt differs from its bytes.')
            value=_load(path,digest)
            if any(value.get(key)!=item for key,item in context.items()):
                raise StateError('Account checkpoint belongs to different original inputs.')
        with lab.store.db() as db:
            db.execute('BEGIN');committed=_committed(lab,db,jid,part,windows,value,digest)
        return value,committed,digest
    except StateError:raise
    except (OSError,ValueError,TypeError,KeyError,EOFError) as error:
        raise StateError('Original account checkpoint files are unavailable or incompatible.') from error


def _computed(lab,db,jid,part,window,value):
    row=lab.store._trials.row(db,jid,part,window);digest=identity(value)
    attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(row['id'],row['attempts'])).fetchone()
    if (row['state']!='computed' or row['computed_sha256']!=digest or row['attempts']<1 or attempt is None
            or attempt['state']!='computed' or attempt['computed_sha256']!=digest):
        raise StateError('An unfinished account file cannot replace an actual recorded computation.')
    starts=_events(db,jid,row,'trial_computation_started',row['attempts'])
    expected=dict(trial_id=row['id'],part=part,window=window,attempt=row['attempts'])
    if len(starts)!=1 or starts[0]['bytes']>4096 or json.loads(starts[0]['details'])!=expected:
        raise StateError('Original account computation start is missing or changed.')


def publish_checkpoint(worker,job,part,path,receipt,value,windows,cancel,write,write_receipt):
    require_current_source();jid=job['id']
    candidate=path.parent/('unpublished-part-'+worker.owner+'-'+uuid.uuid4().hex+'.json.gz')
    write(candidate,value);digest=file_hash(candidate)
    if cancel():raise InterruptedError('Account stopped before checkpoint publication.')
    with worker.lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');worker.lab.store._trials.owned(db,jid,worker.owner)
        worker.lab.store._trials.verify(jid,db);require_current_source()
        if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(jid,)).fetchone()[0]:
            raise InterruptedError('Account stopped at checkpoint publication.')
        committed=_committed(worker.lab,db,jid,part,windows,value,digest)
        if committed and (not path.exists() or file_hash(path)!=digest):
            raise StateError('An earlier committed window changed before checkpoint publication.')
        for window in windows:
            if window not in committed:_computed(worker.lab,db,jid,part,window,value[window])
        if path.exists() and not committed and file_hash(path)!=digest:
            # Preserve different uncommitted bytes rather than deleting history.
            shutil.copyfile(path,path.parent/('orphan-part-'+uuid.uuid4().hex+'.json.gz'))
        os.replace(candidate,path);write_receipt(receipt,{'sha256':digest})
        for window in windows:
            worker.lab.store._trials.checkpoint_owned(db,jid,part,window,worker.owner,value[window],digest)
        db.execute('COMMIT')
    return digest


MAX_BATCH_ACCOUNTS=8
MAX_BATCH_ENCODED_BYTES=8*1024*1024


def publish_checkpoints(worker,job,items,cancel,write,write_receipt):
    """Bind distinct original accounts in one bounded exclusive writer snapshot.

    Computations/attempts and files remain individual. The original complete
    plan check is shared only inside this transaction, never between units.
    """
    if not isinstance(items,(list,tuple)) or not 1<=len(items)<=MAX_BATCH_ACCOUNTS:
        raise StateError('Choose one to8 original account checkpoints per publication unit.')
    if any(not isinstance(item,(list,tuple)) or len(item)!=5 for item in items):
        raise StateError('Original account checkpoint records are malformed.')
    parts=[item[0] for item in items]
    paths=[str(path.resolve()) for item in items for path in item[1:3]]
    if len(set(parts))!=len(parts) or len(set(paths))!=len(paths):
        raise StateError('Original account publication parts and paths must be distinct.')
    if len(items)==1:
        return [publish_checkpoint(worker,job,*items[0],cancel,write,write_receipt)]
    if sum(len(canonical(item[3]).encode()) for item in items)>MAX_BATCH_ENCODED_BYTES:
        raise StateError('Multiple account reports exceed the bounded encoded publication budget.')
    require_current_source();jid=job['id'];prepared=[]
    for part,path,receipt,value,windows in items:
        if cancel():raise InterruptedError('Accounts stopped before private checkpoint preparation.')
        candidate=path.parent/('unpublished-part-'+worker.owner+'-'+uuid.uuid4().hex+'.json.gz')
        write(candidate,value)
        prepared.append((part,path,receipt,value,windows,candidate,file_hash(candidate)))
    if cancel():raise InterruptedError('Accounts stopped before checkpoint publication.')
    with worker.lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');worker.lab.store._trials.owned(db,jid,worker.owner)
        worker.lab.store._trials.verify(jid,db);require_current_source()
        # Validate the complete unit before promoting its first file. All
        # immutable inputs stay in this same exclusive writer snapshot.
        for part,path,receipt,value,windows,candidate,digest in prepared:
            if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(jid,)).fetchone()[0]:
                raise InterruptedError('Accounts stopped at checkpoint publication.')
            if file_hash(candidate)!=digest:
                raise StateError('Private account checkpoint candidate changed before publication.')
            committed=_committed(worker.lab,db,jid,part,windows,value,digest)
            if committed and (not path.exists() or file_hash(path)!=digest):
                raise StateError('An earlier committed account changed before batch publication.')
            for window in windows:
                if window not in committed:_computed(worker.lab,db,jid,part,window,value[window])
        for part,path,receipt,value,windows,candidate,digest in prepared:
            worker.lab.store._trials.owned(db,jid,worker.owner)
            if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(jid,)).fetchone()[0]:
                raise InterruptedError('Accounts stopped during checkpoint publication.')
            if file_hash(candidate)!=digest:
                raise StateError('Private account checkpoint candidate changed during publication.')
            committed=_committed(worker.lab,db,jid,part,windows,value,digest)
            if committed and (not path.exists() or file_hash(path)!=digest):
                raise StateError('An earlier committed account changed during batch publication.')
            if path.exists() and not committed and file_hash(path)!=digest:
                shutil.copyfile(path,path.parent/('orphan-part-'+uuid.uuid4().hex+'.json.gz'))
            os.replace(candidate,path);write_receipt(receipt,{'sha256':digest})
            for window in windows:
                worker.lab.store._trials.checkpoint_owned(db,jid,part,window,worker.owner,value[window],digest)
        require_current_source();worker.lab.store._trials.owned(db,jid,worker.owner)
        if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(jid,)).fetchone()[0]:
            raise InterruptedError('Accounts stopped before the publication unit committed.')
        db.execute('COMMIT')
    return [item[-1] for item in prepared]


def reuse_checkpoint(worker,job,part,path,receipt,context,windows,cancel):
    value,committed,digest=load_checkpoint(worker.lab,job['id'],part,path,receipt,context,windows)
    if committed!=set(windows):raise StateError('Only original committed account windows may be reused.')
    with worker.lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');worker.lab.store._trials.owned(db,job['id'],worker.owner)
        require_current_source()
        if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(job['id'],)).fetchone()[0]:
            raise InterruptedError('Account stopped before original checkpoint reuse.')
        if file_hash(path)!=digest or _committed(worker.lab,db,job['id'],part,windows,value,digest)!=set(windows):
            raise StateError('Original account changed before checkpoint reuse.')
        if not receipt.exists():
            # The sidecar is derived. Original attempts/events and file bytes,
            # rather than the sidecar's presence, authorize this owned repair.
            from .data import atomic_json
            atomic_json(receipt,{'sha256':digest})
            worker.lab.store.event('account_receipt_restored',job['id'],dict(part=part,sha256=digest),db)
        for window in windows:
            worker.lab.store._trials.checkpoint_owned(db,job['id'],part,window,worker.owner,value[window],digest)
        db.execute('COMMIT')
    return value,digest
