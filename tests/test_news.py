"""Independent news-date, immutable snapshot and causal-clock expectations."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json
import pytest


def spec(**updates):
    return dict(name='Authored calendar',start='2022-01-01',end='2022-01-31',mode='synthetic',
        kinds=['cpi','jobs','fed'],complete=True,events=[
            dict(date='2022-01-07',kind='jobs',label='Jobs report'),
            dict(date='2022-01-12',kind='cpi',label='Consumer prices'),
            dict(date='2022-01-26',kind='fed',label='Scheduled Fed decision')])|updates


def test_immutable_idempotent_versions_and_reordered_events(tmp_path):
    from backend.lab.news import NewsCalendar,NewsStore
    store=NewsStore(tmp_path);value=NewsCalendar(**spec());first=store.save(value)
    assert len(first['id'])==64
    path=store.calendar_path(first['id']);original=path.read_bytes()
    assert store.save(NewsCalendar(**spec(events=list(reversed(spec()['events'])))))['id']==first['id']
    other=store.save(NewsCalendar(**spec(name='Amended calendar')))
    assert other['id']!=first['id'] and path.read_bytes()==original
    clock=store.clock(first['id'],'2022-01-03','2022-01-31',first)
    assert clock.is_news(datetime(2022,1,12,14,30,tzinfo=timezone.utc))
    assert not clock.is_news(datetime(2022,1,13,14,30,tzinfo=timezone.utc))


@pytest.mark.parametrize('updates',[
    dict(start='2022-02-01'),dict(kinds=[]),dict(kinds=['cpi','cpi']),
    dict(events=[dict(date='2021-12-31',kind='cpi',label='Outside')]),
    dict(events=[dict(date='2022-01-12',kind='custom',label='Unselected')]),
    dict(events=spec()['events']*2),dict(mode='asof'),
    dict(mode='asof',events=[dict(date='2022-01-12',kind='cpi',label='Naive',known_at='2022-01-11T12:00:00')]),
    dict(mode='retrospective',events=[dict(date='2022-01-12',kind='cpi',label='Mixed',known_at='2022-01-11T12:00:00Z')])])
def test_invalid_calendar_contract(updates):
    from backend.lab.news import NewsCalendar
    with pytest.raises(ValueError):NewsCalendar(**spec(**updates))


@pytest.mark.parametrize('known,at,expected',[
    ('2022-01-12T14:30:00Z','2022-01-12T14:29:59.999999Z',False),
    ('2022-01-12T14:30:00Z','2022-01-12T14:30:00Z',True),
    ('2022-01-12T14:30:00Z','2022-01-12T14:30:00.000001Z',True),
    ('2022-01-13T00:00:00Z','2022-01-12T20:59:00Z',False)])
def test_asof_clock_exact_knowledge_boundary(known,at,expected):
    from backend.lab.news import NewsClock,NewsCalendar
    c=NewsClock(NewsCalendar(**spec(mode='asof',events=[dict(date='2022-01-12',kind='cpi',label='CPI',known_at=known)])))
    assert c.is_news(datetime.fromisoformat(at.replace('Z','+00:00'))) is expected


def test_new_york_day_dst_and_multi_event_earliest_knowledge():
    from backend.lab.news import NewsClock,NewsCalendar
    c=NewsClock(NewsCalendar(**spec(start='2022-03-01',end='2022-03-31',mode='asof',events=[
        dict(date='2022-03-14',kind='fed',label='Fed',known_at='2022-03-14T15:00:00Z'),
        dict(date='2022-03-14',kind='cpi',label='CPI',known_at='2022-03-14T13:30:00Z')])))
    for at,expected in [('2022-03-14T03:59:59+00:00',False),('2022-03-14T13:30:00+00:00',True),('2022-03-15T03:59:00+00:00',True),('2022-03-15T04:00:00+00:00',False)]:
        assert c.is_news(datetime.fromisoformat(at)) is expected


def test_corrupt_snapshot_sources_partial_coverage_and_safe_ids(tmp_path):
    from backend.lab.news import NewsCalendar,NewsStore
    from backend.lab.data import DataError
    store=NewsStore(tmp_path);saved=store.save(NewsCalendar(**spec()))
    with pytest.raises(DataError):store.clock(saved['id'],'2021-12-31','2022-01-31',saved)
    changed=deepcopy(saved);changed['spec']['name']='Other'
    with pytest.raises(DataError):store.clock(saved['id'],'2022-01-03','2022-01-31',changed)
    for bad in ['../secret','.env','A'*64,'0'*63]:
        with pytest.raises(DataError):store.load(bad)
    original=store.calendar_path(saved['id']).read_bytes();store.calendar_path(saved['id']).write_bytes(original+b'bad')
    with pytest.raises(DataError):store.load(saved['id'])
    assert any(x.get('error') for x in store.list())
    partial=store.save(NewsCalendar(**spec(complete=False)))
    with pytest.raises(DataError):store.clock(partial['id'],'2022-01-03','2022-01-31',partial)


def test_captured_official_parsers_independent_january_dates():
    from backend.lab.news import parse_bls,parse_fed
    root=Path(__file__).resolve().parents[1]
    bls=parse_bls((root/'verification/fixtures/news-bls-2022-01.html').read_bytes(),2022,1,['cpi','jobs'])
    assert {(e['date'],e['kind']) for e in bls}=={('2022-01-07','jobs'),('2022-01-12','cpi')}
    fed=parse_fed((root/'verification/fixtures/news-fomc.html').read_bytes(),2022)
    assert [e['date'] for e in fed]==['2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27','2022-09-21','2022-11-02','2022-12-14']
    fed24=parse_fed((root/'verification/fixtures/news-fomc.html').read_bytes(),2024)
    assert '2024-05-01' in [e['date'] for e in fed24] and '2024-04-01' not in [e['date'] for e in fed24]


def test_parser_changed_or_missing_source_fails_closed():
    from backend.lab.news import parse_bls,parse_fed
    from backend.lab.data import DataError
    for call in [lambda:parse_bls(b'<html>Changed page</html>',2022,1,['jobs']),lambda:parse_fed(b'<h4>2022 FOMC Meetings</h4>',2022)]:
        with pytest.raises(DataError):call()


def test_csv_import_timezone_empty_and_duplicate_fields(tmp_path):
    from backend.lab.news import NewsStore,parse_csv
    from backend.lab.data import DataError
    meta=spec(events=[],mode='asof')
    value=parse_csv(b'date,kind,label,known_at\n2022-01-12,cpi,Consumer prices,2022-01-10T12:00:00Z\n',meta)
    saved=NewsStore(tmp_path).save(value)
    assert saved['spec']['events'][0]['known_at'].startswith('2022-01-10T12:00:00')
    for raw in [b'',b'date,date,kind,label\na,b,c,d',b'date,kind,label,known_at\n2022-01-12,cpi,X,2022-01-10T12:00:00\n']:
        with pytest.raises((DataError,ValueError)):parse_csv(raw,meta)
