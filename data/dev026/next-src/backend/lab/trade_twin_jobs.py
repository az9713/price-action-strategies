"""Original, atomic reservations for paired whole-cohort trade-twin studies.

This module does not simulate prices or produce financial outcomes. The original
account remains authority; links and bounded projections are checked against it.
"""
import json
import re
import sqlite3
import time
import uuid

from .config import canonical, identity
from .store import StateError
from datetime import date, timedelta
from .data import read_manifest
from .result_index import file_hash
from .trade_twin_source import read_saved_source, _saved_state
from .trade_twins import DRAW_POLICY, EXECUTION_POLICIES, TOTAL_SETS, _cancel


PROTOCOL = dict(version=1, draw_policy=DRAW_POLICY,
                sets_per_policy=TOTAL_SETS, policies=list(EXECUTION_POLICIES))
INHERIT = ('dataset_id', 'dataset_manifest_hash', 'dataset_context', 'context',
           'start', 'end', 'seed', 'costs', 'portfolio', 'news_dates',
           'news_calendar_id', 'news_calendar')
PARENT_EXPR = "json_extract(projection,'$.twin_parent.job_id')"
PART_EXPR = "json_extract(projection,'$.twin_parent.part')"
CHILD_PREDICATE = "json_valid(projection) AND json_type(projection,'$.twin_parent')='object'"
CHILD_INDEX = ('CREATE INDEX trade_twin_child_parent_index ON job_input_index('
               + PARENT_EXPR + ',' + PART_EXPR + ',job_id) WHERE ' + CHILD_PREDICATE)
ORIGINAL_PREDICATE = "kind='trade_twins' AND json_valid(payload)"
ORIGINAL_INDEX = ("CREATE INDEX trade_twin_original_parent_index ON jobs("
                  "json_extract(payload,'$.twin_parent.job_id'),json_extract(payload,'$.twin_parent.part'),id) WHERE " + ORIGINAL_PREDICATE)
EVENT_PREDICATE = "kind='trade_twins_frozen' AND json_valid(details)"
EVENT_INDEX = ("CREATE INDEX trade_twin_parent_event_index ON events(entity_id,"
               "json_extract(details,'$.part'),id) WHERE " + EVENT_PREDICATE)


