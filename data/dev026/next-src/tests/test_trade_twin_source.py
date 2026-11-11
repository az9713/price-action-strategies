"""Original saved-account extraction contracts, authored before implementation."""
from dataclasses import replace
from contextlib import closing
import copy,hashlib,importlib,importlib.util,json
from pathlib import Path
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab import service
from backend.lab.service import Lab
from backend.lab.config import identity
from backend.lab.data import normalize,prepare,save_dataset,Action
from backend.lab.models import Experiment,Search
from backend.lab.worker import Worker
from test_reference_execution import CFG,ZERO,ACCOUNT,sig
from test_spread_probe import owned

def test_original_saved_source_extractor_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_source') is not None,'Original account extraction is not implemented.'

@pytest.fixture
def source_module():return importlib.import_module('backend.lab.trade_twin_source')

@pytest.fixture
def original(tmp_path,monkeypatch):
    lab=Lab(tmp_path);day='2026-11-04';frame=minute_frame(day)
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='D046 source contract',corporate_actions_complete=True))
    regular=prepare(normalize(frame)[0]);signal=sig(regular,at=20)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
    job=lab.create_experiment(Experiment(dataset_id=manifest['id'],start=day,end=day,strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    report=lab.result(job['id'])['report']
    return lab,job,report

def test_report_extraction_preserves_complete_actual_cohort_and_detached_original_bindings(source_module,original):
    lab,job,report=original
    result=source_module.extract_report(report,job['payload'],CFG.model_dump())
    assert len(result['sources'])==len(report['trades'])==1
    row=result['sources'][0];trace=report['entry_traces'][0];trade=report['trades'][0]
    assert row['trade_id']==trade['id'] and row['entry_stop']==trace['entry_stop'] and row['entry_atr']==trace['entry_atr']
    assert row['exit_boundary']=='close' and row['net_profit']==trade['net_pnl']
    assert result['report_hash']==identity(report) and abs(float(result['profit_residual']))<=1e-7
    before=copy.deepcopy(result);report['entry_traces'][0]['quantity']=999
    assert result==before

@pytest.mark.parametrize('fault',['missing_traces','trace_version','extra_trace_field','trace_hash','trace_signal_hash','trace_config','trace_costs','trace_portfolio','trace_ledger','trace_quantity','trace_side','trace_time','trace_atr','trace_factor','trace_stop','trace_target','trace_reference','trace_fee','trace_order','trace_id','duplicate_trace','duplicate_signal','duplicate_trade','extra_entry','missing_entry','entry_price','unknown_exit','trade_profit','metric_profit','wrong_dates','wrong_dataset','wrong_manifest','wrong_config','wrong_costs','wrong_account','wrong_core','wrong_subject'])
def test_report_local_corruptions_cannot_be_rehashed_into_valid_entry_authority(source_module,original,fault):
    _,job,report=original;r=copy.deepcopy(report);t=r['entry_traces'][0]
    if fault=='missing_traces':r.pop('entry_traces')
    elif fault=='trace_version':r['entry_trace_version']=True
    elif fault=='extra_trace_field':t['future_win']=True
    elif fault=='trace_hash':t['trace_sha256']='0'*64
    elif fault.startswith('trace_'):
        fields={'trace_signal_hash':('signal_sha256','0'*64),'trace_config':('config_id','0'*64),'trace_costs':('costs_sha256','0'*64),'trace_portfolio':('portfolio_sha256','0'*64),'trace_ledger':('entry_ledger_sha256','0'*64),'trace_quantity':('quantity',1),'trace_side':('side',-1),'trace_time':('entry_at','2026-11-04T15:00:00+00:00'),'trace_atr':('entry_atr',1.1),'trace_factor':('price_factor',2.),'trace_stop':('entry_stop',97.),'trace_target':('entry_target',103.),'trace_reference':('entry_reference',-1.),'trace_fee':('entry_fee',1.),'trace_order':('entry_order_type','limit'),'trace_id':('trade_id','other')}
        key,value=fields[fault];t[key]=value
    elif fault=='duplicate_trace':r['entry_traces'].append(copy.deepcopy(t))
    elif fault=='duplicate_signal':r['signals'].append(copy.deepcopy(r['signals'][0]))
    elif fault=='duplicate_trade':r['trades'].append(copy.deepcopy(r['trades'][0]))
    elif fault=='extra_entry':r['ledger'].append(next(copy.deepcopy(e) for e in r['ledger'] if e['kind']=='entry'))
    elif fault=='missing_entry':r['ledger']=[e for e in r['ledger'] if e['kind']!='entry']
    elif fault=='entry_price':r['trades'][0]['entry_price']=99.
    elif fault=='unknown_exit':r['trades'][0]['exit_reason']='unknown'
    elif fault=='trade_profit':r['trades'][0]['net_pnl']=True
    elif fault=='metric_profit':r['metrics']['net_profit']+=1.
    elif fault=='wrong_dates':r['end']='2026-11-05'
    elif fault=='wrong_dataset':r['dataset_id']='0'*24
    elif fault=='wrong_manifest':r['dataset_manifest_hash']='0'*64
    elif fault=='wrong_config':r['config']['swing_strength']=3
    elif fault=='wrong_costs':r['costs']['borrow_annual']=.1
    elif fault=='wrong_account':r['portfolio']['capital']=99999.
    elif fault=='wrong_core':r['core_hash']='0'*64
    elif fault=='wrong_subject':r['numerical_contract']={}
    if fault.startswith('trace_') and fault!='trace_hash':t['trace_sha256']=identity({k:v for k,v in t.items() if k!='trace_sha256'})
    with pytest.raises(ValueError):source_module.extract_report(r,job['payload'],CFG.model_dump())

def test_actual_split_account_uses_entry_stop_not_exit_stop(source_module,tmp_path,monkeypatch):
    lab=Lab(tmp_path);first=minute_frame('2026-11-04');second=minute_frame('2026-11-05',close=[50.]);actions=[Action('SPY','2026-11-05','split',2.)]
    frame=pd.concat([first,second],ignore_index=True);manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='split source',corporate_actions_complete=True),actions)
    regular=prepare(normalize(frame)[0],actions);s=sig(regular,at=20)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[s])
    payload=dict(dataset_id=manifest['id'],dataset_manifest_hash=identity(manifest),start='2026-11-04',end='2026-11-05',costs=ZERO.model_dump(),portfolio=ACCOUNT.model_dump())
    r=lab.evaluate(manifest['id'],CFG,ZERO,ACCOUNT,payload['start'],payload['end'])
    result=source_module.extract_report(r,payload,CFG.model_dump())
    assert result['sources'][0]['entry_stop']==98. and r['trades'][0]['stop']==49.


