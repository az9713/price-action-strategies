"""Prototype causal candidate features; not yet installed in the staged app.

Pure preparation on already-authorized observations. Original-store and file
authority must be supplied and rechecked by the future durable workflow.
"""
from datetime import date
import math,re
import numpy as np
import pandas as pd
from backend.lab.config import Strategy
from backend.lab.data import aggregate,schedule
from backend.lab.signals import prior_atr
from backend.lab.trade_twins import TwinMoment,MAX_CLOCK_MINUTES,MAX_MOMENTS


def candidate_features(regular,configuration,symbols,start,end,cancel=None):
    if cancel and cancel():raise InterruptedError('Twin feature preparation canceled.')
    cfg=Strategy(**(configuration.model_dump() if isinstance(configuration,Strategy) else configuration))
    if any(not isinstance(d,str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}',d) is None or date.fromisoformat(d).isoformat()!=d for d in [start,end]) or start>end:
        raise ValueError('Twin feature dates must be canonical and ordered.')
    if not isinstance(symbols,(list,tuple)) or any(not isinstance(s,str) or re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',s) is None for s in symbols) or len(set(symbols))!=len(symbols):
        raise ValueError('Twin features require the frozen distinct instrument cohort.')
    required={'timestamp','symbol','open','high','low','close','volume','session','session_open','session_close','factor'}
    if not isinstance(regular,pd.DataFrame) or not required<=set(regular.columns):raise ValueError('Prepared original observations are required.')
    if len(regular)>MAX_CLOCK_MINUTES:raise ValueError('Twin source-feature observation working bound exceeded.')
    if not symbols:return dict(moments=[],clock={})
    sessions=schedule(start,end);expected=[]
    for opened,closed in sessions.values():
        minutes=int((closed-opened)//pd.Timedelta(minutes=1))
        if (len(expected)+minutes)*len(symbols)>MAX_CLOCK_MINUTES:raise ValueError('Twin feature clock working bound exceeded.')
        expected.extend(pd.date_range(opened,closed,freq='min',inclusive='left'))
    if not expected:raise ValueError('The source date window has no exchange sessions.')
    moments=[];clock={}
    for symbol in sorted(symbols):
        if cancel and cancel():raise InterruptedError('Twin feature preparation canceled.')
        frame=regular[regular.symbol==symbol].sort_values('timestamp').copy()
        if frame.empty or frame.timestamp.duplicated().any():raise ValueError('Twin source instrument is absent or duplicated.')
        for row in frame.itertuples(index=False):
            if not isinstance(row.timestamp,pd.Timestamp) or row.timestamp.tzinfo is None or row.timestamp.second or row.timestamp.microsecond or row.timestamp.nanosecond:
                raise ValueError('Twin features require aware original minute clocks.')
            if any(isinstance(getattr(row,k),bool) or not math.isfinite(float(getattr(row,k))) or getattr(row,k)<=0 for k in ['open','high','low','close','factor']):
                raise ValueError('Twin feature prices and split factors must be positive and finite.')
            if row.low>min(row.open,row.close) or row.high<max(row.open,row.close):raise ValueError('Twin original OHLC observations are inconsistent.')
        window=frame[(frame.session>=start)&(frame.session<=end)]
        if list(window.timestamp)!=expected:raise ValueError('Twin features require the complete expected original regular-minute clock.')
        for row in window.itertuples(index=False):
            day=row.timestamp.tz_convert('America/New_York').date().isoformat()
            if row.session!=day or (row.session_open,row.session_close)!=sessions.get(day):raise ValueError('Twin feature session identity differs from the exchange calendar.')
        clock[symbol]=[t.isoformat() for t in expected]
        chart=aggregate(frame,cfg.timeframe);chart=chart[chart.complete].reset_index(drop=True)
        atr=prior_atr(chart.high.to_numpy(),chart.low.to_numpy(),chart.close.to_numpy()) if len(chart) else np.array([])
        boundaries=chart.available_at.astype('int64').to_numpy()
        for ordinal,row in enumerate(window.itertuples(index=False)):
            if cancel and ordinal%100==0 and cancel():raise InterruptedError('Twin feature preparation canceled at minute checkpoint.')
            index=int(np.searchsorted(boundaries,row.timestamp.value,side='right'))-1
            if index<0 or not np.isfinite(atr[index]) or atr[index]<=0:continue
            value=float(atr[index]/row.factor)
            if not math.isfinite(value) or value<=0:raise ValueError('Known raw twin ATR is outside the numerical range.')
            moment=TwinMoment(symbol=symbol,entry_at=row.timestamp.isoformat(),reference_price=float(row.open),atr=value,atr_available_at=chart.iloc[index].available_at.isoformat())
            moments.append(moment.model_dump(mode='json'))
            if len(moments)>MAX_MOMENTS:raise ValueError('Twin candidate-feature working bound exceeded; no subset retained.')
    if cancel and cancel():raise InterruptedError('Twin feature preparation canceled before return.')
    return dict(moments=moments,clock=clock)
