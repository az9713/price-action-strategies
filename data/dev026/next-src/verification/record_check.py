"""Run an implementation check and preserve a schema-valid, redacted evidence receipt.

This records actual commands/results, never infers acceptance-case passes. Product
case certification will require the completed test mapping and verification runner.
"""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import shutil
import os
import zipfile
from jsonschema import Draft202012Validator,FormatChecker

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from verification.trace_privacy import Sanitizer,PrivacyError,audit_archive

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def source_paths(root=ROOT):
    paths=[root/name for name in ['PLAN.md','VERIFICATION_PLAN.md','RULEBOOK.md','decisions.md','README.md','THIRD_PARTY_NOTICES.md','pyproject.toml','requirements.lock','strategy.schema.json','verification/catalog.json','verification/implementation-map.json','verification/receipt.schema.json','verification/record_check.py']]
    paths+=sorted((root/'backend').rglob('*.py'))+sorted((root/'tests').rglob('*.py'))
    paths+=sorted(p for p in (root/'verification').glob('*.py') if p.name!='record_check.py')
    paths+=sorted(p for p in (root/'frontend'/'src').rglob('*') if p.is_file())
    paths+=sorted((root/'frontend'/'tests').rglob('*.ts'))
    paths+=[root/p for p in ['frontend/package.json','frontend/package-lock.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/playwright.config.ts','frontend/index.html','start.ps1'] if (root/p).exists()]
    return list(dict.fromkeys(paths))

def inventory_changes(before,initial_sources,root=ROOT):
    changed=[p for p,digest in before.items() if not (root/p).exists() or sha(root/p)!=digest]
    after={p.relative_to(root).as_posix() for p in source_paths(root)}
    added=sorted(after-set(initial_sources))
    return changed,added

def redact(value,root=ROOT,scrubber=None):
    # JSON/trace diagnostics may contain escaped Windows paths. Redact those
    # too, while preserving valid JSON and keeping credentials out of evidence.
    scrubber=scrubber or Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')])
    scrubber.learn(value)
    return scrubber.clean(value)

