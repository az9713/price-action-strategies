"""Application operations shared by HTTP and durable workers."""
from dataclasses import asdict
from datetime import date,timedelta
from pathlib import Path
import gzip
import json
import math
import uuid
import hashlib
import numpy as np
from .config import Strategy,Costs,Portfolio,FAMILIES,TIMEFRAMES,identity,canonical
from .data import read_manifest,load_window,normalize,audit,prepare,aggregate,Action,atomic_json,DataError,select_dataset
from .evaluation_cache import current_cache
from .signals import generate_signals
from .engine import simulate
from .metrics import summary,block_interval
from .models import Experiment,Search,Study,Download,PortfolioExperiment,BenchmarkExperiment,ControlsExperiment,BehaviorExperiment,AblationExperiment,BorrowSensitivity
from .benchmarks import compare_passive
from .controls import feature_table,make_control_plan
from .behavior import analyze_chart
from .research import Guard,ResearchError,core_hash,core_subject,require_current_source,study_input_hash
from .store import Store,StateError
from .news import NewsStore,NewsClock,NewsCalendar,event_dates,news_assumptions
from .borrow import BorrowSchedule
from .sensitivity import cost_arms,POLICY
from .dataset_context import freeze_context,validate_context

def compressed_write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=canonical(value).encode()
    temp=path.with_suffix('.tmp')
    temp.write_bytes(gzip.compress(raw,mtime=0))
    temp.replace(path)

def compressed_read(path): return json.loads(gzip.decompress(path.read_bytes()))

class SamplingError(DataError):
    def __init__(self,message,configurations,sampling):
        super().__init__(message);self.configurations=configurations;self.sampling=sampling

