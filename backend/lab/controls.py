"""Outcome-blind conditional randomization, separate from executable strategies."""
from bisect import bisect_right
from collections import deque
from decimal import Decimal
from numbers import Integral
import math
import numpy as np
import pandas as pd

from .config import identity
from .data import DataError,aggregate
from .signals import Signal,prior_atr
from .metrics import block_interval
from .news import news_weight

POLICY_VERSION=1
VOLATILITY_BOUNDARIES=[Decimal(x) for x in ['.0025','.005','.01','.02','.04']]
MAX_EDGES=2_000_000
MAX_STORED_CONTROLS=100_000


def volatility_band(atr,close):
    if not math.isfinite(atr) or not math.isfinite(close) or atr<=0 or close<=0:
        raise DataError('Control volatility needs positive finite ATR and close.')
    return bisect_right(VOLATILITY_BOUNDARIES,Decimal(str(atr))/Decimal(str(close)))


def feature_table(regular,configuration,cancel=None):
    output=[]
    for symbol,minutes in regular.groupby('symbol',sort=True):
        if cancel and cancel():raise InterruptedError('Control features canceled.')
        setup=aggregate(minutes,configuration.timeframe)
        setup=setup[setup.complete].copy()
        if setup.empty:continue
        setup['atr']=prior_atr(*(setup[name].to_numpy(float) for name in ['high','low','close']))
        trigger=setup if configuration.trigger==configuration.timeframe else aggregate(minutes,configuration.trigger)
        trigger=trigger[trigger.complete]
        merged=pd.merge_asof(trigger[['available_at','close','duration_minutes']].sort_values('available_at'),
            setup[['available_at','atr']].sort_values('available_at'),on='available_at',direction='backward')
        for row in merged.itertuples(index=False):
            if np.isfinite(row.atr) and row.atr>0:
                output.append(dict(symbol=symbol,available_at=row.available_at.isoformat(),close=float(row.close),
                                   atr=float(row.atr),duration_minutes=int(row.duration_minutes)))
    return output


def _maximum_matching(source_ids,pools,order,cancel=None):
    """Iterative augmenting paths: no recursion-depth limit or greedy sample loss."""
    assigned={};owner={}
    for root in source_ids:
        if cancel and cancel():raise InterruptedError('Control matching canceled.')
        queue=deque([root]);parents={};seen_sources={root};seen_candidates=set();free=None
        while queue and free is None:
            source=queue.popleft()
            if cancel and cancel():raise InterruptedError('Control matching canceled.')
            for candidate in sorted(pools[source],key=lambda key:order(source,key)):
                if candidate in seen_candidates:continue
                seen_candidates.add(candidate)
                if candidate not in owner:
                    free=(source,candidate);break
                other=owner[candidate]
                if other not in seen_sources:
                    seen_sources.add(other);parents[other]=(source,candidate);queue.append(other)
        if free is None:continue
        source,candidate=free
        while True:
            assigned[source]=candidate;owner[candidate]=source
            if source not in parents:break
            source,candidate=parents[source]
    return assigned


def _geometry(source,source_close,candidate):
    distance=source.side*(source_close-source.stop)/source.atr
    level=candidate['close']+(source.level-source_close)/source.atr*candidate['atr']
    stop=candidate['close']-source.side*distance*candidate['atr']
    target=None if source.target_swing is None else candidate['close']+(source.target_swing-source_close)/source.atr*candidate['atr']
    return dict(level=level,stop=stop,target_swing=target)


