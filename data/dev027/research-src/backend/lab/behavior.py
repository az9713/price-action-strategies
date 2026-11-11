"""Causal feature lifetimes and retrospective, explicitly censored behavior tests.

These are price measurements, not fills or tradable strategy accounts. Detector
snapshots are consumed after each close; future bars are used only for scoring.
"""
from decimal import Decimal
from datetime import date,timedelta
import math
import json
import numpy as np
import pandas as pd

from .config import Strategy,identity
from .data import aggregate,DataError
from .signals import contexts,Signal
from .controls import make_control_plan

TABLES={
    'levels_vs_shifted':'Confirmed levels versus shifted stand-ins',
    'touch_count':'Hold fraction by qualifying visit count',
    'wall_target':'Repeated levels as walls and through-movement proxies',
    'shrinking_bounces':'Change in successive full-horizon favorable excursions',
    'line_vs_zone':'Point line versus tolerance box',
    'wick_vs_close':'Forward movement after wick penetration or close-through',
    'flip_zones':'Broken levels returning from the new side',
    'bos_forward':'Break-of-structure forward movement',
    'choch_forward':'Change-of-character forward movement',
    'sweep_vs_close':'Reclaim direction after sweeps versus penetration direction after close-through',
    'sweep_started_trends':'Structure breaks with versus without a recent same-side reclaim',
    'trend_lines':'Confirmed-anchor trend-line touches',
    'gap_hold_fill':'Fair-value-gap hold and full-fill measurements',
    'supply_demand_returns':'Supply/demand first versus later qualifying visits',
    'pullback_depth':'Forward movement by prior-ATR pullback depth',
    'engulfing_at_levels':'Directional engulfing candles at confirmed levels',
    'rejection_at_levels':'Rejection wicks at confirmed levels'}
HORIZONS=(10,20,50)
MAX_EVENTS=250000
D=lambda value:value if isinstance(value,Decimal) else Decimal(str(value))


def _validate(rows,index,lo,hi,side,atr,horizon):
    if not 0<=index<len(rows) or side not in {-1,1} or not np.isfinite([lo,hi,atr]).all() or lo>hi or atr<=0:
        raise DataError('Invalid behavior event geometry or observation index.')
    if not isinstance(horizon,int) or isinstance(horizon,bool) or not 1<=horizon<=500:
        raise DataError('Behavior horizon must be one to500 completed bars.')


def score_touch(rows,index,lo,hi,side,atr,horizon=50):
    _validate(rows,index,lo,hi,side,atr,horizon)
    near=D(hi if side==1 else lo);far=D(lo if side==1 else hi);a=D(atr)
    following=rows[index+1:index+1+horizon];complete=len(following)==horizon
    observed='unresolved';resolved=None
    if side*(D(rows[index]['close'])-far)<-a/4:observed='break';resolved=0
    for offset,row in enumerate(following,1):
        if observed!='unresolved':break
        favorable=D(row['high'] if side==1 else row['low'])
        if side*(favorable-near)>=a:observed='hold';resolved=offset
        elif side*(D(row['close'])-far)<-a/4:observed='break';resolved=offset
    favorable=[float(side*(D(row['high'] if side==1 else row['low'])-near)/a) for row in following]
    adverse=[float(-side*(D(row['low'] if side==1 else row['high'])-far)/a) for row in following]
    return dict(outcome=observed if complete else 'censored',observed_outcome=observed,
        complete_horizon=complete,resolved_after_bars=resolved,followup_bars=len(following),
        max_favorable_atr=max([0.,*favorable]),max_adverse_atr=max([0.,*adverse]),
        forward_move_atr=float(side*(D(following[-1]['close'])-D(rows[index]['close']))/a) if complete else None)


def score_gap_fill(rows,index,lo,hi,side,horizon=50):
    _validate(rows,index,lo,hi,side,1,horizon)
    far=D(lo if side==1 else hi);following=rows[index+1:index+1+horizon]
    filled=side*(D(rows[index]['close'])-far)<=0;when=0 if filled else None
    for offset,row in enumerate(following,1):
        if not filled and side*(D(row['low'] if side==1 else row['high'])-far)<=0:filled=True;when=offset
    return dict(filled=filled if len(following)==horizon else None,observed_fill=filled,
                complete_horizon=len(following)==horizon,filled_after_bars=when)


