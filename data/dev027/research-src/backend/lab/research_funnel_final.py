"""One original, one-time final evaluation of all versions on both instruments."""
from collections.abc import Mapping
import json
import math
import os
import sqlite3
import time
import uuid
from .config import Strategy,Costs,Portfolio,canonical,identity
from .data import read_manifest,atomic_json
from .research import core_hash,core_subject,require_current_source,study_input_hash,checked_saved_read
from .research_funnel_arms import _study
from .research_funnel_jobs import (_event,_job as qualification_job,inspect_qualification,
    _occurrence as analysis_occurrence)
from .research_family_source import _cancel,_load,_root_event,_trial_events
from .research_funnel import family_average,SOURCE_VIDEO
from .research_qualification import _Members
from .result_index import file_hash
from .store import StateError
from .account_checkpoints import preflight,load_checkpoint,publish_checkpoint,reuse_checkpoint

ARMS=('primary_final','replication_final')
PREDICATE="kind='funnel_final' AND json_valid(payload)"


def initialize(store):
    with store.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS funnel_final_links(study_id TEXT PRIMARY KEY REFERENCES studies(id),job_id TEXT NOT NULL UNIQUE REFERENCES jobs(id))')
        db.execute("CREATE INDEX IF NOT EXISTS funnel_final_original_jobs ON jobs(json_extract(payload,'$.study_id'),id) WHERE "+PREDICATE)


def _qualified(lab,sid,cancel=None):
    with lab.store.db() as db:
        row=db.execute('SELECT job_id FROM funnel_qualification_links WHERE study_id=?',(sid,)).fetchone()
    if row is None:raise StateError('Complete original research qualification before reserving final evaluation.')
    value=inspect_qualification(lab,row[0],cancel=cancel)
    with lab.store.db() as db:
        db.execute('BEGIN');event,digest=_root_event(db,row[0]);job,study=qualification_job(lab,db,row[0],completed=True)
    return study,value,dict(job_id=row[0],payload_hash=identity(job['payload']),result_event_id=event,
        root_sha256=digest,computed_sha256=identity(value),candidate_freeze_hash=identity(value['candidate_freeze']))


def _check_qualification(lab,db,sid,binding):
    job,study=qualification_job(lab,db,binding['job_id'],completed=True)
    event,digest=_root_event(db,job['id']);row=db.execute('SELECT * FROM funnel_candidate_freezes WHERE study_id=?',(sid,)).fetchone()
    trial=lab.store._trials.row(db,job['id'],0,'report')
    attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
    if (study['id']!=sid or identity(job['payload'])!=binding['payload_hash'] or (event,digest)!=(binding['result_event_id'],binding['root_sha256'])
            or file_hash(lab.output_path(job['id']))!=digest or trial['state']!='completed' or trial['computed_sha256']!=binding['computed_sha256']
            or trial['artifact_sha256']!=digest or attempt is None or attempt['state']!='checkpointed'
            or attempt['computed_sha256']!=trial['computed_sha256'] or attempt['artifact_sha256']!=digest
            or row is None or row['job_id']!=job['id'] or row['result_sha256']!=digest
            or identity(json.loads(row['freeze']))!=binding['candidate_freeze_hash']):
        raise StateError('Original final qualification or candidate/family freeze changed.')
    _trial_events(db,job['id'],trial,digest,event)
    frozen=_event(db,sid,'funnel_candidates_frozen')
    if frozen is None or frozen[1]!=dict(job_id=job['id'],result_sha256=digest,freeze_hash=binding['candidate_freeze_hash']):
        raise StateError('Original candidate/family publication is missing or changed.')
    return study,json.loads(row['freeze'])


def _payload(study,binding):
    spec=study['spec'];payload=dict(name=(study['name']+' / all-version final')[:100],study_id=study['id'],final_policy_version=1,
        study_input_hash=study_input_hash(spec),core_hash=core_hash(),qualification_binding=binding,
        configuration_universe_hash=spec['configuration_universe_hash'],configurations=spec['configurations'],
        final_arms=spec['final_arms'],costs=spec['costs'],portfolio=spec['portfolio'],seed=spec['seed'],
        final_version_policy=spec['qualification_policy']['final_version'],family_minimum_sharpe=spec['family_minimum_sharpe'],
        final_cohort_policy=spec['final_cohort_policy'])
    payload.update({key:value for key,value in spec.items() if key.startswith('news_')})
    return payload


