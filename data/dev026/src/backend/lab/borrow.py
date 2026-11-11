"""Explicit lending scenarios. No broker, credential, price or network IO."""
from bisect import bisect_left,bisect_right
from datetime import date,datetime,timezone
from typing import Literal
from zoneinfo import ZoneInfo
import re
from pydantic import BaseModel,ConfigDict,Field,field_validator,model_validator

NY=ZoneInfo('America/New_York')


class BorrowModel(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False,validate_assignment=True)


def symbol_text(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',value):
        raise ValueError('Borrow symbols require uppercase instrument identifiers.')
    return value


class BorrowEvent(BorrowModel):
    symbol:str
    effective_at:str
    available:bool=Field(strict=True)
    annual_rate:float=Field(ge=0,le=5,strict=True)
    recall:bool=Field(strict=True)

    @field_validator('symbol')
    @classmethod
    def valid_symbol(cls,value):return symbol_text(value)

    @field_validator('effective_at')
    @classmethod
    def minute(cls,value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:00(?:Z|[+-]\d{2}:\d{2})',value):
            raise ValueError('Borrow event needs an explicit ISO timezone at a whole minute.')
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        return parsed.astimezone(timezone.utc).isoformat()

    @model_validator(mode='after')
    def consistent(self):
        if self.recall and self.available:raise ValueError('A recalled state cannot allow new short loans.')
        return self


class BorrowScenario(BorrowModel):
    name:str=Field(min_length=1,max_length=100)
    start:str
    end:str
    symbols:list[str]=Field(min_length=1,max_length=1000)
    complete:bool=Field(False,strict=True)
    mode:Literal['assumed','synthetic']='assumed'
    note:str=Field('',max_length=1000)
    events:list[BorrowEvent]=Field(default_factory=list,max_length=10000)

    @field_validator('name')
    @classmethod
    def name_text(cls,value):
        if not value.strip() or any(ord(c)<32 for c in value):raise ValueError('Borrow scenario name requires plain nonblank text.')
        return value.strip()

    @field_validator('start','end')
    @classmethod
    def calendar_date(cls,value):
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):raise ValueError('Borrow coverage requires YYYY-MM-DD dates.')
        date.fromisoformat(value);return value

    @model_validator(mode='after')
    def valid(self):
        if self.start>self.end or (date.fromisoformat(self.end)-date.fromisoformat(self.start)).days>3660:
            raise ValueError('Borrow coverage must be ordered and at most ten years.')
        symbols=[symbol_text(s) for s in self.symbols]
        if len(set(symbols))!=len(symbols):raise ValueError('Borrow symbols must be distinct.')
        seen=set()
        for event in self.events:
            key=(event.symbol,event.effective_at)
            if key in seen:raise ValueError('Duplicate borrow event for the same symbol and instant.')
            seen.add(key);day=datetime.fromisoformat(event.effective_at).astimezone(NY).date().isoformat()
            if event.symbol not in symbols or not self.start<=day<=self.end:
                raise ValueError('Borrow event is outside declared symbol/date coverage.')
        object.__setattr__(self,'symbols',sorted(symbols))
        object.__setattr__(self,'events',sorted(self.events,key=lambda e:(e.symbol,e.effective_at)))
        return self


class BorrowSchedule:
    def __init__(self,spec,annual_rate,available):
        self.spec=BorrowScenario(**spec.model_dump()) if isinstance(spec,BorrowScenario) else BorrowScenario(**spec)
        self.initial=(available,annual_rate,False)
        self.events={symbol:[] for symbol in self.spec.symbols}
        for event in self.spec.events:self.events[event.symbol].append(event)
        self.times={s:[datetime.fromisoformat(e.effective_at) for e in events] for s,events in self.events.items()}
        self.recalls={s:[datetime.fromisoformat(e.effective_at) for e in events if e.recall] for s,events in self.events.items()}

    def validate(self,symbols,start,end):
        if not self.spec.complete or not set(symbols)<=set(self.spec.symbols) or str(start)<self.spec.start or str(end)>self.spec.end or str(start)>str(end):
            raise ValueError('A complete borrowing scenario must cover every instrument and evaluation date.')

    def aware(self,when):
        if not isinstance(when,datetime) or when.tzinfo is None or when.utcoffset() is None:
            raise ValueError('Borrow decisions require an aware timestamp.')
        return when.astimezone(timezone.utc)

    def state(self,symbol,when):
        when=self.aware(when)
        if symbol not in self.times:raise ValueError('Borrow symbol is outside scenario coverage.')
        index=bisect_right(self.times[symbol],when)-1
        if index<0:return self.initial
        event=self.events[symbol][index]
        return event.available,event.annual_rate,event.recall

    def rate_seconds(self,symbol,since,until):
        since=self.aware(since);until=self.aware(until)
        if until<since:raise ValueError('Borrow accrual interval is reversed.')
        rate=self.state(symbol,since)[1];total=0.;cursor=since
        index=bisect_right(self.times[symbol],since)
        stop=bisect_left(self.times[symbol],until)
        for i in range(index,stop):
            at=self.times[symbol][i];event=self.events[symbol][i]
            total+=rate*(at-cursor).total_seconds();cursor=at;rate=event.annual_rate
        return total+rate*(until-cursor).total_seconds()

    def recalled(self,symbol,entry,when):
        entry=self.aware(entry);when=self.aware(when)
        if when<entry:raise ValueError('Borrow recall interval is reversed.')
        if symbol not in self.recalls:raise ValueError('Borrow symbol is outside scenario coverage.')
        return bisect_right(self.recalls[symbol],when)>bisect_left(self.recalls[symbol],entry)
