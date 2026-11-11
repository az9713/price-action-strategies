"""Immutable minute datasets, exchange calendars, audits and causal split normalization."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from datetime import date
import hashlib
import json
import os
import tempfile
import numpy as np
import pandas as pd
import exchange_calendars as xcals
from .config import TIMEFRAMES, canonical, identity

REQUIRED=['symbol','timestamp','open','high','low','close','volume']
ALIASES={'t':'timestamp','ts_event':'timestamp','o':'open','h':'high','l':'low','c':'close','v':'volume'}

class DataError(ValueError):
    pass

@dataclass(frozen=True)
class Action:
    symbol: str
    ex_date: str
    kind: str  # split: new shares / old shares; dividend: dollars per current share
    value: float
    pay_date: str | None = None

    def __post_init__(self):
        date.fromisoformat(self.ex_date)
        if self.pay_date: date.fromisoformat(self.pay_date)
        if self.kind not in {'split','dividend'} or not np.isfinite(self.value) or self.value<=0:
            raise DataError('Invalid corporate action.')

@lru_cache(maxsize=32)
def schedule(start:str,end:str):
    if start>end: raise DataError('Session date range is reversed.')
    cal=_calendar(date.fromisoformat(start).year,date.fromisoformat(end).year)
    rows=cal.schedule.loc[start:end].copy()
    return {pd.Timestamp(day).strftime('%Y-%m-%d'):(pd.Timestamp(row['open']),pd.Timestamp(row['close']))
            for day,row in rows.iterrows()}

@lru_cache(maxsize=8)
def _calendar(first_year,last_year):
    return xcals.get_calendar('XNYS',start=f'{first_year}-01-01',end=f'{last_year+1}-01-01')

def normalize(frame:pd.DataFrame, timezone_hint:str|None=None):
    if len(frame)>15_000_000: raise DataError('Import exceeds 15 million rows; partition the input.')
    if frame.empty: raise DataError('No price rows were supplied.')
    frame=frame.copy()
    if any(old in frame and new in frame for old,new in ALIASES.items()):
        raise DataError('Ambiguous original and alias columns.')
    frame.rename(columns=ALIASES,inplace=True)
    missing=set(REQUIRED)-set(frame)
    if missing: raise DataError('Missing columns: '+', '.join(sorted(missing)))
    frame=frame[REQUIRED]
    if frame.symbol.isna().any(): raise DataError('Missing symbol.')
    frame['symbol']=frame.symbol.astype(str).str.upper().str.strip()
    if not frame.symbol.str.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}').all(): raise DataError('Invalid symbol.')
    try:
        aware=isinstance(frame.timestamp.dtype,pd.DatetimeTZDtype)
        if frame.timestamp.dtype=='object' or pd.api.types.is_string_dtype(frame.timestamp.dtype):
            flags=frame.timestamp.astype(str).str.contains(r'(?:Z|[+-]\d{2}:?\d{2})$',regex=True)
            if flags.any() and not flags.all(): raise DataError('Mixed naive and timezone-aware timestamps.')
            aware=bool(flags.all())
        stamps=pd.to_datetime(frame.timestamp,format='mixed',errors='raise',utc=True if aware else False)
        if not isinstance(stamps.dtype,pd.DatetimeTZDtype):
            if not timezone_hint: raise DataError('Naive timestamps need an explicit timezone.')
            stamps=stamps.dt.tz_localize(timezone_hint,ambiguous='raise',nonexistent='raise')
        frame['timestamp']=stamps.dt.tz_convert('UTC')
    except DataError: raise
    except Exception as exc: raise DataError('Unparseable or mixed/ambiguous timestamps.') from exc
    if (frame.timestamp.dt.second.ne(0)|frame.timestamp.dt.microsecond.ne(0)|frame.timestamp.isna()).any():
        raise DataError('Minute bar-open timestamps must align to exact minutes.')
    for col in REQUIRED[2:]:
        try: frame[col]=pd.to_numeric(frame[col],errors='raise').astype(float)
        except Exception as exc: raise DataError('Nonnumeric '+col) from exc
    if not np.isfinite(frame[REQUIRED[2:]].to_numpy()).all(): raise DataError('Nonfinite OHLCV.')
    invalid=(frame.low<=0)|(frame.volume<0)|(frame.low>frame[['open','close']].min(axis=1))|(frame.high<frame[['open','close']].max(axis=1))
    if invalid.any(): raise DataError(f'Invalid OHLCV in {int(invalid.sum())} rows.')
    duplicated=frame.duplicated(['symbol','timestamp'],keep=False)
    conflicting=frame[duplicated].groupby(['symbol','timestamp']).nunique().max(axis=1)
    if (conflicting>1).any(): raise DataError('Conflicting duplicate minute bars.')
    original_order=frame[['symbol','timestamp']].copy()
    duplicate_count=int(frame.duplicated(['symbol','timestamp']).sum())
    frame=frame.drop_duplicates(['symbol','timestamp']).sort_values(['timestamp','symbol']).reset_index(drop=True)
    reordered=not frame[['symbol','timestamp']].equals(original_order.reset_index(drop=True))
    return frame,{'identical_duplicates_removed':duplicate_count,'reordered':reordered}

def regular_minutes(frame):
    local=frame.timestamp.dt.tz_convert('America/New_York')
    sessions=local.dt.strftime('%Y-%m-%d')
    sched=schedule(sessions.min(),sessions.max())
    if not sched:
        out=frame.iloc[:0].copy()
        out['session']=pd.Series(dtype=str)
        out['session_open']=pd.Series(dtype='datetime64[ns, UTC]')
        out['session_close']=pd.Series(dtype='datetime64[ns, UTC]')
        return out,len(frame)
    opens=sessions.map({k:v[0] for k,v in sched.items()})
    closes=sessions.map({k:v[1] for k,v in sched.items()})
    inside=opens.notna()&(frame.timestamp>=opens)&(frame.timestamp<closes)
    out=frame.loc[inside].copy()
    out['session']=sessions[inside]
    out['session_open']=opens[inside]
    out['session_close']=closes[inside]
    return out.reset_index(drop=True),int((~inside).sum())

def audit(frame, start:str|None=None, end:str|None=None):
    regular,outside=regular_minutes(frame)
    if regular.empty: raise DataError('No regular-session minute bars.')
    start=start or regular.session.min()
    end=end or regular.session.max()
    sched=schedule(start,end)
    rows=[]
    for symbol in sorted(frame.symbol.unique()):
        group=regular[regular.symbol==symbol]
        by_session={k:g for k,g in group.groupby('session')}
        for day,(opened,closed) in sched.items():
            expected=int((closed-opened).total_seconds()/60)
            current=by_session.get(day)
            actual=0 if current is None else len(current)
            missing=expected-actual
            rows.append(dict(symbol=symbol,session=day,expected=expected,observed=actual,missing=missing,
                             zero_volume=0 if current is None else int(current.volume.eq(0).sum()),
                             complete=missing==0))
    missing_total=sum(r['missing'] for r in rows)
    return {'rows':len(frame),'regular_rows':len(regular),'outside_regular_rows':outside,
            'symbols':sorted(frame.symbol.unique()),'start':start,'end':end,
            'missing_minutes':missing_total,'incomplete_sessions':sum(not r['complete'] for r in rows),
            'sessions':rows,'eligible':missing_total==0,
            'policy':'Missing expected minutes block normal research; no prices are forward-filled. Zero-volume bars are flagged separately.'}

def prepare(frame,actions=()):
    regular,_=regular_minutes(frame)
    regular['factor']=1.0
    for symbol,idx in regular.groupby('symbol').groups.items():
        splits=sorted([a for a in actions if a.symbol==symbol and a.kind=='split'],key=lambda a:a.ex_date)
        for action in splits:
            # Forward normalization uses only splits effective by this session.
            active=regular.loc[idx,'session']>=action.ex_date
            selected=regular.loc[idx].index[active]
            regular.loc[selected,'factor']*=action.value
    return regular

def aggregate(regular,timeframe):
    if timeframe not in TIMEFRAMES: raise DataError('Unknown chart timeframe.')
    df=regular.copy()
    minutes=TIMEFRAMES[timeframe]
    df['bucket']=0 if timeframe=='1d' else ((df.timestamp-df.session_open).dt.total_seconds()//(60*minutes)).astype(int)
    for col in ['open','high','low','close']: df[col]*=df.factor
    group=df.groupby(['symbol','session','bucket'],sort=True)
    result=group.agg(open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'),
                     volume=('volume','sum'),count=('timestamp','size'),session_open=('session_open','first'),
                     session_close=('session_close','first'),factor=('factor','last')).reset_index()
    result['timestamp']=result.session_open+pd.to_timedelta(result.bucket*minutes,unit='m')
    nominal=result.timestamp+pd.to_timedelta(minutes,unit='m')
    result['available_at']=pd.concat([nominal,result.session_close],axis=1).min(axis=1)
    result['duration_minutes']=((result.available_at-result.timestamp).dt.total_seconds()/60).astype(int)
    result['complete']=result['count']==result.duration_minutes
    result['partial_length']=result.duration_minutes<minutes
    return result.sort_values(['available_at','symbol']).reset_index(drop=True)

def atomic_json(path:Path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=path.parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            f.write(canonical(value));f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def save_dataset(root:Path,frame,metadata,actions=(),start=None,end=None):
    frame,normalization=normalize(frame)
    quality=audit(frame,start,end)
    digest=hashlib.sha256(frame.to_csv(index=False,float_format='%.17g').encode()).hexdigest()
    payload=dict(metadata=metadata,bars_sha256=digest,normalization=normalization,quality=quality,
                 actions=[a.__dict__ for a in actions],version=1)
    dataset_id=identity(payload)[:24]
    target=root/dataset_id
    target.mkdir(parents=True,exist_ok=True)
    destination=target/'minutes.parquet'
    if not (target/'manifest.json').exists():
        tmp=target/'minutes.parquet.tmp'
        frame.to_parquet(tmp,index=False)
        os.replace(tmp,destination)
        payload.update(id=dataset_id,parquet_sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
        atomic_json(target/'manifest.json',payload)
    return load_dataset(root,dataset_id)[1]

def read_manifest(root:Path,dataset_id):
    import re
    if not re.fullmatch(r'[0-9a-f]{24}',dataset_id): raise DataError('Invalid dataset ID.')
    target=root/dataset_id
    payload=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
    if payload.get('id')!=dataset_id: raise DataError('Dataset identity mismatch.')
    if identity({k:v for k,v in payload.items() if k not in {'id','parquet_sha256'}})[:24]!=dataset_id:
        raise DataError('Dataset manifest hash mismatch.')
    return payload

def load_dataset(root:Path,dataset_id):
    payload=read_manifest(root,dataset_id)
    target=root/dataset_id
    if hashlib.sha256((target/'minutes.parquet').read_bytes()).hexdigest()!=payload['parquet_sha256']:
        raise DataError('Dataset file hash mismatch; the dataset is corrupt or modified.')
    frame=pd.read_parquet(target/'minutes.parquet')
    digest=hashlib.sha256(frame.to_csv(index=False,float_format='%.17g').encode()).hexdigest()
    if digest!=payload['bars_sha256']: raise DataError('Normalized input hash mismatch.')
    return frame,payload

def load_window(root:Path,dataset_id,start,end,symbols=None):
    payload=read_manifest(root,dataset_id)
    path=root/dataset_id/'minutes.parquet'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=payload['parquet_sha256']:
        raise DataError('Dataset file hash mismatch.')
    lo=pd.Timestamp(start,tz='America/New_York').tz_convert('UTC')
    hi=(pd.Timestamp(end)+pd.Timedelta(days=1)).tz_localize('America/New_York').tz_convert('UTC')
    filters=[('timestamp','>=',lo),('timestamp','<',hi)]
    if symbols: filters.append(('symbol','in',symbols))
    return pd.read_parquet(path,filters=filters),payload

def select_dataset(root:Path,dataset_id,symbols,start=None,end=None):
    parent=read_manifest(root,dataset_id)
    symbols=sorted(set(symbols))
    if not symbols or set(symbols)-set(parent['quality']['symbols']): raise DataError('Selection contains absent/unknown instruments.')
    start=start or parent['quality']['start'];end=end or parent['quality']['end']
    if start<parent['quality']['start'] or end>parent['quality']['end'] or start>end:
        raise DataError('Selection must stay inside the parent dataset dates.')
    selected,_=load_window(root,dataset_id,start,end,symbols)
    actions=[Action(**a) for a in parent['actions'] if a['symbol'] in symbols and start<=a['ex_date']<=end]
    metadata={**parent['metadata'],'selection':dict(parent_id=dataset_id,symbols=symbols,start=start,end=end)}
    return save_dataset(root,selected,metadata,actions,start,end)
