import asyncio
from fastapi.testclient import TestClient
from backend.lab.http_boundary import BoundedBody
from backend.lab.api import create_app


def test_chunked_excess_is_rejected_before_parser_and_stops_reading():
    consumed=[];sent=[];called=[]
    messages=iter([{'type':'http.request','body':b'abc','more_body':True},
                   {'type':'http.request','body':b'def','more_body':True},
                   {'type':'http.request','body':b'not-consumed','more_body':False}])
    async def receive():
        value=next(messages);consumed.append(value);return value
    async def send(message): sent.append(message)
    async def parser(*args): called.append(True)
    asyncio.run(BoundedBody(parser,4)({'type':'http','method':'POST'},receive,send))
    assert len(consumed)==2 and not called
    assert sent[0]['status']==413


def test_exact_boundary_replays_the_original_bytes():
    sent=[];seen=[]
    messages=iter([{'type':'http.request','body':b'ab','more_body':True},
                   {'type':'http.request','body':b'cd','more_body':False}])
    async def receive(): return next(messages)
    async def send(message): sent.append(message)
    async def parser(scope,replay,send): seen.append(await replay())
    asyncio.run(BoundedBody(parser,4)({'type':'http','method':'POST'},receive,send))
    assert seen==[{'type':'http.request','body':b'abcd','more_body':False}]


def test_http_disconnect_and_non_http_scopes_do_not_parse_a_partial_body():
    called=[]
    async def receive(): return {'type':'http.disconnect'}
    async def send(message): pass
    async def parser(*args): called.append(True)
    asyncio.run(BoundedBody(parser,4)({'type':'http'},receive,send));assert not called
    asyncio.run(BoundedBody(parser,4)({'type':'lifespan'},receive,send));assert called==[True]


def test_actual_api_counts_chunked_and_falsely_small_declared_bodies(tmp_path):
    app=create_app(tmp_path,False,max_request_bytes=1024)
    with TestClient(app,base_url='http://localhost',client=('127.0.0.1',1)) as client:
        token=client.get('/api/session').json()['token']
        headers={'Origin':'http://localhost','X-Lab-Token':token,'Content-Type':'application/json'}
        for extra in [{},{'Content-Length':'12'}]:
            response=client.post('/api/strategies',content=iter([b'{"name":"',b'x'*2000,b'","strategy":{}}']),headers={**headers,**extra})
            assert response.status_code==413
        assert client.post('/api/strategies',json={'name':'Within limit','strategy':{}},headers=headers).status_code==201
        assert len(app.state.lab.store.strategies())==1
