"""Real historical supplied-signal differential, plus independent basic metrics.

This verifies execution/accounting on generated signals, not independent signal
detection, a market-data certification, or statistical evidence of trading edge.
"""
from pathlib import Path
from decimal import Decimal
import json
import math
import os
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import load_window,read_manifest,prepare,Action
from backend.lab.engine import simulate
from backend.lab.signals import generate_signals
from backend.lab.metrics import summary
from backend.lab.service import Lab
from backend.lab.research import core_hash,core_subject
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute

def main():
    dataset_id='90f347229b2fb03ec112ee71'
    lab=Lab(ROOT);manifest=read_manifest(lab.datasets_root,dataset_id);quality=manifest['quality']
    start,end=quality['start'],quality['end']
    lab._validate_window(manifest,start,end)
    lab.guard.access(quality['symbols'],start,end,'reference_execution_verification')
    frame,_=load_window(lab.datasets_root,dataset_id,start,end)
    actions=[Action(**a) for a in manifest['actions']]
    regular=prepare(frame,actions)
    cfg=Strategy(family='change_of_character',timeframe='1h');costs=Costs();account=Portfolio()
    timings={};begun=time.perf_counter()
    signals=generate_signals(regular,cfg);timings['signal_seconds']=time.perf_counter()-begun
    begun=time.perf_counter();actual=simulate(regular,signals,cfg,costs,account,actions,start,end)
    timings['production_seconds']=time.perf_counter()-begun
    begun=time.perf_counter()
    expected=execute(primitive(regular),[s.json()|{'config_id':identity(cfg)} for s in signals],
        {identity(cfg):cfg.model_dump()},costs.model_dump(),account.model_dump(),[a.__dict__ for a in actions],start,end)
    timings['reference_seconds']=time.perf_counter()-begun
    assert_parity(actual,expected)
    assert signals and actual.trades and {t['side'] for t in actual.trades}=={-1,1}
    stats=summary(actual,account.capital)
    values=[Decimal(str(account.capital)),*[r['equity'] for r in expected['equity']]]
    returns=[float((b-a)/a) for a,b in zip(values,values[1:])]
    sigma=statistics.stdev(returns)
    sharpe=statistics.mean(returns)/sigma*math.sqrt(252) if sigma else None
    high=values[0];worst=Decimal(0)
    for value in values:
        high=max(high,value);worst=max(worst,(high-value)/high)
    profits=[t['net_pnl'] for t in expected['trades']]
    positive=sum((p for p in profits if p>0),Decimal(0));loss=-sum((p for p in profits if p<0),Decimal(0))
    daily=[b-a for a,b in zip(values,values[1:])]
    independent={'net_profit':values[-1]-values[0],'total_return':values[-1]/values[0]-1,
        'marked_sharpe':sharpe,'max_drawdown':worst,'trades':len(profits),
        'win_rate':sum(p>0 for p in profits)/len(profits),'profit_factor':positive/loss if loss else None,
        'profit_without_ten_best_days':sum(daily)-sum(sorted(daily)[-min(10,len(daily)):])}
    comparisons=[]
    for key,value in independent.items():
        if value is None: assert stats[key] is None
        else:
            difference=abs(Decimal(str(stats[key]))-Decimal(str(value)))
            tolerance=Decimal('1e-7' if key in {'net_profit','profit_without_ten_best_days'} else '1e-10')
            assert difference<=tolerance,(key,stats[key],str(value),str(difference))
            comparisons.append({'metric':key,'actual':stats[key],'reference':str(value),'absolute_difference':str(difference)})
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'historical-reference' if os.environ.get('PA_EVIDENCE_RUN_DIR') else ROOT/'verification/runs/historical-reference-manual'
    folder.mkdir(parents=True,exist_ok=True)
    output={'input_kind':'historical_market_data','dataset_id':dataset_id,'dataset_manifest_hash':identity(manifest),
        'core_hash':core_hash(),'numerical_contract':core_subject(),'config':cfg.model_dump(),'costs':costs.model_dump(),
        'portfolio':account.model_dump(),'start':start,'end':end,'signals':[s.json() for s in signals],
        'actual':{key:getattr(actual,key) for key in ['trades','ledger','equity','rejected']},
        'independent_reference':expected,'metric_comparisons':comparisons,'timings':timings,
        'scope':'Execution/accounting and basic metrics on supplied historical signals; detectors and trading-edge inference are separate gates.'}
    (folder/'comparison.json').write_text(json.dumps(output,default=str,indent=2),encoding='utf-8')
    print(json.dumps({'signals':len(signals),'trades':len(actual.trades),'ledger_events':len(actual.ledger),
        'equity_points':len(actual.equity),'metrics':{k:stats[k] for k in independent},'timings':timings},indent=2))
if __name__=='__main__': main()
