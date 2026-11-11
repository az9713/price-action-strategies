"""Family arithmetic over actual engine accounts with authored signals, not totals.

This verifies accounting-to-family integration, not the strategy detectors or the
unfinished durable research funnel/API/UI.
"""
from decimal import Decimal, localcontext
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pytest
from conftest import minute_frame
from test_reference_execution import sig
from backend.lab import service
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import save_dataset
from backend.lab.service import Lab
from backend.lab.research_funnel import family_average


def test_actual_all_version_accounts_preserve_losses_unequal_trade_counts_and_both_daily_conventions(tmp_path,monkeypatch):
    lab=Lab(tmp_path)
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04']],ignore_index=True)
    frame[['open','high','low','close']]=[100.,101.,99.,100.]
    frame['volume']=10000.
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Authored complete family accounting integration',corporate_actions_complete=True))
    def authored(regular,*args,**kwargs):
        return [replace(sig(regular,at=day*390+20),id='authored-day-'+str(day)) for day in range(3)]
    monkeypatch.setattr(service,'generate_signals',authored)
    versions=[Strategy(timeframe='1m',max_hold=value) for value in [0,24,96]]
    costs=Costs(commission_per_share=.01,spread_bps=2,slippage_bps=1,borrow_annual=0)
    account=Portfolio(capital=100000)
    reports={identity(c):lab.evaluate(manifest['id'],c,costs,account,'2026-11-02','2026-11-04') for c in versions}
    before={key:identity(value) for key,value in reports.items()}
    assert len({len(r['trades']) for r in reports.values()})>1
    assert all(r['metrics']['net_profit']<0 and r['cashflow_audit']['policy']=='decimal80-observed-fills-v1' for r in reports.values())
    value=family_average(versions,reports)
    assert value['version_count']==3 and value['state']=='complete'
    assert not value['marked']['gate_pass']
    days=['2026-11-02','2026-11-03','2026-11-04']
    with localcontext() as context:
        context.prec=80
        marked=[Decimal(0)]*3;realized=[Decimal(0)]*3
        for report in reports.values():
            previous=Decimal(str(account.capital))
            for index,row in enumerate(report['equity']):
                observed=Decimal(str(row['equity']));marked[index]+=(observed-previous)/Decimal(3);previous=observed
            for trade in report['trades']:
                day=pd.Timestamp(trade['exit_at']).tz_convert('America/New_York').date().isoformat()
                realized[days.index(day)]+=Decimal(str(trade['net_pnl']))/Decimal(3)
        for convention,expected in [('marked',marked),('realized_exit_day_compatibility',realized)]:
            for row,amount in zip(value[convention]['daily'],expected):
                exact=Fraction(int(row['mean_pnl']['numerator']),int(row['mean_pnl']['denominator']))
                assert abs(Decimal(exact.numerator)/Decimal(exact.denominator)-amount)<Decimal('1e-65')
    assert before=={key:identity(report) for key,report in reports.items()}
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-family-accounts.json'
        output.write_text(json.dumps(dict(scope=__doc__,versions=[c.model_dump() for c in versions],
            original_reports=reports,family=value,independent_marked=[str(x) for x in marked],
            independent_realized=[str(x) for x in realized],original_accounts_unchanged=True),indent=2),encoding='utf-8')


@pytest.mark.parametrize('raw',[True,None,'not-money','NaN','Infinity','1e1001','1'*513])
def test_finite_original_amounts_do_not_silently_coerce_or_overflow(raw):
    from backend.lab.research_funnel import _amount
    with pytest.raises(ValueError):_amount(raw)


def test_floating_summary_overflow_is_an_explicit_error():
    from backend.lab.research_funnel import _float
    with pytest.raises(ValueError):_float(Fraction(10**1000))
    with pytest.raises(ValueError):_float(float('inf'))
