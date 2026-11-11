"""Separate frozen-manifest, complete account/CSV and saved-fact reader for both provenance desktops.
This verifies scoped software behavior, not detector omission, market edge or final acceptance.
"""
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from io import StringIO
import csv,hashlib,json,os,re,struct,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.research import current_core_hash
from backend.lab.presentation_audit import audit_deck
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
browser=(root/sys.argv[1]).resolve();browser.relative_to(root);out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);lab=Lab(root)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b,tolerance='1e-7'):assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal(tolerance),(a,b)
records=[];images=[]
for observation in sorted((browser/'artifacts').glob('*/dataset-context-observations.json')):
 folder=observation.parent;v=read(observation);jid=v['job_id'];saved=read(folder/'saved-summary.json');report=read(folder/'saved-account.json');manifest=read_manifest(lab.datasets_root,v['dataset_id'])
 expected=dict(policy_version=1,dataset_id=manifest['id'],dataset_manifest_hash=hashlib.sha256(canonical(manifest)).hexdigest(),input_kind='synthetic',source='User import',symbols=manifest['quality']['symbols'])
 assert read(folder/'imported-manifest.json')==manifest
 assert v['expected_context']==saved['dataset_context']==report['dataset_context']==expected
 job=lab.store.job(jid);assert job['payload']['dataset_context']==expected
 assert saved==lab.result(jid) and report==lab.report(jid,0)
 assert saved['core_hash']==current_core_hash()==v['core_hash'] and len(saved['rows'])==1
 assert v['errors']==v['network']==[] and all(row['issues']==[] for row in v['layouts'])
 for filename in ['saved-screen.csv','saved-account.csv']:
  table=csv.DictReader(StringIO((folder/filename).read_text(encoding='utf-8')));rows=list(table)
  assert set(['input_kind','data_source','symbols','dataset_manifest_hash'])<=set(table.fieldnames)
  for row in rows:
   assert (row['input_kind'],row['data_source'],json.loads(row['symbols']),row['dataset_manifest_hash'])==('synthetic','User import',expected['symbols'],expected['dataset_manifest_hash'])
  if filename=='saved-screen.csv':assert len(rows)==1 and rows[0]['dataset_id']==expected['dataset_id']
  else:
   assert len(rows)==len(report['trades'])
   for row,trade in zip(rows,report['trades']):
    assert row['id']==trade['id'] and row['symbol']==trade['symbol']
    for field in ['entry_price','exit_price','entry_quantity','exit_quantity','net_pnl','fees','borrow','distributions']:close(row[field],trade[field])
 start=report['provenance']['warmup_start'];lab.guard.access(expected['symbols'],start,report['end'],'dataset_context_independent_account_read')
 frame,_=load_window(lab.datasets_root,report['dataset_id'],start,report['end']);actions=[Action(**a) for a in manifest['actions'] if start<=a['ex_date']<=report['end']]
 regular=prepare(frame,actions);signals=[s|dict(config_id=report['config_id']) for s in report['signals']]
 reference=execute(primitive(regular),signals,{report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end']);assert_parity(SimpleNamespace(**report),reference)
 equity=reference['equity'];close(report['metrics']['net_profit'],equity[-1]['equity']-Decimal(str(report['portfolio']['capital'])))
 legacy=read(folder/'legacy-summary.json');assert legacy==lab.result(v['legacy_job_id']) and 'dataset_context' not in legacy
 # The selected other dataset is genuinely cached historical input; it is not
 # synthetic geometry mislabeled for the UI test, and is not evaluated here.
 other=read_manifest(lab.datasets_root,v['unrelated_selection']);assert other['metadata']['input_kind']=='historical_market_data'
 audits=[]
 for prefix,document in [('new',saved),('legacy',legacy)]:
  html=(folder/(prefix+'-presentation.html')).read_text(encoding='utf-8');deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',html,re.S).group(1))
  assert len(deck['sources'])==1;audits.append(audit_deck({deck['sources'][0]['name']:canonical(document)},deck))
  context_facts={tuple(f['path']):f['value'] for f in deck['facts'].values() if f['path'][0]=='dataset_context'}
  if prefix=='new':
   assert len(context_facts)==7
   for key,value in expected.items():assert context_facts[('dataset_context',key)]==value
   assert context_facts[('dataset_context','symbols',0)]==expected['symbols'][0]
  else:assert not context_facts and any(p['title']=='Dataset context not recorded' for p in deck['pages'])
  assert len(deck['pages'])==next(d['pages'] for d in v['decks'] if d['prefix']==prefix)
  for index in range(len(deck['pages'])):
   p=folder/(prefix+'-page-'+str(index+1)+'.png');raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',raw[16:24]);assert dict(width=w,height=h)==v['viewport']
   images.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
 records.append(dict(profile=folder.name,job_id=jid,context=expected,trades=len(report['trades']),ledger_events=len(reference['ledger']),daily_marks=len(equity),legacy_core=legacy['core_hash'],presenter_audits=audits))
assert len(records)==2 and {r['profile'].split('-')[-1] for r in records}=={'desktop1920','desktop1280'}
value=dict(scope=__doc__,profiles=records,complete_independent_accounts=2,offline_screenshots=len(images),images=images)
(out/'dataset-context-browser-independent-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=2,complete_independent_accounts=2,offline_screenshots=len(images),trades=[r['trades'] for r in records],scope=__doc__)))
