"""Actual final long/short fills and independent whole-family daily arithmetic.

Artificial prices and a prespecified clock-based signal stub test execution and
persistence, not detectors, real investment returns or a profitable strategy.
"""
from dataclasses import replace
from decimal import Decimal
from fractions import Fraction
import json
import os
from pathlib import Path
import pandas as pd
from conftest import minute_frame
from test_reference_execution import sig
from backend.lab import service,research_funnel_jobs,research_funnel_final
from backend.lab.config import Strategy
from backend.lab.data import save_dataset
from backend.lab.research_funnel import FunnelStudy
from backend.lab.research_funnel_registration import register_funnel
from backend.lab.service import Lab
from backend.lab.worker import Worker


def rational(value):return Fraction(int(value['numerator']),int(value['denominator']))


def test_actual_final_both_sides_fills_preserve_original_nonselection_and_exact_all_version_means(tmp_path,monkeypatch):
    lab=Lab(tmp_path);days=['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06'];frames=[]
    for symbol in ['SPY','QQQ']:
        for day in days:
            frame=minute_frame(day,symbol)
            for ordinal in range(24):
                if ordinal%2==0:frame.loc[21+7*ordinal,'high']=104.
                else:frame.loc[21+7*ordinal,'low']=96.
            frames.append(frame)
    manifest=save_dataset(lab.datasets_root,pd.concat(frames,ignore_index=True),dict(input_kind='synthetic',
        provider='Artificial final long/short execution schedule; not market or investment evidence',corporate_actions_complete=True))
    study=register_funnel(lab,FunnelStudy(name='Original nonselected versions still receive complete final accounts',dataset_id=manifest['id'],
        primary_symbol='SPY',replication_symbol='QQQ',discovery=dict(start=days[0],end=days[1]),
        era_one=dict(start=days[0],end=days[0]),era_two=dict(start=days[1],end=days[1]),
        validation=dict(start=days[2],end=days[2]),holdout=dict(start=days[3],end=days[4]),
        configurations=[Strategy(timeframe='1m',target='1R'),Strategy(timeframe='1m',target='2R')]))
    def authored(regular,*args,**kwargs):
        output=[]
        for day,group in regular.groupby(regular.timestamp.dt.strftime('%Y-%m-%d'),sort=True):
            if day<days[3]:continue
            for ordinal in range(20 if day==days[3] else 24):
                side=1 if ordinal%2==0 else -1;at=int(group.index[20+7*ordinal])
                signal=sig(regular,side=side,at=at,stop=99. if side==1 else 101.)
                output.append(replace(signal,id='authored-'+day+'-'+str(ordinal)+'-'+signal.symbol))
        return output
    # This same fixed signal function is installed before any development or
    # final account runs. It uses only the known decision clock/symbol.
    monkeypatch.setattr(service,'generate_signals',authored)
    qualification=research_funnel_jobs.create_qualification(lab,study['id'])
    for _ in range(6):assert Worker(lab).run_once()
    assert lab.store.job(qualification['id'])['status']=='completed'
    assert research_funnel_jobs.inspect_qualification(lab,qualification['id'])['report']['candidate_ids']==[]
    final=research_funnel_final.create_final(lab,study['id']);assert Worker(lab).run_once()
    assert lab.store.job(final['id'])['status']=='completed',lab.store.job(final['id'])['error']
    saved=research_funnel_final.inspect_final(lab,final['id']);accounts={};independent={}
    for key in research_funnel_final.ARMS:
        reports=[research_funnel_final.read_final_account(lab,final['id'],part,key) for part in range(2)]
        accounts[key]=reports
        for report in reports:
            assert len(report['trades'])==44 and {trade['side'] for trade in report['trades']}=={-1,1}
            assert report['metrics']['net_profit']>0 and report['metrics']['marked_sharpe']>=.5
            assert abs(sum(Decimal(str(trade['net_pnl'])) for trade in report['trades'])-Decimal(str(report['metrics']['net_profit'])))<Decimal('.000001')
            assert len(report['entry_traces'])==44 and report['cashflow_audit']['policy']=='decimal80-observed-fills-v1'
        expected=[Fraction() for _ in reports[0]['equity']]
        for report in reports:
            previous=Fraction(str(report['portfolio']['capital']))
            for index,row in enumerate(report['equity']):
                current=Fraction(str(row['equity']));expected[index]+=(current-previous)/2;previous=current
        mean=saved['report']['arms'][key]['families']['change_of_character']
        assert mean['version_count']==2 and mean['marked']['gate_pass'] is True
        assert [rational(row['mean_pnl']) for row in mean['marked']['daily']]==expected
        independent[key]=[dict(numerator=str(value.numerator),denominator=str(value.denominator)) for value in expected]
    assert all(not row['candidate'] and not row['family_passed'] and all(value['final_gate_pass'] for value in row['reports'].values()) for row in saved['rows'])
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='strategy' AND state='completed'",(final['id'],)).fetchone()[0]==4
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-final-long-short-accounts.json').write_text(json.dumps(dict(
            scope=__doc__,final=saved,original_accounts=accounts,independent_exact_daily_means=independent,
            actual_final_financial_accounts=4,actual_executed_trades=176,candidate_selection_changed=False,
            actual_market_or_detector_evidence=False),indent=2),encoding='utf-8')
