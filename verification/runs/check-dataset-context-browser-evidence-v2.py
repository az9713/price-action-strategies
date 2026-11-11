"""Keep exact saved source bytes for deck fingerprints; preserve every parity/fact check.
The browser's legacy JSON.stringify observation normalizes integral float spellings.
It is semantically equal but cannot stand in for the original canonical source bytes.
"""
from pathlib import Path
import hashlib,json,os,re,sys
root=Path.cwd();sys.path.insert(0,str(root));from backend.lab.service import Lab
lab=Lab(root);browser=root/sys.argv[1];rows=[]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
for observation in sorted((browser/'artifacts').glob('*/dataset-context-observations.json')):
 v=json.loads(observation.read_text(encoding='utf-8'))
 for prefix,file,jid in [('new','saved-summary.json',v['job_id']),('legacy','legacy-summary.json',v['legacy_job_id'])]:
  observed=json.loads((observation.parent/file).read_text(encoding='utf-8'));original=lab.result(jid)
  deck=json.loads(re.search(r'<script id="presentation-manifest" type="application/json">(.*?)</script>',(observation.parent/(prefix+'-presentation.html')).read_text(encoding='utf-8'),re.S).group(1))
  assert observed==original and digest(original)==deck['sources'][0]['sha256']
  rows.append(dict(profile=observation.parent.name,prefix=prefix,artifact_semantically_equal=True,artifact_hash_matches_original=digest(observed)==deck['sources'][0]['sha256'],original_canonical_hash_matches=True))
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'canonical-source-diagnostic.json').write_text(json.dumps(dict(scope=__doc__,rows=rows),indent=2),encoding='utf-8')
source=(root/'verification/runs/check-dataset-context-browser-evidence.py').read_text(encoding='utf-8')
before="audit_deck({deck['sources'][0]['name']:canonical(document)},deck)"
after="audit_deck({deck['sources'][0]['name']:canonical(lab.result(jid if prefix=='new' else v['legacy_job_id']))},deck)"
assert source.count(before)==1
exec(compile(source.replace(before,after),'dataset-context-independent-source-bytes-resolved.py','exec'))