def database_fingerprint(lab):
    with lab.store.db() as db:
        return {name:identity([dict(r) for r in db.execute('SELECT * FROM '+name+' ORDER BY rowid')]) for name in ['jobs','events','trial_plans','trial_attempts','viewed_windows']}


def test_saved_reader_requires_real_original_authority_and_does_not_recompute_or_write(source_module,original,monkeypatch):
    lab,job,report=original
    assert hasattr(source_module,'read_saved_source'), 'Saved original source authority reader is not implemented.'
    def forbidden(*a,**k):raise AssertionError('Source extraction must not compute new signals/accounts or load execution windows.')
    monkeypatch.setattr(service,'generate_signals',forbidden);monkeypatch.setattr(service,'simulate',forbidden);monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    before=database_fingerprint(lab)
    result=source_module.read_saved_source(lab,job['id'])
    assert result['original_saved_store_authority_verified'] and result['job_id']==job['id']
    assert result['report_hash']==identity(report) and result['source_count']==1
    assert source_module.read_saved_source(lab,job['id'])==result
    assert database_fingerprint(lab)==before


@pytest.mark.parametrize('fault',['root_bytes','result_event','frozen_inputs','payload','trial_computation','trial_artifact','attempt_computation','attempt_artifact','missing_attempt','trial_state','job_state','view_missing','manifest_bytes','price_bytes'])
def test_original_storage_guard_faults_refuse_without_new_jobs(source_module,original,fault):
    from backend.lab.store import StateError
    lab,job,_=original;jid=job['id']
    if fault=='root_bytes':
        p=lab.output_path(jid);raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
    elif fault=='price_bytes':
        p=lab.datasets_root/job['payload']['dataset_id']/'minutes.parquet';raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
    elif fault=='manifest_bytes':
        p=lab.datasets_root/job['payload']['dataset_id']/'manifest.json';v=json.loads(p.read_text());v['metadata']['provider']='changed';p.write_text(json.dumps(v))
    else:
        with lab.store.db() as db:
            if fault=='result_event':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(jid,))
            if fault=='frozen_inputs':db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_plan_frozen'",(jid,))
            if fault=='payload':
                p=copy.deepcopy(job['payload']);p['seed']+=1;db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(p),jid))
            if fault=='trial_computation':db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=?",('0'*64,jid))
            if fault=='trial_artifact':db.execute("UPDATE trial_plans SET artifact_sha256=? WHERE job_id=?",('0'*64,jid))
            if fault=='attempt_computation':db.execute("UPDATE trial_attempts SET computed_sha256=? WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)",('0'*64,jid))
            if fault=='attempt_artifact':db.execute("UPDATE trial_attempts SET artifact_sha256=? WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)",('0'*64,jid))
            if fault=='missing_attempt':db.execute("DELETE FROM trial_attempts WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)",(jid,))
            if fault=='trial_state':db.execute("UPDATE trial_plans SET state='computed' WHERE job_id=?",(jid,))
            if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(jid,))
            if fault=='view_missing':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))
    before=database_fingerprint(lab)
    with pytest.raises((StateError,ValueError)):source_module.read_saved_source(lab,jid)
    assert database_fingerprint(lab)==before