def choose_shift(feature,known_intervals,seed,replica):
    if not np.isfinite([feature['lo'],feature['hi'],feature['atr']]).all() or feature['lo']>feature['hi'] or feature['atr']<=0:
        raise DataError('Invalid shifted-feature birth geometry.')
    a=D(feature['atr'])
    for attempt in range(128):
        digest=identity(dict(seed=seed,feature=feature['id'],replica=replica,attempt=attempt,policy=1))
        value=int(digest,16);offset=(D(1)+D(value%1000001)/D(500000))*a*(1 if (value>>24)&1 else -1)
        lo=D(feature['lo'])+offset;hi=D(feature['hi'])+offset
        if lo<=0:continue
        if all(max(D(left)-hi,lo-D(right),D(0))>=a/2 for left,right in known_intervals):
            return dict(offset=float(offset),attempts=attempt+1,stream_key=digest)
    return None


def session_contrast(records,sessions,seed=42,resamples=2000):
    if len(set(sessions))!=len(sessions) or not sessions:raise DataError('Behavior bootstrap needs distinct declared sessions.')
    if not isinstance(resamples,int) or not 2<=resamples<=100000:raise DataError('Invalid behavior resample count.')
    position={day:i for i,day in enumerate(sessions)};matrix=np.zeros((len(sessions),4))
    for row in records:
        if row['session'] not in position or row['group'] not in {'real','control'} or not math.isfinite(row['value']):
            raise DataError('Invalid behavior bootstrap observation.')
        column=0 if row['group']=='real' else 2
        matrix[position[row['session']],column]+=row['value'];matrix[position[row['session']],column+1]+=1
    total=matrix.sum(axis=0);real=float(total[0]/total[1]) if total[1] else None
    control=float(total[2]/total[3]) if total[3] else None
    difference=None if real is None or control is None else real-control
    valid=0;values=[];rng=np.random.default_rng(seed)
    attempted=resamples if difference is not None and len(sessions)>=2 else 0
    if attempted:
        for begin in range(0,resamples,128):
            draws=rng.integers(0,len(sessions),size=(min(128,resamples-begin),len(sessions)))
            sums=matrix[draws].sum(axis=1);mask=(sums[:,1]>0)&(sums[:,3]>0)
            values.extend((sums[mask,0]/sums[mask,1]-sums[mask,2]/sums[mask,3]).tolist());valid+=int(mask.sum())
    interval=None
    if valid==resamples:
        interval=dict(low=float(np.quantile(values,.025)),high=float(np.quantile(values,.975)),
                      method='IID whole sessions; paired real/control session draws',resamples=resamples,seed=seed)
    return dict(real_mean=real,control_mean=control,difference=difference,real_n=int(total[1]),control_n=int(total[3]),
                valid_resamples=valid,resamples=resamples,attempted_resamples=attempted,interval=interval)


def _forward(rows,index,side,atr,horizon):
    complete=index+horizon<len(rows)
    return dict(complete_horizon=complete,value=float(side*(D(rows[index+horizon]['close'])-D(rows[index]['close']))/D(atr)) if complete else None)


