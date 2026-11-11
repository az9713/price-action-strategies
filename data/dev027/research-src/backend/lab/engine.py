"""Minute-event long/short execution with shared capital and an auditable cash ledger."""
from collections import defaultdict
from itertools import groupby
from operator import attrgetter, itemgetter
from dataclasses import dataclass, field
import math
from decimal import Decimal,ROUND_CEILING,ROUND_FLOOR
import numpy as np
import pandas as pd
from .config import Strategy, Costs, Portfolio, identity, TIMEFRAMES
from .signals import Signal, contexts
from .data import aggregate, DataError
from .borrow import BorrowSchedule

def tick_price(price,tick,up):
    value=Decimal(str(price));step=Decimal(str(tick))
    return float((value/step).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*step)

def market_price(price,transaction_side,costs:Costs,portfolio:Portfolio,stop=False):
    adjustment=Decimal(str(costs.slippage_bps))+Decimal(str(costs.spread_bps))/Decimal(2)
    value=Decimal(str(price))*(1+transaction_side*adjustment/Decimal(10000))
    if stop: value+=transaction_side*Decimal(str(portfolio.tick_size))
    quoted=tick_price(value,portfolio.tick_size,transaction_side==1)
    if quoted<=0: raise DataError('Modeled execution is nonpositive for this price/tick/cost combination.')
    return quoted

def commission(quantity,price,transaction_side,costs):
    return max(costs.minimum_commission,quantity*costs.commission_per_share)+costs.fixed_fee_per_order+(quantity*price*costs.sell_fee_per_dollar if transaction_side==-1 else 0)

@dataclass
class Position:
    signal: Signal
    cfg: Strategy
    key: tuple
    quantity: float
    entry_quantity: float
    entry_at: pd.Timestamp
    entry_price: float
    original_entry_price: float
    stop: float
    target: float
    fees: float
    borrow: float = 0
    distributions: float = 0
    borrow_at: pd.Timestamp | None = None
    borrow_mark: float = 0

@dataclass
class Simulation:
    trades:list = field(default_factory=list)
    entry_traces:list = field(default_factory=list)
    equity:list = field(default_factory=list)
    ledger:list = field(default_factory=list)
    rejected:list = field(default_factory=list)
    signals:list = field(default_factory=list)
    assumptions:list = field(default_factory=list)

def _cash_equity(minutes, cash, cancel):
    """Mark cash at the same close events as the position engine."""
    final_time = minutes.timestamp.max()
    minute = pd.Timedelta(minutes=1)
    clock = minutes[['timestamp', 'symbol', 'session', 'session_close']]
    events = groupby(clock.itertuples(index=False, name=None), key=itemgetter(0))
    equity = []
    for ordinal, (timestamp, rows) in enumerate(events):
        if cancel and ordinal % 100 == 0 and cancel():
            raise InterruptedError('Experiment canceled at checkpoint.')
        sessions = {symbol: (session, closed) for _, symbol, session, closed in rows}
        if timestamp == final_time or any(timestamp + minute == closed for _, closed in sessions.values()):
            equity.append(dict(date=min(session for session, _ in sessions.values()), equity=cash,
                               cash=cash, receivables=0, gross_exposure=0))
    return equity