@pytest.mark.parametrize('part',[True,-1,1,1.5,'0'])
def test_original_single_account_part_identity_is_strict(source_module,original,part):
    from backend.lab.store import StateError
    with pytest.raises((ValueError,StateError)):source_module.read_saved_source(original[0],original[1]['id'],part)


def test_saved_source_still_obeys_protected_price_guard_and_cancellation(source_module,original,monkeypatch):
    from backend.lab.research import ResearchError
    lab,job,_=original;seen=[]
    def sealed(symbols,start,end,kind,record=True):
        seen.append((symbols,start,end,record));raise ResearchError('Read would expose protected final data.')
    monkeypatch.setattr(lab.guard,'access',sealed)
    with pytest.raises(ResearchError):source_module.read_saved_source(lab,job['id'])
    assert seen and seen[0][-1] is False
    with pytest.raises(InterruptedError):source_module.read_saved_source(lab,job['id'],cancel=lambda:True)


def search_original(original):
    lab,job,_=original;p=job['payload']
    search=lab.create_experiment(Search(dataset_id=p['dataset_id'],start=p['start'],end=p['end'],strategy=CFG,costs=ZERO,portfolio=ACCOUNT,count=2,families=[CFG.family],timeframes=['1m']))
    assert Worker(lab).run_once() and lab.store.job(search['id'])['status']=='completed'
    return lab,search


def test_selected_search_accounts_preserve_each_original_ordinal_and_registry(source_module,original):
    lab,search=search_original(original);before=database_fingerprint(lab)
    for part in [0,1]:
        expected=lab.result_index.part(search['id'],part)
        result=source_module.read_saved_source(lab,search['id'],part)
        assert result['original_saved_store_authority_verified'] and result['report_hash']==identity(expected)
        assert result['authority']['config_id']==identity(search['payload']['configurations'][part]) and result['part']==part
        assert result['source_count']==len(expected['trades'])
    assert database_fingerprint(lab)==before


@pytest.mark.parametrize('fault',['part_bytes','sidecar','sidecar_extra','sidecar_large','sidecar_missing','part_missing'])
def test_selected_search_part_and_sidecar_cannot_replace_originals(source_module,original,fault):
    from backend.lab.store import StateError
    lab,job=search_original(original);path=lab.output_path(job['id']).parent/'parts'/'000000.json.gz';sidecar=path.with_suffix('.sha256.json')
    if fault=='part_bytes':
        raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
    if fault=='sidecar':sidecar.write_text(json.dumps(dict(sha256='0'*64)))
    if fault=='sidecar_extra':
        value=json.loads(sidecar.read_text());value['extra']='not original';sidecar.write_text(json.dumps(value))
    if fault=='sidecar_large':sidecar.write_text(' '*4097)
    if fault=='sidecar_missing':sidecar.unlink()
    if fault=='part_missing':path.unlink()
    before=database_fingerprint(lab)
    with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'],0)
    assert database_fingerprint(lab)==before