def analyze_chart(regular,timeframe,start,end,seed=42,replicas=20,cancel=None):
    if not isinstance(replicas,int) or isinstance(replicas,bool) or not 2<=replicas<=20:raise DataError('Choose two to20 shifted replicas.')
    regular=regular[regular.session<=end]
    cfg=Strategy(family='trend_pullback',timeframe=timeframe,swing_strength=3,level_tolerance=.25,pullback_max=10)
    touches=[];features=[];moments=[];fills=[];charts={};unshiftable=[];moment_pairs=[];moment_assessments=[];moment_plans=[];updates=[];superseded=[]
    sessions=sorted(regular[regular.session.between(start,end)].session.unique())
    def check():
        if cancel and cancel():raise InterruptedError('Behavior analysis canceled.')
        if len(touches)+len(moments)+len(fills)+len(moment_pairs)+len(moment_assessments)>MAX_EVENTS:raise DataError('Behavior chart exceeds250000 measurement records; reduce the date window.')
    for symbol,minutes in regular.groupby('symbol',sort=True):
        check();bars=aggregate(minutes,timeframe);bars=bars[bars.complete].reset_index(drop=True)
        if bars.empty:continue
        # This input ends at the guarded evaluation end. Future scoring cannot
        # read past that end or relabel a short path as fully observed.
        rows=bars.to_dict('records');active={};seen=set();moment_map={};latest_line={};atr_values={};known_sweeps=[]
        def emit(kind,index,side,atr,**facts):
            if not start<=rows[index]['session']<=end:return
            key=(kind,index,side)
            item=dict(id=identity(dict(symbol=symbol,timeframe=timeframe,kind=kind,at=rows[index]['available_at'].isoformat(),side=side))[:24],
                kind=kind,symbol=symbol,timeframe=timeframe,index=index,side=side,atr=float(atr),
                available_at=rows[index]['available_at'].isoformat(),session=rows[index]['session'],**facts)
            old=moment_map.get(key)
            if old is None or facts.get('feature_born',-1)>old.get('feature_born',-1):moment_map[key]=item
        def observe(index,bar,row,state):
            check();a=row['atr'];atr_values[index]=a
            if not np.isfinite(a) or a<=0:return
            c=float(bar['close']);h=float(bar['high']);l=float(bar['low']);previous=rows[index-1] if index else bar
            for fid,f in list(active.items()):
                if index>f['expires'] or not any(any(v['alive'].values()) for v in f['variants']):active.pop(fid,None);continue
                base_lo=f['lo']+f['slope']*(index-f['reference_index']);base_hi=f['hi']+f['slope']*(index-f['reference_index'])
                pad=.25*a if f['kind']=='level' else 0
                if f['side']==1 and l>base_hi+pad+f['max_offset']:continue
                if f['side']==-1 and h<base_lo-pad+f['min_offset']:continue
                for variant in f['variants']:
                    for shape in (['line','zone'] if f['kind']=='level' else ['line'] if f['kind']=='trend_line' else ['zone']):
                        if not variant['alive'][shape]:continue
                        lo=base_lo+variant['offset']-(pad if shape=='zone' else 0);hi=base_hi+variant['offset']+(pad if shape=='zone' else 0)
                        near=hi if f['side']==1 else lo;far=lo if f['side']==1 else hi
                        prior_side=f['side']*(float(previous['close'])-near)>=0
                        hit=l<=hi and h>=lo;visit=variant['visits'].setdefault(shape,dict(last=-2,count=0))
                        if variant['group']=='real' and f['kind']=='level' and shape=='line' and prior_side:
                            if f['side']*(c-near)<0:emit('close_break',index,-f['side'],a,feature_born=f['born'])
                            elif f['side']*((l if f['side']==1 else h)-near)<0:emit('wick_break',index,-f['side'],a,feature_born=f['born'])
                        if hit:
                            if visit['last']<index-1 and prior_side:
                                visit['count']+=1
                                if start<=bar['session']<=end:
                                    result=score_touch(rows,index,lo,hi,f['side'],a)
                                    touches.append(dict(id=identity(dict(feature=fid,group=variant['group'],replica=variant['replica'],shape=shape,index=index))[:24],
                                        feature_id=fid,kind=f['kind'],shape=shape,symbol=symbol,timeframe=timeframe,
                                        group=variant['group'],replica=variant['replica'],matchable=f['matchable'],
                                        session=bar['session'],available_at=bar['available_at'].isoformat(),index=index,
                                        side=f['side'],lo=lo,hi=hi,atr=float(a),visit=visit['count'],**result))
                                    if variant['group']=='real' and f['kind']=='level' and shape=='zone':
                                        span=h-l;side=f['side']
                                        rejection=span>0 and ((min(bar['open'],c)-l)/span>=.5 if side==1 else (h-max(bar['open'],c))/span>=.5)
                                        engulf=side*(c-bar['open'])>0 and min(bar['open'],c)<=min(previous['open'],previous['close']) and max(bar['open'],c)>=max(previous['open'],previous['close'])
                                        if rejection:emit('rejection',index,side,a,feature_born=f['born'])
                                        if engulf:emit('engulfing',index,side,a,feature_born=f['born'])
                            visit['last']=index
                        # Each geometry has its own close invalidation after
                        # measuring this candle; line/box lifetimes can differ.
                        if D(f['side'])*(D(c)-D(far))<-D(a)/4:variant['alive'][shape]=False
            births=[]
            def add(kind,key,side,lo,hi,born,age,slope=0.):
                fid=identity(dict(kind=kind,key=key,symbol=symbol,timeframe=timeframe))[:24]
                if fid in seen:
                    if fid in active and kind=='level':
                        if active[fid]['lo']!=lo or active[fid]['hi']!=hi:
                            updates.append(dict(feature_id=fid,index=index,known_at=bar['available_at'].isoformat(),lo=float(lo),hi=float(hi)))
                        active[fid].update(lo=lo,hi=hi,reference_index=index)
                    return fid
                seen.add(fid)
                births.append(dict(id=fid,kind=kind,side=side,lo=float(lo),hi=float(hi),born=index,source_born=born,
                    expires=index+age,reference_index=index,slope=float(slope),atr=float(a),symbol=symbol,timeframe=timeframe,
                    available_at=bar['available_at'].isoformat(),session=bar['session'],origin_key=key,source_born_at=rows[born]['available_at'].isoformat()))
                return fid
            stamp=lambda j:rows[j]['available_at'].isoformat()
            for side,price,born in state['levels']:add('level',(side,stamp(born)),-side,price,price,born,max(0,96-(index-born)))
            for side,price,born in state['flips']:add('flip',(side,stamp(born),price),side,price-.25*a,price+.25*a,born,max(0,24-(index-born)))
            for source,kind in [('zones','supply_demand'),('gaps','gap')]:
                for side,lo,hi,born in state[source]:add(kind,(side,stamp(born),lo,hi),side,lo,hi,born,96)
            for side,anchors in [(1,state['lows']),(-1,state['highs'])]:
                if len(anchors)<2:continue
                (x0,y0),(x1,y1)=anchors;slope=(y1-y0)/(x1-x0)
                if side*slope<=0:continue
                price=y1+slope*(index-x1);fid=add('trend_line',(side,stamp(x0),stamp(x1)),side,price,price,x1,96,slope)
                if latest_line.get(side)!=fid:
                    if side in latest_line:
                        superseded.append(dict(feature_id=latest_line[side],index=index,known_at=bar['available_at'].isoformat(),replacement=fid))
                        active.pop(latest_line[side],None)
                    latest_line[side]=fid
            known=[(price-.25*a,price+.25*a) for _,price,_ in state['levels']]
            known += [(f['lo']+f['slope']*(index-f['reference_index']),f['hi']+f['slope']*(index-f['reference_index'])) for f in active.values()]
            known += [(f['lo'],f['hi']) for f in births]
            for f in births:
                screen=f|dict(lo=f['lo']-(.25*a if f['kind']=='level' else 0),hi=f['hi']+(.25*a if f['kind']=='level' else 0))
                shifts=[choose_shift(screen,known,seed,replica) for replica in range(replicas)]
                f['matchable']=all(x is not None for x in shifts)
                if not f['matchable']:unshiftable.append(dict(feature_id=f['id'],reason='No admissible birth-time shift for every requested replica.',symbol=symbol,timeframe=timeframe))
                f['shift_draws']=shifts
                f['screening_intervals']=[list(interval) for interval in known]
                variants=[dict(group='real',replica=None,offset=0.)]
                if f['matchable']:variants += [dict(group='control',replica=i,offset=x['offset']) for i,x in enumerate(shifts)]
                shapes=['line','zone'] if f['kind']=='level' else ['line'] if f['kind']=='trend_line' else ['zone']
                for variant in variants:
                    alive={}
                    for shape in shapes:
                        pad=.25*a if f['kind']=='level' and shape=='zone' else 0
                        far=f['lo']-pad+variant['offset'] if f['side']==1 else f['hi']+pad+variant['offset']
                        alive[shape]=D(f['side'])*(D(c)-D(far))>=-D(a)/4
                    variant.update(alive=alive,visits={})
                f['birth_states']=[dict(group=v['group'],replica=v['replica'],alive=v['alive'].copy()) for v in variants]
                features.append({k:v for k,v in f.items()})
                f['variants']=variants;f['min_offset']=min(v['offset'] for v in variants);f['max_offset']=max(v['offset'] for v in variants)
                active[f['id']]=f
                if f['kind']=='gap' and start<=bar['session']<=end:
                    for variant in variants:
                        result=score_gap_fill(rows,index,f['lo']+variant['offset'],f['hi']+variant['offset'],f['side'])
                        fills.append(dict(feature_id=f['id'],kind='gap_fill',symbol=symbol,timeframe=timeframe,session=bar['session'],
                            index=index,available_at=bar['available_at'].isoformat(),side=f['side'],lo=f['lo']+variant['offset'],hi=f['hi']+variant['offset'],
                            group=variant['group'],replica=variant['replica'],matchable=f['matchable'],**result))
            if row['sweep']:known_sweeps.append((index,int(row['sweep'])))
            for name,kind in [('bos','bos'),('choch','choch'),('sweep','sweep'),('pullback','pullback')]:
                side=int(row[name])
                if not side:continue
                facts={}
                if kind in {'bos','choch'}:
                    facts['recent_sweep']=any(s==side and 0<=index-j<=3 for j,s in known_sweeps[-12:])
                if kind=='pullback':
                    peak=max(float(x['high']) for x in rows[max(0,index-10):index+1]) if side==1 else min(float(x['low']) for x in rows[max(0,index-10):index+1])
                    facts['depth_atr']=float(side*(peak-(l if side==1 else h))/a)
                emit(kind,index,side,a,**facts)
        context=contexts(bars,cfg,cancel,observe)
        real_moments=sorted(moment_map.values(),key=lambda x:(x['index'],x['kind'],x['side']));moments.extend(real_moments)
        feature_rows=[dict(symbol=symbol,available_at=bar['available_at'].isoformat(),close=float(bar['close']),atr=float(atr_values.get(i,np.nan)),duration_minutes=int(bar['duration_minutes']))
            for i,bar in enumerate(rows) if np.isfinite(atr_values.get(i,np.nan)) and atr_values[i]>0]
        at_index={bar['available_at'].isoformat():i for i,bar in enumerate(rows)}
        for kind in sorted({event['kind'] for event in real_moments}):
            for horizon in HORIZONS:
                check();eligible=[e for e in real_moments if e['kind']==kind and e['index']+horizon<len(rows)]
                all_sources=[e for e in real_moments if e['kind']==kind]
                if not eligible:
                    moment_assessments.extend(dict(**e,horizon=horizon,group='real',matchable=False,complete_horizon=False,value=None,status='censored') for e in all_sources)
                    continue
                controls_cfg=Strategy(timeframe=timeframe,target='2R')
                signals=[Signal(e['id'],symbol,pd.Timestamp(e['available_at']),e['side'],float(rows[e['index']]['close']),e['atr'],
                    float(rows[e['index']]['close'])-e['side']*e['atr'],None,1.,pd.Timestamp(e['available_at']),e['index']) for e in eligible]
                pool=[r for r in feature_rows if at_index[r['available_at']]+horizon<len(rows)]
                sub_seed=int(identity(dict(seed=seed,timeframe=timeframe,symbol=symbol,kind=kind,horizon=horizon))[:8],16)%(2**31)
                plan=make_control_plan(pool,signals,controls_cfg,start,end,sub_seed,replicas,cancel)
                matched=set(plan['matched_source_ids'])
                for event in all_sources:
                    measure=_forward(rows,event['index'],event['side'],event['atr'],horizon)
                    moment_assessments.append(dict(**event,**measure,horizon=horizon,group='real',matchable=event['id'] in matched,
                        status='matched' if event['id'] in matched else 'censored' if not measure['complete_horizon'] else 'unmatched'))
                moment_plans.append(dict(kind=kind,horizon=horizon,seed=sub_seed,source_count=plan['source_count'],
                    matched_source_ids=plan['matched_source_ids'],unmatched=plan['unmatched'],
                    replicas=[dict(replica=r['replica'],stream_key=r['stream_key'],matches=[dict(source_id=m['source_id'],candidate_key=m['candidate_key'],matching=m['matching']) for m in r['matches']]) for r in plan['replicas']]))
                by_id={e['id']:e for e in eligible}
                for source_id in plan['matched_source_ids']:
                    event=by_id[source_id];value=_forward(rows,event['index'],event['side'],event['atr'],horizon)['value']
                    moment_pairs.append(dict(**event,group='real',horizon=horizon,value=value,replica=None))
                for replica in plan['replicas']:
                    for match in replica['matches']:
                        event=by_id[match['source_id']];control=match['signal'];i=at_index[control['available_at']]
                        moment_pairs.append(dict(**{k:v for k,v in event.items() if k not in {'session','available_at','index','atr'}},
                            session=rows[i]['session'],available_at=control['available_at'],index=i,atr=control['atr'],
                            group='control',replica=replica['replica'],horizon=horizon,value=_forward(rows,i,event['side'],control['atr'],horizon)['value']))
        chart=context[context.session.between(start,end)]
        charts[symbol]=json.loads(chart[['timestamp','available_at','open','high','low','close','volume','factor','complete']].to_json(orient='records',date_format='iso'))
    check()
    return dict(timeframe=timeframe,bars=charts,touches=touches,features=features,moments=moments,
                moment_pairs=moment_pairs,moment_assessments=moment_assessments,moment_plans=moment_plans,
                gap_fills=fills,unshiftable=unshiftable,feature_updates=updates,superseded_lines=superseded,sessions=sessions)