def simulate(regular:pd.DataFrame,signals:list[Signal],cfg:Strategy,costs:Costs|None=None,
             portfolio:Portfolio|None=None,actions=(),start=None,end=None,cancel=None,
             strategy_map:dict|None=None,chart_provider=None):
    costs=costs or Costs();portfolio=portfolio or Portfolio()
    result=Simulation(signals=[s.json() for s in signals])
    trace_costs_id=identity(costs);trace_portfolio_id=identity(portfolio)
    result.assumptions=[
        'Bar-based conservative fills; no tick sequence or guaranteed liquidity.',
        'Short availability is a scenario, not historical lending evidence.',
        'One-times-equity gross cap; short proceeds do not expand the exposure budget.',
        'Corporate-action fractional shares are retained until exit; new orders use whole shares.',
        'Borrow accrues on prior marked short notional over elapsed calendar time / 365.',
    ]
    if regular.empty: raise DataError('No execution bars.')
    all_minutes=regular.sort_values(['timestamp','symbol']).copy()
    minutes=all_minutes
    if start: minutes=minutes[minutes.session>=start]
    if end: minutes=minutes[minutes.session<=end]
    if minutes.empty: raise DataError('No execution bars in evaluation window.')
    borrowing=None
    if costs.borrow_scenario is not None:
        borrowing=BorrowSchedule(costs.borrow_scenario,costs.borrow_annual,costs.borrow_available)
        try:borrowing.validate(minutes.symbol.unique(),start or minutes.session.min(),end or minutes.session.max())
        except ValueError as exc:raise DataError(str(exc)) from exc
        result.assumptions.extend([
            'Borrow scenario: '+borrowing.spec.name+'; '+borrowing.spec.mode+' inputs, '+borrowing.spec.start+' through '+borrowing.spec.end+'.',
            'Minute borrowing states are input assumptions; recalls exit at the next observed opening and financing uses365 calendar days. Exact broker lending/billing is not established.'
        ])
    first=minutes.timestamp.min()
    # Warm-up builds detectors only. It cannot create entry orders in the evaluation window.
    def cfg_for(signal): return strategy_map.get(signal.id,cfg) if strategy_map else cfg
    def priority(signal): return signal.available_at,signal.symbol,identity(cfg_for(signal)),signal.id
    queue=sorted([s for s in signals if s.available_at>=first],key=priority)
    if not queue and isinstance(actions, (list, tuple)) and not actions:
        result.equity = _cash_equity(minutes, float(portfolio.capital), cancel)
        return result
    signal_index=0;pending=defaultdict(list);positions={};cash=float(portfolio.capital)
    marks={};previous_volume={};previous_volume_at={};entry_volume_used=defaultdict(int)
    last_time=None;receivables=[];paid_actions=set();applied_splits=set()
    configs={identity(cfg):cfg}
    if strategy_map:
        for configuration in strategy_map.values(): configs[identity(configuration)]=configuration
    ends={};trigger_ends={};changes={}
    for symbol,frame in all_minutes.groupby('symbol'):
        for config_id,configuration in configs.items():
            key=(symbol,config_id)
            bars=aggregate(frame,configuration.timeframe) if chart_provider is None else chart_provider(symbol,configuration.timeframe)
            complete=bars[bars.complete].reset_index(drop=True)
            ends[key]=complete.available_at.astype('int64').to_numpy()
            if configuration.stop_kind=='close':
                tr=aggregate(frame,configuration.trigger) if chart_provider is None else chart_provider(symbol,configuration.trigger)
                trigger_ends[key]=set(tr.loc[tr.complete,'available_at'].astype('int64'))
            if configuration.structure_exit:
                ctx=contexts(complete,configuration)
                changes[key]={r.available_at.value:int(r.choch) for _,r in ctx.iterrows() if r.choch}
    final_time=minutes.timestamp.max()
    last_rows={};current_time=None

    def marked_equity():
        return cash+sum(p.signal.side*p.quantity*marks.get(p.signal.symbol,p.entry_price) for p in positions.values())+sum(r['amount'] for r in receivables)
    def ledger(kind,amount,event_at=None,**fields):
        nonlocal cash
        before=cash;cash+=amount
        result.ledger.append(dict(timestamp=(event_at or current_time).isoformat(),kind=kind,cash_before=before,cash_change=amount,cash_after=cash,**fields))
    def accrue(position,until):
        since=position.borrow_at or position.entry_at
        if until<=since: return
        if position.signal.side==-1:
            rate_seconds=borrowing.rate_seconds(position.signal.symbol,since,until) if borrowing else costs.borrow_annual*(until-since).total_seconds()
            charge=position.quantity*position.borrow_mark*rate_seconds/86400/365
            position.borrow+=charge
            if charge: ledger('borrow',-charge,event_at=until,trade_id=position.signal.id,symbol=position.signal.symbol)
        position.borrow_at=until
    def close(key,base,reason,at,limit=False,stop=False):
        position=positions.pop(key);side=position.signal.side
        accrue(position,at)
        price=base if limit else market_price(base,-side,costs,portfolio,stop=stop)
        fee=commission(position.quantity,price,-side,costs)
        ledger('exit',side*position.quantity*price-fee,event_at=at,trade_id=position.signal.id,symbol=position.signal.symbol,
               quantity=position.quantity,price=price,fee=fee,reason=reason)
        gross=side*position.quantity*(price-position.entry_price)
        risk=abs(position.entry_price-position.stop)*position.quantity
        net=gross+position.distributions-position.borrow-position.fees-fee
        result.trades.append(dict(id=position.signal.id,symbol=position.signal.symbol,
            strategy_id=key[1],family=position.cfg.family,timeframe=position.cfg.timeframe,side=side,
            signal_at=position.signal.available_at.isoformat(),entry_at=position.entry_at.isoformat(),exit_at=at.isoformat(),
            entry_price=position.original_entry_price,split_adjusted_entry=position.entry_price,
            exit_price=price,entry_quantity=position.entry_quantity,exit_quantity=position.quantity,
            stop=position.stop,target=position.target,gross_pnl=gross,net_pnl=net,
            fees=position.fees+fee,borrow=position.borrow,distributions=position.distributions,
            net_r=net/risk if risk else None,exit_reason=reason))

    # The frame is already sorted by timestamp/symbol. Convert its rows once;
    # creating a pandas subgroup and namedtuple class per minute is unnecessary.
    events=groupby(minutes.itertuples(index=False),key=attrgetter('timestamp'))
    for iteration,(timestamp,group) in enumerate(events):
        current_time=timestamp
        if cancel and iteration%100==0 and cancel(): raise InterruptedError('Experiment canceled at checkpoint.')
        by_symbol={r.symbol:r for r in group}
        session=min(r.session for r in by_symbol.values())
        for position in positions.values(): accrue(position,timestamp)
        last_time=timestamp
        for action in sorted(actions,key=lambda a:(a.ex_date,0 if a.kind=='split' else 1)):
            action_key=(action.symbol,action.ex_date,action.kind,action.value)
            row=by_symbol.get(action.symbol)
            if row is None: continue
            if action.kind=='split' and row.session>=action.ex_date and action_key not in applied_splits:
                # Only positions crossing the effective session receive an action.
                for position in positions.values():
                    if position.signal.symbol==action.symbol and position.entry_at<row.session_open:
                        position.quantity*=action.value
                        position.entry_price/=action.value
                        position.stop/=action.value;position.target/=action.value
                        position.borrow_mark/=action.value
                if action.symbol in marks: marks[action.symbol]/=action.value
                applied_splits.add(action_key)
            if action.kind=='dividend' and row.session==action.ex_date and action_key not in paid_actions:
                for position in positions.values():
                    if position.signal.symbol==action.symbol and position.entry_at<row.session_open:
                        amount=position.signal.side*position.quantity*action.value
                        position.distributions+=amount
                        receivables.append(dict(amount=amount,pay_date=action.pay_date or action.ex_date,trade_id=position.signal.id,symbol=action.symbol))
                        result.ledger.append(dict(timestamp=timestamp.isoformat(),kind='distribution_entitlement',cash_change=0,cash_before=cash,cash_after=cash,amount=amount,trade_id=position.signal.id,symbol=action.symbol))
                paid_actions.add(action_key)
        for receivable in list(receivables):
            if session>=receivable['pay_date']:
                ledger('distribution_payment',receivable['amount'],trade_id=receivable['trade_id'],symbol=receivable['symbol'])
                receivables.remove(receivable)
        for symbol,row in by_symbol.items(): marks[symbol]=row.open
        for position in positions.values(): position.borrow_mark=marks[position.signal.symbol]
        if borrowing:
            for key,position in list(positions.items()):
                row=by_symbol.get(position.signal.symbol)
                if row is not None and position.signal.side==-1 and borrowing.recalled(position.signal.symbol,position.entry_at,timestamp):
                    close(key,row.open,'borrow_recall',timestamp)
        # Existing overnight positions see opening gaps before any new entry.
        for key,position in list(positions.items()):
            row=by_symbol.get(position.signal.symbol)
            if row is None: continue
            side=position.signal.side
            if position.cfg.stop_kind=='hard' and side*(row.open-position.stop)<=0:
                close(key,row.open,'gap_stop',timestamp,stop=True)
            elif side*(Decimal(str(row.open))-Decimal(str(position.target)))>=Decimal(str(portfolio.tick_size)):
                close(key,position.target,'gap_target',timestamp,limit=True)
        while signal_index<len(queue) and queue[signal_index].available_at<=timestamp:
            signal=queue[signal_index];signal_index+=1
            pending[signal.symbol].append(signal)

        def enter(signal,row,same_close=False):
            configuration=cfg_for(signal);config_id=identity(configuration);key=(signal.symbol,config_id)
            if key in positions:
                result.rejected.append(dict(id=signal.id,reason='Position already open'));return True
            side=signal.side
            entered=timestamp+(pd.Timedelta(minutes=1) if same_close else pd.Timedelta(0))
            available,_,recalled=borrowing.state(signal.symbol,entered) if borrowing else (costs.borrow_available,costs.borrow_annual,False)
            if side==-1 and (not available or recalled):
                result.rejected.append(dict(id=signal.id,reason='Short borrow unavailable'));return True
            factor=row.factor
            if configuration.entry=='limit':
                level=tick_price(Decimal(str(signal.level))/Decimal(str(factor)),portfolio.tick_size,side==-1)
                if level<=0:
                    result.rejected.append(dict(id=signal.id,reason='Limit is not a positive tradable price'));return True
                through=Decimal(str(level))-side*Decimal(str(portfolio.tick_size))
                if (Decimal(str(row.low))>through if side==1 else Decimal(str(row.high))<through): return False
                price=level
            else:
                price=market_price(row.close if same_close else row.open,side,costs,portfolio)
            raw_stop=Decimal(str(signal.stop))/Decimal(str(factor))
            stop=tick_price(raw_stop,portfolio.tick_size,side==-1)
            distance=side*(price-stop)
            if distance<=0 or price<=0 or stop<=0:
                result.rejected.append(dict(id=signal.id,reason='Invalid stop after fill/gap'));return True
            if configuration.target=='swing':
                if signal.target_swing is None or side*(signal.target_swing/factor-price)<=0:
                    result.rejected.append(dict(id=signal.id,reason='No valid known swing target'));return True
                target=Decimal(str(signal.target_swing))/Decimal(str(factor))
            else:
                decimal_risk=side*(Decimal(str(price))-Decimal(str(stop)))
                target=Decimal(str(price))+side*decimal_risk*Decimal(configuration.target[:-1])
            if target<=0:
                result.rejected.append(dict(id=signal.id,reason='Target is not a positive tradable price'));return True
            target=tick_price(target,portfolio.tick_size,side==1)
            if target<=0:
                result.rejected.append(dict(id=signal.id,reason='Target is not a positive tradable price'));return True
            equity=marked_equity()
            gross=sum(p.quantity*marks.get(p.signal.symbol,p.entry_price) for p in positions.values())
            symbol_gross=sum(p.quantity*marks.get(p.signal.symbol,p.entry_price) for p in positions.values() if p.signal.symbol==signal.symbol)
            capacity=min(equity*portfolio.total_exposure-gross,equity*portfolio.symbol_exposure-symbol_gross)
            # An upper bound followed by monotone integer feasibility search;
            # fees at a large trial quantity must not skip smaller valid sizes.
            modeled_stop=market_price(stop,-side,costs,portfolio,stop=True)
            loss_per_share=side*(price-modeled_stop)
            mark=marks[signal.symbol]
            reference_at=timestamp if same_close else previous_volume_at.get(signal.symbol)
            reference_volume=row.volume if same_close else previous_volume.get(signal.symbol,0)
            volume_key=(signal.symbol,reference_at)
            volume_limit=int(Decimal(str(reference_volume))*Decimal(str(portfolio.participation)))
            volume_before=entry_volume_used[volume_key]
            liquidity=max(0,volume_limit-volume_before)
            # Ceil the loose arithmetic bounds; exact feasibility below removes
            # the extra candidate instead of losing a whole share to float floor.
            high=max(0,min(math.ceil(max(0,equity)*portfolio.risk_fraction*signal.weight/loss_per_share),
                math.ceil(max(0,capacity)/mark),liquidity))
            def feasible(qty):
                fee=commission(qty,price,side,costs);exit_fee=commission(qty,modeled_stop,-side,costs)
                after=equity+side*qty*(mark-price)-fee
                return (qty*loss_per_share+fee+exit_fee<=equity*portfolio.risk_fraction*signal.weight+1e-8 and
                    gross+qty*mark<=after*portfolio.total_exposure+1e-8 and
                    symbol_gross+qty*mark<=after*portfolio.symbol_exposure+1e-8 and
                    (side==-1 or qty*price+fee<=cash+1e-8))
            qty=0
            while qty<high:
                trial=(qty+high+1)//2
                if feasible(trial): qty=trial
                else: high=trial-1
            if qty<=0:
                result.rejected.append(dict(id=signal.id,reason='Capital, risk or prior-minute liquidity cap'));return True
            fee=commission(qty,price,side,costs)
            positions[key]=Position(signal,configuration,key,qty,qty,entered,price,price,stop,target,fee,borrow_at=entered,borrow_mark=mark)
            entry_volume_used[volume_key]+=qty
            ledger('entry',-side*qty*price-fee,event_at=positions[key].entry_at,trade_id=signal.id,symbol=signal.symbol,quantity=qty,price=price,fee=fee,
                liquidity_reference_at=reference_at.isoformat(),liquidity_reference_volume=float(reference_volume),
                entry_volume_limit=volume_limit,entry_volume_before=volume_before,entry_volume_after=entry_volume_used[volume_key])
            # Capture original raw-price geometry before splits or an immediate exit
            # can alter a position. This is additional evidence, not a new fill.
            trace=dict(version=1,trade_id=signal.id,symbol=signal.symbol,side=side,config_id=config_id,
                signal_sha256=identity(signal.json()),costs_sha256=trace_costs_id,portfolio_sha256=trace_portfolio_id,
                entry_at=entered.isoformat(),atr_available_at=signal.available_at.isoformat(),entry_price=price,
                entry_reference=float(price if configuration.entry=='limit' else row.close if same_close else row.open),
                reference_kind='limit' if configuration.entry=='limit' else 'close' if same_close else 'open',
                entry_order_type=configuration.entry,entry_atr=float(Decimal(str(signal.atr))/Decimal(str(factor))),
                price_factor=float(factor),entry_stop=stop,entry_target=target,quantity=qty,entry_fee=fee,
                entry_ledger_sha256=identity(result.ledger[-1]))
            result.entry_traces.append(trace|dict(trace_sha256=identity(trace)))
            if configuration.entry=='limit' and configuration.stop_kind=='hard' and side*(row.open-stop)<=0:
                close(key,row.open,'gap_stop',timestamp,stop=True)
            return True

        for signal in sorted([s for symbol in by_symbol for s in pending[symbol]],key=priority):
            symbol=signal.symbol;row=by_symbol[symbol]
            configuration=cfg_for(signal)
            age=(timestamp-signal.available_at).total_seconds()/60
            if configuration.entry=='same_close':
                # Close entries are handled at the preceding minute close below.
                pending[symbol].remove(signal);continue
            if configuration.entry=='limit' and age>=configuration.limit_expiry*TIMEFRAMES[configuration.trigger]:
                result.rejected.append(dict(id=signal.id,reason='Limit expired'));pending[symbol].remove(signal);continue
            if enter(signal,row): pending[symbol].remove(signal)
        close_time=timestamp+pd.Timedelta(minutes=1)
        for position in positions.values(): accrue(position,close_time)
        for key,position in list(positions.items()):
            row=by_symbol.get(position.signal.symbol)
            if row is None: continue
            side=position.signal.side
            stopped=(row.low<=position.stop if side==1 else row.high>=position.stop)
            through=Decimal(str(position.target))+side*Decimal(str(portfolio.tick_size))
            targeted=(Decimal(str(row.high))>=through if side==1 else Decimal(str(row.low))<=through)
            new_limit=position.entry_at==timestamp and position.cfg.entry=='limit'
            if stopped and position.cfg.stop_kind=='hard': close(key,position.stop,'stop',close_time,stop=True)
            elif targeted and not new_limit: close(key,position.target,'target',close_time,limit=True)
            elif position.cfg.stop_kind=='close' and close_time.value in trigger_ends[key] and side*(row.close-position.stop)<0:
                close(key,row.close,'close_stop',close_time)
            elif position.cfg.structure_exit and changes.get(key,{}).get(close_time.value)==-side:
                close(key,row.close,'structure',close_time)
            elif position.cfg.flat_at_close and close_time==row.session_close:
                close(key,row.close,'session_close',close_time)
            elif position.cfg.max_hold and (np.searchsorted(ends[key],close_time.value,side='right')-np.searchsorted(ends[key],position.entry_at.value,side='right'))>=position.cfg.max_hold:
                close(key,row.close,'timeout',close_time)
        for symbol,row in by_symbol.items():
            marks[symbol]=row.close;previous_volume[symbol]=row.volume;previous_volume_at[symbol]=timestamp;last_rows[symbol]=row
        # Only the latest completed sample can fund a later order. Keep its
        # consumed amount across the synthetic-close / next-open boundary.
        entry_volume_used=defaultdict(int,{k:v for k,v in entry_volume_used.items() if k[1]==previous_volume_at.get(k[0])})
        for position in positions.values(): position.borrow_mark=marks[position.signal.symbol]
        # Same-close uses all now-known closing marks, with no earlier target credit.
        while signal_index<len(queue) and queue[signal_index].available_at<=close_time:
            signal=queue[signal_index];signal_index+=1
            configuration=cfg_for(signal)
            if configuration.entry=='same_close' and signal.available_at==close_time and signal.symbol in by_symbol:
                enter(signal,by_symbol[signal.symbol],same_close=True)
            else: pending[signal.symbol].append(signal)
        if timestamp==final_time:
            for key,position in list(positions.items()):
                row=last_rows[position.signal.symbol]
                close(key,row.close,'end_of_window',row.timestamp+pd.Timedelta(minutes=1))
        if any(close_time==r.session_close for r in by_symbol.values()) or timestamp==final_time:
            result.equity.append(dict(date=session,equity=marked_equity(),cash=cash,
                                      receivables=sum(r['amount'] for r in receivables),
                                      gross_exposure=sum(p.quantity*marks[p.signal.symbol] for p in positions.values())))
    for values in pending.values():
        for signal in values: result.rejected.append(dict(id=signal.id,reason='No eligible fill before end of window'))
    return result
