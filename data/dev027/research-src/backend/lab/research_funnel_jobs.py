"""Owned two-phase qualification, original dependencies and candidate freezing.

Waiting uses the ordinary queued state with explicit original dependencies. No
strategy account is calculated here and no final date is unlocked or consumed.
"""
import json
import os
import re
import sqlite3
import time
import uuid
from .config import canonical,identity
from .research import core_hash,require_current_source,study_input_hash,checked_saved_read
from .research_funnel_arms import queue_arms,_study,_reserved,_verify
from .research_family_source import _cancel,_load,_root_event,_trial_events
from .research_qualification_source import qualification_snapshot,verify_snapshot
from .result_index import file_hash
from .store import StateError
from .trade_twin_jobs import _existing
from .trade_twin_source import _saved_state

PREDICATE="kind='funnel_qualification' AND json_valid(payload)"
PHASES=('preliminary','report')


def initialize(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS funnel_qualification_links(study_id TEXT PRIMARY KEY REFERENCES studies(id),job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id))')
        db.execute('CREATE TABLE IF NOT EXISTS funnel_dependencies(parent_id TEXT NOT NULL REFERENCES jobs(id),role TEXT NOT NULL,child_id TEXT NOT NULL REFERENCES jobs(id),PRIMARY KEY(parent_id,role),UNIQUE(parent_id,child_id))')
        db.execute('CREATE TABLE IF NOT EXISTS funnel_candidate_freezes(study_id TEXT PRIMARY KEY REFERENCES studies(id),job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id),result_sha256 TEXT NOT NULL,freeze TEXT NOT NULL)')
        db.execute("CREATE INDEX IF NOT EXISTS funnel_qualification_original_jobs ON jobs(json_extract(payload,'$.study_id'),id) WHERE "+PREDICATE)


def _event(db,entity,kind):
    rows=db.execute('SELECT id,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind=? ORDER BY id LIMIT 2',(entity,kind)).fetchall()
    if not rows:return None
    if len(rows)!=1 or rows[0]['bytes']>16384:raise StateError('Exactly one bounded original '+kind+' event is required.')
    value=json.loads(rows[0]['details'])
    if not isinstance(value,dict):raise StateError('Original qualification event must be an object.')
    return rows[0]['id'],value


def _payload(study,reserved):
    return dict(name=(study['name']+' / qualification')[:100],study_id=study['id'],qualification_policy=1,
        study_input_hash=study_input_hash(study['spec']),core_hash=core_hash(),
        configuration_universe_hash=study['spec']['configuration_universe_hash'],arms=reserved['arms'])


def _reservation(lab,db,study):
    sid=study['id'];event=_event(db,sid,'funnel_qualification_reserved')
    links=db.execute('SELECT job_id FROM funnel_qualification_links WHERE study_id=?',(sid,)).fetchall()
    jobs=db.execute("SELECT id FROM jobs INDEXED BY funnel_qualification_original_jobs WHERE "+PREDICATE+" AND json_extract(payload,'$.study_id')=? ORDER BY id LIMIT 2",(sid,)).fetchall()
    if event is None and not links and not jobs:return None
    if event is None or len(links)!=1 or len(jobs)!=1 or links[0][0]!=jobs[0][0]:
        raise StateError('Original qualification reservation is missing or duplicated; replacement is refused.')
    payload=_payload(study,_reserved(lab,db,study));expected=dict(job_id=jobs[0][0],payload_hash=identity(payload),study_input_hash=payload['study_input_hash'])
    if event[1]!=expected:raise StateError('Original qualification reservation changed.')
    return expected


