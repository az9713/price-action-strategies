"""Independent canonical-byte, original protocol, primary-window and registry reconciliation.

This audits actual saved synthetic signal qualification. It is not an independent
detector implementation, selected-account P&L, source-scale or final certificate.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip,hashlib,json,os,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);receipt_path=root/sys.argv[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def identity(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
def read(p):return json.loads(p.read_text(encoding='utf-8'))
receipt=read(receipt_path);assert receipt['command']['exit_code']==0
base=root/'verification/runs'/receipt['receipt_id']/'actual-spread-worker';assert base.is_dir()
for item in receipt['artifacts']:
 p=root/item['path'];assert p.stat().st_size==item['bytes'] and sha(p.read_bytes())==item['sha256']
inputs=read(base/'frozen-inputs.json');payload=inputs['payload'];binding=identity(payload);assert inputs['payload_sha256']==binding
events=read(base/'events.json');registry=read(base/'registry.json');folder=base/'original-job-artifacts'
result_bytes=(folder/'result.json.gz').read_bytes();result=json.loads(gzip.decompress(result_bytes))
saved=[e for e in events if e['kind']=='result_saved'];assert len(saved)==1 and saved[0]['details']['sha256']==sha(result_bytes)
assert result['payload_hash']==binding and result['job_id']==inputs['job_id'] and result['account_phase']=='not_started'
assert identity(result['numerical_contract'])==result['core_hash']==payload['core_hash']
assert payload['seed']==payload['settings']['seed'] and payload['context']['primary_symbol']==payload['primary_symbol']
protocol=[e['details'] for e in events if e['kind']=='spread_protocol'];head=None;planned={};starts={};completed={};selected=[];batches=[];sealed=None
settings=payload['settings'];context=payload['context'];ny=ZoneInfo('America/New_York')
def part(event):return settings['families'].index(event['family'])*settings['max_batches_per_family']*settings['batch_size']+event['batch']*settings['batch_size']+event['ordinal']
for number,envelope in enumerate(protocol):
 body={k:envelope[k] for k in ['sequence','previous','payload_sha256','event','artifact_sha256','owner']}
 assert body['sequence']==number and body['previous']==head and body['payload_sha256']==binding and identity(body)==envelope['event_sha256']
 head=envelope['event_sha256'];event=body['event'];kind=event['kind']
 if kind=='preparation_batch':batches.append(event['record'])
 elif kind=='preparation_sealed':assert sealed is None;sealed=event['plan_id']
 elif kind=='probe_planned':assert part(event) not in planned;planned[part(event)]=event
 elif kind=='probe_started':starts.setdefault(part(event),[]).append((event['attempt'],body['owner']))
 elif kind=='probe_completed':completed[part(event)]=(event,body['artifact_sha256'])
 elif kind=='version_selected':selected.append(event)
manifest=read(folder/'spread-proposals/manifest.json');header=read(folder/'spread-preparation/contract.json')
assert identity(manifest)==sealed and identity(header)==manifest['preparation_contract_hash'] and header['binding']==binding
assert manifest['settings']==header['settings']==settings
assert len(batches)==len(settings['families'])*settings['max_batches_per_family']
configurations={};planned_versions=0
for family in settings['families']:
 p=folder/'spread-proposals'/(family+'.jsonl.gz');raw=p.read_bytes();assert manifest['files'][family]==dict(bytes=len(raw),sha256=sha(raw))
 rows=[json.loads(line) for line in gzip.decompress(raw).splitlines()];assert len(rows)==settings['max_batches_per_family']
 for batch,row in enumerate(rows):
  assert row['family']==family and row['batch']==batch and len(row['configurations'])==settings['batch_size']
  record=next(r for r in batches if r['family']==family and r['batch']==batch);p=folder/'spread-preparation'/record['relative_path'];compressed=p.read_bytes()
  assert len(compressed)==record['bytes'] and sha(compressed)==record['sha256'] and json.loads(gzip.decompress(compressed))==row and identity(row['configurations'])==record['configurations_hash']
  for ordinal,cfg in enumerate(row['configurations']):configurations[(family,batch,ordinal)]=cfg;planned_versions+=1
assert planned_versions==manifest['planned_proposals']==result['spread_selection']['planned_proposals']
counts=[];documents=[]
for key,(event,artifact_hash) in completed.items():
 digest=event['evidence']['evidence_sha256'];p=folder/'spread-signals'/(digest+'.json.gz');raw=p.read_bytes();assert sha(raw)==artifact_hash
 report=json.loads(gzip.decompress(raw));assert identity(report)==digest
 cfg=configurations[(event['family'],event['batch'],event['ordinal'])]
 assert report['config']==cfg and identity(cfg)==report['config_id']==event['config_id']==planned[key]['config_id']
 assert report['context']==context and report['numerical_contract']==result['numerical_contract'] and report['core_hash']==result['core_hash']
 assert report['dataset_context']['input_kind']=='synthetic' and not {'metrics','trades','equity','ledger'}&set(report)
 window=0
 for signal in report['signals']:
  assert signal['symbol']==context['primary_symbol'];timestamp=datetime.fromisoformat(signal['available_at']);assert timestamp.tzinfo is not None
  day=timestamp.astimezone(ny).date().isoformat();window+=context['start']<=day<=context['end']
 assert window==report['signal_count']==event['evidence']['signal_count'] and report['excluded_warmup_signals']==len(report['signals'])-window
 counts.append(window);documents.append(dict(part=key,config_id=report['config_id'],full_signals=len(report['signals']),discovery_signals=window,excluded_warmup=report['excluded_warmup_signals'],artifact_sha256=artifact_hash,canonical_sha256=digest))
selection=result['selection_manifest'];assert selection['configurations']==[e['configuration'] for e in selected]
assert identity(selection)==result['selection_manifest_hash']==result['spread_selection']['selection_manifest_hash']
assert all(completed[part(e)][0]['evidence']['signal_count']>=settings['minimum_signals'] for e in selected)
assert registry['totals']['computation_attempts']==sum(map(len,starts.values()))==len(completed)==9
assert set(registry['totals']['roles'])=={'signal_probe'} and registry['totals']['planned_occurrences']==len(planned)
phases={e['details']['trial_id']:e['details'] for e in events if e['kind']=='staged_trial_frozen'}
for row in registry['rows']:
 phase=phases[row['id']];original={k:v for k,v in phase.items() if k not in {'trial_id','plan_hash'}}
 assert identity(original)==phase['plan_hash']==row['plan_hash'] and phase['proposal_plan_id']==sealed and phase['payload_hash']==binding
 assert row['attempts']==len(starts[row['part']]) and row['computed_sha256']==completed[row['part']][0]['evidence']['evidence_sha256'] and row['artifact_sha256']==completed[row['part']][1]
assert len([e for e in events if e['kind']=='trial_plan_frozen'])==1
value=dict(scope=__doc__,input_payload_hash=binding,core_hash=result['core_hash'],frozen_proposals=planned_versions,committed_batches=len(batches),signal_documents=documents,discovery_signal_counts=counts,selected_versions=len(selected),protocol_events=len(protocol),protocol_head=head,financial_accounts_executed=0,source_scale_executed=False,final_acceptance_certified=False)
(out/'independent-durable-spread-audit.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='signal_documents'},indent=2))