def _reservation(lab,db,sid):
    event=_event(db,sid,'funnel_final_reserved');links=db.execute('SELECT job_id FROM funnel_final_links WHERE study_id=?',(sid,)).fetchall()
    jobs=db.execute("SELECT id FROM jobs INDEXED BY funnel_final_original_jobs WHERE "+PREDICATE+" AND json_extract(payload,'$.study_id')=? ORDER BY id LIMIT 2",(sid,)).fetchall()
    if event is None and not links and not jobs:return None
    if event is None or len(links)!=1 or len(jobs)!=1 or links[0][0]!=jobs[0][0] or event[1].get('job_id')!=jobs[0][0]:
        raise StateError('Original final reservation is missing or duplicated; replacement is refused.')
    return event[1]


def _consumption(lab,db,job,study,*,required=False):
    spec=study['spec'];event=_event(db,study['id'],'final_unlock_consumed')
    if event is None:
        if required or spec.get('final_job_id') or study['status']!='registered':raise StateError('Original final consumption is missing or incompatible.')
        return None
    expected=dict(job_id=job['id'],candidate_freeze_hash=job['payload']['qualification_binding']['candidate_freeze_hash'],
        configuration_universe_hash=spec['configuration_universe_hash'],account_count=2*len(spec['configurations']))
    if event[1]!=expected or spec.get('final_job_id')!=job['id'] or study['status'] not in {'consumed','final_failed','final_complete'}:
        raise StateError('Only the original consumed final job can continue.')
    reserved=_event(db,study['id'],'funnel_final_reserved')
    first=db.execute("SELECT MIN(id) FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.window') IN ('primary_final','replication_final')",(job['id'],)).fetchone()[0]
    if reserved is None or event[0]<=reserved[0] or first is not None and event[0]>=first:
        raise StateError('Original final reservation/consumption must precede every final account computation.')
    return event


def _job(lab,db,jid,owner=None,*,completed=False,consumed=False):
    require_current_source();job,sha,provenance=lab.store._input_index.verified_inputs(jid,db)
    if job['kind']!='funnel_final' or provenance!='prespecified':raise StateError('Choose an original all-version final job.')
    payload=job['payload'];study=_study(lab,db,payload['study_id']);study,freeze=_check_qualification(lab,db,study['id'],payload['qualification_binding'])
    if payload!=_payload(study,payload['qualification_binding']):raise StateError('Original complete final inputs or instrument arms changed.')
    expected=dict(job_id=jid,payload_hash=sha,study_input_hash=study_input_hash(study['spec']),candidate_freeze_hash=identity(freeze))
    if _reservation(lab,db,study['id'])!=expected:raise StateError('Final job does not own its original reservation.')
    if owner is not None:
        lab.store._trials.owned(db,jid,owner)
        if job['cancel_requested']:raise InterruptedError('Final evaluation canceled before original publication.')
    elif completed and job['status']!='completed':raise StateError('Final results require successful original completion.')
    lab.store._trials.verify(jid,db);_consumption(lab,db,job,study,required=consumed)
    return job,study,freeze


def create_final(lab,sid):
    require_current_source()
    try:
        study,qualified,binding=_qualified(lab,sid)
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');study,freeze=_check_qualification(lab,db,sid,binding);existing=_reservation(lab,db,sid)
            if existing is not None:
                job,_,_=_job(lab,db,existing['job_id']);db.execute('COMMIT');return job
            if study['status']!='registered' or study['spec'].get('final_job_id'):
                raise StateError('Final access cannot be reserved again after consumption.')
            payload=_payload(study,binding);jid=uuid.uuid4().hex;now=time.time()
            db.execute('INSERT INTO jobs(id,kind,payload,created,updated) VALUES(?,?,?,?,?)',(jid,'funnel_final',canonical(payload),now,now))
            lab.store._trials.freeze(dict(id=jid,kind='funnel_final',payload=payload),db);lab.store._input_index.add(db,jid,payload)
            lab.store.event('job_created',jid,dict(kind='funnel_final'),db);db.execute('INSERT INTO funnel_final_links VALUES(?,?)',(sid,jid))
            lab.store.event('funnel_final_reserved',sid,dict(job_id=jid,payload_hash=identity(payload),study_input_hash=payload['study_input_hash'],candidate_freeze_hash=identity(freeze)),db)
            db.execute('COMMIT')
        return lab.store.job(jid)
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original final reservation evidence is unavailable; no replacement was created.') from error