def _dependencies(lab,db,job,study,*,eligible=None,complete=False):
    payload=job['payload'];expected={'arm:'+key:value['job_id'] for key,value in payload['arms'].items()}
    rows=db.execute('SELECT role,child_id FROM funnel_dependencies WHERE parent_id=? ORDER BY role',(job['id'],)).fetchall()
    mapped={row['role']:row['child_id'] for row in rows};controls={}
    for role,jid in mapped.items():
        if role.startswith('arm:'):continue
        match=re.fullmatch(r'control:(\d{6})',role)
        if match is None:raise StateError('Unknown original qualification dependency role.')
        part=int(match[1]);configurations=study['spec']['configurations']
        if part>=len(configurations) or eligible is not None and part not in eligible:
            raise StateError('A control dependency is outside the original eligible cohort.')
        child,_,provenance=lab.store._input_index.verified_inputs(jid,db)
        parent=payload['arms']['primary_discovery']['job_id'];_,configuration,binding=_saved_state(lab,parent,part,db)
        actual=_existing(lab.store,db,child['payload'])
        if (provenance!='prespecified' or actual is None or actual['id']!=jid or child['kind']!='trade_twins'
                or child['payload'].get('twin_parent')!=dict(job_id=parent,part=part,authority_hash=identity(binding),authority=binding)
                or child['payload'].get('strategy')!=configuration or child['payload']['source']['report_hash']!=binding['computed_sha256']):
            raise StateError('Original diagnostic dependency differs from its account/reservation.')
        controls[part]=jid
    if any(mapped.get(role)!=jid for role,jid in expected.items()) or set(mapped)-set(expected)-{'control:'+str(p).zfill(6) for p in controls}:
        raise StateError('Original account dependencies are missing or replaced.')
    if complete and set(controls)!=set(eligible):raise StateError('The complete original diagnostic dependency cohort is required.')
    waiting=_event(db,job['id'],'funnel_waiting')
    if waiting is not None and waiting[1].get('dependencies_hash')!=identity(mapped):
        raise StateError('Original waiting dependencies changed; missing links cannot be reconstructed.')
    return mapped,controls


def _job(lab,db,jid,owner=None,*,completed=False):
    require_current_source();job,digest,provenance=lab.store._input_index.verified_inputs(jid,db)
    if job['kind']!='funnel_qualification' or provenance!='prespecified':raise StateError('Choose an original qualification job.')
    study=_study(lab,db,job['payload']['study_id']);reserved=_reserved(lab,db,study)
    if reserved is None or job['payload']!=_payload(study,reserved):raise StateError('Original qualification inputs or arms changed.')
    if _reservation(lab,db,study)!=dict(job_id=jid,payload_hash=digest,study_input_hash=study_input_hash(study['spec'])):
        raise StateError('Qualification does not own its original reservation.')
    if owner is not None:
        lab.store._trials.owned(db,jid,owner)
        if job['cancel_requested']:raise InterruptedError('Qualification canceled before original publication.')
    elif completed and job['status']!='completed':raise StateError('Saved qualification requires successful original completion.')
    for binding in reserved['arms'].values():
        _verify(lab,db,lab.store.decode(db.execute('SELECT * FROM jobs WHERE id=?',(binding['job_id'],)).fetchone()),study,reserved)
    lab.store._trials.verify(jid,db);_dependencies(lab,db,job,study)
    return job,study


def create_qualification(lab,sid):
    require_current_source();queue_arms(lab,sid)
    try:
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');study=_study(lab,db,sid);reserved=_reserved(lab,db,study);existing=_reservation(lab,db,study)
            if existing is not None:
                job,_=_job(lab,db,existing['job_id']);db.execute('COMMIT');return job
            jid=uuid.uuid4().hex;now=time.time();payload=_payload(study,reserved)
            db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,'funnel_qualification',canonical(payload),now,now))
            lab.store._trials.freeze(dict(id=jid,kind='funnel_qualification',payload=payload),db)
            lab.store._input_index.add(db,jid,payload);lab.store.event('job_created',jid,dict(kind='funnel_qualification'),db)
            db.execute('INSERT INTO funnel_qualification_links VALUES(?,?)',(sid,jid))
            for key,binding in reserved['arms'].items():db.execute('INSERT INTO funnel_dependencies VALUES(?,?,?)',(jid,'arm:'+key,binding['job_id']))
            lab.store.event('funnel_qualification_reserved',sid,dict(job_id=jid,payload_hash=identity(payload),study_input_hash=payload['study_input_hash']),db)
            db.execute('COMMIT')
        return lab.store.job(jid)
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original qualification reservation is unavailable; no replacement was authorized.') from error


def _path(lab,jid,phase):
    return lab.output_path(jid) if phase=='report' else lab.output_path(jid).parent/'qualification'/'preliminary.json.gz'


def _occurrence(lab,db,jid,phase,value,digest,event):
    trial=lab.store._trials.row(db,jid,0,phase);computed=identity(value)
    if (trial['role']!='research_funnel' or trial['state'] not in {'checkpointed','completed'} or trial['attempts']<1
            or trial['computed_sha256']!=computed or trial['artifact_sha256']!=digest):
        raise StateError('Original qualification analysis occurrence changed.')
    attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
    if attempt is None or attempt['state']!='checkpointed' or attempt['computed_sha256']!=computed or attempt['artifact_sha256']!=digest:
        raise StateError('Original qualification analysis attempt changed.')
    start,checkpoint=_trial_events(db,jid,trial,digest,event,phase)
    rows=db.execute("SELECT id,substr(details,1,4097) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind='trial_computation_recorded' AND json_extract(details,'$.trial_id')=? AND id>? ORDER BY id LIMIT 2",(jid,trial['id'],start)).fetchall()
    expected=dict(trial_id=trial['id'],part=0,window=phase,attempt=trial['attempts'],sha256=computed)
    if len(rows)!=1 or rows[0]['bytes']>4096 or json.loads(rows[0]['details'])!=expected or rows[0]['id']>=checkpoint:
        raise StateError('Original qualification computation event is missing or changed.')


