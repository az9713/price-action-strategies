"""Exact detector-context reuse, complete dependencies, isolation and cancellation."""
import ast
import hashlib
import inspect
from pathlib import Path

import pandas as pd
import pytest

from backend.lab import signals
from backend.lab.config import APPLICABILITY,Strategy
from backend.lab.data import aggregate, normalize, prepare
from backend.lab.evaluation_cache import EvaluationCache
from conftest import minute_frame


@pytest.fixture
def context_input(tmp_path):
    regular = prepare(normalize(minute_frame(close=[100, 101, 103, 105, 102, 100, 103, 106, 110, 112, 108, 105]))[0])
    source = tmp_path / "authored-source.bin"
    source.write_bytes(b"authored verified context")
    cache = EvaluationCache(tmp_path)
    frame, _ = cache.prepared(("one",), source, hashlib.sha256(source.read_bytes()).hexdigest(), lambda: (regular, []))
    bars = aggregate(frame, "1m")
    return cache, frame, bars[bars.complete].reset_index(drop=True)


def test_context_key_covers_every_configuration_dependency():
    function = ast.parse(inspect.getsource(signals.contexts))
    used = {node.attr for node in ast.walk(function)
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "cfg"}
    assert set(signals.CONTEXT_FIELDS) == used and len(signals.CONTEXT_FIELDS) == len(used) == 12


def test_identical_context_is_reused_across_distinct_rules_and_returns_defensive_copies(context_input, monkeypatch):
    cache, frame, bars = context_input
    cfg = Strategy()
    expected = signals.contexts(bars, cfg)
    real = signals.contexts
    calls = []
    def observed(*args, **kwargs):
        calls.append(True)
        return real(*args, **kwargs)
    monkeypatch.setattr(signals, "contexts", observed)
    provider = cache.context_provider(frame)
    first = provider("SPY", "1m", cfg, bars, None)
    first.loc[0, "close"] = -1
    changed_rule = Strategy(**(cfg.model_dump() | {"target": "3R", "stop_buffer": .25}))
    actual = provider("SPY", "1m", changed_rule, bars, None)
    assert len(calls) == 1 and changed_rule != cfg
    pd.testing.assert_frame_equal(actual, expected)
    assert 0 < cache.cache_bytes <= cache.max_bytes
    assert cache.context_provider(frame.copy()) is None
    cache.clear()
    assert cache.context_provider(frame) is None and cache.cache_bytes == 0


@pytest.mark.parametrize("name,value", [
    ("impulse_atr", 3.), ("impulse_bars", 4), ("level_age", 97), ("level_shape", "zone"),
    ("level_tolerance", .5), ("min_touches", 2), ("pullback_max", 4.), ("pullback_min", .1),
    ("reclaim_bars", 4), ("retest_window", 13), ("sweep_depth", .25), ("swing_strength", 5),
])
def test_each_actual_context_parameter_invalidates_its_entry(context_input, monkeypatch, name, value):
    cache, frame, bars = context_input
    family = sorted(APPLICABILITY.get(name, {"change_of_character"}))[0]
    cfg = Strategy(family=family, sweep_required=family == "change_of_character" and name in {"reclaim_bars", "sweep_depth"})
    assert getattr(cfg, name) != value
    real, calls = signals.contexts, []
    def observed(*args, **kwargs):
        calls.append(True)
        return real(*args, **kwargs)
    monkeypatch.setattr(signals, "contexts", observed)
    provider = cache.context_provider(frame)
    provider("SPY", "1m", cfg, bars, None)
    changed = Strategy(**(cfg.model_dump() | {name: value}))
    actual = provider("SPY", "1m", changed, bars, None)
    assert len(calls) == 2
    pd.testing.assert_frame_equal(actual, real(bars, changed))


def test_cached_context_replays_original_cancellation_checkpoints(context_input):
    cache, frame, bars = context_input
    cfg = Strategy()
    provider = cache.context_provider(frame)
    provider("SPY", "1m", cfg, bars, None)
    counts = []
    for compute in (lambda cancel: signals.contexts(bars, cfg, cancel),
                    lambda cancel: provider("SPY", "1m", cfg, bars, cancel)):
        calls = []
        def cancel():
            calls.append(True)
            return len(calls) == 3
        with pytest.raises(InterruptedError, match="Signal calculation canceled"):
            compute(cancel)
        counts.append(len(calls))
    assert counts == [3, 3]


def test_context_eviction_recomputes_identical_values(context_input, monkeypatch):
    cache, frame, bars = context_input
    real, calls = signals.contexts, []
    def observed(*args, **kwargs):
        calls.append(True)
        return real(*args, **kwargs)
    monkeypatch.setattr(signals, "contexts", observed)
    provider = cache.context_provider(frame)
    expected = provider("SPY", "1m", Strategy(), bars, None)
    cache.put(("authored-eviction",), b"x", cache.max_bytes)
    actual = provider("SPY", "1m", Strategy(), bars, None)
    assert len(calls) == 2 and cache.cache_bytes <= cache.max_bytes
    pd.testing.assert_frame_equal(actual, expected)
