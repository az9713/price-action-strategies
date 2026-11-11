"""Input rejection, historical exposure, all-history guards and saved-output faults.

Authored malformed inputs/fault injection are not live-provider or capacity tests.
"""
from pathlib import Path
import hashlib
import json
import pandas as pd
import pytest
from backend.lab import data,service
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import DataError,Action,save_dataset,load_dataset,load_window,normalize
from backend.lab.models import Experiment,Search,Study
from backend.lab.research import ResearchError
from backend.lab.store import StateError
from backend.lab.service import Lab,compressed_read,compressed_write
from backend.lab.worker import Worker
from conftest import minute_frame

@pytest.mark.parametrize('mode',['missing_column','missing_symbol','bad_symbol','mixed_timezone','bad_timestamp','nonnumeric'])
def test_untrusted_import_rejection_has_no_silent_conversion(mode):
    frame=minute_frame().iloc[:2].copy()
    if mode=='missing_column':frame=frame.drop(columns='close')
    if mode=='missing_symbol':frame.loc[0,'symbol']=None
    if mode=='bad_symbol':frame.loc[0,'symbol']='SPY;DROP'
    if mode=='mixed_timezone':frame['timestamp']=['2026-11-05T14:30:00Z','2026-11-05T14:31:00']
    if mode=='bad_timestamp':frame['timestamp']=['not-a-date','2026-11-05T14:31:00Z']
    if mode=='nonnumeric':frame['volume']=['not-a-number','100']
    with pytest.raises(DataError):normalize(frame)

def test_empty_and_oversized_imports_reject_before_copy_or_allocation(monkeypatch):
    with pytest.raises(DataError):normalize(pd.DataFrame())
    class LargeInput(pd.DataFrame):
        def __len__(self):return 15_000_001
        def copy(self,*args,**kwargs):pytest.fail('Oversized import copied before rejection')
    with pytest.raises(DataError,match='15 million'):normalize(LargeInput())

def test_reversed_calendar_and_unknown_chart_reject():
    with pytest.raises(DataError,match='reversed'):data.schedule('2026-11-06','2026-11-05')
    with pytest.raises(DataError,match='Unknown'):data.aggregate(pd.DataFrame(),'2h')

@pytest.mark.parametrize('changes',[dict(kind='merger'),dict(value=0),dict(value=float('inf')),dict(ex_date='invalid'),dict(pay_date='invalid')])
def test_malformed_corporate_action_is_never_accepted(changes):
    with pytest.raises((DataError,ValueError)):Action(**(dict(symbol='SPY',ex_date='2026-11-05',kind='split',value=2)|changes))

def test_failed_atomic_write_preserves_old_document_and_removes_temporary_file(tmp_path,monkeypatch):
    target=tmp_path/'state.json';target.write_text('original',encoding='utf-8')
    def fail(*args,**kwargs):raise OSError('Authored failed replacement')
    monkeypatch.setattr(data.os,'replace',fail)
    with pytest.raises(OSError):data.atomic_json(target,dict(new='not committed'))
    assert target.read_text(encoding='utf-8')=='original' and list(tmp_path.glob('*.tmp'))==[]

@pytest.mark.parametrize('kind',['identity','normalized','window_file'])
def test_distinct_dataset_integrity_layers_refuse_corruption(tmp_path,kind,monkeypatch):
    manifest=save_dataset(tmp_path,minute_frame(),dict(input_kind='synthetic'));path=tmp_path/manifest['id']
    if kind=='identity':
        manifest['id']='0'*24;data.atomic_json(path/'manifest.json',manifest)
        with pytest.raises(DataError,match='identity'):load_dataset(tmp_path,path.name)
    elif kind=='normalized':
        manifest['bars_sha256']='0'*64
        manifest['id']=identity({k:v for k,v in manifest.items() if k not in {'id','parquet_sha256'}})[:24]
        other=tmp_path/manifest['id'];other.mkdir();(other/'minutes.parquet').write_bytes((path/'minutes.parquet').read_bytes());data.atomic_json(other/'manifest.json',manifest)
        with pytest.raises(DataError,match='Normalized'):load_dataset(tmp_path,manifest['id'])
    else:
        target=path/'minutes.parquet';target.write_bytes(target.read_bytes()+b'authored corruption')
        monkeypatch.setattr(data.pd,'read_parquet',lambda *args,**kwargs:pytest.fail('Corrupt file reached parser'))
        with pytest.raises(DataError,match='file hash'):load_window(tmp_path,manifest['id'],'2026-11-05','2026-11-05')

