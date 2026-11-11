from concurrent.futures import ThreadPoolExecutor
import json
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy,identity
from backend.lab.data import save_dataset,DataError
from backend.lab.models import Study,Experiment,Search
from backend.lab.research import ResearchError,core_hash
from backend.lab.service import Lab,sample_configurations,compressed_read
from backend.lab.worker import Worker

@pytest.fixture
def lab_data(tmp_path):
    lab=Lab(tmp_path)
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']],ignore_index=True)
    manifest=save_dataset(lab.datasets_root,frame,{'input_kind':'synthetic','source':'Flat test prices'},start='2026-11-02',end='2026-11-06')
    return lab,manifest

def spec(manifest):
    return Study(name='Frozen study',dataset_id=manifest['id'],
        discovery={'start':'2026-11-02','end':'2026-11-03'},validation={'start':'2026-11-04','end':'2026-11-04'},
        holdout={'start':'2026-11-05','end':'2026-11-06'},configurations=[Strategy()],minimum_trades=1)

def experiment(manifest,**kwargs):
    return Experiment(dataset_id=manifest['id'],start='2026-11-02',end='2026-11-04',**kwargs)

def test_guard_blocks_preview_analysis_selection_and_alias_before_read(lab_data,monkeypatch):
    lab,m=lab_data;study=lab.register_study(spec(m))
    alias=save_dataset(lab.datasets_root,pd.concat([minute_frame(day) for day in ['2026-11-05','2026-11-06']]),
        {'input_kind':'synthetic','source':'Alias'},start='2026-11-05',end='2026-11-06')
    def must_not_read(*a,**kw): raise AssertionError('Protected price rows were read.')
    monkeypatch.setattr('backend.lab.service.load_window',must_not_read)
    monkeypatch.setattr('backend.lab.service.select_dataset',must_not_read)
    with pytest.raises(ResearchError): lab.preview(m['id'],'SPY','2026-11-05','2026-11-06')
    with pytest.raises(ResearchError): lab.select(m['id'],['SPY'],'2026-11-05','2026-11-06')
    with pytest.raises(ResearchError): lab.create_experiment(Experiment(dataset_id=alias['id'],start='2026-11-05',end='2026-11-06'))
    with pytest.raises(ResearchError): lab.evaluate(m['id'],Strategy(),spec(m).costs,spec(m).portfolio,'2026-11-05','2026-11-06')
    assert lab.guard.study(study['id'])['status']=='registered'

def test_preview_marks_exposure_and_rejects_outside_window(lab_data):
    lab,m=lab_data
    bars=lab.preview(m['id'],'SPY','2026-11-05','2026-11-06')
    assert len(bars)==14 and bars[0]['complete']
    with pytest.raises(ResearchError,match='already been viewed'): lab.register_study(spec(m))
    with pytest.raises(DataError): lab.preview(m['id'],'SPY','2026-01-01','2026-11-02')
    with pytest.raises(DataError): lab.preview(m['id'],'SPY','2026-11-05','2026-11-06','2h')

def test_concurrent_holdout_registration_only_one_wins(lab_data):
    lab,m=lab_data
    def register(_):
        try: return lab.register_study(spec(m))['id']
        except ResearchError: return None
    with ThreadPoolExecutor(max_workers=2) as pool: ids=list(pool.map(register,[1,2]))
    assert sum(i is not None for i in ids)==1

def test_frozen_engine_and_candidate_tamper_prevent_final(lab_data,monkeypatch):
    lab,m=lab_data;study=lab.register_study(spec(m));sid=study['id']
    lab.guard.screened(sid,'screenhash',[Strategy().model_dump()])
    monkeypatch.setattr('backend.lab.research.core_hash',lambda:'changed')
    with pytest.raises(ResearchError,match='hash changed'): lab.guard.begin_final(sid,'job',m)
    monkeypatch.setattr('backend.lab.research.core_hash',core_hash)
    with lab.store.db() as db:
        value=lab.guard.study(sid)['spec'];value['candidates'][0]['target']='2R'
        db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(value),sid))
    with pytest.raises(ResearchError,match='hash changed'): lab.guard.begin_final(sid,'job',m)

def test_final_consume_is_once_and_continuation_remains_consumed(lab_data):
    lab,m=lab_data;sid=lab.register_study(spec(m))['id']
    lab.guard.screened(sid,'screenhash',[Strategy().model_dump()])
    lab.guard.begin_final(sid,'one',m)
    lab.guard.access(['SPY'],'2026-11-05','2026-11-06','final',sid,'one')
    lab.guard.finish_final(sid,'one',False);lab.guard.begin_final(sid,'one',m)
    with pytest.raises(ResearchError): lab.guard.begin_final(sid,'two',m)
    with pytest.raises(ResearchError): lab.guard.access(['SPY'],'2026-11-05','2026-11-06','preview')
    lab.guard.finish_final(sid,'one',True)
    assert lab.guard.study(sid)['status']=='final_complete'
    assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1

