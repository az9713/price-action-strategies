"""Production preparation integration contracts, authored before prototype install."""
from decimal import Decimal,localcontext
from fractions import Fraction
import importlib.util
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab import service
from backend.lab.config import Costs,Portfolio,Strategy
from backend.lab.data import save_dataset
from backend.lab.models import Experiment
from backend.lab.service import Lab
from backend.lab.signals import Signal
from backend.lab.worker import Worker
from backend.lab.trade_twin_source import read_saved_source

@pytest.mark.parametrize('name',['trade_twin_features','trade_twin_amounts','trade_twin_results'])
def test_verified_preparation_components_are_installed_as_production_modules(name):
    assert importlib.util.find_spec('backend.lab.'+name) is not None,'Verified preparation component is not installed.'

def test_actual_original_account_retains_tiny_profit_beside_large_trade(tmp_path,monkeypatch):
    """Numerical-boundary fixture, not realistic US-stock prices or trading edge."""
    lab=Lab(tmp_path);day='2026-11-04';frames=[]
    for symbol,price in [('SPY',100.),('QQQ',1e-30)]:
        frame=minute_frame(day,symbol);frame[['open','high','low','close']]=[price,price*1.01,price*.99,price]
        if symbol=='SPY':frame.loc[389,['high','close']]=[1e10+1,1e10]
        else:frame.loc[389,['high','close']]=[1.003e-30,1.002e-30]
        frames.append(frame)
    raw=pd.concat(frames,ignore_index=True)
    manifest=save_dataset(lab.datasets_root,raw,dict(input_kind='synthetic',provider='Authored exact-total exponent-span boundary',corporate_actions_complete=True))
    at=frames[0].iloc[20].timestamp
    supplied=[Signal('large-source','SPY',at,1,100.,2.,98.,1e15,1.,at,20),Signal('tiny-source','QQQ',at,1,1e-30,1e-33,5e-31,1e-26,1.,at,20)]
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:supplied)
    cfg=Strategy(timeframe='1m',max_hold=0,target='swing')
    costs=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
    job=lab.create_experiment(Experiment(dataset_id=manifest['id'],start=day,end=day,strategy=cfg,costs=costs,portfolio=Portfolio(tick_size=1e-34)))
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    report=lab.result(job['id'])['report'];assert len(report['trades'])==2
    amounts=[Fraction(str(t['net_pnl'])) for t in report['trades']]
    assert min(amounts)>0 and max(amounts)>10**10 and min(amounts)<Fraction('1e-20')
    fraction=sum(amounts,Fraction(0))
    with localcontext() as context:
        context.prec=1024
        expected=Decimal(fraction.numerator)/Decimal(fraction.denominator)
    original=read_saved_source(lab,job['id'])
    assert original['original_saved_store_authority_verified'] and len(original['sources'])==2
    assert Decimal(original['reported_source_profit'])==expected,'Original reported closed-profit sum lost the tiny executed trade.'
    canonical=sum((Fraction(str(t['entry_quantity']))*(Fraction(str(t['exit_price']))-Fraction(str(t['entry_price']))) for t in report['trades']),Fraction(0))
    assert Fraction(original['source_profit'])==canonical,'Canonical observed fills lost the tiny executed trade.'
