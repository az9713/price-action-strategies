"""Read-only qualification of complete original five-arm and control accounts.

No prices are decoded or signals, accounts, jobs or final unlocks created here.
Every original control set is streamed and proved before its count can pass.
"""
from decimal import Decimal
import sqlite3
from .config import identity
from .research import require_current_source,study_input_hash,core_hash
from .research_funnel_arms import _study,_reserved,_verify,verify_arm
from .research_family_source import FamilyReports,_cancel
from .research_qualification import qualify,finish_controls,ARMS
from .store import StateError
from .trade_twins import EXECUTION_POLICIES,TOTAL_SETS
from .trade_twin_results import CanonicalOutcome
from .trade_twin_jobs import _payload,_existing,verify_child
from .trade_twin_source import read_saved_source
from .trade_twin_views import Originals,original_preparation,_load
from .trade_twin_parts import MAX_PART_BYTES


def _arms(lab,sid):
    with lab.store.db() as db:
        db.execute('BEGIN');study=_study(lab,db,sid);reservation=_reserved(lab,db,study)
        if reservation is None:return study,None
        jobs={}
        for key,binding in reservation['arms'].items():
            job=lab.store.job(binding['job_id']);_verify(lab,db,job,study,reservation);jobs[key]=job
        return study,jobs


def _control(lab,parent,part,cancel):
    source=read_saved_source(lab,parent['id'],part,cancel)
    payload=_payload(parent,source)
    with lab.store.db() as db:
        db.execute('BEGIN');child=_existing(lab.store,db,payload)
    if child is None:return dict(state='missing'),None
    verify_child(lab,child,cancel)
    if child['status']!='completed':return dict(state=child['status'],job_id=child['id']),None
    original=Originals(lab,child['id'],cancel=cancel)
    with lab.store.db() as db:
        db.execute('BEGIN');_,preparation=original_preparation(original,db)
    plan=preparation['plan'];eligible=bool(plan['sources']) and all(plan['pools'])
    if (plan['source_parent_identity']!=source['authority_hash'] or original.manifest['ineligible'] is not (not eligible)):
        raise StateError('Original diagnostic eligibility or source authority differs.')
    if not eligible:
        original.guard()
        return dict(state='ineligible',job_id=child['id'],original_plan_hash=plan['plan_hash'],
            reasons=plan['reasons'] if plan['sources'] else ['Original account has no executed trades.']),original
    counts={policy:[bytearray(TOTAL_SETS),0,0,0] for policy in EXECUTION_POLICIES}
    real=Decimal(source['source_profit'])
    for part,header in enumerate(original.headers):
        _cancel(cancel)
        with lab.store.db() as db:
            db.execute('BEGIN');_,_,path=original.part(db,part)
            value=_load(path,MAX_PART_BYTES,header['sha256'])
            if (value.get('format')!=2 or value.get('job_id')!=child['id'] or value.get('payload_hash')!=original.payload_hash
                    or any(value.get(k)!=header[k] for k in ['part','start','stop','attempt','plan_hash'])
                    or not isinstance(value.get('sets'),list) or len(value['sets'])!=2*(header['stop']-header['start'])):
                raise StateError('Original diagnostic part is incomplete or belongs to another computation.')
            for row in value['sets']:
                _cancel(cancel);outcome=CanonicalOutcome.model_validate(row['outcome']);ordinal=outcome.set_index;policy=outcome.policy
                if (outcome.plan_hash!=original.header['plan_hash'] or outcome.seed!=original.payload['seed']
                        or outcome.trade_count!=source['source_count'] or len(row['members'])!=outcome.trade_count
                        or len(row['draw']['matches'])!=outcome.trade_count or not header['start']<=ordinal<header['stop']
                        or counts[policy][0][ordinal]):
                    raise StateError('Original diagnostic ordinal, complete cohort or interpretation differs.')
                original.row_original(db,ordinal,policy,identity(row),part,header['attempt'])
                counts[policy][0][ordinal]=1
                if outcome.state=='failed':counts[policy][2]+=1
                else:counts[policy][1]+=1;counts[policy][3]+=Decimal(outcome.net_profit)>=real
    summaries=original.report['summaries']
    if set(summaries)!=set(EXECUTION_POLICIES):raise StateError('Original diagnostic interpretations differ.')
    for policy,(seen,complete,failed,exceedances) in counts.items():
        summary=summaries[policy];observed=sum(seen)
        if any(summary.get(key)!=value for key,value in dict(expected_sets=TOTAL_SETS,observed_sets=observed,
                complete_sets=complete,failed_sets=failed,exceedances=exceedances,real_profit=source['source_profit']).items()):
            raise StateError('Original diagnostic summary differs from complete original computed set counts.')
        if observed!=TOTAL_SETS or failed or complete!=TOTAL_SETS:
            original.guard();return dict(state='incomplete',job_id=child['id']),original
    original.guard();verify_child(lab,lab.store.job(child['id']),cancel)
    return dict(state='completed',job_id=child['id'],summaries=summaries,
        original_report_hash=original.report_hash,original_manifest_hash=original.manifest_hash,
        original_source_authority_hash=source['authority_hash'],all_original_set_occurrences_verified=True),original


