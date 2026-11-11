from dataclasses import replace
from pathlib import Path
import json
import random
import os
import pandas as pd
import pytest
from backend.lab.config import Strategy,Costs,Portfolio,TIMEFRAMES
from test_reference_execution import rows,sig,primitive,run_both,assert_parity

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=json.loads((ROOT/'verification/fixtures/reference-random-domain.json').read_text())

def generated_case(seed):
    rng=random.Random(seed);parts=[]
    for symbol in DOMAIN['symbols']:
        frame=rows(DOMAIN['minutes_per_symbol'],symbol)
        prior=10000
        for i in frame.index:
            opened=prior+rng.randint(-50,50);closed=opened+rng.randint(-60,60)
            frame.loc[i,['open','high','low','close','volume']]=[
                opened/100,(max(opened,closed)+rng.randint(0,60))/100,
                (min(opened,closed)-rng.randint(0,60))/100,closed/100,rng.choice([0,10,100,500,10000])]
            prior=closed
        parts.append(frame)
    configurations=[]
    for _ in range(2):
        timeframe=rng.choice(list(TIMEFRAMES));index=list(TIMEFRAMES).index(timeframe)
        trigger='1h' if timeframe=='1d' else rng.choice(list(TIMEFRAMES)[max(0,index-2):index+1])
        configurations.append(Strategy(timeframe=timeframe,trigger_timeframe=trigger,
            entry=rng.choice(['next_open','same_close','limit']),stop_kind=rng.choice(['hard','close']),
            target=rng.choice(['1R','1.5R','2R','3R','4R','5R','swing']),max_hold=rng.choice([0,24,96]),
            limit_expiry=rng.choice([1,3,12]),structure_exit=rng.choice([False,True]),
            swing_strength=rng.choice([2,3,5,8]),flat_at_close=timeframe not in {'4h','1d'} and rng.choice([False,True])))
    signals=[];mapping={}
    for part in parts:
        for at in [1,4,8,12,20,32,40]:
            side=rng.choice([1,-1]);level=round(float(part.iloc[at-1].close)+rng.randint(-10,10)/100,2)
            stop=round(level-side*rng.randint(20,200)/100,2)
            target=round(level+side*rng.randint(30,500)/100,2) if rng.randrange(5) else None
            signal=replace(sig(part,side,at,stop,name=str(part.iloc[0].symbol)+'-'+str(at),target=target),
                level=level,weight=rng.choice([.5,1]))
            signals.append(signal);mapping[signal.id]=rng.choice(configurations)
    costs=Costs(commission_per_share=rng.choice([0,.005,.5,1]),minimum_commission=rng.choice([0,.25,2]),
        fixed_fee_per_order=rng.choice([0,.05,.1]),sell_fee_per_dollar=rng.choice([0,.0001]),
        spread_bps=rng.choice([0,1,5,30]),slippage_bps=rng.choice([0,1,10]),
        borrow_annual=rng.choice([0,.03,.365]),borrow_available=seed%17!=0)
    account=Portfolio(capital=2000,risk_fraction=rng.choice([.005,.02,.1]),
        symbol_exposure=rng.choice([.25,.5,1]),total_exposure=rng.choice([.3,.7,1]),
        participation=rng.choice([.01,.05,.29,.5,1]))
    return pd.concat(parts,ignore_index=True),signals,configurations[0],costs,account,mapping

@pytest.mark.parametrize('seed',range(DOMAIN['seed_range_inclusive'][0],DOMAIN['seed_range_inclusive'][1]+1))
def test_seeded_independent_finite_paths(seed):
    frame,signals,cfg,costs,account,mapping=generated_case(seed)
    actual,expected=run_both(frame,signals,cfg,costs,account,strategy_map=mapping)
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'reference-properties' if os.environ.get('PA_EVIDENCE_RUN_DIR') else ROOT/'verification/runs/reference-properties-manual'
    folder.mkdir(parents=True,exist_ok=True)
    value={'seed':seed,'input_kind':'synthetic_fixture','bars':primitive(frame),
        'signals':[s.json() for s in signals],'configurations':{key:c.model_dump() for key,c in mapping.items()},
        'costs':costs.model_dump(),'portfolio':account.model_dump(),
        'actual':{key:getattr(actual,key) for key in ['trades','ledger','equity','rejected']},
        'expected_independent_decimal':expected}
    (folder/('seed-'+str(seed).zfill(3)+'.json')).write_text(json.dumps(value,default=str,indent=2),encoding='utf-8')
    assert_parity(actual,expected)
