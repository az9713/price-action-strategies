"""Durable data-free preparation followed by guarded primary signal qualification."""
from datetime import date,timedelta
from pathlib import Path
import gzip,hashlib,json,os
from .config import Strategy,canonical,identity
from .data import read_manifest
from .research import core_hash,core_subject,require_current_source
from .store import StateError
from .spread import SpreadSettings,select,file_hash
from .spread_jobs import SpreadJournal,coordinate,WINDOW,digest
from .spread_preparation import prepare_plan,preparation_contract
from .sampling import count_discovery_signals
from .service import compressed_read,compressed_write

def execute_spread(worker,job,cancel):
    lab=worker.lab;payload=job['payload'];context=payload['context'];settings=SpreadSettings(**payload['settings']);journal=SpreadJournal(lab.store,job,worker.owner,stream=True)
    folder=lab.output_path(job['id']).parent;folder.mkdir(parents=True,exist_ok=True);signals=folder/'spread-signals';signals.mkdir(exist_ok=True)
    binding=identity(payload);contract=preparation_contract(settings,binding);original_status=journal.status()
    def authorize():
        require_current_source()
        if cancel():raise InterruptedError('Spread qualification canceled before source access.')
        manifest=read_manifest(lab.datasets_root,context['dataset_id'])
        if identity(manifest)!=context['dataset_manifest_hash']:raise StateError('Frozen spread dataset manifest changed.')
        warmup=max(manifest['quality']['start'],(date.fromisoformat(context['start'])-timedelta(days=365)).isoformat())
        lab.guard.access([context['primary_symbol']],warmup,context['end'],'spread_qualification',record=False)
        if 'news_calendar_id' in context:
            calendar=lab.news.load(context['news_calendar_id'])
            if identity(calendar)!=context['news_calendar_hash'] or calendar!=payload.get('news_calendar'):raise StateError('Frozen spread news calendar changed.')
        return manifest
    authorize()
    if original_status['event_count']==0:journal.append(dict(kind='preparation_started',contract_hash=identity(contract)))
    elif original_status['preparation_contract_hash']!=identity(contract):raise StateError('Spread preparation contract changed after queueing.')
    batches=(e['record'] for e in journal.iter_events(journal.replay_through) if e['kind']=='preparation_batch')
    sealed=original_status['proposal_plan_id']
    def preparation_progress(done,total):
        worker._progress(job,max(job['progress'],.4*done/total),f'{done} / {total} proposal batches frozen; no signal prices read.')
    prepared=prepare_plan(folder/'spread-proposals',folder/'spread-preparation',settings,binding=binding,committed=batches,
        commit=lambda record:journal.append(dict(kind='preparation_batch',record=record)),cancel=cancel,progress=preparation_progress,expected_plan_id=sealed)
    plan=prepared['plan']
    if not sealed:journal.append(dict(kind='preparation_sealed',plan_id=plan.plan_id))
    artifacts={e['event']['evidence']['evidence_sha256']:e['artifact_sha256'] for e in journal.iter_envelopes(journal.replay_through) if e['event']['kind']=='probe_completed'}
    def preserved(path):
        if not path.exists():return
        target=folder/'spread-orphans';target.mkdir(exist_ok=True);destination=target/(file_hash(path)+'.gz')
        if destination.exists():
            if file_hash(destination)!=file_hash(path):raise StateError('Original spread orphan bytes changed.')
            path.unlink()
        else:path.replace(destination)
    def save_signal(value):
        report=lab.spread_signal_probe(context,Strategy(**value),cancel);raw=canonical(report).encode();evidence_hash=hashlib.sha256(raw).hexdigest();path=signals/(evidence_hash+'.json.gz');zipped=gzip.compress(raw,mtime=0)
        if path.exists():
            if evidence_hash in artifacts:
                if file_hash(path)!=artifacts[evidence_hash]:raise StateError('Committed spread signal artifact changed.')
            elif path.read_bytes()!=zipped:preserved(path)
        if not path.exists():
            temporary=path.with_name(path.name+'.uncommitted');preserved(temporary)
            with temporary.open('wb') as stream:stream.write(zipped);stream.flush();os.fsync(stream.fileno())
            temporary.replace(path)
        return dict(signal_count=report['signal_count'],evidence_sha256=evidence_hash)
    def verify_signal(point,evidence,expected=None,check_prices=False):
        manifest=authorize();evidence_hash=digest(evidence['evidence_sha256']);path=signals/(evidence_hash+'.json.gz')
        if check_prices and file_hash(lab.datasets_root/context['dataset_id']/'minutes.parquet')!=manifest['parquet_sha256']:raise StateError('Original spread source bytes changed before signal reuse.')
        try:
            snapshot=path.read_bytes();artifact_hash=hashlib.sha256(snapshot).hexdigest()
            if expected is not None and artifact_hash!=expected:raise StateError('Committed spread signal artifact changed.')
            report=json.loads(gzip.decompress(snapshot))
            if identity(report)!=evidence_hash or report['context']!=context or report['core_hash']!=core_hash() or report['numerical_contract']!=core_subject() or report['config_id']!=point['config_id'] or identity(report['config'])!=point['config_id']:raise StateError('Saved spread signal evidence belongs to different inputs or code.')
            count=count_discovery_signals(report['signals'],context['start'],context['end'])
            if report['signal_count']!=count or evidence['signal_count']!=count or report['excluded_warmup_signals']!=len(report['signals'])-count or any(s['symbol']!=context['primary_symbol'] for s in report['signals']):raise StateError('Saved primary signal counts/scope changed.')
        except StateError:raise
        except (OSError,ValueError,TypeError,KeyError) as error:raise StateError('Committed spread signal evidence is missing or malformed.') from error
        return report,artifact_hash
    def record(event):
        if event['kind']=='probe_completed':
            point={k:event[k] for k in ['family','batch','ordinal','config_id']};report,artifact_hash=verify_signal(point,event['evidence'])
            journal.append(event,artifact_sha256=artifact_hash);artifacts[event['evidence']['evidence_sha256']]=artifact_hash
        else:journal.append(event)
        if event['kind']=='batch_finished':
            p=journal.status();worker._progress(job,max(job['progress'],.4+.6*p['selected_versions']/p['target_versions']),f"{p['selected_versions']} / {p['target_versions']} signal-qualified versions; P&L not started.")
    def reuse(point,evidence):
        expected=artifacts.get(evidence['evidence_sha256'])
        if expected is None:raise StateError('Signal reuse has no committed original artifact.')
        report,artifact=verify_signal(point,evidence,expected,check_prices=True)
        lab.store.checkpoint_trial(job['id'],coordinate(settings,point),WINDOW,worker.owner,report,artifact)
    prefix=(e for e in journal.iter_events(journal.replay_through) if e['kind'] not in {'preparation_started','preparation_batch','preparation_sealed'})
    result=select(plan,context,save_signal,record,authorize=authorize,cancel=cancel,replay=prefix,verify_evidence=reuse)
    # Reconcile every committed signal artifact again before publishing a root,
    # including failed probes that influenced the qualified selection.
    for envelope in journal.iter_envelopes():
        event=envelope['event']
        if event['kind']=='probe_completed':verify_signal({k:event[k] for k in ['family','batch','ordinal','config_id']},event['evidence'],envelope['artifact_sha256'])
    authorize();lab.store.verify_trial_plan(job['id']);projection=journal.status()
    stable={k:v for k,v in result.items() if k not in {'probe_computations','reused_probes','new_events'}}
    value=dict(job_id=job['id'],kind='spread',payload_hash=binding,core_hash=core_hash(),numerical_contract=core_subject(),dataset_id=payload['dataset_id'],dataset_manifest_hash=payload['dataset_manifest_hash'],dataset_context=payload['dataset_context'],
        spread_selection=stable,selection_manifest=result['selection_manifest'],selection_manifest_hash=result['selection_manifest_hash'],spread_summary=projection,account_phase='not_started',
        context=context,source_video='https://www.youtube.com/watch?v=z97PnFIPoFg',scope='Primary-signal-qualified spread selection. Selected-account P&L and the later source funnel have not run.')
    destination=lab.output_path(job['id']);saved=[e['details']['sha256'] for e in lab.store.events(job['id']) if e['kind']=='result_saved']
    if saved:
        if not destination.exists() or file_hash(destination)!=saved[-1]:raise StateError('Saved spread result bytes changed.')
        original=compressed_read(destination)
        for key in ['job_id','kind','payload_hash','core_hash','context','selection_manifest','selection_manifest_hash']:
            if original.get(key)!=value[key]:raise StateError('Saved spread result differs from its original qualified selection.')
    else:
        preserved(destination);compressed_write(destination,value);lab.store.event('result_saved',job['id'],dict(sha256=file_hash(destination)))
    worker._progress(job,1,'Spread qualification saved. Selected-account P&L has not started.' if result['complete'] else 'Spread budget exhausted; no complete selected set or P&L search authorized.')
