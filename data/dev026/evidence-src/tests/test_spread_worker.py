"""Actual durable worker flow, saved signals, source-qualified selection and recovery."""
from pathlib import Path
import json,os,shutil
import pytest
from test_spread_probe import owned
from backend.lab.worker import Worker
from backend.lab.store import StateError
from backend.lab.spread_jobs import SpreadJournal

def request(manifest,**updates):
    from backend.lab.models import SpreadExperiment
    value=dict(dataset_id=manifest['id'],primary_symbol='SPY',start='2026-10-19',end='2026-10-30',name='Owned spread worker',settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=40,max_batches_per_family=2))
    value.update(updates);return SpreadExperiment(**value)
def job_and_worker(owned,**updates):
    lab,m,context,cfg=owned;job=lab.create_spread(request(m,**updates));return lab,job,Worker(lab)
def state(lab,job):return SpreadJournal(lab.store,lab.store.job(job['id']),None).status()

def test_actual_worker_freezes_all_proposals_then_saves_primary_signals_without_pnl(owned,monkeypatch):
    lab,job,worker=job_and_worker(owned)
    def forbidden(*a,**k):raise AssertionError('Qualification executed account P&L')
    monkeypatch.setattr('backend.lab.service.simulate',forbidden);assert worker.run_once()
    saved=lab.store.job(job['id']);assert saved['status']=='completed',saved.get('error')
    result=lab.result(job['id']);assert result['spread_selection']['complete'] and len(result['selection_manifest']['configurations'])==1
    projection=state(lab,job);assert projection['frozen_proposals']==80 and projection['committed_probes']==9 and projection['selected_versions']==1
    registry=lab.store.registry(job_id=job['id']);assert registry['totals']['computation_attempts']==9
    assert set(registry['totals']['roles'])=={'signal_probe'} and registry['totals']['roles']['signal_probe']['occurrences']==9
    assert result['account_phase']=='not_started' and 'report' not in result and 'rows' not in result
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        destination=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-spread-worker';destination.mkdir()
        (destination/'frozen-inputs.json').write_text(json.dumps(lab.store.job_inputs(job['id']),indent=2),encoding='utf-8')
        (destination/'registry.json').write_text(json.dumps(registry,indent=2),encoding='utf-8')
        (destination/'events.json').write_text(json.dumps(lab.store.events(job['id']),indent=2),encoding='utf-8')
        (destination/'summary.json').write_text(json.dumps(dict(scope='Actual synthetic primary signals only; zero selected-account P&L executions',job_id=job['id'],status=projection),indent=2),encoding='utf-8')
        folder=lab.output_path(job['id']).parent
        for p in folder.rglob('*'):
            if p.is_file():
                relative=p.relative_to(folder);assert relative.parts[0] in {'result.json.gz','spread-signals','spread-proposals','spread-preparation'} and not p.is_symlink()
                q=destination/'original-job-artifacts'/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)

def test_cancelled_preparation_resumes_committed_batches_without_any_early_price_read(owned,monkeypatch):
    from backend.lab import spread
    lab,job,worker=job_and_worker(owned);original=spread.draw;trigger=[]
    def interrupted(*a):
        value=original(*a)
        if not trigger:trigger.append(True);lab.store.cancel(job['id'])
        return value
    monkeypatch.setattr(spread,'draw',interrupted);assert worker.run_once();assert lab.store.job(job['id'])['status']=='canceled'
    assert state(lab,job)['frozen_batches']==1 and state(lab,job)['probe_attempts']==0
    monkeypatch.setattr(spread,'draw',original);lab.store.resume(job['id']);assert Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed'
    assert state(lab,job)['frozen_batches']==2

@pytest.mark.parametrize('after',['probe_started','probe_completed'])
def test_signal_boundary_resume_retains_distinct_attempts_and_reuses_committed_evidence(owned,monkeypatch,after):
    lab,job,worker=job_and_worker(owned);original=SpreadJournal.append;once=[];calls=[];probe=lab.spread_signal_probe
    def observed(*a,**k):calls.append(1);return probe(*a,**k)
    monkeypatch.setattr(lab,'spread_signal_probe',observed)
    def interrupted(self,event,*a,**k):
        value=original(self,event,*a,**k)
        if event['kind']==after and not once:once.append(True);raise InterruptedError('Owned persisted signal-boundary interruption')
        return value
    monkeypatch.setattr(SpreadJournal,'append',interrupted);assert worker.run_once();assert lab.store.job(job['id'])['status']=='canceled'
    monkeypatch.setattr(SpreadJournal,'append',original);lab.store.resume(job['id']);assert Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    registry=lab.store.registry(job_id=job['id']);assert registry['totals']['computation_attempts']==(10 if after=='probe_started' else 9)
    if after=='probe_completed':assert registry['rows'][0]['reuses']>=1
    assert len(calls)==9

def test_corrupt_committed_signal_file_fails_before_any_new_probe(owned,monkeypatch):
    lab,job,worker=job_and_worker(owned);original=SpreadJournal.append;once=[]
    def interrupted(self,event,*a,**k):
        value=original(self,event,*a,**k)
        if event['kind']=='probe_completed' and not once:once.append(event['evidence']['evidence_sha256']);raise InterruptedError('Owned completed probe stop')
        return value
    monkeypatch.setattr(SpreadJournal,'append',interrupted);assert worker.run_once();assert once
    path=lab.root/'data/jobs'/job['id']/'spread-signals'/(once[0]+'.json.gz');raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
    monkeypatch.setattr(SpreadJournal,'append',original)
    def forbidden(*a,**k):raise AssertionError('A new signal was computed after committed corruption')
    monkeypatch.setattr(lab,'spread_signal_probe',forbidden);lab.store.resume(job['id']);assert Worker(lab).run_once()
    assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()

def test_exhausted_pool_has_no_successful_manifest_or_account_execution(owned):
    lab,job,worker=job_and_worker(owned,primary_symbol='QQQ',settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=2,max_batches_per_family=1))
    assert worker.run_once();saved=lab.store.job(job['id']);assert saved['status']=='completed',saved.get('error')
    result=lab.result(job['id']);assert not result['spread_selection']['complete'] and result['selection_manifest'] is None
    assert result['account_phase']=='not_started' and state(lab,job)['stage']=='exhausted'

def test_late_committed_signal_corruption_prevents_result_publication(owned,monkeypatch):
    lab,job,worker=job_and_worker(owned);original=SpreadJournal.append
    def corrupt(self,event,*a,**k):
        value=original(self,event,*a,**k)
        if event['kind']=='selection_finished':
            p=next((lab.root/'data/jobs'/job['id']/'spread-signals').glob('*.json.gz'));raw=p.read_bytes();p.write_bytes(b'X'+raw[1:])
        return value
    monkeypatch.setattr(SpreadJournal,'append',corrupt);assert worker.run_once()
    assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()

def test_parent_uses_one_master_seed_and_rejects_conflicting_seed_controls(owned):
    from pydantic import ValidationError
    lab,m,context,cfg=owned
    resolved=request(m,seed=117);assert resolved.seed==resolved.settings['seed']==117
    with pytest.raises(ValidationError):request(m,seed=117,settings=dict(seed=42))
