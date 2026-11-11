"""Deliberately slow, independent Decimal execution/accounting oracle.

No production imports, pandas, NumPy, detector, sizing, quote or ledger helpers.
Inputs are primitive records. This models supplied signals; strategy detectors
need their own independently authored fixtures. Share sizing enumerates feasible
integers rather than using the production engine's adjustment algorithm.
"""
from collections import defaultdict
from datetime import datetime,timedelta
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR,localcontext

D=lambda value:Decimal(str(value))
ZERO=D(0)
MINUTE=timedelta(minutes=1)

def stamp(value):
    return datetime.fromisoformat(str(value))

def chart_closures(bars,minutes):
    """Independently assemble complete session-anchored candles."""
    groups=defaultdict(list)
    for bar in bars:
        start=stamp(bar['session_open']);ts=stamp(bar['timestamp'])
        bucket=int((ts-start).total_seconds()//60)//minutes
        groups[(bar['symbol'],bar['session'],bucket)].append(bar)
    out=defaultdict(list)
    for (symbol,day,bucket),items in sorted(groups.items()):
        items.sort(key=lambda b:stamp(b['timestamp']))
        start=stamp(items[0]['session_open'])+timedelta(minutes=bucket*minutes)
        end=min(start+timedelta(minutes=minutes),stamp(items[0]['session_close']))
        if len(items)!=int((end-start).total_seconds()/60): continue
        if any(stamp(item['timestamp'])!=start+i*MINUTE for i,item in enumerate(items)): continue
        factors=[D(x.get('factor',1)) for x in items]
        out[symbol].append({'at':end,'high':max(D(x['high'])*f for x,f in zip(items,factors)),
            'low':min(D(x['low'])*f for x,f in zip(items,factors)),'close':D(items[-1]['close'])*factors[-1]})
    for rows in out.values(): rows.sort(key=lambda r:r['at'])
    return out

def reversal_events(candles,strength):
    """Plain strict-pivot structural reversal reference, independently evaluated."""
    peaks=[];troughs=[];used=set();direction=0;events={}
    for current in range(len(candles)):
        center=current-strength
        if center>=strength:
            window=candles[center-strength:current+1]
            for field,target,mode in [('high',peaks,max),('low',troughs,min)]:
                value=candles[center][field]
                if value==mode(x[field] for x in window) and sum(x[field]==value for x in window)==1:
                    target.append((center,value))
            if direction==0 and len(peaks)>=2 and len(troughs)>=2:
                if peaks[-1][1]>peaks[-2][1] and troughs[-1][1]>troughs[-2][1]: direction=1
                elif peaks[-1][1]<peaks[-2][1] and troughs[-1][1]<troughs[-2][1]: direction=-1
        previous=direction
        for side,points in [(1,peaks),(-1,troughs)]:
            if not points: continue
            pivot,value=points[-1]
            if side*(candles[current]['close']-value)>0 and (side,pivot) not in used:
                used.add((side,pivot))
                if previous==-side: events[candles[current]['at']]=side;direction=side
    return events

def execute(bars,signals,configurations,costs,account,actions=(),start=None,end=None):
    with localcontext() as ctx:
        ctx.prec=40
        return _execute(bars,signals,configurations,costs,account,actions,start,end)

def _execute(bars,signals,configurations,costs,account,actions,start,end):
    frames={'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':390}
    bars=sorted(bars,key=lambda b:(stamp(b['timestamp']),b['symbol']))
    eligible=[b for b in bars if (not start or b['session']>=start) and (not end or b['session']<=end)]
    if not eligible: raise ValueError('Reference needs execution observations.')
    tick=D(account['tick_size']);capital=D(account['capital']);cash=capital
    cost={k:D(v) for k,v in costs.items() if k not in {'borrow_available','borrow_scenario'}}
    lending=costs.get('borrow_scenario')
    lending_events=sorted(lending['events'],key=lambda e:stamp(e['effective_at'])) if lending else []
    def lending_state(symbol,at):
        state=(costs['borrow_available'],cost['borrow_annual'],False)
        for event in lending_events:
            if event['symbol']==symbol and stamp(event['effective_at'])<=at:
                state=(event['available'],D(event['annual_rate']),event['recall'])
        return state
    risk_fraction=D(account['risk_fraction']);symbol_cap=D(account['symbol_exposure']);gross_cap=D(account['total_exposure'])
    participation=D(account['participation'])
    def grid(value,buy): return (value/tick).to_integral_value(rounding=ROUND_CEILING if buy else ROUND_FLOOR)*tick
    def quote(value,side,stop=False):
        value=D(value)*(1+D(side)*(cost['slippage_bps']+cost['spread_bps']/2)/D(10000))
        if stop: value+=D(side)*tick
        value=grid(value,side>0)
        if value<=0: raise ValueError('Reference modeled a nonpositive execution price.')
        return value
    def fee(qty,price,side):
        return max(cost['minimum_commission'],qty*cost['commission_per_share'])+cost['fixed_fee_per_order']+(qty*price*cost['sell_fee_per_dollar'] if side<0 else ZERO)

    endings={};reversals={};triggers={}
    for config_id,cfg in configurations.items():
        candles=chart_closures(bars,frames[cfg['timeframe']])
        trigger=cfg.get('trigger_timeframe') or ('1h' if cfg['timeframe']=='1d' else cfg['timeframe'])
        lower=chart_closures(bars,frames[trigger])
        for symbol in {b['symbol'] for b in bars}:
            endings[(symbol,config_id)]=[c['at'] for c in candles[symbol]]
            triggers[(symbol,config_id)]={c['at'] for c in lower[symbol]}
            reversals[(symbol,config_id)]=reversal_events(candles[symbol],cfg['swing_strength']) if cfg['structure_exit'] else {}
    by_time=defaultdict(dict)
    for bar in eligible: by_time[stamp(bar['timestamp'])][bar['symbol']]=bar
    first=min(by_time);final=max(by_time)
    def priority(signal): return stamp(signal['available_at']),signal['symbol'],signal['config_id'],signal['id']
    awaiting=sorted([dict(s) for s in signals if stamp(s['available_at'])>=first],key=priority)
    pending=[];positions={};marks={};previous_volume={};previous_sample={};entry_history=[];receivables=[]
    result={'trades':[],'ledger':[],'equity':[],'rejected':[]}
    seen_actions=set();last_rows={}

    def equity():
        return cash+sum(p['side']*p['qty']*marks[p['symbol']] for p in positions.values())+sum(r['amount'] for r in receivables)
    def transaction(kind,cash_delta,when,**fields):
        nonlocal cash
        before=cash;cash+=cash_delta
        result['ledger'].append({'timestamp':when.isoformat(),'kind':kind,'cash_before':before,'cash_change':cash_delta,'cash_after':cash,**fields})
    def borrow(position,when):
        if when<=position['accrued_at']: return
        if position['side']<0:
            since=position['accrued_at']
            cuts=[since]+[stamp(e['effective_at']) for e in lending_events if e['symbol']==position['symbol'] and since<stamp(e['effective_at'])<when]+[when]
            annual_seconds=sum((lending_state(position['symbol'],left)[1]*D(str((right-left).total_seconds())) for left,right in zip(cuts,cuts[1:])),ZERO)
            charge=position['qty']*position['borrow_mark']*annual_seconds/D(365*86400)
            position['borrow']+=charge
            if charge: transaction('borrow',-charge,when,trade_id=position['id'],symbol=position['symbol'])
        position['accrued_at']=when
    def exit_position(key,base,why,when,limited=False,stopped=False):
        p=positions[key];borrow(p,when)
        price=D(base) if limited else quote(base,-p['side'],stopped)
        charge=fee(p['qty'],price,-p['side'])
        transaction('exit',p['side']*p['qty']*price-charge,when,trade_id=p['id'],symbol=p['symbol'],quantity=p['qty'],price=price,fee=charge,reason=why)
        price_pnl=p['side']*p['qty']*(price-p['basis'])
        net=price_pnl+p['distributions']-p['borrow']-p['fees']-charge
        reference_risk=abs(p['basis']-p['stop'])*p['qty']
        result['trades'].append({'id':p['id'],'symbol':p['symbol'],'strategy_id':p['config_id'],
            'family':p['cfg']['family'],'timeframe':p['cfg']['timeframe'],'side':p['side'],
            'signal_at':p['signal']['available_at'],'entry_at':p['entered'].isoformat(),'exit_at':when.isoformat(),
            'entry_price':p['original_basis'],'split_adjusted_entry':p['basis'],'exit_price':price,
            'entry_quantity':p['original_qty'],'exit_quantity':p['qty'],'stop':p['stop'],'target':p['target'],
            'gross_pnl':price_pnl,'net_pnl':net,'fees':p['fees']+charge,'borrow':p['borrow'],
            'distributions':p['distributions'],'net_r':net/reference_risk if reference_risk else None,'exit_reason':why})
        del positions[key]
    def reject(signal,reason): result['rejected'].append({'id':signal['id'],'reason':reason})
    def enter(signal,bar,now,same_close=False):
        cfg=configurations[signal['config_id']];side=signal['side'];key=(signal['symbol'],signal['config_id'])
        if key in positions: reject(signal,'Position already open');return True
        available,_,recalled=lending_state(signal['symbol'],now)
        if side<0 and (not available or recalled): reject(signal,'Short borrow unavailable');return True
        factor=D(bar.get('factor',1));limit=cfg['entry']=='limit'
        if limit:
            # Buy limit rounds down to its allowable maximum; sell limit up
            # to its allowable minimum. Fill needs a tick through that price.
            price=grid(D(signal['level'])/factor,side<0)
            if price<=0: reject(signal,'Limit is not a positive tradable price');return True
            if (D(bar['low'])>price-tick if side>0 else D(bar['high'])<price+tick): return False
        else: price=quote(bar['close'] if same_close else bar['open'],side)
        stop=grid(D(signal['stop'])/factor,side<0)
        distance=side*(price-stop)
        if distance<=0 or stop<=0: reject(signal,'Invalid stop after fill/gap');return True
        if cfg['target']=='swing':
            if signal['target_swing'] is None or side*(D(signal['target_swing'])/factor-price)<=0:
                reject(signal,'No valid known swing target');return True
            target=D(signal['target_swing'])/factor
        else: target=price+side*distance*D(cfg['target'][:-1])
        if target<=0: reject(signal,'Target is not a positive tradable price');return True
        target=grid(target,side>0)
        if target<=0: reject(signal,'Target is not a positive tradable price');return True
        value=equity();gross=sum(p['qty']*marks[p['symbol']] for p in positions.values())
        symbol_gross=sum(p['qty']*marks[p['symbol']] for p in positions.values() if p['symbol']==signal['symbol'])
        volume=D(bar['volume']) if same_close else previous_volume.get(signal['symbol'],ZERO)
        sample=stamp(bar['timestamp']) if same_close else previous_sample.get(signal['symbol'])
        # Deliberately derive usage from the accepted-entry history, separately
        # from production's bounded per-sample counter/cache.
        consumed=sum((q for symbol,source,q in entry_history if symbol==signal['symbol'] and source==sample),ZERO)
        available=volume*participation-consumed
        mark=marks[signal['symbol']]
        # With <=1 gross exposure and adverse execution, feasible new shares
        # cannot exceed equity / min(mark, fill). Do not reuse production caps
        # or fee-adjustment heuristics to bound this exhaustive enumeration.
        upper=max(0,int(max(0,value)/min(price,mark)))
        modeled_stop=quote(stop,-side,True);qty=0
        # Exhaustive integer feasibility oracle on deliberately small fixtures.
        if upper>100000: raise ValueError('Reference fixture exceeds the deliberate sizing envelope.')
        for quantity in range(1,upper+1):
            q=D(quantity);charge=fee(q,price,side)
            after=value+side*q*(mark-price)-charge
            planned=q*side*(price-modeled_stop)+charge+fee(q,modeled_stop,-side)
            if (q<=available and planned<=value*risk_fraction*D(signal['weight']) and gross+q*mark<=after*gross_cap and
                symbol_gross+q*mark<=after*symbol_cap and (side<0 or q*price+charge<=cash)):
                qty=quantity
        if not qty: reject(signal,'Capital, risk or prior-minute liquidity cap');return True
        qty=D(qty);charge=fee(qty,price,side)
        p={'id':signal['id'],'symbol':signal['symbol'],'side':side,'config_id':signal['config_id'],'cfg':cfg,'signal':signal,
            'qty':qty,'original_qty':qty,'basis':price,'original_basis':price,'stop':stop,'target':target,'entered':now,
            'fees':charge,'borrow':ZERO,'distributions':ZERO,'accrued_at':now,'borrow_mark':mark}
        positions[key]=p
        entry_history.append((signal['symbol'],sample,qty))
        transaction('entry',-side*qty*price-charge,now,trade_id=p['id'],symbol=p['symbol'],quantity=qty,price=price,fee=charge,
            liquidity_reference_at=sample.isoformat(),liquidity_reference_volume=volume,entry_volume_limit=int(volume*participation),
            entry_volume_before=consumed,entry_volume_after=consumed+qty)
        if limit and side*(D(bar['open'])-stop)<=0 and cfg['stop_kind']=='hard':
            exit_position(key,D(bar['open']),'gap_stop',now,stopped=True)
        return True

    for now,observations in sorted(by_time.items()):
        for p in positions.values(): borrow(p,now)
        day=min(b['session'] for b in observations.values())
        for action in sorted(actions,key=lambda a:(a['ex_date'],a['kind']!='split')):
            signature=(action['symbol'],action['ex_date'],action['kind'],action['value'])
            if signature in seen_actions or action['symbol'] not in observations: continue
            bar=observations[action['symbol']]
            if (action['kind']=='split' and bar['session']>=action['ex_date']) or (action['kind']=='dividend' and bar['session']==action['ex_date']):
                seen_actions.add(signature)
                for p in positions.values():
                    if p['symbol']!=action['symbol'] or p['entered']>=stamp(bar['session_open']): continue
                    if action['kind']=='split':
                        ratio=D(action['value']);p['qty']*=ratio
                        for field in ['basis','stop','target','borrow_mark']: p[field]/=ratio
                    else:
                        amount=p['side']*p['qty']*D(action['value']);p['distributions']+=amount
                        receivables.append({'amount':amount,'pay_date':action.get('pay_date') or action['ex_date'],'trade_id':p['id'],'symbol':p['symbol']})
                        transaction('distribution_entitlement',ZERO,now,amount=amount,trade_id=p['id'],symbol=p['symbol'])
                if action['kind']=='split' and action['symbol'] in marks: marks[action['symbol']]/=D(action['value'])
        for receivable in list(receivables):
            if day>=receivable['pay_date']:
                transaction('distribution_payment',receivable['amount'],now,trade_id=receivable['trade_id'],symbol=receivable['symbol']);receivables.remove(receivable)
        for symbol,bar in observations.items(): marks[symbol]=D(bar['open'])
        for key,p in list(positions.items()):
            if p['symbol'] not in observations: continue
            opening=D(observations[p['symbol']]['open']);p['borrow_mark']=opening
            if p['side']<0 and any(e['symbol']==p['symbol'] and e['recall'] and p['entered']<=stamp(e['effective_at'])<=now for e in lending_events):
                exit_position(key,opening,'borrow_recall',now)
            elif p['cfg']['stop_kind']=='hard' and p['side']*(opening-p['stop'])<=0: exit_position(key,opening,'gap_stop',now,stopped=True)
            elif p['side']*(opening-p['target'])>=tick: exit_position(key,p['target'],'gap_target',now,limited=True)
        while awaiting and stamp(awaiting[0]['available_at'])<=now: pending.append(awaiting.pop(0))
        for signal in sorted(list(pending),key=priority):
            if signal['symbol'] not in observations: continue
            cfg=configurations[signal['config_id']]
            if cfg['entry']=='same_close': pending.remove(signal);continue
            trigger=cfg.get('trigger_timeframe') or ('1h' if cfg['timeframe']=='1d' else cfg['timeframe'])
            if cfg['entry']=='limit' and (now-stamp(signal['available_at'])).total_seconds()>=60*frames[trigger]*cfg['limit_expiry']:
                reject(signal,'Limit expired');pending.remove(signal);continue
            if enter(signal,observations[signal['symbol']],now): pending.remove(signal)
        closed=now+MINUTE
        for p in positions.values(): borrow(p,closed)
        for key,p in list(positions.items()):
            if p['symbol'] not in observations: continue
            bar=observations[p['symbol']];side=p['side'];cfg=p['cfg']
            stop_hit=D(bar['low'])<=p['stop'] if side>0 else D(bar['high'])>=p['stop']
            target_hit=D(bar['high'])>=p['target']+tick if side>0 else D(bar['low'])<=p['target']-tick
            if stop_hit and cfg['stop_kind']=='hard': exit_position(key,p['stop'],'stop',closed,stopped=True)
            elif target_hit and not (cfg['entry']=='limit' and p['entered']==now): exit_position(key,p['target'],'target',closed,limited=True)
            elif cfg['stop_kind']=='close' and closed in triggers[key] and side*(D(bar['close'])-p['stop'])<0: exit_position(key,bar['close'],'close_stop',closed)
            elif cfg['structure_exit'] and reversals[key].get(closed)==-side: exit_position(key,bar['close'],'structure',closed)
            elif cfg['flat_at_close'] and closed==stamp(bar['session_close']): exit_position(key,bar['close'],'session_close',closed)
            elif cfg['max_hold'] and sum(p['entered']<t<=closed for t in endings[key])>=cfg['max_hold']: exit_position(key,bar['close'],'timeout',closed)
        for symbol,bar in observations.items():
            marks[symbol]=D(bar['close']);previous_volume[symbol]=D(bar['volume']);previous_sample[symbol]=stamp(bar['timestamp']);last_rows[symbol]=bar
        for p in positions.values(): p['borrow_mark']=marks[p['symbol']]
        at_close=[]
        while awaiting and stamp(awaiting[0]['available_at'])<=closed: at_close.append(awaiting.pop(0))
        for signal in sorted(at_close,key=priority):
            cfg=configurations[signal['config_id']]
            if cfg['entry']=='same_close' and stamp(signal['available_at'])==closed and signal['symbol'] in observations:
                enter(signal,observations[signal['symbol']],closed,True)
            else: pending.append(signal)
        if now==final:
            for key,p in list(positions.items()): exit_position(key,last_rows[p['symbol']]['close'],'end_of_window',closed)
        if now==final or any(closed==stamp(bar['session_close']) for bar in observations.values()):
            result['equity'].append({'date':day,'equity':equity(),'cash':cash,'receivables':sum((r['amount'] for r in receivables),ZERO),
                'gross_exposure':sum((p['qty']*marks[p['symbol']] for p in positions.values()),ZERO)})
    for signal in pending: reject(signal,'No eligible fill before end of window')
    return result
