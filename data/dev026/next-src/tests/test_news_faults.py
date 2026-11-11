from datetime import datetime,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import httpx
import pytest
from backend.lab import news
from backend.lab.config import identity
from backend.lab.data import DataError
from test_news import spec
from test_news_acquisition import document,mock_transport


def test_invalid_source_bounds_citations_json_and_atomic_content_conflicts(tmp_path):
    store=news.NewsStore(tmp_path)
    for raw in ['not bytes',b'x'*(news.MAX_SOURCE+1)]:
        with pytest.raises(DataError):store.source(raw)
    for url in ['http://example.test','https://name:password@example.test/a','https://example.test/a?credential=marker','https://example.test/a#fragment']:
        with pytest.raises(DataError):store.source(b'not sensitive',url)
    for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}',b'invalid']:
        with pytest.raises(DataError):news.strict_json(raw)
    assert news.strict_json(b'{"x":1.25}')['x']==1.25
    value=store.source(b'original');store.source_path(value['sha256']).write_bytes(b'changed')
    with pytest.raises(DataError):store.source(b'original')
    with pytest.raises(DataError):store.save(news.NewsCalendar(**spec()),[value])
    with pytest.raises(DataError):store.save(news.NewsCalendar(**spec()),origin='unsupported')
    with pytest.raises(DataError):store.load('0'*64)
    for digest in ['../outside','A'*64,None]:
        with pytest.raises(DataError):store.source_path(digest)


def test_concurrent_identical_version_publication_is_idempotent(tmp_path):
    store=news.NewsStore(tmp_path);value=news.NewsCalendar(**spec())
    with ThreadPoolExecutor(max_workers=4) as pool:versions=list(pool.map(lambda _:store.save(value),range(8)))
    assert len({v['id'] for v in versions})==1 and len(store.list())==1
    assert not list(store.root.rglob('.news-*.tmp'))


def test_manifest_identity_and_source_inventory_layers_reject(tmp_path):
    store=news.NewsStore(tmp_path);saved=store.save(news.NewsCalendar(**spec()));path=store.calendar_path(saved['id'])
    damaged=saved|dict(version=2);path.write_text(json.dumps(damaged),encoding='utf-8')
    with pytest.raises(DataError):store.load(saved['id'])
    for change in [dict(origin='fake'),dict(sources=[]),dict(sources=[dict(sha256='0'*64,bytes=5)])]:
        value={k:v for k,v in saved.items() if k!='id'}|change;cid=identity(value)
        store.calendar_path(cid).write_text(json.dumps(dict(id=cid,**value)),encoding='utf-8')
        with pytest.raises(DataError):store.load(cid)


def test_naive_decision_and_legacy_set_weight_remain_explicit():
    c=news.NewsClock(news.NewsCalendar(**spec()))
    with pytest.raises(DataError):c.is_news(datetime(2022,1,12,12))
    at=datetime(2022,1,12,15,tzinfo=timezone.utc)
    assert news.news_weight('half',{'2022-01-12'},at)==.5
    assert news.news_weight('skip',{'2022-01-12'},at)==0
    assert news.news_weight('half',{'2022-01-13'},at)==1
    with pytest.raises(DataError):news.news_weight('skip',None,at)
    assert news.news_assumptions(None)==[]
    for label in ['','\n','bad\x00value']:
        with pytest.raises(ValueError):news.NewsCalendar(**spec(events=[dict(date='2022-01-12',kind='cpi',label=label)]))


def test_csv_wrong_columns_encoding_and_bounds_reject():
    metadata=spec(events=[])
    for raw in [b'date,kind,label\n2022-01-12,cpi,x,extra',b'date,kind,label\n2022-01-12,cpi',b'\xff',b'x'*(news.MAX_SOURCE+1)]:
        with pytest.raises((DataError,ValueError)):news.parse_csv(raw,metadata)


def test_committed_checkpoint_disagreement_url_and_source_budget_reject(tmp_path,monkeypatch):
    request=news.NewsDownload(start='2022-01-01',end='2022-01-31',kinds=['cpi']);cp=tmp_path/'data/jobs/cp'
    monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:document(url))
    news.acquire_calendar(tmp_path,request,checkpoint_dir=cp)
    cache=json.loads((cp/'news-documents.json').read_text(encoding='utf-8'));url=next(iter(cache['documents']));entry=cache['documents'][url]
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,request,checkpoint_dir=cp,committed={url:entry|dict(bytes=entry['bytes']+1)})
    cache['documents'][url]['url']='https://wrong.test';(cp/'news-documents.json').write_text(json.dumps(cache),encoding='utf-8')
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,request,checkpoint_dir=cp)
    # Exercise the declared total-budget guard with a tiny test budget, retaining real parsed input.
    monkeypatch.setattr(news,'MAX_TOTAL',1)
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,request)


