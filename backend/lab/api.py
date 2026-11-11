"""Same-origin loopback HTTP application. Credentials never leave this process."""
from contextlib import asynccontextmanager,nullcontext
from datetime import date
from io import BytesIO,StringIO
from pathlib import Path
from threading import Event,Thread,Lock
import asyncio
import multiprocessing
import os
from urllib.parse import urlsplit
import csv
import hashlib
import ipaddress
import json
import secrets
import pandas as pd
from fastapi import FastAPI,Request,UploadFile,File,Form,Query,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,Response,FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from .config import Strategy,Costs,Portfolio,FAMILIES,TIMEFRAMES,APPLICABILITY,identity,canonical
from .data import Action,DataError,read_manifest,normalize,save_dataset
from .models import Download,Selection,Experiment,Search,SearchStatistics,SearchSampling,SamplingPreview,StrategySave,Study,PortfolioExperiment,BenchmarkExperiment,ControlsExperiment,BehaviorExperiment,AblationExperiment,PresentationExport,BorrowSensitivity
from .provider import credentials,ProviderError
from .research import core_hash,current_core_hash,require_current_source
from .service import Lab
from .store import StateError
from .worker import Worker,run_worker as worker_process_main
from .http_boundary import BoundedBody
from .runtime import StoreLease
from .dataset_context import csv_context,CSV_COLUMNS
from .models import SpreadExperiment,SpreadContinuation
from .spread import SpreadSettings,recipe as spread_recipe
from .presenter import build_deck,render_html,PresentationError
from .news import NewsCalendar,NewsDownload,parse_csv,strict_json,MAX_SOURCE
from .borrow import BorrowScenario

ROOT=Path(__file__).resolve().parents[2]
MAX_UPLOAD=64*1024*1024

def local_authority(authority):
    try:
        parsed=urlsplit('http://'+authority)
        if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment: return False
        if parsed.port is not None and not 1<=parsed.port<=65535: return False
        if parsed.hostname=='localhost': return True
        return ipaddress.ip_address(parsed.hostname or '').is_loopback
    except ValueError: return False