def _consume(worker,job,cancel):
    lab=worker.lab
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');current,study,freeze=_job(lab,db,job['id'],worker.owner);_cancel(cancel)
        if _consumption(lab,db,current,study) is None:
            spec=study['spec'];spec['final_job_id']=job['id']
            details=dict(job_id=job['id'],candidate_freeze_hash=identity(freeze),configuration_universe_hash=spec['configuration_universe_hash'],account_count=2*len(spec['configurations']))
            db.execute("UPDATE studies SET spec=?,status='consumed',updated=? WHERE id=?",(canonical(spec),time.time(),study['id']))
            for symbol in spec['symbols']:
                db.execute('INSERT INTO viewed_windows(symbol,start,end,kind,study_id,at) VALUES(?,?,?,?,?,?)',(symbol,spec['holdout']['start'],spec['holdout']['end'],'final_consumed',study['id'],time.time()))
            lab.store.event('final_unlock_consumed',study['id'],details,db);lab.store._study_index.add(db,study['id'],spec)
        _cancel(cancel);db.execute('COMMIT')


def _context(job,part,key):
    return dict(job_id=job['id'],payload_hash=identity(job['payload']),core_hash=core_hash(),part=part,
        config_id=identity(job['payload']['configurations'][part]),arm_key=key,arm_hash=identity(job['payload']['final_arms'][key]))


def _path(lab,jid,part,key):
    if type(part) is not int or part<0 or key not in ARMS:raise StateError('Choose a frozen final configuration and instrument arm.')
    path=lab.output_path(jid).parent/'final'/key/(str(part).zfill(6)+'.json.gz')
    return path,path.with_suffix('.sha256.json')


def _validate_account(job,part,key,report):
    payload=job['payload'];arm=payload['final_arms'][key];configuration=payload['configurations'][part]
    expected=dict(report_type='single_strategy',config_id=identity(configuration),config=configuration,
        core_hash=core_hash(),numerical_contract=core_subject(),dataset_id=arm['dataset_context']['dataset_id'],
        dataset_manifest_hash=arm['dataset_context']['dataset_manifest_hash'],dataset_context=arm['dataset_context'],
        start=arm['start'],end=arm['end'],costs=payload['costs'],portfolio=payload['portfolio'],seed=payload['seed'],
        research_final_context=dict(study_id=payload['study_id'],arm_key=key,arm_hash=identity(arm),
            candidate_freeze_hash=payload['qualification_binding']['candidate_freeze_hash'],role=arm['role']))
    if not isinstance(report,dict) or any(report.get(k)!=v for k,v in expected.items()) or set(report.get('charts',{}))!={arm['symbol']}:
        raise StateError('Original final account role, rule, scope or assumptions differ.')
    metrics=report['metrics'];profit=metrics['net_profit'];sharpe=metrics['marked_sharpe']
    if (type(profit) not in (int,float) or not math.isfinite(profit) or type(metrics['trades']) is not int
            or metrics['trades']!=len(report['trades']) or sharpe is not None and (type(sharpe) not in (int,float) or not math.isfinite(sharpe))):
        raise StateError('Original final account metrics are malformed or nonfinite.')
    return report


def _read(lab,job,part,key,cancel=None):
    _cancel(cancel)
    if type(part) is not int or not 0<=part<len(job['payload']['configurations']):raise StateError('Choose a frozen final configuration ordinal.')
    path,receipt=_path(lab,job['id'],part,key);context=_context(job,part,key)
    value,committed,digest=load_checkpoint(lab,job['id'],part,path,receipt,context,[key])
    if committed!={key}:raise StateError('A complete original committed final account is required.')
    return _validate_account(job,part,key,value[key]),digest


class _Reports(Mapping):
    def __init__(self,lab,job,key,cancel):
        self.lab=lab;self.job=job;self.key=key;self.cancel=cancel
        self.parts={identity(c):i for i,c in enumerate(job['payload']['configurations'])}
    def __len__(self):return len(self.parts)
    def __iter__(self):return iter(self.parts)
    def __getitem__(self,cid):return _read(self.lab,self.job,self.parts[cid],self.key,self.cancel)[0]


