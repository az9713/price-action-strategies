"""Independent canonical input/projection/history audit plus Decimal supplied-signal portfolio accounting."""
from pathlib import Path
import hashlib,json,os,runpy,struct,sys,urllib.request
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);base='http://127.0.0.1:8767'
def get(path):
 with urllib.request.urlopen(base+path,timeout=30) as response:return response.read()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def browser(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];receipt=json.loads(p.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
 return root/'verification/runs'/receipt['receipt_id']/'browser'
monitor=browser('study-status-current-two-desktop-download-repair-history-ownership-and-current-errors');records=[]
health=json.loads(get('/api/health'));assert health['source_current'] and health['worker_ready'] and health['store_lease_held']
for path in sorted(monitor.rglob('study-status-observations.json')):
 observation=json.loads(path.read_text(encoding='utf-8'));source=path.with_name('complete-original-study-inputs.json');raw=source.read_bytes();full=json.loads(raw);sid=observation['study_id'];spec=full['study']['spec']
 excluded={'screening_report_hash','candidates','candidate_hash','final_job_id','reserved_final_job_id'}
 expected=digest({k:v for k,v in spec.items() if k not in excluded})
 assert expected==full['spec_hash']==observation['spec_hash']
 assert get('/api/studies/'+sid+'/inputs')==raw
 assert len(spec['configurations'])==len({digest(c) for c in spec['configurations']})==1000
 assert spec['dataset_context']['symbols']==spec['symbols']==[observation['symbol']]
 status=json.loads(get('/api/studies/'+sid));assert status['index_integrity'] and status['index_provenance']=='rebuilt_verified_registration'
 assert status['status']=='registered' and status['spec']['configuration_count']==1000 and status['spec']['candidate_count'] is None
 assert 'configurations' not in status['spec'] and status['spec_hash']==expected
 events_raw=get('/api/studies/'+sid+'/events');events=json.loads(events_raw)
 assert len([e for e in events if e['kind']=='study_registered' and e['details']['spec_hash']==expected])==1
 assert len([e for e in events if e['kind']=='study_input_index_repaired' and e['details']['spec_hash']==expected])==1
 assert not [e for e in events if e['kind'] in ['candidates_frozen','final_unlock_consumed','portfolio_final_reserved']]
 assert observation['price_accounts_executed']==0 and observation['errors']==[]
 (out/(sid+'-study-events.json')).write_bytes(events_raw)
 images=[]
 for image_path in sorted(path.parent.glob('*.png')):
  image_raw=image_path.read_bytes();assert image_raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',image_raw[16:24]);assert dict(width=w,height=h)==observation['viewport']
  images.append(dict(path=image_path.relative_to(root).as_posix(),sha256=hashlib.sha256(image_raw).hexdigest()))
 assert len(images)>=3
 records.append(dict(study_id=sid,viewport=observation['viewport'],spec_hash=expected,original_download_sha256=hashlib.sha256(raw).hexdigest(),configurations=1000,unique_configs=1000,original_bytes_equal_live_inputs=True,screenshots=images))
assert len(records)==2 and sorted(r['viewport']['width'] for r in records)==[1280,1920]
histories=[]
for path in sorted(monitor.rglob('study-history-transport-observations.json')):
 value=json.loads(path.read_text(encoding='utf-8'));assert value['long_refresh_additional_requests']==0 and value['errors']==[]
 assert value['current_failure_preserved_last_verified_page'] and value['current_failure_recovered']
 assert [r['stale'] for r in value['observations']]==['success','failure']
 assert all(r['shown_records']=='501 to 505' and r['stale_error_visible'] is False for r in value['observations'])
 histories.append(value)
assert len(histories)==2
(out/'independent-study-status-browser-evidence.json').write_text(json.dumps(dict(scope=__doc__,core_hash=health['core_hash'],metadata_profiles=records,controlled_transport_profiles=histories,financial_outcome_certified=False),indent=2),encoding='utf-8')
joint=browser('study-status-current-two-desktop-portfolio-final-and-result-ownership')
sys.argv=['verification/runs/check-main-portfolio-study-browser-accounts.py',joint.relative_to(root).as_posix()]
runpy.run_path(sys.argv[0],run_name='__main__')
print(json.dumps(dict(metadata_profiles=len(records),independent_input_configurations=2000,controlled_transport_profiles=len(histories),source_bytes_preserved=True,scope=__doc__)))
