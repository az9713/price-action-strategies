"""Reserve five original account cohorts before any worker can read outcomes.

These use the existing checkpointed independent-search account engine. Each job
keeps a complete explicit configuration plan, its role, and original study link.
"""
import json
import sqlite3
import time
import uuid
from .config import Strategy,canonical,identity
from .data import read_manifest
from .models import Search
from .research import core_hash,require_current_source,study_input_hash
from .research_funnel import FunnelStudy
from .research_funnel_registration import prepare_registration
from .research_family_source import _cancel
from .store import StateError

PREDICATE="kind='search' AND json_valid(payload) AND json_type(payload,'$.funnel_arm')='object'"


def initialize(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS funnel_arm_links(study_id TEXT NOT NULL REFERENCES studies(id),arm_key TEXT NOT NULL,job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),PRIMARY KEY(study_id,arm_key))')
        db.execute("CREATE INDEX IF NOT EXISTS funnel_arm_original_jobs ON jobs(json_extract(payload,'$.funnel_arm.study_id'),id) WHERE "+PREDICATE)


def _study(lab,db,sid):
    row=db.execute('SELECT * FROM studies WHERE id=?',(sid,)).fetchone()
    if row is None:
        raise StateError('Choose an original registered research-funnel study.')
    study=lab.store.decode(row);lab.guard.verify_inputs(study,db);spec=study['spec']
    if spec.get('funnel_version')!=1 or spec.get('core_hash')!=core_hash():
        raise StateError('Research-funnel registration or original engine differs.')
    request=FunnelStudy(**{name:spec[name] for name in FunnelStudy.model_fields if name in spec})
    _,primary,expected,protected=prepare_registration(lab,request)
    if (any(spec.get(key)!=value for key,value in expected.items()) or spec.get('symbols')!=protected
            or spec.get('dataset_manifest_hash')!=identity(primary)):
        raise StateError('Original research arm definitions, assumptions or manifests changed.')
    return study


def _access(lab,db,arm):
    manifest=read_manifest(lab.datasets_root,arm['dataset_context']['dataset_id'])
    lab.guard.check_access(db,[arm['symbol']],manifest['quality']['start'],arm['end'])


def _payload(study,key):
    spec=study['spec'];arm=spec['development_arms'][key];configurations=spec['configurations']
    request=Search(dataset_id=arm['dataset_context']['dataset_id'],start=arm['start'],end=arm['end'],
        name=(study['name']+' / '+key)[:100],count=len(configurations),strategy=Strategy(**configurations[0]),
        costs=spec['costs'],portfolio=spec['portfolio'],seed=spec['seed'],news_calendar_id=spec.get('news_calendar_id'),
        families=sorted({c['family'] for c in configurations}),timeframes=sorted({c['timeframe'] for c in configurations}))
    payload=request.model_dump(mode='json')
    payload.update(configurations=configurations,sampling=None,core_hash=spec['core_hash'],
        dataset_context=arm['dataset_context'],dataset_manifest_hash=arm['dataset_context']['dataset_manifest_hash'],
        evaluation_symbols=[arm['symbol']],study_id=study['id'],
        funnel_arm=dict(study_id=study['id'],study_input_hash=study_input_hash(spec),arm_key=key,arm_hash=identity(arm),
            role=arm['role'],configuration_universe_hash=spec['configuration_universe_hash']))
    payload.update({key:value for key,value in spec.items() if key.startswith('news_')})
    return payload