def qualification_snapshot(lab,sid,cancel=None,*,include_controls=True):
    """A snapshot never schedules missing work or silently repairs originals."""
    _cancel(cancel);require_current_source()
    try:
        study,jobs=_arms(lab,sid);spec=study['spec'];study_hash=study_input_hash(spec)
        if jobs is None:return dict(study_id=sid,state='awaiting_arm_reservation',candidate_ids=[],qualification_does_not_consume_final=True)
        statuses={key:dict(job_id=job['id'],status=job['status']) for key,job in jobs.items()}
        if any(job['status']!='completed' for job in jobs.values()):
            return dict(study_id=sid,state='incomplete_accounts',arms=statuses,candidate_ids=[],qualification_does_not_consume_final=True)
        sources={key:FamilyReports(lab,jobs[key]['id'],None,cancel,_all_families=True) for key in ARMS}
        result=qualify(spec,sources,cancel=cancel);controls={};originals=[]
        parent=jobs['primary_discovery']
        for part,row in enumerate(result['rows']):
            _cancel(cancel)
            if include_controls and row['prequalified']:
                value,original=_control(lab,parent,part,cancel);controls[row['config_id']]=value
                if original is not None:originals.append(original)
        result=finish_controls(result,controls,cancel)
        for original in originals:original.guard()
        for key,source in sources.items():source.guard();verify_arm(lab,lab.store.job(jobs[key]['id']),cancel)
        again,current=_arms(lab,sid)
        if study_input_hash(again['spec'])!=study_hash or current!=jobs:raise StateError('Original study/arm state changed while qualifying.')
        _cancel(cancel);require_current_source()
        return result | dict(study_id=sid,controls=controls,evidence_phase='qualified' if include_controls else 'preliminary',
            source_authority=dict(study_input_hash=study_hash,
            core_hash=core_hash(),original_saved_accounts_verified=True,all_frozen_versions_included=True,
            price_signal_or_financial_recomputation=False,derived_result_views_used=bool(controls),
            diagnostic_source_locator_derived_views_used=bool(controls),derived_result_views_used_for_authority=False,
            arms={key:dict(job_id=source.jid,payload_hash=source.payload_hash,root_sha256=source.root_sha,
                original_result_event_id=source.result_event,verified_parts=len(source.used),
                parts=[dict(part=part,config_id=cid,report_sha256=source.rows[part]['report_sha256'],
                    witness=source.used[part]) for cid,part in source.parts.items()]) for key,source in sources.items()}))
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,TypeError,KeyError,OverflowError) as error:
        raise StateError('Original qualification evidence is missing, corrupt or incompatible; no strategy is certified.') from error


def verify_snapshot(lab,value,cancel=None):
    """Check witnesses after the caller proves its original analysis occurrence.

    This checks account/control ancestry, not a supplied certificate's arithmetic.
    Owned saved inspection separately binds the complete value to its original
    computation/checkpoint/publication before granting any saved-result authority.
    """
    _cancel(cancel);require_current_source()
    try:
        study,jobs=_arms(lab,value['study_id']);spec=study['spec'];authority=value['source_authority']
        configurations=spec['configurations'];ids=[identity(c) for c in configurations]
        if (jobs is None or any(job['status']!='completed' for job in jobs.values())
                or authority['study_input_hash']!=study_input_hash(spec) or authority['core_hash']!=core_hash()
                or value['configuration_universe_hash']!=spec['configuration_universe_hash']
                or value['version_count']!=len(ids) or [r['config_id'] for r in value['rows']]!=ids
                or set(authority['arms'])!=set(ARMS) or value['evidence_phase'] not in {'preliminary','qualified'}):
            raise StateError('Saved qualification omits or substitutes original study/accounts.')
        for key in ARMS:
            source=FamilyReports(lab,jobs[key]['id'],None,cancel,_all_families=True);saved=authority['arms'][key]
            expected=dict(job_id=source.jid,payload_hash=source.payload_hash,root_sha256=source.root_sha,
                original_result_event_id=source.result_event,verified_parts=len(ids))
            if (any(saved.get(k)!=v for k,v in expected.items()) or len(saved['parts'])!=len(ids)):
                raise StateError('Saved qualification original arm identity changed.')
            for part,(cid,record) in enumerate(zip(ids,saved['parts'])):
                _cancel(cancel)
                if (record['part']!=part or record['config_id']!=cid or source.parts[cid]!=part
                        or record['report_sha256']!=source.rows[part]['report_sha256'] or len(record['witness'])!=3
                        or value['rows'][part]['accounts'][key]['report_hash']!=record['witness'][0]):
                    raise StateError('Saved qualification account witness or membership differs.')
                computed,attempt,events=record['witness'];source.used[part]=(computed,attempt,tuple(events))
            source.guard();verify_arm(lab,jobs[key],cancel)
        required={row['config_id'] for row in value['rows'] if row['prequalified']}
        if value['evidence_phase']=='preliminary':
            if value['controls']:raise StateError('A preliminary account checkpoint cannot contain diagnostic decisions.')
        else:
            if set(value['controls'])!=required:raise StateError('Saved qualification diagnostic membership differs.')
            for part,row in enumerate(value['rows']):
                if row['prequalified']:
                    current,original=_control(lab,jobs['primary_discovery'],part,cancel)
                    if current!=value['controls'][row['config_id']]:raise StateError('Original diagnostic evidence changed since qualification.')
                    if original is not None:original.guard()
        again,current=_arms(lab,study['id'])
        if study_input_hash(again['spec'])!=study_input_hash(spec) or current!=jobs:
            raise StateError('Original study/arms changed while verifying saved qualification.')
        _cancel(cancel);require_current_source()
        return study,jobs
    except (StateError,InterruptedError):raise
    except (OSError,sqlite3.DatabaseError,ValueError,TypeError,KeyError,OverflowError) as error:
        raise StateError('Original saved qualification witnesses are missing or incompatible; no math was regenerated.') from error
