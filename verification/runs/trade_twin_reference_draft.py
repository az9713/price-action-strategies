"""Independent one-trade twin Decimal reference; no production numerical imports.

This deliberately uses a chronological open/close event list rather than the
production minute loop. Inputs are primitive, already-authorized test records.
It is an oracle for the published adaptation, not the host's private engine.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext, ROUND_CEILING, ROUND_FLOOR


def stamp(value):
    result=datetime.fromisoformat(str(value))
    if result.tzinfo is None:raise ValueError('Reference requires aware clocks.')
    return result.astimezone(timezone.utc)


def execute_reference(bars,match,configuration,costs,account,actions=(),policy='barrier_capped_elapsed_v1'):
    with localcontext() as context:
        context.prec=80
        return _reference(bars,match,configuration,costs,account,actions,policy)


def _reference(bars,match,cfg,costs,account,actions,policy):
    D=lambda value:Decimal(str(value))
    zero=D(0);tick=D(account['tick_size']);side=match['side'];quantity=D(match['quantity'])
    entered=stamp(match['entry_at']);cutoff=stamp(match['cutoff_at'])
    if policy not in {'barrier_capped_elapsed_v1','fixed_elapsed_v1'} or cutoff<=entered:
        raise ValueError('Reference requires a supported positive-duration interpretation.')
    observations=sorted([b for b in bars if b['symbol']==match['symbol']],key=lambda b:stamp(b['timestamp']))
    opening=next(b for b in observations if stamp(b['timestamp'])==entered)
    prior=[b for b in observations if stamp(b['timestamp'])+timedelta(minutes=1)<=entered]
    before=prior[-1] if prior else None
    cost={k:D(v) for k,v in costs.items() if k not in {'borrow_available','borrow_scenario'}}
    def grid(price,up):return (price/tick).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*tick
    def quote(price,direction,stopped=False):
        value=D(price)*(1+D(direction)*(cost['slippage_bps']+cost['spread_bps']/2)/10000)
        if stopped:value+=direction*tick
        value=grid(value,direction>0)
        if value<=0:raise ValueError('Reference quote is nonpositive.')
        return value
    def fee(q,p,direction):
        return max(cost['minimum_commission'],q*cost['commission_per_share'])+cost['fixed_fee_per_order']+(q*p*cost['sell_fee_per_dollar'] if direction<0 else zero)
    def number(text):
        pieces=str(text).split('/')
        return D(pieces[0])/(D(pieces[1]) if len(pieces)==2 else 1)
    fill=quote(opening['open'],side);reference=D(match['entry_reference'])
    raw_stop=fill+number(match['stop'])-reference;raw_target=fill+number(match['target'])-reference
    stop=grid(raw_stop,side<0);target=grid(raw_target,side>0)
    geometry=dict(planned_stop=match['stop'],planned_target=match['target'],entry_reference=reference,entry_fill=fill,
        stop=stop,target=target,stop_rounding_residual=stop-raw_stop,target_rounding_residual=target-raw_target)
    events=sorted((e for b in observations if entered<=stamp(b['timestamp'])<=cutoff
        for e in [(stamp(b['timestamp']),1,'open',b),(stamp(b['timestamp'])+timedelta(minutes=1),0,'close',b)]
        if e[0]<cutoff or e[0]==cutoff and (e[2]=='close' or match['exit_boundary']=='open')),
        key=lambda e:(e[0],e[1]))
    lending=costs.get('borrow_scenario');lending_events=sorted(lending['events'],key=lambda e:stamp(e['effective_at'])) if lending else []
    def lending_state(at):
        state=(costs['borrow_available'],cost['borrow_annual'],False)
        for event in lending_events:
            if event['symbol']==match['symbol'] and stamp(event['effective_at'])<=at:
                state=(event['available'],D(event['annual_rate']),event['recall'])
        return state
    limit=int(D(before['volume'])*D(account['participation'])) if before else 0
    capital=D(account['capital']);initial=capital;cash=capital;position=None;receivables=[]
    result=dict(status='complete',failure=None,trade=None,ledger=[],equity=[],rejected=[],encounters=[],geometry=geometry)
    result['financing']=dict(initial_cash=capital,capital_top_up=zero,entry_notional=quantity*fill,
        liquidity_reference_at=stamp(before['timestamp']).isoformat() if before else None,
        liquidity_reference_volume=D(before['volume']) if before else zero,participation_limit=limit)
    reason=None
    if min(stop,target)<=0 or side*(fill-stop)<=0 or side*(target-fill)<=0:reason='Invalid transported tradable geometry'
    elif side<0 and (not lending_state(entered)[0] or lending_state(entered)[2]):reason='Short borrow unavailable'
    elif quantity>limit:reason='Original quantity exceeds prior-minute liquidity'
    if reason:
        result.update(status='failed',failure=reason,net_profit=None,final_cash=cash,final_receivables=zero,accounting_residual=zero)
        result['rejected']=[dict(id=match['source_id'],reason=reason)]
        return result
    charge=fee(quantity,fill,side);initial=max(capital,quantity*fill+charge);cash=initial
    result['financing'].update(initial_cash=initial,capital_top_up=initial-capital)
    def transaction(kind,delta,at,**fields):
        nonlocal cash
        old=cash;cash+=delta
        result['ledger'].append(dict(timestamp=at.isoformat(),kind=kind,cash_before=old,cash_change=delta,cash_after=cash,**fields))
    def accrue(at):
        if not position or at<=position['accrued']:return
        if side<0:
            cuts=[position['accrued']]+[stamp(e['effective_at']) for e in lending_events
                if e['symbol']==match['symbol'] and position['accrued']<stamp(e['effective_at'])<at]+[at]
            seconds=sum((lending_state(left)[1]*D((right-left).total_seconds()) for left,right in zip(cuts,cuts[1:])),zero)
            amount=position['quantity']*position['mark']*seconds/D(365*86400)
            position['borrow']+=amount
            if amount:transaction('borrow',-amount,at)
        position['accrued']=at
    def liquidate(base,why,at,limited=False,stopped=False):
        nonlocal position
        accrue(at);p=position;price=D(base) if limited else quote(base,-side,stopped)
        exit_fee=fee(p['quantity'],price,-side)
        transaction('exit',side*p['quantity']*price-exit_fee,at,quantity=p['quantity'],price=price,fee=exit_fee,reason=why)
        gross=side*p['quantity']*(price-p['basis']);net=gross+p['distributions']-p['borrow']-p['fee']-exit_fee
        risk=abs(p['basis']-p['stop'])*p['quantity']
        result['trade']=dict(id=match['source_id'],symbol=match['symbol'],side=side,entry_at=entered.isoformat(),exit_at=at.isoformat(),
            entry_price=fill,split_adjusted_entry=p['basis'],exit_price=price,entry_quantity=quantity,exit_quantity=p['quantity'],
            stop=p['stop'],target=p['target'],gross_pnl=gross,net_pnl=net,fees=p['fee']+exit_fee,borrow=p['borrow'],
            distributions=p['distributions'],net_r=net/risk,exit_reason=why)
        if policy=='fixed_elapsed_v1' and (at!=cutoff or why=='borrow_recall' and match['exit_boundary']!='open'):
            result.update(status='failed',failure='Borrow recall prevents exact elapsed holding')
        position=None
    seen=set();trigger=cfg.get('trigger_timeframe') or ('1h' if cfg['timeframe']=='1d' else cfg['timeframe'])
    trigger_minutes={'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':390}[trigger]
    for at,_,boundary,bar in events:
        accrue(at)
        if boundary=='open':
            for index,action in sorted(enumerate(actions),key=lambda pair:(pair[1]['ex_date'],pair[1]['kind']!='split',pair[0])):
                if index in seen or action['symbol']!=match['symbol']:continue
                active=bar['session']>=action['ex_date'] if action['kind']=='split' else bar['session']==action['ex_date']
                if not active:continue
                seen.add(index)
                if position and entered<stamp(bar['session_open']):
                    if action['kind']=='split':
                        ratio=D(action['value']);position['quantity']*=ratio
                        for field in ['basis','stop','target','mark']:position[field]/=ratio
                    else:
                        amount=side*position['quantity']*D(action['value']);position['distributions']+=amount
                        receivables.append(dict(amount=amount,pay_date=action.get('pay_date') or action['ex_date']))
                        transaction('distribution_entitlement',zero,at,amount=amount)
            for item in list(receivables):
                if bar['session']>=item['pay_date']:
                    transaction('distribution_payment',item['amount'],at);receivables.remove(item)
            if at==entered:
                position=dict(quantity=quantity,basis=fill,stop=stop,target=target,mark=D(bar['open']),borrow=zero,
                    distributions=zero,fee=charge,accrued=at)
                transaction('entry',-side*quantity*fill-charge,at,quantity=quantity,price=fill,fee=charge)
            elif position:
                position['mark']=D(bar['open'])
                recalled=side<0 and any(e['symbol']==match['symbol'] and e['recall'] and entered<=stamp(e['effective_at'])<=at for e in lending_events)
                if recalled:liquidate(bar['open'],'borrow_recall',at)
                elif at==cutoff and match['exit_boundary']=='open':liquidate(bar['open'],'elapsed_cutoff',at)
                else:
                    hit_stop=cfg['stop_kind']=='hard' and side*(D(bar['open'])-position['stop'])<=0
                    hit_target=side*(D(bar['open'])-position['target'])>=tick
                    for hit,kind in [(hit_stop,'gap_stop'),(hit_target,'gap_target')]:
                        if hit:result['encounters'].append(dict(timestamp=at.isoformat(),boundary='open',kind=kind))
                    if policy=='barrier_capped_elapsed_v1':
                        if hit_stop:liquidate(bar['open'],'gap_stop',at,stopped=True)
                        elif hit_target:liquidate(position['target'],'gap_target',at,limited=True)
        elif position:
            p=position
            hits=[]
            if cfg['stop_kind']=='hard' and (D(bar['low'])<=p['stop'] if side>0 else D(bar['high'])>=p['stop']):hits.append('stop')
            if (D(bar['high'])>=p['target']+tick if side>0 else D(bar['low'])<=p['target']-tick):hits.append('target')
            session_end=stamp(bar['session_close']);elapsed=int((at-stamp(bar['session_open'])).total_seconds()//60)
            trigger_close=(at==session_end or elapsed%trigger_minutes==0) and elapsed>0
            if cfg['stop_kind']=='close' and trigger_close and side*(D(bar['close'])-p['stop'])<0:hits.append('close_stop')
            result['encounters'].extend(dict(timestamp=at.isoformat(),boundary='close',kind=kind) for kind in hits)
            if policy=='barrier_capped_elapsed_v1' and hits:
                why=hits[0];base=p['stop'] if why=='stop' else p['target'] if why=='target' else bar['close']
                liquidate(base,why,at,limited=why=='target',stopped=why=='stop')
            if position and at==cutoff and match['exit_boundary']=='close':liquidate(bar['close'],'elapsed_cutoff',at)
            if position:position['mark']=D(bar['close'])
        final=at==cutoff and boundary==match['exit_boundary']
        if boundary=='close' and at==stamp(bar['session_close']) or final:
            outstanding=sum((r['amount'] for r in receivables),zero)
            exposure=position['quantity']*position['mark'] if position else zero
            result['equity'].append(dict(date=bar['session'],timestamp=at.isoformat(),equity=cash+(side*exposure if position else zero)+outstanding,
                cash=cash,receivables=outstanding,gross_exposure=exposure))
        if final:break
    if position or result['trade'] is None:raise ValueError('Reference could not observe its exact exit.')
    outstanding=sum((r['amount'] for r in receivables),zero)
    realized=result['trade']['net_pnl'];residual=cash+outstanding-initial-realized
    result.update(net_profit=realized if result['status']=='complete' else None,final_cash=cash,final_receivables=outstanding,accounting_residual=residual)
    return result