def test_rehashed_root_and_derived_view_cannot_replace_the_recorded_computation(source_module,original):
    from backend.lab.service import compressed_write
    from backend.lab.result_index import file_hash
    from backend.lab.store import StateError
    lab,job,_=original;wrapped=lab.result(job['id']);wrapped['report']['trades'][0]['net_pnl']+=100.
    path=lab.output_path(job['id']);compressed_write(path,wrapped)
    with lab.store.db() as db:db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256=file_hash(path))),job['id']))
    lab.result_index.build(job['id'],wrapped)
    with pytest.raises(StateError,match='recorded computation'):source_module.read_saved_source(lab,job['id'])


@pytest.mark.parametrize('fault',['price_bytes','manifest_bytes','manifest_and_price','job_state','result_event'])
def test_late_original_changes_cannot_become_authorized_source(source_module,original,monkeypatch,fault):
    from backend.lab.store import StateError
    lab,job,_=original;extract=source_module.extract_report
    def changed(*args,**kwargs):
        result=extract(*args,**kwargs)
        if fault=='price_bytes':
            p=lab.datasets_root/job['payload']['dataset_id']/'minutes.parquet';raw=bytearray(p.read_bytes());raw[-1]^=1;p.write_bytes(raw)
        elif fault=='manifest_bytes':
            p=lab.datasets_root/job['payload']['dataset_id']/'manifest.json';v=json.loads(p.read_text());v['metadata']['provider']='late change';p.write_text(json.dumps(v))
        elif fault=='manifest_and_price':
            folder=lab.datasets_root/job['payload']['dataset_id'];price=folder/'minutes.parquet'
            raw=bytearray(price.read_bytes());raw[-1]^=1;price.write_bytes(raw)
            p=folder/'manifest.json';v=json.loads(p.read_text());v['parquet_sha256']=hashlib.sha256(raw).hexdigest();p.write_text(json.dumps(v))
        else:
            with lab.store.db() as db:
                if fault=='job_state':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(job['id'],))
                else:db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256='0'*64)),job['id']))
        return result
    monkeypatch.setattr(source_module,'extract_report',changed)
    with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])


def test_actual_selected_spread_account_verifies_original_qualification_without_new_probes(source_module,owned,monkeypatch):
    from test_spread_account_handoff import qualified
    lab,parent,_=qualified(owned);child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once()
    assert lab.store.job(child['id'])['status']=='completed'
    before=database_fingerprint(lab)
    def forbidden(*a,**k):raise AssertionError('Saved source cannot generate another signal/probe/account.')
    monkeypatch.setattr(service,'generate_signals',forbidden);monkeypatch.setattr(service,'simulate',forbidden)
    result=source_module.read_saved_source(lab,child['id'],0)
    assert result['source_count']>0 and all(s['symbol']=='SPY' for s in result['sources'])
    assert result['authority']['kind']=='spread_accounts' and result['original_saved_store_authority_verified']
    assert database_fingerprint(lab)==before


@pytest.mark.parametrize('side,mode',[(1,'swing'),(-1,'swing'),(-1,'next_open'),(1,'empty')])
def test_source_swing_short_and_empty_accounts_retain_original_results(source_module,original,monkeypatch,side,mode):
    lab,job,_=original;payload=job['payload'];regular=prepare(normalize(minute_frame(payload['start']))[0])
    signal=sig(regular,side=side,at=20,target=104. if side==1 else 96.)
    cfg=CFG.model_copy(update={'target':'swing'}) if mode=='swing' else CFG
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[] if mode=='empty' else [signal])
    new=lab.create_experiment(Experiment(dataset_id=payload['dataset_id'],start=payload['start'],end=payload['end'],strategy=cfg,costs=ZERO,portfolio=ACCOUNT));assert Worker(lab).run_once()
    result=source_module.read_saved_source(lab,new['id'])
    assert result['source_count']==(0 if mode=='empty' else 1)
    if result['sources']:assert result['sources'][0]['side']==side


