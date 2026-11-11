from pathlib import Path
import hashlib,json,os,re
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);files=['STATUS.md','verification/evidence-index.md','verification/defects.json'];links=0
for name in files[:2]:
 p=root/name;text=p.read_text(encoding='utf-8');assert 'Latest0.16' in text and '1446' in text and '422' in text and 'no_candidates' in text
 for target in re.findall(r'\]\(([^)]+)\)',text):
  if target.startswith(('http://','https://','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(name,target);links+=1
v=json.loads((root/files[2]).read_text(encoding='utf-8'));assert len({d['id'] for d in v['defects']})==len(v['defects'])
for d in v['defects'][-7:]:
 for key in ('initial_evidence','regression_receipt','full_regression_receipt'):assert (root/d[key]).is_file()
result=dict(scope='Current documentation integrity and retained-failure links, not final acceptance.',files=[dict(path=n,sha256=hashlib.sha256((root/n).read_bytes()).hexdigest()) for n in files],local_links_checked=links,total_defect_records=len(v['defects']),new_retained_failure_records=7)
(out/'documentation-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
