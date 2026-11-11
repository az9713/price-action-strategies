"""Independent complete-universe facts and supplied-signal account reader, plus original desktop audits."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,json,os,re,runpy,struct,sys
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
runpy.run_path(str(root/'verification/runs/check-dataset-context-browser-evidence-v2.py'),run_name='__main__')
from backend.lab.service import Lab
from backend.lab.data import read_manifest,load_window,prepare,Action
from backend.lab.presentation_audit import audit_deck
from backend.lab.research import current_core_hash
from verification.reference_execution import execute
from test_reference_execution import primitive,assert_parity
lab=Lab(root);browser=root/sys.argv[1];out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);records=[]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
for p in sorted((browser/'artifacts').glob('*/universe-observations.json')):
 v=read(p);folder=p.parent;report=lab.report(v['job_id']);assert read(folder/'universe-report.json')==report
 m=read_manifest(lab.datasets_root,v['dataset_id']);assert read(folder/'universe-manifest.json')==m
 expected=dict(policy_version=1,dataset_id=m['id'],dataset_manifest_hash=hashlib.sha256(canonical(m)).hexdigest(),input_kind='synthetic',source='User import',symbols=sorted(v['symbols']))
 assert report['dataset_context']==lab.store.job(v['job_id'])['payload']['dataset_context']==expected
 assert len(expected['symbols'])==21 and report['core_hash']==current_core_hash()==v['core_hash']
 assert not v['errors'] and not v['network'] and all(not x for x in v['layouts'])
 start=report['provenance']['warmup_start'];lab.guard.access(expected['symbols'],start,report['end'],'universe_context_independent_account')
 prices,_=load_window(lab.datasets_root,m['id'],start,report['end']);actions=[Action(**a) for a in m['actions'] if start<=a['ex_date']<=report['end']]
 signals=[s|dict(config_id=report['config_id']) for s in report['signals']]
 reference=execute(primitive(prepare(prices,actions)),signals,{report['config_id']:report['config']},report['costs'],report['portfolio'],[a.__dict__ for a in actions],report['start'],report['end']);assert_parity(SimpleNamespace(**report),reference)
 html=(folder/'universe-presentation.html').read_text(encoding='utf-8');deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',html,re.S).group(1))
 assert len(deck['sources'])==1;audit=audit_deck({deck['sources'][0]['name']:canonical(report)},deck)
 facts={tuple(f['path']):f for f in deck['facts'].values() if f['path'][0]=='dataset_context'};assert len(facts)==27
 for key,value in expected.items():assert facts[('dataset_context',key)]['value']==value
 assert facts[('dataset_context','symbols')]['text']=='21 instruments; see indexed pages'
 assert [facts[('dataset_context','symbols',i)]['value'] for i in range(21)]==expected['symbols']
 assert len(deck['pages'])==v['pages']==len(v['layouts'])
 images=[]
 for i in range(v['pages']):
  image=folder/('universe-page-'+str(i+1)+'.png');raw=image.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',raw[16:24]);assert dict(width=w,height=h)==v['viewport'];images.append(dict(path=image.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
 records.append(dict(profile=folder.name,job_id=v['job_id'],context=expected,trades=len(report['trades']),ledger_events=len(reference['ledger']),presenter_audit=audit,screenshots=images))
assert len(records)==2
primary=read(out/'dataset-context-browser-independent-evidence.json')
value=dict(scope=__doc__,profiles=records,total_complete_accounts=primary['complete_independent_accounts']+2,total_offline_screenshots=primary['offline_screenshots']+sum(len(r['screenshots']) for r in records),financial_edge_claim=False)
(out/'complete-universe-independent-evidence.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='profiles'}))
