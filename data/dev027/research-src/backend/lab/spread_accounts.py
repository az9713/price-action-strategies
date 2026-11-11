"""Prespecified financial continuation of one complete original qualified spread."""
from datetime import date,timedelta
import gzip,json
from .config import Strategy,Costs,identity
from .data import read_manifest
from .research import require_current_source,core_hash,core_subject
from .store import StateError
from .spread import ProposalPlan,select,file_hash,SpreadSettings
from .spread_jobs import SpreadJournal
from .sampling import count_discovery_signals

INHERIT=['dataset_id','dataset_manifest_hash','dataset_context','start','end','seed','costs','portfolio','statistics','minimum_trades','minimum_sharpe','news_dates','news_calendar_id','news_calendar']

def parent(lab,parent_id,cancel=None):
    """Verify originals and replay qualification; never generate a new signal or account."""
    require_current_source()
    try:
        job=lab.store.job(parent_id);payload=job['payload']
        if job['kind']!='spread' or job['status']!='completed' or payload.get('core_hash')!=core_hash():raise StateError('Continue a completed spread from the current numerical source.')
        result=lab.result(parent_id);context=payload['context'];settings=SpreadSettings(**payload['settings'])
        if result.get('core_hash')!=core_hash() or result.get('context')!=context or result.get('account_phase')!='not_started' or result.get('spread_selection',{}).get('complete') is not True or result.get('selection_manifest') is None:raise StateError('An incomplete or exhausted spread cannot authorize financial trials.')
        journal=SpreadJournal(lab.store,job,None,stream=True);status=journal.status()
        if status['stage']!='qualified' or not status['qualified_complete'] or status['selection_manifest_hash']!=result['selection_manifest_hash']:raise StateError('Spread completion differs from its original journal.')
        manifest=read_manifest(lab.datasets_root,payload['dataset_id'])
        if identity(manifest)!=payload['dataset_manifest_hash'] or context['dataset_manifest_hash']!=payload['dataset_manifest_hash']:raise StateError('Original spread source manifest changed before accounts.')
        lab.dataset_context_input(payload)
        warmup=max(manifest['quality']['start'],(date.fromisoformat(context['start'])-timedelta(days=365)).isoformat())
        def authorize():
            require_current_source()
            if cancel and cancel():raise InterruptedError('Spread account continuation canceled while verifying original evidence.')
            lab.guard.access([context['primary_symbol']],warmup,context['end'],'spread_account_parent',record=False)
        authorize()
        if file_hash(lab.datasets_root/payload['dataset_id']/'minutes.parquet')!=manifest['parquet_sha256']:raise StateError('Original spread price bytes changed before accounts.')
        lab.borrow_input(payload['dataset_id'],Costs(**payload['costs']),context['start'],context['end'],symbols=[context['primary_symbol']])
        lab.news_input(payload,[Strategy(news='skip')] if settings.include_news else [],context['start'],context['end'])
        if settings.include_news and identity(lab.news.load(context['news_calendar_id']))!=context['news_calendar_hash']:raise StateError('Original spread news calendar changed before accounts.')
        folder=lab.output_path(parent_id).parent;plan=ProposalPlan.open(folder/'spread-proposals',status['proposal_plan_id'])
        if plan.manifest['settings']!=settings.model_dump():raise StateError('Original proposal settings differ from the qualified parent.')
        for envelope in journal.iter_envelopes():
            authorize();event=envelope['event']
            if event['kind']!='probe_completed':continue
            evidence=event['evidence'];path=folder/'spread-signals'/(evidence['evidence_sha256']+'.json.gz');snapshot=path.read_bytes()
            import hashlib
            if hashlib.sha256(snapshot).hexdigest()!=envelope['artifact_sha256']:raise StateError('Original committed spread signal bytes changed before accounts.')
            report=json.loads(gzip.decompress(snapshot));count=count_discovery_signals(report['signals'],context['start'],context['end'])
            if (identity(report)!=evidence['evidence_sha256'] or report['context']!=context or report['core_hash']!=core_hash() or report['numerical_contract']!=core_subject() or
                report['config_id']!=event['config_id'] or identity(report['config'])!=event['config_id'] or report['signal_count']!=count or evidence['signal_count']!=count or
                report['excluded_warmup_signals']!=len(report['signals'])-count or any(s['symbol']!=context['primary_symbol'] for s in report['signals'])):
                raise StateError('Original committed primary signal evidence changed before accounts.')
        def forbidden(*a,**k):raise StateError('A completed parent requires a complete original replay; no new qualification is allowed.')
        events=(e for e in journal.iter_events() if e['kind'] not in {'preparation_started','preparation_batch','preparation_sealed'})
        replayed=select(plan,context,forbidden,forbidden,authorize=authorize,cancel=cancel,replay=events)
        stable={k:v for k,v in replayed.items() if k not in {'probe_computations','reused_probes','new_events'}}
        if not replayed['complete'] or replayed['selection_manifest']!=result['selection_manifest'] or replayed['selection_manifest_hash']!=result['selection_manifest_hash'] or result['spread_selection']!=stable:
            raise StateError('Original spread result differs from its full qualification replay.')
        configurations=replayed['selection_manifest']['configurations']
        if len(configurations)!=len(settings.families)*settings.per_family or len({identity(c) for c in configurations})!=len(configurations):raise StateError('The full unique qualified cohort is required before accounts.')
        # Confirm the original root once more after reading all its supporting artifacts.
        if lab.result(parent_id)!=result:raise StateError('Original spread result changed during continuation verification.')
        authorize();return job,result
    except (InterruptedError,StateError):raise
    except (OSError,ValueError,TypeError,KeyError) as error:raise StateError('Original spread evidence is missing, malformed or incompatible; account continuation refused.') from error

