"""Online confirmed structure and ten distinct price-action setup detectors.

Prices are in the causal split-normalized numeraire. Engine converts to raw tradable
prices at fill time. No detector sees an unclosed candle or an unconfirmed pivot.
"""
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from .config import Strategy, TIMEFRAMES, identity
from .data import aggregate, DataError
from .news import news_weight

CONTEXT_FIELDS=(
    'impulse_atr','impulse_bars','level_age','level_shape','level_tolerance','min_touches',
    'pullback_max','pullback_min','reclaim_bars','retest_window','sweep_depth','swing_strength',
)

def prior_atr(h,l,c,period=14):
    out=np.full(len(c),np.nan)
    tr=np.maximum(h-l,np.maximum(abs(h-np.r_[c[0],c[:-1]]),abs(l-np.r_[c[0],c[:-1]])))
    value=np.nan
    for i in range(period,len(c)):
        value=float(np.mean(tr[:period])) if i==period else (value*(period-1)+tr[i-1])/period
        out[i]=value
    return out

def contexts(bars:pd.DataFrame,cfg:Strategy,cancel=None,observer=None):
    """One symbol, ordered completed bars. Historical rows are never revised."""
    b=bars.sort_values('available_at').reset_index(drop=True).copy()
    n=len(b)
    if not n: return b
    o,h,l,c=[b[x].to_numpy(float) for x in ['open','high','low','close']]
    atr=prior_atr(h,l,c)
    highs=[]; lows=[]; levels=[]; flips=[]; gaps=[]; zones=[]; sweeps=[]
    trend=0; used_high=-1; used_low=-1; pullback_used={1:False,-1:False}
    records=[]
    for i in range(n):
        if cancel and i%100==0 and cancel(): raise InterruptedError('Signal calculation canceled.')
        a=atr[i]; k=cfg.swing_strength
        if i>=2*k:
            j=i-k
            for side,array,pivots in [(1,h,highs),(-1,l,lows)]:
                window=array[j-k:j+k+1]
                extreme=np.max(window) if side==1 else np.min(window)
                if array[j]==extreme and np.count_nonzero(window==extreme)==1:
                    pivots.append((j,float(array[j])))
                    if np.isfinite(a) and a>0:
                        near=[x for x in levels if x['side']==side and abs(x['price']-array[j])<=cfg.level_tolerance*a]
                        if near:
                            level=min(near,key=lambda x:(abs(x['price']-array[j]),x['born']))
                            level['price']=(level['price']*level['pivots']+array[j])/(level['pivots']+1)
                            level['pivots']+=1
                        else:
                            levels.append(dict(side=side,price=float(array[j]),born=i,touches=0,last_touch=-2,pivots=1,broken=False,bounce_visit=-1))
            if len(highs)>=2 and len(lows)>=2:
                seed=1 if highs[-1][1]>highs[-2][1] and lows[-1][1]>lows[-2][1] else (-1 if highs[-1][1]<highs[-2][1] and lows[-1][1]<lows[-2][1] else 0)
                if not trend and seed: trend=seed
        before=trend
        sh=highs[-1][1] if highs else np.nan
        sl=lows[-1][1] if lows else np.nan
        bos=choch=0
        if highs and c[i]>sh and highs[-1][0]!=used_high:
            if before==-1: choch=1;trend=1
            elif before==1: bos=1
            used_high=highs[-1][0];pullback_used[1]=False
        if lows and c[i]<sl and lows[-1][0]!=used_low:
            if before==1: choch=-1;trend=-1
            elif before==-1: bos=-1
            used_low=lows[-1][0];pullback_used[-1]=False
        row=dict(atr=a,trend=trend,trend_before=before,swing_high=sh,swing_low=sl,bos=bos,choch=choch,
                 breakout=0,breakout_level=np.nan,bounce=0,bounce_level=np.nan,
                 flip=0,flip_level=np.nan,sweep=0,sweep_level=np.nan,sweep_wick=np.nan,
                 pullback=0,pullback_level=np.nan,line=0,line_level=np.nan,
                 demand=0,demand_level=np.nan,gap=0,gap_level=np.nan,gap_stop=np.nan,gap_active=0,gap_active_long=False,gap_active_short=False,
                 efficiency=1.0)
        offered={}
        def offer(name,side,level,born,**extra):
            offered.setdefault(name,[]).append(dict(side=side,level=level,born=born,**extra))
        if i>=10:
            path=np.sum(abs(np.diff(c[i-10:i+1])))
            row['efficiency']=abs(c[i]-c[i-10])/path if path else 0.0
        if np.isfinite(a) and a>0:
            tol=cfg.level_tolerance*a
            levels=[x for x in levels if i-x['born']<=cfg.level_age]
            for level in levels:
                price=level['price'];side=level['side']
                touches=l[i]<=price+tol and h[i]>=price-tol
                if touches:
                    if level['last_touch']<i-1: level['touches']+=1
                    level['last_touch']=i
                if level['touches']<cfg.min_touches: continue
                edge=tol if cfg.level_shape=='zone' else 0
                if not level['broken'] and i and side*(c[i]-price)>edge and side*(c[i-1]-price)<=edge:
                    offer('breakout',side,price,level['born'])
                    level['broken']=True
                    flips.append(dict(side=side,price=price,born=i,used=False))
                bounce_side=-side
                if not level['broken'] and touches and level['bounce_visit']!=level['touches'] and bounce_side*(c[i]-price)>0 and i and bounce_side*(c[i-1]-price)>0:
                    offer('bounce',bounce_side,price-bounce_side*edge,level['born'])
                    level['bounce_visit']=level['touches']
            for flip in flips:
                side=flip['side'];price=flip['price']
                if 0<i-flip['born']<=cfg.retest_window and not flip['used'] and l[i]<=price+tol and h[i]>=price-tol:
                    if side*(c[i]-price)>0:
                        offer('flip',side,price,flip['born'])
                    flip['used']=True
            flips=[x for x in flips if i-x['born']<=cfg.retest_window]
            for side,price in [(1,sl),(-1,sh)]:
                wick=l[i] if side==1 else h[i]
                if np.isfinite(price) and side*(price-wick)>cfg.sweep_depth*a:
                    sweeps.append(dict(side=side,price=price,wick=wick,born=i))
            for sweep in sweeps:
                side=sweep['side']
                if i-sweep['born']<=cfg.reclaim_bars and side*(c[i]-sweep['price'])>0:
                    offer('sweep',side,sweep['price'],sweep['born'],sweep_wick=sweep['wick'])
                    sweep['used']=True
            sweeps=[x for x in sweeps if i-x['born']<cfg.reclaim_bars and not x.get('used')]
            if trend and not pullback_used[trend] and np.isfinite(sh) and np.isfinite(sl):
                reference=sh if trend==1 else sl
                peak=max(h[max(0,i-10):i+1]) if trend==1 else min(l[max(0,i-10):i+1])
                wick=l[i] if trend==1 else h[i]
                depth=trend*(peak-wick)/a
                if cfg.pullback_min<=depth<=cfg.pullback_max and l[i]<=reference+tol and h[i]>=reference-tol and trend*(c[i]-o[i])>0:
                    row['pullback']=trend;row['pullback_level']=reference;pullback_used[trend]=True
            for side,pivots in [(1,lows),(-1,highs)]:
                if len(pivots)>=2:
                    (x0,y0),(x1,y1)=pivots[-2:]
                    slope=(y1-y0)/(x1-x0)
                    line=y1+slope*(i-x1)
                    if side*slope>0 and l[i]<=line+tol and h[i]>=line-tol and side*(c[i]-line)>0:
                        offer('line',side,line,x1)
            # Zones/gaps are created now but cannot be retested before a later bar.
            if i>=2:
                if l[i]>h[i-2]: gaps.append(dict(side=1,lo=h[i-2],hi=l[i],stop=l[i-1],born=i,used=False))
                if h[i]<l[i-2]: gaps.append(dict(side=-1,lo=h[i],hi=l[i-2],stop=h[i-1],born=i,used=False))
            length=cfg.impulse_bars
            if i>=length:
                start=i-length+1
                for side in [1,-1]:
                    if np.all(side*(c[start:i+1]-o[start:i+1])>0) and side*(c[i]-o[start])>=cfg.impulse_atr*a:
                        base=start-1
                        zones.append(dict(side=side,lo=l[base],hi=h[base],born=i,used=False))
            for collection,name in [(zones,'demand'),(gaps,'gap')]:
                for zone in collection:
                    side=zone['side']
                    valid=(i-zone['born']<=cfg.level_age and (c[i]>=zone['lo'] if side==1 else c[i]<=zone['hi']))
                    if not valid: zone['used']=True;continue
                    if name=='gap' and not zone['used']:
                        row['gap_active']=side # Latest side for diagnostics; flags retain both directions.
                        row['gap_active_long' if side==1 else 'gap_active_short']=True
                    if i>zone['born'] and not zone['used'] and l[i]<=zone['hi'] and h[i]>=zone['lo']:
                        offer(name,side,zone['lo'] if side==1 else zone['hi'],zone['born'],
                              **({'gap_stop':zone['stop']} if name=='gap' else {}))
                        zone['used']=True
            zones=[x for x in zones if not x['used']]
            gaps=[x for x in gaps if not x['used']]
        for name,candidates in offered.items():
            newest=max(x['born'] for x in candidates)
            current=[x for x in candidates if x['born']==newest]
            if len({x['side'] for x in current})>1: continue
            chosen=min(current,key=lambda x:abs(c[i]-x['level']))
            row[name]=chosen['side'];row[name+'_level']=chosen['level']
            for key in ['gap_stop','sweep_wick']:
                if key in chosen: row[key]=chosen[key]
        if observer is not None:
            # Scalars/immutable tuples only: an internal measurement observer
            # cannot mutate the detector's live containers or output row.
            observer(i,b.iloc[i].to_dict(),row.copy(),dict(
                levels=tuple((x['side'],float(x['price']),x['born']) for x in levels),
                flips=tuple((x['side'],float(x['price']),x['born']) for x in flips),
                zones=tuple((x['side'],float(x['lo']),float(x['hi']),x['born']) for x in zones if x['born']==i),
                gaps=tuple((x['side'],float(x['lo']),float(x['hi']),x['born']) for x in gaps if x['born']==i),
                highs=tuple(highs[-2:]),lows=tuple(lows[-2:])))
        records.append(row)
    return pd.concat([b,pd.DataFrame(records)],axis=1)