def create_app(root:Path=ROOT,run_worker=True,max_request_bytes=MAX_UPLOAD+1024*1024):
    lab=Lab(root);token=secrets.token_urlsafe(32);import_lock=Lock()
    def public_job(job):return lab.store.job_status(job['id'])
    context=multiprocessing.get_context('spawn')
    stop=context.Event();ready=context.Event();worker=Worker(lab,stop)
    @asynccontextmanager
    async def lifespan(app):
        lease=StoreLease(root) if run_worker else None
        with lease if lease is not None else nullcontext():
            app.state.store_lease=lease
            process=None;started=False
            try:
                if run_worker:
                    stop.clear();ready.clear()
                    process=context.Process(target=worker_process_main,args=(str(root),stop,ready),name='research-worker',daemon=True)
                    process.start();started=True
                app.state.worker_process=process
                yield
            finally:
                stop.set()
                if started:
                    await asyncio.to_thread(process.join,12)
                    if process.is_alive():
                        process.terminate();await asyncio.to_thread(process.join,3)
                    if process.is_alive():raise RuntimeError('Research worker did not exit; runtime cleanup is not verified.')
    app=FastAPI(title='Price Action Research Lab',version='0.1.0',lifespan=lifespan,
        docs_url=None,redoc_url=None,openapi_url=None)
    app.state.lab=lab;app.state.worker=worker;app.state.stop=stop;app.state.worker_ready=ready
    app.add_middleware(BoundedBody,max_bytes=max_request_bytes)

    @app.middleware('http')
    async def boundary(request:Request,call_next):
        host=request.headers.get('host','')
        if not local_authority(host): return JSONResponse({'detail':'Loopback Host required.'},status_code=403)
        peer=request.client.host if request.client else ''
        try: is_local=ipaddress.ip_address(peer).is_loopback
        except ValueError: is_local=False
        if not is_local: return JSONResponse({'detail':'Loopback client required.'},status_code=403)
        if request.headers.get('sec-fetch-site')=='cross-site':
            return JSONResponse({'detail':'Cross-site requests are not allowed.'},status_code=403)
        if request.headers.get('origin'):
            try: supplied=urlsplit(request.headers['origin'])
            except ValueError: supplied=None
            if not supplied or supplied.scheme not in {'http','https'} or supplied.netloc.lower()!=host.lower() or supplied.path or supplied.query or supplied.fragment:
                return JSONResponse({'detail':'Cross-origin requests are not allowed.'},status_code=403)
        if request.method not in {'GET','HEAD','OPTIONS'}:
            origin=request.headers.get('origin')
            try: source=urlsplit(origin or '')
            except ValueError: source=None
            if not source or source.scheme not in {'http','https'} or source.netloc.lower()!=host.lower() or source.path or source.query or source.fragment:
                return JSONResponse({'detail':'Matching same-origin header required.'},status_code=403)
            if not secrets.compare_digest(request.headers.get('x-lab-token',''),token):
                return JSONResponse({'detail':'Local session token required.'},status_code=403)
        length=request.headers.get('content-length')
        if length:
            try: excessive=int(length)>max_request_bytes or int(length)<0
            except ValueError: excessive=True
            if excessive: return JSONResponse({'detail':'Request exceeds the 64 MiB upload envelope.'},status_code=413)
        try: response=await call_next(request)
        except Exception:
            return JSONResponse({'detail':'Internal request failure. No result was certified.'},status_code=500)
        response.headers.update({'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer',
            'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"})
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid(request,error):
        return JSONResponse({'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in error.errors()]},status_code=422)
    @app.exception_handler(DataError)
    @app.exception_handler(StateError)
    @app.exception_handler(PresentationError)
    async def domain_error(request,error): return JSONResponse({'detail':str(error)},status_code=409)
    @app.exception_handler(FileNotFoundError)
    async def missing(request,error): return JSONResponse({'detail':'Local dataset or artifact does not exist.'},status_code=404)

    @app.get('/api/session')
    def session(): return {'token':token}
    @app.get('/api/health')
    def health():
        try: credentials(root/'.env');configured=True
        except ProviderError: configured=False
        return {'status':'ok','credentials_configured':configured,'core_hash':core_hash(),'source_current':core_hash()==current_core_hash(),
            'release_status':'Implementation in progress; final conformance not verified.',
            'worker_enabled':run_worker,'worker_alive':bool(app.state.worker_process and app.state.worker_process.is_alive()),'worker_ready':ready.is_set(),
            'server_pid':os.getpid(),'worker_pid':app.state.worker_process.pid if app.state.worker_process else None,
            'store_lease_held':bool(app.state.store_lease and app.state.store_lease.handle is not None),
            'source_video':'https://www.youtube.com/watch?v=z97PnFIPoFg'}
    @app.get('/api/schema')
    def schema(): return {'strategy':Strategy.model_json_schema(),'costs':Costs.model_json_schema(),
        'search_statistics':SearchStatistics.model_json_schema(),
        'sampling_policy':SearchSampling.model_json_schema(),
        'spread_settings':SpreadSettings.model_json_schema(),'spread_run':SpreadExperiment.model_json_schema(),
        'spread_continuation':SpreadContinuation.model_json_schema(),
        'portfolio':Portfolio.model_json_schema(),'portfolio_run':PortfolioExperiment.model_json_schema(),'controls_run':ControlsExperiment.model_json_schema(),'behavior_run':BehaviorExperiment.model_json_schema(),'ablation_run':AblationExperiment.model_json_schema(),'families':FAMILIES,'timeframes':TIMEFRAMES,
        'applicability':{k:sorted(v) for k,v in APPLICABILITY.items()}}
    @app.get('/api/datasets')
    def datasets(): return lab.datasets()
    @app.get('/api/news-calendars')
    def news_calendars():return lab.news.list()
    @app.get('/api/news-calendars/{calendar_id}')
    def news_calendar(calendar_id:str):return lab.news.load(calendar_id)
    @app.post('/api/borrow-scenarios/validate')
    async def validate_borrow_scenario(request:Request,value:BorrowScenario):
        require_current_source();raw=await request.body()
        if len(raw)>MAX_SOURCE:raise DataError('Borrow scenario JSON exceeds two MiB.')
        try:strict_json(raw)
        except DataError:raise DataError('Borrow scenario JSON is malformed or has duplicate fields.') from None
        return dict(scenario=value.model_dump(),scenario_id=identity(value))
    @app.post('/api/news-calendars',status_code=201)
    async def create_news_calendar(request:Request,value:NewsCalendar):
        require_current_source();raw=await request.body()
        if len(raw)>MAX_SOURCE:raise DataError('Calendar JSON exceeds two MiB.')
        strict_json(raw)
        return lab.news.save(value)
    @app.post('/api/news-downloads',status_code=202)
    def download_news(value:NewsDownload):
        require_current_source()
        return public_job(lab.store.create_job('news_download',value.model_dump(mode='json')|dict(core_hash=core_hash())))
    @app.post('/api/news-imports',status_code=201)
    async def import_news(file:UploadFile=File(...),metadata_json:str=Form(...)):
        require_current_source()
        if not (file.filename or '').lower().endswith('.csv'):raise DataError('Choose a UTF-8 calendar CSV file.')
        raw=await file.read(MAX_SOURCE+1)
        try:spec=parse_csv(raw,strict_json(metadata_json))
        except (ValueError,TypeError):raise DataError('Calendar CSV or metadata are invalid; check dates, kinds and knowledge timestamps.') from None
        return lab.news.save(spec,[lab.news.source(raw)],'user_csv')
    @app.get('/api/datasets/{dataset_id}/audit')
    def dataset_audit(dataset_id:str): return lab.dataset_audit(dataset_id)
    @app.get('/api/datasets/{dataset_id}/preview')
    def preview(dataset_id:str,symbol:str,start:date,end:date,timeframe:str='1h',limit:int=Query(1000,ge=1,le=5000)):
        return lab.preview(dataset_id,symbol,str(start),str(end),timeframe,limit)
    @app.post('/api/datasets/{dataset_id}/select')
    def selection(dataset_id:str,value:Selection):
        manifest=lab.select(dataset_id,value.symbols,str(value.start),str(value.end))
        return lab.dataset_audit(manifest['id'])
    @app.post('/api/downloads',status_code=202)
    def download(value:Download): return public_job(lab.store.create_job('download',{**value.model_dump(mode='json'),'core_hash':core_hash()}))

    @app.post('/api/imports',status_code=201)
    async def imported(file:UploadFile=File(...),start:date=Form(...),end:date=Form(...),
        input_kind:str=Form('historical_market_data'),adjustment:str=Form('raw'),timezone_hint:str|None=Form(None),
        actions_json:str=Form('[]'),actions_complete:bool=Form(False)):
        if start>end: raise DataError('Import dates are reversed.')
        if adjustment!='raw': raise DataError('Only raw tradable OHLCV is accepted. Adjusted prices require a separately implemented action contract.')
        if input_kind not in {'historical_market_data','synthetic'}: raise DataError('Declare historical market data or synthetic input.')
        raw=await file.read(MAX_UPLOAD+1)
        if len(raw)>MAX_UPLOAD: return JSONResponse({'detail':'File exceeds 64 MiB; partition the input.'},status_code=413)
        def parse_and_publish():
            with import_lock:
                suffix=Path(file.filename or '').suffix.lower()
                try:
                    if suffix=='.csv': frame=pd.read_csv(BytesIO(raw))
                    elif suffix in {'.parquet','.pq'}:
                        import pyarrow.parquet as pq
                        meta=pq.ParquetFile(BytesIO(raw)).metadata
                        if meta.num_rows>2_000_000 or sum(meta.row_group(i).total_byte_size for i in range(meta.num_row_groups))>512*1024*1024:
                            raise DataError('Parquet expands beyond the import envelope; partition it.')
                        frame=pd.read_parquet(BytesIO(raw))
                    else: raise DataError('Choose a CSV or Parquet file.')
                    frame,_=normalize(frame,timezone_hint)
                    values=json.loads(actions_json)
                    if not isinstance(values,list): raise DataError('Actions must be a JSON list.')
                    actions=[Action(**a) for a in values]
                except DataError: raise
                except Exception: raise DataError('Malformed import or corporate-action metadata.') from None
                symbols=set(frame.symbol)
                if any(a.symbol not in symbols or a.ex_date<str(start) or a.ex_date>str(end) for a in actions):
                    raise DataError('Corporate actions must match imported instruments and dates.')
                local_dates=frame.timestamp.dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d')
                if not local_dates.between(str(start),str(end)).all(): raise DataError('Rows fall outside the declared import dates.')
                issues=[] if actions_complete or input_kind=='synthetic' else ['Importer has not attested that corporate-action metadata are complete.']
                manifest=save_dataset(lab.datasets_root,frame,{'source':'User import','input_kind':input_kind,'file_sha256':hashlib.sha256(raw).hexdigest(),
                    'adjustment':'raw','corporate_action_issues':issues,'actions_attestation':actions_complete,
                    'limitations':['Imported corporate actions are user supplied, not independently corroborated.']},actions,str(start),str(end))
                return manifest
        return await asyncio.to_thread(parse_and_publish)

    @app.get('/api/strategies')
    def strategies(): return lab.store.strategies()
    @app.post('/api/strategies',status_code=201)
    def save_strategy(value:StrategySave):
        sid=lab.store.save_strategy(value.name,value.strategy.model_dump(),value.parent_id)
        return next(s for s in lab.store.strategies() if s['id']==sid)
    @app.post('/api/experiments',status_code=202)
    def experiment(value:Experiment): return public_job(lab.create_experiment(value))
    @app.post('/api/searches',status_code=202)
    def search(value:Search): return public_job(lab.create_experiment(value))
    @app.post('/api/spreads/preview')
    def spread_preview(value:SpreadSettings):
        return dict(settings=value.model_dump(),selected_target=len(value.families)*value.per_family,planned_batches=len(value.families)*value.max_batches_per_family,
            planned_proposals=len(value.families)*value.max_batches_per_family*value.batch_size,requires_signal_data=True,
            source_video='https://www.youtube.com/watch?v=z97PnFIPoFg',recipe=spread_recipe(),scope='Data-free work preview; full default resource use and completion time remain unmeasured. Qualification and P&L are separate phases.')
    @app.post('/api/spreads',status_code=202)
    def spread_experiment(value:SpreadExperiment):return public_job(lab.create_spread(value))
    @app.post('/api/spreads/{job_id}/accounts',status_code=202)
    def spread_accounts(job_id:str,value:SpreadContinuation):return public_job(lab.create_spread_accounts(job_id))
    @app.post('/api/spreads/{job_id}/repair-account-link')
    def repair_spread_account_link(job_id:str,value:SpreadContinuation):return lab.repair_spread_account_link(job_id)
    @app.get('/api/spreads/{job_id}')
    def spread_status(job_id:str):return lab.spread_status(job_id)
    @app.get('/api/spreads/{job_id}/events')
    def spread_events(job_id:str,after:int=Query(0,ge=0),limit:int=Query(20,ge=1,le=20)):return lab.spread_events(job_id,after,limit)
    @app.get('/api/spreads/{job_id}/selections')
    def spread_selections(job_id:str,after:int=Query(0,ge=0),limit:int=Query(50,ge=1,le=100)):return lab.spread_selections(job_id,after,limit)
    @app.get('/api/spreads/{job_id}/result')
    def spread_result(job_id:str):
        value=lab.result(job_id)
        if value.get('kind')!='spread':raise StateError('Choose a saved spread qualification result.')
        return Response(canonical(value),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{job_id}-spread-selection.json"'})
    @app.post('/api/searches/preview')
    def sampling_preview(value:SamplingPreview):
        require_current_source()
        from .sampling import preview_recipe
        return preview_recipe(value.families,value.timeframes,value.include_news)
    @app.post('/api/portfolios',status_code=202)
    def portfolio_experiment(value:PortfolioExperiment): return public_job(lab.create_portfolio(value))
    @app.post('/api/benchmarks',status_code=202)
    def passive_benchmarks(value:BenchmarkExperiment): return public_job(lab.create_benchmarks(value))
    @app.post('/api/controls',status_code=202)
    def random_controls(value:ControlsExperiment):return public_job(lab.create_controls(value))
    @app.post('/api/behavior',status_code=202)
    def price_behavior(value:BehaviorExperiment):return public_job(lab.create_behavior(value))
    @app.post('/api/ablations',status_code=202)
    def paired_ablations(value:AblationExperiment):return public_job(lab.create_ablation(value))
    @app.post('/api/borrow-sensitivity',status_code=202)
    def borrowing_sensitivity(value:BorrowSensitivity):return public_job(lab.create_borrow_sensitivity(value))
    @app.get('/api/trial-registry')
    def trial_registry(limit:int=Query(20,ge=1,le=200),offset:int=Query(0,ge=0),job_id:str|None=None):
        if job_id:lab.store.job_status(job_id)
        return lab.store.registry(limit,offset,job_id)
    @app.get('/api/trial-registry/export/{format}')
    def trial_registry_export(format:str,job_id:str):
        lab.store.job_status(job_id)
        if format not in {'json','csv'}:raise HTTPException(status_code=400,detail='Choose json or csv for a complete selected-job trial ledger.')
        return StreamingResponse(lab.store.export_trials(job_id,format),media_type='application/json' if format=='json' else 'text/csv',
            headers={'Content-Disposition':f'attachment; filename="trial-ledger-{job_id}.{format}"'})
    @app.get('/api/jobs')
    def jobs(limit:int=Query(500,ge=1,le=500),offset:int=Query(0,ge=0)): return lab.store.job_statuses(limit,offset)
    @app.get('/api/jobs/{job_id}')
    def job(job_id:str): return lab.store.job_status(job_id)
    @app.post('/api/jobs/{job_id}/cancel')
    def cancel_job(job_id:str): return lab.store.cancel(job_id,public=True)
    @app.post('/api/jobs/{job_id}/resume')
    def resume_job(job_id:str): return lab.store.resume(job_id,public=True)
    @app.get('/api/jobs/{job_id}/inputs')
    def job_inputs(job_id:str):
        return Response(canonical(lab.store.job_inputs(job_id)),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{job_id}-stored-inputs.json"'})
    @app.post('/api/jobs/{job_id}/repair-index')
    def repair_job_index(job_id:str):return lab.store.repair_job_index(job_id)
    @app.get('/api/jobs/{job_id}/events')
    def job_events(job_id:str): lab.store.job_status(job_id);return lab.store.events(job_id)
    @app.get('/api/jobs/{job_id}/result-summary')
    def result_summary(job_id:str):return lab.result_index.summary(job_id)
    @app.get('/api/jobs/{job_id}/result-rows')
    def result_rows(job_id:str,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):return lab.result_index.rows(job_id,limit,offset)
    @app.get('/api/jobs/{job_id}/result-statistics')
    def result_statistics(job_id:str,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):return lab.result_index.auxiliary(job_id,'statistics',limit,offset)
    @app.get('/api/jobs/{job_id}/result-screen')
    def result_screen_page(job_id:str,limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):return lab.result_index.auxiliary(job_id,'screen',limit,offset)
    @app.post('/api/jobs/{job_id}/result-view/repair')
    def result_view_repair(job_id:str):return lab.repair_result_view(job_id)
    @app.get('/api/jobs/{job_id}/result')
    def result(job_id:str): return lab.result(job_id)
    @app.get('/api/jobs/{job_id}/search-statistics/export/{format}')
    def search_statistics_export(job_id:str,format:str):
        if format not in {'json','csv'}:raise StateError('Choose json or csv for saved search statistics.')
        saved=lab.result(job_id);statistics=saved.get('search_statistics')
        if saved.get('kind') not in {'search','spread_accounts'} or not isinstance(statistics,dict) or statistics.get('policy_version')!=1:
            raise StateError('This saved result has no supported search-statistic diagnostic. Original evidence is unchanged.')
        if format=='json':body=canonical(statistics)
        else:
            columns=CSV_COLUMNS+['job_id','dataset_id','core_hash','start','end','dispersion_mode','trial_sharpe_std','raw_configurations','finite_sharpe_accounts','generation_attempts','generation_unique','generation_duplicates','generation_rejected','part','config_id','source_part_sha256','net_profit','observations','daily_sharpe','skewness','raw_kurtosis','effective_trials','score','undefined_reason']
            output=StringIO(newline='');writer=csv.DictWriter(output,fieldnames=columns);writer.writeheader()
            for account in statistics['accounts']:
                for scenario in account['sensitivity']:
                    row=csv_context(saved.get('dataset_context'))|{key:saved[key] for key in ['job_id','dataset_id','core_hash','start','end']}
                    row.update({key:statistics[key] for key in ['trial_sharpe_std','raw_configurations','finite_sharpe_accounts']})
                    row.update(dispersion_mode=statistics['settings']['dispersion_mode'])
                    row.update({'generation_'+key:value for key,value in statistics['raw_generation'].items()})
                    row.update({key:value for key,value in account.items() if key!='sensitivity'});row.update(scenario)
                    writer.writerow(row)
            body=output.getvalue()
        return Response(body,media_type='application/json' if format=='json' else 'text/csv',headers={'Content-Disposition':f'attachment; filename="{job_id}-search-statistics.{format}"'})
    @app.get('/api/jobs/{job_id}/search-screen/export/{format}')
    def search_screen_export(job_id:str,format:str):
        if format not in {'json','csv'}:raise StateError('Choose json or csv for saved discovery gates.')
        saved=lab.result(job_id);screen=saved.get('search_screen')
        if saved.get('kind') not in {'search','spread_accounts'} or not isinstance(screen,dict) or screen.get('policy_version')!=1:
            raise StateError('This saved search has no supported initial discovery gates.')
        if saved.get('sampling_policy')!=screen.get('settings') or 'news_calendar_id' not in saved or 'news_calendar' not in saved:
            raise StateError('This original summary predates complete sampling/news export assumptions. Inspect its original parts and frozen job inputs; create a new search for complete exports.')
        if format=='json':body=canonical(screen)
        else:
            output=StringIO(newline='');columns=CSV_COLUMNS+['job_id','dataset_id','core_hash','start','end','mode','include_news','recipe_hash','news_calendar_id','minimum_signals','minimum_trades','minimum_sharpe','part','config_id','source_part_sha256','family','timeframe','signal_count','trades','net_profit','marked_sharpe','signal_qualified','enough_trades','profitable','sharpe_passed','initial_gates_passed','failures']
            writer=csv.DictWriter(output,fieldnames=columns);writer.writeheader()
            for account in screen['accounts']:
                row=csv_context(saved.get('dataset_context'))|{k:saved[k] for k in ['job_id','dataset_id','core_hash','start','end']}
                row.update({k:screen['settings'][k] for k in ['mode','include_news','minimum_signals','minimum_trades','minimum_sharpe']})
                row.update(recipe_hash=saved['sampling']['recipe_hash'],news_calendar_id=saved['news_calendar_id'])
                row.update(account);row['failures']=';'.join(account['failures']);writer.writerow(row)
            body=output.getvalue()
        return Response(body,media_type='application/json' if format=='json' else 'text/csv',headers={'Content-Disposition':f'attachment; filename="{job_id}-initial-discovery.{format}"'})
    @app.get('/api/jobs/{job_id}/report')
    def report(job_id:str,part:int|None=Query(None,ge=0),window:str='report'): return lab.report(job_id,part,window)
    def presentation_source(job_id,part,window):
        if window not in {'report','discovery','validation'} or (part is None and window!='report'):
            raise StateError('Choose a saved report window and configuration part.')
        if part is None:
            saved=lab.result(job_id);value=saved.get('report',saved)
        else:value=lab.report(job_id,part,window)
        return (job_id+('/part-'+str(part) if part is not None else '')+'/'+window+'.json',canonical(value).encode())
    @app.post('/api/presentations')
    def presentation(value:PresentationExport):
        sources=[presentation_source(s.job_id,s.part,s.window) for s in value.sources]
        deck=build_deck(sources)
        return dict(html=render_html(deck),manifest=deck)
    @app.get('/api/jobs/{job_id}/export/{format}')
    def export(job_id:str,format:str,part:int|None=Query(None,ge=0),window:str='report',table:str|None=None):
        if format in {'html','presentation.json'}:
            if table is not None:raise StateError('The presenter includes all saved table rows; table selection is not supported.')
            deck=build_deck([presentation_source(job_id,part,window)])
            body=render_html(deck) if format=='html' else json.dumps(deck,allow_nan=False)
            return Response(body,media_type='text/html' if format=='html' else 'application/json',
                headers={'Content-Disposition':f'attachment; filename="{job_id}-presentation.{"html" if format=="html" else "json"}"'})
        report=lab.report(job_id,part,window)
        if format=='json': return Response(canonical(report),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{job_id}.json"'})
        if format!='csv': raise StateError('Choose json or csv export.')
        if report.get('report_type')=='matched_random_controls':
            raise HTTPException(status_code=400,detail='Choose an individual control-study account part for trade CSV; the aggregate study has several separate accounts.')
        if report.get('report_type') in {'paired_ablations','borrow_sensitivity'}:
            if table is not None:raise HTTPException(status_code=400,detail='Aggregate comparison CSV uses the complete comparison table without a table selector.')
            rows=report['comparison_rows']
        elif report.get('report_type')=='price_behavior':
            if table not in report['tables']:raise HTTPException(status_code=400,detail='Choose a behavior table for CSV export.')
            rows=report['tables'][table]['rows']
        elif report.get('report_type')=='behavior_chart':
            raise HTTPException(status_code=400,detail='Export a behavior table as CSV or the complete chart records as JSON.')
        else:
            if table is not None:raise HTTPException(status_code=400,detail='Table selection applies only to a behavior study.')
            rows=report['trades']
        provenance=dict(dataset_id=report.get('dataset_id','not_recorded'))|csv_context(report.get('dataset_context'))
        rows=[provenance|row for row in rows]
        buffer=StringIO()
        if rows:
            writer=csv.DictWriter(buffer,fieldnames=list(rows[0]));writer.writeheader()
            def safe(value):
                if isinstance(value,str) and value.lstrip().startswith(('=','+','-','@','\t','\r')): return "'"+value
                return value
            writer.writerows({k:safe(v) for k,v in row.items()} for row in rows)
        else:
            writer=csv.DictWriter(buffer,fieldnames=list(provenance));writer.writeheader()
        return Response(buffer.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{job_id}-trades.csv"'})
    @app.get('/api/studies')
    def studies(limit:int=Query(500,ge=1,le=500),offset:int=Query(0,ge=0)): return lab.store.study_statuses(limit,offset)
    @app.post('/api/studies',status_code=201)
    def study(value:Study): return lab.store.study_status(lab.register_study(value)['id'])
    @app.get('/api/studies/{study_id}')
    def study_status(study_id:str):return lab.store.study_status(study_id)
    @app.get('/api/studies/{study_id}/inputs')
    def study_inputs(study_id:str):
        return Response(canonical(lab.store.study_inputs(study_id)),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="{study_id}-stored-study-inputs.json"'})
    @app.post('/api/studies/{study_id}/repair-index')
    def study_repair(study_id:str):return lab.store.repair_study_index(study_id)
    @app.get('/api/studies/{study_id}/events')
    def study_events(study_id:str): lab.store.study_status(study_id);return lab.store.events(study_id)
    @app.post('/api/studies/{study_id}/screen',status_code=202)
    def screen(study_id:str): return public_job(lab.screen(study_id))
    @app.post('/api/studies/{study_id}/final',status_code=202)
    def final(study_id:str): return public_job(lab.final(study_id))

    dist=root/'frontend'/'dist'
    if (dist/'assets').is_dir(): app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/')
    def index():
        if (dist/'index.html').exists(): return FileResponse(dist/'index.html')
        return Response('Frontend build is pending. The local API is available at /api/health.',media_type='text/plain')
    return app