def _preliminary(lab,job,owner,cancel):
    with lab.store.db() as db:
        db.execute('BEGIN');_job(lab,db,job['id'],owner);event=_event(db,job['id'],'funnel_preliminary_saved')
        trial=lab.store._trials.row(db,job['id'],0,'preliminary')
        if event is None:
            saved=db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.window')='preliminary' LIMIT 1",(job['id'],)).fetchone()
            if trial['artifact_sha256'] is not None or trial['state'] in {'checkpointed','completed'} or saved:
                raise StateError('Original preliminary commitment is missing; replacement is refused.')
            return None
    value=_load(_path(lab,job['id'],'preliminary'),event[1]['sha256'])
    if (value.get('job_id')!=job['id'] or value.get('payload_hash')!=identity(job['payload']) or value.get('phase')!='preliminary'
            or value.get('core_hash')!=core_hash() or value['report'].get('evidence_phase')!='preliminary'):
        raise StateError('Original preliminary artifact/input identity changed.')
    with lab.store.db() as db:
        db.execute('BEGIN');_occurrence(lab,db,job['id'],'preliminary',value,event[1]['sha256'],event[0])
    verify_snapshot(lab,value['report'],cancel)
    return value,event[1]['sha256']


def _freeze(job,study,report,preliminary_sha):
    spec=study['spec'];members={family:[identity(c) for c in spec['configurations'] if c['family']==family]
        for family in sorted({c['family'] for c in spec['configurations']})}
    return dict(version=1,study_id=study['id'],qualification_job_id=job['id'],study_input_hash=study_input_hash(spec),
        configuration_universe_hash=spec['configuration_universe_hash'],core_hash=core_hash(),preliminary_sha256=preliminary_sha,
        qualification_report_hash=identity(report),candidate_ids=report['candidate_ids'],family_members=members,
        passing_families=sorted(family for family,value in report['families'].items() if value['passed']),
        final_cohort_policy=spec['final_cohort_policy'])


def _publish(worker,job,phase,value,cancel):
    from .service import compressed_write
    lab=worker.lab;jid=job['id'];destination=_path(lab,jid,phase)
    candidate=destination.parent/('unpublished-'+phase+'-'+worker.owner+'-'+uuid.uuid4().hex+'.json.gz')
    compressed_write(candidate,value);digest=file_hash(candidate);verify_snapshot(lab,value['report'],cancel);_cancel(cancel)
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');current,study=_job(lab,db,jid,worker.owner);_cancel(cancel)
        kind='result_saved' if phase=='report' else 'funnel_preliminary_saved'
        if _event(db,jid,kind) is not None:raise StateError('Original qualification publication already exists.')
        if phase=='report':
            _dependencies(lab,db,current,study,eligible={i for i,row in enumerate(value['report']['rows']) if row['prequalified']},complete=True)
            if value['report']['state']!='complete':raise StateError('Unresolved evidence cannot freeze candidates.')
            freeze=value['candidate_freeze']
            if freeze!=_freeze(job,study,value['report'],value['preliminary_sha256']):raise StateError('Original candidate/family freeze differs.')
            if db.execute('SELECT 1 FROM funnel_candidate_freezes WHERE study_id=?',(study['id'],)).fetchone() or _event(db,study['id'],'funnel_candidates_frozen'):
                raise StateError('An original candidate freeze already exists; replacement is refused.')
        if destination.exists():
            os.replace(destination,destination.parent/('orphan-'+phase+'-'+uuid.uuid4().hex+'.json.gz'))
        os.replace(candidate,destination)
        lab.store._trials.checkpoint_owned(db,jid,0,phase,worker.owner,value,digest)
        lab.store.event(kind,jid,dict(sha256=digest),db)
        if phase=='report':
            db.execute('INSERT INTO funnel_candidate_freezes VALUES(?,?,?,?)',(study['id'],jid,digest,canonical(freeze)))
            lab.store.event('funnel_candidates_frozen',study['id'],dict(job_id=jid,result_sha256=digest,freeze_hash=identity(freeze)),db)
        _cancel(cancel)
        db.execute('COMMIT')
    return digest