@dataclass(frozen=True)
class Signal:
    id: str
    symbol: str
    available_at: pd.Timestamp
    side: int
    level: float
    atr: float
    stop: float
    target_swing: float | None
    weight: float
    setup_at: pd.Timestamp
    source_index: int

    def json(self):
        value=asdict(self)
        for key in ['available_at','setup_at']: value[key]=value[key].isoformat()
        return value

_CANDIDATE_COLUMN = {
    'level_bounce': 'bounce', 'breakout': 'breakout', 'flip_zone': 'flip',
    'trend_pullback': 'pullback', 'trend_line': 'line', 'break_of_structure': 'bos',
    'change_of_character': 'choch', 'sweep_reclaim': 'sweep',
    'supply_demand': 'demand', 'fair_value_gap': 'gap',
}


def _candidate(row,cfg):
    name=_CANDIDATE_COLUMN[cfg.family];side=int(row[name])
    if not side: return None
    if name in {'bos','choch'}: level=row.swing_high if side==1 else row.swing_low
    else: level=row[name+'_level']
    return side,float(level)


def _candidate_rows(setup, configuration, cancel):
    atr = setup['atr'].to_numpy()
    sides = setup[_CANDIDATE_COLUMN[configuration.family]].to_numpy()
    eligible = np.isfinite(atr) & (atr > 0) & (sides != 0)
    # Keep the original cancellation cadence and source indexes, including
    # intervals that contain no candidate.
    for start in range(0, len(setup), 100):
        if cancel and cancel():
            raise InterruptedError('Signal calculation canceled.')
        for offset in np.flatnonzero(eligible[start:start + 100]):
            index = start + int(offset)
            yield index, setup.iloc[index]


