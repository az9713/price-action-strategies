from .evaluation_cache import evaluation_cache
"""Durable single-job worker. Checkpoints are content-bound, never inferred passes."""
from pathlib import Path
from threading import Event,Thread
import hashlib
import json
import multiprocessing
import os
import sqlite3
import time
import uuid
from .config import Strategy,Costs,Portfolio,identity
from .data import DataError,read_manifest,atomic_json
from .ingest import ingest
from .research import core_hash,core_subject,ResearchError,passes_screen,require_current_source
from .models import SearchStatistics
from .search_statistics import build_search_statistics
from .controls import comparison_statistics
from .behavior import build_tables
from .ablations import paired_comparison
from .signals import Signal
import pandas as pd
from .service import Lab,compressed_read,compressed_write,study_input_hash
from .store import StateError
from .news import NewsDownload,acquire_calendar
from .sensitivity import cost_arms,summarize_accounts,POLICY


class Worker:
    def __init__(self,lab:Lab,shutdown=None):
        self.lab=lab;self.owner=uuid.uuid4().hex;self.shutdown=shutdown or Event()

    def run_once(self):
        job=self.lab.store.claim(self.owner)
        if job is None: return False
        stop=Event();canceled=Event();lost=Event()
        def beat():
            last_success=time.monotonic()
            while not stop.wait(1):
                try:
                    if self.lab.store.heartbeat(job['id'],self.owner,busy_timeout_ms=250): canceled.set()
                    last_success=time.monotonic()
                except StateError:
                    lost.set();return
                except sqlite3.DatabaseError as error:
                    code=getattr(error,'sqlite_errorcode',0)
                    code=code&255 if type(code) is int else 0
                    if code in {sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED} and time.monotonic()-last_success<10:
                        continue
                    # Stop main computation before the15-second lease can be
                    # trusted after a failed renewal; never lose a thread silently.
                    lost.set();return
                except Exception:
                    lost.set();return
        thread=Thread(target=beat,name='job-heartbeat',daemon=True);thread.start()
        def requested():
            try:
                if self.lab.store.cancellation_requested(job['id'],self.owner):canceled.set()
            except StateError:
                lost.set();return True
            return canceled.is_set()
        def cancel():
            if self.shutdown.is_set(): return True
            if stop.is_set() or lost.is_set() or canceled.is_set(): return True
            return requested()
        try:
            with self.lab.store.control_reads(),evaluation_cache(self.lab.root,cancel=cancel):
                outcome=self._execute(job,cancel)
            if job['kind']=='funnel_qualification' and outcome=='waiting':return True
            if cancel(): raise InterruptedError('Job canceled.')
            terminal=self.lab.store.finish(job['id'],self.owner,'completed')
            if job['kind']=='final': self.lab.guard.finish_final(job['payload']['study_id'],job['id'],terminal['status']=='completed')
            elif job['kind']=='funnel_final':
                study=self.lab.guard.study(job['payload']['study_id'])
                if study['spec'].get('final_job_id')==job['id']:self.lab.guard.finish_final(study['id'],job['id'],terminal['status']=='completed')
        except Exception as error:
            if not lost.is_set():
                actual_cancel=requested()
                if lost.is_set():return True
                if self.shutdown.is_set() and not actual_cancel:
                    self.lab.store.release(job['id'],self.owner)
                    return True
                status='canceled' if isinstance(error,InterruptedError) or actual_cancel else 'failed'
                # Provider and numerical errors have deliberate safe messages. Unexpected
                # exceptions expose only a type; no request headers, environment or traceback.
                message=str(error) if isinstance(error,(DataError,StateError,InterruptedError)) else 'Internal '+type(error).__name__+'. See the failed job event; no result was certified.'
                try: self.lab.store.finish(job['id'],self.owner,status,message)
                except StateError: pass
                if job['kind'] in {'final','funnel_final'}:
                    study=self.lab.guard.study(job['payload']['study_id'])
                    if study['spec'].get('final_job_id')==job['id']:
                        self.lab.guard.finish_final(study['id'],job['id'],False)
        finally:
            stop.set();thread.join(timeout=2)
        return True

    def serve(self,stop:Event):
        while not stop.is_set():
            if not self.run_once(): stop.wait(.25)

    def _progress(self,job,fraction,note,checkpoint=None):
        if self.lab.store.heartbeat(job['id'],self.owner,fraction,note,checkpoint):
            raise InterruptedError('Job canceled at a saved checkpoint.')

    def _execute(self,job,cancel):
        payload=job['payload'];job_id=job['id'];kind=job['kind']
        if payload.get('core_hash') and payload['core_hash']!=core_hash():
            raise StateError('Engine changed since job creation. Create a new experiment; final evidence remains consumed if already accessed.')
        self.lab.store.verify_trial_plan(job_id)
        if 'funnel_arm' in payload:
            from .research_funnel_arms import verify_arm
            verify_arm(self.lab,job,cancel)
        if kind=='family_analysis':
            from .research_family_jobs import execute_analysis
            execute_analysis(self,job,cancel)
            return
        if kind=='funnel_qualification':
            from .research_funnel_jobs import execute_qualification
            return execute_qualification(self,job,cancel)
        if kind=='funnel_final':
            from .research_funnel_final import execute_final
            return execute_final(self,job,cancel)
        dataset_context=self.lab.dataset_context_input(payload)
        if kind=='trade_twins':
            from .trade_twin_worker import execute_trade_twins
            execute_trade_twins(self,job,cancel)
            return
        if kind=='spread':
            from .spread_worker import execute_spread
            execute_spread(self,job,cancel)
            return
        if kind=='spread_accounts':
            from .spread_accounts import verify_child
            verify_child(self.lab,job,cancel)
        if kind in {'experiment','search','portfolio','controls','ablation','benchmark','borrow_sensitivity','spread_accounts'}:
            self.lab.borrow_input(payload['dataset_id'],Costs(**payload.get('costs',{})),payload['start'],payload['end'],**({'symbols':payload['evaluation_symbols']} if 'evaluation_symbols' in payload else {}))
        elif kind in {'screen','final'}:
            study=self.lab.guard.study(payload['study_id']);self.lab.guard.verify_inputs(study);spec=study['spec']
            if spec.get('funnel_version'):
                raise ResearchError('Research funnel accounts and final evidence require the complete original funnel workflow.')
            self.lab._study_source(spec)
            if payload.get('study_input_hash')!=study_input_hash(spec):raise StateError('Frozen study inputs changed before borrowing validation.')
            if payload.get('study_mode','independent')!=spec.get('study_mode','independent'):raise StateError('Frozen study selection mode changed.')
            self.lab.news_input(spec,[Strategy(**c) for c in spec['configurations']],spec['discovery']['start'],spec['holdout']['end'])
            self.lab.borrow_input(spec['dataset_id'],Costs(**spec['costs']),spec['discovery']['start'],spec['holdout']['end'])
            if kind=='final':
                with self.lab.store.db() as db:
                    self.lab.guard.verify_candidates(spec,db,study['id'])
                    self.lab.guard.verify_final_reservation(spec,study['id'],job_id,db)
                if payload.get('candidate_hash')!=spec.get('candidate_hash'):raise StateError('Frozen final candidates changed.')
        if kind in {'experiment','search','ablation','portfolio','controls','borrow_sensitivity','spread_accounts'}:
            configs=[Strategy(**c) for c in payload.get('configurations',[payload.get('strategy',{})])]
            self.lab.news_input(payload,configs,payload['start'],payload['end'])
        if kind=='borrow_sensitivity':
            if (payload.get('rate_policy')!=POLICY or payload.get('original_costs_id')!=identity(Costs(**payload['costs'])) or
                payload.get('cost_arms')!=cost_arms(Costs(**payload['costs']),Strategy(**payload['strategy']))):
                raise StateError('Frozen borrowing sensitivity arms or policy do not match original inputs.')
        destination=self.lab.output_path(job_id)
        context=dict(job_id=job_id,kind=kind,payload_hash=identity(payload),core_hash=core_hash())
        if 'funnel_arm' in payload:context['funnel_arm']=payload['funnel_arm']
        if dataset_context is not None:context.update(dataset_context=dataset_context,dataset_id=dataset_context['dataset_id'],dataset_manifest_hash=dataset_context['dataset_manifest_hash'])
        if destination.exists():
            events=[e for e in self.lab.store.events(job_id) if e['kind']=='result_saved']
            digest=hashlib.sha256(destination.read_bytes()).hexdigest()
            if events and events[-1]['details']['sha256']!=digest: raise StateError('Saved result was modified.')
            if events:
                saved=compressed_read(destination)
                if any(saved.get(k)!=v for k,v in context.items()):raise StateError('Saved result does not match this job/source.')
                if kind=='final' and (spec.get('final_job_id')!=job_id or study['status'] not in {'consumed','final_failed','final_complete'}):
                    raise ResearchError('Saved final result does not own the consumed study.')
                if kind=='news_download':
                    calendar=self.lab.news.load(saved.get('news_calendar_id'))
                    if calendar!=saved.get('calendar'):raise StateError('Saved news result differs from its immutable calendar.')
                if kind in {'search','spread_accounts','screen','final'}:
                    from .account_checkpoints import preflight,reuse_checkpoint
                    preflight(self.lab,job_id)
                for row in saved.get('rows',[]):
                    path=destination.parent/'parts'/(str(row['part']).zfill(6)+'.json.gz')
                    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['report_sha256']:
                        raise StateError('Saved result references a missing or modified report part.')
                    part=compressed_read(path)
                    if kind in {'search','spread_accounts','screen','final'}:
                        windows=['discovery','validation'] if kind=='screen' else ['report']
                        expected=dict(config_id=row['config_id'],payload_hash=context['payload_hash'],core_hash=context['core_hash'])
                        reuse_checkpoint(self,job,row['part'],path,path.with_suffix('.sha256.json'),expected,windows,cancel)
                    else:
                        for window in ['report','discovery','validation']:
                            if window in part:self.lab.store.checkpoint_trial(job_id,row['part'],window,self.owner,part[window],row['report_sha256'])
                if not saved.get('rows') and 'report' in saved:
                    if kind=='benchmark':
                        for index,key in enumerate(['cash','buy_hold']):self.lab.store.checkpoint_trial(job_id,index,'report',self.owner,saved['report']['benchmarks'][key],digest)
                    else:self.lab.store.checkpoint_trial(job_id,0,'report',self.owner,saved['report'],digest)
                self.lab.store.bind_trial_result(job_id,self.owner,digest)
                if kind=='screen': self._freeze_screen(payload['study_id'],saved)
                self.lab.result_index.build(job_id,saved,cancel,owner=self.owner)
                if 'funnel_arm' in payload:verify_arm(self.lab,job,cancel)
                return
            # An orphan without a persisted result digest is not committed
            # evidence. Rebuild from verified parts or rerun the computation.
        if cancel(): raise InterruptedError('Job canceled before data access.')
        if payload.get('sampling_failure'):raise DataError(payload['sampling_failure'])
        if kind=='news_download':
            documents={e['details']['url']:e['details']['document'] for e in self.lab.store.events(job_id) if e['kind']=='news_document_saved'}
            def commit_news(url,document):
                with self.lab.store.db() as db:
                    db.execute('BEGIN IMMEDIATE')
                    state=db.execute('SELECT owner,status FROM jobs WHERE id=?',(job_id,)).fetchone()
                    if state is None or state['owner']!=self.owner or state['status']!='running':raise StateError('News document belongs to an inactive worker.')
                    prior=[json.loads(e['details']) for e in db.execute("SELECT details FROM events WHERE entity_id=? AND kind='news_document_saved'",(job_id,))]
                    existing=next((e['document'] for e in prior if e['url']==url),None)
                    if existing is not None and existing!=document:raise StateError('Committed news source cannot change during a job.')
                    if existing is None:self.lab.store.event('news_document_saved',job_id,dict(url=url,document=document),db)
                    db.execute('COMMIT')
            calendar=acquire_calendar(self.lab.root,NewsDownload(**{k:v for k,v in payload.items() if k!='core_hash'}),cancel,
                lambda p,n:self._progress(job,p,n),destination.parent,documents,commit_news)
            result=dict(news_calendar_id=calendar['id'],calendar=calendar)
        elif kind=='download':
            manifest=ingest(self.lab.root,payload['symbols'],payload['start'],payload['end'],cancel,
                lambda p:self._progress(job,0,'Acquired '+str(p['pages'])+' page(s); cached='+str(p['cached'])))
            result={'dataset_id':manifest['id'],'quality':manifest['quality'],
                'corporate_action_issues':manifest['metadata'].get('corporate_action_issues',[])}
        elif kind=='experiment':
            result={'report':self._trial(job,0,'report',lambda:self._evaluate(payload,payload['strategy'],payload['start'],payload['end'],cancel))}
        elif kind=='portfolio':
            result={'report':self._trial(job,0,'report',lambda:self.lab.evaluate_portfolio(payload['dataset_id'],[Strategy(**c) for c in payload['configurations']],
                Costs(**payload['costs']),Portfolio(**payload['portfolio']),payload['start'],payload['end'],
                payload.get('seed',42),payload.get('news_dates'),cancel,payload.get('dataset_manifest_hash'),payload.get('news_calendar')))}
        elif kind=='benchmark':
            for part in [0,1]:self.lab.store.start_trial(job_id,part,'report',self.owner)
            result={'report':self.lab.evaluate_benchmarks(payload['dataset_id'],Costs(**payload['costs']),
                Portfolio(**payload['portfolio']),payload['start'],payload['end'],payload.get('seed',42),
                cancel,payload.get('dataset_manifest_hash'))}
            for part,key in enumerate(['cash','buy_hold']):self.lab.store.computed_trial(job_id,part,'report',self.owner,result['report']['benchmarks'][key])
        elif kind=='controls':
            result=self._controls(job,cancel)
        elif kind=='behavior':
            result=self._behavior(job,cancel)
        elif kind=='ablation':
            result=self._ablation(job,cancel)
        elif kind=='borrow_sensitivity':
            result=self._borrow_sensitivity(job,cancel)
        elif kind=='search':
            result=self._many(job,payload,payload['configurations'],cancel)
            if 'funnel_arm' in payload:verify_arm(self.lab,job,cancel)
            result.update(sampling=payload['sampling'],selection_warning='Discovery results from a search are selected outcomes, not untouched validation.')
            result['search_statistics']=build_search_statistics(result['rows'],SearchStatistics(**payload['statistics']),payload['sampling'],cancel)
            if payload.get('sampling_policy',{}).get('mode','legacy')!='legacy':
                from .sampling import initial_screen
                from .models import SearchSampling
                result['search_screen']=initial_screen(result['rows'],SearchSampling(**payload['sampling_policy']),cancel,strata=payload['sampling']['recipe']['cells'])
            result.update(**{key:payload[key] for key in ['dataset_id','dataset_manifest_hash','start','end','seed','costs','portfolio']})
            result.update(sampling_policy=payload.get('sampling_policy'),news_calendar_id=payload.get('news_calendar_id'),news_calendar=payload.get('news_calendar'))
            if 'funnel_arm' in payload:
                result.update(funnel_arm=payload['funnel_arm'],evaluation_symbols=payload['evaluation_symbols'],
                    selection_warning='Prespecified research arm: '+payload['funnel_arm']['role']+'. This is not final-window evidence.')
        elif kind=='spread_accounts':
            from .spread_accounts import screen,verify_child
            result=self._many(job,payload,payload['configurations'],cancel)
            verify_child(self.lab,job,cancel)
            result.update(spread_parent=payload['spread_parent'],search_statistics=build_search_statistics(result['rows'],SearchStatistics(**payload['statistics']),None,cancel),
                search_screen=screen(result['rows'],payload,cancel),sampling=payload['spread_sampling'],sampling_policy=payload['sampling_policy'],news_calendar_id=payload.get('news_calendar_id'),news_calendar=payload.get('news_calendar'),
                selection_warning='Discovery accounts from the complete signal-qualified spread are selected research outcomes, not untouched validation.')
            result.update(**{key:payload[key] for key in ['dataset_id','dataset_manifest_hash','start','end','seed','costs','portfolio','evaluation_symbols']})
        elif kind=='screen':
            study=self.lab.guard.study(payload['study_id']);spec=study['spec']
            if payload.get('study_input_hash')!=study_input_hash(spec):raise ResearchError('Frozen study inputs changed before screening.')
            if study['status']!='registered': raise ResearchError('Study is no longer eligible for screening.')
            self.lab.news_input(spec,[Strategy(**c) for c in spec['configurations']],spec['discovery']['start'],spec['holdout']['end'])
            mode=spec.get('study_mode','independent')
            units=[spec['configurations']] if mode=='portfolio' else spec['configurations']
            result=self._many(job,spec,units,cancel,screen=True)
            result.update(study_id=study['id'],study_mode=mode,candidates=[r['configurations'] if mode=='portfolio' else r['config'] for r in result['rows'] if r['candidate']],
                gates={'minimum_trades_each_window':spec['minimum_trades'],'minimum_sharpe_each_window':spec['minimum_sharpe'],'positive_net_profit_each_window':True},
                limitations=['These minimum gates do not certify a trading edge. Random controls and search-aware corrections are separate evidence.'])
        elif kind=='final':
            study=self.lab.guard.study(payload['study_id']);spec=study['spec']
            if payload.get('study_input_hash')!=study_input_hash(spec) or payload.get('candidate_hash')!=spec.get('candidate_hash'):
                raise ResearchError('Frozen study inputs/candidates changed before final access.')
            manifest=read_manifest(self.lab.datasets_root,spec['dataset_id'])
            self.lab.news_input(spec,[Strategy(**c) for c in spec['configurations']],spec['discovery']['start'],spec['holdout']['end'])
            self.lab.guard.begin_final(study['id'],job_id,manifest)
            result=self._many(job,spec,spec['candidates'],cancel,final=True)
            result.update(study_id=study['id'],study_mode=spec.get('study_mode','independent'),final_window=spec['holdout'],candidate_hash=spec['candidate_hash'],
                evidence_status='Final dates consumed. Amended strategies require fresh evidence.')
        else: raise StateError('This job type is not implemented yet.')
        if dataset_context is not None and isinstance(result.get('report'),dict):result['report']['dataset_context']=dataset_context
        if cancel(): raise InterruptedError('Job canceled before saving final output.')
        self.lab.store.verify_trial_plan(job_id)
        self._publish_result(job,destination,{**context,**result},cancel)
        if kind=='screen': self._freeze_screen(payload['study_id'],{**context,**result})
        self.lab.result_index.build(job_id,{**context,**result},cancel,owner=self.owner)
        if 'funnel_arm' in payload:verify_arm(self.lab,job,cancel)
        self._progress(job,1,'Results saved and content-bound.')

    def _publish_result(self,job,destination,value,cancel):
        require_current_source()
        # Encode privately; an inactive worker must never replace an original
        # published by a later owner while it was encoding these same inputs.
        candidate=destination.parent/('unpublished-root-'+self.owner+'-'+uuid.uuid4().hex+'.json.gz')
        compressed_write(candidate,value)
        digest=hashlib.sha256(candidate.read_bytes()).hexdigest()
        if cancel():raise InterruptedError('Job stopped before original result publication.')
        with self.lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self.lab.store._trials.owned(db,job['id'],self.owner)
            self.lab.store._trials.verify(job['id'],db)
            require_current_source()
            if cancel() or db.execute('SELECT cancel_requested FROM jobs WHERE id=?',(job['id'],)).fetchone()[0]:
                raise InterruptedError('Job stopped at original result publication.')
            if db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind IN ('result_saved','result_view_saved','job_completed') LIMIT 1",(job['id'],)).fetchone():
                raise StateError('An original result publication already exists; replacement is refused.')
            os.replace(candidate,destination)
            self.lab.store.event('result_saved',job['id'],{'sha256':digest},db)
            self.lab.store._trials.bind_result_owned(db,job['id'],self.owner,digest)
            db.execute('COMMIT')

    def _trial(self,job,part,window,calculate):
        self.lab.store.start_trial(job['id'],part,window,self.owner)
        report=calculate()
        if 'dataset_context' in job['payload']:report['dataset_context']={**job['payload']['dataset_context'],'symbols':list(job['payload']['dataset_context']['symbols'])}
        self.lab.store.computed_trial(job['id'],part,window,self.owner,report)
        return report

    def _ablation(self,job,cancel):
        payload=job['payload'];folder=self.lab.root/'data/jobs'/job['id']/'parts';folder.mkdir(parents=True,exist_ok=True)
        events={e['details']['part']:e['details'] for e in self.lab.store.events(job['id']) if e['kind']=='ablation_part_saved'}
        reports=[];rows=[]
        for part,configuration in enumerate(payload['configurations']):
            if cancel():raise InterruptedError('Ablation canceled between complete accounts.')
            expected=dict(job_id=job['id'],part=part,payload_hash=identity(payload),core_hash=core_hash(),config_id=identity(configuration))
            path=folder/(str(part).zfill(6)+'.json.gz')
            if path.exists() and part in events:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=events[part]['sha256']:raise StateError('Saved ablation account integrity check failed.')
                value=compressed_read(path)
                if any(value.get(k)!=v for k,v in expected.items()):raise StateError('Saved ablation account identity mismatch.')
                report=value['report']
            else:
                report=self._trial(job,part,'report',lambda:self._evaluate(payload,configuration,payload['start'],payload['end'],cancel))
                compressed_write(path,expected|dict(report=report))
                self.lab.store.event('ablation_part_saved',job['id'],dict(part=part,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            digest=hashlib.sha256(path.read_bytes()).hexdigest();self.lab.store.checkpoint_trial(job['id'],part,'report',self.owner,report,digest)
            reports.append(report);rows.append(dict(part=part,config_id=expected['config_id'],report_sha256=digest))
            self._progress(job,(part+1)/(len(payload['configurations'])+1),'Saved '+str(part+1)+'/'+str(len(payload['configurations']))+' independent ablation accounts.',part+1)
        baseline=reports[0];comparisons=[];flat=[]
        for part,report in enumerate(reports[1:],1):
            if cancel():raise InterruptedError('Ablation canceled before paired summaries.')
            seed=int(identity(dict(policy=1,seed=payload['seed'],baseline=baseline['config_id'],alternative=report['config_id'],field=payload['field']))[:8],16)%(2**31)
            value=paired_comparison(baseline,report,payload['field'],seed)|dict(baseline_part=0,alternative_part=part)
            comparisons.append(value);interval=value['paired_pnl_interval']
            flat.append({k:v for k,v in value.items() if k not in {'daily_differences','paired_pnl_interval','limitations'}}|dict(seed=seed,
                interval_low=None if interval is None else interval['low'],interval_high=None if interval is None else interval['high']))
        report=dict(report_type='paired_ablations',field=payload['field'],baseline_config_id=baseline['config_id'],
            news_calendar=baseline.get('news_calendar'),
            dataset_id=payload['dataset_id'],dataset_manifest_hash=payload['dataset_manifest_hash'],core_hash=core_hash(),numerical_contract=core_subject(),
            start=payload['start'],end=payload['end'],seed=payload['seed'],costs=payload['costs'],portfolio=payload['portfolio'],
            arms=[dict(part=i,config_id=r['config_id'],config=r['config'],role='baseline' if i==0 else 'alternative',value=r['config'][payload['field']],metrics=r['metrics']) for i,r in enumerate(reports)],
            comparisons=comparisons,comparison_rows=flat,provenance=baseline['provenance'],
            assumptions=['Exactly one declared public Strategy field differs. Any inferred trigger change is displayed.',
                'Each pair uses the first32 SHA-256 bits of policy/master seed/baseline/alternative/field, modulo2^31, so its saved seed is an exact browser JSON integer.',
                'Each arm is a separate complete account with its own generated signals, fills, sizing and costs. These are not shared-capital components.',
                'Paired daily marked dollar P&L uses the identical complete eligible-session calendar including no-trade days. Trade IDs are not paired.',
                'Intervals are descriptive and do not correct strategy selection or establish future profitability. Every planned arm and execution attempt remains in the trial ledger.'],
            verification='Research comparison under verification, not final software acceptance or a trading-edge certificate.')
        return dict(report=report,rows=rows)

    def _borrow_sensitivity(self,job,cancel):
        payload=job['payload'];configuration=payload['strategy'];folder=self.lab.output_path(job['id']).parent/'parts'
        folder.mkdir(parents=True,exist_ok=True)
        events={e['details']['part']:e['details'] for e in self.lab.store.events(job['id']) if e['kind']=='borrow_sensitivity_part_saved'}
        reports=[];rows=[]
        for arm in payload['cost_arms']:
            if cancel():raise InterruptedError('Borrow sensitivity canceled between complete accounts.')
            part=arm['part'];expected=dict(job_id=job['id'],part=part,payload_hash=identity(payload),core_hash=core_hash(),
                config_id=identity(configuration),costs_id=arm['costs_id'],account_id=arm['account_id'])
            path=folder/(str(part).zfill(6)+'.json.gz')
            if path.exists() and part in events:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=events[part]['sha256']:raise StateError('Saved borrowing sensitivity account was modified.')
                value=compressed_read(path)
                if any(value.get(k)!=v for k,v in expected.items()):raise StateError('Saved borrowing sensitivity account identity mismatch.')
                report=value['report']
                if report['costs']!=arm['costs'] or report['config']!=configuration:raise StateError('Saved borrowing sensitivity account inputs changed.')
            else:
                inputs=payload|dict(costs=arm['costs'])
                def calculate():
                    report=self._evaluate(inputs,configuration,payload['start'],payload['end'],cancel)
                    report['borrow_sensitivity']=dict(policy=POLICY,annual_rate=arm['annual_rate'],costs_id=arm['costs_id'],
                        account_id=arm['account_id'],original_costs_id=payload['original_costs_id'])
                    report['assumptions'].append('Flat borrowing-rate counterfactual: initial and scheduled rates are overridden; original scenario names/notes remain user context. Availability, recalls and other inputs are unchanged.')
                    return report
                report=self._trial(job,part,'report',calculate)
                compressed_write(path,expected|dict(report=report))
                self.lab.store.event('borrow_sensitivity_part_saved',job['id'],dict(part=part,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            digest=hashlib.sha256(path.read_bytes()).hexdigest();self.lab.store.checkpoint_trial(job['id'],part,'report',self.owner,report,digest)
            reports.append(report);rows.append(dict(part=part,config_id=expected['config_id'],costs_id=arm['costs_id'],account_id=arm['account_id'],report_sha256=digest))
            self._progress(job,(part+1)/5,'Saved '+str(part+1)+'/4 complete borrowing-rate accounts.',part+1)
        if cancel():raise InterruptedError('Borrow sensitivity canceled before complete comparison.')
        comparison=summarize_accounts(reports,Costs(**payload['costs']),Strategy(**configuration))
        report=dict(report_type='borrow_sensitivity',rate_policy=POLICY,original_costs=payload['costs'],original_costs_id=payload['original_costs_id'],
            costs=payload['costs'],config=configuration,config_id=identity(configuration),portfolio=payload['portfolio'],
            dataset_id=payload['dataset_id'],dataset_manifest_hash=payload['dataset_manifest_hash'],start=payload['start'],end=payload['end'],seed=payload['seed'],
            news_calendar=payload.get('news_calendar'),news_dates=reports[0].get('news_dates'),core_hash=core_hash(),numerical_contract=core_subject(),
            provenance=reports[0]['provenance'],**comparison)
        return dict(report=report,rows=rows)

    def _controls(self,job,cancel):
        payload=job['payload'];job_id=job['id']
        self._progress(job,0,'Preparing outcome-blind matched control eligibility.')
        context=self.lab.control_context(payload,cancel);plan=context['plan'];plan_hash=identity(plan)
        matched=set(plan['matched_source_ids'])
        books=[('full_real',None,context['signals']),('matched_real',None,[s for s in context['signals'] if s.id in matched])]
        if matched:
            for replica in plan['replicas']:
                signals=[]
                for row in replica['matches']:
                    value=row['signal'].copy()
                    for key in ['available_at','setup_at']:value[key]=pd.Timestamp(value[key])
                    signals.append(Signal(**value))
                books.append(('random_control',replica['replica'],signals))
        else:
            for part in range(2,payload['replicas']+2):self.lab.store.skip_trial(job_id,part,'report',self.owner,'No matched source signals; this requested replica was not generated.')
        destination=self.lab.root/'data'/'jobs'/job_id/'parts';destination.mkdir(parents=True,exist_ok=True)
        events={e['details']['part']:e['details'] for e in self.lab.store.events(job_id) if e['kind']=='control_part_saved'}
        rows=[];summaries=[];daily_dates=None
        for part,(role,replica,signals) in enumerate(books):
            if cancel():raise InterruptedError('Controls canceled between complete accounts.')
            path=destination/(str(part).zfill(6)+'.json.gz')
            expected=dict(job_id=job_id,payload_hash=identity(payload),core_hash=core_hash(),
                          plan_hash=plan_hash,part=part,config_id=identity(context['configuration']))
            if path.exists() and part in events:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=events[part]['sha256']:
                    raise StateError('Saved control account integrity check failed.')
                saved=compressed_read(path)
                if any(saved.get(k)!=v for k,v in expected.items()):raise StateError('Saved control account identity mismatch.')
                report=saved['report']
                if report.get('role')!=role or report.get('replica')!=replica:raise StateError('Saved control account role mismatch.')
            else:
                # A file without a persisted digest is an untrusted orphan, never
                # a completed checkpoint. Recompute it from frozen inputs.
                report=self._trial(job,part,'report',lambda:self.lab.control_book(context,payload,signals,role,replica,cancel))
                compressed_write(path,expected|dict(report=report))
                self.lab.store.event('control_part_saved',job_id,dict(part=part,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),plan_hash=plan_hash))
            dates=[d['date'] for d in report['equity']]
            if daily_dates is None:daily_dates=dates
            elif dates!=daily_dates:raise StateError('Saved control accounts have incompatible daily sessions.')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            self.lab.store.checkpoint_trial(job_id,part,'report',self.owner,report,digest)
            row=dict(part=part,config_id=expected['config_id'],role=role,replica=replica,metrics=report['metrics'])
            rows.append(row|dict(report_sha256=digest));summaries.append(row)
            self._progress(job,(part+1)/len(books),str(part+1)+'/'+str(len(books))+' complete control-comparison accounts saved.',part+1)
        real=summaries[1]['metrics'];controls=[r['metrics'] for r in summaries if r['role']=='random_control']
        report=dict(report_type='matched_random_controls',config=context['configuration'].model_dump(),
            news_calendar=context.get('news_calendar'),
            config_id=identity(context['configuration']),core_hash=core_hash(),numerical_contract=core_subject(),
            dataset_id=payload['dataset_id'],dataset_manifest_hash=identity(context['manifest']),
            start=payload['start'],end=payload['end'],seed=payload.get('seed',42),replicas_requested=payload['replicas'],
            costs=payload['costs'],portfolio=payload['portfolio'],matching=plan,books=summaries,
            comparison=comparison_statistics(real,controls,payload.get('seed',42)),
            provenance=dict(input_kind=context['manifest']['metadata'].get('input_kind','user_import'),
                source=context['manifest']['metadata'].get('provider','Imported'),warmup_start=context['warmup']),
            assumptions=['Retrospective conditional comparison: control candles match symbol, trigger duration, direction, New York30-minute close-time and fixed prior-ATR/close band.',
                'Every replica uses the same maximum-cardinality real subset and distinct non-signal moments. Unmatched events and full-real results remain separate.',
                'Source ATR-relative level/stop/target geometry is transplanted to each candidate close and prior ATR. Future outcomes do not determine eligibility or ranking.',
                'All accounts use the same execution/risk/exit/cost contract and actual shared-capital constraints; signal counts are not executed-trade counts.',
                'No favorable profit sign is required. Paired dollar intervals/exceedance are descriptive and do not correct a wider strategy search.'],
            verification='Research comparison, not final software acceptance or evidence of live profitability.')
        return dict(report=report,rows=rows)

    def _behavior(self,job,cancel):
        payload=job['payload'];job_id=job['id'];context=self.lab.behavior_context(payload)
        destination=self.lab.root/'data/jobs'/job_id/'parts';destination.mkdir(parents=True,exist_ok=True)
        events={e['details']['part']:e['details'] for e in self.lab.store.events(job_id) if e['kind']=='behavior_part_saved'}
        parts=[];rows=[];total_events=0
        for part,timeframe in enumerate(payload['timeframes']):
            if cancel():raise InterruptedError('Behavior study canceled between charts.')
            self._progress(job,part/(len(payload['timeframes'])+1),'Measuring '+timeframe+' features and shifted controls.')
            expected=dict(job_id=job_id,payload_hash=identity(payload),core_hash=core_hash(),part=part,
                          config_id=identity(dict(behavior_policy=1,timeframe=timeframe)))
            path=destination/(str(part).zfill(6)+'.json.gz')
            if path.exists() and part in events:
                if hashlib.sha256(path.read_bytes()).hexdigest()!=events[part]['sha256']:raise StateError('Saved behavior chart integrity check failed.')
                saved=compressed_read(path)
                if any(saved.get(k)!=v for k,v in expected.items()):raise StateError('Saved behavior chart identity mismatch.')
                report=saved['report']
            else:
                report=self._trial(job,part,'report',lambda:self.lab.behavior_chart(context,payload,timeframe,cancel))
                compressed_write(path,expected|dict(report=report))
                self.lab.store.event('behavior_part_saved',job_id,dict(part=part,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            self.lab.store.checkpoint_trial(job_id,part,'report',self.owner,report,hashlib.sha256(path.read_bytes()).hexdigest())
            total_events+=sum(len(report[k]) for k in ['touches','moments','moment_pairs','moment_assessments','gap_fills'])
            if total_events>500000:raise DataError('Behavior study exceeds500000 measurement records; reduce charts or the date window.')
            parts.append(report);rows.append(dict(part=part,timeframe=timeframe,config_id=expected['config_id'],report_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
            self._progress(job,(part+1)/(len(payload['timeframes'])+1),'Completed '+timeframe+' chart and saved its measurement records.',part+1)
        self._progress(job,len(parts)/(len(parts)+1),'Computing whole-session uncertainty and descriptive tables.')
        tables,split=build_tables(parts,payload['start'],payload['end'],payload.get('seed',42),cancel)
        report=dict(report_type='price_behavior',core_hash=core_hash(),numerical_contract=core_subject(),
            dataset_id=payload['dataset_id'],dataset_manifest_hash=identity(context['manifest']),start=payload['start'],end=payload['end'],
            settings={k:payload[k] for k in ['timeframes','shift_replicas','swing_strength','level_tolerance','touch_horizon','bootstrap_resamples','seed']},
            tables=tables,era_split=split,charts=[dict(part=r['part'],timeframe=r['timeframe']) for r in rows],
            counts=dict(features=sum(len(p['features']) for p in parts),unshiftable_features=sum(len(p['unshiftable']) for p in parts),
                real_touches=sum(t['group']=='real' for p in parts for t in p['touches']),
                control_touches=sum(t['group']=='control' for p in parts for t in p['touches']),
                censored_touches=sum(t['outcome']=='censored' for p in parts for t in p['touches']),
                real_moments=sum(len(p['moments']) for p in parts),matched_moment_measurements=sum(len(p['moment_pairs']) for p in parts),
                censored_forward_measures=sum(a['status']=='censored' for p in parts for a in p['moment_assessments']),
                unmatched_forward_measures=sum(a['status']=='unmatched' for p in parts for a in p['moment_assessments'])),
            provenance=dict(input_kind=context['manifest']['metadata'].get('input_kind','user_import'),
                source=context['manifest']['metadata'].get('provider','Imported'),warmup_start=context['warmup']),
            assumptions=['Price behavior measurements are not trades, account returns or evidence of profitable execution.',
                'Features become available at their confirming close. Favorable excursion on the touch candle is excluded; close-through at that close is an immediate observed break.',
                'Primary touch outcomes require all50 future completed bars. Edge observations are censored even if a partial path resolved early; unresolved means a full undecided horizon.',
                'Random stand-ins shift1–3 birth ATR and avoid known real intervals by0.5 birth ATR. Own visits and invalidation are measured; real touch times are never copied.',
                'Only features with all requested birth-time shifts enter matched rate summaries. Full real observations and unshiftable reasons remain saved.',
                'Forward moves use10/20/50 bars, known candidate ATR and matched random moments with full horizon eligibility. Counts and samples can differ by horizon.',
                'Intervals resample whole event sessions2000 times with paired real/control draws; any zero-denominator draw leaves the nominal95% interval undefined.',
                'Events can overlap across sessions and charts. Intervals are descriptive, not search-adjusted global significance or universal true/false verdicts.',
                'Wall/target and shrinking-bounce diagnostics are descriptive excursions, not executable exit rules. Equity instrument/era comparisons do not reproduce NQ/ES findings.'],
            verification='Descriptive research evidence; not final software acceptance or proof of a trading edge.')
        return dict(report=report,rows=rows)

    def _freeze_screen(self,study_id,result):
        study=self.lab.guard.study(study_id)
        report_hash=identity(result)
        if study['status']=='registered': self.lab.guard.screened(study_id,report_hash,result['candidates'])
        elif study['spec'].get('screening_report_hash')!=report_hash:
            raise ResearchError('Frozen screening evidence differs from the saved job result.')

    def _evaluate(self,payload,configuration,start,end,cancel,study_id=None,final_job_id=None):
        if payload.get('study_mode')=='portfolio':
            configs=[Strategy(**c) for c in configuration]
            self.lab.news_input(payload,configs,start,end)
            return self.lab.evaluate_portfolio(payload['dataset_id'],configs,Costs(**payload['costs']),Portfolio(**payload['portfolio']),
                start,end,payload.get('seed',42),payload.get('news_dates'),cancel,payload.get('dataset_manifest_hash'),
                payload.get('news_calendar'),study_id,final_job_id)
        self.lab.news_input(payload,[Strategy(**configuration)],start,end)
        return self.lab.evaluate(payload['dataset_id'],Strategy(**configuration),Costs(**payload['costs']),
            Portfolio(**payload['portfolio']),start,end,payload.get('seed',42),payload.get('news_dates'),
            cancel,study_id,final_job_id,payload.get('dataset_manifest_hash'),payload.get('news_calendar'),**({'symbols':payload['evaluation_symbols']} if 'evaluation_symbols' in payload else {}))

    def _many(self,job,payload,configurations,cancel,screen=False,final=False):
        from .account_checkpoints import preflight,load_checkpoint,publish_checkpoint,reuse_checkpoint
        preflight(self.lab,job['id'])
        rows=[];folder=self.lab.root/'data'/'jobs'/job['id']/'parts';folder.mkdir(parents=True,exist_ok=True)
        payload_hash=identity(job['payload'])
        for index,configuration in enumerate(configurations):
            if cancel(): raise InterruptedError('Job canceled between configurations.')
            part=folder/(str(index).zfill(6)+'.json.gz')
            receipt=part.with_suffix('.sha256.json')
            part_context=dict(config_id=identity(configuration),payload_hash=payload_hash,core_hash=core_hash())
            def evaluate_window(phase,start,end):
                report=self._evaluate(payload,configuration,start,end,cancel,job['payload'].get('study_id'),job['id'] if final else None)
                if 'funnel_arm' in payload:report['research_arm_context']=payload['funnel_arm']
                if screen or final:
                    report['study_context']=dict(study_id=job['payload']['study_id'],study_mode=payload.get('study_mode','independent'),
                        phase=phase,study_input_hash=job['payload']['study_input_hash'],candidate_hash=payload.get('candidate_hash') if final else None,
                        selection_unit_id=identity(configuration))
                return report
            windows=['discovery','validation'] if screen else ['report']
            value,committed,digest=load_checkpoint(self.lab,job['id'],index,part,receipt,part_context,windows)
            if committed!=set(windows):
                if screen:
                    discovery=value['discovery'] if 'discovery' in committed else self._trial(job,index,'discovery',lambda:evaluate_window('discovery',**payload['discovery']))
                    if cancel():raise InterruptedError('Study canceled between discovery and validation accounts.')
                    validation=value['validation'] if 'validation' in committed else self._trial(job,index,'validation',lambda:evaluate_window('validation',**payload['validation']))
                    candidate=passes_screen([r['metrics'] for r in [discovery,validation]],payload['minimum_trades'],payload['minimum_sharpe'])
                    value={**part_context,'discovery':discovery,'validation':validation,'candidate':candidate}
                else:
                    window=payload['holdout'] if final else {'start':payload['start'],'end':payload['end']}
                    report=self._trial(job,index,'report',lambda:evaluate_window('final' if final else 'report',**window))
                    value={**part_context,'report':report}
                digest=publish_checkpoint(self,job,index,part,receipt,value,windows,cancel,compressed_write,atomic_json)
            else:
                value,digest=reuse_checkpoint(self,job,index,part,receipt,part_context,windows,cancel)
            if screen:
                row=dict(config_id=value['config_id'],config=configuration,discovery=value['discovery']['metrics'],
                    validation=value['validation']['metrics'],candidate=value['candidate'])
            else: row=dict(config_id=value['config_id'],config=configuration,metrics=value['report']['metrics'])
            if job['kind'] in {'search','spread_accounts'}:
                from .sampling import count_discovery_signals
                row['signal_count']=count_discovery_signals(value['report']['signals'],value['report']['start'],value['report']['end'])
            if payload.get('study_mode')=='portfolio':row.update(config=None,configurations=configuration,study_mode='portfolio')
            rows.append({**row,'part':index,'report_sha256':digest})
            self._progress(job,(index+1)/len(configurations),f'{index+1} / {len(configurations)} configurations saved.',index+1)
        return {'rows':rows,'count':len(rows),'parts_format':'One compressed report plus integrity hash per configuration.'}


def run_worker(root,stop,ready=None):
    """Spawn-safe entry point; numerical work lives outside the HTTP process."""
    import signal
    previous_sigint=signal.signal(signal.SIGINT,signal.SIG_IGN)
    parent=multiprocessing.parent_process();finished=Event()
    def watch_parent():
        while not finished.wait(.5):
            if parent is not None and not parent.is_alive(): stop.set();return
    watcher=Thread(target=watch_parent,name='parent-liveness',daemon=True);watcher.start()
    try:
        worker=Worker(Lab(Path(root)),stop)
        if ready is not None: ready.set()
        worker.serve(stop)
    finally:
        finished.set();watcher.join(timeout=1)
        signal.signal(signal.SIGINT,previous_sigint)
