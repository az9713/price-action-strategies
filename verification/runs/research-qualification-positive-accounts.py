"""Actual profitable five-axis accounts with authored causal signal decisions.

This proves preliminary qualification and original pending-control integration,
not detector correctness, a completed10000-set control pass or investment edge.
"""
from dataclasses import replace
import json
import os
from pathlib import Path
import pandas as pd
from conftest import minute_frame
from test_reference_execution import sig
from backend.lab import service
from backend.lab.config import Strategy,identity
from backend.lab.data import save_dataset
from backend.lab.research_funnel import FunnelStudy
from backend.lab.research_funnel_registration import register_funnel
from backend.lab.research_funnel_arms import queue_arms
from backend.lab.research_qualification_source import qualification_snapshot
from backend.lab.service import Lab
from backend.lab.worker import Worker


def build_positive_accounts(tmp_path,monkeypatch):
    lab=Lab(tmp_path);days=['2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23',
                         '2026-10-26','2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-11-02']
    frames=[]
    for index,day in enumerate(days):
        frame=minute_frame(day)
        # Signals are authored at known decision bars; entry bars reach a target
        # while respecting causal opens/stops. They are not detected patterns.
        for ordinal in range(50):frame.loc[21+7*ordinal,'high']=102.+.1*(index%5)
        frames.append(frame)
    primary=pd.concat(frames,ignore_index=True);replica=primary.copy();replica['symbol']='QQQ'
    manifest=save_dataset(lab.datasets_root,pd.concat([primary,replica],ignore_index=True),
        dict(input_kind='synthetic',provider='Authored positive original qualification; no investment evidence',corporate_actions_complete=True))
    request=FunnelStudy(name='Authored positive original qualification',dataset_id=manifest['id'],primary_symbol='SPY',replication_symbol='QQQ',
        discovery=dict(start=days[0],end=days[3]),era_one=dict(start=days[0],end=days[1]),era_two=dict(start=days[2],end=days[3]),
        validation=dict(start=days[4],end=days[7]),holdout=dict(start=days[8],end=days[-1]),
        configurations=[Strategy(timeframe='1m',stop_buffer=0,max_hold=24)])
    study=register_funnel(lab,request);arms=queue_arms(lab,study['id'])['arms']
    def authored(regular,*args,**kwargs):
        signals=[]
        for day_number,(_,group) in enumerate(regular.groupby(regular.timestamp.dt.strftime('%Y-%m-%d'),sort=True)):
            for ordinal in range(40+2*(day_number%5)):
                at=int(group.index[20+7*ordinal]);signal=sig(regular,at=at,stop=99.)
                signals.append(replace(signal,id='authored-'+str(at)+'-'+signal.symbol))
        return signals
    monkeypatch.setattr(service,'generate_signals',authored)
    for _ in range(5):assert Worker(lab).run_once()
    assert all(lab.store.job(jid)['status']=='completed' for jid in arms.values()),[lab.store.job(jid)['error'] for jid in arms.values()]
    return lab,study,arms


def test_actual_profitable_original_arms_require_real_controls_and_do_not_consume_final(tmp_path,monkeypatch):
    lab,study,arms=build_positive_accounts(tmp_path,monkeypatch)
    def forbidden(*args,**kwargs):raise AssertionError('Saved qualification must not execute another account or decode prices.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    result=qualification_snapshot(lab,study['id']);cid=identity(study['spec']['configurations'][0])
    assert result['state']=='awaiting_controls' and result['pending_control_ids']==[cid]
    assert result['candidate_ids']==[] and result['rows'][0]['prequalified'] is True
    assert result['controls'][cid]['state']=='missing' and result['families']['change_of_character']['passed'] is True
    for key,account in result['rows'][0]['accounts'].items():
        assert account['trades']>=30 and account['net_profit']>0 and account['marked_sharpe']>=.5
        assert account['signal_count']>=40
    child=lab.create_trade_twins(arms['primary_discovery'],0)
    result=qualification_snapshot(lab,study['id'])
    assert result['state']=='awaiting_controls' and result['candidate_ids']==[]
    assert result['controls'][cid]['state']=='queued' and result['controls'][cid]['job_id']==child['id']
    assert child['payload']['twin_parent']['job_id']==arms['primary_discovery']
    assert child['payload']['evaluation_symbols']==['SPY']
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
        assert db.execute('SELECT MAX(end) FROM viewed_windows').fetchone()[0]<'2026-10-29'
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==6
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'positive-original-qualification.json').write_text(json.dumps(dict(
            scope=__doc__,study=study,original_jobs={key:lab.store.job(jid) for key,jid in arms.items()},
            original_reports={key:lab.report(jid,0) for key,jid in arms.items()},qualification=result,
            control_job=dict(id=child['id'],status=child['status'],payload=child['payload']),
            completed_control_sets=0,final_consumptions=0),indent=2),encoding='utf-8')
