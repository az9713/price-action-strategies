"""Canonical audit of observed original fills, never a strategy/allocation replay.

Produced before the original report is committed. Legacy float fields stay intact;
the Decimal audit is the frozen baseline for strict counterfactual comparisons.
"""
from bisect import bisect_left, bisect_right
from dataclasses import asdict
from decimal import Decimal, localcontext
import pandas as pd
from .config import Costs, identity
from .trade_twin_amounts import canonical_amount, read_amount, exact_total

POLICY = 'decimal80-observed-fills-v1'
TOLERANCE = Decimal('0.0000001')
FIELDS = ('entry_price', 'exit_price', 'entry_quantity', 'exit_quantity',
          'split_adjusted_entry', 'gross_pnl', 'fees', 'borrow', 'distributions', 'net_pnl')


def _number(value):
    if isinstance(value, bool):
        raise ValueError('Original cash-flow amounts cannot be booleans.')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Original cash-flow amounts must be finite.')
    return result


def _cancel(cancel):
    if cancel and cancel():
        raise InterruptedError('Original cash-flow audit canceled.')


def _input_hash(trades, traces, costs, manifest_hash):
    return identity(dict(trades=trades, entry_traces=traces, costs=costs,
                         dataset_manifest_hash=manifest_hash))


def _fee(quantity, price, direction, cost):
    return (max(_number(cost.minimum_commission), quantity*_number(cost.commission_per_share))
            + _number(cost.fixed_fee_per_order)
            + (quantity*price*_number(cost.sell_fee_per_dollar) if direction == -1 else Decimal(0)))


def _trade(trade, trace, rows, times, cost, actions, cancel):
    side = trade['side']; quantity = initial = _number(trade['entry_quantity'])
    entered = pd.Timestamp(trade['entry_at']); exited = pd.Timestamp(trade['exit_at'])
    if (type(side) is not int or side not in (-1, 1) or quantity <= 0 or quantity != int(quantity)
            or entered.tzinfo is None or exited.tzinfo is None or exited < entered):
        raise ValueError('Original executed direction, quantity or clock is invalid.')
    basis = fill = _number(trade['entry_price']); price = _number(trade['exit_price'])
    if min(fill, price) <= 0:
        raise ValueError('Original executed prices must be positive.')
    borrow = distributions = Decimal(0)
    if rows is not None and exited > entered:
        close_entry = trace['entry_order_type'] == 'same_close'
        index = bisect_left(times, entered.value) - int(close_entry)
        if index < 0 or rows[index].timestamp + (pd.Timedelta(minutes=1) if close_entry else pd.Timedelta(0)) != entered:
            raise ValueError('Original entry does not have its observed market mark.')
        mark = _number(rows[index].close if close_entry else rows[index].open)
        cursor = entered
        events = [] if cost.borrow_scenario is None else [e for e in cost.borrow_scenario.events if e.symbol == trade['symbol']]
        event_times = [pd.Timestamp(e.effective_at).value for e in events]
        seen = {(a.symbol, a.ex_date, a.kind, a.value) for a in actions
                if a.ex_date <= entered.tz_convert('America/New_York').date().isoformat()}

        def accrue(until):
            nonlocal cursor, borrow
            if until <= cursor:
                return
            if side == -1:
                i = bisect_right(event_times, cursor.value)-1
                rate = _number(events[i].annual_rate if i >= 0 else cost.borrow_annual)
                weighted = Decimal(0); at = cursor
                for event in events[i+1:bisect_right(event_times, until.value)]:
                    boundary = pd.Timestamp(event.effective_at)
                    weighted += rate*Decimal(boundary.value-at.value)/Decimal(1_000_000_000)
                    at = boundary; rate = _number(event.annual_rate)
                weighted += rate*Decimal(until.value-at.value)/Decimal(1_000_000_000)
                borrow += quantity*mark*weighted/Decimal(365*86400)
            cursor = until

        # A close exit at a coincident next open precedes that opening's actions.
        open_exit = trade.get('exit_reason') in {'gap_stop', 'gap_target', 'borrow_recall'}
        for ordinal in range(index+int(close_entry), bisect_right(times, exited.value)):
            if ordinal % 100 == 0:
                _cancel(cancel)
            row = rows[ordinal]; at = row.timestamp
            if at > exited or at == exited and not open_exit:
                break
            accrue(at)
            for action in actions:
                key = (action.symbol, action.ex_date, action.kind, action.value)
                if key in seen:
                    continue
                active = row.session >= action.ex_date if action.kind == 'split' else row.session == action.ex_date
                if active:
                    seen.add(key)
                    if entered < row.session_open:
                        if action.kind == 'split':
                            ratio = _number(action.value); quantity *= ratio; basis /= ratio; mark /= ratio
                        else:
                            distributions += side*quantity*_number(action.value)
            mark = _number(row.open)
            if at == exited:
                break
            closed = at+pd.Timedelta(minutes=1)
            accrue(min(closed, exited))
            if closed >= exited:
                break
            mark = _number(row.close)
        accrue(exited)
    entry_fee = _fee(initial, fill, side, cost); exit_fee = _fee(quantity, price, -side, cost)
    gross = side*quantity*(price-basis)
    net = gross+distributions-borrow-entry_fee-exit_fee
    return dict(id=trade['id'], **{k: canonical_amount(v) for k, v in dict(
        entry_price=fill, exit_price=price, entry_quantity=initial, exit_quantity=quantity,
        split_adjusted_entry=basis, gross_pnl=gross, fees=entry_fee+exit_fee,
        borrow=borrow, distributions=distributions, net_pnl=net).items()})


