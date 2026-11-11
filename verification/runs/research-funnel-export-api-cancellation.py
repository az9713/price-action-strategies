"""A completed temporary export must be removed if delivery is canceled."""
import asyncio,importlib.util,threading
import pytest
from pathlib import Path
from backend.lab.api import create_app
from backend.lab import research_funnel_exports as exports

spec=importlib.util.spec_from_file_location('canceled_export_original_fixtures',Path(__file__).with_name('research-funnel-export-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;finals=fixtures.finals;saved=fixtures.saved


def test_cancellation_after_build_before_delivery_removes_completed_private_export(saved,monkeypatch):
    lab,qid,fid=saved;before=fixtures.counts(lab);built=threading.Event();original=exports.build_export
    def observed(*args,**kwargs):
        result=original(*args,**kwargs);built.set();return result
    monkeypatch.setattr(exports,'build_export',observed)
    class CanceledRequest:
        async def is_disconnected(self):
            assert await asyncio.to_thread(built.wait,45),'Authored export did not finish.'
            await asyncio.sleep(.02)
            raise asyncio.CancelledError('Authored cancellation after original export completed, before response delivery.')
    app=create_app(lab.root,run_worker=False)
    endpoint=next(route.endpoint for route in app.routes if getattr(route,'path','')=='/api/jobs/{job_id}/funnel-export/{format}')
    response=asyncio.run(endpoint(CanceledRequest(),fid,'html'))
    assert response.status_code==499
    assert not list((lab.root/'data/exports').iterdir()),'A canceled HTTP delivery left the completed private export behind.'
    assert fixtures.counts(lab)==before


def test_cancellation_during_response_streaming_removes_completed_private_export(saved):
    import pytest
    lab,qid,fid=saved;before=fixtures.counts(lab)
    class ConnectedRequest:
        async def is_disconnected(self):return False
    app=create_app(lab.root,run_worker=False)
    endpoint=next(route.endpoint for route in app.routes if getattr(route,'path','')=='/api/jobs/{job_id}/funnel-export/{format}')
    response=asyncio.run(endpoint(ConnectedRequest(),fid,'html'));path=Path(response.path);assert path.exists()
    async def receive():raise AssertionError('ASGI2.4 send-exception delivery must not poll a fake receive loop.')
    async def send(message):
        if message['type']=='http.response.body':raise asyncio.CancelledError('Authored client cancellation during file-body transfer.')
    with pytest.raises(asyncio.CancelledError):asyncio.run(response({'type':'http','method':'GET','headers':[],'extensions':{},'asgi':{'spec_version':'2.4'}},receive,send))
    assert not path.exists() and fixtures.counts(lab)==before


def test_asgi20_disconnect_receiver_cleans_file_without_a_busy_fixture_loop(saved):
    lab,qid,fid=saved;before=fixtures.counts(lab)
    class ConnectedRequest:
        async def is_disconnected(self):return False
    app=create_app(lab.root,run_worker=False)
    endpoint=next(route.endpoint for route in app.routes if getattr(route,'path','')=='/api/jobs/{job_id}/funnel-export/{format}')
    response=asyncio.run(endpoint(ConnectedRequest(),fid,'html'));path=Path(response.path);assert path.exists()
    async def receive():
        await asyncio.sleep(.001)
        return {'type':'http.disconnect'}
    async def send(message):await asyncio.sleep(.005)
    asyncio.run(response({'type':'http','method':'GET','headers':[],'extensions':{},'asgi':{'spec_version':'2.0'}},receive,send))
    assert not path.exists() and fixtures.counts(lab)==before


def test_abandoned_evidence_page_cancels_original_read_without_new_work(saved,monkeypatch):
    import time
    lab,qid,fid=saved;before=fixtures.counts(lab);entered=threading.Event();original=exports.inspect_export_source
    def observed(lab,jid,cancel=None):
        entered.set();deadline=time.monotonic()+5
        while not cancel():
            assert time.monotonic()<deadline,'The abandoned read did not receive its cancellation signal.'
            time.sleep(.001)
        return original(lab,jid,cancel=cancel)
    monkeypatch.setattr(exports,'inspect_export_source',observed)
    class AbandonedRequest:
        async def is_disconnected(self):
            assert await asyncio.to_thread(entered.wait,45)
            return True
    app=create_app(lab.root,run_worker=False)
    endpoint=next(route.endpoint for route in app.routes if getattr(route,'path','')=='/api/jobs/{job_id}/funnel-evidence/{table}')
    response=asyncio.run(endpoint(AbandonedRequest(),fid,'family_daily',limit=50,offset=0))
    assert response.status_code==499 and fixtures.counts(lab)==before


@pytest.mark.parametrize('name,phase',[('qualification_summary','qualification'),('final_summary','final'),('final_rows','final')])
def test_superseded_summary_and_final_version_reads_receive_cancellation(saved,monkeypatch,name,phase):
    import time
    from backend.lab import research_funnel_jobs,research_funnel_final
    lab,qid,fid=saved;jid=qid if phase=='qualification' else fid;before=fixtures.counts(lab);entered=threading.Event()
    module=research_funnel_jobs if phase=='qualification' else research_funnel_final;original=getattr(module,name)
    def observed(*args,cancel=None,**kwargs):
        entered.set();deadline=time.monotonic()+5
        while not cancel():
            assert time.monotonic()<deadline,'The superseded read did not receive cancellation.'
            time.sleep(.001)
        return original(*args,cancel=cancel,**kwargs)
    monkeypatch.setattr(module,name,observed)
    class AbandonedRequest:
        async def is_disconnected(self):
            assert await asyncio.to_thread(entered.wait,45)
            return True
    app=create_app(lab.root,run_worker=False)
    path='/api/jobs/{job_id}/funnel-final-versions' if name=='final_rows' else '/api/jobs/{job_id}/funnel-summary'
    endpoint=next(route.endpoint for route in app.routes if getattr(route,'path','')==path)
    response=asyncio.run(endpoint(AbandonedRequest(),jid,limit=50,offset=0) if name=='final_rows' else endpoint(AbandonedRequest(),jid))
    assert response.status_code==499 and fixtures.counts(lab)==before


def test_owned_summary_and_final_page_routes_match_original_generic_views(saved):
    from test_search_statistics_integration import client
    lab,qid,fid=saved;before=fixtures.counts(lab)
    with client(lab) as c:
        for jid in [qid,fid]:
            original=c.get('/api/jobs/'+jid+'/result-summary');owned=c.get('/api/jobs/'+jid+'/funnel-summary')
            assert original.status_code==owned.status_code==200
            assert original.json()==owned.json()
        original=c.get('/api/jobs/'+fid+'/result-rows?limit=1&offset=1');owned=c.get('/api/jobs/'+fid+'/funnel-final-versions?limit=1&offset=1')
        assert original.status_code==owned.status_code==200 and original.json()==owned.json()
        assert c.get('/api/jobs/'+qid+'/funnel-final-versions').status_code==409
    assert fixtures.counts(lab)==before
