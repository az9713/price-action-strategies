"""Real same-origin API queue/status/inputs/result and bounded journal pages."""
from contextlib import contextmanager
import json,sqlite3
import pytest
from fastapi.testclient import TestClient
from test_spread_probe import owned
from test_spread_worker import request
from backend.lab.api import create_app
from backend.lab.worker import Worker

@contextmanager
def client(lab):
    with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',50001)) as c:
        c.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':c.get('/api/session').json()['token']});yield c

def test_preview_is_data_free_and_preserves_source_defaults_and_actual_work(owned,monkeypatch):
    lab,m,context,cfg=owned
    def forbidden(*a,**k):raise AssertionError('Preview accessed datasets or credentials')
    monkeypatch.setattr('backend.lab.service.read_manifest',forbidden)
    with client(lab) as c:
        response=c.post('/api/spreads/preview',json={});assert response.status_code==200,response.text;v=response.json()
        assert v['selected_target']==40000 and v['planned_proposals']==32000000 and v['planned_batches']==80000 and v['settings']['batch_size']==400
        assert v['requires_signal_data'] and v['source_video'].endswith('z97PnFIPoFg')

def test_actual_api_queue_metadata_and_complete_saved_result(owned):
    lab,m,context,cfg=owned
    with client(lab) as c:
        response=c.post('/api/spreads',json=request(m).model_dump(mode='json'));assert response.status_code==202,response.text;created=response.json();jid=created['id']
        queued=c.get('/api/spreads/'+jid);assert queued.status_code==200 and queued.json()['spread']['frozen_proposals']==0
        original=c.get('/api/jobs/'+jid+'/inputs');assert original.status_code==200 and original.json()['payload']['settings']['batch_size']==40
        assert Worker(lab).run_once();complete=c.get('/api/spreads/'+jid);assert complete.status_code==200 and complete.json()['spread']['stage']=='qualified'
        result=c.get('/api/spreads/'+jid+'/result');assert result.status_code==200 and result.json()['selection_manifest']['context']['primary_symbol']=='SPY'
        pages=[];cursor=0
        while True:
            response=c.get('/api/spreads/'+jid+'/events',params={'after':cursor,'limit':7});assert response.status_code==200
            page=response.json();assert len(page['events'])<=7;pages.extend(page['events'])
            if not page['has_more']:break
            assert page['next_after']>cursor;cursor=page['next_after']
        assert [r['sequence'] for r in pages]==list(range(complete.json()['spread']['event_count']))
        assert c.get('/api/spreads/'+jid+'/events',params={'limit':21}).status_code==422

def test_status_does_not_read_raw_plan_or_entire_journal(owned,monkeypatch):
    lab,m,context,cfg=owned;job=lab.create_spread(request(m));assert Worker(lab).run_once()
    original=lab.store.db;reads=[]
    @contextmanager
    def guarded(*args,**kwargs):
        with original(*args,**kwargs) as db:
            def authorize(action,table,column,*rest):
                if action==sqlite3.SQLITE_READ:
                    reads.append((table,column))
                    if table=='jobs' and column=='payload':return sqlite3.SQLITE_DENY
                    if table=='events' and column=='details':return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            db.set_authorizer(authorize);yield db
    monkeypatch.setattr(lab.store,'db',guarded)
    status=lab.spread_status(job['id']);assert status['spread']['stage']=='qualified' and len(json.dumps(status).encode())<=65536
    assert ('spread_state','projection') in reads