def review_artifact_allowed(path,root=ROOT):
    relative=path.resolve().relative_to(root.resolve())
    if [p.lower() for p in relative.parts[:2]]==['data','private-evidence']:return False
    if path.suffix.lower()=='.zip' or zipfile.is_zipfile(path):
        try:
            with zipfile.ZipFile(path) as z:is_trace=any(n.lower().endswith('.trace') for n in z.namelist())
            if is_trace:audit_archive(path)
        except (zipfile.BadZipFile,PrivacyError,OSError):return False
    return True

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    parser=argparse.ArgumentParser()
    parser.add_argument('--label',required=True)
    parser.add_argument('--input',action='append',default=[])
    parser.add_argument('--artifact',action='append',default=[])
    parser.add_argument('--artifact-tree',action='append',default=[])
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    argv=args.command[1:] if args.command[:1]==['--'] else args.command
    if not argv: parser.error('A command is required.')
    sources=source_paths()
    inputs=[ROOT/p for p in (args.input or ['verification/fixtures/core-fixtures.json'])]
    for path in sources+inputs:
        path.resolve().relative_to(ROOT.resolve())
        if path.name.startswith('.env'): raise ValueError('Credentials cannot be evidence.')
    before={p.relative_to(ROOT).as_posix():sha(p) for p in sources+inputs}
    locks=[dict(path=p,sha256=before[p]) for p in ['requirements.lock','frontend/package-lock.json'] if p in before]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_id=stamp+'-'+''.join(c if c.isalnum() or c in '-_' else '-' for c in args.label)
    folder=ROOT/'verification'/'runs'/run_id;folder.mkdir(parents=True)
    started=datetime.now(timezone.utc).isoformat()
    environment=os.environ.copy();environment['PA_EVIDENCE_RUN_DIR']=str(folder)
    process=subprocess.run(argv,cwd=ROOT,capture_output=True,env=environment)
    finished=datetime.now(timezone.utc).isoformat()
    private=(ROOT/'data/private-evidence/commands'/run_id).resolve()
    if not private.is_relative_to(ROOT.resolve()/'data/private-evidence'):raise ValueError('Private diagnostics escaped the workspace.')
    private.mkdir(parents=True)
    (private/'stdout.log').write_bytes(process.stdout);(private/'stderr.log').write_bytes(process.stderr)
    (private/'command.json').write_text(json.dumps(dict(argv=argv,cwd=str(ROOT),exit_code=process.returncode),indent=2),encoding='utf-8')
    out=process.stdout.decode('utf-8',errors='replace').replace('\r\n','\n').replace('\r','\n')
    err=process.stderr.decode('utf-8',errors='replace').replace('\r\n','\n').replace('\r','\n')
    scrubber=Sanitizer([(str(ROOT),'<workspace>'),(str(Path.home()),'<user-home>')]);scrubber.learn(out);scrubber.learn(err)
    outputs=[]
    for name,content in [('stdout.log',out),('stderr.log',err)]:
        path=folder/name;path.write_text(redact(content,scrubber=scrubber),encoding='utf-8');outputs.append(path)
    changed,added=inventory_changes(before,[p.relative_to(ROOT).as_posix() for p in sources])
    requested=[ROOT/p for p in args.artifact]
    requested+=sorted(p for p in folder.rglob('*') if p.is_file() and p not in outputs)
    for item in args.artifact_tree:
        tree=ROOT/item
        tree.resolve().relative_to(ROOT.resolve())
        if tree.is_dir(): requested+=sorted(p for p in tree.rglob('*') if p.is_file())
        else: requested.append(tree)
    missing=[p.relative_to(ROOT).as_posix() for p in requested if not p.exists()]
    artifacts=outputs[:]
    blocked=[]
    for path in dict.fromkeys(p for p in requested if p.is_file()):
        relative=path.resolve().relative_to(ROOT.resolve())
        if path.name.startswith('.env'): raise ValueError('Credentials cannot be evidence.')
        if not review_artifact_allowed(path):
            blocked.append(relative.as_posix());missing.append(relative.as_posix()+' (excluded by evidence privacy policy)')
            if path.is_relative_to(folder):
                quarantine=(ROOT/'data/private-evidence/blocked'/run_id/path.relative_to(folder)).resolve()
                if not quarantine.is_relative_to((ROOT/'data/private-evidence/blocked').resolve()) or quarantine.exists():raise ValueError('Unsafe private quarantine destination.')
                quarantine.parent.mkdir(parents=True,exist_ok=True);path.replace(quarantine)
            continue
        if path.is_relative_to(folder):
            artifacts.append(path);continue
        destination=folder/'artifacts'/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination)
        artifacts.append(destination)
    manifest=[]
    for path in artifacts:
        path.resolve().relative_to(ROOT.resolve())
        if path.name.startswith('.env'): raise ValueError('Credentials cannot be evidence.')
        manifest.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size,
                             purpose='Actual command log' if path in outputs else 'Check output artifact'))
    receipt=dict(version=1,receipt_id=run_id,kind='implementation',started_at_utc=started,finished_at_utc=finished,
                 timezone='America/Los_Angeles',subject=dict(plan_sha256=before['PLAN.md'],verification_plan_sha256=before['VERIFICATION_PLAN.md'],
                    catalog_sha256=before['verification/catalog.json'],source_files={p.relative_to(ROOT).as_posix():before[p.relative_to(ROOT).as_posix()] for p in sources},
                    rulebook=dict(path='RULEBOOK.md',sha256=before['RULEBOOK.md']),dependency_locks=locks,
                    input_manifests=[dict(path=p.relative_to(ROOT).as_posix(),sha256=before[p.relative_to(ROOT).as_posix()]) for p in inputs]),
                 environment=dict(os=platform.platform(),python=platform.python_version(),runner='verification/record_check.py'),
                 command=dict(argv=[redact(s,scrubber=scrubber) for s in argv],cwd='.',exit_code=process.returncode,seed=None),
                 artifacts=manifest,results=[],notes=['Actual component/integration execution; not full acceptance certification.']+['Missing requested artifact: '+p for p in missing]+['Source changed during command; not a coherent verification baseline: '+p for p in changed]+['Source changed during command; added source not in the initial baseline: '+p for p in added])
    schema=json.loads((ROOT/'verification/receipt.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(receipt)
    receipt_dir=ROOT/'verification/receipts';receipt_dir.mkdir(exist_ok=True)
    destination=receipt_dir/(run_id+'.json');destination.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(redact(out[-5000:],scrubber=scrubber))
    if err: print(redact(err[-2000:],scrubber=scrubber),file=sys.stderr)
    print(json.dumps({'receipt':destination.relative_to(ROOT).as_posix(),'exit_code':process.returncode,
                      'coherent_subject':not changed and not added,'requested_artifacts_present':not missing}))
    return process.returncode or (2 if changed or added or missing else 0)

if __name__=='__main__': raise SystemExit(main())