def test_actual_worker_experiment_and_offline_reopen(lab_data):
    lab,m=lab_data;job=lab.create_experiment(experiment(m));assert Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed'
    result=Lab(lab.root).result(job['id'])
    assert result['report']['metrics']['trades']==0 and result['report']['metrics']['net_profit']==0
    assert len(result['report']['equity'])==3 and result['report']['provenance']['input_kind']=='synthetic'
    assert result['report']['dataset_manifest_hash']==identity(m) and len(result['report']['charts']['SPY'])==21
    assert identity(result['report']['numerical_contract'])==result['report']['core_hash']

def test_screen_no_candidates_is_honest_terminal_outcome(lab_data):
    lab,m=lab_data;sid=lab.register_study(spec(m))['id'];job=lab.screen(sid);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed' and lab.result(job['id'])['candidates']==[]
    assert lab.guard.study(sid)['status']=='no_candidates'
    with pytest.raises(ResearchError): lab.final(sid)

def test_final_worker_uses_guard_and_saves_inspection_data(lab_data):
    lab,m=lab_data;sid=lab.register_study(spec(m))['id']
    # Unit-injected candidate tests transitions; flat prices did NOT pass screening.
    lab.guard.screened(sid,'test-only-injected-screen',[Strategy().model_dump()])
    job=lab.final(sid);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed' and lab.guard.study(sid)['status']=='final_complete'
    assert lab.result(job['id'])['count']==1
    part=compressed_read(lab.root/'data'/'jobs'/job['id']/'parts'/'000000.json.gz')
    assert len(part['report']['equity'])==2 and part['report']['charts']['SPY']
    with pytest.raises(ResearchError): lab.final(sid)

def test_search_sampling_reproducible_unique_and_all_requested_strata(lab_data):
    _,m=lab_data
    request=Search(**experiment(m).model_dump(),count=120,
        families=['level_bounce','breakout','flip_zone','trend_pullback','trend_line','break_of_structure','change_of_character','sweep_reclaim','supply_demand','fair_value_gap'],
        timeframes=['1m','5m','15m','1h','4h','1d'])
    configs,info=sample_configurations(request)
    assert configs==sample_configurations(request)[0] and len({identity(c) for c in configs})==120
    assert len({(c['family'],c['timeframe']) for c in configs})==60 and info['seed']==42

def test_worker_source_change_fails_without_evaluation(lab_data,monkeypatch):
    lab,m=lab_data;job=lab.create_experiment(experiment(m));monkeypatch.setattr('backend.lab.worker.core_hash',lambda:'new-source')
    Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()

def test_search_cancel_resume_reuses_verified_completed_part(lab_data,monkeypatch):
    lab,m=lab_data;request=Search(**experiment(m).model_dump(),count=2,timeframes=['1h'])
    job=lab.create_experiment(request);worker=Worker(lab);original=worker._progress
    def cancel_after_first(j,f,n,checkpoint=None):
        original(j,f,n,checkpoint)
        if checkpoint==1: lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',cancel_after_first);worker.run_once()
    assert lab.store.job(job['id'])['status']=='canceled'
    path=lab.root/'data'/'jobs'/job['id']/'parts'/'000000.json.gz';raw=path.read_bytes()
    lab.store.resume(job['id']);Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed' and path.read_bytes()==raw and lab.result(job['id'])['count']==2

def test_corrupt_checkpoint_rejected_on_resume(lab_data,monkeypatch):
    lab,m=lab_data;job=lab.create_experiment(Search(**experiment(m).model_dump(),count=2,timeframes=['1h']))
    worker=Worker(lab);original=worker._progress
    def cancel_after_first(j,f,n,checkpoint=None):
        original(j,f,n,checkpoint)
        if checkpoint==1: lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',cancel_after_first);worker.run_once()
    path=lab.root/'data'/'jobs'/job['id']/'parts'/'000000.json.gz';path.write_bytes(path.read_bytes()+b'corrupt')
    lab.store.resume(job['id']);Worker(lab).run_once();finished=lab.store.job(job['id'])
    assert finished['status']=='failed' and 'modified' in finished['error']

def test_signal_cancellation_exits_without_output(lab_data):
    from backend.lab.signals import contexts
    from backend.lab.data import aggregate,prepare
    with pytest.raises(InterruptedError): contexts(aggregate(prepare(minute_frame()),'1m'),Strategy(),lambda:True)

def test_duplicate_study_configs_rejected(lab_data):
    from pydantic import ValidationError
    _,m=lab_data;value=spec(m).model_dump();value['configurations']*=2
    with pytest.raises(ValidationError,match='unique'): Study(**value)
