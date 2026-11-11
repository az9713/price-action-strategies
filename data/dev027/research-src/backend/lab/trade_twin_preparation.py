"""Owned outcome-blind preparation, sealed atomically with its original trial.

Financial execution must not begin until this original seal has been verified.
An uncommitted attempt file is retained, never treated as a reusable checkpoint.
"""
from datetime import date, timedelta
from dataclasses import asdict
import gzip
import json
import re

from .config import canonical, identity
from .data import read_manifest
from .result_index import file_hash
from .service import compressed_write
from .store import StateError
from .trade_twin_features import candidate_features
from .trade_twin_jobs import verify_child, _checked_source
from .trade_twin_source import _original_trial_event
from .trade_twins import prepare_plan, _cancel


# This is a visible serialization guard, not a measured memory/throughput claim.
MAX_PREPARED_BYTES = 512 * 1024 * 1024
SEAL_KEYS = {'filename', 'sha256', 'plan_hash', 'payload_hash', 'trial_id', 'attempt'}


def _owned(lab, db, job, owner):
    lab.store._trials.owned(db, job['id'], owner)
    row = db.execute('SELECT cancel_requested FROM jobs WHERE id=?', (job['id'],)).fetchone()
    if row['cancel_requested']:
        raise InterruptedError('Trade-twin preparation canceled before publication.')


def _sealed(lab, job, owner):
    """Read only an original seal and its original trial/attempt/event chain."""
    with lab.store.db() as db:
        db.execute('BEGIN')
        _owned(lab, db, job, owner)
        events = list(db.execute("SELECT id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind='twin_preparation_sealed' ORDER BY id LIMIT 2", (job['id'],)))
        trial = lab.store._trials.row(db, job['id'], 0, 'prepare')
        if not events:
            if trial['artifact_sha256'] is not None or trial['state'] in {'checkpointed', 'completed'}:
                raise StateError('Original preparation seal is missing; replacement is refused.')
            return None
        if len(events) != 1 or events[0]['bytes'] > 16384:
            raise StateError('Exactly one bounded original preparation seal is required.')
        event = events[0];seal = json.loads(event['details'])
        if (not isinstance(seal, dict) or set(seal) != SEAL_KEYS or type(seal['attempt']) is not int or seal['attempt'] < 1
                or seal['attempt'] != trial['attempts'] or seal['trial_id'] != trial['id']
                or seal['filename'] != 'attempt-' + str(seal['attempt']).zfill(6) + '.json.gz'
                or seal['payload_hash'] != identity(job['payload'])
                or trial['state'] != 'checkpointed' or trial['artifact_sha256'] != seal['sha256']):
            raise StateError('Original preparation seal differs from its owned trial.')
        started = _original_trial_event(db, job['id'], 'trial_computation_started', trial['id'],
                                       dict(trial_id=trial['id'], part=0, window='prepare', attempt=seal['attempt']))
        checkpoint = _original_trial_event(db, job['id'], 'trial_checkpoint_saved', trial['id'],
                                          dict(trial_id=trial['id'], part=0, window='prepare', sha256=seal['sha256']), after_id=started)
        if checkpoint >= event['id']:
            raise StateError('Preparation seal must follow its original checkpoint.')
        attempt = db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?', (trial['id'], trial['attempts'])).fetchone()
        if attempt is None or attempt['state'] != 'checkpointed' or attempt['computed_sha256'] != trial['computed_sha256'] or attempt['artifact_sha256'] != seal['sha256']:
            raise StateError('Original preparation attempt is incomplete or changed.')
        if not isinstance(seal['sha256'], str) or re.fullmatch('[a-f0-9]{64}', seal['sha256']) is None:
            raise StateError('Original preparation digest is malformed.')
        path = lab.output_path(job['id']).parent / 'twins/preparation' / seal['filename']
        if path.stat().st_size > MAX_PREPARED_BYTES or file_hash(path) != seal['sha256']:
            raise StateError('Original preparation artifact changed or exceeded its bound.')
        with gzip.open(path, 'rb') as stream:
            raw = stream.read(MAX_PREPARED_BYTES + 1)
        if len(raw) > MAX_PREPARED_BYTES:
            raise StateError('Original preparation serialization working bound exceeded.')
        value = json.loads(raw)
        if identity(value) != trial['computed_sha256'] or value.get('plan', {}).get('plan_hash') != seal['plan_hash']:
            raise StateError('Original preparation content differs from its recorded computation.')
        return seal, value


