"""Original profitable and losing accounts: identical clock-based signals, different exits.

Artificial prices isolate account and export arithmetic; not detector or market-edge evidence.
"""
from dataclasses import replace
from fractions import Fraction
import csv,io,json,os,zipfile
from pathlib import Path
import pandas as pd
from conftest import minute_frame
from test_reference_execution import sig
from backend.lab import service,research_funnel_jobs,research_funnel_final,research_funnel_exports as exports
from backend.lab.config import Strategy
from backend.lab.data import save_dataset
from backend.lab.research_funnel import FunnelStudy
from backend.lab.research_funnel_registration import register_funnel
from backend.lab.service import Lab
from backend.lab.worker import Worker


def test_actual_gain_loss_accounts_and_every_exact_family_day_survive_complete_exports(tmp_path,monkeypatch):
    lab=Lab(tmp_path);days=['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06'];frames=[]
    for symbol in ['SPY','QQQ']:
        for day in days:
            frame=minute_frame(day,symbol)
            for ordinal in range(24):
                entry=21+7*ordinal
                if ordinal%2==0:frame.loc[entry,'high']=101.1;frame.loc[entry+1,'low']=98.9
                else:frame.loc[entry,'low']=98.9;frame.loc[entry+1,'high']=101.1
            frames.append(frame)
    manifest=save_dataset(lab.datasets_root,pd.concat(frames,ignore_index=True),dict(input_kind='synthetic',provider='Authored first-target gain, second-target loss schedule',corporate_actions_complete=True))
    study=register_funnel(lab,FunnelStudy(name='Complete gain and loss export fixture',dataset_id=manifest['id'],primary_symbol='SPY',replication_symbol='QQQ',
        discovery=dict(start=days[0],end=days[1]),era_one=dict(start=days[0],end=days[0]),era_two=dict(start=days[1],end=days[1]),
        validation=dict(start=days[2],end=days[2]),holdout=dict(start=days[3],end=days[4]),configurations=[Strategy(timeframe='1m',target='1R'),Strategy(timeframe='1m',target='2R')]))
    def authored(regular,*args,**kwargs):
        output=[]
        for day,group in regular.groupby(regular.timestamp.dt.strftime('%Y-%m-%d'),sort=True):
            if day<days[3]:continue
            for ordinal in range(20 if day==days[3] else 24):
                side=1 if ordinal%2==0 else -1;at=int(group.index[20+7*ordinal])
                signal=sig(regular,side=side,at=at,stop=99. if side==1 else 101.)
                output.append(replace(signal,id='authored-'+day+'-'+str(ordinal)+'-'+signal.symbol))
        return output
    monkeypatch.setattr(service,'generate_signals',authored)
    q=research_funnel_jobs.create_qualification(lab,study['id'])
    for _ in range(6):assert Worker(lab).run_once()
    assert lab.store.job(q['id'])['status']=='completed'
    final=research_funnel_final.create_final(lab,study['id']);assert Worker(lab).run_once()
    assert lab.store.job(final['id'])['status']=='completed',lab.store.job(final['id'])['error']
    value=research_funnel_final.inspect_final(lab,final['id']);accounts={};independent={}
    for arm in research_funnel_final.ARMS:
        reports=[research_funnel_final.read_final_account(lab,final['id'],part,arm) for part in range(2)];accounts[arm]=reports
        assert all(len(report['trades'])==44 and {t['side'] for t in report['trades']}=={-1,1} for report in reports)
        assert reports[0]['metrics']['net_profit']>0 and reports[1]['metrics']['net_profit']<0
        means=[Fraction() for _ in reports[0]['equity']]
        for report in reports:
            previous=Fraction(str(report['portfolio']['capital']))
            for index,row in enumerate(report['equity']):
                current=Fraction(str(row['equity']));means[index]+=(current-previous)/2;previous=current
        average=value['report']['arms'][arm]['families']['change_of_character']
        assert [Fraction(int(row['mean_pnl']['numerator']),int(row['mean_pnl']['denominator'])) for row in average['marked']['daily']]==means
        independent[arm]=[dict(numerator=str(n.numerator),denominator=str(n.denominator)) for n in means]
    def forbidden(*a,**k):raise AssertionError('Actual saved accounts must not rerun during export.')
    monkeypatch.setattr(Lab,'evaluate',forbidden);monkeypatch.setattr(service,'generate_signals',forbidden)
    built=exports.build_export(lab,final['id'],'zip')
    try:
        with zipfile.ZipFile(built['path']) as archive:
            rows=list(csv.DictReader(io.StringIO(archive.read('accounts.csv').decode())))
            assert len(rows)==4 and sum(int(row['trades']) for row in rows)==176
            for row in rows:
                original=accounts[row['arm']][int(row['part'])]
                assert Fraction(row['net_profit'])==Fraction(str(original['metrics']['net_profit']))
            daily=list(csv.DictReader(io.StringIO(archive.read('family_daily.csv').decode())))
            for arm in research_funnel_final.ARMS:
                observed=[row for row in daily if row['arm']==arm and row['convention']=='marked']
                parsed=[Fraction(int(row['mean_pnl_numerator'].removeprefix("'")),int(row['mean_pnl_denominator'].removeprefix("'"))) for row in observed]
                assert parsed==[Fraction(int(n['numerator']),int(n['denominator'])) for n in independent[arm]]
            assert json.loads(archive.read('original-result.json'))==value
        assert all(not row['candidate'] and not row['family_passed'] for row in value['rows'])
        out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(out/'actual-mixed-gain-loss-export-evidence.json').write_text(json.dumps(dict(scope=__doc__,final=value,original_accounts=accounts,
            independent_exact_family_daily_means=independent,actual_final_accounts=4,executed_trades=176,winning_accounts=2,losing_accounts=2,original_selection_changed=False,detector_or_market_edge_certified=False),indent=2),encoding='utf-8')
    finally:built['path'].unlink(missing_ok=True)