def test_late_protected_scope_and_cancellation_are_rechecked_before_return(source_module,original,monkeypatch):
    from backend.lab.research import ResearchError
    lab,job,_=original;extract=source_module.extract_report;state={'stop':False}
    def changed(*a,**k):
        answer=extract(*a,**k);state['stop']=True;return answer
    monkeypatch.setattr(source_module,'extract_report',changed)
    with pytest.raises(InterruptedError):source_module.read_saved_source(lab,job['id'],cancel=lambda:state['stop'])
    state['stop']=False
    access=lab.guard.access
    def sealed(*a,**k):
        if state['stop']:raise ResearchError('Late protected scope refuses another source read.')
        return access(*a,**k)
    monkeypatch.setattr(lab.guard,'access',sealed)
    with pytest.raises(ResearchError):source_module.read_saved_source(lab,job['id'])


@pytest.mark.parametrize('kind',['single','search'])
def test_missing_original_trial_events_cannot_be_replaced_by_intact_current_rows(source_module,original,kind):
    from backend.lab.store import StateError
    lab,job,_=original
    if kind=='search':lab,job=search_original(original)
    event='trial_computation_started' if kind=='single' else 'trial_checkpoint_saved'
    with lab.store.db() as db:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(job['id'],event))
    before=database_fingerprint(lab)
    with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])
    assert database_fingerprint(lab)==before


def test_actual_owned_retry_retains_old_checkpoint_and_selects_latest_original_attempt(source_module,original,monkeypatch):
    import shutil,hashlib
    from backend.lab.store import StateError
    lab,old,_=original;p=old['payload']
    job=lab.create_experiment(Search(dataset_id=p['dataset_id'],start=p['start'],end=p['end'],strategy=CFG,costs=ZERO,portfolio=ACCOUNT,count=1,families=[CFG.family],timeframes=['1m']))
    worker=Worker(lab);progress=worker._progress
    def interrupted(job,amount,note,checkpoint=None):
        if 'configurations saved.' in note:raise StateError('Owned fault after the first durable checkpoint.')
        return progress(job,amount,note,checkpoint)
    monkeypatch.setattr(worker,'_progress',interrupted)
    assert worker.run_once() and lab.store.job(job['id'])['status']=='failed'
    folder=lab.output_path(job['id']).parent;part=folder/'parts'/'000000.json.gz';sidecar=part.with_suffix('.sha256.json')
    backup=folder/'original-attempt-one';backup.mkdir()
    before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in [part,sidecar]}
    for f in [part,sidecar]:
        assert f.resolve().is_relative_to(folder.resolve());shutil.copyfile(f,backup/f.name);f.unlink()
    lab.store.resume(job['id']);assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    with lab.store.db() as db:
        assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==2
    result=source_module.read_saved_source(lab,job['id'])
    assert result['authority']['attempt_ordinal']==2 and result['original_saved_store_authority_verified']
    assert {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in backup.iterdir()}==before


@pytest.mark.parametrize('fault',['not_report','wrong_kind','context','ledger_none','ledger_row','trades_none','signal_id','missing_signal','missing_exit','signal_clock','fee_negative','quantity_bool','direction_bool','trade_direction_bool','seed_bool','missing_payload','metric_bool','omitted_trade'])
def test_strict_original_report_shape_and_typed_evidence_boundaries(source_module,original,fault):
    _,job,r=original;r=copy.deepcopy(r);payload=copy.deepcopy(job['payload']);trace=r['entry_traces'][0]
    if fault=='not_report':r=[]
    elif fault=='wrong_kind':r['report_type']='matched_control_book'
    elif fault=='context':r['dataset_context']={}
    elif fault=='ledger_none':r['ledger']=None
    elif fault=='ledger_row':r['ledger'].append(None)
    elif fault=='trades_none':r['trades']=None
    elif fault=='signal_id':r['signals'][0]['id']=42
    elif fault=='missing_signal':r['signals']=[]
    elif fault=='missing_exit':r['trades'][0].pop('exit_at')
    elif fault=='signal_clock':
        r['signals'][0]['available_at']='2026-11-04T14:49:00+00:00';trace['signal_sha256']=identity(r['signals'][0])
    elif fault=='fee_negative':trace['entry_fee']=-1.
    elif fault=='quantity_bool':trace['quantity']=True
    elif fault=='direction_bool':trace['side']=True
    elif fault=='trade_direction_bool':r['trades'][0]['side']=True
    elif fault=='seed_bool':r['seed']=True
    elif fault=='missing_payload':payload.pop('start')
    elif fault=='metric_bool':r['metrics']['net_profit']=False
    elif fault=='omitted_trade':r['trades']=[]
    if isinstance(r,dict):trace['trace_sha256']=identity({k:v for k,v in trace.items() if k!='trace_sha256'})
    with pytest.raises(ValueError):source_module.extract_report(r,payload,CFG.model_dump())


