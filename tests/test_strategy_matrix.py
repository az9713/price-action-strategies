from pathlib import Path
import json
import os
import hashlib
import pandas as pd
import pytest
from backend.lab.config import Strategy,Costs,Portfolio,FAMILIES,TIMEFRAMES
from backend.lab.signals import generate_signals
from backend.lab.engine import simulate
from backend.lab.research import core_hash
from verification.strategy_fixtures import SPEC,scenario
from test_reference_execution import run_both,assert_parity

ROOT=Path(__file__).resolve().parents[1]
CASES=[(family,timeframe,side) for family in FAMILIES for timeframe in TIMEFRAMES for side in [1,-1]]
IDS=['MATRIX-'+family+'-'+timeframe+'-'+('long' if side>0 else 'short') for family,timeframe,side in CASES]

@pytest.mark.parametrize('family,timeframe,side',CASES,ids=IDS)
def test_full_baseline_strategy_matrix(family,timeframe,side):
    frame,known=scenario(family,timeframe,side)
    cfg=Strategy(family=family,timeframe=timeframe,direction='long' if side>0 else 'short',**SPEC['config'])
    signals=generate_signals(frame,cfg)
    matches=[s for s in signals if s.available_at==known['available_at'] and s.side==side]
    assert len(matches)==1,(family,timeframe,side,known,[(s.source_index,s.side,s.level) for s in signals])
    wanted=matches[0]
    assert wanted.level==pytest.approx(known['level'],abs=1e-8,rel=0),known['reason']
    assert wanted.source_index==known['index']
    prefix=generate_signals(frame[frame.timestamp<known['available_at']],cfg)
    assert [s.json() for s in signals if s.available_at<=known['available_at']]==[s.json() for s in prefix]
    costs=Costs(**SPEC['costs']);account=Portfolio(**SPEC['portfolio'])
    actual,expected=run_both(frame,signals,cfg,costs,account,start=known['start'],end=known['end'])
    assert any(t['id']==wanted.id for t in actual.trades),('Known positive setup did not produce an executed trade.',wanted.json(),actual.rejected)
    assert_parity(actual,expected)
    flat=frame.copy();flat[['open','high','low','close']]=[100,100.1,99.9,100]
    negative=generate_signals(flat,cfg)
    assert negative==[]
    # No fabricated negative-control trades; evaluate only the same final window.
    empty=simulate(flat,negative,cfg,costs,account,start=known['start'],end=known['end'])
    assert not empty.trades and empty.equity[-1]['equity']==account.capital
    artifact={'case_id':'MATRIX-'+family+'-'+timeframe+'-'+cfg.direction,'input_kind':'synthetic_fixture',
        'geometry':known|{'available_at':known['available_at'].isoformat()},'config':cfg.model_dump(),
        'signal':wanted.json(),'matched_trade':next(t for t in actual.trades if t['id']==wanted.id),
        'signal_count':len(signals),'trade_count':len(actual.trades),'negative_signal_count':len(negative),
        'reference_parity':True,'prefix_invariance':True,'execution_start':known['start'],'execution_end':known['end'],
        'core_hash':core_hash(),'fixture_sha256':hashlib.sha256((ROOT/'verification/fixtures/strategy-baselines.json').read_bytes()).hexdigest(),
        'minute_rows':len(frame),'minute_sha256':hashlib.sha256(frame.to_csv(index=False,float_format='%.17g').encode()).hexdigest()}
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'strategy-matrix' if os.environ.get('PA_EVIDENCE_RUN_DIR') else ROOT/'verification/runs/strategy-matrix-manual'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/(artifact['case_id']+'.json')).write_text(json.dumps(artifact,indent=2),encoding='utf-8')
