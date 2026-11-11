"""Run npm with an explicit working directory and preserve its actual exit code."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import os
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from verification.trace_privacy import sanitize_capture,PrivacyError

ROOT=Path(__file__).resolve().parent.parent
def browser_run(arguments):
    run=os.environ.get('PA_EVIDENCE_RUN_DIR')
    review=(Path(run)/'browser' if run else ROOT/'verification/runs'/('browser-local-manual-'+uuid.uuid4().hex)).resolve()
    if not review.is_relative_to((ROOT/'verification/runs').resolve()) or review.exists():raise PrivacyError('Review output needs an unused verification run directory.')
    private=(ROOT/'data/private-evidence/captures'/uuid.uuid4().hex).resolve()
    if not private.is_relative_to((ROOT/'data/private-evidence').resolve()):raise PrivacyError('Private output escaped its declared root.')
    private.mkdir(parents=True)
    env=os.environ.copy();env['PA_BROWSER_OUTPUT']=str(private);env['PA_EVIDENCE_RUN_DIR']=str(private)
    try:
        result=subprocess.run(['npm.cmd',*arguments],cwd=ROOT/'frontend',env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
    except OSError as error:
        metadata=dict(child_exit_code=None,runner_error=type(error).__name__,raw_retained_private=True)
        (private/'capture-metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
        review.mkdir(parents=True);(review/'privacy-failure.json').write_text(json.dumps(metadata),encoding='utf-8')
        print('Browser runner did not start; no child exit code or workflow pass was recorded.',file=sys.stderr);return 2
    (private/'runner-stdout.log').write_text(result.stdout,encoding='utf-8')
    (private/'runner-stderr.log').write_text(result.stderr,encoding='utf-8')
    (private/'capture-metadata.json').write_text(json.dumps(dict(child_exit_code=result.returncode,argv=['npm.cmd',*arguments],raw_retained_private=True,private_capture_id=private.name),indent=2),encoding='utf-8')
    aliases=[(str(private),str(review)),(os.path.relpath(private,ROOT/'frontend'),os.path.relpath(review,ROOT/'frontend')),
        (str(ROOT),'<workspace>'),(str(Path.home()),'<user-home>')]
    try:
        sanitize_capture(private,review,result.returncode,aliases)
    except PrivacyError as error:
        # No raw stdout/trace is emitted on a failed privacy derivation.
        # The actual child status remains explicit; wrapper failure is separate.
        review.mkdir(parents=True,exist_ok=True)
        (review/'privacy-failure.json').write_text(json.dumps(dict(child_exit_code=result.returncode,privacy_error=str(error),raw_retained_private=True,capture_id=private.name)),encoding='utf-8')
        print('Browser child exit '+str(result.returncode)+'; privacy derivation failed. Raw capture remains private; no workflow pass accepted.',file=sys.stderr)
        return 2
    print((review/'runner-stdout.log').read_text(encoding='utf-8'),end='')
    print((review/'runner-stderr.log').read_text(encoding='utf-8'),end='',file=sys.stderr)
    print(json.dumps(dict(review_output=review.relative_to(ROOT).as_posix(),child_exit_code=result.returncode,privacy_policy=1,raw_capture_id=private.name)))
    return result.returncode

def main():
    sys.stdout.reconfigure(encoding='utf-8',errors='replace')
    sys.stderr.reconfigure(encoding='utf-8',errors='replace')
    command=sys.argv[1]
    arguments={'install':['install','--ignore-scripts'],'build':['run','build'],'audit':['audit','--json'],
        'browser':['exec','--','playwright','test']}[command]
    if command=='browser':arguments+=sys.argv[2:]
    if command=='browser':return browser_run(arguments)
    result=subprocess.run(['npm.cmd',*arguments],cwd=ROOT/'frontend',env=os.environ.copy())
    if command=='build' and result.returncode==0:
        files={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'frontend'/'dist').rglob('*')) if p.is_file()}
        (ROOT/'verification'/'runs'/'frontend-build.json').write_text(json.dumps({'files':files},indent=2),encoding='utf-8')
    return result.returncode
if __name__=='__main__': raise SystemExit(main())