def _reserved(lab,db,study):
    sid=study['id'];keys=set(study['spec']['development_arms'])
    events=db.execute("SELECT substr(details,1,8193) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind='funnel_arms_frozen' ORDER BY id LIMIT 2",(sid,)).fetchall()
    links=db.execute('SELECT arm_key,job_id FROM funnel_arm_links WHERE study_id=? ORDER BY arm_key LIMIT 6',(sid,)).fetchall()
    children=db.execute("SELECT id,json_extract(payload,'$.funnel_arm.arm_key') arm_key FROM jobs INDEXED BY funnel_arm_original_jobs WHERE "+PREDICATE+" AND json_extract(payload,'$.funnel_arm.study_id')=? ORDER BY id LIMIT 6",(sid,)).fetchall()
    if not events and not links and not children:
        return None
    if len(events)!=1 or events[0]['bytes']>8192 or len(links)!=len(keys) or len(children)!=len(keys):
        raise StateError('Original complete arm reservation is missing or duplicated; replacement jobs are refused.')
    value=json.loads(events[0]['details'])
    if (not isinstance(value,dict) or set(value)!= {'study_input_hash','configuration_universe_hash','arms'}
            or value['study_input_hash']!=study_input_hash(study['spec'])
            or value['configuration_universe_hash']!=study['spec']['configuration_universe_hash']
            or not isinstance(value['arms'],dict) or set(value['arms'])!=keys):
        raise StateError('Original arm reservation does not identify the complete frozen study.')
    mapped={key:item['job_id'] for key,item in value['arms'].items()}
    if (mapped!={row['arm_key']:row['job_id'] for row in links}
            or mapped!={row['arm_key']:row['id'] for row in children}):
        raise StateError('Original arm jobs and reservation links differ.')
    return value


def _verify(lab,db,job,study,reserved):
    current,digest,provenance=lab.store._input_index.verified_inputs(job['id'],db)
    key=current['payload']['funnel_arm']['arm_key']
    if (reserved is None or key not in study['spec']['development_arms'] or current['kind']!='search'
            or provenance!='prespecified' or identity(job['payload'])!=digest
            or current['payload']!=_payload(study,key)
            or reserved['arms'][key]!=dict(job_id=job['id'],payload_hash=digest)):
        raise StateError('Original complete arm inputs or reservation changed.')
    lab.store._trials.verify(job['id'],db);_access(lab,db,study['spec']['development_arms'][key])
    return current['payload']['funnel_arm']


def queue_arms(lab,sid):
    require_current_source()
    try:
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');study=_study(lab,db,sid);reserved=_reserved(lab,db,study)
            if reserved is not None:
                for item in reserved['arms'].values():
                    row=db.execute('SELECT * FROM jobs WHERE id=?',(item['job_id'],)).fetchone()
                    _verify(lab,db,lab.store.decode(row),study,reserved)
                db.execute('COMMIT')
                return dict(study_id=sid,arms={key:item['job_id'] for key,item in reserved['arms'].items()})
            spec=study['spec'];mapped={}
            for key,arm in spec['development_arms'].items():
                _access(lab,db,arm);payload=_payload(study,key);jid=uuid.uuid4().hex;now=time.time()
                db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,'search',canonical(payload),now,now))
                lab.store._trials.freeze(dict(id=jid,kind='search',payload=payload),db)
                lab.store._input_index.add(db,jid,payload);lab.store.event('job_created',jid,dict(kind='search'),db)
                db.execute('INSERT INTO funnel_arm_links VALUES(?,?,?)',(sid,key,jid))
                mapped[key]=dict(job_id=jid,payload_hash=identity(payload))
            value=dict(study_input_hash=study_input_hash(spec),configuration_universe_hash=spec['configuration_universe_hash'],arms=mapped)
            lab.store.event('funnel_arms_frozen',sid,value,db);db.execute('COMMIT')
        return dict(study_id=sid,arms={key:item['job_id'] for key,item in mapped.items()})
    except StateError:
        raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original research-arm reservation is unavailable; no replacement cohort is authorized.') from error


def verify_arm(lab,job,cancel=None):
    require_current_source();_cancel(cancel)
    try:
        sid=job['payload']['funnel_arm']['study_id']
        with lab.store.db() as db:
            db.execute('BEGIN');study=_study(lab,db,sid);reserved=_reserved(lab,db,study)
            value=_verify(lab,db,job,study,reserved)
        _cancel(cancel);require_current_source()
        return value
    except InterruptedError:
        raise
    except StateError:
        raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original research-arm identity is missing or incompatible; no account is authorized.') from error
