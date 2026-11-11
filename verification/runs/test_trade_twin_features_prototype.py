"""Independent primitive-candle/Wilder checks for the next feature component."""
from datetime import timedelta
from decimal import Decimal
import copy,importlib.util,json,math,os,random
from pathlib import Path
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy
from backend.lab.data import prepare,normalize,Action

path=Path(os.environ['PA_FEATURE_PROTOTYPE_PATH'])
spec=importlib.util.spec_from_file_location('owned_candidate_prototype',path);prototype=importlib.util.module_from_spec(spec);spec.loader.exec_module(prototype)

def rows(days=('2026-11-04',),actions=()):
    frame=pd.concat([minute_frame(day,'SPY') for day in days],ignore_index=True)
    frame[['open','high','low','close']]=[100.,101.,99.,100.]
    for action in actions:
        if action.kind=='split':frame.loc[frame.timestamp.dt.tz_convert('America/New_York').dt.date.astype(str)>=action.ex_date,['open','high','low','close']]/=action.value
    return prepare(normalize(frame)[0],actions)

def oracle(frame,tf,start,end):
    """No production aggregation, ATR, as-of join or feature function."""
    D=lambda v:Decimal(str(v));width={'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':390}[tf]
    buckets={}
    for row in sorted(frame.to_dict('records'),key=lambda r:r['timestamp']):
        index=0 if tf=='1d' else int((row['timestamp']-row['session_open']).total_seconds()//(width*60))
        buckets.setdefault((row['session'],index),[]).append(row)
    candles=[]
    for (_,index),values in sorted(buckets.items()):
        opened=values[0]['session_open']+timedelta(minutes=index*width)
        closed=min(opened+timedelta(minutes=width),values[0]['session_close'])
        if len(values)!=int((closed-opened).total_seconds()//60):continue
        high=max(D(v['high'])*D(v['factor']) for v in values);low=min(D(v['low'])*D(v['factor']) for v in values)
        close=D(values[-1]['close'])*D(values[-1]['factor'])
        previous=candles[-1]['close'] if candles else D(values[0]['close'])*D(values[0]['factor'])
        tr=max(high-low,abs(high-previous),abs(low-previous))
        i=len(candles);atr=None
        if i==14:atr=sum((c['tr'] for c in candles),D(0))/14
        elif i>14:atr=(candles[-1]['atr']*13+candles[-1]['tr'])/14
        candles.append(dict(at=closed,tr=tr,atr=atr,close=close))
    result=[]
    for row in frame.sort_values('timestamp').to_dict('records'):
        if not start<=row['session']<=end:continue
        known=[c for c in candles if c['at']<=row['timestamp']]
        if not known or known[-1]['atr'] is None or known[-1]['atr']<=0:continue
        result.append(dict(symbol=row['symbol'],entry_at=row['timestamp'].isoformat(),reference_price=float(row['open']),atr=known[-1]['atr']/D(row['factor']),atr_available_at=known[-1]['at'].isoformat()))
    return result

def check(frame,cfg,start='2026-11-04',end='2026-11-04'):
    original=frame.copy(deep=True);actual=prototype.candidate_features(frame,cfg,['SPY'],start,end)
    expected=oracle(frame,cfg.timeframe,start,end)
    assert len(actual['moments'])==len(expected)
    for a,b in zip(actual['moments'],expected):
        assert set(a)==set(b)
        for k in a:
            if k=='atr':assert abs(Decimal(str(a[k]))-b[k])<=Decimal('1e-9')
            else:assert a[k]==b[k]
        assert a['atr_available_at']<=a['entry_at']
    assert actual['clock']['SPY']==[r.timestamp.isoformat() for r in frame.itertuples(index=False) if start<=r.session<=end]
    pd.testing.assert_frame_equal(frame,original)
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        import hashlib
        payload=dict(configuration=cfg.model_dump(),start=start,end=end,actual=actual,reference=expected)
        raw=json.dumps(payload,sort_keys=True,default=str);folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'feature-oracles';folder.mkdir(exist_ok=True)
        (folder/(hashlib.sha256(raw.encode()).hexdigest()+'.json')).write_text(raw,encoding='utf-8')
    return actual

@pytest.mark.parametrize('tf',['1m','5m','15m','1h','4h','1d'])
def test_setup_chart_completed_asof_and_independent_wilder(tf):
    frame=rows();cfg=Strategy(timeframe=tf)
    result=check(frame,cfg)
    if tf=='1m':
        assert result['moments'][0]['entry_at']=='2026-11-04T14:45:00+00:00'
        assert all(m['atr']==2 for m in result['moments'])
    if tf in {'1h','4h','1d'}:assert not result['moments']

@pytest.mark.parametrize('seed',range(16))
def test_random_ohlc_completed_wilder_and_future_suffix_invariance(seed):
    rng=random.Random(seed);frame=rows();price=100
    for index in range(len(frame)):
        opened=round(price+rng.uniform(-.2,.2),4);closed=round(opened+rng.uniform(-.5,.5),4)
        frame.loc[index,['open','high','low','close']]=[opened,max(opened,closed)+.3,min(opened,closed)-.3,closed];price=closed
    cfg=Strategy(timeframe=rng.choice(['1m','5m','15m']));result=check(frame,cfg)
    changed=frame.copy();changed.loc[250:,['open','high','low','close']]*=3
    later=prototype.candidate_features(changed,cfg,['SPY'],'2026-11-04','2026-11-04')
    boundary=frame.iloc[250].timestamp.isoformat()
    assert [m for m in result['moments'] if m['entry_at']<boundary]==[m for m in later['moments'] if m['entry_at']<boundary]

def test_setup_atr_not_trigger_atr_and_no_signal_or_news_filter(monkeypatch):
    import backend.lab.signals as signals
    def forbidden(*args,**kwargs):raise AssertionError('Candidate features must not regenerate signals.')
    monkeypatch.setattr(signals,'generate_signals',forbidden)
    frame=rows();cfg=Strategy(timeframe='5m',trigger_timeframe='1m',news='skip',direction='short')
    actual=check(frame,cfg)
    baseline=prototype.candidate_features(frame,Strategy(timeframe='5m'),['SPY'],'2026-11-04','2026-11-04')
    assert actual==baseline and actual['moments'][0]['entry_at']=='2026-11-04T15:45:00+00:00'

@pytest.mark.parametrize('ratio',[2,.5])
def test_split_units_at_next_open_are_known_before_new_chart_close(ratio):
    actions=[Action('SPY','2026-11-05','split',ratio)];frame=rows(('2026-11-04','2026-11-05'),actions)
    result=check(frame,Strategy(timeframe='1m'),end='2026-11-05')
    first=next(m for m in result['moments'] if m['entry_at']=='2026-11-05T14:30:00+00:00')
    assert first['atr']==2/ratio and first['reference_price']==100/ratio
    assert first['atr_available_at']=='2026-11-04T21:00:00+00:00'

@pytest.mark.parametrize('days',[('2026-10-30','2026-11-02'),('2026-11-25','2026-11-27')])
def test_dst_weekend_and_early_close_clock(days):
    frame=rows(days);result=check(frame,Strategy(timeframe='1m'),start=days[0],end=days[-1])
    assert len(result['clock']['SPY'])==len(frame)

@pytest.mark.parametrize('fault',['missing','duplicate','factor','ohlc','naive','seconds','symbol','dates','bounds','moment_bounds','session','no_sessions','missing_columns'])
def test_refuse_unknown_or_corrupt_source_without_selecting_a_subset(fault,monkeypatch):
    frame=rows();cfg=Strategy(timeframe='1m');symbols=['SPY'];start=end='2026-11-04'
    if fault=='missing':frame=frame.drop(index=50)
    elif fault=='duplicate':frame=pd.concat([frame,frame.iloc[[50]]])
    elif fault=='factor':frame.loc[1,'factor']=0
    elif fault=='ohlc':frame.loc[1,'high']=90
    elif fault=='naive':frame['timestamp']=frame.timestamp.dt.tz_localize(None)
    elif fault=='seconds':frame.loc[1,'timestamp']+=pd.Timedelta(seconds=1)
    elif fault=='symbol':symbols=['SPY','SPY']
    elif fault=='dates':start='bad'
    elif fault=='bounds':monkeypatch.setattr(prototype,'MAX_CLOCK_MINUTES',20)
    elif fault=='moment_bounds':monkeypatch.setattr(prototype,'MAX_MOMENTS',2)
    elif fault=='session':frame.loc[2,'session_open']+=pd.Timedelta(minutes=1)
    elif fault=='no_sessions':start=end='2026-11-07'
    else:frame=frame.drop(columns=['factor'])
    with pytest.raises(ValueError):prototype.candidate_features(frame,cfg,symbols,start,end)

@pytest.mark.parametrize('point',[1,2,3,4])
def test_cancel_before_symbol_during_minutes_and_before_return(point):
    frame=rows();count=0
    def cancel():
        nonlocal count
        count+=1
        return count==point
    with pytest.raises(InterruptedError):prototype.candidate_features(frame,Strategy(timeframe='1m'),['SPY'],'2026-11-04','2026-11-04',cancel)

def test_empty_original_cohort_is_not_fabricated():
    assert prototype.candidate_features(rows(),Strategy(timeframe='1m'),[],'2026-11-04','2026-11-04')==dict(moments=[],clock={})

@pytest.mark.parametrize('tf',['1h','4h','1d'])
def test_long_setup_charts_have_positive_independently_verified_warmup(tf):
    days=tuple(day.strftime('%Y-%m-%d') for day in pd.bdate_range('2026-11-02','2026-11-23'))
    result=check(rows(days),Strategy(timeframe=tf),start=days[0],end=days[-1])
    assert result['moments'] and all(m['atr']==2 for m in result['moments'])
