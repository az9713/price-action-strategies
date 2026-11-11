"""Strict extraction of a complete original account's immutable entry evidence.

extract_report checks report-local consistency without granting store authority.
read_saved_source additionally verifies original input/result/part/trial records
and source-date guards. Consumers must repeat verification before later work.
"""
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
import math
import json
import re
from datetime import date,timedelta
from .store import StateError
from .data import read_manifest
from .research import require_current_source
from .result_index import file_hash
from .config import Strategy,Costs,Portfolio,identity
from .research import core_hash,core_subject
from .trade_twin_amounts import exact_total
from .source_cashflows import validate_audit, POLICY as CASHFLOW_POLICY
from .trade_twins import SourceTrade,MAX_SOURCE_TRADES,_time,_cancel

TRACE_KEYS=frozenset(['version','trade_id','symbol','side','config_id','signal_sha256','costs_sha256','portfolio_sha256',
 'entry_at','atr_available_at','entry_price','entry_reference','reference_kind','entry_order_type','entry_atr','price_factor',
 'entry_stop','entry_target','quantity','entry_fee','entry_ledger_sha256','trace_sha256'])
OPEN_EXITS=frozenset(['gap_stop','gap_target','borrow_recall'])
CLOSE_EXITS=frozenset(['stop','target','close_stop','structure','session_close','timeout','end_of_window'])


from contextlib import nullcontext

def _number(value,positive=False):
    if type(value) not in (int,float) or not math.isfinite(value) or (positive and value<=0):
        raise ValueError('Original account has a nonfinite, boolean or invalid numeric value.')
    return Decimal(str(value))


def _index(rows,key,label):
    if not isinstance(rows,list) or any(not isinstance(row,dict) or not isinstance(row.get(key),str) for row in rows):
        raise ValueError('Original '+label+' must have explicit string identities.')
    answer={row[key]:row for row in rows}
    if len(answer)!=len(rows):
        raise ValueError('Duplicate original '+label+' identity.')
    return answer


def _rounded(value,step,up):
    return float((value/step).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*step)


