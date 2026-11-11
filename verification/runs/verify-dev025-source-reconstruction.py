"""Restore the WIP source from hash-checked archives in a fresh owned directory.

Uses the existing locked environment, not a fresh dependency installation. Does
not restore credentials, cached prices, live databases or final acceptance.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,shutil,stat,subprocess,sys,uuid,zipfile
root=Path.cwd();run=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def receipt(name):
 p=root/name;r=read(p);assert r['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 for a in r['artifacts']:
  q=root/a['path'];assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256'],a['path']
 return r
r=receipt(sys.argv[1]);a=next(a for a in r['artifacts'] if a['path'].endswith('/spread-ui-source-checkpoint.json'));checkpoint=read(root/a['path']);base=receipt(checkpoint['base_receipt'])
base_manifest=read(root/next(a['path'] for a in base['artifacts'] if a['path'].endswith('/source-checkpoint-manifest.json')));expected={v['path']:v for v in base_manifest}
archive=root/checkpoint['base_archive']['path'];assert sha(archive)==checkpoint['base_archive']['sha256']
owned=root/'data/dev025/reconstructions'/uuid.uuid4().hex;owned.mkdir(parents=True,exist_ok=False);assert owned.resolve().is_relative_to((root/'data/dev025/reconstructions').resolve())
def target(name):
 path=PurePosixPath(name);assert not path.is_absolute() and ':' not in name and '..' not in path.parts and not any(p.lower().startswith('.env') for p in path.parts)
 p=owned.joinpath(*path.parts);assert p.resolve().is_relative_to(owned.resolve());return p
with zipfile.ZipFile(archive) as z:
 assert set(z.namelist())==set(expected)
 for info in z.infolist():
  assert not info.is_dir() and not stat.S_ISLNK(info.external_attr>>16)
  raw=z.read(info);meta=expected[info.filename];assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
  p=target(info.filename);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
dist=owned/'frontend/dist'
if dist.exists():
 assert not dist.is_symlink() and dist.resolve().is_relative_to(owned.resolve()) and dist.resolve()==(owned.resolve()/'frontend/dist')
 shutil.rmtree(dist)
overlay_root=(root/a['path']).parent/'source-overlay'
for meta in checkpoint['overlay']:
 p=overlay_root/meta['path'];assert p.stat().st_size==meta['bytes'] and sha(p)==meta['sha256'];q=target(meta['path']);q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
def source_check():
 for name,digest in checkpoint['source_files'].items():assert sha(target(name))==digest,name
source_check()
actual_assets={p.relative_to(owned).as_posix():sha(p) for p in dist.rglob('*') if p.is_file()}
assert actual_assets=={v['path']:v['sha256'] for v in checkpoint['overlay'] if v['path'].startswith('frontend/dist/')}
environment=os.environ.copy();environment['PYTHONPATH']=str(owned);environment['PYTHONNOUSERSITE']='1'
probe='from backend.lab.research import core_hash,current_core_hash;import json;print(json.dumps(dict(core_hash=core_hash(),current_core_hash=current_core_hash())))'
observations=[]
for cwd in [root/'data/dev025/src',owned]:
 environment['PYTHONPATH']=str(cwd);p=subprocess.run([sys.executable,'-c',probe],cwd=cwd,env=environment,capture_output=True,text=True,check=True);observations.append(json.loads(p.stdout))
assert observations[0]==observations[1] and observations[0]['core_hash']==observations[0]['current_core_hash']
environment['PYTHONPATH']=str(owned);p=subprocess.run([sys.executable,'-m','pytest','-q','-c','pyproject.toml','tests/test_spread_public_schema.py','tests/test_coverage_gate.py','--junitxml='+str(run/'reconstruction-junit.xml')],cwd=owned,env=environment,capture_output=True)
sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);source_check()
catalog=read(owned/'verification/catalog.json');assert len(catalog['requirements'])==83 and len(catalog['cases'])==422
value=dict(scope=__doc__,source_checkpoint_receipt=sys.argv[1],source_files_verified=len(checkpoint['source_files']),base_archive_files=len(expected),overlay_files=len(checkpoint['overlay']),core_subjects=observations,compiled_assets=actual_assets,child_exit_code=p.returncode,owned_source=owned.relative_to(root).as_posix(),final_acceptance_certified=False)
(run/'source-reconstruction.json').write_text(json.dumps(value,indent=2),encoding='utf-8');raise SystemExit(p.returncode)