@pytest.mark.parametrize('kind',['timeout','cancel_backoff'])
def test_timeout_budget_and_cancel_during_retry(monkeypatch,kind):
    calls=[];stopped=False
    def handler(request):
        calls.append(request)
        if kind=='timeout':raise httpx.ReadTimeout('Authored timeout')
        return httpx.Response(429)
    mock_transport(monkeypatch,handler)
    if kind=='timeout':
        with pytest.raises(DataError):news.fetch_document(news.FED_URL)
        assert len(calls)==3
    else:
        monkeypatch.setattr(news.time,'sleep',lambda _:None)
        def cancel():return len(calls)>0
        with pytest.raises(InterruptedError):news.fetch_document(news.FED_URL,cancel)
        assert len(calls)==1


def test_parser_invalid_month_dates_and_missing_clock_reject():
    root=Path(__file__).resolve().parents[1]/'verification/fixtures'
    bls=(root/'news-bls-2022-01.html').read_bytes()
    with pytest.raises(DataError):news.parse_bls(bls.replace(b'08:30 AM',b'Unknown'),2022,1,['jobs'])
    fed=(root/'news-fomc.html').read_bytes()
    with pytest.raises(DataError):news.parse_fed(fed.replace(b'>January</strong>',b'>Mystery</strong>'),2022)
    with pytest.raises(DataError):news.parse_fed(fed.replace(b'>25-26</div>',b'>25-99</div>'),2022)


@pytest.mark.skipif(os.name!='nt',reason='Actual junction boundary for the supported Windows host.')
def test_actual_windows_junction_escape_is_rejected(tmp_path):
    workspace=tmp_path/'workspace';outside=tmp_path/'outside';workspace.mkdir();outside.mkdir()
    (workspace/'data').mkdir();link=workspace/'data/news'
    assert link.absolute().is_relative_to(tmp_path.absolute()) and outside.absolute().is_relative_to(tmp_path.absolute())
    r=subprocess.run(['cmd','/c','mklink','/J',str(link),str(outside)],capture_output=True)
    assert r.returncode==0
    with pytest.raises(DataError):news.NewsStore(workspace)


@pytest.mark.parametrize('field,value',[
    ('start',1640995200),('end',1643587200),('start','1640995200'),
    ('start',True),('start','2022-01-01T00:00:00Z'),
    ('name','   '),('name','bad\x00name'),
])
def test_calendar_and_download_reject_implicit_dates_or_empty_control_names(field,value):
    for model,base in [(news.NewsCalendar,spec()),(news.NewsDownload,dict(start='2022-01-01',end='2022-01-31'))]:
        with pytest.raises(ValueError):model(**(base|{field:value}))


@pytest.mark.parametrize('value',[1641997800,'1641997800',True,'2022-01-12T14:30:00.1234567Z'])
def test_knowledge_time_requires_explicit_iso_timezone_without_precision_loss(value):
    with pytest.raises(ValueError):news.NewsCalendar(**spec(mode='asof',events=[dict(date='2022-01-12',kind='cpi',label='CPI',known_at=value)]))
    # A numeric or timestamp-coerced event date must also fail independently.
    with pytest.raises(ValueError):news.NewsCalendar(**spec(events=[dict(date=1641945600,kind='cpi',label='CPI')]))


@pytest.mark.parametrize('change',[
    dict(url='https:///missing-host'),dict(url='https://user:pass@example.test/a'),
    dict(url='https://example.test/a?token=marker'),dict(url=123),
    dict(bytes=True),dict(bytes=-1),dict(acquired_at='2022-01-01T12:00:00'),
    dict(acquired_at=1640995200),dict(extra='not in source schema'),
])
def test_source_metadata_is_validated_before_publish_and_on_hash_consistent_read(tmp_path,change):
    store=news.NewsStore(tmp_path);source=store.source(b'public fixture');bad=source|change
    with pytest.raises(DataError):store.save(news.NewsCalendar(**spec()),[bad])
    assert not list((store.root/'calendars').glob('*.json'))
    doc=dict(version=1,spec=news.NewsCalendar(**spec()).model_dump(mode='json'),origin='user_json',sources=[bad]);cid=identity(doc)
    store.calendar_path(cid).write_text(json.dumps(dict(id=cid,**doc)),encoding='utf-8')
    for full in [True,False]:
        with pytest.raises(DataError):store.load(cid,full)


def test_source_constructor_rejects_missing_host_and_naive_observation_before_writing(tmp_path):
    store=news.NewsStore(tmp_path)
    for args in [dict(url='https:///missing'),dict(acquired_at='2022-01-01T12:00:00')]:
        with pytest.raises(DataError):store.source(b'must not be published',**args)
    assert not list((store.root/'sources').glob('*.bin'))
