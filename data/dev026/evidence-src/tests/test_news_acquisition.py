from pathlib import Path
import json
import httpx
import pytest
from backend.lab import news
from backend.lab.data import DataError

FIXTURES=Path(__file__).resolve().parents[1]/'verification/fixtures'


def document(url):return (FIXTURES/('news-fomc.html' if 'federalreserve' in url else 'news-bls-2022-01.html')).read_bytes()


def test_cancel_resume_bound_receipts_preserve_sources_and_never_partial_publish(tmp_path,monkeypatch):
    request=news.NewsDownload(start='2022-01-01',end='2022-01-31');calls=[];committed={};stopped=False
    def fetch(url,cancel=None):calls.append(url);return document(url)
    monkeypatch.setattr(news,'fetch_document',fetch)
    def progress(p,n):
        nonlocal stopped
        stopped=True
    cp=tmp_path/'data/jobs/authored'
    with pytest.raises(InterruptedError):news.acquire_calendar(tmp_path,request,lambda:stopped,progress,cp,committed,lambda url,s:committed.update({url:s}))
    assert news.NewsStore(tmp_path).list()==[] and len(calls)==len(committed)==1
    saved=news.acquire_calendar(tmp_path,request,None,None,cp,committed,lambda url,s:committed.update({url:s}))
    assert len(calls)==2 and len(saved['spec']['events'])==3 and len(committed)==2
    assert {e['date'] for e in saved['spec']['events']}=={'2022-01-07','2022-01-12','2022-01-26'}
    assert saved['spec']['mode']=='retrospective' and saved['origin']=='official'
    assert news.acquire_calendar(tmp_path,request,None,None,cp,committed)['id']==saved['id'] and len(calls)==2
    path=news.NewsStore(tmp_path).source_path(saved['sources'][0]['sha256']);path.write_bytes(path.read_bytes()+b'corrupt')
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,request,None,None,cp,committed)


def test_orphan_document_without_commit_is_refetched_and_changed_checkpoint_rejects(tmp_path,monkeypatch):
    request=news.NewsDownload(start='2022-01-01',end='2022-01-31',kinds=['cpi']);calls=[]
    monkeypatch.setattr(news,'fetch_document',lambda url,cancel=None:(calls.append(url) or document(url)))
    cp=tmp_path/'data/jobs/orphan';news.acquire_calendar(tmp_path,request,checkpoint_dir=cp)
    news.acquire_calendar(tmp_path,request,checkpoint_dir=cp,committed={})
    assert len(calls)==2
    value=json.loads((cp/'news-documents.json').read_text(encoding='utf-8'));value['request_hash']='changed'
    (cp/'news-documents.json').write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,request,checkpoint_dir=cp)


def mock_transport(monkeypatch,handler):
    real=httpx.Client;transport=httpx.MockTransport(handler)
    monkeypatch.setattr(news.httpx,'Client',lambda **kw:real(transport=transport,**kw))


def test_actual_http_client_uses_only_allowlist_without_auth_or_redirect(monkeypatch):
    seen=[]
    def handler(request):
        seen.append(request)
        assert 'authorization' not in request.headers and 'apca-api-key-id' not in request.headers and 'apca-api-secret-key' not in request.headers
        return httpx.Response(200,headers={'content-type':'text/html'},content=b'<html>public</html>')
    mock_transport(monkeypatch,handler)
    assert news.fetch_document(news.FED_URL)==b'<html>public</html>'
    for url in ['http://127.0.0.1/private','https://evil.test/a','https://www.bls.gov/schedule/2022/13_sched.htm',news.FED_URL+'?token=x']:
        with pytest.raises(DataError):news.fetch_document(url)
    assert len(seen)==1


@pytest.mark.parametrize('status',[301,302,400,403,404])
def test_nonretry_http_failures_do_not_follow_or_publish(monkeypatch,status):
    calls=[]
    mock_transport(monkeypatch,lambda request:(calls.append(request.url) or httpx.Response(status,headers={'location':'https://evil.test'})))
    with pytest.raises(DataError):news.fetch_document(news.FED_URL)
    assert len(calls)==1


@pytest.mark.parametrize('kind',['429','503','timeout'])
def test_bounded_retries_then_success(monkeypatch,kind):
    calls=[]
    def handler(request):
        calls.append(request)
        if len(calls)==1:
            if kind=='timeout':raise httpx.ReadTimeout('Authored timeout')
            return httpx.Response(int(kind))
        return httpx.Response(200,headers={'content-type':'text/html'},content=b'ok')
    mock_transport(monkeypatch,handler)
    assert news.fetch_document(news.FED_URL)==b'ok' and len(calls)==2


def test_retry_exhaustion_cancel_and_size_media_guards(monkeypatch):
    calls=[]
    mock_transport(monkeypatch,lambda r:(calls.append(r) or httpx.Response(503)))
    with pytest.raises(DataError):news.fetch_document(news.FED_URL)
    assert len(calls)==3
    with pytest.raises(InterruptedError):news.fetch_document(news.FED_URL,lambda:True)
    # Use a fresh original client for successive transport monkeypatches.


@pytest.mark.parametrize('media,body',[('application/json',b'{}'),('text/html',b'x'*(news.MAX_SOURCE+1))])
def test_invalid_source_media_or_expansion_rejects(monkeypatch,media,body):
    mock_transport(monkeypatch,lambda r:httpx.Response(200,headers={'content-type':media},content=body))
    with pytest.raises(DataError):news.fetch_document(news.FED_URL)


def test_acquisition_bounds_changed_context_and_empty_selected_source(tmp_path,monkeypatch):
    with pytest.raises(ValueError):news.NewsDownload(start='2020-01-01',end='2022-01-01')
    with pytest.raises(ValueError):news.NewsDownload(start='2022-01-01',end='2022-01-01',kinds=['cpi','cpi'])
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,news.NewsDownload(start='2022-01-01',end='2022-01-31'),checkpoint_dir=tmp_path/'outside')
    monkeypatch.setattr(news,'fetch_document',lambda *args:b'<title>Changed source</title>')
    with pytest.raises(DataError):news.acquire_calendar(tmp_path,news.NewsDownload(start='2022-01-01',end='2022-01-31'))
    assert news.NewsStore(tmp_path).list()==[]