@pytest.mark.parametrize('symbols,start,end',[
    ([],None,None),(['QQQ'],None,None),(['SPY'],'2026-11-04',None),(['SPY'],None,'2026-11-06'),(['SPY'],'2026-11-05','2026-11-04')])
def test_selection_never_expands_parent_dates_or_symbols(tmp_path,symbols,start,end):
    manifest=save_dataset(tmp_path,minute_frame(),dict(input_kind='synthetic'))
    with pytest.raises(DataError):data.select_dataset(tmp_path,manifest['id'],symbols,start,end)

def test_selected_action_history_is_scoped_and_parent_is_immutable(tmp_path):
    frame=pd.concat([minute_frame('2026-11-04'),minute_frame('2026-11-05')],ignore_index=True)
    manifest=save_dataset(tmp_path,frame,dict(input_kind='synthetic'),[Action('SPY','2026-11-04','dividend',1),Action('SPY','2026-11-05','dividend',2)])
    before=(tmp_path/manifest['id']/'manifest.json').read_bytes()
    selected=data.select_dataset(tmp_path,manifest['id'],['SPY'],'2026-11-05','2026-11-05')
    assert selected['actions']==[dict(symbol='SPY',ex_date='2026-11-05',kind='dividend',value=2,pay_date=None)]
    assert selected['metadata']['selection']['parent_id']==manifest['id']
    assert (tmp_path/manifest['id']/'manifest.json').read_bytes()==before

@pytest.fixture
def lab_data(tmp_path):
    lab=Lab(tmp_path);frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04']],ignore_index=True)
    m=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',source='Authored boundary prices'))
    return lab,m

def study(m):
    return Study(name='All-history guard',dataset_id=m['id'],configurations=[Strategy()],minimum_trades=1,
        discovery=dict(start='2026-11-02',end='2026-11-02'),validation=dict(start='2026-11-03',end='2026-11-03'),holdout=dict(start='2026-11-04',end='2026-11-04'))

@pytest.mark.parametrize('families,frames',[([],['1m']),(['unknown'],['1m']),(['breakout'],[]),(['breakout'],['2h'])])
def test_unsupported_sampler_strata_reject_before_rng_or_prices(monkeypatch,families,frames):
    monkeypatch.setattr(service.np.random,'default_rng',lambda *args,**kwargs:pytest.fail('Invalid sample reached RNG'))
    request=Search(dataset_id='a'*24,start='2026-11-02',end='2026-11-03',count=1,families=families,timeframes=frames)
    with pytest.raises(DataError):service.sample_configurations(request)

def test_prior_exposure_migration_is_complete_idempotent_and_does_not_invent_failed_probe_reads(tmp_path):
    saved=save_dataset(tmp_path/'data/datasets',minute_frame('2026-11-04'),dict(input_kind='synthetic'))
    probe=tmp_path/'research/alpaca_probe/report.json';probe.parent.mkdir(parents=True)
    probe.write_text(json.dumps(dict(requests=[
        dict(http_status=200,parameters=dict(symbols='SPY,QQQ',start='2026-10-01T00:00:00Z',end='2026-10-02T23:59:00Z')),
        dict(http_status=403,parameters=dict(symbols='SPY',start='2026-10-20',end='2026-10-21')),
        dict(http_status=200,parameters=dict(symbols='SPY',end='2026-10-21')),
        dict(http_status=200,parameters={})])),encoding='utf-8')
    runs=tmp_path/'data/cli-runs';runs.mkdir();(runs/'old.json').write_text(json.dumps(dict(dataset_id=saved['id'])),encoding='utf-8')
    lab=Lab(tmp_path)
    with lab.store.db() as db:rows=[dict(r) for r in db.execute('SELECT symbol,start,end,kind FROM viewed_windows ORDER BY symbol,start')]
    assert rows==[dict(symbol='QQQ',start='2026-10-01',end='2026-10-02',kind='prior_provider_probe'),dict(symbol='SPY',start='2026-10-01',end='2026-10-02',kind='prior_provider_probe'),dict(symbol='SPY',start='2026-11-04',end='2026-11-04',kind='prior_prototype_analysis')]
    assert lab.store.events('system')[-1]['details']['windows']==2
    again=Lab(tmp_path)
    with again.store.db() as db:assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==3

def test_inventory_flags_bad_manifest_and_ignores_nondirectory(lab_data):
    lab,m=lab_data;(lab.datasets_root/'not-a-dataset.txt').write_text('not a dataset',encoding='utf-8');(lab.datasets_root/'bad').mkdir()
    rows=lab.datasets();assert len(rows)==2
    assert next(r for r in rows if r['id']==m['id'])['eligible']
    assert 'error' in next(r for r in rows if r['id']=='bad')