def generate_signals(regular:pd.DataFrame,cfg:Strategy,news_dates:set|None=None,cancel=None,chart_provider=None,context_provider=None):
    if cfg.news!='trade' and news_dates is None: raise DataError('This news filter needs a versioned news calendar.')
    output=[]
    for symbol,minutes in regular.groupby('symbol',sort=True):
        if cancel and cancel(): raise InterruptedError('Signal calculation canceled.')
        charts={}
        def chart(tf):
            if tf not in charts:
                bars=chart_provider(symbol,tf) if chart_provider is not None else aggregate(minutes,tf)
                complete=bars[bars.complete].reset_index(drop=True)
                charts[tf]=contexts(complete,cfg,cancel) if context_provider is None else context_provider(symbol,tf,cfg,complete,cancel)
            return charts[tf]
        setup=chart(cfg.timeframe)
        trigger=chart(cfg.trigger)
        if setup.empty or trigger.empty: continue
        trigger_times=trigger.available_at.astype('int64').to_numpy()
        daily=chart('1d') if cfg.skip_run_days or cfg.trend_filter=='daily' else None
        higher=list(TIMEFRAMES)[min(list(TIMEFRAMES).index(cfg.timeframe)+1,5)]
        filter_chart=chart(higher) if cfg.trend_filter=='higher' else (daily if cfg.trend_filter=='daily' else setup)
        for i,row in _candidate_rows(setup,cfg,cancel):
            candidate=_candidate(row,cfg)
            if candidate is None: continue
            side,level=candidate
            if cfg.direction!='both' and side!=(1 if cfg.direction=='long' else -1): continue
            if cfg.sweep_required and not (setup.iloc[max(0,i-cfg.reclaim_bars):i+1]['sweep']==side).any(): continue
            if cfg.skip_choppy and row.efficiency<.3: continue
            if cfg.fresh_breakout and cfg.family=='flip_zone' and i and setup.iloc[i-1].breakout!=side: continue
            if cfg.gap_confluence and not row['gap_active_long' if side==1 else 'gap_active_short'] and row.gap!=side: continue
            if cfg.confirmation=='none': chosen=row
            else:
                start=int(np.searchsorted(trigger_times,row.available_at.value,side='left'))
                chosen=None
                for j in range(start,min(start+cfg.confirmation_window,len(trigger))):
                    current=trigger.iloc[j]
                    span=current.high-current.low
                    rejection=span>0 and ((min(current.open,current.close)-current.low)/span>=.5 if side==1 else (current.high-max(current.open,current.close))/span>=.5)
                    engulfing=j>0 and side*(current.close-current.open)>0 and min(current.open,current.close)<=min(trigger.iloc[j-1].open,trigger.iloc[j-1].close) and max(current.open,current.close)>=max(trigger.iloc[j-1].open,trigger.iloc[j-1].close)
                    ok={'close_back':side*(current.close-level)>0,'rejection':rejection,
                        'engulfing':engulfing,'either':rejection or engulfing,'lower_bos':current.bos==side}[cfg.confirmation]
                    if ok: chosen=current;break
                if chosen is None: continue
            when=chosen.available_at
            local=when.tz_convert('America/New_York')
            if cfg.session_filter=='open' and not (9*60+30<=local.hour*60+local.minute<11*60): continue
            day=local.date().isoformat()
            weight=news_weight(cfg.news,news_dates,when)
            if weight==0: continue
            if cfg.trend_filter!='none':
                allowed=filter_chart[filter_chart.available_at<=when]
                if allowed.empty or allowed.iloc[-1].trend!=side: continue
            if cfg.skip_run_days:
                known=daily[daily.available_at<=when]
                offset=cfg.skip_run_days+(1 if len(known) and known.iloc[-1].session==day else 0)
                if len(known)<offset: continue
                if side*(chosen.close-known.iloc[-offset].close)>0: continue
            reference={'swing':row.swing_low if side==1 else row.swing_high,
                       'level':level,'wick':row.low if side==1 else row.high,'gap':row.gap_stop}[cfg.stop_reference]
            stop=reference-side*cfg.stop_buffer*row.atr
            target=row.swing_high if side==1 else row.swing_low
            if not np.isfinite(stop): continue
            sig_id=identity(dict(symbol=symbol,setup_at=row.available_at.isoformat(),side=side,config=cfg.model_dump()))[:24]
            output.append(Signal(sig_id,symbol,when,side,level,float(row.atr),float(stop),
                                 float(target) if np.isfinite(target) else None,
                                 weight,
                                 row.available_at,int(i)))
    return sorted(output,key=lambda s:(s.available_at,s.symbol,s.id))
