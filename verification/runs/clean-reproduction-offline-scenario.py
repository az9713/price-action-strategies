"""Synthetic saved-account restart under a process-local external-socket audit guard."""
from pathlib import Path
import ipaddress,json,os,socket,sys,time
source=Path(sys.argv[1]).resolve();sys.path.insert(0,str(source));blocked=[]
PROBE_STARTUP_SECONDS=120
PROBE_ACCOUNT_SECONDS=120
def is_loopback(host):
 if host in {None,'localhost','localhost.'}:return True
 try:return ipaddress.ip_address(host).is_loopback
 except ValueError:return False
def offline_guard(event,args):
 if event=='socket.getaddrinfo' and not is_loopback(args[0]):
  blocked.append(event);raise OSError('External network disabled by owned reproduction fixture')
 if event=='socket.connect':
  address=args[1]
  if isinstance(address,tuple) and not is_loopback(address[0]):
   blocked.append(event);raise OSError('External network disabled by owned reproduction fixture')
sys.addaudithook(offline_guard)
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.config import Strategy,identity
from backend.lab.data import save_dataset,schedule
from backend.lab.research import core_hash
import numpy as np,pandas as pd

def exercise():
 out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=False);store=out/'owned-store';app=create_app(store,run_worker=True)
 expected_core=sys.argv[3] if len(sys.argv)==4 else 'e25126a77ca89ae2c7301d50d4551cdadee9c43dd88f011b4bd4569f97ba395d'
 assert core_hash()==expected_core
 assert Path(__import__('backend.lab.api',fromlist=['ROOT']).__file__).resolve().is_relative_to(source)
 # Prove the guard actually rejects both external address resolution and direct IP sockets.
 for attempt in [lambda:socket.getaddrinfo('example.invalid',443),lambda:socket.socket().connect(('203.0.113.1',443))]:
  try:attempt();raise AssertionError('External socket guard did not reject a positive control')
  except OSError:pass
 denied_positive_controls=len(blocked);assert denied_positive_controls==2
 frames=[]
 # Known discriminating geometry, completed to whole sessions. Random shared
 # open/close extrema are not a reliable positive strict-pivot fixture.
 authored=json.loads((source/'verification/fixtures/strategy-baselines.json').read_text(encoding='utf-8'))['common_closes']
 for day,(opened,closed) in schedule('2026-11-02','2026-11-06').items():
  ticks=pd.date_range(opened,closed,freq='min',inclusive='left');values=np.full(len(ticks),200.);values[:len(authored)]=authored
  for symbol,side in [('SPY',1),('QQQ',-1)]:
   closes=values if side==1 else 300-values
   frames.append(pd.DataFrame(dict(symbol=symbol,timestamp=ticks,open=closes-.02,high=closes+.1,low=closes-.1,close=closes,volume=10000.)))
 manifest=save_dataset(app.state.lab.datasets_root,pd.concat(frames,ignore_index=True),dict(input_kind='synthetic',source='Prespecified authored mirrored strict-pivot geometry; complete sessions'),start='2026-11-02',end='2026-11-06')
 reports=[];jobs=[];strategies=[];originals={};worker_pids=[]
 def client(a):return TestClient(a,base_url='http://localhost:8799',client=('127.0.0.1',51000))
 def ready(c):
  deadline=time.monotonic()+PROBE_STARTUP_SECONDS
  while True:
   h=c.get('/api/health').json()
   if h['worker_ready']:assert h['worker_alive'] and h['store_lease_held'] and not h['credentials_configured'];worker_pids.append(h['worker_pid']);return
   assert time.monotonic()<deadline,'Owned offline worker readiness timeout';time.sleep(.05)
 def mutation_headers(c):return {'Origin':'http://localhost:8799','X-Lab-Token':c.get('/api/session').json()['token']}
 with client(app) as c:
  ready(c);headers=mutation_headers(c)
  for side in ['long','short']:
   cfg=Strategy(family='break_of_structure',timeframe='1m',direction=side,swing_strength=2,stop_reference='level',max_hold=24,target='2R')
   saved=c.post('/api/strategies',headers=headers,json={'name':'Offline '+side,'strategy':cfg.model_dump()});assert saved.status_code==201;strategies.append(saved.json()['id'])
   response=c.post('/api/experiments',headers=headers,json=dict(dataset_id=manifest['id'],start='2026-11-02',end='2026-11-06',strategy=cfg.model_dump(),seed=42));assert response.status_code==202,response.text;job=response.json()['id'];jobs.append(job)
   deadline=time.monotonic()+PROBE_ACCOUNT_SECONDS
   while True:
    state=c.get('/api/jobs/'+job).json()
    if state['status']=='completed':break
    assert state['status'] not in ['failed','canceled'],state
    assert time.monotonic()<deadline,'Owned offline account timeout';time.sleep(.05)
   response=c.get('/api/jobs/'+job+'/report');assert response.status_code==200,response.text;report=response.json();assert report['signals'] and report['trades'];assert report['config']['direction']==side
   for format in ['json','csv','html','presentation.json']:
    response=c.get('/api/jobs/'+job+'/export/'+format);assert response.status_code==200 and response.content
    originals[(job,format)]=response.content
    if format=='json':assert response.json()==report
   reports.append(report)
  assert any(d['id']==manifest['id'] for d in c.get('/api/datasets').json())
 assert not app.state.worker_process.is_alive() and app.state.store_lease.handle is None
 # Same owned store, new actual spawned worker, unchanged original saved outputs.
 restarted=create_app(store,run_worker=True)
 with client(restarted) as c:
  ready(c);assert set(strategies)<={s['id'] for s in c.get('/api/strategies').json()}
  assert any(d['id']==manifest['id'] for d in c.get('/api/datasets').json())
  for job,report in zip(jobs,reports):
   assert c.get('/api/jobs/'+job).json()['status']=='completed'
   assert c.get('/api/jobs/'+job+'/report').json()==report
   for format in ['json','csv','html','presentation.json']:
    response=c.get('/api/jobs/'+job+'/export/'+format);assert response.status_code==200 and response.content==originals[(job,format)]
 assert not restarted.state.worker_process.is_alive() and restarted.state.store_lease.handle is None
 assert len(blocked)==denied_positive_controls,'Saved workflow attempted external network'
 # Explicit fixture credentials exercise the read-only provider transport failure; no real .env is accessed.
 from backend.lab.provider import Alpaca,ProviderError
 fixture=out/'nonsecret-offline-provider-input.txt';fixture.write_text('ALPACA_API_KEY=fixture-key\nALPACA_SECRET_KEY=fixture-secret\n',encoding='utf-8')
 with Alpaca(fixture,out/'owned-provider-cache') as provider:
  try:provider._request('/v2/stocks/bars',{'symbols':'SPY'});raise AssertionError('Uncached offline provider request unexpectedly succeeded')
  except ProviderError as error:assert 'timed out or failed' in str(error)
 assert len(blocked)>denied_positive_controls
 scientific=dict(dataset_manifest=manifest,reports=reports)
 (out/'scientific-reports.json').write_text(json.dumps(scientific,sort_keys=True,separators=(',',':'),allow_nan=False),encoding='utf-8')
 value=dict(scope=__doc__,core_hash=core_hash(),signals=[len(r['signals']) for r in reports],trades=[len(r['trades']) for r in reports],long_and_short_executed=True,original_export_formats=['json','csv','html','presentation.json'],original_exports_identical_after_restart=True,worker_pids=worker_pids,workers_exited=True,guard_positive_controls=denied_positive_controls,external_attempts_during_saved_workflow=0,provider_transport_denials=len(blocked)-denied_positive_controls,uncached_provider_failed_clearly=True,network_boundary='Process-local Python socket audit, installed before backend imports and inherited by script-based spawned workers; not an OS firewall or graphical browser assertion.',final_acceptance_certified=False)
 (out/'offline-summary.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
if __name__=='__main__':exercise()