def _reduce(lab,job,freeze,cancel):
    payload=job['payload'];configurations=payload['configurations'];candidates=set(freeze['candidate_ids']);families=set(freeze['passing_families']);rows=[]
    for part,configuration in enumerate(configurations):
        _cancel(cancel);reports={}
        for key in ARMS:
            report,digest=_read(lab,job,part,key,cancel);metrics=report['metrics'];sharpe=metrics['marked_sharpe']
            passed=metrics['net_profit']>0 and sharpe is not None and sharpe>=payload['final_version_policy']['minimum_sharpe']
            reports[key]=dict(report_sha256=digest,computed_sha256=identity(report),metrics=metrics,final_gate_pass=passed)
        rows.append(dict(part=part,config_id=identity(configuration),config=configuration,candidate=identity(configuration) in candidates,
            family_passed=configuration['family'] in families,reports=reports))
    summaries={}
    for key in ARMS:
        source=_Reports(lab,job,key,cancel);averages={}
        for family in sorted({c['family'] for c in configurations}):
            members=[Strategy(**c) for c in configurations if c['family']==family];ids=[identity(c) for c in members]
            averages[family]=family_average(members,_Members(source,ids),minimum_sharpe=payload['family_minimum_sharpe'],cancel=cancel)
        summaries[key]=dict(symbol=payload['final_arms'][key]['symbol'],version_count=len(rows),
            passing_versions=sum(row['reports'][key]['final_gate_pass'] for row in rows),families=averages)
    report=dict(report_type='research_funnel_final',state='complete',version_count=len(rows),instrument_count=2,source_video=SOURCE_VIDEO,
        host_engine_parity_verified=False,arms=summaries,final_version_policy=payload['final_version_policy'],
        candidate_count=len(candidates),final_cohort_policy=payload['final_cohort_policy'],all_frozen_versions_evaluated=True)
    return dict(job_id=job['id'],kind='funnel_final',payload_hash=identity(payload),core_hash=core_hash(),
        candidate_freeze_hash=identity(freeze),qualification_binding=payload['qualification_binding'],report=report,rows=rows)


def _accounts_guard(lab,job,value,cancel):
    rows=value.get('rows');configurations=job['payload']['configurations']
    if not isinstance(rows,list) or len(rows)!=len(configurations):raise StateError('Original final result omits frozen versions.')
    with lab.store.db() as db:
        db.execute('BEGIN');_,_,freeze=_job(lab,db,job['id'],consumed=True)
        aggregate=lab.store._trials.row(db,job['id'],0,'aggregate')
        starts=db.execute("SELECT id FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=? AND json_extract(details,'$.attempt')=? ORDER BY id LIMIT 2",(job['id'],aggregate['id'],aggregate['attempts'])).fetchall()
        if len(starts)!=1:raise StateError('Original final aggregation computation start is missing or duplicated.')
        aggregate_start=starts[0]['id']
    candidates=set(freeze['candidate_ids']);passing=set(freeze['passing_families'])
    for part,(configuration,row) in enumerate(zip(configurations,rows)):
        _cancel(cancel)
        if (row.get('part')!=part or row.get('config_id')!=identity(configuration) or row.get('config')!=configuration or set(row.get('reports',{}))!=set(ARMS)
                or row.get('candidate') is not (identity(configuration) in candidates) or row.get('family_passed') is not (configuration['family'] in passing)):
            raise StateError('Original final configuration membership changed.')
        for key in ARMS:
            report,digest=_read(lab,job,part,key,cancel);record=row['reports'][key]
            with lab.store.db() as db:
                db.execute('BEGIN');trial=lab.store._trials.row(db,job['id'],part,key)
                _trial_events(db,job['id'],trial,digest,aggregate_start,key)
            if record['report_sha256']!=digest or record['computed_sha256']!=identity(report) or record['metrics']!=report['metrics']:
                raise StateError('Original final account/publication binding changed.')
            metrics=report['metrics'];expected=metrics['net_profit']>0 and metrics['marked_sharpe'] is not None and metrics['marked_sharpe']>=job['payload']['final_version_policy']['minimum_sharpe']
            if record['final_gate_pass'] is not expected:raise StateError('Original final gate differs from its frozen policy.')
    if set(value['report']['arms'])!=set(ARMS):raise StateError('Original final result omits an instrument.')
    for key,arm in value['report']['arms'].items():
        if arm['symbol']!=job['payload']['final_arms'][key]['symbol'] or arm['version_count']!=len(rows) or set(arm['families'])!=set(freeze['family_members']):
            raise StateError('Original final family/instrument membership differs.')
        for family,average in arm['families'].items():
            ids=freeze['family_members'][family];known=set(ids)
            if average['members']!=sorted(ids) or average['version_count']!=len(ids) or average.get('source_report_hashes')!={row['config_id']:row['reports'][key]['computed_sha256'] for row in rows if row['config_id'] in known}:
                raise StateError('Original final family average omits or replaces original accounts.')