def sample_configurations(request:Search):
    if request.sampling_policy.mode!='legacy':
        from .sampling import sample_common,CommonSamplingError
        try:return sample_common(request)
        except CommonSamplingError as error:raise SamplingError(str(error),error.configurations,error.sampling) from error
    families=list(dict.fromkeys(request.families));frames=list(dict.fromkeys(request.timeframes))
    if not families or set(families)-set(FAMILIES) or not frames or set(frames)-set(TIMEFRAMES):
        raise DataError('Choose supported, nonempty strategy families and timeframes.')
    rng=np.random.default_rng(request.seed)
    configurations=[];seen=set();attempts=0;duplicates=0;rejected=0;proposals=[]
    def record():
        return dict(attempts=attempts,unique=len(seen),duplicates=duplicates,rejected=rejected,seed=request.seed,
            proposals=proposals,method='Round-robin family/timeframe strata; seeded conditional draws, unique configurations. Not the undisclosed host grid.')
    while len(configurations)<request.count:
        if attempts>=min(request.count*1000,200000):
            raise SamplingError('Requested sample exceeds the bounded200000-proposal/unique-space allowance; no partial search will run.',configurations,record())
        idx=len(configurations)
        family=families[idx%len(families)];tf=frames[(idx//len(families))%len(frames)]
        value=dict(family=family,timeframe=tf,news=request.strategy.news,direction=str(rng.choice(['both','long','short'])),
            swing_strength=int(rng.choice([2,3,5,8])),stop_reference=str(rng.choice(['swing','level','wick'])),
            stop_buffer=float(rng.choice([0,.1,.25])),stop_kind=str(rng.choice(['hard','close'])),
            target=str(rng.choice(['1R','1.5R','2R','3R','4R','5R','swing'])),
            confirmation=str(rng.choice(['none','close_back','rejection','engulfing','either'])),
            entry=str(rng.choice(['next_open','limit'])),max_hold=int(rng.choice([24,96])),
            trend_filter=str(rng.choice(['none','setup','higher','daily'])),
            session_filter=str(rng.choice(['core','open'])),skip_run_days=int(rng.choice([0,3,5])))
        if family in {'level_bounce','breakout','flip_zone'}:
            value.update(min_touches=int(rng.integers(1,5)),level_shape=str(rng.choice(['line','zone'])))
        attempts+=1
        try:configuration=Strategy(**value)
        except ValueError as error:
            rejected+=1;proposals.append(dict(attempt=attempts,status='invalid',configuration=value,reason=str(error)[:500]));continue
        config_id=identity(configuration);duplicate=config_id in seen
        proposals.append(dict(attempt=attempts,status='duplicate' if duplicate else 'accepted',config_id=config_id,family=family,timeframe=tf))
        if duplicate:duplicates+=1
        else:seen.add(config_id);configurations.append(configuration.model_dump())
    return configurations,record()

from .result_index import ResultIndex,ViewUnavailable

class Lab:
    def __init__(self,root:Path):
        self.root=root;self.store=Store(root);self.guard=Guard(self.store);self.result_index=ResultIndex(self)
        self.news=NewsStore(root)
        self.datasets_root=root/'data'/'datasets';self.datasets_root.mkdir(parents=True,exist_ok=True)
        subject=root/'data'/'subjects'/(core_hash()+'.json')
        if subject.exists():
            if identity(json.loads(subject.read_text(encoding='utf-8')))!=core_hash(): raise StateError('Saved numerical subject was modified.')
        else: atomic_json(subject,core_subject())
        self._record_prior_exposure()

    def _record_prior_exposure(self):
        with self.store.db() as db:
            if db.execute("SELECT 1 FROM events WHERE kind='prior_exposure_migrated' LIMIT 1").fetchone(): return
        windows=[]
        probe=self.root/'research'/'alpaca_probe'/'report.json'
        if probe.exists():
            for request in json.loads(probe.read_text(encoding='utf-8')).get('requests',[]):
                params=request.get('parameters',{})
                if request.get('http_status')==200 and params.get('start') and params.get('end'):
                    windows.append((params['symbols'].split(','),params['start'][:10],params['end'][:10],'prior_provider_probe'))
        for path in (self.root/'data'/'cli-runs').glob('*.json'):
            value=json.loads(path.read_text(encoding='utf-8'))
            manifest=read_manifest(self.datasets_root,value['dataset_id'])
            q=manifest['quality'];windows.append((q['symbols'],q['start'],q['end'],'prior_prototype_analysis'))
        for symbols,start,end,kind in windows:
            self.guard.access(symbols,start,end,kind)
        self.store.event('prior_exposure_migrated','system',{'windows':len(windows)})

    def datasets(self):
        output=[]
        for folder in self.datasets_root.iterdir():
            if not folder.is_dir(): continue
            try:
                m=read_manifest(self.datasets_root,folder.name)
                q=m['quality']
                output.append(dict(id=m['id'],symbols=q['symbols'],start=q['start'],end=q['end'],
                    rows=q['rows'],regular_rows=q['regular_rows'],missing_minutes=q['missing_minutes'],
                    eligible=q['eligible'] and not m['metadata'].get('corporate_action_issues'),
                    source=m['metadata'].get('provider',m['metadata'].get('source','Imported')),
                    input_kind=m['metadata'].get('input_kind','user_import'),
                    selection=m['metadata'].get('selection'),
                    corporate_action_issues=m['metadata'].get('corporate_action_issues',[])))
            except (OSError,ValueError,KeyError):
                output.append(dict(id=folder.name,error='Dataset manifest is invalid; not eligible.'))
        return output

    def freeze_news(self,payload,configurations,start,end):
        if payload.get('news_dates') is not None:raise DataError('Use the versioned news workflow instead of raw news_dates.')
        cid=payload.get('news_calendar_id')
        if cid is None:
            if any(c.news!='trade' for c in configurations):raise DataError('This news scenario requires a versioned news calendar.')
            return {}
        snapshot=self.news.load(cid);self.news.clock(cid,start,end,snapshot)
        return dict(news_calendar=snapshot)

    def borrow_input(self,dataset_id,costs,start,end,symbols=None):
        if costs.borrow_scenario is None:return None
        manifest=read_manifest(self.datasets_root,dataset_id)
        try:
            schedule=BorrowSchedule(costs.borrow_scenario,costs.borrow_annual,costs.borrow_available)
            schedule.validate(manifest['quality']['symbols'] if symbols is None else symbols,start,end)
        except ValueError as exc:raise DataError(str(exc)) from exc
        return schedule

    def news_input(self,payload,configurations,start,end):
        if payload.get('news_dates') is not None:raise DataError('Use the versioned news workflow instead of raw news_dates.')
        cid=payload.get('news_calendar_id');snapshot=payload.get('news_calendar')
        if cid is None:
            if snapshot is not None or any(c.news!='trade' for c in configurations):raise DataError('A frozen versioned news calendar is required.')
            return None,None
        if not isinstance(snapshot,dict) or snapshot.get('id')!=cid:raise DataError('Frozen news calendar identity is missing or changed.')
        return self.news.clock(cid,start,end,snapshot),snapshot

    def dataset_audit(self,dataset_id):
        manifest=read_manifest(self.datasets_root,dataset_id)
        # Manifests remain intact locally, but an ordinary audit must not expose
        # future distribution amounts or raw action payloads from a protected
        # interval (including metadata inherited by a discovery-only subset).
        allowed={'provider','source','input_kind','selection','corporate_action_issues',
            'corporate_actions_status','limitations','adjustment','actions_attestation'}
        return {k:manifest[k] for k in ['id','version','quality','normalization','bars_sha256','parquet_sha256']}|{
            'metadata':{k:v for k,v in manifest['metadata'].items() if k in allowed},
            'manifest_sha256':identity(manifest),
            'action_detail_policy':'Price-bearing action details remain in the immutable local manifest; ordinary audits do not expose future action values.'}

    def preview(self,dataset_id,symbol,start,end,timeframe='1h',limit=1000):
        manifest=read_manifest(self.datasets_root,dataset_id)
        if symbol not in manifest['quality']['symbols']: raise DataError('Unknown instrument in this dataset.')
        q=manifest['quality']
        if start>end or start<q['start'] or end>q['end']: raise DataError('Preview dates must stay inside the dataset.')
        if timeframe not in TIMEFRAMES or not 1<=limit<=5000: raise DataError('Unsupported preview timeframe or row limit.')
        self.guard.access([symbol],start,end,'preview')
        frame,_=load_window(self.datasets_root,dataset_id,start,end,[symbol])
        if frame.empty: return []
        actions=[Action(**a) for a in manifest['actions'] if a['symbol']==symbol]
        bars=aggregate(prepare(frame,actions),timeframe)
        columns=['symbol','timestamp','available_at','open','high','low','close','volume','complete','partial_length','factor']
        return json.loads(bars[columns].tail(min(limit,5000)).to_json(orient='records',date_format='iso'))

    def select(self,dataset_id,symbols,start,end):
        # Selection is not an analysis bypass: check protected ranges before raw reads.
        self.guard.access(symbols,start,end,'dataset_selection')
        return select_dataset(self.datasets_root,dataset_id,symbols,start,end)

    def spread_status(self,job_id):
        from .spread_jobs import bounded_status
        return bounded_status(self.store,job_id)

    def spread_events(self,job_id,after=0,limit=20):
        from .spread_jobs import event_page
        return event_page(self.store,job_id,after,limit)

    def spread_selections(self,job_id,after=0,limit=50):
        from .spread_jobs import selection_page
        return selection_page(self.store,job_id,after,limit)

    def repair_spread_account_link(self,job_id):
        from .spread_jobs import repair_account_link
        return repair_account_link(self.store,job_id)

    def create_spread_accounts(self,parent_id):
        from .spread_accounts import create
        return create(self,parent_id)

    def create_spread(self,request):
        from .models import SpreadExperiment
        request=SpreadExperiment.model_validate(request.model_dump(mode='json') if hasattr(request,'model_dump') else request)
        require_current_source();manifest=read_manifest(self.datasets_root,request.dataset_id);primary=request.primary_symbol
        if primary not in manifest['quality']['symbols']:raise DataError('Choose a primary instrument present in the frozen dataset.')
        start,end=str(request.start),str(request.end);self._validate_window(manifest,start,end,symbols=[primary])
        warmup=max(manifest['quality']['start'],(request.start-timedelta(days=365)).isoformat())
        self.guard.access([primary],warmup,end,'spread_preflight',record=False)
        self.borrow_input(request.dataset_id,request.costs,start,end,symbols=[primary])
        payload=request.model_dump(mode='json');payload.update(self.freeze_news(payload,[Strategy(news='skip')] if request.settings['include_news'] else [],start,end))
        context=dict(dataset_id=manifest['id'],dataset_manifest_hash=identity(manifest),primary_symbol=primary,start=start,end=end)
        if request.settings['include_news']:
            context.update(news_calendar_id=payload['news_calendar']['id'],news_calendar_hash=identity(payload['news_calendar']))
        payload.update(context=context,core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest),count=len(request.settings['families'])*request.settings['per_family'])
        return self.store.create_job('spread',payload)

    def create_experiment(self,request:Experiment|Search):
        require_current_source()
        m=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(m,str(request.start),str(request.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        self.guard.access(m['quality']['symbols'],m['quality']['start'],str(request.end),'experiment_preflight',record=False)
        payload=request.model_dump(mode='json')
        payload.update(self.freeze_news(payload,[request.strategy],str(request.start),str(request.end)))
        payload.update(core_hash=core_hash(),dataset_manifest_hash=identity(m),dataset_context=freeze_context(m))
        if isinstance(request,Search):
            try:configs,sampling=sample_configurations(request)
            except SamplingError as error:
                configs,sampling=error.configurations,error.sampling;payload['sampling_failure']=str(error)
            payload.update(configurations=configs,sampling=sampling)
            payload.update(self.freeze_news(payload,(Strategy(**c) for c in configs),str(request.start),str(request.end)))
            kind='search'
        else: kind='experiment'
        return self.store.create_job(kind,payload)

    def register_study(self,request:Study):
        require_current_source();request=Study(**request.model_dump(mode='json'))
        manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.discovery.start),str(request.holdout.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.discovery.start),str(request.holdout.end))
        extra=self.freeze_news(request.model_dump(mode='json'),request.configurations,str(request.discovery.start),str(request.holdout.end))
        extra['dataset_context']=freeze_context(manifest)
        return self.guard.register(request,manifest,extra)

    def create_portfolio(self,request:PortfolioExperiment):
        require_current_source()
        manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),
                          'portfolio_preflight',record=False)
        payload=request.model_dump(mode='json')
        payload.update(self.freeze_news(payload,request.configurations,str(request.start),str(request.end)))
        payload['configurations']=sorted(payload['configurations'],key=identity)
        payload.update(core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        return self.store.create_job('portfolio',payload)

    def screen(self,study_id):
        require_current_source()
        study=self.guard.study(study_id)
        self.guard.verify_inputs(study)
        self._study_source(study['spec'])
        if study['status']!='registered': raise ResearchError('Only a registered study can be screened.')
        if self.store.pending_study_job('screen',study_id):
            raise ResearchError('Screening is already queued/running.')
        spec=study['spec']
        return self.store.create_job('screen',dict(study_id=study_id,core_hash=core_hash(),name=study['name'],
            **({k:spec[k] for k in ['dataset_context','dataset_id','dataset_manifest_hash']} if 'dataset_context' in spec else {}),
            study_mode=spec.get('study_mode','independent'),study_input_hash=study_input_hash(spec),
            trial_configurations=[spec['configurations']] if spec.get('study_mode')=='portfolio' else spec['configurations'],
            trial_windows={k:spec[k] for k in ['discovery','validation']}))

    def create_ablation(self,request:AblationExperiment):
        require_current_source();manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),'ablation_preflight',record=False)
        payload=request.model_dump(mode='json');payload.update(configurations=[c.model_dump() for c in request.arms()],
            core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        payload.update(self.freeze_news(payload,request.arms(),str(request.start),str(request.end)))
        return self.store.create_job('ablation',payload)

    def create_borrow_sensitivity(self,request:BorrowSensitivity):
        require_current_source();manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),'borrow_sensitivity_preflight',record=False)
        payload=request.model_dump(mode='json')
        payload.update(self.freeze_news(payload,[request.strategy],str(request.start),str(request.end)))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        payload.update(cost_arms=cost_arms(request.costs,request.strategy),rate_policy=POLICY,
            original_costs_id=identity(request.costs),core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        return self.store.create_job('borrow_sensitivity',payload)

    def create_benchmarks(self,request:BenchmarkExperiment):
        require_current_source()
        manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),
                          'benchmark_preflight',record=False)
        payload=request.model_dump(mode='json')
        payload.update(core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        return self.store.create_job('benchmark',payload)

    def create_controls(self,request:ControlsExperiment):
        require_current_source()
        manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.borrow_input(request.dataset_id,request.costs,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),'controls_preflight',record=False)
        payload=request.model_dump(mode='json')
        payload.update(self.freeze_news(payload,[request.strategy],str(request.start),str(request.end)))
        payload.update(core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        return self.store.create_job('controls',payload)

    def create_behavior(self,request:BehaviorExperiment):
        require_current_source()
        manifest=read_manifest(self.datasets_root,request.dataset_id)
        self._validate_window(manifest,str(request.start),str(request.end))
        self.guard.access(manifest['quality']['symbols'],manifest['quality']['start'],str(request.end),'behavior_preflight',record=False)
        payload=request.model_dump(mode='json');payload['timeframes']=sorted(payload['timeframes'],key=lambda tf:list(TIMEFRAMES).index(tf))
        payload.update(core_hash=core_hash(),dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest))
        return self.store.create_job('behavior',payload)

    def dataset_context_input(self,payload):
        if 'dataset_context' not in payload:return None
        manifest=read_manifest(self.datasets_root,payload['dataset_id'])
        context=validate_context(payload['dataset_context'],manifest=manifest)
        if context['dataset_manifest_hash']!=payload.get('dataset_manifest_hash'):
            raise DataError('Dataset context and frozen dataset fingerprint differ.')
        return context

    def behavior_context(self,payload):
        manifest,regular,_,warmup=self._evaluation_input(payload['dataset_id'],payload['start'],payload['end'],
            expected_manifest=payload.get('dataset_manifest_hash'))
        return dict(manifest=manifest,regular=regular,warmup=warmup)

    def behavior_chart(self,context,payload,timeframe,cancel=None):
        result=analyze_chart(context['regular'],timeframe,payload['start'],payload['end'],payload.get('seed',42),payload['shift_replicas'],cancel)
        return dict(report_type='behavior_chart',core_hash=core_hash(),numerical_contract=core_subject(),
            dataset_id=payload['dataset_id'],dataset_manifest_hash=identity(context['manifest']),dataset_context=freeze_context(context['manifest']),start=payload['start'],end=payload['end'],
            seed=payload.get('seed',42),shift_replicas=payload['shift_replicas'],**result)

    def control_context(self,payload,cancel=None):
        configuration=Strategy(**payload['strategy'])
        clock,calendar=self.news_input(payload,[configuration],payload['start'],payload['end'])
        self.borrow_input(payload['dataset_id'],Costs(**payload['costs']),payload['start'],payload['end'])
        manifest,regular,actions,warmup=self._evaluation_input(payload['dataset_id'],payload['start'],payload['end'],
            expected_manifest=payload.get('dataset_manifest_hash'))
        signals=generate_signals(regular,configuration,clock,cancel)
        plan=make_control_plan(feature_table(regular,configuration,cancel),signals,configuration,
            payload['start'],payload['end'],payload.get('seed',42),payload['replicas'],cancel,news_dates=clock)
        charts={}
        for symbol,group in regular[regular.session.between(payload['start'],payload['end'])].groupby('symbol'):
            chart=aggregate(group,configuration.timeframe)
            charts[symbol]=json.loads(chart[['timestamp','available_at','open','high','low','close','volume','factor','complete']].to_json(orient='records',date_format='iso'))
        return dict(manifest=manifest,regular=regular,actions=actions,warmup=warmup,configuration=configuration,
                    signals=signals,plan=plan,charts=charts,news_calendar=calendar)

    def control_book(self,context,payload,signals,role,replica=None,cancel=None):
        cfg=context['configuration'];account=Portfolio(**payload['portfolio']);costs=Costs(**payload['costs'])
        result=simulate(context['regular'],signals,cfg,costs,account,context['actions'],payload['start'],payload['end'],cancel)
        return dict(report_type='matched_control_book',role=role,replica=replica,config=cfg.model_dump(),config_id=identity(cfg),
            news_calendar=context.get('news_calendar'),
            core_hash=core_hash(),numerical_contract=core_subject(),dataset_id=payload['dataset_id'],
            dataset_manifest_hash=identity(context['manifest']),dataset_context=freeze_context(context['manifest']),start=payload['start'],end=payload['end'],seed=payload.get('seed',42),
            costs=costs.model_dump(),portfolio=account.model_dump(),metrics=summary(result,account.capital),
            signals=[s.json() for s in signals],trades=result.trades,equity=result.equity,ledger=result.ledger,rejected=result.rejected,
            charts=context['charts'],assumptions=result.assumptions+news_assumptions(context.get('news_calendar'))+['Conditional matched-moment randomization is a research comparison, not a separately executable strategy.'],
            provenance=dict(input_kind=context['manifest']['metadata'].get('input_kind','user_import'),warmup_start=context['warmup']))

    def evaluate_benchmarks(self,dataset_id,costs,portfolio,start,end,seed=42,cancel=None,expected_manifest=None):
        self.borrow_input(dataset_id,costs,start,end)
        manifest,regular,actions,warmup_start=self._evaluation_input(dataset_id,start,end,expected_manifest=expected_manifest)
        comparison=compare_passive(regular,costs,portfolio,actions,start,end,cancel)
        return dict(report_type='passive_benchmarks',dataset_id=dataset_id,dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest),
            core_hash=core_hash(),numerical_contract=core_subject(),start=start,end=end,seed=seed,
            costs=costs.model_dump(),portfolio=portfolio.model_dump(),benchmarks=comparison,
            trades=comparison['buy_hold']['trades'],
            provenance=dict(input_kind=manifest['metadata'].get('input_kind','user_import'),
                source=manifest['metadata'].get('provider','Imported'),warmup_start=warmup_start,
                limitations=manifest['metadata'].get('limitations',[])),
            verification='Passive comparison research output, not proof of strategy superiority or software acceptance.')

    def final(self,study_id):
        require_current_source()
        study=self.guard.study(study_id)
        self.guard.verify_inputs(study)
        self._study_source(study['spec'])
        if study['status']!='screened': raise ResearchError('Screen and freeze nonempty candidates before final evaluation.')
        if study['spec'].get('study_mode')=='portfolio' and study['spec'].get('reserved_final_job_id'):
            raise ResearchError('Portfolio final job is already reserved; resume the original job.')
        if self.store.pending_study_job('final',study_id):
            raise ResearchError('Final evaluation already queued/running.')
        spec=study['spec']
        return self.store.create_job('final',dict(study_id=study_id,core_hash=core_hash(),name=study['name'],
            **({k:spec[k] for k in ['dataset_context','dataset_id','dataset_manifest_hash']} if 'dataset_context' in spec else {}),
            study_mode=spec.get('study_mode','independent'),study_input_hash=study_input_hash(spec),trial_configurations=spec['candidates'],trial_windows={'report':spec['holdout']},
            candidate_hash=spec['candidate_hash']))

    def _study_source(self,spec):
        if spec['core_hash']!=core_hash():raise ResearchError('Frozen study engine changed; register fresh evidence before evaluation.')
        manifest=read_manifest(self.datasets_root,spec['dataset_id'])
        if identity(manifest)!=spec['dataset_manifest_hash']:raise ResearchError('Frozen study dataset manifest changed.')
        if 'dataset_context' in spec:validate_context(spec['dataset_context'],manifest=manifest)
        return manifest

    def _validate_window(self,manifest,start,end,symbols=None):
        q=manifest['quality']
        if start<q['start'] or end>q['end'] or start>end: raise DataError('Evaluation dates are outside the dataset.')
        if manifest['metadata'].get('corporate_action_issues'):
            raise DataError('Corporate-action issues block this dataset. Inspect the audit.')
        bad=[s for s in q['sessions'] if start<=s['session']<=end and not s['complete'] and (symbols is None or s['symbol'] in symbols)]
        if bad: raise DataError('Incomplete regular sessions block this selection; choose a separately audited date/instrument selection.')

    def _evaluation_input(self,dataset_id,start,end,study_id=None,final_job_id=None,expected_manifest=None,symbols=None):
        manifest=read_manifest(self.datasets_root,dataset_id)
        if expected_manifest and identity(manifest)!=expected_manifest: raise DataError('Dataset manifest changed after experiment creation.')
        if symbols is not None and (not isinstance(symbols,list) or not symbols or any(not isinstance(s,str) for s in symbols) or len(set(symbols))!=len(symbols) or set(symbols)-set(manifest['quality']['symbols'])):
            raise DataError('Evaluation instruments must be a distinct nonempty subset of the frozen source.')
        selected=manifest['quality']['symbols'] if symbols is None else sorted(symbols)
        self._validate_window(manifest,start,end,symbols=selected if symbols is not None else None)
        warmup_start=max(manifest['quality']['start'],(date.fromisoformat(start)-timedelta(days=365)).isoformat())
        self.guard.access(selected,warmup_start,end,'final' if final_job_id else 'analysis',study_id,final_job_id)
        def load():
            frame,loaded=load_window(self.datasets_root,dataset_id,warmup_start,end) if symbols is None else load_window(self.datasets_root,dataset_id,warmup_start,end,symbols=selected)
            if identity(loaded)!=identity(manifest):raise DataError('Dataset manifest changed during price loading.')
            quality=audit(frame,warmup_start,end)
            if not quality['eligible']: raise DataError('Warm-up/evaluation data have missing expected minutes.')
            actions=[Action(**a) for a in manifest['actions'] if warmup_start<=a['ex_date']<=end and (symbols is None or a['symbol'] in selected)]
            return prepare(frame,actions),actions
        cache=current_cache(self.root)
        if cache is None:regular,actions=load()
        else:
            key=(dataset_id,identity(manifest),warmup_start,end)+((tuple(selected),) if symbols is not None else ())
            regular,actions=cache.prepared(key,self.datasets_root/dataset_id/'minutes.parquet',manifest['parquet_sha256'],load)
        return manifest,regular,actions,warmup_start

    def spread_signal_probe(self,context,configuration,cancel=None):
        """Primary-instrument signal evidence only; no simulated account or P&L."""
        from .spread import validated_context
        from .sampling import count_discovery_signals
        require_current_source();context=validated_context(context)
        configuration=Strategy(**(configuration.model_dump() if isinstance(configuration,Strategy) else configuration))
        manifest=read_manifest(self.datasets_root,context['dataset_id'])
        if identity(manifest)!=context['dataset_manifest_hash']:raise DataError('Frozen spread dataset manifest changed.')
        primary=context['primary_symbol']
        if primary not in manifest['quality']['symbols']:raise DataError('Primary spread instrument is absent from the frozen dataset.')
        calendar=None;clock=None
        if 'news_calendar_id' in context:
            calendar=self.news.load(context['news_calendar_id'])
            if identity(calendar)!=context['news_calendar_hash']:raise DataError('Frozen spread news calendar hash changed.')
            clock=self.news.clock(calendar['id'],context['start'],context['end'],calendar)
        elif configuration.news!='trade':raise DataError('News-qualified spread probes require a frozen calendar identity and hash.')
        manifest,regular,actions,warmup=self._evaluation_input(context['dataset_id'],context['start'],context['end'],
            expected_manifest=context['dataset_manifest_hash'],symbols=[primary])
        cache=current_cache(self.root);provider=cache.provider(regular) if cache is not None else None
        signals=[s.json() for s in generate_signals(regular,configuration,clock,cancel,chart_provider=provider)]
        count=count_discovery_signals(signals,context['start'],context['end'])
        return dict(report_type='spread_primary_signal_probe',context=context,config=configuration.model_dump(),config_id=identity(configuration),
            dataset_context=freeze_context(manifest),core_hash=core_hash(),numerical_contract=core_subject(),news_calendar=calendar,
            signal_scope=dict(symbols=[primary],start=context['start'],end=context['end']),source_read_scope=dict(symbols=[primary],start=warmup,end=context['end']),
            signals=signals,signal_count=count,excluded_warmup_signals=len(signals)-count,
            scope='Discovery primary signals, with warm-up excluded from qualification. No trades, profit or Sharpe are computed.')

    def evaluate(self,dataset_id,configuration,costs,portfolio,start,end,seed=42,news_dates=None,
                 cancel=None,study_id=None,final_job_id=None,expected_manifest=None,news_calendar=None,symbols=None):
        self.borrow_input(dataset_id,costs,start,end,**({'symbols':symbols} if symbols is not None else {}))
        if news_calendar is not None:news_dates=self.news.clock(news_calendar['id'],start,end,news_calendar)
        manifest,regular,actions,warmup_start=self._evaluation_input(dataset_id,start,end,study_id,final_job_id,expected_manifest,**({'symbols':symbols} if symbols is not None else {}))
        cache=current_cache(self.root);provider=cache.provider(regular) if cache is not None else None
        signals=generate_signals(regular,configuration,news_dates if isinstance(news_dates,NewsClock) else None if news_dates is None else {str(x) for x in news_dates},cancel,chart_provider=provider)
        result=simulate(regular,signals,configuration,costs,portfolio,actions,start,end,cancel,chart_provider=provider)
        stats=summary(result,portfolio.capital)
        stats['pnl_interval']=block_interval(stats['daily_pnl'],seed=seed)
        # Save chart outputs with final results; trade inspection must never reopen sealed data.
        charts={}
        for symbol,group in regular[regular.session.between(start,end)].groupby('symbol'):
            chart=aggregate(group,configuration.timeframe) if provider is None else provider(symbol,configuration.timeframe).loc[lambda bars:bars.session.between(start,end)]
            charts[symbol]=json.loads(chart[['timestamp','available_at','open','high','low','close','volume','factor','complete']].to_json(orient='records',date_format='iso'))
        return dict(config=configuration.model_dump(),config_id=identity(configuration),dataset_id=dataset_id,
            report_type='single_strategy',news_dates=event_dates(news_dates),news_calendar=news_calendar,
            dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest),core_hash=core_hash(),numerical_contract=core_subject(),start=start,end=end,seed=seed,
            costs=costs.model_dump(),portfolio=portfolio.model_dump(),metrics=stats,
            trades=result.trades,equity=result.equity,ledger=result.ledger,rejected=result.rejected,
            signals=result.signals,assumptions=result.assumptions+news_assumptions(news_calendar),charts=charts,
            provenance=dict(input_kind=manifest['metadata'].get('input_kind','user_import'),
                source=manifest['metadata'].get('provider','Imported'),warmup_start=warmup_start,
                limitations=manifest['metadata'].get('limitations',[])),
            verification='Research output; not a product verification receipt or promise of live profitability.',
            **(dict(signal_scope=dict(symbols=sorted(symbols),start=start,end=end),source_read_scope=dict(symbols=sorted(symbols),start=warmup_start,end=end)) if symbols is not None else {}))

    def evaluate_portfolio(self,dataset_id,configurations,costs,portfolio,start,end,seed=42,
                           news_dates=None,cancel=None,expected_manifest=None,news_calendar=None,study_id=None,final_job_id=None):
        self.borrow_input(dataset_id,costs,start,end)
        if news_calendar is not None:news_dates=self.news.clock(news_calendar['id'],start,end,news_calendar)
        if not 1<=len(configurations)<=64 or len({identity(c) for c in configurations})!=len(configurations):
            raise DataError('Choose one to64 unique portfolio configurations.')
        configurations=sorted(configurations,key=identity)
        manifest,regular,actions,warmup_start=self._evaluation_input(dataset_id,start,end,study_id,final_job_id,expected_manifest)
        cache=current_cache(self.root);provider=cache.provider(regular) if cache is not None else None
        signals=[];strategy_map={};signal_counts={}
        for configuration in configurations:
            if cancel and cancel(): raise InterruptedError('Portfolio canceled between strategy calculations.')
            generated=generate_signals(regular,configuration,news_dates if isinstance(news_dates,NewsClock) else None if news_dates is None else {str(x) for x in news_dates},cancel,chart_provider=provider)
            signal_counts[identity(configuration)]=sum(start<=s.available_at.tz_convert('America/New_York').strftime('%Y-%m-%d')<=end for s in generated)
            for signal in generated:
                if signal.id in strategy_map: raise DataError('Portfolio signal identity collision.')
                strategy_map[signal.id]=configuration
            signals.extend(generated)
        result=simulate(regular,signals,configurations[0],costs,portfolio,actions,start,end,cancel,strategy_map=strategy_map,chart_provider=provider)
        stats=summary(result,portfolio.capital);stats['pnl_interval']=block_interval(stats['daily_pnl'],seed=seed)
        chart_sets={};chart_cache={}
        for configuration in configurations:
            if cancel and cancel(): raise InterruptedError('Portfolio canceled before saving chart outputs.')
            if configuration.timeframe not in chart_cache:
                charts={}
                for symbol,group in regular[regular.session.between(start,end)].groupby('symbol'):
                    chart=aggregate(group,configuration.timeframe) if provider is None else provider(symbol,configuration.timeframe).loc[lambda bars:bars.session.between(start,end)]
                    charts[symbol]=json.loads(chart[['timestamp','available_at','open','high','low','close','volume','factor','complete']].to_json(orient='records',date_format='iso'))
                chart_cache[configuration.timeframe]=charts
            chart_sets[identity(configuration)]=chart_cache[configuration.timeframe]
        attribution=[]
        for configuration in configurations:
            cid=identity(configuration);trades=[t for t in result.trades if t['strategy_id']==cid]
            attribution.append(dict(config_id=cid,config=configuration.model_dump(),signals=signal_counts[cid],trades=len(trades),
                closed_trade_net_profit=sum(t['net_pnl'] for t in trades),fees=sum(t['fees'] for t in trades),
                borrow=sum(t['borrow'] for t in trades),distributions=sum(t['distributions'] for t in trades)))
        return dict(report_type='shared_capital_portfolio',config=None,config_id=identity([c.model_dump() for c in configurations]),
            configurations=[dict(config_id=identity(c),config=c.model_dump()) for c in configurations],
            allocation_policy='Each order risks the configured fraction of the one current marked account equity. No per-strategy capital reset or profit summation. Global order priority is defined in RULEBOOK.md.',
            attribution=attribution,dataset_id=dataset_id,dataset_manifest_hash=identity(manifest),dataset_context=freeze_context(manifest),core_hash=core_hash(),
            numerical_contract=core_subject(),start=start,end=end,seed=seed,news_dates=event_dates(news_dates),news_calendar=news_calendar,
            costs=costs.model_dump(),portfolio=portfolio.model_dump(),metrics=stats,trades=result.trades,
            equity=result.equity,ledger=result.ledger,rejected=result.rejected,
            signals=[s.json()|{'config_id':identity(strategy_map[s.id])} for s in signals],
            assumptions=result.assumptions+news_assumptions(news_calendar)+['All strategies share this single account. Attribution is closed-trade P&L from this constrained run, not independent account returns.'],
            charts={},chart_sets=chart_sets,provenance=dict(input_kind=manifest['metadata'].get('input_kind','user_import'),
                source=manifest['metadata'].get('provider','Imported'),warmup_start=warmup_start,limitations=manifest['metadata'].get('limitations',[])),
            verification='Research output; not a product verification receipt or promise of live profitability.')

    def output_path(self,job_id):
        self.store.job_status(job_id) # Only registered identifiers can address result storage.
        return self.root/'data'/'jobs'/job_id/'result.json.gz'

    def result(self,job_id):
        job=self.store.job(job_id)
        if job['status']!='completed': raise StateError('Results are available only after successful completion.')
        path=self.output_path(job_id)
        events=[e for e in self.store.events(job_id) if e['kind']=='result_saved']
        if not events or hashlib.sha256(path.read_bytes()).hexdigest()!=events[-1]['details']['sha256']:
            raise StateError('Saved result integrity check failed.')
        value=compressed_read(path)
        if value.get('job_id')!=job_id or value.get('payload_hash')!=identity(job['payload']): raise StateError('Result identity mismatch.')
        return value

    def repair_result_view(self,job_id):
        original=self.result(job_id)
        self.result_index.build(job_id,original)
        return self.result_index.summary(job_id)

    def report(self,job_id,part=None,window='report'):
        if part is not None:
            try:return self.result_index.part(job_id,part,window)
            except ViewUnavailable:pass # Explicit original report access remains available for legacy/bad views.
        value=self.result(job_id)
        if part is None:
            if 'report' not in value: raise StateError('Choose a configuration part from this job.')
            return value['report']
        row=next((r for r in value.get('rows',[]) if r['part']==part),None)
        if row is None: raise StateError('Unknown configuration part.')
        path=self.root/'data'/'jobs'/job_id/'parts'/(str(part).zfill(6)+'.json.gz')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=row['report_sha256']: raise StateError('Configuration report integrity check failed.')
        saved=compressed_read(path)
        if window not in {'report','discovery','validation'} or window not in saved: raise StateError('Choose a saved report window.')
        if saved.get('config_id')!=row['config_id']: raise StateError('Configuration identity mismatch.')
        return saved[window]
