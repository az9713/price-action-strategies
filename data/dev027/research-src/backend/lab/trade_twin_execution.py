"""Single-position financial twin books under the explicit D046 adaptation.

This internal kernel does not authorize source reports, pick candidates, create
jobs, redraw failures or promise broker financing. Callers must verify original
authority and sealed matching-plan membership before execution and publication.
Amounts remain Decimal until an explicitly versioned persistence boundary.
"""
from bisect import bisect_right
from collections import OrderedDict
from decimal import Decimal, localcontext
from fractions import Fraction
from threading import get_ident
import math
import re
import sys
import pandas as pd

from .borrow import BorrowSchedule
from .config import Costs, Portfolio, Strategy
from .data import Action, aggregate, schedule
from .trade_twins import EXECUTION_POLICIES, _time


class TwinPreparationCache:
    """Thread-owned, bounded reuse of pure transforms of exactly equal frames.

    Financial results, validation decisions and source authority are never
    cached. Unknown object columns use the original uncached transformations.
    The byte budget conservatively estimates retained frames and scalar records;
    it is not a bound on total process RSS or temporary financial working memory.
    """
    def __init__(self,max_bytes=64*1024*1024,max_entries=4):
        if type(max_bytes) is not int or not 1<=max_bytes<=64*1024*1024 or type(max_entries) is not int or not 1<=max_entries<=4:
            raise ValueError('Preparation reuse requires bounded integer byte and entry limits.')
        self.max_bytes=max_bytes;self.max_entries=max_entries;self.retained_bytes=0
        self.entries=OrderedDict();self.sequence=0;self.owner=get_ident()

    def _standard(self,frame):
        if get_ident()!=self.owner:raise ValueError('A preparation cache belongs to one execution thread.')
        known={'timestamp','symbol','open','high','low','close','volume','session','session_open','session_close','factor'}
        if not set(frame.columns)<=known:return False
        for name in frame.columns:
            dtype=frame[name].dtype
            if pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_datetime64_any_dtype(dtype):continue
            if name in {'symbol','session'} and all(type(value) is str for value in frame[name]):continue
            return False
        return True

    def _find(self,frame,kind,timeframe=None):
        if not self._standard(frame):return None
        for key,(tag,period,snapshot,value,size) in self.entries.items():
            if tag==kind and period==timeframe and frame.equals(snapshot):
                self.entries.move_to_end(key)
                return value
        return None

    def _remember(self,frame,kind,value,timeframe=None):
        if not self._standard(frame):return
        size=int(frame.memory_usage(index=True,deep=True).sum())+4096
        if kind=='records':
            size+=sys.getsizeof(value)+sum(sys.getsizeof(row)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in row.items()) for row in value)
        else:size+=int(value.memory_usage(index=True,deep=True).sum())+4096
        if size>self.max_bytes:return
        while self.entries and (len(self.entries)>=self.max_entries or self.retained_bytes+size>self.max_bytes):
            _,removed=self.entries.popitem(last=False);self.retained_bytes-=removed[4]
        owned=[row.copy() for row in value] if kind=='records' else value.copy(deep=True)
        self.sequence+=1
        self.entries[self.sequence]=(kind,timeframe,frame.copy(deep=True),owned,size)
        self.retained_bytes+=size

    def records(self,frame):
        value=self._find(frame,'records')
        if value is not None:return [row.copy() for row in value]
        value=frame.to_dict('records');self._remember(frame,'records',value)
        return value

    def aggregated(self,frame,timeframe):
        value=self._find(frame,'aggregate',timeframe)
        if value is not None:return value.copy(deep=True)
        value=aggregate(frame,timeframe);self._remember(frame,'aggregate',value,timeframe)
        return value


def _number(value):
    if not isinstance(value,str) or len(value)>1024:
        raise ValueError('Twin rational input must be a bounded string.')
    result=Fraction(value)
    if abs(result)>10**18:
        raise ValueError('Twin price/geometry working bound exceeded.')
    return result


def _decimal(value):
    ratio=value if isinstance(value,Fraction) else Fraction(str(value))
    return Decimal(ratio.numerator)/Decimal(ratio.denominator)


