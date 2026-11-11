"""Public API input contracts."""
from datetime import date
import re
from typing import Literal,Any,Annotated
from pydantic import Field,model_validator
from .config import Contract,Strategy,Costs,Portfolio,identity

DatasetId=str

class Window(Contract):
    start: date
    end: date
    @model_validator(mode='after')
    def dates(self):
        if self.start>self.end: raise ValueError('Start must be on or before end.')
        return self

class Download(Window):
    symbols:list[str]=Field(default_factory=lambda:['SPY','QQQ','IWM','DIA','AAPL','MSFT'],min_length=1,max_length=20)
    @model_validator(mode='after')
    def valid_symbols(self):
        if any(not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',s) for s in self.symbols):
            raise ValueError('Use uppercase US stock/ETF symbols.')
        if len(set(self.symbols))!=len(self.symbols): raise ValueError('Duplicate instruments.')
        return self

class Selection(Window):
    symbols:list[str]=Field(min_length=1,max_length=20)

class RunInputs(Contract):
    dataset_id:str=Field(pattern=r'^[0-9a-f]{24}$')
    name:str=Field('Strategy experiment',min_length=1,max_length=100)
    costs:Costs=Field(default_factory=Costs)
    portfolio:Portfolio=Field(default_factory=Portfolio)
    start:date
    end:date
    seed:int=Field(42,ge=0,le=2**31-1)
    news_dates:list[date]|None=None
    news_calendar_id:str|None=Field(None,pattern=r'^[a-f0-9]{64}$')
    @model_validator(mode='after')
    def dates(self):
        if self.start>self.end: raise ValueError('Evaluation dates are reversed.')
        if self.news_dates is not None:raise ValueError('Use a versioned news calendar instead of raw news_dates.')
        return self

class Experiment(RunInputs):
    strategy:Strategy=Field(default_factory=Strategy)

class BorrowSensitivity(Experiment):
    """Fixed four-rate policy; callers cannot inject a different rate grid."""
    pass

class BenchmarkExperiment(RunInputs):
    @model_validator(mode='after')
    def no_news_filter(self):
        if self.news_dates is not None or self.news_calendar_id is not None: raise ValueError('Passive benchmarks do not apply a strategy news filter.')
        return self

class ControlsExperiment(Experiment):
    replicas:int=Field(20,ge=2,le=200)
    @model_validator(mode='after')
    def frozen_calendar_required(self):
        if self.strategy.news!='trade' and self.news_calendar_id is None:
            raise ValueError('Control news scenarios require a versioned calendar.')
        return self

class AblationExperiment(Experiment):
    field:str='target'
    alternatives:list[Any]=Field(default_factory=lambda:['2R','3R'],min_length=1,max_length=32)
    @model_validator(mode='after')
    def one_field(self):
        if self.field not in Strategy.model_fields:raise ValueError('Choose one public strategy field for an ablation.')
        if self.field=='limit_expiry' and self.strategy.entry!='limit':raise ValueError('Vary limit expiry only with a limit-entry baseline.')
        if self.field=='confirmation_window' and self.strategy.confirmation=='none':raise ValueError('Enable a confirmation before varying its waiting window.')
        if self.strategy.news!='trade' and self.news_calendar_id is None:raise ValueError('Ablation news scenarios require a versioned calendar.')
        self.arms()
        return self

    def arms(self):
        base=self.strategy.model_dump();seen={identity(self.strategy)};arms=[]
        for value in self.alternatives:
            if not isinstance(value,(str,int,float,bool,type(None))):raise ValueError('Alternative values must be JSON scalars.')
            arm=Strategy(**(base|{self.field:value}))
            if arm.news!='trade' and self.news_calendar_id is None:raise ValueError('News alternatives require the versioned calendar contract.')
            if [key for key,val in arm.model_dump().items() if val!=base[key]]!=[self.field]:
                raise ValueError('An alternative must change exactly the one selected public field.')
            if identity(arm) in seen:raise ValueError('Duplicate or unchanged ablation alternatives are not allowed.')
            seen.add(identity(arm));arms.append(arm)
        return [self.strategy,*sorted(arms,key=identity)]

class BehaviorExperiment(Window):
    dataset_id:str=Field(pattern=r'^[0-9a-f]{24}$')
    name:str=Field('Price behavior study',min_length=1,max_length=100)
    seed:int=Field(42,ge=0,le=2**31-1)
    timeframes:list[Literal['1m','5m','15m','1h','4h','1d']]=Field(default_factory=lambda:['5m','15m','1h','4h','1d'],min_length=1,max_length=6)
    shift_replicas:int=Field(20,ge=2,le=20)
    swing_strength:Literal[3]=3
    level_tolerance:Literal[0.25]=.25
    touch_horizon:Literal[50]=50
    bootstrap_resamples:Literal[2000]=2000
    @model_validator(mode='after')
    def unique_charts(self):
        if len(set(self.timeframes))!=len(self.timeframes):raise ValueError('Behavior charts must be unique.')
        return self

class PortfolioExperiment(RunInputs):
    configurations:list[Strategy]=Field(min_length=1,max_length=64)
    @model_validator(mode='after')
    def unique_rules(self):
        if len({identity(c) for c in self.configurations})!=len(self.configurations):
            raise ValueError('Portfolio configurations must be unique; duplicate saved names do not create another strategy.')
        return self

class SearchStatistics(Contract):
    effective_trials:list[Annotated[int,Field(strict=True,ge=1,le=100000)]]|None=Field(None,min_length=1,max_length=16)
    dispersion_mode:Literal['empirical','assumed']='empirical'
    trial_sharpe_std:float|None=Field(None,strict=True,ge=0,le=1000)

    @model_validator(mode='after')
    def assumptions(self):
        if (self.dispersion_mode=='assumed')!=(self.trial_sharpe_std is not None):
            raise ValueError('Assumed dispersion needs an explicit standard deviation; empirical mode does not take an ignored value.')
        if self.effective_trials is not None:
            if len(set(self.effective_trials))!=len(self.effective_trials):raise ValueError('Trial-count assumptions must be distinct.')
            object.__setattr__(self,'effective_trials',sorted(self.effective_trials))
        return self

    def resolve(self,count):
        if self.effective_trials is None:
            values=[1];power=10
            while power<count:values.append(power);power*=10
            values=sorted(set([*values,count]))
        else:values=self.effective_trials
        if any(n>count for n in values):raise ValueError('Effective-trial assumptions cannot exceed this search configuration count.')
        return type(self)(effective_trials=values,dispersion_mode=self.dispersion_mode,trial_sharpe_std=self.trial_sharpe_std)

class SearchSampling(Contract):
    mode:Literal['legacy','common_grid','common_random']='legacy'
    include_news:bool=Field(False,strict=True)
    minimum_signals:int=Field(40,strict=True,ge=1,le=1000000)
    minimum_trades:int=Field(30,strict=True,ge=1,le=1000000)
    minimum_sharpe:float=Field(.5,strict=True,ge=0,le=10)
    @model_validator(mode='after')
    def meaningful(self):
        if self.mode=='legacy' and (self.include_news or self.minimum_signals!=40 or self.minimum_trades!=30 or self.minimum_sharpe!=.5):
            raise ValueError('Legacy sampling does not use common-mode news or discovery gates.')
        return self

class SamplingPreview(Contract):
    families:list[str]=Field(min_length=1,max_length=10)
    timeframes:list[str]=Field(min_length=1,max_length=6)
    include_news:bool=Field(False,strict=True)

class Search(Experiment):
    count:int=Field(100,ge=1,le=100000)
    families:list[str]=Field(default_factory=lambda:['change_of_character'])
    timeframes:list[str]=Field(default_factory=lambda:['1h','1d'])
    statistics:SearchStatistics=Field(default_factory=SearchStatistics)
    sampling_policy:SearchSampling=Field(default_factory=SearchSampling)
    @model_validator(mode='after')
    def resolve_statistics(self):
        object.__setattr__(self,'statistics',self.statistics.resolve(self.count))
        if self.sampling_policy.mode!='legacy':
            if self.sampling_policy.include_news and not self.news_calendar_id:
                raise ValueError('Common-mode news variants require an explicit versioned calendar.')
            if self.strategy.news!='trade':
                raise ValueError('Common modes use sampling_policy.include_news, not the single-strategy news setting.')
        return self

class StrategySave(Contract):
    name:str=Field(min_length=1,max_length=100)
    strategy:Strategy
    parent_id:str|None=None

class SpreadContinuation(Contract):
    """The complete parent supplies every assumption; no override fields exist."""
    pass


class TradeTwinContinuation(Contract):
    """The original independent account supplies all financial assumptions."""
    part: int = Field(0,strict=True,ge=0)

class SpreadAccountScreen(Contract):
    mode:Literal['spread_selected']='spread_selected'
    include_news:bool=Field(False,strict=True)
    minimum_signals:int=Field(40,strict=True,ge=40,le=1000000)
    minimum_trades:int=Field(30,strict=True,ge=1,le=1000000)
    minimum_sharpe:float=Field(.5,strict=True,ge=0,le=10)

class SpreadExperiment(RunInputs):
    seed:int=Field(42,strict=True,ge=0,le=2**31-1)
    primary_symbol:str=Field(pattern=r'^[A-Z][A-Z0-9.\-]{0,14}$')
    settings:dict[str,Any]=Field(default_factory=dict)
    minimum_trades:int=Field(30,strict=True,ge=1,le=1000000)
    minimum_sharpe:float=Field(.5,strict=True,ge=0,le=10)
    statistics:SearchStatistics=Field(default_factory=SearchStatistics)
    @model_validator(mode='after')
    def freeze_settings(self):
        from .spread import SpreadSettings
        if 'seed' in self.settings and (type(self.settings['seed']) is not int or self.settings['seed']!=self.seed):raise ValueError('Use one strict integer master seed for the entire spread workflow.')
        resolved=SpreadSettings(**(self.settings|dict(seed=self.seed)))
        if resolved.include_news!=(self.news_calendar_id is not None):raise ValueError('Spread news inclusion requires its explicit frozen calendar; disabled news does not take an ignored calendar.')
        object.__setattr__(self,'settings',resolved.model_dump())
        object.__setattr__(self,'statistics',self.statistics.resolve(len(resolved.families)*resolved.per_family))
        return self


class PresentationSource(Contract):
    job_id:str=Field(pattern=r'^[a-f0-9]{32}$')
    part:int|None=Field(None,ge=0)
    window:Literal['report','discovery','validation']='report'


class PresentationExport(Contract):
    sources:list[PresentationSource]=Field(min_length=1,max_length=16)
    @model_validator(mode='after')
    def distinct_sources(self):
        keys={(s.job_id,s.part,s.window) for s in self.sources}
        if len(keys)!=len(self.sources):raise ValueError('Choose distinct saved sources.')
        if any(s.part is None and s.window!='report' for s in self.sources):
            raise ValueError('A discovery or validation window needs a saved configuration part.')
        return self

class Study(Contract):
    name:str=Field(min_length=1,max_length=100)
    study_mode:Literal['independent','portfolio']='independent'
    dataset_id:str=Field(pattern=r'^[0-9a-f]{24}$')
    discovery:Window
    validation:Window
    holdout:Window
    configurations:list[Strategy]=Field(min_length=1,max_length=100000)
    costs:Costs=Field(default_factory=Costs)
    portfolio:Portfolio=Field(default_factory=Portfolio)
    seed:int=Field(42,ge=0,le=2**31-1)
    minimum_trades:int=Field(30,ge=1,le=10000)
    minimum_sharpe:float=Field(.5,ge=0,le=10)
    news_calendar_id:str|None=Field(None,pattern=r'^[a-f0-9]{64}$')
    @model_validator(mode='after')
    def chronology(self):
        if not self.discovery.end<self.validation.start<=self.validation.end<self.holdout.start:
            raise ValueError('Discovery, validation and final dates must be ordered and disjoint.')
        if len({identity(c) for c in self.configurations})!=len(self.configurations):
            raise ValueError('Study configurations must be unique.')
        if self.study_mode=='portfolio':
            if len(self.configurations)>64:raise ValueError('A shared-portfolio study accepts at most64 unique rules.')
            object.__setattr__(self,'configurations',sorted(self.configurations,key=identity))
        if any(c.news!='trade' for c in self.configurations) and self.news_calendar_id is None:
            raise ValueError('Study news filters need a frozen versioned calendar.')
        return self