@checked_saved_read
def inspect_qualification(lab,jid,*,active_owner=None,cancel=None):
    _cancel(cancel);require_current_source()
    try:
        with lab.store.db() as db:
            db.execute('BEGIN');job,study=_job(lab,db,jid,active_owner,completed=active_owner is None);event,digest=_root_event(db,jid)
        value=_load(lab.output_path(jid),digest);preliminary=_preliminary(lab,job,active_owner,cancel)
        if (value.get('job_id')!=jid or value.get('kind')!='funnel_qualification' or value.get('payload_hash')!=identity(job['payload'])
                or value.get('core_hash')!=core_hash() or value.get('phase')!='report' or preliminary is None
                or value.get('preliminary_sha256')!=preliminary[1] or value['report'].get('evidence_phase')!='qualified'
                or value['report'].get('state')!='complete' or value.get('candidate_freeze')!=_freeze(job,study,value['report'],preliminary[1])):
            raise StateError('Original qualification publication or complete candidate/family membership changed.')
        verify_snapshot(lab,value['report'],cancel)
        with lab.store.db() as db:
            db.execute('BEGIN');_job(lab,db,jid,active_owner,completed=active_owner is None)
            _occurrence(lab,db,jid,'report',value,digest,event)
            _dependencies(lab,db,job,study,eligible={i for i,row in enumerate(value['report']['rows']) if row['prequalified']},complete=True)
            row=db.execute('SELECT * FROM funnel_candidate_freezes WHERE study_id=?',(study['id'],)).fetchone();freeze=value['candidate_freeze']
            saved=_event(db,study['id'],'funnel_candidates_frozen')
            if (row is None or row['job_id']!=jid or row['result_sha256']!=digest or json.loads(row['freeze'])!=freeze
                    or saved is None or saved[1]!=dict(job_id=jid,result_sha256=digest,freeze_hash=identity(freeze))
                    or saved[0]<=event or _root_event(db,jid)!=(event,digest) or file_hash(lab.output_path(jid))!=digest):
                raise StateError('Original qualification/candidate publication changed during inspection.')
        _cancel(cancel);require_current_source();return value
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original qualification evidence is missing or incompatible; no math was regenerated.') from error


def qualification_summary(lab,jid,*,cancel=None):
    """Bounded public metadata still requires complete original authority."""
    value=inspect_qualification(lab,jid,cancel=cancel);report=value['report'];freeze=value['candidate_freeze']
    families={name:dict(version_count=len(family['members']),passed=family['passed'],gate_basis=family['gate_basis'])
        for name,family in report['families'].items()}
    result=dict(job_id=jid,kind='funnel_qualification',study_id=report['study_id'],core_hash=value['core_hash'],
        report_type=report['report_type'],state=report['state'],version_count=report['version_count'],
        configuration_universe_hash=report['configuration_universe_hash'],candidate_count=len(report['candidate_ids']),
        ineligible_control_count=len(report['ineligible_control_ids']),pending_control_count=len(report['pending_control_ids']),
        candidate_freeze_hash=identity(freeze),families=families,attrition=report['attrition'],
        source_video=report['source_video'],host_engine_parity_verified=False,financial_accounts_recomputed=0,
        final_dates_accessed=False,final_cohort_policy=report['final_cohort_policy'],
        control_scheduling_policy=report['control_scheduling_policy'],has_report=True,row_count=report['version_count'],
        original_evidence_verified=True,complete_json_url='/api/jobs/'+jid+'/result')
    if len(canonical(result).encode())>49152:raise StateError('Qualification summary bound exceeded; no partial evidence claim was published.')
    _cancel(cancel);return result


def _wait(worker,job,preliminary,cancel):
    lab=worker.lab;jid=job['id'];eligible={i for i,row in enumerate(preliminary['report']['rows']) if row['prequalified']}
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');current,study=_job(lab,db,jid,worker.owner);_cancel(cancel)
        mapped,_=_dependencies(lab,db,current,study,eligible=eligible,complete=True)
        pending=db.execute("SELECT 1 FROM funnel_dependencies d JOIN jobs j ON j.id=d.child_id WHERE d.parent_id=? AND j.status NOT IN ('completed','failed','canceled') LIMIT 1",(jid,)).fetchone()
        if pending is None:db.execute('COMMIT');return False
        if _event(db,jid,'funnel_waiting') is None:lab.store.event('funnel_waiting',jid,dict(dependencies_hash=identity(mapped)),db)
        db.execute("UPDATE jobs SET status='queued',owner=NULL,lease_until=NULL,progress=.5,note='Waiting for original comparison tests.',updated=? WHERE id=?",(time.time(),jid))
        db.execute('COMMIT')
    return True


