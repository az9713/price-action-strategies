"""Prespecified small positive funnel; authored signals/prices, not a market edge.

Both original10000-set interpretations must eventually execute without reducing
counts. The preflight case intentionally stops before the first financial set.
"""
from dataclasses import replace
from pathlib import Path
import json,os
import pandas as pd
from conftest import minute_frame
from test_reference_execution import sig
from backend.lab import service,research_funnel_jobs,trade_twin_worker
from backend.lab.config import Strategy
from backend.lab.data import save_dataset
from backend.lab.research_funnel import FunnelStudy
from backend.lab.research_funnel_registration import register_funnel
from backend.lab.research_qualification_source import qualification_snapshot
from backend.lab.service import Lab
from backend.lab.worker import Worker

DAYS=['2026-10-19','2026-10-20','2026-10-21','2026-10-22','2026-10-23','2026-10-26','2026-10-27','2026-10-28']
COUNTS=dict(zip(DAYS,[8,10,11,12,16,18,12,17]))


def build_small_positive(root,monkeypatch):
    lab=Lab(root);frames=[]
    for symbol in ['SPY','QQQ']:
        for day in DAYS:
            frame=minute_frame(day,symbol)
            for ordinal in range(18):
                if ordinal%2==0:frame.loc[21+18*ordinal,'high']=101.2
                else:frame.loc[21+18*ordinal,'low']=98.8
            frames.append(frame)
    manifest=save_dataset(lab.datasets_root,pd.concat(frames,ignore_index=True),dict(input_kind='synthetic',provider='Prespecified clock-based positive complete-funnel fixture; no detector or investment evidence',corporate_actions_complete=True))
    request=FunnelStudy(name='Small original positive funnel with both sides',dataset_id=manifest['id'],primary_symbol='SPY',replication_symbol='QQQ',
        discovery=dict(start=DAYS[0],end=DAYS[3]),era_one=dict(start=DAYS[0],end=DAYS[1]),era_two=dict(start=DAYS[2],end=DAYS[3]),
        validation=dict(start=DAYS[4],end=DAYS[5]),holdout=dict(start=DAYS[6],end=DAYS[7]),
        configurations=[Strategy(timeframe='1m',target='1R',stop_buffer=0.,max_hold=24)])
    study=register_funnel(lab,request)
    def authored(regular,*args,**kwargs):
        output=[]
        for day,group in regular.groupby(regular.timestamp.dt.tz_convert('America/New_York').dt.strftime('%Y-%m-%d'),sort=True):
            for ordinal in range(COUNTS[day]):
                side=1 if ordinal%2==0 else -1;at=int(group.index[20+18*ordinal]);signal=sig(regular,side=side,at=at,stop=99. if side==1 else 101.)
                output.append(replace(signal,id='positive-'+day+'-'+str(ordinal)+'-'+signal.symbol))
        return output
    monkeypatch.setattr(service,'generate_signals',authored)
    q=research_funnel_jobs.create_qualification(lab,study['id'])
    for _ in range(6):assert Worker(lab).run_once()
    with lab.store.db() as db:
        child=db.execute("SELECT child_id FROM funnel_dependencies WHERE parent_id=? AND role='control:000000'",(q['id'],)).fetchone()
    assert child is not None,'The original version did not qualify for actual matching controls.'
    return lab,study,q,child[0]


def test_original_positive_both_side_cohort_has_eligible_full_plan_before_financial_sets(tmp_path,monkeypatch):
    lab,study,q,child=build_small_positive(tmp_path,monkeypatch);saved={}
    def stop_after_preparation(*args,**kwargs):
        saved['prepared']=args[3]
        raise InterruptedError('Authored preflight stop after original preparation, before any matched financial set.')
    with monkeypatch.context() as patch:
        patch.setattr(trade_twin_worker,'FinancialParts',stop_after_preparation)
        assert Worker(lab).run_once()
    assert lab.store.job(child)['status']=='canceled'
    plan=saved['prepared']['plan'];assert plan.eligible and len(plan.sources)==41 and all(plan.pools)
    assert {trade.side for trade in plan.sources}=={-1,1} and all(trade.net_profit>0 for trade in plan.sources)
    snapshot=qualification_snapshot(lab,study['id']);assert snapshot['state']=='awaiting_controls' and snapshot['candidate_ids']==[]
    assert snapshot['rows'][0]['prequalified'] and snapshot['families']['change_of_character']['passed']
    assert snapshot['rows'][0]['accounts']['primary_discovery']['trades']==41
    with lab.store.db() as db:
        financial=db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans p ON p.id=a.trial_id WHERE p.job_id=? AND p.role='trade_twin_set'",(child,)).fetchone()[0]
        planned=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set'",(child,)).fetchone()[0]
        consumptions=db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]
    assert financial==consumptions==0 and planned==20000
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'small-positive-original-control-preflight.json').write_text(json.dumps(dict(scope=__doc__,study=study,qualification=snapshot,
            original_control_job_id=child,original_source_count=41,planned_original_financial_sets=planned,executed_financial_sets=financial,final_consumptions=consumptions,
            original_matching_plan=plan.json(),intentional_preflight_cancellation=True,completed_statistical_control_proof=False),indent=2),encoding='utf-8')