def payload_for(lab,job,result):
    original=job['payload'];root_hash=file_hash(lab.output_path(job['id']))
    from .models import SpreadAccountScreen
    screen=SpreadAccountScreen(include_news=original['settings']['include_news'],minimum_signals=original['settings']['minimum_signals'],minimum_trades=original['minimum_trades'],minimum_sharpe=original['minimum_sharpe'])
    proposal_manifest=json.loads((lab.output_path(job['id']).parent/'spread-proposals/manifest.json').read_text(encoding='utf-8'))
    return {k:original[k] for k in INHERIT if k in original}|dict(name=('Spread accounts: '+original['name'])[:100],core_hash=core_hash(),
        configurations=result['selection_manifest']['configurations'],evaluation_symbols=[original['primary_symbol']],count=len(result['selection_manifest']['configurations']),
        sampling_policy=screen.model_dump(),spread_sampling=dict(mode='spread_selected',recipe_hash=proposal_manifest['recipe_hash'],selection_manifest_hash=result['selection_manifest_hash'],
            selected_versions=len(result['selection_manifest']['configurations']),qualification_probes=result['spread_summary']['committed_probes'],planned_proposals=result['spread_summary']['planned_proposals']),
        spread_parent=dict(job_id=job['id'],payload_hash=identity(original),result_sha256=root_hash,selection_manifest_hash=result['selection_manifest_hash']))

def create(lab,parent_id):
    job,result=parent(lab,parent_id);payload=payload_for(lab,job,result)
    return lab.store.create_job('spread_accounts',payload,spread_parent=payload['spread_parent'])

def verify_child(lab,job,cancel=None):
    frozen=job['payload'];binding=frozen.get('spread_parent',{});parent_job,result=parent(lab,binding.get('job_id'),cancel)
    expected=payload_for(lab,parent_job,result)
    if identity(frozen)!=identity(expected):raise StateError('Spread account inputs differ from their complete original parent assumptions.')
    with lab.store.db() as db:
        link=db.execute('SELECT child_id FROM spread_account_links WHERE parent_id=?',(parent_job['id'],)).fetchone()
        event=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='spread_accounts_frozen' ORDER BY id LIMIT 1",(parent_job['id'],)).fetchone()
        original=None if event is None else json.loads(event['details'])
        if link is None or link['child_id']!=job['id'] or original!=dict(child_id=job['id'],**binding):raise StateError('Spread account child differs from its original atomic continuation link.')
    return result

def screen(rows,payload,cancel=None):
    from .sampling import initial_screen
    from .models import SpreadAccountScreen
    return initial_screen(rows,SpreadAccountScreen(**payload['sampling_policy']),cancel)