def make_control_plan(features,signals,configuration,start,end,seed=42,replicas=20,cancel=None,news_dates=None):
    policy=POLICY_VERSION+(1 if configuration.news!='trade' else 0)
    if not isinstance(replicas,Integral) or isinstance(replicas,bool) or not 1<=replicas<=200:
        raise DataError('Choose one to200 control replicas internally; public jobs require at least two.')
    if not isinstance(seed,Integral) or isinstance(seed,bool) or not 0<=seed<=2**31-1:
        raise DataError('Controls require a nonnegative31-bit master seed.')
    candidates={}
    for row in features:
        at=pd.Timestamp(row['available_at'])
        if at.tz is None:raise DataError('Control candle times require an explicit timezone.')
        at=at.tz_convert('UTC');local=at.tz_convert('America/New_York')
        if not start<=local.strftime('%Y-%m-%d')<=end:continue
        weight=news_weight(configuration.news,news_dates,at)
        if weight==0:continue
        key=row['symbol']+'|'+at.isoformat()
        if key in candidates:raise DataError('Duplicate control candle identity.')
        close=float(row['close']);atr=float(row['atr']);duration=row['duration_minutes']
        if not isinstance(duration,Integral) or duration<=0:raise DataError('Invalid control candle duration.')
        candidates[key]=dict(symbol=row['symbol'],available_at=at.isoformat(),close=close,atr=atr,duration_minutes=int(duration),
            time_bucket=(local.hour*60+local.minute-570)//30,volatility_band=volatility_band(atr,close),news_weight=weight)
    sources=[s for s in signals if start<=s.available_at.tz_convert('America/New_York').strftime('%Y-%m-%d')<=end]
    if len({s.id for s in sources})!=len(sources):raise DataError('Duplicate source signal identity.')
    if len(sources)>20000:raise DataError('Controls exceed20000 source events; select a smaller date window.')
    sources=sorted(sources,key=lambda s:s.id);by_id={s.id:s for s in sources}
    real_moments={s.symbol+'|'+s.available_at.tz_convert('UTC').isoformat() for s in sources}
    strata={}
    for key,row in sorted(candidates.items()):
        if key in real_moments:continue
        stratum=(row['symbol'],row['duration_minutes'],row['time_bucket'],row['volatility_band'],row['news_weight'] if configuration.news=='half' else 1.)
        strata.setdefault(stratum,[]).append(key)
    pools={};reasons={};source_closes={};edges=0
    for source in sources:
        if cancel and cancel():raise InterruptedError('Control eligibility canceled.')
        key=source.symbol+'|'+source.available_at.tz_convert('UTC').isoformat()
        current=candidates.get(key)
        invalid=(current is None or not np.isfinite([source.atr,source.level,source.stop,source.weight]).all() or source.atr<=0 or not 0<source.weight<=1 or source.side not in {-1,1})
        if not invalid:
            invalid=source.side*(current['close']-source.stop)<=0
            if configuration.target=='swing':
                invalid=invalid or source.target_swing is None or not np.isfinite(source.target_swing) or source.side*(source.target_swing-current['close'])<=0
        if invalid:
            pools[source.id]=[];reasons[source.id]='Source decision candle or positive stop/target geometry is unavailable.';continue
        source_closes[source.id]=current['close']
        stratum=(source.symbol,current['duration_minutes'],current['time_bucket'],volatility_band(source.atr,current['close']),source.weight if configuration.news=='half' else 1.)
        keys=[]
        for candidate_key in strata.get(stratum,[]):
            geometry=_geometry(source,current['close'],candidates[candidate_key])
            values=[geometry['level'],geometry['stop']]+([] if geometry['target_swing'] is None else [geometry['target_swing']])
            if np.isfinite(values).all() and min(values)>0:keys.append(candidate_key)
        edges+=len(keys)
        if edges>MAX_EDGES:raise DataError('Controls exceed two million matching edges; reduce the date window.')
        pools[source.id]=keys
        if not keys:reasons[source.id]='No non-signal moment matches symbol, time, duration, volatility and positive geometry.'
    canonical=_maximum_matching([s.id for s in sources],pools,lambda source,key:key,cancel)
    matched=sorted(canonical)
    if len(matched)*replicas>MAX_STORED_CONTROLS:
        raise DataError('Controls exceed100000 stored matched events; reduce the window or replica count.')
    output=[];config_id=identity(configuration)
    for replica in range(replicas):
        stream=dict(policy=policy,seed=int(seed),configuration=config_id,replica=replica)
        rank=lambda source,key:identity(stream|dict(source=source,candidate=key))
        assigned=_maximum_matching(matched,pools,rank,cancel)
        if set(assigned)!=set(matched):raise DataError('Control assignment failed to preserve the frozen matched subset.')
        matches=[]
        for source_id in matched:
            source=by_id[source_id];key=assigned[source_id];candidate=candidates[key]
            geometry=_geometry(source,source_closes[source_id],candidate)
            when=pd.Timestamp(candidate['available_at'])
            sid=identity(stream|dict(source=source_id,candidate=key))[:24]
            control=Signal(sid,source.symbol,when,source.side,geometry['level'],candidate['atr'],geometry['stop'],
                geometry['target_swing'],source.weight,when,-1)
            matches.append(dict(source_id=source_id,candidate_key=key,signal=control.json(),
                matching=dict(time_bucket=candidate['time_bucket'],volatility_band=candidate['volatility_band'],duration_minutes=candidate['duration_minutes'],news_weight=candidate['news_weight']),
                source_geometry=dict(close=source_closes[source_id],atr=source.atr,level=source.level,stop=source.stop,target_swing=source.target_swing)))
        output.append(dict(replica=replica,stream_key=identity(stream),matches=matches))
    return dict(policy_version=policy,configuration_id=config_id,seed=int(seed),source_count=len(sources),
        matched_count=len(matched),matched_source_ids=matched,matching_edges=edges,
        unmatched=[dict(source_id=s.id,reason=reasons.get(s.id,'Insufficient distinct matched moments for all source events.')) for s in sources if s.id not in canonical],
        replicas=output)


def comparison_statistics(real,controls,seed=42):
    x=np.asarray(real['daily_pnl'],float)
    if x.ndim!=1 or not np.isfinite(x).all():raise DataError('Real control comparison P&L must be finite daily observations.')
    for control in controls:
        y=np.asarray(control['daily_pnl'],float)
        if y.shape!=x.shape or not np.isfinite(y).all():raise DataError('Control daily sessions must align with the real book.')
    notes=['Conditional randomization exceedance is descriptive, not a search-adjusted global significance level or trading-edge certificate.']
    eligible=bool(controls) and real['trades']>0 and all(c['trades']>0 for c in controls)
    net=[c['net_profit'] for c in controls]
    average=float(np.mean(net)) if net else None
    count=sum(value>=real['net_profit'] for value in net)
    difference=None if average is None else real['net_profit']-average
    interval=None
    if eligible:
        daily=x-np.mean([c['daily_pnl'] for c in controls],axis=0)
        interval=block_interval(daily,seed=seed)
    else:notes.append('No eligible comparison: real or control accounts have no executed trades, or no matched controls exist.')
    return dict(real_net_profit=real['net_profit'],mean_control_net_profit=average,net_difference=difference,
        control_accounts=len(controls),control_at_least_real=count,
        exceedance_fraction=(1+count)/(len(controls)+1) if eligible else None,
        paired_pnl_interval=interval,limitations=notes)
