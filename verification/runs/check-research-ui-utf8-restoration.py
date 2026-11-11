"""Reconcile untouched App text with its original pre-integration source hash."""
import hashlib,json,os,re
from pathlib import Path
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
rid='20261110T104323032525Z-funnel-public-original-registration-seeded-generation-full-worker-final-and-http-boundaries'
receipt=json.loads((root/'verification/receipts'/(rid+'.json')).read_text(encoding='utf-8'))
items=[a for a in receipt['artifacts'] if a['path'].endswith('/research-stage-subject.json')]
assert len(items)==1
p=root/items[0]['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==items[0]['sha256']
subject=json.loads(p.read_text(encoding='utf-8'));assert not subject['changed_during_check']
app=root/'data/dev027/research-src/frontend/src/App.tsx';s=app.read_text(encoding='utf-8')
changes=[
 ("import {ResearchFunnel} from './ResearchFunnel';\n",''),
 ("type Page='Research funnel'|'Data'|","type Page='Data'|"),
 ("const pages:Page[]=['Data','Research funnel',","const pages:Page[]=['Data',"),
 ("\n  const [funnelStudy,setFunnelStudy]=useState(()=>localStorage.getItem('research-funnel-study')||'');\n  useEffect(()=>{localStorage.setItem('research-funnel-study',funnelStudy);},[funnelStudy]);",''),
 ("      if(part===null&&['funnel_qualification','funnel_final'].includes(value.kind)){setFunnelStudy(value.study_id);if(go&&navigationRevision.current===navigationAtStart)setPage('Research funnel');return;}\n",''),
 ("'Research funnel':'Freeze a complete cohort, qualify it, and preserve both final instruments.',",''),
 ("s.status==='registered'&&!s.spec.funnel_version&&<button","s.status==='registered'&&<button")]
for old,new in changes:
    assert s.count(old)==1
    s=s.replace(old,new)
s,count=re.subn(r"\{page==='Research funnel'&&<ResearchFunnel[^\n]+\n\n  ",'',s);assert count==1
expected=subject['source_files']['frontend/src/App.tsx']
reconstructed=hashlib.sha256(s.replace('\n','\r\n').encode('utf-8')).hexdigest()
assert reconstructed==expected
component=root/'data/dev027/research-src/frontend/src/ResearchFunnel.tsx';text=component.read_text(encoding='utf-8')
assert '\u2013' in text and '\u2265' in text
for file in [app,component]:
    value=file.read_text(encoding='utf-8')
    assert '\u00c3' not in value and '\u00c2' not in value
result=dict(pre_integration_receipt=rid,baseline_run_passed=False,baseline_source_coherent=True,
    intended_app_additions_removed_only_in_memory=True,original_app_bytes_sha256=expected,
    reconstructed_original_app_bytes_sha256=reconstructed,unrelated_original_text_exactly_restored=True,
    utf8_glyphs_present=True,source_files_modified_by_check=False,not_browser_or_final_acceptance=True)
(out/'ui-utf8-original-source-reconciliation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
