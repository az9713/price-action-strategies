"""Frozen complete-cohort trade-twin matching, streamed draws and strict grading.

This module does not execute accounts or establish original-account authority.
Callers must bind verified originals and complete numerical outcomes separately.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction
import re
from typing import Literal
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy.stats import binomtest
from .config import identity
from .data import schedule
from .trade_twin_amounts import read_amount

TOTAL_SETS = 10000
MAX_SOURCE_TRADES = 20000
MAX_EDGES = 2_000_000
MAX_MOMENTS = 2_000_000
MAX_CLOCK_MINUTES = 2_000_000
MAX_ASSESSMENTS = 2_000_000
DRAW_POLICY = 'complete-executed-cohort-sha256-independent-replacement-v1'
EXECUTION_POLICIES = ('barrier_capped_elapsed_v1', 'fixed_elapsed_v1')


def _time(value):
    if not isinstance(value, str):
        raise ValueError('Twin clocks require explicit timestamp strings.')
    try:
        at = pd.Timestamp(value)
    except (ValueError, TypeError, OverflowError) as error:
        raise ValueError('Invalid twin timestamp.') from error
    if pd.isna(at) or at.tz is None or at.second or at.microsecond or at.nanosecond:
        raise ValueError('Twin clocks require timezone-aware whole-minute boundaries.')
    return at.tz_convert('UTC').isoformat()


def _integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(name + ' must be an integer in its declared range.')
    return value


def _cancel(check):
    if check and check():
        raise InterruptedError('Trade twins canceled at a deterministic boundary.')


class _Frozen(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)


class SourceTrade(_Frozen):
    trade_id: str = Field(pattern=r'^[A-Za-z0-9_.:-]{1,128}$', strict=True)
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$', strict=True)
    side: Literal[-1, 1]
    entry_at: str
    exit_at: str
    exit_boundary: Literal['open', 'close']
    entry_price: float = Field(gt=0, strict=True)
    entry_atr: float = Field(gt=0, strict=True)
    atr_available_at: str
    entry_stop: float = Field(gt=0, strict=True)
    entry_target: float = Field(gt=0, strict=True)
    quantity: int = Field(gt=0, le=1_000_000_000, strict=True)
    net_profit: float = Field(strict=True)
    net_profit_exact: str | None = None

    @field_validator('net_profit_exact')
    @classmethod
    def canonical_profit(cls, value):
        if value is not None:
            read_amount(value)
        return value

    @field_validator('side', mode='before')
    @classmethod
    def strict_side(cls, value):
        return _integer(value, -1, 1, 'Direction')

    @field_validator('entry_at', 'exit_at', 'atr_available_at')
    @classmethod
    def minute_clock(cls, value):
        return _time(value)

    @model_validator(mode='after')
    def geometry_and_clock(self):
        if self.exit_at < self.entry_at or self.atr_available_at > self.entry_at:
            raise ValueError('Twin source exit or ATR availability is invalid.')
        if self.side * (self.entry_price - self.entry_stop) <= 0 or self.side * (self.entry_target - self.entry_price) <= 0:
            raise ValueError('Twin source needs positive original entry stop and target distances.')
        return self


class TwinMoment(_Frozen):
    symbol: str = Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$', strict=True)
    entry_at: str
    reference_price: float = Field(gt=0, strict=True)
    atr: float = Field(gt=0, strict=True)
    atr_available_at: str

    @field_validator('entry_at', 'atr_available_at')
    @classmethod
    def minute_clock(cls, value):
        return _time(value)

    @model_validator(mode='after')
    def known_at_entry(self):
        if self.atr_available_at > self.entry_at:
            raise ValueError('Twin candidate ATR is not available at entry.')
        return self


def _bucket(at):
    local = pd.Timestamp(at).tz_convert('America/New_York')
    return (local.hour * 60 + local.minute - 570) // 30


def _duration(source):
    return int((pd.Timestamp(source.exit_at) - pd.Timestamp(source.entry_at)) // pd.Timedelta(minutes=1))


def _geometry(source, moment):
    """Exact rational geometry; no precision-context rounding affects eligibility."""
    side = source.side
    price, atr = Fraction(str(moment.reference_price)), Fraction(str(moment.atr))
    original, original_atr = Fraction(str(source.entry_price)), Fraction(str(source.entry_atr))
    stop_distance = side * (original - Fraction(str(source.entry_stop))) / original_atr
    target_distance = side * (Fraction(str(source.entry_target)) - original) / original_atr
    return price - side * stop_distance * atr, price + side * target_distance * atr


@dataclass(frozen=True)
class PreparedTwins:
    sources: tuple[SourceTrade, ...]
    moments: tuple[TwinMoment, ...]
    clocks: tuple[tuple[str, tuple[str, ...]], ...]
    pools: tuple[tuple[int, ...], ...]
    reasons: tuple[str | None, ...]
    start: str
    end: str
    parent_identity: str
    plan_hash: str

    @property
    def eligible(self):
        return bool(self.sources) and all(self.pools)

    def json(self):
        return dict(draw_policy=DRAW_POLICY, execution_policies=list(EXECUTION_POLICIES),
                    source_parent_identity=self.parent_identity, start=self.start, end=self.end,
                    sources=[s.model_dump(exclude_none=True) for s in self.sources], moments=[m.model_dump() for m in self.moments],
                    clocks={symbol: list(times) for symbol, times in self.clocks},
                    pools=[list(p) for p in self.pools], reasons=list(self.reasons), plan_hash=self.plan_hash)


def prepare_plan(sources, moments, clock, start, end, parent_identity, cancel=None):
    """Only time/known entry features determine pools; future OHLC is not accepted."""
    _cancel(cancel)
    if not isinstance(parent_identity, str) or not re.fullmatch('[0-9a-f]{64}', parent_identity):
        raise ValueError('Twin plans require the original parent authority digest.')
    for value in (start, end):
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) or date.fromisoformat(value).isoformat() != value:
            raise ValueError('Twin dates require canonical calendar dates.')
    if start > end:
        raise ValueError('Twin dates are reversed.')
    actual_sources = []
    for value in sources:
        _cancel(cancel)
        actual_sources.append(SourceTrade.model_validate(value))
        if len(actual_sources) > MAX_SOURCE_TRADES:
            raise ValueError('Twin source-trade working bound exceeded; no subset was selected.')
    actual_sources = tuple(sorted(actual_sources, key=lambda s: s.trade_id))
    actual_moments = []
    for value in moments:
        _cancel(cancel)
        actual_moments.append(TwinMoment.model_validate(value))
        if len(actual_moments) > MAX_MOMENTS:
            raise ValueError('Twin feature working bound exceeded; no subset was selected.')
    actual_moments = tuple(sorted(actual_moments, key=lambda m: (m.symbol, m.entry_at)))
    if len({s.trade_id for s in actual_sources}) != len(actual_sources):
        raise ValueError('Duplicate real trade identity.')
    if len({(m.symbol, m.entry_at) for m in actual_moments}) != len(actual_moments):
        raise ValueError('Duplicate twin candidate minute.')
    symbols = {s.symbol for s in actual_sources} | {m.symbol for m in actual_moments}
    if not isinstance(clock, dict) or set(clock) != symbols:
        raise ValueError('Twin clock instruments must exactly match the frozen cohort/features.')
    if any(not isinstance(clock[symbol], (list, tuple)) for symbol in symbols):
        raise ValueError('Twin execution clocks require finite timestamp sequences.')
    lengths = {len(clock[symbol]) for symbol in symbols}
    if len(lengths) > 1 or sum(len(clock[symbol]) for symbol in symbols) > MAX_CLOCK_MINUTES:
        raise ValueError('Twin clock lengths differ or exceed the explicit total working bound.')
    opens = set()
    allowed_minutes = next(iter(lengths), 0)
    sessions = schedule(start, end) if symbols else {}
    for opened, closed in sessions.values():
        _cancel(cancel)
        if len(opens) + int((closed - opened) // pd.Timedelta(minutes=1)) > allowed_minutes:
            raise ValueError('Twin clock does not cover every expected session minute.')
        opens.update(t.isoformat() for t in pd.date_range(opened, closed, freq='min', inclusive='left'))
    closes = {(pd.Timestamp(t) + pd.Timedelta(minutes=1)).isoformat() for t in opens}
    frozen_clocks = []
    for symbol in sorted(symbols):
        _cancel(cancel)
        values = [_time(t) for t in clock[symbol]]
        if len(values) != len(set(values)) or set(values) != opens:
            raise ValueError('Twin execution clock is duplicated or does not cover every expected session minute.')
        frozen_clocks.append((symbol, tuple(sorted(values))))
    execution_boundaries = opens | closes
    for source in actual_sources:
        _cancel(cancel)
        if source.entry_at not in execution_boundaries or source.exit_at not in (opens if source.exit_boundary == 'open' else closes):
            raise ValueError('Real executed trade is outside its frozen execution clock.')
    for moment in actual_moments:
        if moment.entry_at not in opens:
            raise ValueError('Twin entry feature is outside a frozen regular-session minute open.')
    original_entries = {(s.symbol, s.entry_at) for s in actual_sources}
    strata = {}
    for index, moment in enumerate(actual_moments):
        if (moment.symbol, moment.entry_at) not in original_entries:
            strata.setdefault((moment.symbol, _bucket(moment.entry_at)), []).append(index)
    pools, reasons, edges, assessments = [], [], 0, 0
    for source in actual_sources:
        _cancel(cancel)
        duration = _duration(source)
        pool = []
        if duration:
            boundaries = opens if source.exit_boundary == 'open' else closes
            for index in strata.get((source.symbol, _bucket(source.entry_at)), ()):
                _cancel(cancel)
                assessments += 1
                if assessments > MAX_ASSESSMENTS:
                    raise ValueError('Twin candidate-assessment working bound exceeded; no subset was selected.')
                moment = actual_moments[index]
                cutoff = (pd.Timestamp(moment.entry_at) + pd.Timedelta(minutes=duration)).isoformat()
                if cutoff not in boundaries:
                    continue
                stop, target = _geometry(source, moment)
                if min(stop, target) > 0:
                    pool.append(index)
                    edges += 1
                    if edges > MAX_EDGES:
                        raise ValueError('Twin matching-edge working bound exceeded; no subset was selected.')
        pools.append(tuple(pool))
        reasons.append(None if pool else ('Zero-duration original trade is ineligible.' if duration == 0 else 'No complete compatible entry/cutoff and positive-geometry twin minute.'))
    plan = PreparedTwins(actual_sources, actual_moments, tuple(frozen_clocks), tuple(pools), tuple(reasons), start, end, parent_identity, '')
    content = plan.json()
    del content['plan_hash']
    return PreparedTwins(actual_sources, actual_moments, tuple(frozen_clocks), tuple(pools), tuple(reasons), start, end, parent_identity, identity(content))


def _hash_integer(value):
    return int(identity(value), 16)


def sample_index(plan_hash, seed, set_index, source_id, size):
    _integer(seed, 0, 2**31 - 1, 'Seed')
    _integer(set_index, 0, TOTAL_SETS - 1, 'Set ordinal')
    _integer(size, 1, MAX_EDGES, 'Pool size')
    if not isinstance(plan_hash, str) or not re.fullmatch('[a-f0-9]{64}', plan_hash):
        raise ValueError('Invalid frozen twin plan identity.')
    if not isinstance(source_id, str) or not re.fullmatch('[A-Za-z0-9_.:-]{1,128}', source_id):
        raise ValueError('Invalid real source identity.')
    coordinate = dict(policy=DRAW_POLICY, plan_hash=plan_hash, seed=seed, set_index=set_index, source_id=source_id)
    domain = 1 << 256
    ceiling = domain - domain % size
    counter = 0
    while True:
        value = _hash_integer(coordinate | dict(counter=counter))
        if value < ceiling:
            return value % size
        counter += 1


def draw_set(plan, seed, set_index, cancel=None):
    _cancel(cancel)
    _integer(seed, 0, 2**31 - 1, 'Seed')
    _integer(set_index, 0, TOTAL_SETS - 1, 'Set ordinal')
    if not plan.eligible:
        raise ValueError('The entire real-trade cohort must have nonempty twin pools.')
    matches = []
    for source, pool in zip(plan.sources, plan.pools):
        _cancel(cancel)
        moment = plan.moments[pool[sample_index(plan.plan_hash, seed, set_index, source.trade_id, len(pool))]]
        stop, target = _geometry(source, moment)
        duration = _duration(source)
        matches.append(dict(source_id=source.trade_id, symbol=source.symbol, side=source.side, quantity=source.quantity,
            candidate_key=moment.symbol + '|' + moment.entry_at, entry_at=moment.entry_at,
            entry_reference=str(Decimal(str(moment.reference_price))), atr=str(Decimal(str(moment.atr))),
            stop=str(stop), target=str(target), holding_minutes=duration, exit_boundary=source.exit_boundary,
            cutoff_at=(pd.Timestamp(moment.entry_at) + pd.Timedelta(minutes=duration)).isoformat()))
    content = dict(plan_hash=plan.plan_hash, seed=seed, set_index=set_index, matches=matches)
    return content | dict(draw_hash=identity(content))


def stream_sets(plan, seed, start=0, stop=TOTAL_SETS, cancel=None):
    _integer(start, 0, TOTAL_SETS, 'First set ordinal')
    _integer(stop, start, TOTAL_SETS, 'Exclusive last set ordinal')
    _integer(seed, 0, 2**31 - 1, 'Seed')
    for ordinal in range(start, stop):
        yield draw_set(plan, seed, ordinal, cancel)


class _SetOutcome(_Frozen):
    plan_hash: str = Field(pattern=r'^[a-f0-9]{64}$', strict=True)
    seed: int = Field(ge=0, lt=2**31, strict=True)
    policy: Literal['barrier_capped_elapsed_v1', 'fixed_elapsed_v1']
    set_index: int = Field(ge=0, lt=TOTAL_SETS, strict=True)
    trade_count: int = Field(ge=0, le=MAX_SOURCE_TRADES, strict=True)
    state: Literal['completed', 'failed']
    net_profit: float | None = Field(strict=True)
    error: str | None = Field(max_length=4096)

    @model_validator(mode='after')
    def complete_or_failure(self):
        if self.state == 'completed' and (self.net_profit is None or self.error is not None):
            raise ValueError('A completed twin set requires finite profit and no hidden failure.')
        if self.state == 'failed' and (self.net_profit is not None or not self.error or not self.error.strip()):
            raise ValueError('A failed twin set needs an explicit reason and no invented profit.')
        return self


def summarize(plan, seed, policy, results, cancel=None):
    _integer(seed, 0, 2**31 - 1, 'Seed')
    if policy not in EXECUTION_POLICIES:
        raise ValueError('Choose a declared twin execution interpretation.')
    real = sum((Decimal(str(s.net_profit)) for s in plan.sources), Decimal(0))
    seen = bytearray(TOTAL_SETS)
    observed = complete = failed = exceedances = 0
    for value in results:
        _cancel(cancel)
        if not plan.eligible:
            raise ValueError('An ineligible complete cohort cannot have executed twin-set outcomes.')
        row = _SetOutcome.model_validate(value)
        if (row.plan_hash, row.seed, row.policy, row.trade_count) != (plan.plan_hash, seed, policy, len(plan.sources)):
            raise ValueError('Twin-set outcome differs from the frozen full-cohort identity.')
        if seen[row.set_index]:
            raise ValueError('Duplicate twin-set ordinal; no denominator replacement is allowed.')
        seen[row.set_index] = 1
        observed += 1
        if row.state == 'failed':
            failed += 1
        else:
            complete += 1
            exceedances += Decimal(str(row.net_profit)) >= real
    eligible = plan.eligible and complete == TOTAL_SETS and failed == 0
    state = 'completed' if eligible else ('ineligible' if not plan.eligible else ('failed' if failed else 'incomplete'))
    interval = None
    if eligible:
        ci = binomtest(exceedances, TOTAL_SETS).proportion_ci(confidence_level=.95, method='exact')
        interval = [float(ci.low), float(ci.high)]
    return dict(plan_hash=plan.plan_hash, seed=seed, policy=policy, state=state, expected_sets=TOTAL_SETS,
                observed_sets=observed, complete_sets=complete, failed_sets=failed,
                source_trades=len(plan.sources), real_profit=str(real), exceedances=exceedances,
                raw_exceedance_fraction=exceedances / TOTAL_SETS if eligible else None,
                plus_one_diagnostic=(1 + exceedances) / (TOTAL_SETS + 1) if eligible else None,
                monte_carlo_interval_95=interval, adapted_pass=20 * exceedances < TOTAL_SETS if eligible else None,
                host_engine_parity_verified=False,
                limitations=['Conditional diagnostics for a frozen cohort, not independent markets or search-adjusted trading-edge evidence.',
                    'The exact interval describes finite independent set draws conditional on this model; it does not cover selection or market-model uncertainty.',
                    'Matching/grading alone does not establish original-account authority or verify financial execution.'])