def execute_qualification(worker,job,cancel):
    lab=worker.lab;jid=job['id']
    with lab.store.db() as db:
        db.execute('BEGIN');_,study=_job(lab,db,jid,worker.owner);published=_event(db,jid,'result_saved')
    if published is not None:
        value=inspect_qualification(lab,jid,active_owner=worker.owner,cancel=cancel)
        lab.result_index.build(jid,value,cancel,owner=worker.owner)
        inspect_qualification(lab,jid,active_owner=worker.owner,cancel=cancel);return
    preliminary=_preliminary(lab,job,worker.owner,cancel)
    if preliminary is None:
        lab.store.start_trial(jid,0,'preliminary',worker.owner)
        report=qualification_snapshot(lab,study['id'],cancel,include_controls=False)
        if report['state']=='incomplete_accounts':raise StateError('Original research arms failed or were canceled; recover those original jobs before resuming qualification.')
        value=dict(job_id=jid,kind='funnel_qualification',payload_hash=identity(job['payload']),core_hash=core_hash(),phase='preliminary',report=report)
        lab.store.computed_trial(jid,0,'preliminary',worker.owner,value);digest=_publish(worker,job,'preliminary',value,cancel)
        preliminary=(value,digest)
    value,digest=preliminary;verify_snapshot(lab,value['report'],cancel)
    from .trade_twin_jobs import create as create_control
    for part,row in enumerate(value['report']['rows']):
        if not row['prequalified']:continue
        def guard(db):
            _job(lab,db,jid,worker.owner);_cancel(cancel)
            if file_hash(_path(lab,jid,'preliminary'))!=digest:raise StateError('Original preliminary artifact changed before control reservation.')
            verify_snapshot(lab,value['report'],cancel)
        child=create_control(lab,job['payload']['arms']['primary_discovery']['job_id'],part,cancel,reservation_guard=guard)
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');_job(lab,db,jid,worker.owner);_cancel(cancel)
            role='control:'+str(part).zfill(6);saved=db.execute('SELECT child_id FROM funnel_dependencies WHERE parent_id=? AND role=?',(jid,role)).fetchone()
            if saved is None:db.execute('INSERT INTO funnel_dependencies VALUES(?,?,?)',(jid,role,child['id']))
            elif saved[0]!=child['id']:raise StateError('Original diagnostic dependency cannot be replaced.')
            db.execute('COMMIT')
    if _wait(worker,job,value,cancel):return 'waiting'
    with lab.store.db() as db:
        db.execute('BEGIN');_job(lab,db,jid,worker.owner);trial=lab.store._trials.row(db,jid,0,'report')
        if trial['artifact_sha256'] is not None or trial['state'] in {'checkpointed','completed'}:
            raise StateError('Original qualification result publication is missing; replacement is refused.')
    lab.store.start_trial(jid,0,'report',worker.owner);report=qualification_snapshot(lab,study['id'],cancel)
    if report['state']!='complete':raise StateError('Original comparison evidence is unresolved; recover the original comparison jobs before resuming qualification.')
    # Every non-control observation must be identical to the original preliminary
    # reduction. The second occurrence attaches actual completed control evidence.
    for old,new in zip(value['report']['rows'],report['rows']):
        if any(old[key]!=new[key] for key in ['config_id','configuration','accounts','prequalified','family_passed','controls_required']):
            raise StateError('Original preliminary eligibility or account observations changed.')
    if value['report']['families']!=report['families'] or value['report']['stability']!=report['stability']:
        raise StateError('Original all-version family or frozen-neighbor reduction changed.')
    result=dict(job_id=jid,kind='funnel_qualification',payload_hash=identity(job['payload']),core_hash=core_hash(),phase='report',
        preliminary_sha256=digest,report=report,candidate_freeze=_freeze(job,study,report,digest),financial_accounts_recomputed=0,final_dates_accessed=False)
    lab.store.computed_trial(jid,0,'report',worker.owner,result);_publish(worker,job,'report',result,cancel)
    inspect_qualification(lab,jid,active_owner=worker.owner,cancel=cancel)
    lab.result_index.build(jid,result,cancel,owner=worker.owner)
    inspect_qualification(lab,jid,active_owner=worker.owner,cancel=cancel)
    worker._progress(job,1,'Original qualification and complete candidate/family freeze saved.')
