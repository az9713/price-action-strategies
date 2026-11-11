"""Owned saved-family analyses. Original financial accounts are never rerun.

One analysis occurrence retains the complete source cohort and its witnesses.
This is descriptive research aggregation, not another strategy trial or final test.
"""
import json
import sqlite3
import time
import uuid
from .config import identity
from .research import core_hash,require_current_source
from .research_funnel import family_average
from .research_family_source import FamilyReports,_cancel,_load,_root_event,_trial_events
from .result_index import file_hash
from .store import StateError


def initialize(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS family_analysis_links(parent_id TEXT NOT NULL REFERENCES jobs(id),family TEXT NOT NULL,child_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),PRIMARY KEY(parent_id,family))')
        db.execute("CREATE INDEX IF NOT EXISTS family_analysis_sources ON jobs(json_extract(payload,'$.family_parent.original_job_id'),json_extract(payload,'$.family')) WHERE kind='family_analysis' AND json_valid(payload)")


def _binding(source):
    return dict(original_job_id=source.jid,family=source.family,payload_hash=source.payload_hash,
        root_sha256=source.root_sha,original_result_event_id=source.result_event,
        original_core_hash=source.payload['core_hash'],version_count=len(source),
        members_hash=identity(list(source.parts)))


def _reservation(db,parent,family):
    malformed=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='family_analysis_reserved' AND (NOT json_valid(details) OR length(CAST(details AS BLOB))>4096) LIMIT 1",(parent,)).fetchone()
    if malformed:
        raise StateError('Original family reservation metadata is malformed.')
    events=db.execute("SELECT substr(details,1,4097) details FROM events WHERE entity_id=? AND kind='family_analysis_reserved' AND json_extract(details,'$.family')=? ORDER BY id LIMIT 2",(parent,family)).fetchall()
    links=db.execute('SELECT child_id FROM family_analysis_links WHERE parent_id=? AND family=?',(parent,family)).fetchall()
    children=db.execute("SELECT id FROM jobs WHERE kind='family_analysis' AND json_valid(payload) AND json_extract(payload,'$.family_parent.original_job_id')=? AND json_extract(payload,'$.family')=? ORDER BY id LIMIT 2",(parent,family)).fetchall()
    if not events and not links and not children:
        return None
    if len(events)!=1 or len(links)!=1 or len(children)!=1:
        raise StateError('Original family reservation is missing or duplicated; a replacement analysis is refused.')
    value=json.loads(events[0]['details'])
    if not isinstance(value,dict) or value.get('child_id')!=links[0]['child_id'] or value['child_id']!=children[0]['id']:
        raise StateError('Original family reservation/link identity differs.')
    return value


def _create_analysis(lab,parent,family):
    require_current_source();source=FamilyReports(lab,parent,family);binding=_binding(source)
    payload=dict(family=family,family_parent=binding,minimum_sharpe=.5,analysis_policy=1,core_hash=core_hash())
    jid=uuid.uuid4().hex;now=time.time()
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');existing=_reservation(db,parent,family)
        if existing is not None:
            saved,sha,provenance=lab.store._input_index.verified_inputs(existing['child_id'],db)
            # An already reserved analysis keeps its original analysis engine.
            original=saved['payload'];expected=payload|dict(core_hash=original.get('core_hash'))
            if (saved['kind']!='family_analysis' or provenance!='prespecified' or original!=expected
                    or existing!=dict(child_id=saved['id'],family=family,payload_hash=sha,binding=binding)):
                raise StateError('Original family analysis inputs changed; no replacement is authorized.')
            lab.store._trials.verify(saved['id'],db);source.guard();db.execute('COMMIT')
            return saved
        db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,'family_analysis',json.dumps(payload,sort_keys=True,separators=(',',':')),now,now))
        lab.store._trials.freeze(dict(id=jid,kind='family_analysis',payload=payload),db)
        lab.store._input_index.add(db,jid,payload)
        lab.store.event('job_created',jid,dict(kind='family_analysis'),db)
        db.execute('INSERT INTO family_analysis_links VALUES(?,?,?)',(parent,family,jid))
        lab.store.event('family_analysis_reserved',parent,dict(child_id=jid,family=family,payload_hash=identity(payload),binding=binding),db)
        source.guard();db.execute('COMMIT')
    return lab.store.job(jid)


def create_analysis(lab,parent,family):
    try:
        return _create_analysis(lab,parent,family)
    except StateError:
        raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original family registration evidence is missing or incompatible; no replacement was created.') from error