@checked_saved_read
def inspect_final(lab,jid,*,active_owner=None,cancel=None):
    try:
        with lab.store.db() as db:
            db.execute('BEGIN');job,study,freeze=_job(lab,db,jid,active_owner,completed=active_owner is None,consumed=True);event,digest=_root_event(db,jid)
        value=_load(lab.output_path(jid),digest)
        if (value.get('job_id')!=jid or value.get('kind')!='funnel_final' or value.get('payload_hash')!=identity(job['payload'])
                or value.get('core_hash')!=core_hash() or value.get('candidate_freeze_hash')!=identity(freeze)
                or value.get('qualification_binding')!=job['payload']['qualification_binding']
                or value['report'].get('version_count')!=len(job['payload']['configurations']) or value['report'].get('instrument_count')!=2):
            raise StateError('Original final result or complete frozen cohort identity changed.')
        inspect_qualification(lab,freeze['qualification_job_id'],cancel=cancel);_accounts_guard(lab,job,value,cancel)
        with lab.store.db() as db:
            db.execute('BEGIN');_job(lab,db,jid,active_owner,completed=active_owner is None,consumed=True)
            analysis_occurrence(lab,db,jid,'aggregate',value,digest,event)
            if _root_event(db,jid)!=(event,digest) or file_hash(lab.output_path(jid))!=digest:
                raise StateError('Original final publication changed during inspection.')
        _cancel(cancel);return value
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,KeyError,TypeError) as error:
        raise StateError('Original final evidence is missing or incompatible; no final prices or accounts were regenerated.') from error


def read_final_account(lab,jid,part,key):
    value=inspect_final(lab,jid)
    with lab.store.db() as db:
        db.execute('BEGIN');job,_,_=_job(lab,db,jid,completed=True,consumed=True)
    report,digest=_read(lab,job,part,key)
    if value['rows'][part]['reports'][key]['report_sha256']!=digest:raise StateError('Original requested final account changed.')
    return report


def final_summary(lab,jid,*,cancel=None):
    value=inspect_final(lab,jid,cancel=cancel);report=value['report'];arms={}
    for key,arm in report['arms'].items():
        families={}
        for family,average in arm['families'].items():
            families[family]=dict(version_count=average['version_count'],state=average['state'],
                marked={k:v for k,v in average['marked'].items() if k!='daily'},
                realized_exit_day_compatibility={k:v for k,v in average['realized_exit_day_compatibility'].items() if k!='daily'})
        arms[key]=dict(symbol=arm['symbol'],version_count=arm['version_count'],passing_versions=arm['passing_versions'],families=families)
    with lab.store.db() as db:
        db.execute('BEGIN');original,_,_=lab.store._input_index.verified_inputs(jid,db)
    result=dict(job_id=jid,kind='funnel_final',study_id=original['payload']['study_id'],core_hash=value['core_hash'],report_type=report['report_type'],
        state=report['state'],version_count=report['version_count'],instrument_count=2,arms=arms,candidate_count=report['candidate_count'],
        candidate_freeze_hash=value['candidate_freeze_hash'],source_video=SOURCE_VIDEO,host_engine_parity_verified=False,
        final_cohort_policy=report['final_cohort_policy'],final_version_policy=report['final_version_policy'],
        original_evidence_verified=True,has_report=True,row_count=len(value['rows']),complete_json_url='/api/jobs/'+jid+'/result')
    if len(canonical(result).encode())>49152:raise StateError('Final summary bound exceeded; no partial authority claim was published.')
    _cancel(cancel);return result


def final_rows(lab,jid,limit=50,offset=0,*,cancel=None):
    if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:raise StateError('Choose final page size1 through100 and a nonnegative offset.')
    value=inspect_final(lab,jid,cancel=cancel);rows=[]
    for row in value['rows'][offset:offset+limit]:
        _cancel(cancel)
        reports={}
        for key,record in row['reports'].items():
            reports[key]=record|dict(metrics={k:v for k,v in record['metrics'].items() if k not in {'daily_pnl','daily_returns'}},
                omitted_metric_arrays=['daily_pnl','daily_returns'],complete_account_url='/api/jobs/'+jid+'/report?part='+str(row['part'])+'&window='+key)
        rows.append(row|dict(reports=reports))
    result=dict(job_id=jid,rows=rows,pagination=dict(limit=limit,offset=offset,total=len(value['rows'])),original_evidence_verified=True)
    if len(canonical(result).encode())>8*1024*1024:raise StateError('Final response bound exceeded; choose a smaller page.')
    _cancel(cancel);return result