def test_weekend_preview_is_empty_without_filling_prices(tmp_path):
    lab=Lab(tmp_path);m=save_dataset(lab.datasets_root,pd.concat([minute_frame('2026-11-06'),minute_frame('2026-11-09')]),dict(input_kind='synthetic'))
    assert lab.preview(m['id'],'SPY','2026-11-07','2026-11-08')==[]

def test_incomplete_warmup_blocks_an_otherwise_complete_evaluation_day(tmp_path):
    lab=Lab(tmp_path);frame=pd.concat([minute_frame('2026-11-02').iloc[1:],minute_frame('2026-11-03')],ignore_index=True)
    m=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic'))
    with pytest.raises(DataError,match='Warm-up'):lab._evaluation_input(m['id'],'2026-11-03','2026-11-03')

def test_unresolved_actions_block_before_evaluation(lab_data):
    lab,m=lab_data;m['metadata']['corporate_action_issues']=['Authored unresolved action']
    with pytest.raises(DataError,match='Corporate-action'):lab._validate_window(m,'2026-11-02','2026-11-03')

@pytest.mark.parametrize('mode',['skip','dates'])
def test_unsupported_control_news_rejects_before_raw_input_loading(lab_data,monkeypatch,mode):
    lab,m=lab_data;payload=dict(dataset_id=m['id'],start='2026-11-02',end='2026-11-03',strategy=Strategy(news='skip' if mode=='skip' else 'trade').model_dump(),news_dates=None if mode=='skip' else ['2026-11-02'])
    monkeypatch.setattr(lab,'_evaluation_input',lambda *args,**kwargs:pytest.fail('Unsupported news read prices before rejection'))
    with pytest.raises(DataError,match='versioned news'):lab.control_context(payload)

@pytest.mark.parametrize('kind',['screen','final'])
def test_active_study_job_cannot_be_hidden_by_latest500_history(lab_data,kind):
    lab,m=lab_data;sid=lab.register_study(study(m))['id']
    if kind=='final':lab.guard.screened(sid,'unit-injected-transition-not-a-passing-strategy',[Strategy().model_dump()])
    create=lab.screen if kind=='screen' else lab.final
    original=create(sid)
    with pytest.raises(ResearchError,match='already'):create(sid)
    for _ in range(505):lab.store.create_job('download',dict(name='Unexecuted pagination filler'))
    assert original['id'] not in {j['id'] for j in lab.store.jobs()}
    # The transactional store is the authoritative all-history guard; its
    # StateError base also covers the service's optimistic ResearchError.
    with pytest.raises(StateError,match='already'):create(sid)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind=? AND json_extract(payload,'$.study_id')=?",(kind,sid)).fetchone()[0]==1

@pytest.fixture
def completed_search(lab_data):
    lab,m=lab_data;job=lab.create_experiment(Search(dataset_id=m['id'],start='2026-11-02',end='2026-11-03',count=2,timeframes=['1m']))
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    return lab,job

def commit_faulty_root(lab,job,value):
    path=lab.output_path(job['id']);compressed_write(path,value)
    lab.store.event('result_saved',job['id'],dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

@pytest.mark.parametrize('kind',['missing_event','job_identity','payload_identity'])
def test_saved_result_digest_is_not_a_substitute_for_its_recorded_identity(completed_search,kind):
    lab,job=completed_search;value=lab.result(job['id'])
    if kind=='missing_event':
        with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],))
    else:
        value['job_id' if kind=='job_identity' else 'payload_hash']='wrong';commit_faulty_root(lab,job,value)
    with pytest.raises(StateError):lab.result(job['id'])

@pytest.mark.parametrize('kind',['root','unknown_part','changed_part','window','configuration'])
def test_saved_part_selection_and_independent_integrity_guards(completed_search,kind):
    lab,job=completed_search
    if kind=='root':
        with pytest.raises(StateError,match='Choose'):lab.report(job['id'])
    elif kind=='unknown_part':
        with pytest.raises(StateError,match='Unknown'):lab.report(job['id'],99)
    elif kind=='window':
        with pytest.raises(StateError,match='window'):lab.report(job['id'],0,'raw')
    else:
        path=lab.root/'data/jobs'/job['id']/'parts/000000.json.gz'
        if kind=='changed_part':path.write_bytes(path.read_bytes()+b'authored corruption')
        else:
            part=compressed_read(path);part['config_id']='wrong';compressed_write(path,part)
            value=lab.result(job['id']);value['rows'][0]['report_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();commit_faulty_root(lab,job,value)
        with pytest.raises(StateError):lab.report(job['id'],0)
