"""Compare original/fresh complete synthetic accounts and actual cached API restart under external socket denial."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
receipt=sorted((root/'verification/receipts').glob('*-current-clean-locked-install-frontend-byte-rebuild-and-full-backend-reproduction.json'))[-1];r=json.loads(receipt.read_text(encoding='utf-8'));assert r['command']['exit_code']==0
artifact=next(a for a in r['artifacts'] if a['path'].endswith('/clean-reproduction.json'));p=root/artifact['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==artifact['sha256'];fresh=json.loads(p.read_text(encoding='utf-8'));base=root/fresh['owned_directory'];scenario=root/'verification/runs/clean-reproduction-offline-scenario.py'
private=root/'data/private-evidence/clean-offline'/out.name;private.mkdir(parents=True,exist_ok=False);summaries=[];reports=[];lineage=[]
for label,python,source in [('original',Path(sys.executable),root),('fresh',base/'venv/Scripts/python.exe',base/'src')]:
 owned=base/('offline-'+label+'-'+out.name[:22]);assert not owned.exists();args=[str(python),str(scenario),str(source),str(owned)];started=time.monotonic()
 result=subprocess.run(args,cwd=source,capture_output=True,timeout=180)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')]);decoded={name:raw.decode('utf-8',errors='replace') for name,raw in [('stdout',result.stdout),('stderr',result.stderr)]}
 for text in decoded.values():scrub.learn(text)
 for name,raw in [('stdout',result.stdout),('stderr',result.stderr)]:
  original=private/(label+'-'+name+'.log');original.write_bytes(raw);derived=out/(label+'-'+name+'.log');derived.write_text(scrub.clean(decoded[name]),encoding='utf-8');lineage.append(dict(original_private=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.name,derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 print(json.dumps(dict(label=label,exit_code=result.returncode,elapsed_seconds=time.monotonic()-started)),flush=True)
 (out/'privacy-lineage-progress.json').write_text(json.dumps(lineage,indent=2),encoding='utf-8')
 assert result.returncode==0,(label,result.returncode,'See retained sanitized stderr')
 summary=json.loads((owned/'offline-summary.json').read_text(encoding='utf-8'));summaries.append(dict(label=label,**summary));raw=(owned/'scientific-reports.json').read_bytes();reports.append(json.loads(raw));(out/(label+'-complete-scientific-reports.json')).write_bytes(raw)
assert reports[0]==reports[1],'Complete manifest/report equality failed; no fields excluded'
value=dict(scope=__doc__,environment_summaries=summaries,complete_manifest_and_report_equality=True,financial_or_provenance_fields_excluded=[],privacy_lineage=lineage,final_acceptance_certified=False)
(out/'offline-reproduction.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='privacy_lineage'},indent=2))
