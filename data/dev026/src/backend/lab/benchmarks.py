"""Passive cash/equal-weight equity books with explicit entry and action ledgers.

These benchmarks have no strategy stops or rebalancing. Entry limits, transaction
costs, actual capital and distribution entitlement remain auditable.
"""
from decimal import Decimal,ROUND_FLOOR
import pandas as pd

from .data import DataError
from .engine import Simulation,commission,market_price
from .metrics import summary


def compare_passive(regular,costs,portfolio,actions,start,end,cancel=None):
    def check():
        if cancel and cancel(): raise InterruptedError('Benchmark canceled; no partial account is completed.')
    check()
    frame=regular.sort_values(['timestamp','symbol']).reset_index(drop=True)
    selected=frame[frame.session.between(start,end)]
    if selected.empty: raise DataError('No eligible sessions for benchmarks.')
    symbols=sorted(selected.symbol.unique());days=sorted(selected.session.unique())
    weight=min(portfolio.symbol_exposure,portfolio.total_exposure/len(symbols))
    allocation=portfolio.capital*weight
    entry_plan={}
    for symbol,group in frame.groupby('symbol',sort=True):
        if symbol not in symbols: continue
        records=list(group.itertuples(index=False))
        for index,row in enumerate(records):
            if start<=row.session<=end and index>0:
                entry_plan[symbol]=(row,records[index-1]);break
    cash=float(portfolio.capital);positions={};marks={};receivables=[]
    trades=[];ledger=[];daily=[];rejected=[];allocations=[]

    def book(at,kind,amount,trade_id=None,**details):
        nonlocal cash
        before=cash;cash+=amount
        ledger.append(dict(timestamp=pd.Timestamp(at).isoformat(),kind=kind,trade_id=trade_id,
                           cash_before=before,cash_change=amount,cash_after=cash,**details))

    def value():
        gross=sum(p['quantity']*marks[s] for s,p in positions.items())
        due=sum(r['amount'] for r in receivables if not r['paid'])
        return cash+gross+due,gross,due

    for day in days:
        check()
        session=selected[selected.session==day]
        first=session.sort_values('timestamp').groupby('symbol',sort=True).first()
        last=session.sort_values('timestamp').groupby('symbol',sort=True).last()
        opened=min(first.timestamp);closed=max(last.timestamp)+pd.Timedelta(minutes=1)
        marks.update({s:float(row.open) for s,row in first.iterrows()})
        todays=sorted([a for a in actions if a.ex_date==day],key=lambda a:(a.kind!='split',a.symbol,a.value))
        for action in todays:
            check()
            position=positions.get(action.symbol)
            if position is None: continue
            if action.kind=='split':
                before=position['quantity'];position['quantity']*=action.value
                book(opened,'split',0,position['id'],quantity_before=before,quantity_after=position['quantity'],ratio=action.value)
            else:
                amount=position['quantity']*action.value;position['distributions']+=amount
                receivables.append(dict(trade_id=position['id'],amount=amount,pay_date=action.pay_date or day,paid=False))
                book(opened,'distribution_entitlement',0,position['id'],receivable_change=amount,pay_date=action.pay_date or day)
        for due in receivables:
            if not due['paid'] and due['pay_date']<=day:
                book(opened,'distribution_payment',due['amount'],due['trade_id'],receivable_change=-due['amount'])
                due['paid']=True
        entries=sorted([(row.timestamp,symbol,row,prior) for symbol,(row,prior) in entry_plan.items() if row.session==day],key=lambda x:(x[0],x[1]))
        for at,symbol,row,prior in entries:
            check()
            # Every current minute open is known before simultaneous allocation.
            current=session[session.timestamp==at]
            marks.update({r.symbol:float(r.open) for r in current.itertuples(index=False)})
            price=market_price(float(row.open),1,costs,portfolio)
            equity,gross,_=value()
            volume_limit=int((Decimal(str(prior.volume))*Decimal(str(portfolio.participation))).to_integral_value(rounding=ROUND_FLOOR))
            upper=max(0,min(volume_limit,int(Decimal(str(allocation))/Decimal(str(price))),int(max(cash,0)/price)))
            def feasible(quantity):
                if not quantity: return True
                fee=commission(quantity,price,1,costs)
                after=equity-quantity*(price-marks[symbol])-fee
                return (quantity*price+fee<=cash+1e-8 and quantity*price<=allocation+1e-8 and
                        quantity*marks[symbol]<=after*portfolio.symbol_exposure+1e-8 and
                        gross+quantity*marks[symbol]<=after*portfolio.total_exposure+1e-8)
            low=0;high=upper
            while low<high:
                middle=(low+high+1)//2
                if feasible(middle): low=middle
                else: high=middle-1
            quantity=low
            allocations.append(dict(symbol=symbol,target_initial_weight=weight,initial_allocation=allocation,
                actual_entry_notional=quantity*price,uninvested_initial_allocation=allocation-quantity*price,
                entry_quantity=quantity,entry_at=pd.Timestamp(at).isoformat(),liquidity_reference_at=pd.Timestamp(prior.timestamp).isoformat(),
                liquidity_reference_volume=float(prior.volume),entry_volume_limit=volume_limit))
            if not quantity:
                rejected.append(dict(symbol=symbol,at=pd.Timestamp(at).isoformat(),reason='One passive entry attempt could not fund a whole share within cash/exposure/volume limits. No later accumulation.'))
                continue
            tid='buy-hold-'+symbol
            fee=commission(quantity,price,1,costs)
            position=dict(id=tid,symbol=symbol,side=1,entry_at=pd.Timestamp(at).isoformat(),entry_price=price,
                entry_quantity=quantity,quantity=float(quantity),entry_fee=fee,distributions=0.,borrow=0.,
                liquidity_reference_at=pd.Timestamp(prior.timestamp).isoformat(),liquidity_reference_volume=float(prior.volume))
            positions[symbol]=position
            book(at,'entry',-quantity*price-fee,tid,symbol=symbol,quantity=quantity,price=price,fee=fee,
                 liquidity_reference_at=position['liquidity_reference_at'],liquidity_reference_volume=float(prior.volume),entry_volume_limit=volume_limit)
        marks.update({s:float(row.close) for s,row in last.iterrows()})
        if day==days[-1]:
            for symbol,position in sorted(positions.items()):
                check()
                price=market_price(marks[symbol],-1,costs,portfolio);quantity=position['quantity']
                fee=commission(quantity,price,-1,costs)
                book(closed,'exit',quantity*price-fee,position['id'],symbol=symbol,quantity=quantity,price=price,fee=fee)
                trade={k:v for k,v in position.items() if k not in {'quantity','entry_fee'}}
                trade.update(exit_at=pd.Timestamp(closed).isoformat(),exit_price=price,exit_quantity=quantity,
                    exit_reason='end_of_window',fees=position['entry_fee']+fee,
                    net_pnl=quantity*price-position['entry_quantity']*position['entry_price']+position['distributions']-position['entry_fee']-fee)
                trades.append(trade)
            positions.clear()
        equity,gross,due=value()
        daily.append(dict(date=day,equity=equity,cash=cash,receivables=due,gross_exposure=gross))
    for symbol in symbols:
        if symbol not in entry_plan:
            rejected.append(dict(symbol=symbol,reason='No evaluation open with a known prior completed volume sample.'))
    cash_daily=[dict(date=day,equity=float(portfolio.capital),cash=float(portfolio.capital),receivables=0.,gross_exposure=0.) for day in days]
    cash_sim=Simulation(equity=cash_daily);passive_sim=Simulation(equity=daily,trades=trades)
    return dict(cash=dict(metrics=summary(cash_sim,portfolio.capital),equity=cash_daily,trades=[],ledger=[]),
        buy_hold=dict(metrics=summary(passive_sim,portfolio.capital),equity=daily,trades=trades,ledger=ledger,
                      rejected=rejected,allocation=allocations,outstanding_receivables=[r for r in receivables if not r['paid']]),
        assumptions=['Cash earns zero interest and uses the same starting capital and eligible session dates.',
            'Buy-and-hold is long-only, initially equal-notional-weighted subject to symbol/aggregate entry limits, whole shares, costs, cash and known prior-minute volume.',
            'One entry attempt per instrument; no later accumulation, stop, target or rebalancing. Exposure can drift after entry. Actual allocation and unused initial allocation are saved.',
            'Risk fraction is not applied to a passive position without a stop. This benchmark is capital-comparable, not a claim of equal strategy exposure or risk.',
            'Splits precede ex-date distribution entitlement. Unpaid distributions remain receivables, including after final liquidation.',
            'End-of-window liquidation charges actual modeled selling costs. Exit liquidity retains the stated conservative bar-model assumption.'])
