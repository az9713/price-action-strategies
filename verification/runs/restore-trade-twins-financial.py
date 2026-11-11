"""Actually restore source-only archive to a new directory and execute components.

Existing locked dependencies are reused; this is not a fresh installation.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,zipfile,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=(root/sys.argv[1]).resolve();assert p.is_relative_to((root/'verification/receipts').resolve())
r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
artifacts={}
for a in r['artifacts']:
 q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];artifacts[q.name]=q
checkpoint=read(artifacts['trade-twins-financial-checkpoint.json']);manifest=read(artifacts['trade-twins-financial-manifest.json']);archive=artifacts['trade-twins-financial-source.zip']
assert sha(archive)==checkpoint['archive_sha256']
target=root/'data/dev026/reconstructions'/out.name;assert not target.exists();target.mkdir(parents=True)
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==len(manifest)==checkpoint['archive_files'] and set(z.namelist())=={m['path'] for m in manifest}
 for item in manifest:
  relative=Path(item['path']);dest=(target/relative).resolve()
  assert not relative.is_absolute() and dest.is_relative_to(target.resolve()) and not any(part.lower().startswith('.env') for part in relative.parts)
  raw=z.read(item['path']);assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join([str(target),str(target/'tests')]),PYTHONNOUSERSITE='1',PA_EVIDENCE_RUN_DIR=str(out),PA_FEATURE_PROTOTYPE_PATH=str(target/'verification/runs/trade_twin_features_draft.py'),PA_GRADE_PROTOTYPE_PATH=str(target/'verification/runs/trade_twin_decimal_grading_draft.py'))
probe=subprocess.run([sys.executable,'-c','from backend.lab.research import core_hash,current_core_hash;import json;print(json.dumps(dict(loaded=core_hash(),current=current_core_hash())))'],cwd=target,env=env,capture_output=True,text=True,check=True)
core=json.loads(probe.stdout);assert core==checkpoint['isolated_core']
args=[sys.executable,'-m','pytest','-q','-c',str(target/'pyproject.toml'),'tests/test_trade_twin_execution.py','tests/test_trade_twin_source.py','tests/test_entry_traces.py','tests/test_trade_twins.py','tests/test_coverage_gate.py','tests/test_catalog_generation.py','tests/test_spread_public_schema.py',str(target/'verification/runs/test_trade_twin_features_prototype.py'),str(target/'verification/runs/test_trade_twin_decimal_grading_prototype.py'),'--junitxml='+str(out/'restored-source-junit.xml')]
args[6:6]=['tests/test_spread.py','tests/test_spread_faults.py','tests/test_spread_saved_boundaries.py','tests/test_spread_transaction_boundaries.py']
executed=subprocess.run(args,cwd=target,env=env,capture_output=True,timeout=900)
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')])
for raw in [executed.stdout,executed.stderr]:scrub.learn(raw.decode('utf-8',errors='replace'))
for name,raw in [('stdout',executed.stdout),('stderr',executed.stderr)]:
 (out/('restore-'+name+'.log')).write_text(scrub.clean(raw.decode('utf-8',errors='replace')),encoding='utf-8')
 print(scrub.clean(raw.decode('utf-8',errors='replace')))
assert executed.returncode==0
suites=list(ET.parse(out/'restored-source-junit.xml').iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
assert counts['tests']>=578 and counts['failures']==counts['errors']==counts['skipped']==0
for item in manifest:assert sha(target/item['path'])==item['sha256'] and (target/item['path']).stat().st_size==item['bytes']
assert not list(target.rglob('.env'))
value=dict(scope=__doc__,archive_receipt=r['receipt_id'],archive_sha256=sha(archive),files_restored=len(manifest),core=core,tests=counts,all_restored_source_bytes_unchanged=True,locked_existing_environment_reused=True,credentials_prices_and_user_databases_copied=False,financial_sets_executed=0,final_acceptance_certified=False)
(out/'trade-twins-financial-restoration.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
