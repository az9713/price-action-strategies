"""Explicit remaining news clock, matching and comparison acceptance boundaries."""
from copy import deepcopy
from dataclasses import replace
import pandas as pd
import pytest
from backend.lab.news import NewsCalendar,NewsClock,news_weight
from backend.lab.config import Strategy,identity
from backend.lab.controls import make_control_plan
from backend.lab.ablations import paired_comparison
from backend.lab.data import DataError
from test_confirmation_filters import tables,candle,select
from test_random_controls import feature,signal,CFG
from test_ablations import report


def clock(events,mode='synthetic'):
    return NewsClock(NewsCalendar(name='Explicit acceptance fixture',start='2026-10-05',end='2026-10-09',
        mode=mode,kinds=['fed'],complete=True,events=events))


@pytest.mark.parametrize('mode',['synthetic','asof'])
@pytest.mark.parametrize('rule',['trade','skip','half'])
def test_future_appended_events_preserve_all_prior_clock_weights(mode,rule):
    first=dict(date='2026-10-05',kind='fed',label='First event')
    future=dict(date='2026-10-09',kind='fed',label='Future appended event')
    if mode=='asof':first['known_at']='2026-10-05T14:30:00Z';future['known_at']='2026-10-09T12:00:00Z'
    before=clock([first],mode);after=clock([first,future],mode)
    moments=pd.date_range('2026-10-05T00:00:00Z','2026-10-08T23:59:00Z',freq='17min')
    assert [news_weight(rule,before,at) for at in moments]==[news_weight(rule,after,at) for at in moments]
    if rule!='trade':
        assert news_weight(rule,after,pd.Timestamp('2026-10-09T14:30:00Z'))==(0 if rule=='skip' else .5)
        assert news_weight(rule,before,pd.Timestamp('2026-10-09T14:30:00Z'))==1


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('rule',['half','skip'])
@pytest.mark.parametrize('offset',[-1,0,1])
def test_overnight_setup_uses_confirmation_day_and_exact_recorded_knowledge(monkeypatch,side,rule,offset):
    setup=pd.Timestamp('2026-10-05T19:55:00Z');confirmed=pd.Timestamp('2026-10-06T13:35:00Z')
    charts=tables(side,at=setup)
    charts['5m']=[candle(setup,side,close=100),candle(confirmed,side,close=100.5)]
    event=dict(date='2026-10-06',kind='fed',label='Known at confirmation',
               known_at=(confirmed+pd.Timedelta(microseconds=offset)).isoformat())
    current=clock([event],'asof')
    signals,cfg=select(monkeypatch,charts,side,calendar=current,news=rule)
    known=offset<=0
    if rule=='skip' and known:assert signals==[]
    else:
        assert len(signals)==1 and signals[0].side==side
        assert signals[0].setup_at==setup and signals[0].available_at==confirmed
        assert signals[0].weight==(.5 if rule=='half' and known else 1)
    future=event|dict(date='2026-10-09',label='Future event',known_at='2026-10-09T12:00:00Z')
    later,_=select(monkeypatch,charts,side,calendar=clock([event,future],'asof'),news=rule)
    assert [s.json() for s in later]==[s.json() for s in signals]


@pytest.mark.parametrize('rule',['half','skip'])
def test_matching_news_eligibility_weights_and_denominators_are_explicit(rule):
    dates=['2026-10-05','2026-10-07','2026-10-09']
    calendar=clock([dict(date=day,kind='fed',label='Authored event') for day in dates])
    cfg=CFG.model_copy(update={'news':rule})
    rows=[feature(),feature('2026-10-06'),feature('2026-10-07',close=100,atr=1),
          feature('2026-10-08',close=100,atr=1),feature('2026-10-09')]
    normal=signal(name='ordinary',day='2026-10-08')
    sources=[replace(signal(name='news'),weight=.5),normal] if rule=='half' else [normal]
    result=make_control_plan(rows,sources,cfg,'2026-10-05','2026-10-09',42,20,news_dates=calendar)
    assert result['source_count']==result['matched_count']==(2 if rule=='half' else 1)
    assert result['unmatched']==[]
    for replica in result['replicas']:
        assert len(replica['matches'])==len(sources)
        assert {m['source_id'] for m in replica['matches']}=={s.id for s in sources}
        for match in replica['matches']:
            expected=.5 if match['source_id']=='news' else 1
            assert match['signal']['weight']==match['matching']['news_weight']==expected
            active=calendar.is_news(pd.Timestamp(match['signal']['available_at']))
            assert active is (expected==.5)
    more=make_control_plan(rows,sources,cfg,'2026-10-05','2026-10-09',42,30,news_dates=calendar)
    assert more['matched_count']==result['matched_count'] and more['replicas'][:20]==result['replicas']


@pytest.mark.parametrize('change',['id','mode','event','source'])
def test_paired_news_alternatives_refuse_any_incompatible_calendar_version(change):
    baseline=report([10,-5,2,0,4,-1]);alternative=report([20,-7,4,0,-2,3])
    for value,rule in [(baseline,'half'),(alternative,'skip')]:
        cfg=Strategy(**(value['config']|dict(news=rule)));value['config']=cfg.model_dump();value['config_id']=identity(cfg)
        value['news_dates']=['2026-10-05']
        value['news_calendar']=dict(id='a'*64,spec=dict(mode='synthetic',events=[dict(date='2026-10-05')]),sources=[dict(sha256='b'*64)])
    result=paired_comparison(baseline,alternative,'news')
    assert result['field']=='news' and result['baseline_net_profit']==baseline['metrics']['net_profit']
    alternative=deepcopy(alternative)
    if change=='id':alternative['news_calendar']['id']='c'*64
    elif change=='mode':alternative['news_calendar']['spec']['mode']='retrospective'
    elif change=='event':alternative['news_calendar']['spec']['events'][0]['date']='2026-10-06'
    else:alternative['news_calendar']['sources'][0]['sha256']='d'*64
    with pytest.raises(DataError,match='incompatible news_calendar'):paired_comparison(baseline,alternative,'news')