def extract_report(report,payload,configuration,cancel=None):
    """Validate complete local evidence; returned dictionaries are detached copies."""
    _cancel(cancel)
    try:
        if not isinstance(report,dict) or report.get('report_type')!='single_strategy':
            raise ValueError('Trade twins require an independent single-version strategy account.')
        cfg=Strategy(**configuration);costs=Costs(**payload['costs']);account=Portfolio(**payload['portfolio'])
        cid=identity(cfg)
        if (report.get('core_hash')!=core_hash() or report.get('numerical_contract')!=core_subject() or
            report.get('config')!=cfg.model_dump() or report.get('config_id')!=cid or
            report.get('costs')!=costs.model_dump() or report.get('portfolio')!=account.model_dump()):
            raise ValueError('Original account differs from the frozen rule, costs, account or numerical source.')
        if any(report.get(key)!=payload[key] for key in ['dataset_id','dataset_manifest_hash','start','end']):
            raise ValueError('Original account data identity or date scope differs.')
        if type(report.get('seed')) is not int or report.get('seed')!=payload.get('seed',42):
            raise ValueError('Original account seed differs.')
        if 'dataset_context' in payload and report.get('dataset_context')!=payload['dataset_context']:
            raise ValueError('Original account data context differs.')
        if type(report.get('entry_trace_version')) is not int or report['entry_trace_version']!=1:
            raise ValueError('Original entry traces are unavailable; create a new explicitly identified account.')
        traces=_index(report.get('entry_traces'),'trade_id','entry trace')
        trades=_index(report.get('trades'),'id','executed trade')
        signals=_index(report.get('signals'),'id','signal')
        ledger=report.get('ledger')
        if not isinstance(ledger,list) or any(not isinstance(row,dict) for row in ledger):
            raise ValueError('Original account ledger is missing or malformed.')
        entries=_index([row for row in ledger if row.get('kind')=='entry'],'trade_id','entry ledger')
        if set(trades)!=set(traces) or set(trades)!=set(entries) or len(trades)>MAX_SOURCE_TRADES:
            raise ValueError('Every original executed trade requires exactly one entry trace and entry ledger; no subset is accepted.')
        audited=validate_audit(report.get('cashflow_audit'),report['trades'],report['entry_traces'],report['costs'],report['dataset_manifest_hash'])
        output=[];profits=[]
        for tid,trade in sorted(trades.items()):
            _cancel(cancel)
            trace=traces[tid];entry=entries[tid];signal=signals.get(tid)
            if (set(trace)!=TRACE_KEYS or type(trace['version']) is not int or trace['version']!=1 or
                trace['trace_sha256']!=identity({k:v for k,v in trace.items() if k!='trace_sha256'})):
                raise ValueError('Original entry trace schema or digest differs.')
            if signal is None or trace['signal_sha256']!=identity(signal):
                raise ValueError('Original entry signal binding differs.')
            if trace['config_id']!=cid or trace['costs_sha256']!=identity(report['costs']) or trace['portfolio_sha256']!=identity(report['portfolio']):
                raise ValueError('Original entry assumptions differ.')
            if trace['entry_ledger_sha256']!=identity(entry):
                raise ValueError('Original entry ledger binding differs.')
            if trace['entry_order_type']!=cfg.entry or trace['reference_kind']!={'next_open':'open','same_close':'close','limit':'limit'}[cfg.entry]:
                raise ValueError('Original entry order role differs.')
            for key in ['entry_price','entry_reference','entry_atr','price_factor','entry_stop','entry_target']:_number(trace[key],True)
            if _number(trace['entry_fee'])<0:
                raise ValueError('Original entry fee is negative.')
            if type(trace['quantity']) is not int or trace['quantity']<=0:
                raise ValueError('Original entry quantity is not whole positive shares.')
            if type(trace['side']) is not int or trace['side'] not in (-1,1):
                raise ValueError('Original direction is not explicit.')
            if type(trade.get('side')) is not int:
                raise ValueError('Original trade direction must be an integer, not a boolean.')
            _number(trade['entry_price'],True)
            if any(trace[key]!=trade[key] for key in ['symbol','side','entry_at','entry_price']):
                raise ValueError('Original trade does not match its immutable entry.')
            if trade['strategy_id']!=cid or trace['quantity']!=_number(trade['entry_quantity'],True):
                raise ValueError('Original trade configuration or entry shares differ.')
            if any(entry[key]!=trace[field] for key,field in [('symbol','symbol'),('quantity','quantity'),('price','entry_price'),('fee','entry_fee'),('timestamp','entry_at')]):
                raise ValueError('Original entry ledger fields differ from the trace.')
            if signal['symbol']!=trace['symbol'] or signal['side']!=trace['side'] or _time(signal['available_at'])!=_time(trace['atr_available_at']):
                raise ValueError('Original entry signal clock or direction differs.')
            factor=_number(trace['price_factor'],True);step=Decimal(str(account.tick_size));side=trace['side']
            if trace['entry_atr']!=float(_number(signal['atr'],True)/factor):
                raise ValueError('Original entry ATR is not in raw entry-price units.')
            stop=_rounded(_number(signal['stop'],True)/factor,step,side==-1)
            if cfg.target=='swing':target=_number(signal['target_swing'],True)/factor
            else:target=Decimal(str(trace['entry_price']))+side*(side*(Decimal(str(trace['entry_price']))-Decimal(str(stop))))*Decimal(cfg.target[:-1])
            target=_rounded(target,step,side==1)
            if trace['entry_stop']!=stop or trace['entry_target']!=target:
                raise ValueError('Original entry stop/target differs from known signal geometry.')
            why=trade['exit_reason']
            if why not in OPEN_EXITS|CLOSE_EXITS:
                raise ValueError('Unknown original exit boundary; no holding-time interpretation was guessed.')
            _number(trade['net_pnl']);profits.append(Decimal(str(trade['net_pnl'])))
            source=SourceTrade(trade_id=tid,symbol=trace['symbol'],side=side,entry_at=trace['entry_at'],exit_at=trade['exit_at'],
                exit_boundary='open' if why in OPEN_EXITS else 'close',entry_price=trace['entry_price'],entry_atr=trace['entry_atr'],
                atr_available_at=trace['atr_available_at'],entry_stop=stop,entry_target=target,quantity=trace['quantity'],net_profit=trade['net_pnl'],net_profit_exact=audited[tid])
            output.append(source.model_dump(exclude_none=True))
        closed=exact_total(profits)
        marked=_number(report['metrics']['net_profit']);residual=closed-marked
        if abs(residual)>Decimal('0.0000001'):
            raise ValueError('Complete original closed-trade profit does not reconcile with the account result.')
        return dict(sources=output,source_count=len(output),report_hash=identity(report),config_id=cid,
            source_profit=str(exact_total(audited.values())),reported_source_profit=str(closed),
            cashflow_policy=CASHFLOW_POLICY,cashflow_audit_hash=report['cashflow_audit']['audit_sha256'],
            cashflow_precision_difference=report['cashflow_audit']['difference'],
            marked_account_profit=str(marked),profit_residual=str(residual),
            local_consistency_verified=True,original_saved_store_authority_verified=False)
    except (KeyError,TypeError,OverflowError) as error:
        raise ValueError('Original account/entry evidence is missing or malformed; no source cohort was inferred.') from error