def _grid(value,tick,up):
    units=Fraction(value)/Fraction(tick)
    count=-(-units.numerator//units.denominator) if up else units.numerator//units.denominator
    return Decimal(count)*tick


def _inputs(regular,match,configuration,costs,portfolio,actions,policy,preparation=None):
    fields={'source_id','symbol','side','quantity','candidate_key','entry_at','entry_reference','atr','stop','target','holding_minutes','exit_boundary','cutoff_at'}
    if not isinstance(match,dict) or set(match)!=fields or policy not in EXECUTION_POLICIES:
        raise ValueError('Twin execution requires an exact frozen match and interpretation.')
    if type(match['side']) is not int or match['side'] not in {-1,1} or type(match['quantity']) is not int or not 0<match['quantity']<=10**9:
        raise ValueError('Twin direction and original whole quantity must be strict integers.')
    if not isinstance(match['source_id'],str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}',match['source_id']) is None or not isinstance(match['symbol'],str) or re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',match['symbol']) is None:
        raise ValueError('Twin source and instrument identities are invalid.')
    entered=pd.Timestamp(_time(match['entry_at']));cutoff=pd.Timestamp(_time(match['cutoff_at']))
    if type(match['holding_minutes']) is not int or match['holding_minutes']<=0 or cutoff-entered!=pd.Timedelta(minutes=match['holding_minutes']) or match['exit_boundary'] not in {'open','close'}:
        raise ValueError('Twin execution requires the exact positive elapsed cutoff and boundary.')
    if match['candidate_key']!=match['symbol']+'|'+entered.isoformat():
        raise ValueError('Twin candidate identity differs from its clock.')
    ref,atr,stop,target=(_number(match[k]) for k in ['entry_reference','atr','stop','target'])
    if ref<=0 or atr<=0 or match['side']*(ref-stop)<=0 or match['side']*(target-ref)<=0:
        raise ValueError('Twin transported distances must be positive.')
    cfg=Strategy(**(configuration.model_dump() if isinstance(configuration,Strategy) else configuration))
    cost=Costs(**(costs.model_dump() if isinstance(costs,Costs) else costs))
    account=Portfolio(**(portfolio.model_dump() if isinstance(portfolio,Portfolio) else portfolio))
    required={'timestamp','symbol','open','high','low','close','volume','session','session_open','session_close'}
    if not isinstance(regular,pd.DataFrame) or not required<=set(regular.columns):
        raise ValueError('Twin execution observations are incomplete.')
    frame=regular[regular.symbol==match['symbol']].sort_values('timestamp').copy()
    if frame.empty or frame.timestamp.duplicated().any():
        raise ValueError('Twin instrument clock is absent or duplicated.')
    observations=frame.to_dict('records') if preparation is None else preparation.records(frame)
    for bar in observations:
        at=bar['timestamp']
        if not isinstance(at,pd.Timestamp) or at.tzinfo is None or at.second or at.microsecond or at.nanosecond:
            raise ValueError('Twin observations require aware minute timestamps.')
        if any(isinstance(bar[k],bool) or not math.isfinite(float(bar[k])) or float(bar[k])<=0 for k in ['open','high','low','close']) or not math.isfinite(float(bar['volume'])) or bar['volume']<0:
            raise ValueError('Twin observations require finite positive prices and nonnegative volume.')
        if bar['low']>min(bar['open'],bar['close']) or bar['high']<max(bar['open'],bar['close']) or bar['low']>bar['high']:
            raise ValueError('Twin OHLC observations are inconsistent.')
    sessions=schedule(entered.tz_convert('America/New_York').date().isoformat(),cutoff.tz_convert('America/New_York').date().isoformat())
    expected=[]
    for day,(opened,closed) in sessions.items():
        expected.extend(t for t in pd.date_range(opened,closed,freq='min',inclusive='left') if entered<=t and (t<=cutoff if match['exit_boundary']=='open' else t<cutoff))
    window=[b for b in observations if entered<=b['timestamp'] and (b['timestamp']<=cutoff if match['exit_boundary']=='open' else b['timestamp']<cutoff)]
    if [b['timestamp'] for b in window]!=expected or not window or window[0]['timestamp']!=entered:
        raise ValueError('Twin execution requires every expected minute without sliding a cutoff.')
    for bar in window:
        day=bar['timestamp'].tz_convert('America/New_York').date().isoformat()
        if bar['session']!=day or (bar['session_open'],bar['session_close'])!=sessions[day]:
            raise ValueError('Twin session metadata differs from the exchange clock.')
    if (window[-1]['timestamp'] if match['exit_boundary']=='open' else window[-1]['timestamp']+pd.Timedelta(minutes=1))!=cutoff:
        raise ValueError('Twin exact exit boundary is not observed.')
    if Fraction(str(window[0]['open']))!=ref:
        raise ValueError('Twin planned reference differs from the observed entry open.')
    prior=[bar for bar in observations if bar['timestamp']+pd.Timedelta(minutes=1)<=entered]
    history=schedule((entered-pd.Timedelta(days=30)).tz_convert('America/New_York').date().isoformat(),entered.tz_convert('America/New_York').date().isoformat())
    previous_expected=max(t for opened,closed in history.values() for t in [min(entered,closed)-pd.Timedelta(minutes=1)] if opened<=t<entered)
    before=prior[-1] if prior and prior[-1]['timestamp']==previous_expected else None
    lending=BorrowSchedule(cost.borrow_scenario,cost.borrow_annual,cost.borrow_available) if cost.borrow_scenario else None
    if lending:lending.validate([match['symbol']],window[0]['session'],window[-1]['session'])
    owned_actions=[Action(**(a.__dict__ if isinstance(a,Action) else a)) for a in actions]
    signatures=[(a.symbol,a.ex_date,a.kind,a.value) for a in owned_actions]
    if len(signatures)!=len(set(signatures)):
        raise ValueError('Duplicate original corporate action.')
    if 'factor' not in frame:frame['factor']=1.
    bars=aggregate(frame,cfg.trigger) if preparation is None else preparation.aggregated(frame,cfg.trigger)
    triggers=set(bars.loc[bars.complete,'available_at'])
    return cfg,cost,account,window,before,lending,owned_actions,triggers


