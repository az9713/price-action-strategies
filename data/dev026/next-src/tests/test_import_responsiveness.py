"""A slow local import must not hold the HTTP event loop or race another import."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from conftest import minute_frame
from test_api import client_lab
import backend.lab.api as api

def body():
 return dict(files={'file':('synthetic.csv',minute_frame('2026-11-02').to_csv(index=False).encode(),'text/csv')},data={'start':'2026-11-02','end':'2026-11-02','input_kind':'synthetic'})

def test_health_responds_while_an_actual_import_is_blocked_in_normalization(client_lab,monkeypatch):
 client,_=client_lab;entered=Event();release=Event();normalize=api.normalize
 def held(*a,**k):
  entered.set();assert release.wait(5),'Test did not release its owned import.'
  return normalize(*a,**k)
 monkeypatch.setattr(api,'normalize',held)
 with ThreadPoolExecutor(max_workers=2) as pool:
  imported=pool.submit(client.post,'/api/imports',**body())
  try:
   assert entered.wait(5)
   health=pool.submit(client.get,'/api/health')
   assert health.result(timeout=2).status_code==200
  finally:release.set()
  assert imported.result(timeout=10).status_code==201

def test_identical_concurrent_imports_publish_one_complete_immutable_dataset(client_lab):
 client,lab=client_lab
 with ThreadPoolExecutor(max_workers=2) as pool:
  calls=[pool.submit(client.post,'/api/imports',**body()) for _ in range(2)]
  responses=[r.result(timeout=20) for r in calls]
 assert [r.status_code for r in responses]==[201,201]
 assert responses[0].json()==responses[1].json()
 assert len(lab.datasets())==1 and lab.datasets()[0]['eligible']