def _original_trial_event(db,jid,kind,trial_id,expected,after_id=0):
    rows=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind=? AND id>? AND CASE WHEN json_valid(details) THEN json_extract(details,'$.trial_id') END=? ORDER BY id",(jid,kind,after_id,trial_id))
    matches=[]
    for row in rows:
        raw=row['details']
        if len(raw.encode('utf-8'))>4096:
            raise StateError('Original trial event exceeds its fixed metadata bound.')
        value=json.loads(raw)
        if kind=='trial_computation_started':
            ordinal=value.get('attempt')
            if type(ordinal) is not int or ordinal<1 or ordinal>expected['attempt']:
                raise StateError('Original attempt history contradicts the current computation.')
            if ordinal<expected['attempt']:continue
        if value!=expected:
            raise StateError('Original trial event differs from its recorded occurrence.')
        matches.append(row['id'])
        if len(matches)>1:
            raise StateError('Duplicate original trial event for the current attempt.')
    if len(matches)!=1:
        raise StateError('Exactly one intact original trial event is required.')
    return matches[0]

def _saved_state(lab,jid,part,db=None):
    """Snapshot original input/plan/result and both selected trial records."""
    owned=db is None
    with lab.store.db() if owned else nullcontext(db) as db:
        if owned:db.execute('BEGIN')
        elif not db.in_transaction:raise StateError('Original source verification requires an active transaction.')
        job,digest,provenance=lab.store._input_index.verified_inputs(jid,db)
        if job['status']!='completed' or job['kind'] not in {'experiment','search','spread_accounts'} or provenance!='prespecified':
            raise StateError('Use a completed original independent strategy/search account, not a legacy or final-test report.')
        lab.store._trials.verify(jid,db)
        payload=job['payload']
        if payload.get('core_hash')!=core_hash():
            raise StateError('Original account uses another numerical source; create a new explicitly identified account.')
        configs=[payload['strategy']] if job['kind']=='experiment' else payload['configurations']
        if not isinstance(configs,list) or part>=len(configs):
            raise StateError('Unknown original configuration ordinal.')
        incomplete=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND (window!='report' OR state!='completed')",(jid,)).fetchone()[0]
        if incomplete:
            raise StateError('The full original account plan has incomplete trial evidence.')
        trial=db.execute("SELECT * FROM trial_plans WHERE job_id=? AND part=? AND window='report'",(jid,part)).fetchone()
        if trial is None or trial['attempts']<1:
            raise StateError('Original trial computation is missing.')
        attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=? AND ordinal=?',(trial['id'],trial['attempts'])).fetchone()
        if attempt is None or attempt['state']!='checkpointed':
            raise StateError('Original computed attempt is missing or incomplete.')
        started_event_id=_original_trial_event(db,jid,'trial_computation_started',trial['id'],dict(trial_id=trial['id'],part=part,window='report',attempt=trial['attempts']))
        checkpoint_event_id=None
        if job['kind']!='experiment':
            checkpoint_event_id=_original_trial_event(db,jid,'trial_checkpoint_saved',trial['id'],dict(trial_id=trial['id'],part=part,window='report',sha256=trial['artifact_sha256']),after_id=started_event_id)
        result_events=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id LIMIT 2",(jid,)).fetchall()
        if len(result_events)!=1:
            raise StateError('Exactly one original committed result event is required.')
        result_digest=json.loads(result_events[0]['details'])['sha256']
        binding=dict(job_id=jid,kind=job['kind'],payload_hash=digest,part=part,config_id=identity(configs[part]),root_sha256=result_digest,
            computation_event_id=started_event_id,checkpoint_event_id=checkpoint_event_id,
            trial_id=trial['id'],computed_sha256=trial['computed_sha256'],artifact_sha256=trial['artifact_sha256'],
            attempt_ordinal=trial['attempts'],attempt_computed_sha256=attempt['computed_sha256'],attempt_artifact_sha256=attempt['artifact_sha256'])
        return job,configs[part],binding


