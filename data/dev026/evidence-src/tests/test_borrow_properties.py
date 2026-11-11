"""Seeded finite paths with independently executed time-varying lending states."""
import random
from datetime import timedelta
from pathlib import Path
import json
import os
import pytest
from backend.lab.config import Costs
from test_reference_properties import generated_case
from test_reference_execution import run_both,assert_parity,primitive
from test_borrow import scenario,event


@pytest.mark.parametrize('seed',range(24))
def test_seeded_shared_path_lending_changes_match_independent_decimal_oracle(seed):
    rng=random.Random(7000+seed)
    frame,signals,cfg,costs,account,mapping=generated_case(seed)
    day=str(frame.session.min());events=[];first=frame.timestamp.min()
    for symbol in sorted(frame.symbol.unique()):
        for minute in [0,5,11,19,31,41]:
            recall=rng.choice([False,False,True]);available=False if recall else rng.choice([False,True])
            events.append(event((first+timedelta(minutes=minute)).isoformat(),
                rate=rng.choice([0,.03,.1,.3,.365]),available=available,recall=recall,symbol=symbol))
    spec=scenario(start=day,end=str(frame.session.max()),symbols=sorted(frame.symbol.unique()),events=events)
    current=Costs(**(costs.model_dump()|dict(borrow_scenario=spec)))
    actual,expected=run_both(frame,signals,cfg,current,account,strategy_map=mapping)
    output=Path(os.environ.get('PA_EVIDENCE_RUN_DIR','verification/runs/borrow-properties-manual'))/'borrow-reference-properties'
    output.mkdir(parents=True,exist_ok=True)
    value=dict(seed=seed,input_kind='synthetic',bars=primitive(frame),signals=[s.json() for s in signals],
        configurations={s.id:mapping[s.id].model_dump() for s in signals},costs=current.model_dump(),portfolio=account.model_dump(),
        actual={key:getattr(actual,key) for key in ['trades','ledger','equity','rejected']},independent_reference=expected)
    (output/('seed-'+str(seed).zfill(2)+'.json')).write_text(json.dumps(value,default=str,indent=2),encoding='utf-8')
    assert_parity(actual,expected)
