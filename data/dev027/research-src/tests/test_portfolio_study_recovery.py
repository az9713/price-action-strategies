"""Actual interruptions/committed corruption for real joint screening and final jobs."""
from copy import deepcopy
import hashlib,json
import pytest
from backend.lab.worker import Worker
from backend.lab.research import ResearchError
from backend.lab.store import StateError
from backend.lab.service import compressed_read,compressed_write
from test_portfolio_studies import study_data,request,run,DAYS,CONFIGS,reference


@pytest.mark.parametrize('phase',['screen','final'])
@pytest.mark.parametrize('fault',['cancel','shutdown','corrupt_part','orphan_part'])
def test_complete_part_recovery_preserves_frozen_selection_and_single_final_consumption(study_data,monkeypatch,phase,fault):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id']
    if phase=='final':run(lab,lab.screen(sid))
    job=(lab.final if phase=='final' else lab.screen)(sid);frozen=deepcopy(job['payload'])
    worker=Worker(lab);progress=worker._progress
    def stop(j,p,n,checkpoint=None):
        progress(j,p,n,checkpoint)
        if checkpoint==1:
            if fault=='shutdown':worker.shutdown.set()
            else:lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once()
    assert lab.store.job(job['id'])['status']==('queued' if fault=='shutdown' else 'canceled')
    if phase=='final':assert lab.guard.study(sid)['status'] in {'consumed','final_failed'}
    part=lab.output_path(job['id']).parent/'parts/000000.json.gz';raw=part.read_bytes();digest=part.with_suffix('.sha256.json')
    with lab.store.db() as db:
        original_checkpoints=[tuple(row) for row in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' ORDER BY id",(job['id'],))]
    if fault=='corrupt_part':part.write_bytes(raw+b'changed')
    elif fault=='orphan_part':digest.unlink()
    if fault=='corrupt_part':monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Corrupt committed portfolio part read prices.'))
    if fault!='shutdown':lab.store.resume(job['id'])
    Worker(lab).run_once();state=lab.store.job(job['id']);assert state['payload']==frozen
    if fault=='corrupt_part':assert state['status']=='failed'
    else:
        assert state['status']=='completed',state['error'];assert part.read_bytes()==raw
        ledger=lab.store.registry(job_id=job['id']);expected=1 if phase=='final' else 2
        # This fixture removes a derived sidecar after actual commitment. The
        # original attempts/events and exact bytes still authorize reuse. Truly
        # uncommitted files require a new attempt in the real-death contracts.
        assert ledger['totals']['computation_attempts']==expected
        assert all(row['reuses']==1 for row in ledger['rows'])
        with lab.store.db() as db:
            assert original_checkpoints==[tuple(row) for row in db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' ORDER BY id",(job['id'],))]
        if fault=='orphan_part':
            assert json.loads(digest.read_text(encoding='utf-8'))==dict(sha256=hashlib.sha256(raw).hexdigest())
            assert any(e['kind']=='account_receipt_restored' for e in lab.store.events(job['id']))
        for window in ['report'] if phase=='final' else ['discovery','validation']:reference(lab,lab.report(job['id'],0,window))
    unlocks=[e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'];assert len(unlocks)==(1 if phase=='final' else 0)
    if phase=='final':
        with pytest.raises((ResearchError,StateError)):lab.final(sid)


@pytest.mark.parametrize('shutdown',[False,True])
def test_cancel_between_accounts_does_not_read_validation_prices(study_data,monkeypatch,shutdown):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];job=lab.screen(sid);worker=Worker(lab);evaluate=worker._evaluate;reads=[]
    def instrument(payload,configuration,start,end,*a,**k):
        reads.append((start,end));report=evaluate(payload,configuration,start,end,*a,**k)
        if shutdown:worker.shutdown.set()
        else:lab.store.cancel(job['id'])
        return report
    monkeypatch.setattr(worker,'_evaluate',instrument);worker.run_once()
    assert reads==[(DAYS[0],DAYS[1])] and lab.store.job(job['id'])['status']==('queued' if shutdown else 'canceled')
    if not shutdown:lab.store.resume(job['id'])
    run(lab,lab.store.job(job['id']));ledger=lab.store.registry(job_id=job['id'])
    assert ledger['totals']['computation_attempts']==3 and ledger['totals']['planned_occurrences']==2
    assert lab.guard.study(sid)['status']=='screened'


@pytest.mark.parametrize('fault',['part','root','ownership','candidate_event','reservation','reservation_event'])
def test_cached_final_root_revalidates_complete_evidence_and_ownership_before_any_prices(study_data,monkeypatch,fault):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];run(lab,lab.screen(sid));job=lab.final(sid)
    worker=Worker(lab);progress=worker._progress
    def stop(j,p,n,checkpoint=None):
        progress(j,p,n,checkpoint)
        if n=='Results saved and content-bound.':lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',stop);worker.run_once();assert lab.store.job(job['id'])['status']=='canceled'
    if fault in {'part','root'}:
        path=lab.output_path(job['id']) if fault=='root' else lab.output_path(job['id']).parent/'parts/000000.json.gz';path.write_bytes(path.read_bytes()+b'changed')
    elif fault in {'candidate_event','reservation_event'}:
        kind='candidates_frozen' if fault=='candidate_event' else 'portfolio_final_reserved'
        with lab.store.db() as db:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(sid,kind))
    else:
        spec=lab.guard.study(sid)['spec'];spec['final_job_id' if fault=='ownership' else 'reserved_final_job_id']='0'*32
        with lab.store.db() as db:db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(spec),sid))
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Corrupt cached final evidence read prices.'))
    lab.store.resume(job['id']);Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
    assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