def read_saved_source(lab,jid,part=0,cancel=None):
    """Read existing originals only; no new signals/accounts/jobs or derived repair."""
    _cancel(cancel);require_current_source()
    if not isinstance(jid,str) or re.fullmatch('[a-f0-9]{32}',jid) is None or type(part) is not int or part<0:
        raise StateError('Choose an original job and integer configuration ordinal.')
    try:
        job,configuration,binding=_saved_state(lab,jid,part);payload=job['payload']
        if job['kind']=='spread_accounts':
            from .spread_accounts import verify_child
            verify_child(lab,job,cancel)
        manifest=read_manifest(lab.datasets_root,payload['dataset_id'])
        if identity(manifest)!=payload['dataset_manifest_hash']:
            raise StateError('Original source manifest changed.')
        lab.dataset_context_input(payload)
        symbols=payload['evaluation_symbols'] if job['kind']=='spread_accounts' else manifest['quality']['symbols']
        if not isinstance(symbols,list) or not symbols or len(set(symbols))!=len(symbols) or set(symbols)-set(manifest['quality']['symbols']):
            raise StateError('Original evaluated instruments differ from their source.')
        warmup=max(manifest['quality']['start'],(date.fromisoformat(payload['start'])-timedelta(days=365)).isoformat())
        lab.guard.access(symbols,warmup,payload['end'],'trade_twin_source',record=False)
        _cancel(cancel)
        if file_hash(lab.datasets_root/payload['dataset_id']/'minutes.parquet')!=manifest['parquet_sha256']:
            raise StateError('Original price bytes changed; no twin source was authorized.')
        cfg=Strategy(**configuration)
        lab.borrow_input(payload['dataset_id'],Costs(**payload['costs']),payload['start'],payload['end'],symbols=symbols)
        lab.news_input(payload,[cfg],payload['start'],payload['end'])
        with lab.result_index.snapshot(jid) as (view,meta,original_view):
            if any(meta.get(k)!=v for k,v in [('job_id',jid),('kind',job['kind']),('payload_hash',binding['payload_hash']),('core_hash',core_hash())]):
                raise StateError('Original saved-result metadata differs from the frozen account.')
            if original_view['root_sha256']!=binding['root_sha256']:
                raise StateError('Original root result changed during source verification.')
            if job['kind']=='experiment':
                if meta['row_count']!=0 or not meta['has_report']:
                    raise StateError('Original single account layout differs.')
                wrapped=lab.result(jid)
                if any(wrapped.get(k)!=meta.get(k) for k in ['job_id','kind','payload_hash','core_hash']):
                    raise StateError('Original root identity differs.')
                report=wrapped['report'];artifact=binding['root_sha256']
            else:
                if meta['row_count']!=len(payload['configurations']):
                    raise StateError('The original complete search cohort is missing rows.')
                row=view.execute('SELECT config_id,report_sha256 FROM rows WHERE part=?',(part,)).fetchone()
                if row is None or row['config_id']!=binding['config_id']:
                    raise StateError('Original selected rule identity differs.')
                path=lab.output_path(jid).parent/'parts'/(str(part).zfill(6)+'.json.gz');artifact=file_hash(path)
                sidecar=path.with_suffix('.sha256.json')
                if sidecar.stat().st_size>4096:
                    raise StateError('Original part sidecar is oversized.')
                saved_digest=json.loads(sidecar.read_text(encoding='utf-8'))
                if set(saved_digest)!={'sha256'} or saved_digest['sha256']!=artifact or row['report_sha256']!=artifact:
                    raise StateError('Original account part differs from its saved root and sidecar.')
                from .service import compressed_read
                wrapped=compressed_read(path)
                if wrapped.get('config_id')!=binding['config_id'] or wrapped.get('payload_hash')!=binding['payload_hash'] or wrapped.get('core_hash')!=core_hash():
                    raise StateError('Original account part belongs to different inputs or source.')
                report=wrapped['report']
            if binding['artifact_sha256']!=artifact or binding['attempt_artifact_sha256']!=artifact or binding['computed_sha256']!=identity(report) or binding['attempt_computed_sha256']!=identity(report):
                raise StateError('Original account differs from its recorded computation/attempt artifacts.')
        result=extract_report(report,payload,configuration,cancel)
        if any(s['symbol'] not in symbols for s in result['sources']):
            raise StateError('Original executed cohort contains an unrelated instrument.')
        _cancel(cancel);require_current_source()
        _,_,again=_saved_state(lab,jid,part)
        if again!=binding or file_hash(lab.output_path(jid))!=binding['root_sha256']:
            raise StateError('Original authority changed while extracting the source.')
        if job['kind']!='experiment' and file_hash(path)!=artifact:
            raise StateError('Original selected part changed while extracting the source.')
        current_manifest=read_manifest(lab.datasets_root,payload['dataset_id'])
        if identity(current_manifest)!=payload['dataset_manifest_hash']:
            raise StateError('Original source manifest changed during extraction.')
        lab.guard.access(symbols,warmup,payload['end'],'trade_twin_source',record=False)
        if file_hash(lab.datasets_root/payload['dataset_id']/'minutes.parquet')!=current_manifest['parquet_sha256']:
            raise StateError('Original price bytes changed during extraction.')
        lab.borrow_input(payload['dataset_id'],Costs(**payload['costs']),payload['start'],payload['end'],symbols=symbols)
        lab.news_input(payload,[cfg],payload['start'],payload['end'])
        _cancel(cancel);require_current_source()
        if job['kind']=='spread_accounts':verify_child(lab,job,cancel)
        return result|dict(job_id=jid,part=part,authority=binding,authority_hash=identity(binding),
            original_saved_store_authority_verified=True,assumptions=dict(configuration=configuration,costs=payload['costs'],portfolio=payload['portfolio'],
            dataset_id=payload['dataset_id'],dataset_manifest_hash=payload['dataset_manifest_hash'],start=payload['start'],end=payload['end'],seed=payload['seed']))
    except (StateError,InterruptedError):raise
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
        raise StateError('Original account authority is missing, corrupt or incompatible; no source was authorized.') from error
