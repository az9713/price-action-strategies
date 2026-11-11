"""Compare candidate numerical loops with the original stage on authored data."""
from dataclasses import asdict
import hashlib
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import sys
from time import perf_counter, process_time

import pandas as pd

from backend.lab import engine, signals
from backend.lab.config import Costs, FAMILIES, Portfolio, Strategy, TIMEFRAMES, canonical
from backend.lab.data import normalize, prepare
from conftest import minute_frame
from test_reference_execution import sig
from verification.strategy_fixtures import SPEC, scenario


root = Path.cwd()
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
stage = root / 'data/dev027/research-src'
candidate = root / 'data/dev027/numerical-loop-candidate'
before_receipt = root / 'verification/runs/20261110T223715615104Z-bounded-publication-original-checkpoint-arm-deaths-runtime-trials-and-lease-regression/research-stage-subject.json'
before = json.loads(before_receipt.read_text(encoding='utf-8'))
hashes = {}


def load(name, original):
    assert Path(original.__file__).resolve() == stage / 'backend/lab' / (name + '.py')
    original_hash = hashlib.sha256(Path(original.__file__).read_bytes()).hexdigest()
    assert original_hash == before['source_files'][f'backend/lab/{name}.py']
    path = candidate / (name + '.py')
    hashes[name] = dict(original=original_hash, candidate=hashlib.sha256(path.read_bytes()).hexdigest())
    spec = spec_from_file_location('backend.lab.numerical_loop_candidate_' + name, path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


new_signals = load('signals', signals)
new_engine = load('engine', engine)
cases = [(family, '1m', side) for family in FAMILIES for side in (1, -1)]
cases.extend(('breakout', frame, side) for frame in TIMEFRAMES if frame != '1m' for side in (1, -1))
positive_signals = 0
for family, timeframe, side in cases:
    frame, _ = scenario(family, timeframe, side)
    configuration = Strategy(family=family, timeframe=timeframe, direction='long' if side == 1 else 'short', **SPEC['config'])
    expected = [s.json() for s in signals.generate_signals(frame, configuration)]
    assert expected and [s.json() for s in new_signals.generate_signals(frame, configuration)] == expected
    positive_signals += len(expected)

days = ['2026-11-25', '2026-11-27', '2026-11-30']
raw = pd.concat([minute_frame(day, symbol) for day in days for symbol in ['SPY', 'QQQ']], ignore_index=True)
frame = prepare(normalize(raw)[0])
truncated = frame[(frame.session < days[-1]) | (frame.timestamp < frame.timestamp.max() - pd.Timedelta(minutes=20))]
configuration = Strategy(family='breakout', timeframe='1m', stop_kind='close', structure_exit=True)
costs = Costs(**SPEC['costs'])
portfolio = Portfolio(**SPEC['portfolio'])
cash_cases = 0
for prices in [frame, truncated]:
    for orders in [[], [sig(prices, at=0)]]:
        start = days[1] if orders else days[0]
        args = (prices, orders, configuration, costs, portfolio)
        expected = engine.simulate(*args, start=start)
        actual = new_engine.simulate(*args, start=start)
        assert not expected.trades and not expected.ledger
        assert canonical(asdict(actual)) == canonical(asdict(expected))
        cash_cases += 1


def cancel_after_three_calls(call):
    checks = []

    def cancel():
        checks.append(True)
        return len(checks) == 3

    try:
        call(cancel)
    except InterruptedError as error:
        return str(error), len(checks)
    raise AssertionError('Expected a cancellation checkpoint')


assert cancel_after_three_calls(lambda cancel: engine.simulate(frame, [], configuration, cancel=cancel)) == cancel_after_three_calls(
    lambda cancel: new_engine.simulate(frame, [], configuration, cancel=cancel))
flat = prepare(normalize(minute_frame('2026-11-25', 'SPY'))[0])
assert signals.generate_signals(flat, configuration) == new_signals.generate_signals(flat, configuration) == []


def measure(detector, simulator):
    started_wall, started_cpu = perf_counter(), process_time()
    for _ in range(30):
        chosen = detector(flat, configuration)
        result = simulator(flat, chosen, configuration, costs, portfolio)
        assert not result.trades and result.equity[-1]['equity'] == portfolio.capital
    return dict(wall_seconds=perf_counter()-started_wall, cpu_seconds=process_time()-started_cpu)


measurements = []
for order in [('original', 'candidate'), ('candidate', 'original')]:
    for name in order:
        pair = (signals.generate_signals, engine.simulate) if name == 'original' else (new_signals.generate_signals, new_engine.simulate)
        measurements.append(dict(source=name, accounts=30, **measure(*pair)))
result = dict(source_hashes=hashes, authored_signal_comparisons=len(cases), identical_positive_signals=positive_signals,
              identical_cash_account_comparisons=cash_cases, cancellation_matches=True, measurements=measurements)
(out / 'numerical-loop-comparison.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