def initialize(store):
    """Schema setup only; never reconstruct missing original reservations."""
    with store.db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS trade_twin_links(
            parent_id TEXT NOT NULL REFERENCES jobs(id),part INTEGER NOT NULL,
            child_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),
            PRIMARY KEY(parent_id,part),CHECK(part>=0))''')
        for statement in (CHILD_INDEX, ORIGINAL_INDEX, EVENT_INDEX):
            db.execute(statement.replace('CREATE INDEX', 'CREATE INDEX IF NOT EXISTS', 1))
    from .trade_twin_parts import initialize as initialize_parts
    initialize_parts(store)


def _index(db, name, expected):
    row = db.execute("SELECT substr(sql,1,4097) sql,length(CAST(sql AS BLOB)) bytes FROM sqlite_master WHERE type='index' AND name=?", (name,)).fetchone()
    if row is None or row['bytes'] > 4096 or ''.join(row['sql'].split()).lower() != ''.join(expected.split()).lower():
        raise StateError('Original trade-twin reservation index is unavailable; no replacement is authorized.')


def _children(db, parent_id, part):
    _index(db, 'trade_twin_child_parent_index', CHILD_INDEX)
    rows = list(db.execute('SELECT substr(job_id,1,33) job_id,length(CAST(job_id AS BLOB)) bytes FROM job_input_index INDEXED BY trade_twin_child_parent_index WHERE '
                          + CHILD_PREDICATE + ' AND (' + PARENT_EXPR + ')=? AND (' + PART_EXPR + ')=? ORDER BY job_id LIMIT 2', (parent_id, part)))
    if any(r['bytes'] != 32 or not isinstance(r['job_id'], str) or re.fullmatch('[a-f0-9]{32}', r['job_id']) is None for r in rows):
        raise StateError('Original trade-twin reservation metadata is malformed.')
    _index(db, 'trade_twin_original_parent_index', ORIGINAL_INDEX)
    originals=list(db.execute("SELECT substr(id,1,33) job_id,length(CAST(id AS BLOB)) bytes FROM jobs INDEXED BY trade_twin_original_parent_index WHERE "
                              + ORIGINAL_PREDICATE + " AND json_extract(payload,'$.twin_parent.job_id')=? AND json_extract(payload,'$.twin_parent.part')=? ORDER BY id LIMIT 2", (parent_id,part)))
    ids=[r['job_id'] for r in rows]
    if any(r['bytes']!=32 or not isinstance(r['job_id'],str) or re.fullmatch('[a-f0-9]{32}',r['job_id']) is None for r in originals) or [r['job_id'] for r in originals]!=ids:
        raise StateError('Original trade-twin jobs differ from their bounded reverse reservations.')
    return ids


def _payload(parent, source):
    original = parent['payload']
    from .trade_twin_parts import partition
    return {k: original[k] for k in INHERIT if k in original} | dict(
        name=('Trade twins: ' + original.get('name', 'original account'))[:100],
        core_hash=original['core_hash'], strategy=source['assumptions']['configuration'],
        twin_protocol=json.loads(canonical(PROTOCOL)), work_partition=partition(source['source_count']),
        twin_parent=dict(job_id=source['job_id'], part=source['part'],
                         authority_hash=source['authority_hash'], authority=source['authority']),
        source={k: source[k] for k in ('report_hash', 'source_count', 'source_profit', 'reported_source_profit', 'cashflow_policy', 'cashflow_audit_hash', 'cashflow_precision_difference', 'marked_account_profit', 'profit_residual')}
               | dict(cohort_hash=identity(source['sources'])))


def occurrences(payload):
    """All financial occurrences are prespecified; preparation is separate work."""
    if identity(payload.get('twin_protocol')) != identity(PROTOCOL):
        raise StateError('Both original 10000-set trade-twin policies are mandatory.')
    descriptor = dict(protocol=PROTOCOL, parent=payload['twin_parent'], source=payload['source'],
                      strategy=payload['strategy'])
    yield 0, 'prepare', 'trade_twin_preparation', descriptor
    for ordinal in range(TOTAL_SETS):
        for policy in EXECUTION_POLICIES:
            yield ordinal, policy, 'trade_twin_set', descriptor | dict(policy=policy)


def _existing(store, db, payload):
    binding = payload['twin_parent'];parent_id = binding['job_id'];part = binding['part']
    link = db.execute('SELECT child_id FROM trade_twin_links WHERE parent_id=? AND part=?', (parent_id, part)).fetchone()
    children = _children(db, parent_id, part)
    _index(db, 'trade_twin_parent_event_index', EVENT_INDEX)
    events = list(db.execute("SELECT substr(details,1,8193) details,length(CAST(details AS BLOB)) bytes FROM events INDEXED BY trade_twin_parent_event_index WHERE "
                             + EVENT_PREDICATE + " AND entity_id=? AND json_extract(details,'$.part')=? ORDER BY id LIMIT 2", (parent_id, part)))
    if (link is None and children) or (link is not None and children != [link['child_id']]):
        raise StateError('Original trade-twin child reservation is missing or inconsistent; no replacement is authorized.')
    if len(events) > 1 or bool(events) != (link is not None):
        raise StateError('Original trade-twin reservation event is missing or inconsistent.')
    if link is None:
        return None
    if events[0]['bytes'] > 8192 or json.loads(events[0]['details']) != dict(child_id=link['child_id'], **binding):
        raise StateError('Original trade-twin reservation event changed.')
    child, digest, provenance = store._input_index.verified_inputs(link['child_id'], db)
    if child['kind'] != 'trade_twins' or provenance != 'prespecified' or digest != identity(payload):
        raise StateError('Original linked trade-twin inputs changed.')
    cached = db.execute('SELECT * FROM job_input_index WHERE job_id=?', (child['id'],)).fetchone()
    if cached is None:
        raise StateError('Original trade-twin input summary is missing.')
    try:
        projection, _ = store._input_index.checked(dict(cached))
    except (ValueError, KeyError, TypeError) as error:
        raise StateError('Original trade-twin input summary changed.') from error
    if projection.get('twin_parent') != binding or cached['payload_sha256'] != digest:
        raise StateError('Original trade-twin reverse reservation differs from its inputs.')
    store._trials.verify(child['id'], db)
    return child


def _checked_source(lab, source, db, cancel=None):
    """Recheck original registration, full selected trial, scope and source bytes."""
    _cancel(cancel)
    from .research import require_current_source
    require_current_source()
    parent_id=source['job_id'];part=source['part']
    parent, configuration, binding = _saved_state(lab, parent_id, part, db=db)
    if binding != source['authority'] or configuration != source['assumptions']['configuration']:
        raise StateError('Original source changed before trade-twin reservation.')
    p=parent['payload'];manifest=read_manifest(lab.datasets_root,p['dataset_id'])
    if identity(manifest)!=p['dataset_manifest_hash']:
        raise StateError('Original source manifest changed before reservation.')
    symbols=p['evaluation_symbols'] if parent['kind']=='spread_accounts' else manifest['quality']['symbols']
    warmup=max(manifest['quality']['start'],(date.fromisoformat(p['start'])-timedelta(days=365)).isoformat())
    lab.guard.check_access(db,symbols,warmup,p['end'])
    if file_hash(lab.datasets_root/p['dataset_id']/'minutes.parquet')!=manifest['parquet_sha256'] or file_hash(lab.output_path(parent_id))!=binding['root_sha256']:
        raise StateError('Original source bytes changed before reservation.')
    if parent['kind']!='experiment':
        path=lab.output_path(parent_id).parent/'parts'/(str(part).zfill(6)+'.json.gz')
        sidecar=path.with_suffix('.sha256.json')
        if file_hash(path)!=binding['artifact_sha256'] or sidecar.stat().st_size>4096 or json.loads(sidecar.read_text(encoding='utf-8'))!={'sha256':binding['artifact_sha256']}:
            raise StateError('Original selected account part changed before reservation.')
    _cancel(cancel);require_current_source()
    return parent

def create(lab, parent_id, part=0, cancel=None):
    """Reserve once, or return the same original child, including failed children.

    The full source reader runs first. Its original database binding, protected
    scope and input/artifact bytes are then rechecked in the write reservation.
    A worker must repeat full authority before work and before publication.
    """
    source = read_saved_source(lab, parent_id, part, cancel)
    _cancel(cancel)
    store = lab.store
    try:
        with store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            parent = _checked_source(lab, source, db, cancel)
            payload = _payload(parent, source)
            existing = _existing(store, db, payload)
            if existing is not None:
                _cancel(cancel);db.execute('COMMIT')
                return existing
            child_id = uuid.uuid4().hex;now = time.time()
            _cancel(cancel)
            db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',
                       (child_id, 'trade_twins', canonical(payload), now, now))
            store._trials.freeze(dict(id=child_id, kind='trade_twins', payload=payload), db)
            store._input_index.add(db, child_id, payload)
            store.event('job_created', child_id, dict(kind='trade_twins'), db)
            db.execute('INSERT INTO trade_twin_links VALUES(?,?,?)', (parent_id, part, child_id))
            store.event('trade_twins_frozen', parent_id, dict(child_id=child_id, **payload['twin_parent']), db)
            _cancel(cancel);db.execute('COMMIT')
        return store.job(child_id)
    except (StateError, InterruptedError):
        raise
    except (sqlite3.DatabaseError, KeyError, TypeError, ValueError) as error:
        raise StateError('Original trade-twin reservation is missing, corrupt or incompatible; no replacement is authorized.') from error


def verify_child(lab, job, cancel=None):
    """Repeat original source/link/input/plan authority before work/publication."""
    _cancel(cancel)
    if job.get('kind') != 'trade_twins':
        raise StateError('Expected an original trade-twin job.')
    try:
        binding = job['payload']['twin_parent']
        source = read_saved_source(lab, binding['job_id'], binding['part'], cancel)
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            parent = _checked_source(lab, source, db, cancel)
            payload = _payload(parent, source)
            if payload != job['payload']:
                raise StateError('Frozen trade-twin source or inherited assumptions changed.')
            original = _existing(lab.store, db, payload)
            if original is None or original['id'] != job['id']:
                raise StateError('Trade-twin job does not own the original reservation.')
        _cancel(cancel)
        return source
    except (StateError, InterruptedError):
        raise
    except (sqlite3.DatabaseError, KeyError, TypeError, ValueError) as error:
        raise StateError('Original trade-twin authority is missing, corrupt or incompatible.') from error