def _build(lab, job, source, cancel):
    payload = job['payload'];symbols = sorted({s['symbol'] for s in source['sources']})
    manifest = read_manifest(lab.datasets_root, payload['dataset_id'])
    warmup = max(manifest['quality']['start'], (date.fromisoformat(payload['start']) - timedelta(days=365)).isoformat())
    if symbols:
        _, regular, actions, actual_warmup = lab._evaluation_input(payload['dataset_id'], payload['start'], payload['end'],
            expected_manifest=payload['dataset_manifest_hash'], symbols=symbols)
        if actual_warmup != warmup:
            raise StateError('Frozen original warm-up scope changed.')
        features = candidate_features(regular, payload['strategy'], symbols, payload['start'], payload['end'], cancel)
    else:
        regular = None;actions = [];features = dict(moments=[], clock={})
    plan = prepare_plan(source['sources'], features['moments'], features['clock'], payload['start'], payload['end'], source['authority_hash'], cancel)
    value = dict(report_type='trade_twin_preparation', job_id=job['id'], payload_hash=identity(payload),
                 source_authority_hash=source['authority_hash'], source_cohort_hash=identity(source['sources']),
                 prospective_scope=dict(symbols=symbols, start=payload['start'], end=payload['end'], warmup_start=warmup),
                 actions_hash=identity([asdict(a) for a in actions]), plan=plan.json())
    if len(canonical(value).encode()) > MAX_PREPARED_BYTES:
        raise StateError('Trade-twin preparation serialization working bound exceeded; no subset retained.')
    return dict(plan=plan, regular=regular, actions=actions, source=source, sealed=value)


def prepare(lab, job, owner, cancel=None):
    """Seal a complete plan or independently reverify the original saved plan.

    The caller retains lifecycle ownership and must continue to financial work or
    preserve/release the job. This function cannot complete a financial study.
    """
    def controlled():
        return bool(cancel and cancel()) or lab.store.cancellation_requested(job['id'], owner)
    try:
        with lab.store.control_reads():
            _cancel(controlled)
            source = verify_child(lab, job, controlled)
            lab.store.verify_trial_plan(job['id'])
            prior = _sealed(lab, job, owner)
            if prior is None:
                attempt = lab.store.start_trial(job['id'], 0, 'prepare', owner)
            prepared = _build(lab, job, source, controlled)
            value = prepared['sealed']
            if prior is not None:
                seal, saved = prior
                if saved != value or identity(saved) != identity(value):
                    raise StateError('Original outcome-blind plan differs from independently rebuilt inputs.')
            else:
                filename = 'attempt-' + str(attempt).zfill(6) + '.json.gz'
                path = lab.output_path(job['id']).parent / 'twins/preparation' / filename
                if path.exists():
                    raise StateError('An existing preparation attempt must not be overwritten.')
                _cancel(controlled);compressed_write(path, value)
                digest = file_hash(path)
                lab.store.computed_trial(job['id'], 0, 'prepare', owner, value)
                seal = dict(filename=filename, sha256=digest, plan_hash=prepared['plan'].plan_hash,
                            payload_hash=identity(job['payload']), trial_id=identity(dict(job_id=job['id'], part=0, window='prepare')), attempt=attempt)
            closing = verify_child(lab, job, controlled)
            if identity(closing) != identity(source):
                raise StateError('Original source changed during preparation; no plan was sealed.')
            _cancel(controlled)
            with lab.store.db() as db:
                db.execute('BEGIN IMMEDIATE')
                _owned(lab, db, job, owner)
                _checked_source(lab, source, db, controlled)
                lab.store._trials.checkpoint_owned(db, job['id'], 0, 'prepare', owner, value, seal['sha256'])
                if prior is None:
                    if db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='twin_preparation_sealed' LIMIT 1", (job['id'],)).fetchone():
                        raise StateError('Original preparation seal already exists.')
                    lab.store.event('twin_preparation_sealed', job['id'], seal, db)
                else:
                    lab.store.event('twin_preparation_reverified', job['id'], seal, db)
                _cancel(controlled);db.execute('COMMIT')
            return prepared
    except (StateError, InterruptedError):
        raise
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise StateError('Original trade-twin preparation is missing, corrupt or incompatible; no replacement was certified.') from error
