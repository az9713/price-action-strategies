"""Read complete original saved search families without prices or new accounts.

One part is decoded at a time. Original roots, inputs, trials, attempts and
checkpoint events are authority; generic derived views are never used here.
"""
from collections.abc import Mapping
import gzip
import hashlib
import io
import json
import re
import sqlite3

from .config import FAMILIES, Strategy, identity
from .dataset_context import validate_context
from .research import core_hash, require_current_source
from .research_funnel import family_average
from .result_index import file_hash
from .store import StateError

MAX_ARTIFACT_BYTES = 512*1024*1024
PREDICATE = "json_valid(details) AND kind IN ('trial_computation_started','trial_checkpoint_saved')"
INDEX = "CREATE INDEX research_family_trial_events ON events(entity_id,kind,json_extract(details,'$.trial_id'),id) WHERE "+PREDICATE


def initialize(store):
    with store.db() as db:
        db.execute(INDEX.replace('CREATE INDEX','CREATE INDEX IF NOT EXISTS',1))


def _cancel(cancel):
    if cancel and cancel():
        raise InterruptedError('Original family inspection canceled; no partial result accepted.')


def _load(path,expected):
    if path.stat().st_size>MAX_ARTIFACT_BYTES:
        raise StateError('Original account artifact exceeds its serialization bound.')
    with path.open('rb') as stream:
        compressed=stream.read(MAX_ARTIFACT_BYTES+1)
    if len(compressed)>MAX_ARTIFACT_BYTES or hashlib.sha256(compressed).hexdigest()!=expected:
        raise StateError('Original account artifact bytes changed.')
    # Hash and decode the same observed bytes, rather than a later file reopen.
    with gzip.GzipFile(fileobj=io.BytesIO(compressed),mode='rb') as stream:
        raw=stream.read(MAX_ARTIFACT_BYTES+1)
    if len(raw)>MAX_ARTIFACT_BYTES:
        raise StateError('Original account expansion bound exceeded; no subset accepted.')
    value=json.loads(raw)
    if not isinstance(value,dict):
        raise StateError('Original account artifact must be a complete object.')
    return value


def _schema(db):
    row=db.execute("SELECT substr(sql,1,4097) sql,length(CAST(sql AS BLOB)) bytes FROM sqlite_master WHERE type='index' AND name='research_family_trial_events'").fetchone()
    if (row is None or row['bytes']>4096 or not isinstance(row['sql'],str)
            or ''.join(row['sql'].split()).lower()!=''.join(INDEX.split()).lower()):
        raise StateError('The bounded original family event index is missing or changed.')


def _root_event(db,jid):
    rows=db.execute("SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id LIMIT 2",(jid,)).fetchall()
    if len(rows)!=1 or rows[0]['bytes']>4096:
        raise StateError('Exactly one bounded original result publication is required.')
    value=json.loads(rows[0]['details'])
    if (not isinstance(value,dict) or set(value)!={'sha256'} or not isinstance(value['sha256'],str)
            or re.fullmatch('[a-f0-9]{64}',value['sha256']) is None):
        raise StateError('Original result digest is malformed.')
    return rows[0]['id'],value['sha256']


def _trial_events(db,jid,trial,artifact,result_event,window='report'):
    _schema(db)
    prefix="FROM events INDEXED BY research_family_trial_events WHERE "+PREDICATE+" AND entity_id=? AND kind=? AND json_extract(details,'$.trial_id')=?"
    args=(jid,'trial_computation_started',trial['id'])
    bad=db.execute("SELECT 1 "+prefix+" AND (json_type(details,'$.attempt') IS NOT 'integer' OR json_extract(details,'$.attempt')<1 OR json_extract(details,'$.attempt')>?) LIMIT 1",(*args,trial['attempts'])).fetchone()
    if bad is not None:
        raise StateError('Original family attempt history is malformed.')
    starts=db.execute('SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes '+prefix+" AND json_extract(details,'$.attempt')=? ORDER BY id LIMIT 2",(*args,trial['attempts'])).fetchall()
    expected=dict(trial_id=trial['id'],part=trial['part'],window=window,attempt=trial['attempts'])
    if len(starts)!=1 or starts[0]['bytes']>4096 or json.loads(starts[0]['details'])!=expected:
        raise StateError('Original family computation start is missing or changed.')
    checkpoints=db.execute('SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes '+prefix+' AND id>? ORDER BY id LIMIT 2',(jid,'trial_checkpoint_saved',trial['id'],starts[0]['id'])).fetchall()
    expected=dict(trial_id=trial['id'],part=trial['part'],window=window,sha256=artifact)
    if (len(checkpoints)!=1 or checkpoints[0]['bytes']>4096 or json.loads(checkpoints[0]['details'])!=expected
            or checkpoints[0]['id']>=result_event):
        raise StateError('Original family checkpoint or publication order changed.')
    return starts[0]['id'],checkpoints[0]['id']


