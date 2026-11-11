"""Actual original random-entry reservation from a declared primary-only arm."""
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab import service
from backend.lab.config import Strategy
from backend.lab.data import save_dataset
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.research_funnel import FunnelStudy
from backend.lab.research_funnel_registration import register_funnel
from backend.lab.research_funnel_arms import queue_arms
from backend.lab.service import Lab
from backend.lab.worker import Worker
from backend.lab.trade_twin_source import read_saved_source
from backend.lab.trade_twin_jobs import verify_child


def test_original_primary_arm_diagnostic_does_not_access_unrelated_protected_replica(tmp_path,monkeypatch):
    lab=Lab(tmp_path);days=['2026-10-28','2026-10-29','2026-10-30','2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06']
    primary=pd.concat([minute_frame(day) for day in days],ignore_index=True);replica=primary.copy();replica['symbol']='QQQ'
    both=save_dataset(lab.datasets_root,pd.concat([primary,replica],ignore_index=True),dict(input_kind='synthetic',provider='Authored shared manifest with independent guarded scopes',corporate_actions_complete=True))
    qqq=save_dataset(lab.datasets_root,replica,dict(input_kind='synthetic',provider='Authored separately protected replica',corporate_actions_complete=True))
    study=register_funnel(lab,FunnelStudy(name='Primary arm diagnostic scope',dataset_id=both['id'],primary_symbol='SPY',replication_symbol='QQQ',
        discovery=dict(start='2026-11-02',end='2026-11-03'),era_one=dict(start='2026-11-02',end='2026-11-02'),era_two=dict(start='2026-11-03',end='2026-11-03'),
        validation=dict(start='2026-11-04',end='2026-11-04'),holdout=dict(start='2026-11-05',end='2026-11-06'),configurations=[Strategy(timeframe='1m')]))
    arms=queue_arms(lab,study['id']);parent=arms['arms']['primary_discovery']
    # Scheduling priority only; every original numerical input remains frozen.
    with lab.store.db() as db:db.execute('UPDATE jobs SET created=0 WHERE id=?',(parent,))
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    assert Worker(lab).run_once() and lab.store.job(parent)['status']=='completed'
    protected=lab.register_study(Study(name='Untouched QQQ dates',dataset_id=qqq['id'],configurations=[Strategy()],
        discovery=dict(start='2026-10-28',end='2026-10-29'),validation=dict(start='2026-10-30',end='2026-10-30'),holdout=dict(start='2026-11-02',end='2026-11-03')))
    with pytest.raises(ResearchError):lab.guard.access(['QQQ'],'2026-11-02','2026-11-03','forbidden',record=False)
    source=read_saved_source(lab,parent,0)
    assert source['assumptions']['symbols']==['SPY']
    assert source['assumptions']['dataset_context']['symbols']==['QQQ','SPY']
    child=lab.create_trade_twins(parent,0)
    assert child['payload']['evaluation_symbols']==['SPY']
    assert child['payload']['twin_parent']['job_id']==parent
    verify_child(lab,child)
    assert lab.guard.study(protected['id'])['status']=='registered'
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(protected['id'],)).fetchone()[0]==0