def build_tables(charts,start,end,seed=42,cancel=None):
    """Event-weighted marginal groups, with complete session denominators."""
    observations={key:[] for key in TABLES};sessions=sorted({d for chart in charts for d in chart['sessions']})
    split=(date.fromisoformat(start)+timedelta(days=((date.fromisoformat(end)-date.fromisoformat(start)).days+1)//2)).isoformat()
    def add(table,item,value,metric,category='all',horizon=50):
        observations[table].append(dict(session=item['session'],symbol=item['symbol'],timeframe=item['timeframe'],
            group=item['group'],value=value,metric=metric,category=category,horizon=horizon,
            complete=bool(item['complete_horizon']),matchable=item.get('matchable',True),
            unresolved=item.get('outcome')=='unresolved'))
        if metric in {'hold_fraction','wall_hold_fraction'}:
            add(table,item,None if item.get('outcome')=='unresolved' else value,metric+'_resolved_only',category,horizon)
    previous={}
    for chart in charts:
        for item in chart['touches']:
            if cancel and cancel():raise InterruptedError('Behavior tables canceled.')
            value=float(item['outcome']=='hold') if item['complete_horizon'] else None
            kind=item['kind'];shape=item['shape'];visit=item['visit'];bucket=str(visit) if visit<4 else '4+'
            if kind=='level':
                if shape=='line':
                    add('levels_vs_shifted',item,value,'hold_fraction')
                    add('touch_count',item,value,'hold_fraction',bucket)
                    add('wall_target',item,value,'wall_hold_fraction',bucket)
                    add('wall_target',item,item['max_adverse_atr'] if item['complete_horizon'] else None,'through_excursion_ATR',bucket)
                    key=(item['feature_id'],item['group'],item['replica'],shape)
                    older=previous.get(key)
                    if older and older['visit']==visit-1 and older['complete_horizon'] and item['complete_horizon']:
                        add('shrinking_bounces',item,item['max_favorable_atr']-older['max_favorable_atr'],'successive_excursion_change_ATR',bucket)
                    previous[key]=item
                add('line_vs_zone',item,value,'hold_fraction',shape)
            elif kind=='flip':add('flip_zones',item,value,'hold_fraction')
            elif kind=='trend_line':add('trend_lines',item,value,'hold_fraction')
            elif kind=='gap':add('gap_hold_fill',item,value,'hold_fraction')
            elif kind=='supply_demand':add('supply_demand_returns',item,value,'hold_fraction','first' if visit==1 else 'later')
        for item in chart['gap_fills']:add('gap_hold_fill',item,None if item['filled'] is None else float(item['filled']),'full_fill_fraction')
        forward_rows=chart['moment_pairs']+[x for x in chart.get('moment_assessments',[]) if x['status']!='matched']
        for item in forward_rows:
            kind=item['kind'];value=item['value'];horizon=item['horizon'];item=item|dict(complete_horizon=item.get('complete_horizon',True))
            if kind in {'wick_break','close_break'}:add('wick_vs_close',item,value,'forward_close_move_ATR',kind,horizon)
            if kind=='bos':add('bos_forward',item,value,'forward_close_move_ATR','all',horizon)
            if kind=='choch':add('choch_forward',item,value,'forward_close_move_ATR','all',horizon)
            if kind in {'sweep','close_break'}:add('sweep_vs_close',item,value,'forward_close_move_ATR',kind,horizon)
            if kind in {'bos','choch'}:add('sweep_started_trends',item,value,'forward_close_move_ATR','recent sweep' if item.get('recent_sweep') else 'no recent sweep',horizon)
            if kind=='pullback':
                depth=item['depth_atr'];bucket='<1' if depth<1 else '1–2' if depth<2 else '2–3' if depth<3 else '3+'
                add('pullback_depth',item,value,'forward_close_move_ATR',bucket,horizon)
            if kind=='engulfing':add('engulfing_at_levels',item,value,'forward_close_move_ATR','all',horizon)
            if kind=='rejection':add('rejection_at_levels',item,value,'forward_close_move_ATR','all',horizon)
    tables={}
    for table,items in observations.items():
        groups={}
        for item in items:
            era='early' if item['session']<split else 'late'
            for scope,subset in [('pooled','All instruments/charts'),('timeframe',item['timeframe']),('instrument',item['symbol']),('era',era)]:
                key=(scope,subset,item['metric'],item['category'],item['horizon']);groups.setdefault(key,[]).append(item)
        output=[]
        for key,group in sorted(groups.items()):
            if cancel and cancel():raise InterruptedError('Behavior uncertainty canceled.')
            scope,subset,metric,category,horizon=key
            used=[dict(session=x['session'],group=x['group'],value=x['value']) for x in group if x['complete'] and x['matchable'] and x['value'] is not None]
            eligible_sessions=[d for d in sessions if scope!='era' or ('early' if d<split else 'late')==subset]
            if not eligible_sessions:continue
            row_seed=int(identity(dict(seed=seed,table=table,key=key))[:8],16)%(2**31)
            result=session_contrast(used,eligible_sessions,row_seed)
            interval=result.pop('interval')
            status='insufficient comparison' if result['difference'] is None else 'descriptive difference; interval unavailable'
            if interval:status='interval includes zero' if interval['low']<=0<=interval['high'] else 'descriptive positive difference' if interval['low']>0 else 'descriptive negative difference'
            output.append(dict(scope=scope,subset=subset,metric=metric,category=category,horizon=horizon,
                unit='ATR' if 'ATR' in metric else 'fraction',**result,seed=row_seed,
                interval_low=None if interval is None else interval['low'],interval_high=None if interval is None else interval['high'],
                real_censored=sum(x['group']=='real' and not x['complete'] for x in group),
                control_censored=sum(x['group']=='control' and not x['complete'] for x in group),
                real_unresolved=sum(x['group']=='real' and x['unresolved'] for x in group),
                control_unresolved=sum(x['group']=='control' and x['unresolved'] for x in group),
                real_full_sample_n=sum(x['group']=='real' and x['complete'] for x in group),status=status))
        if not output:
            output=[dict(scope='pooled',subset='All instruments/charts',metric='not_observed',category='all',horizon=None,unit=None,
                real_mean=None,control_mean=None,difference=None,real_n=0,control_n=0,valid_resamples=0,resamples=2000,attempted_resamples=0,
                seed=seed,interval_low=None,interval_high=None,real_censored=0,control_censored=0,real_unresolved=0,control_unresolved=0,
                real_full_sample_n=0,status='insufficient comparison')]
        tables[table]=dict(title=TABLES[table],rows=output,verdict='Descriptive price evidence only; no universal true/false or trading-profit claim.')
    return tables,split