class FamilyReports(Mapping):
    def __init__(self,lab,jid,family,cancel=None,*,_all_families=False):
        _cancel(cancel);require_current_source()
        if not isinstance(jid,str) or re.fullmatch('[a-f0-9]{32}',jid) is None or (family not in FAMILIES and not (_all_families and family is None)):
            raise StateError('Choose an original search and a known strategy family.')
        self.lab=lab;self.jid=jid;self.family=family;self.cancel=cancel;self.used={}
        with lab.store.db() as db:
            db.execute('BEGIN');_schema(db)
            self.job,self.payload_hash,provenance=lab.store._input_index.verified_inputs(jid,db)
            if self.job['status']!='completed' or self.job['kind'] not in {'search','spread_accounts'} or provenance!='prespecified':
                raise StateError('A complete original prespecified search/account cohort is required.')
            lab.store._trials.verify(jid,db)
            malformed=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind IN ('trial_computation_started','trial_checkpoint_saved') AND (NOT json_valid(details) OR length(CAST(details AS BLOB))>4096) LIMIT 1",(jid,)).fetchone()
            if malformed is not None:
                raise StateError('Original family trial metadata is malformed or oversized.')
            incomplete=db.execute("SELECT 1 FROM trial_plans WHERE job_id=? AND (window!='report' OR state!='completed' OR provenance!='prespecified') LIMIT 1",(jid,)).fetchone()
            if incomplete:
                raise StateError('The complete original family source contains unfinished or legacy trials.')
            self.result_event,self.root_sha=_root_event(db,jid)
        self.payload=self.job['payload'];self.root_path=lab.output_path(jid)
        self.context=validate_context(self.payload.get('dataset_context'))
        if (self.context['dataset_id']!=self.payload['dataset_id'] or self.context['dataset_manifest_hash']!=self.payload['dataset_manifest_hash']):
            raise StateError('Original family dataset context differs from frozen inputs.')
        self.symbols=self.payload.get('evaluation_symbols',self.context['symbols'])
        if (not isinstance(self.symbols,list) or not self.symbols or len(set(self.symbols))!=len(self.symbols)
                or set(self.symbols)-set(self.context['symbols'])):
            raise StateError('Original evaluated instruments are malformed.')
        self._access()
        configurations=self.payload.get('configurations')
        if not isinstance(configurations,list) or not configurations or len(configurations)>100000:
            raise StateError('The complete original supported configuration plan is required.')
        self.config_ids=[identity(value) for value in configurations]
        if len(set(self.config_ids))!=len(self.config_ids):
            raise StateError('Original family plan contains duplicate versions.')
        root=_load(self.root_path,self.root_sha)
        if (root.get('job_id')!=jid or root.get('kind')!=self.job['kind'] or root.get('payload_hash')!=self.payload_hash
                or root.get('core_hash')!=self.payload['core_hash'] or type(root.get('count')) is not int
                or root['count']!=len(configurations) or not isinstance(root.get('rows'),list) or len(root['rows'])!=len(configurations)):
            raise StateError('Original complete result/configuration plan differs.')
        self.rows={};self.parts={};self.configurations=[]
        for part,(configuration,row) in enumerate(zip(configurations,root['rows'])):
            _cancel(cancel)
            if (not isinstance(row,dict) or type(row.get('part')) is not int or row['part']!=part
                    or row.get('config_id')!=self.config_ids[part] or row.get('config')!=configuration
                    or not isinstance(row.get('report_sha256'),str) or re.fullmatch('[a-f0-9]{64}',row['report_sha256']) is None):
                raise StateError('Original result rows omit or replace frozen versions.')
            if _all_families or configuration.get('family')==family:
                model=Strategy(**configuration)
                if identity(model)!=self.config_ids[part]:
                    raise StateError('Original configuration encoding is incompatible; no historical identity was rewritten.')
                self.parts[self.config_ids[part]]=part;self.rows[part]=row;self.configurations.append(model)
        if not self.parts:
            raise StateError('The original experiment contains no versions of this family.')

    def _access(self):
        self.lab.guard.access(self.symbols,self.payload['start'],self.payload['end'],'saved_family_source',record=False)

    def __len__(self):
        return len(self.parts)

    def __iter__(self):
        return iter(self.parts)

    def _trial(self,db,part,digest,computed=None):
        trial=self.lab.store._trials.row(db,self.jid,part,'report')
        if (trial['state']!='completed' or trial['role']!='strategy' or trial['provenance']!='prespecified'
                or trial['config_id']!=self.config_ids[part] or trial['attempts']<1
                or trial['artifact_sha256']!=digest or computed is not None and trial['computed_sha256']!=computed):
            raise StateError('Original completed family trial changed.')
        attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
        if (attempt is None or attempt['state']!='checkpointed' or attempt['artifact_sha256']!=digest
                or attempt['computed_sha256']!=trial['computed_sha256']):
            raise StateError('Original completed family attempt changed.')
        events=_trial_events(db,self.jid,trial,digest,self.result_event)
        return trial['computed_sha256'],trial['attempts'],events

    def __getitem__(self,key):
        _cancel(self.cancel)
        part=self.parts[key];row=self.rows[part]
        path=self.root_path.parent/'parts'/(str(part).zfill(6)+'.json.gz')
        value=_load(path,row['report_sha256'])
        if (value.get('config_id')!=key or value.get('payload_hash')!=self.payload_hash or value.get('core_hash')!=self.payload['core_hash']
                or not isinstance(value.get('report'),dict) or value['report'].get('core_hash')!=self.payload['core_hash']):
            raise StateError('Original family part/input identity changed.')
        report=value['report'];computed=identity(report)
        with self.lab.store.db() as db:
            db.execute('BEGIN');marker=self._trial(db,part,row['report_sha256'],computed)
        if part in self.used and self.used[part]!=marker:
            raise StateError('Original family occurrence changed between streamed reads.')
        self.used[part]=marker
        return report

    def guard(self):
        _cancel(self.cancel);require_current_source();self._access()
        with self.lab.store.db() as db:
            db.execute('BEGIN')
            job,digest,provenance=self.lab.store._input_index.verified_inputs(self.jid,db)
            if (job['status']!='completed' or job['kind']!=self.job['kind'] or digest!=self.payload_hash or provenance!='prespecified'
                    or _root_event(db,self.jid)!=(self.result_event,self.root_sha) or file_hash(self.root_path)!=self.root_sha):
                raise StateError('Original family source changed during inspection.')
            self.lab.store._trials.verify(self.jid,db)
            for part,marker in self.used.items():
                _cancel(self.cancel)
                path=self.root_path.parent/'parts'/(str(part).zfill(6)+'.json.gz')
                if file_hash(path)!=self.rows[part]['report_sha256'] or self._trial(db,part,self.rows[part]['report_sha256'],marker[0])!=marker:
                    raise StateError('Original family part/occurrence changed before publication.')


def read_saved_family(lab,jid,family,cancel=None):
    try:
        source=FamilyReports(lab,jid,family,cancel)
        value=family_average(source.configurations,source,cancel=cancel)
        source.guard()
        return value | dict(source_authority=dict(original_job_id=jid,parts=list(source.parts.values()),
            payload_hash=source.payload_hash,root_sha256=source.root_sha,original_result_event_id=source.result_event,
            original_core_hash=source.payload['core_hash'],analysis_core_hash=core_hash(),original_saved_accounts_verified=True,
            price_or_signal_recomputation=False,derived_result_views_used=False))
    except InterruptedError:
        raise
    except (OSError,sqlite3.DatabaseError,ValueError,TypeError,KeyError) as error:
        raise StateError('Original saved family evidence is missing, corrupt or incompatible; no accounts were recomputed.') from error
