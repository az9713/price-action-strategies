"""Validated public numerical contract. Unknown fields are rejected, never ignored."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
import hashlib
import json
from .borrow import BorrowScenario

FAMILIES = {
    'level_bounce': 'Level bounce', 'breakout': 'Breakout', 'flip_zone': 'Flip zone',
    'trend_pullback': 'Trend pullback', 'trend_line': 'Trend line',
    'break_of_structure': 'Break of structure', 'change_of_character': 'Change of character',
    'sweep_reclaim': 'Sweep and reclaim', 'supply_demand': 'Supply and demand',
    'fair_value_gap': 'Fair value gap',
}
TIMEFRAMES = {'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':390}
APPLICABILITY = {
    'gap_confluence':set(FAMILIES)-{'fair_value_gap'},
    'min_touches':{'level_bounce','breakout','flip_zone'},
    'level_shape':{'level_bounce','breakout','flip_zone'},
    'retest_window':{'flip_zone'},
    'pullback_min':{'trend_pullback'},'pullback_max':{'trend_pullback'},
    'impulse_bars':{'supply_demand'},'impulse_atr':{'supply_demand'},
    'sweep_depth':{'sweep_reclaim','change_of_character'},
    'reclaim_bars':{'sweep_reclaim','change_of_character'},
}
Family = Literal['level_bounce','breakout','flip_zone','trend_pullback','trend_line',
                 'break_of_structure','change_of_character','sweep_reclaim','supply_demand','fair_value_gap']
Timeframe = Literal['1m','5m','15m','1h','4h','1d']

class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False, validate_assignment=True)

class Strategy(Contract):
    family: Family = 'change_of_character'
    timeframe: Timeframe = '1h'
    trigger_timeframe: Timeframe | None = None
    direction: Literal['both','long','short'] = 'both'
    swing_strength: Literal[2,3,5,8] = 3
    level_tolerance: Literal[0.1,0.25,0.5] = 0.25
    min_touches: int = Field(1,ge=1,le=4)
    level_shape: Literal['line','zone'] = 'line'
    level_age: int = Field(96,ge=2,le=1000)
    confirmation: Literal['none','close_back','rejection','engulfing','either','lower_bos'] = 'none'
    confirmation_window: int = Field(3,ge=1,le=24)
    entry: Literal['next_open','same_close','limit'] = 'next_open'
    limit_expiry: int = Field(3,ge=1,le=96)
    stop_reference: Literal['swing','level','wick','gap'] = 'swing'
    stop_kind: Literal['hard','close'] = 'hard'
    stop_buffer: Literal[0.0,0.1,0.25] = 0.1
    target: Literal['1R','1.5R','2R','3R','4R','5R','swing'] = '1R'
    structure_exit: bool = False
    max_hold: Literal[0,24,96] = 96
    flat_at_close: bool = False
    trend_filter: Literal['none','setup','higher','daily'] = 'none'
    session_filter: Literal['core','open'] = 'core'
    skip_run_days: Literal[0,3,5] = 0
    skip_choppy: bool = False
    fresh_breakout: bool = False
    news: Literal['trade','skip','half'] = 'trade'
    sweep_required: bool = False
    sweep_depth: float = Field(0.0,ge=0,le=3)
    reclaim_bars: int = Field(3,ge=1,le=12)
    retest_window: int = Field(24,ge=1,le=96)
    pullback_min: float = Field(0.0,ge=0,le=5)
    pullback_max: float = Field(3.0,gt=0,le=10)
    impulse_bars: int = Field(2,ge=2,le=5)
    impulse_atr: Literal[1.5,2.0,3.0] = 1.5
    gap_confluence: bool = False

    @property
    def trigger(self):
        return self.trigger_timeframe or ('1h' if self.timeframe=='1d' else self.timeframe)

    @model_validator(mode='after')
    def combinations(self):
        for name,families in APPLICABILITY.items():
            if self.family not in families and getattr(self,name)!=type(self).model_fields[name].default:
                raise ValueError(f'{name} does not apply to {self.family}.')
        if self.family=='change_of_character' and not self.sweep_required and (self.sweep_depth!=0 or self.reclaim_bars!=3):
            raise ValueError('Sweep dials require the sweep prerequisite to be enabled.')
        order=list(TIMEFRAMES)
        setup=order.index(self.timeframe)
        trigger=order.index(self.trigger)
        if self.timeframe=='1d':
            if self.trigger!='1h': raise ValueError('Daily setups use hourly triggers.')
        elif not max(0,setup-2)<=trigger<=setup:
            raise ValueError('Trigger must be the setup chart or one/two steps lower.')
        if self.confirmation=='lower_bos' and trigger>=setup:
            raise ValueError('Lower-chart confirmation requires a lower trigger chart.')
        if self.stop_reference=='gap' and self.family!='fair_value_gap':
            raise ValueError('Gap-middle stop applies only to fair-value gaps.')
        if self.sweep_required and self.family!='change_of_character':
            raise ValueError('Sweep prerequisite applies only to change of character.')
        if self.fresh_breakout and self.family not in {'breakout','break_of_structure','change_of_character','flip_zone'}:
            raise ValueError('Fresh-breakout filter requires a structure/breakout setup.')
        if self.pullback_min>=self.pullback_max: raise ValueError('Pullback bounds are reversed.')
        if self.flat_at_close and self.timeframe in {'4h','1d'}:
            raise ValueError('Session-flat exit is incompatible with 4h/daily setups.')
        return self

class Costs(Contract):
    commission_per_share: float = Field(0.005,ge=0,le=1)
    minimum_commission: float = Field(0,ge=0,le=100)
    fixed_fee_per_order: float = Field(0,ge=0,le=100)
    sell_fee_per_dollar: float = Field(0,ge=0,le=.01)
    spread_bps: float = Field(1,ge=0,le=1000)
    slippage_bps: float = Field(1,ge=0,le=1000)
    borrow_annual: float = Field(.03,ge=0,le=5)
    borrow_available: bool = True
    borrow_scenario: BorrowScenario | None = None

class Portfolio(Contract):
    capital: float = Field(100000,gt=0,le=1e10)
    risk_fraction: float = Field(.005,gt=0,le=.1)
    symbol_exposure: float = Field(.25,gt=0,le=1)
    total_exposure: float = Field(1,gt=0,le=1)
    participation: float = Field(.05,gt=0,le=1)
    tick_size: float = Field(.01,gt=0,le=10)

def canonical(value):
    return json.dumps(value.model_dump() if isinstance(value,BaseModel) else value,
                      sort_keys=True,separators=(',',':'),allow_nan=False)

def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()