def _publish(worker,job,value,cancel):
    from .service import compressed_write
    lab=worker.lab;path=lab.output_path(job['id']);candidate=path.parent/('unpublished-final-'+worker.owner+'-'+uuid.uuid4().hex+'.json.gz')
    compressed_write(candidate,value);digest=file_hash(candidate);_accounts_guard(lab,job,value,cancel)
    inspect_qualification(lab,job['payload']['qualification_binding']['job_id'],cancel=cancel)
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');_job(lab,db,job['id'],worker.owner,consumed=True);_cancel(cancel)
        if _event(db,job['id'],'result_saved') is not None:raise StateError('Original final publication already exists.')
        if path.exists():os.replace(path,path.parent/('orphan-final-'+uuid.uuid4().hex+'.json.gz'))
        os.replace(candidate,path);lab.store._trials.checkpoint_owned(db,job['id'],0,'aggregate',worker.owner,value,digest)
        lab.store.event('result_saved',job['id'],dict(sha256=digest),db);_cancel(cancel);db.execute('COMMIT')


def execute_final(worker,job,cancel):
    from .service import compressed_write
    lab=worker.lab;payload=job['payload'];jid=job['id'];preflight(lab,jid)
    with lab.store.db() as db:
        db.execute('BEGIN');_,study,freeze=_job(lab,db,jid,worker.owner);published=_event(db,jid,'result_saved')
    inspect_qualification(lab,payload['qualification_binding']['job_id'],cancel=cancel)
    if published is not None:
        value=inspect_final(lab,jid,active_owner=worker.owner,cancel=cancel);lab.result_index.build(jid,value,cancel,owner=worker.owner)
        inspect_final(lab,jid,active_owner=worker.owner,cancel=cancel);return
    _consume(worker,job,cancel)
    for part,configuration in enumerate(payload['configurations']):
        for key in ARMS:
            _cancel(cancel);arm=payload['final_arms'][key];path,receipt=_path(lab,jid,part,key);path.parent.mkdir(parents=True,exist_ok=True)
            context=_context(job,part,key);saved,committed,_=load_checkpoint(lab,jid,part,path,receipt,context,[key])
            if committed:
                saved,_=reuse_checkpoint(worker,job,part,path,receipt,context,[key],cancel);_validate_account(job,part,key,saved[key])
            else:
                def calculate():
                    with lab.store.db() as db:
                        db.execute('BEGIN');_job(lab,db,jid,worker.owner,consumed=True)
                    _cancel(cancel);cfg=Strategy(**configuration);lab.news_input(payload,[cfg],arm['start'],arm['end'])
                    report=lab.evaluate(arm['dataset_context']['dataset_id'],cfg,Costs(**payload['costs']),Portfolio(**payload['portfolio']),
                        arm['start'],arm['end'],payload['seed'],payload.get('news_dates'),cancel,
                        payload['study_id'],jid,arm['dataset_context']['dataset_manifest_hash'],payload.get('news_calendar'),symbols=[arm['symbol']])
                    report['research_final_context']=dict(study_id=payload['study_id'],arm_key=key,arm_hash=identity(arm),
                        candidate_freeze_hash=payload['qualification_binding']['candidate_freeze_hash'],role=arm['role'])
                    return _validate_account(job,part,key,report)
                report=worker._trial(job,part,key,calculate)
                publish_checkpoint(worker,job,part,path,receipt,context|{key:report},[key],cancel,compressed_write,atomic_json)
            worker._progress(job,(2*part+ARMS.index(key)+1)/(2*len(payload['configurations'])+1),'Original final account saved: '+key,part)
    with lab.store.db() as db:
        db.execute('BEGIN');trial=lab.store._trials.row(db,jid,0,'aggregate')
        if trial['artifact_sha256'] is not None or trial['state'] in {'checkpointed','completed'}:
            raise StateError('Original final aggregate publication is missing; replacement is refused.')
    lab.store.start_trial(jid,0,'aggregate',worker.owner);value=_reduce(lab,job,freeze,cancel)
    lab.store.computed_trial(jid,0,'aggregate',worker.owner,value);_publish(worker,job,value,cancel)
    inspect_final(lab,jid,active_owner=worker.owner,cancel=cancel);lab.result_index.build(jid,value,cancel,owner=worker.owner)
    inspect_final(lab,jid,active_owner=worker.owner,cancel=cancel);worker._progress(job,1,'Every frozen version saved on both final instruments.')