def _source(lab,payload,cancel=None):
    source=FamilyReports(lab,payload['family_parent']['original_job_id'],payload['family'],cancel)
    if payload.get('analysis_policy')!=1 or payload.get('minimum_sharpe')!=.5 or _binding(source)!=payload['family_parent']:
        raise StateError('Original complete family source differs from its reservation.')
    return source


def _publication(db,jid):
    count=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]
    if count==0:
        return None
    return _root_event(db,jid)


def _original_job(lab,db,jid,active_owner=None):
    job,sha,provenance=lab.store._input_index.verified_inputs(jid,db)
    if job['kind']!='family_analysis' or provenance!='prespecified':
        raise StateError('Choose an original saved family analysis.')
    if active_owner is None:
        if job['status']!='completed':
            raise StateError('Family analysis is available after successful completion.')
    else:
        lab.store._trials.owned(db,jid,active_owner)
    payload=job['payload'];reservation=_reservation(db,payload['family_parent']['original_job_id'],payload['family'])
    if reservation!=dict(child_id=jid,family=payload['family'],payload_hash=sha,binding=payload['family_parent']):
        raise StateError('Original family analysis reservation changed.')
    lab.store._trials.verify(jid,db)
    return job,sha


def _own_occurrence(lab,db,jid,value,digest,event):
    trial=lab.store._trials.row(db,jid,0,'report');computed=identity(value)
    if (trial['role']!='research_family' or trial['state'] not in {'checkpointed','completed'}
            or trial['computed_sha256']!=computed or trial['artifact_sha256']!=digest or trial['attempts']<1):
        raise StateError('Original family analysis occurrence changed.')
    attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
    if (attempt is None or attempt['state']!='checkpointed' or attempt['computed_sha256']!=computed or attempt['artifact_sha256']!=digest):
        raise StateError('Original family analysis attempt changed.')
    start,checkpoint=_trial_events(db,jid,trial,digest,event)
    rows=db.execute("SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind='trial_computation_recorded' AND id>? ORDER BY id LIMIT 2",(jid,start)).fetchall()
    expected=dict(trial_id=trial['id'],part=0,window='report',attempt=trial['attempts'],sha256=computed)
    if len(rows)!=1 or rows[0]['bytes']>4096 or json.loads(rows[0]['details'])!=expected or rows[0]['id']>=checkpoint:
        raise StateError('Original family analysis computation event is missing or changed.')


def _inspect_analysis(lab,jid,*,active_owner=None,cancel=None):
    require_current_source();_cancel(cancel)
    with lab.store.db() as db:
        db.execute('BEGIN');job,sha=_original_job(lab,db,jid,active_owner);event,digest=_root_event(db,jid)
    value=_load(lab.output_path(jid),digest);payload=job['payload']
    if (value.get('job_id')!=jid or value.get('kind')!='family_analysis' or value.get('payload_hash')!=sha
            or value.get('core_hash')!=payload['core_hash'] or value.get('family_parent')!=payload['family_parent']):
        raise StateError('Original family analysis artifact/input identity differs.')
    source=_source(lab,payload,cancel);rows=value.get('rows');report=value.get('report')
    if (not isinstance(rows,list) or len(rows)!=len(source) or not isinstance(report,dict)
            or report.get('members')!=sorted(source.parts) or report.get('version_count')!=len(source)):
        raise StateError('Original family analysis omits frozen versions.')
    for ordinal,(key,row) in enumerate(zip(source.parts,rows)):
        _cancel(cancel);part=source.parts[key]
        if (not isinstance(row,dict) or row.get('part')!=ordinal or row.get('source_part')!=part or row.get('config_id')!=key
                or row.get('report_sha256')!=source.rows[part]['report_sha256'] or not isinstance(row.get('witness'),list) or len(row['witness'])!=3):
            raise StateError('Original family member or checkpoint witness changed.')
        computed,attempt,events=row['witness']
        source.used[part]=(computed,attempt,tuple(events))
        if report.get('source_report_hashes',{}).get(key)!=computed:
            raise StateError('Original family account computation hash differs.')
    with lab.store.db() as db:
        db.execute('BEGIN');_own_occurrence(lab,db,jid,value,digest,event)
    source.guard()
    with lab.store.db() as db:
        db.execute('BEGIN');closing,closing_sha=_original_job(lab,db,jid,active_owner)
        if closing_sha!=sha or _root_event(db,jid)!=(event,digest) or file_hash(lab.output_path(jid))!=digest:
            raise StateError('Original family analysis changed during inspection.')
        _own_occurrence(lab,db,jid,value,digest,event)
    return value