@pytest.mark.parametrize('fault',['kind','core','payload','missing_report','unexpected_rows'])
def test_self_rehashed_derived_view_still_cannot_override_original_source(source_module,original,fault):
    import sqlite3
    from backend.lab.result_index import file_hash
    from backend.lab.store import StateError
    lab,job,_=original
    with lab.store.db() as db:
        event=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='result_view_saved' ORDER BY id DESC LIMIT 1",(job['id'],)).fetchone()
    details=json.loads(event['details']);path=lab.output_path(job['id']).parent/details['filename']
    with closing(sqlite3.connect(path)) as cache:
        meta=json.loads(cache.execute('SELECT value FROM header').fetchone()[0])
        if fault=='kind':meta['kind']='portfolio'
        elif fault=='core':meta['core_hash']='0'*64
        elif fault=='payload':meta['payload_hash']='0'*64;details['payload_hash']='0'*64
        elif fault=='missing_report':meta['has_report']=False
        else:
            meta['row_count']=1;details['row_count']=1;cache.execute('INSERT INTO rows VALUES(?,?,?,?)',(0,'{}','0'*64,'0'*64))
        cache.execute('UPDATE header SET value=?',(json.dumps(meta),));cache.commit()
    details['metadata_sha256']=identity(meta);details['sha256']=file_hash(path)
    with lab.store.db() as db:db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(details),event['id']))
    before=database_fingerprint(lab)
    with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])
    assert database_fingerprint(lab)==before


@pytest.mark.parametrize('fault',['wrong_part','duplicate','oversized','future_ordinal'])
def test_original_computation_event_schema_duplicates_and_order_are_not_derived_authority(source_module,original,fault):
    from backend.lab.store import StateError
    lab,job,_=original
    with lab.store.db() as db:
        row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='trial_computation_started'",(job['id'],)).fetchone();v=json.loads(row['details'])
        if fault=='duplicate':lab.store.event('trial_computation_started',job['id'],v,db)
        else:
            if fault=='wrong_part':v['part']=1
            if fault=='oversized':v['extra']='x'*4096
            if fault=='future_ordinal':v['attempt']+=1
            db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(v),row['id']))
    with pytest.raises(StateError):source_module.read_saved_source(lab,job['id'])


@pytest.mark.parametrize('fault',['kind','posthoc','rehash_old_core','no_attempt_counter','attempt_state','duplicate_result'])
def test_original_registration_kind_source_and_terminal_record_boundaries(source_module,original,fault):
    from backend.lab.store import StateError
    lab,job,_=original;jid=job['id']
    with lab.store.db() as db:
        if fault=='kind':db.execute("UPDATE jobs SET kind='portfolio' WHERE id=?",(jid,))
        elif fault=='posthoc':db.execute("UPDATE events SET kind='legacy_trial_plan_reconstructed' WHERE entity_id=? AND kind='trial_plan_frozen'",(jid,))
        elif fault=='rehash_old_core':
            p=copy.deepcopy(job['payload']);p['core_hash']='0'*64;db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(p),jid))
            r=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='trial_plan_frozen'",(jid,)).fetchone();v=json.loads(r['details']);v['payload_hash']=identity(p)
            db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(v),r['id']))
        elif fault=='no_attempt_counter':db.execute('UPDATE trial_plans SET attempts=0 WHERE job_id=?',(jid,))
        elif fault=='attempt_state':db.execute("UPDATE trial_attempts SET state='computed' WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)",(jid,))
        else:
            r=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone();lab.store.event('result_saved',jid,json.loads(r[0]),db)
    with pytest.raises(StateError):source_module.read_saved_source(lab,jid)