def audit_fills(regular, trades, entry_traces, costs, actions, dataset_manifest_hash, cancel=None):
    """Reconcile complete observed fills without selecting or executing any orders."""
    _cancel(cancel)
    cost = costs if isinstance(costs, Costs) else Costs(**costs)
    traces = {t['trade_id']: t for t in entry_traces}
    if len(traces) != len(entry_traces) or len({t['id'] for t in trades}) != len(trades) or set(traces) != {t['id'] for t in trades}:
        raise ValueError('Original cash-flow audit requires the complete unique fill cohort.')
    grouped = {}; result = []
    ordered_actions = sorted(actions, key=lambda a: (a.ex_date, a.kind != 'split'))
    with localcontext() as context:
        context.prec = 80
        for trade in trades:
            _cancel(cancel)
            relevant = [a for a in ordered_actions if a.symbol == trade['symbol']]
            needs_clock = bool(relevant) or trade['side'] == -1 and (cost.borrow_annual != 0 or cost.borrow_scenario is not None)
            rows = times = None
            if needs_clock:
                symbol = trade['symbol']
                if symbol not in grouped:
                    frame = regular[regular.symbol == symbol].sort_values('timestamp')
                    if frame.timestamp.duplicated().any():
                        raise ValueError('Original cash-flow clock has duplicate observed bars.')
                    grouped[symbol] = (list(frame.itertuples(index=False)), frame.timestamp.astype('int64').tolist())
                rows, times = grouped[symbol]
            result.append(_trade(trade, traces[trade['id']], rows, times, cost, relevant, cancel))
        reported = exact_total(t['net_pnl'] for t in trades)
        total = exact_total(t['net_pnl'] for t in result)
        value = dict(version=1, policy=POLICY, input_hash=_input_hash(trades, entry_traces, cost.model_dump(), dataset_manifest_hash),
                     actions_hash=identity([asdict(a) for a in actions]), trades=result,
                     net_profit=canonical_amount(total), reported_net_profit=canonical_amount(reported),
                     difference=canonical_amount(exact_total([total, reported.copy_negate()])))
        value['audit_sha256'] = identity(value)
        validate_audit(value, trades, entry_traces, cost.model_dump(), dataset_manifest_hash)
    _cancel(cancel)
    return value


def validate_audit(value, trades, traces, costs, manifest_hash):
    """Check the saved original audit without reading prices or recomputing orders.

    Original report/trial/attempt authority must additionally be verified by its
    caller. A self-consistent digest is not evidence of original computation.
    """
    if (not isinstance(value, dict) or set(value) != {'version', 'policy', 'input_hash', 'actions_hash', 'trades', 'net_profit', 'reported_net_profit', 'difference', 'audit_sha256'}
            or type(value['version']) is not int or value['version'] != 1 or value['policy'] != POLICY
            or value['audit_sha256'] != identity({k: v for k, v in value.items() if k != 'audit_sha256'})
            or value['input_hash'] != _input_hash(trades, traces, costs, manifest_hash)):
        raise ValueError('Original canonical cash-flow audit is unavailable or differs; create a new compatible source account.')
    original = {t['id']: t for t in trades}; records = value['trades']
    if not isinstance(records, list) or len(original) != len(trades) or len(records) != len(trades) or {t.get('id') for t in records if isinstance(t, dict)} != set(original):
        raise ValueError('Original cash-flow audit cohort differs.')
    cost = Costs(**costs); output = {}
    with localcontext() as context:
        context.prec = 80
        for record in records:
            if set(record) != {'id', *FIELDS}:
                raise ValueError('Original cash-flow audit trade shape differs.')
            amounts = {key: read_amount(record[key]) for key in FIELDS}; trade = original[record['id']]
            for key in FIELDS:
                if key in trade and abs(amounts[key]-_number(trade[key])) > TOLERANCE:
                    raise ValueError('Canonical executed cash flow does not reconcile with the original '+key+'.')
            if (amounts['gross_pnl'] != trade['side']*amounts['exit_quantity']*(amounts['exit_price']-amounts['split_adjusted_entry'])
                    or amounts['fees'] != _fee(amounts['entry_quantity'], amounts['entry_price'], trade['side'], cost)+_fee(amounts['exit_quantity'], amounts['exit_price'], -trade['side'], cost)
                    or amounts['net_pnl'] != amounts['gross_pnl']+amounts['distributions']-amounts['borrow']-_fee(amounts['entry_quantity'], amounts['entry_price'], trade['side'], cost)-_fee(amounts['exit_quantity'], amounts['exit_price'], -trade['side'], cost)):
                raise ValueError('Original canonical cash-flow arithmetic differs.')
            output[record['id']] = record['net_pnl']
        total = exact_total(output.values()); reported = exact_total(t['net_pnl'] for t in trades)
        if (read_amount(value['net_profit']) != total or read_amount(value['reported_net_profit']) != reported
                or read_amount(value['difference']) != exact_total([total, reported.copy_negate()])):
            raise ValueError('Original canonical cash-flow total differs.')
    return output
