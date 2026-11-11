"""Prespecified research arms and complete all-version family arithmetic.

This numerical reducer accepts accounts whose original authority has already been
verified by its caller. It is not a public supplied-outcome certification API.
Equal-weight research averages are not executable shared-capital portfolios.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from collections.abc import Mapping
import json
import math
import re
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator, model_validator
from .config import Strategy, identity, canonical
from .data import _calendar
from .models import Study, Window

SOURCE_VIDEO = 'https://www.youtube.com/watch?v=z97PnFIPoFg'
SYMBOL = r'^[A-Z][A-Z0-9.\-]{0,14}$'


class FunnelWindow(Window):
    @field_validator('start', 'end', mode='before')
    @classmethod
    def exact_dates(cls, value):
        if type(value) is date:
            return value
        if not isinstance(value, str) or re.fullmatch(r'\d{4}-\d{2}-\d{2}', value) is None:
            raise ValueError('Use an explicit ISO calendar date; timestamps and numeric dates are not research windows.')
        date.fromisoformat(value)
        return value


class FunnelStudy(Study):
    """Additive study contract; the existing basic/portfolio study stays intact."""
    study_mode: Literal['independent'] = 'independent'
    discovery: FunnelWindow
    validation: FunnelWindow
    holdout: FunnelWindow
    primary_symbol: str = Field(pattern=SYMBOL)
    replication_symbol: str = Field(pattern=SYMBOL)
    replication_dataset_id: str | None = Field(None, pattern=r'^[0-9a-f]{24}$')
    era_one: FunnelWindow
    era_two: FunnelWindow
    minimum_signals: int = Field(40, strict=True, ge=1, le=1000000)
    replication_minimum_sharpe: float = Field(.3, strict=True, ge=0, le=10)
    family_minimum_sharpe: float = Field(.5, strict=True, ge=0, le=10)

    @model_validator(mode='after')
    def replication_axes(self):
        if self.primary_symbol == self.replication_symbol:
            raise ValueError('Instrument replication requires a different declared instrument.')
        if not (self.discovery.start <= self.era_one.start <= self.era_one.end
                < self.era_two.start <= self.era_two.end <= self.discovery.end):
            raise ValueError('The two ordered, disjoint discovery eras must be inside discovery, before chronological validation.')
        return self


def freeze_specification(value):
    if not isinstance(value, FunnelStudy):
        raise ValueError('A complete validated research-funnel study is required.')
    # Serialized detached values are what registration hashes, never aliases to
    # mutable configuration objects owned by a caller.
    return json.loads(canonical(value.model_dump(mode='json') | dict(
        source_video=SOURCE_VIDEO, funnel_version=1,
        replication_role='instrument_discovery_replication_not_untouched_validation',
        family_aggregation='all_prespecified_versions_equal_weight',
        stability_role='descriptive_frozen_neighbor_diagnostics_no_invented_source_gate')))


def _cancel(cancel):
    if cancel and cancel():
        raise InterruptedError('Research-funnel aggregation canceled; no partial family certified.')


def _amount(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError('Original finite numeric account values are required.')
    text = str(value)
    if len(text) > 512:
        raise ValueError('Original numerical value exceeds the visible arithmetic bound.')
    try:
        number = Decimal(text)
    except InvalidOperation as error:
        raise ValueError('Original numerical account value is malformed.') from error
    if not number.is_finite() or abs(number.adjusted()) > 1000:
        raise ValueError('Original numerical account value must be finite and bounded.')
    return Fraction(number)


def _encoded(value):
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def _float(value):
    try:
        converted = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError('Research summary exceeds finite statistical arithmetic.') from error
    if not math.isfinite(converted):
        raise ValueError('Research summary exceeds finite statistical arithmetic.')
    return converted


def _stats(calendar, pnl, capital, minimum_sharpe, *, compatibility=False):
    count = len(pnl)
    net = sum(pnl, Fraction())
    balance = capital
    observations = []
    solvent = capital > 0
    for change in pnl:
        if compatibility:
            observations.append(_float(change))
        elif balance > 0:
            observations.append(_float(change / balance))
        else:
            solvent = False
        balance += change
        solvent = solvent and balance > 0
    sharpe = None
    if count > 1 and len(observations) == count and (compatibility or solvent):
        mean = _float(math.fsum(x/count for x in observations))
        root = math.sqrt(count-1)
        deviation = _float(math.hypot(*(x/root-mean/root for x in observations)))
        if deviation > 0:
            sharpe = _float(mean/deviation*math.sqrt(252))
    annualized = _float(net*252/count) if count else None
    return dict(daily=[dict(date=day, mean_pnl=_encoded(change)) for day,change in zip(calendar,pnl)],
                sessions=count, net_profit=_encoded(net), annualized_profit=annualized,
                sharpe=sharpe, gate_pass=bool(count and net>0 and sharpe is not None and sharpe>=minimum_sharpe),
                minimum_sharpe=minimum_sharpe, window_gate_only=True,
                risk_basis='Exit-day net P&L / sample P&L deviation; source compatibility' if compatibility else
                    'Daily marked equity percentage returns / sample deviation;252 sessions per year',
                undefined=[] if sharpe is not None else ['Sharpe requires at least two varying eligible observations and a valid capital basis.'])


def _dates(report):
    try:
        start = date.fromisoformat(report['start']);end = date.fromisoformat(report['end'])
    except (TypeError,ValueError,KeyError) as error:
        raise ValueError('Original account dates are required.') from error
    if start > end:
        raise ValueError('Original account dates are reversed.')
    return _calendar(start.year,end.year).sessions_in_range(start.isoformat(),end.isoformat()).strftime('%Y-%m-%d').tolist()


def family_average(configurations, reports, *, minimum_sharpe=.5, cancel=None):
    """Complete equal-weight mean of finite original marked and realized P&L.

    Missing original outcomes remain incomplete; a caller cannot quietly shrink
    a frozen family to winners. All eligible no-trade sessions remain present.
    """
    _cancel(cancel)
    if (not isinstance(configurations,(list,tuple)) or not configurations
            or any(not isinstance(c,Strategy) for c in configurations)):
        raise ValueError('A complete nonempty family of original strategies is required.')
    ids = [identity(c) for c in configurations]
    if len(set(ids))!=len(ids) or len({c.family for c in configurations})!=1:
        raise ValueError('Family versions must be distinct and belong to one named family.')
    if not isinstance(reports,Mapping) or set(reports)!=set(ids):
        raise ValueError('Every original family version is required; no profitable subset is accepted.')
    threshold = _float(_amount(minimum_sharpe))
    if not 0 <= threshold <= 10:
        raise ValueError('Family Sharpe threshold is outside its prespecified bounds.')
    base = dict(family=configurations[0].family,version_count=len(ids),members=sorted(ids),
                aggregation_kind='equal_weight_research_average_not_shared_capital_execution',
                source_video=SOURCE_VIDEO,host_engine_parity_verified=False)
    failed = sorted(key for key,value in reports.items() if value is None)
    if failed:
        return base | dict(state='incomplete',failed_members=failed,marked=None,realized_exit_day_compatibility=None,
                           reasons=['At least one original account failed or is unavailable; no partial family result.'])
    reference = None;calendar=None;capital=None;marked=None;realized=None;hashes={}
    for configuration,key in zip(configurations,ids):
        _cancel(cancel)
        report = reports[key]
        if (not isinstance(report,dict) or report.get('report_type')!='single_strategy'
                or report.get('config_id')!=key or report.get('config')!=configuration.model_dump(mode='json')):
            raise ValueError('Original account/configuration identity differs.')
        try:
            assumptions = {k:report[k] for k in ['dataset_id','dataset_manifest_hash','core_hash','start','end','costs','portfolio']}
            account_capital = _amount(report['portfolio']['capital'])
            equity = report['equity'];trades = report['trades']
        except (KeyError,TypeError) as error:
            raise ValueError('Complete original account assumptions and records are required.') from error
        if account_capital <= 0 or not isinstance(equity,list) or not isinstance(trades,list):
            raise ValueError('Positive capital and complete original account arrays are required.')
        days = _dates(report)
        if any(not isinstance(row,dict) for row in equity) or [row.get('date') for row in equity]!=days:
            raise ValueError('Original family accounts require the same complete ordered exchange-session calendar; no zero padding.')
        signature = identity(assumptions)
        if reference is None:
            reference=signature;calendar=days;capital=account_capital
            marked=[Fraction() for _ in days];realized=[Fraction() for _ in days]
        elif signature!=reference or days!=calendar:
            raise ValueError('Family account capital, cost, source, core or calendar assumptions differ.')
        previous=capital
        for index,row in enumerate(equity):
            _cancel(cancel)
            value=_amount(row.get('equity'));marked[index]+=value-previous;previous=value
        by_day={day:index for index,day in enumerate(calendar)}
        for trade in trades:
            _cancel(cancel)
            try:
                exited=datetime.fromisoformat(trade['exit_at'])
                if exited.tzinfo is None or exited.utcoffset() is None:
                    raise ValueError('Naive original trade clock.')
                day=exited.astimezone(ZoneInfo('America/New_York')).date().isoformat()
                if day not in by_day:
                    raise ValueError('Original exit is outside the complete account calendar.')
                realized[by_day[day]]+=_amount(trade['net_pnl'])
            except (KeyError,TypeError,ValueError) as error:
                raise ValueError('Original complete realized trade evidence is invalid.') from error
        hashes[key]=identity(report)
    marked=[value/len(ids) for value in marked];realized=[value/len(ids) for value in realized]
    _cancel(cancel)
    return base | dict(state='complete' if calendar else 'insufficient',failed_members=[],source_report_hashes=hashes,
                       normalization_capital=_encoded(capital),
                       marked=_stats(calendar,marked,capital,threshold),
                       realized_exit_day_compatibility=_stats(calendar,realized,capital,threshold,compatibility=True))