def inspect_analysis(lab,jid,*,active_owner=None,cancel=None):
    try:
        return _inspect_analysis(lab,jid,active_owner=active_owner,cancel=cancel)
    except InterruptedError:
        raise
    except StateError:
        raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original saved family analysis is missing or incompatible; no report was recomputed.') from error


def execute_analysis(worker,job,cancel):
    from .service import compressed_write
    lab=worker.lab;jid=job['id'];payload=job['payload'];source=_source(lab,payload,cancel)
    with lab.store.db() as db:
        db.execute('BEGIN');_original_job(lab,db,jid,worker.owner);published=_publication(db,jid)
    if published is not None:
        value=inspect_analysis(lab,jid,active_owner=worker.owner,cancel=cancel)
        lab.result_index.build(jid,value,cancel,owner=worker.owner)
        inspect_analysis(lab,jid,active_owner=worker.owner,cancel=cancel)
        worker._progress(job,1,'Original saved family analysis reused; no accounts rerun.')
        return
    with lab.store.db() as db:
        # A surviving checkpoint cannot be made into a new publication if its
        # original result event was removed. File-only precommit orphans may retry.
        row=lab.store._trials.row(db,jid,0,'report')
        checkpoint=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind IN ('trial_checkpoint_saved','result_view_saved') LIMIT 1",(jid,)).fetchone()
        if row['state'] in {'checkpointed','completed'} or checkpoint is not None:
            raise StateError('Original family publication is missing; a replacement is refused.')
    lab.store.start_trial(jid,0,'report',worker.owner)
    report=family_average(source.configurations,source,minimum_sharpe=payload['minimum_sharpe'],cancel=cancel)
    source.guard();rows=[]
    for ordinal,(key,part) in enumerate(source.parts.items()):
        rows.append(dict(part=ordinal,source_part=part,config_id=key,report_sha256=source.rows[part]['report_sha256'],witness=source.used[part]))
    value=dict(job_id=jid,kind='family_analysis',payload_hash=identity(payload),core_hash=payload['core_hash'],
        family_parent=payload['family_parent'],report=report|dict(report_type='saved_family_research_average'),rows=rows,
        financial_accounts_recomputed=0,final_dates_accessed=False)
    lab.store.computed_trial(jid,0,'report',worker.owner,value)
    _cancel(cancel);source.guard();path=lab.output_path(jid);compressed_write(path,value);digest=file_hash(path)
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');_original_job(lab,db,jid,worker.owner);_cancel(cancel)
        if _publication(db,jid) is not None:
            raise StateError('Original family publication already exists.')
        source.guard()
        lab.store._trials.checkpoint_owned(db,jid,0,'report',worker.owner,value,digest)
        lab.store.event('result_saved',jid,dict(sha256=digest),db);db.execute('COMMIT')
    lab.result_index.build(jid,value,cancel,owner=worker.owner)
    inspect_analysis(lab,jid,active_owner=worker.owner,cancel=cancel)
    worker._progress(job,1,'Complete original family analysis saved; no financial accounts rerun.')


def analysis_summary(lab,jid):
    value=inspect_analysis(lab,jid);report=value['report']
    result={key:item for key,item in report.items() if key not in {'members','source_report_hashes','marked','realized_exit_day_compatibility'}}
    for convention in ['marked','realized_exit_day_compatibility']:
        result[convention]={key:item for key,item in report[convention].items() if key!='daily'}
    return result|dict(job_id=jid,kind='family_analysis',family_parent=value['family_parent'],
        financial_accounts_recomputed=0,final_dates_accessed=False,complete_json_url='/api/jobs/'+jid+'/family-analysis/export/json',
        daily_csv_url='/api/jobs/'+jid+'/family-analysis/export/csv')


def analysis_page(lab,jid,table,limit=50,offset=0):
    if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0 or table not in {'members','marked','realized_exit_day_compatibility'}:
        raise StateError('Choose a supported family table and page size 1 through 100.')
    value=inspect_analysis(lab,jid);rows=value['rows'] if table=='members' else value['report'][table]['daily']
    return dict(job_id=jid,table=table,rows=rows[offset:offset+limit],pagination=dict(limit=limit,offset=offset,total=len(rows)))
