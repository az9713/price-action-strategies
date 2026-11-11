"""Construct explicitly authored bar geometry on all six real session clocks."""
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path
import json
import pandas as pd
from backend.lab.data import schedule,normalize,prepare

ROOT=Path(__file__).resolve().parent.parent
SPEC=json.loads((ROOT/'verification/fixtures/strategy-baselines.json').read_text())

def scenario(family,timeframe,side):
    case=SPEC['families'][family];count=case['candidate_index']+3
    candles=[]
    for i,close in enumerate(SPEC['common_closes'][:count]):
        c=Decimal(str(close));bar={'open':c-Decimal('.02'),'high':c+Decimal('.1'),'low':c-Decimal('.1'),'close':c}
        bar.update({k:Decimal(str(v)) for k,v in case['edits'].get(str(i),{}).items()})
        if side!=case['base_side']:
            reflected=Decimal(str(SPEC['mirror_about']))
            bar={'open':reflected-bar['open'],'high':reflected-bar['low'],'low':reflected-bar['high'],'close':reflected-bar['close']}
        assert bar['low']<=min(bar['open'],bar['close'])<=max(bar['open'],bar['close'])<=bar['high']
        candles.append(bar)
    first=date.fromisoformat(SPEC['start_session']);sessions=schedule(str(first),str(first+timedelta(days=80)))
    widths={'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':390}
    raw=[];clocks=[]
    for day,(opened,closed) in sessions.items():
        begin=opened
        while begin<closed and len(clocks)<len(candles):
            finish=closed if timeframe=='1d' else min(begin+pd.Timedelta(minutes=widths[timeframe]),closed)
            bar=candles[len(clocks)];n=int((finish-begin).total_seconds()/60)
            if n==1:
                raw.append({'symbol':'SPY','timestamp':begin,**{k:float(v) for k,v in bar.items()},'volume':10000})
            else:
                checkpoints={0:bar['open'],n//3:bar['high'],2*n//3:bar['low'],n-1:bar['close']}
                previous=bar['open']
                for minute in range(n):
                    value=checkpoints.get(minute,previous)
                    raw.append({'symbol':'SPY','timestamp':begin+pd.Timedelta(minutes=minute),
                        'open':float(previous),'high':float(max(previous,value)),'low':float(min(previous,value)),
                        'close':float(value),'volume':10000})
                    previous=value
            clocks.append({'start':begin,'end':finish,'session':day});begin=finish
        if len(clocks)==len(candles): break
    assert len(clocks)==len(candles)
    frame=prepare(normalize(pd.DataFrame(raw))[0])
    level=Decimal(str(case['level']))
    if side!=case['base_side']: level=Decimal(str(SPEC['mirror_about']))-level
    event=clocks[case['candidate_index']]
    return frame,{'available_at':event['end'],'level':float(level),'side':side,'index':case['candidate_index'],
        'start':event['session'],'end':clocks[-1]['session'],'reason':case['independent_reason']}
