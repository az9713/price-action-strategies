"""The receipt runner must expose drift rather than certify the wrong subject."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from verification.record_check import source_paths,inventory_changes,redact

ROOT=Path(__file__).resolve().parents[1]


def minimal_workspace(root):
    (root/'verification').mkdir()
    for name in ['PLAN.md','VERIFICATION_PLAN.md','RULEBOOK.md','decisions.md','README.md',
                 'THIRD_PARTY_NOTICES.md','pyproject.toml','requirements.lock','strategy.schema.json',
                 'verification/catalog.json','verification/implementation-map.json']:
        (root/name).write_text('fixture',encoding='utf-8')
    for name in ['receipt.schema.json','record_check.py','trace_privacy.py']:
        (root/'verification'/name).write_bytes((ROOT/'verification'/name).read_bytes())
    (root/'verification/fixtures').mkdir()
    (root/'verification/fixtures/core-fixtures.json').write_text('{}')
    (root/'backend/lab').mkdir(parents=True)


def test_inventory_detects_added_removed_and_changed_source(tmp_path):
    minimal_workspace(tmp_path)
    existing=tmp_path/'backend/lab/existing.py';existing.write_text('before')
    paths=source_paths(tmp_path)
    before={p.relative_to(tmp_path).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    existing.write_text('after')
    (tmp_path/'README.md').unlink()
    (tmp_path/'backend/lab/added.py').write_text('new source')
    (tmp_path/'.env').write_text('NOT_A_REAL_SECRET=fixture')
    changed,added=inventory_changes(before,before,tmp_path)
    assert set(changed)=={'README.md','backend/lab/existing.py'}
    assert added==['backend/lab/added.py']
    assert '.env' not in {p.name for p in source_paths(tmp_path)}


def test_json_escaped_windows_workspace_path_is_redacted():
    root=Path(r'C:\Users\fixture\workspace')
    encoded=json.dumps({'cwd':str(root),'path':str(root).replace('\\','/')+'/output.json'})
    result=json.loads(redact(encoded,root))
    assert result=={'cwd':'<workspace>','path':'<workspace>/output.json'}


def test_actual_runner_retains_successful_command_but_fails_coherence_for_new_source(tmp_path):
    minimal_workspace(tmp_path)
    command=[sys.executable,'verification/record_check.py','--label','added-source-contract','--',sys.executable,
        '-c',"from pathlib import Path; Path('backend/lab/added.py').write_text('new source'); print('actual command completed')"]
    result=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==2,result.stdout+result.stderr
    files=list((tmp_path/'verification/receipts').glob('*.json'));assert len(files)==1
    receipt=json.loads(files[0].read_text())
    assert receipt['command']['exit_code']==0 and receipt['results']==[]
    assert any('added source' in note and 'backend/lab/added.py' in note for note in receipt['notes'])
    assert any('actual command completed' in (tmp_path/a['path']).read_text() for a in receipt['artifacts'] if a['path'].endswith('stdout.log'))

def test_logs_remove_credentials_and_propagated_values_without_touching_numbers():
    from verification.trace_privacy import REDACTED
    value="{'X-Lab-Token': 'PA_FAKE_RECORDER_LONG_SENTINEL', 'number': 1}\nrepeat PA_FAKE_RECORDER_LONG_SENTINEL"
    result=redact(value)
    assert 'PA_FAKE_RECORDER_LONG_SENTINEL' not in result and "'number': 1" in result and REDACTED in result

def test_private_artifacts_are_refused_and_new_raw_traces_quarantined(tmp_path):
    minimal_workspace(tmp_path)
    private=tmp_path/'data/private-evidence';private.mkdir(parents=True);(private/'keep.txt').write_text('private fixture',encoding='utf-8')
    code="from pathlib import Path; import os,json,zipfile; p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'trace.zip'; z=zipfile.ZipFile(p,'w'); z.writestr('test.trace',json.dumps({'type':'context-options','version':10})); z.close()"
    command=[sys.executable,'verification/record_check.py','--label','private-contract','--artifact','data/private-evidence/keep.txt','--',sys.executable,'-c',code]
    result=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True,encoding='utf-8');assert result.returncode==2
    receipt=json.loads(next((tmp_path/'verification/receipts').glob('*.json')).read_text(encoding='utf-8'))
    assert receipt['command']['exit_code']==0 and sum('excluded by evidence privacy policy' in n for n in receipt['notes'])==2
    assert all('private-evidence' not in a['path'] and not a['path'].endswith('trace.zip') for a in receipt['artifacts'])
    assert len(list((private/'blocked').rglob('trace.zip')))==1 and (private/'keep.txt').exists()

def test_original_child_diagnostics_remain_private_and_public_logs_are_redacted(tmp_path):
    minimal_workspace(tmp_path)
    secret='PA_FAKE_RECORDER_DIAGNOSTIC_SENTINEL'
    code="import sys; print('X-Lab-Token: "+secret+"'); print('repeat "+secret+"',file=sys.stderr); raise SystemExit(7)"
    command=[sys.executable,'verification/record_check.py','--label','redacted-failure','--',sys.executable,'-c',code]
    result=subprocess.run(command,cwd=tmp_path,capture_output=True,text=True,encoding='utf-8');assert result.returncode==7
    receipt=json.loads(next((tmp_path/'verification/receipts').glob('*.json')).read_text(encoding='utf-8'))
    assert receipt['command']['exit_code']==7 and secret not in json.dumps(receipt)
    assert secret not in result.stdout+result.stderr
    assert any(secret in p.read_text(encoding='utf-8') for p in (tmp_path/'data/private-evidence/commands').rglob('*.log'))
    for artifact in receipt['artifacts']:assert secret not in (tmp_path/artifact['path']).read_text(encoding='utf-8')
