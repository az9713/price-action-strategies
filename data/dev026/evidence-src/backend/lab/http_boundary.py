"""Bounded ASGI request buffering before JSON/multipart parsing.

The outer application's origin/token check runs first. Content-Length alone is
not an enforcement boundary: chunked and falsely declared bodies are counted.
"""
from starlette.responses import JSONResponse


class BoundedBody:
    def __init__(self,app,max_bytes):
        self.app=app;self.max_bytes=max_bytes

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':
            await self.app(scope,receive,send);return
        chunks=[];total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            body=message.get('body',b'');total+=len(body)
            if total>self.max_bytes:
                await JSONResponse({'detail':'Request body exceeds the configured upload envelope.'},status_code=413)(scope,receive,send)
                return
            chunks.append(body)
            if not message.get('more_body',False): break
        combined=b''.join(chunks);del chunks
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True
                return {'type':'http.request','body':combined,'more_body':False}
            return await receive()
        await self.app(scope,replay,send)