def execute_twin(regular,match,configuration,costs,portfolio,actions=(),*,policy='barrier_capped_elapsed_v1',cancel=None,preparation=None):
    """Return a complete or explicit failed diagnostic book; never a substitute draw."""
    if cancel and cancel():
        raise InterruptedError('Twin execution canceled.')
    if preparation is not None and not isinstance(preparation,TwinPreparationCache):
        raise ValueError('Choose an owned bounded preparation cache or no reuse.')
    validated=_inputs(regular,match,configuration,costs,portfolio,actions,policy,preparation)
    with localcontext() as context:
        context.prec=80
        result=_execute(match,*validated,policy,cancel)
    if cancel and cancel():
        raise InterruptedError('Twin execution canceled before publication.')
    return result


def _execute(match,cfg,cost,account,window,before,lending,actions,triggers,policy,cancel):
    D=lambda v:Decimal(str(v))
    zero=D(0);tick=D(account.tick_size);side=match['side'];qty=D(match['quantity'])
    entered=pd.Timestamp(match['entry_at']);cutoff=pd.Timestamp(match['cutoff_at'])
    def quote(base,direction,stopped=False):
        value=D(base)*(1+direction*(D(cost.slippage_bps)+D(cost.spread_bps)/2)/10000)
        if stopped:value+=direction*tick
        value=_grid(value,tick,direction==1)
        if value<=0:
            raise ValueError('Modeled twin execution is nonpositive.')
        return value
    def fee(quantity,price,direction):
        return max(D(cost.minimum_commission),quantity*D(cost.commission_per_share))+D(cost.fixed_fee_per_order)+(quantity*price*D(cost.sell_fee_per_dollar) if direction==-1 else zero)
    fill=quote(window[0]['open'],side)
    raw_stop=Fraction(fill)+_number(match['stop'])-_number(match['entry_reference'])
    raw_target=Fraction(fill)+_number(match['target'])-_number(match['entry_reference'])
    stop=_grid(raw_stop,tick,side==-1);target=_grid(raw_target,tick,side==1)
    geometry=dict(planned_stop=match['stop'],planned_target=match['target'],entry_reference=D(match['entry_reference']),entry_fill=fill,
        stop=stop,target=target,stop_rounding_residual=stop-_decimal(raw_stop),target_rounding_residual=target-_decimal(raw_target))
    volume=D(before['volume']) if before else zero;limit=int(volume*D(account.participation))
    initial=D(account.capital);cash=initial;position=None;receivables=[];seen=set()
    result=dict(status='complete',failure=None,trade=None,ledger=[],equity=[],rejected=[],encounters=[],geometry=geometry,
        financing=dict(initial_cash=initial,capital_top_up=zero,entry_notional=qty*fill,liquidity_reference_at=before['timestamp'].isoformat() if before else None,
            liquidity_reference_volume=volume,participation_limit=limit))
    available,_,recalled=lending.state(match['symbol'],entered) if lending else (cost.borrow_available,cost.borrow_annual,False)
    reason='Invalid transported tradable geometry' if min(stop,target)<=0 or side*(fill-stop)<=0 or side*(target-fill)<=0 else 'Short borrow unavailable' if side==-1 and (not available or recalled) else 'Original quantity exceeds prior-minute liquidity' if qty>limit else None
    if reason:
        result.update(status='failed',failure=reason,net_profit=None,final_cash=cash,final_receivables=zero,accounting_residual=zero)
        result['rejected']=[dict(id=match['source_id'],reason=reason)];return result
    entry_fee=fee(qty,fill,side);initial=max(initial,qty*fill+entry_fee);cash=initial
    result['financing'].update(initial_cash=initial,capital_top_up=initial-D(account.capital))
    def ledger(kind,delta,at,**fields):
        nonlocal cash
        old=cash;cash+=delta
        result['ledger'].append(dict(timestamp=at.isoformat(),kind=kind,cash_before=old,cash_change=delta,cash_after=cash,**fields))
    def accrue(at):
        if position is None or at<=position['borrow_at']:return
        if side==-1:
            since=position['borrow_at'];rate=D(lending.state(match['symbol'],since)[1] if lending else cost.borrow_annual);weighted=zero;cursor=since
            if lending:
                sequence=lending.events[match['symbol']];times=lending.times[match['symbol']]
                for event in sequence[bisect_right(times,since):bisect_right(times,at)]:
                    boundary=pd.Timestamp(event.effective_at)
                    weighted+=rate*D((boundary-cursor).total_seconds());cursor=boundary;rate=D(event.annual_rate)
            weighted+=rate*D((at-cursor).total_seconds())
            charge=position['quantity']*position['mark']*weighted/D(365*86400);position['borrow']+=charge
            if charge:ledger('borrow',-charge,at)
        position['borrow_at']=at
    def close(base,why,at,limited=False,stopped=False):
        nonlocal position
        accrue(at);p=position;price=D(base) if limited else quote(base,-side,stopped);charge=fee(p['quantity'],price,-side)
        ledger('exit',side*p['quantity']*price-charge,at,quantity=p['quantity'],price=price,fee=charge,reason=why)
        gross=side*p['quantity']*(price-p['basis']);net=gross+p['distributions']-p['borrow']-entry_fee-charge;risk=abs(p['basis']-p['stop'])*p['quantity']
        result['trade']=dict(id=match['source_id'],symbol=match['symbol'],side=side,entry_at=entered.isoformat(),exit_at=at.isoformat(),entry_price=fill,
            split_adjusted_entry=p['basis'],exit_price=price,entry_quantity=qty,exit_quantity=p['quantity'],stop=p['stop'],target=p['target'],
            gross_pnl=gross,net_pnl=net,fees=entry_fee+charge,borrow=p['borrow'],distributions=p['distributions'],net_r=net/risk,exit_reason=why)
        if policy=='fixed_elapsed_v1' and (at!=cutoff or why=='borrow_recall' and match['exit_boundary']!='open'):
            result.update(status='failed',failure='Borrow recall prevents exact elapsed holding')
        position=None
    def equity(bar,at):
        outstanding=sum((r['amount'] for r in receivables),zero);exposure=position['quantity']*position['mark'] if position else zero
        result['equity'].append(dict(date=bar['session'],timestamp=at.isoformat(),equity=cash+side*exposure+outstanding,cash=cash,receivables=outstanding,gross_exposure=exposure))
    for ordinal,bar in enumerate(window):
        if cancel and ordinal%100==0 and cancel():
            raise InterruptedError('Twin execution canceled at minute checkpoint.')
        at=bar['timestamp'];accrue(at)
        for index,action in sorted(enumerate(actions),key=lambda pair:(pair[1].ex_date,pair[1].kind!='split',pair[0])):
            if index in seen or action.symbol!=match['symbol']:continue
            active=bar['session']>=action.ex_date if action.kind=='split' else bar['session']==action.ex_date
            if not active:continue
            seen.add(index)
            if position is not None and entered<bar['session_open']:
                if action.kind=='split':
                    ratio=D(action.value);position['quantity']*=ratio
                    for field in ['basis','stop','target','mark']:position[field]/=ratio
                else:
                    amount=side*position['quantity']*D(action.value);position['distributions']+=amount
                    receivables.append(dict(amount=amount,pay_date=action.pay_date or action.ex_date));ledger('distribution_entitlement',zero,at,amount=amount)
        for item in list(receivables):
            if bar['session']>=item['pay_date']:ledger('distribution_payment',item['amount'],at);receivables.remove(item)
        if at==entered:
            position=dict(quantity=qty,basis=fill,stop=stop,target=target,mark=D(bar['open']),borrow=zero,distributions=zero,borrow_at=at)
            ledger('entry',-side*qty*fill-entry_fee,at,quantity=qty,price=fill,fee=entry_fee)
        elif position is not None:
            position['mark']=D(bar['open'])
            if side==-1 and lending and lending.recalled(match['symbol'],entered,at):close(bar['open'],'borrow_recall',at)
            elif at==cutoff and match['exit_boundary']=='open':close(bar['open'],'elapsed_cutoff',at)
            else:
                stopped=cfg.stop_kind=='hard' and side*(D(bar['open'])-position['stop'])<=0
                targeted=side*(D(bar['open'])-position['target'])>=tick
                for hit,kind in [(stopped,'gap_stop'),(targeted,'gap_target')]:
                    if hit:result['encounters'].append(dict(timestamp=at.isoformat(),boundary='open',kind=kind))
                if policy=='barrier_capped_elapsed_v1':
                    if stopped:close(bar['open'],'gap_stop',at,stopped=True)
                    elif targeted:close(position['target'],'gap_target',at,limited=True)
        if at==cutoff and match['exit_boundary']=='open':equity(bar,at);break
        closed=at+pd.Timedelta(minutes=1);accrue(closed)
        if position is not None:
            p=position;hits=[]
            if cfg.stop_kind=='hard' and (D(bar['low'])<=p['stop'] if side==1 else D(bar['high'])>=p['stop']):hits.append('stop')
            if (D(bar['high'])>=p['target']+tick if side==1 else D(bar['low'])<=p['target']-tick):hits.append('target')
            if cfg.stop_kind=='close' and closed in triggers and side*(D(bar['close'])-p['stop'])<0:hits.append('close_stop')
            result['encounters'].extend(dict(timestamp=closed.isoformat(),boundary='close',kind=kind) for kind in hits)
            if policy=='barrier_capped_elapsed_v1' and hits:
                why=hits[0];base=p['stop'] if why=='stop' else p['target'] if why=='target' else bar['close']
                close(base,why,closed,limited=why=='target',stopped=why=='stop')
            if position is not None and closed==cutoff and match['exit_boundary']=='close':close(bar['close'],'elapsed_cutoff',closed)
            if position is not None:position['mark']=D(bar['close'])
        if closed==bar['session_close'] or closed==cutoff and match['exit_boundary']=='close':equity(bar,closed)
    if position is not None or result['trade'] is None:
        raise ValueError('Twin execution failed to observe its frozen exit.')
    outstanding=sum((r['amount'] for r in receivables),zero);profit=result['trade']['net_pnl'];residual=cash+outstanding-initial-profit
    if abs(residual)>D('0.0000001'):
        raise ArithmeticError('Twin cash and complete net profit do not reconcile.')
    result.update(net_profit=profit if result['status']=='complete' else None,final_cash=cash,final_receivables=outstanding,accounting_residual=residual)
    return result
