"""The browser child writes privately even on failure or sanitizer errors."""
from pathlib import Path
from types import SimpleNamespace
import json
import pytest
from verification import frontend_check
from test_trace_privacy import archive,SECRETS,read


def test_main_forwards_playwright_options_after_npm_argument_separator(monkeypatch):
    import io
    class Output(io.StringIO):
        def reconfigure(self,**kwargs):pass
    monkeypatch.setattr(frontend_check.sys,'stdout',Output());monkeypatch.setattr(frontend_check.sys,'stderr',Output())
    monkeypatch.setattr(frontend_check.sys,'argv',['frontend_check.py','browser','--project=desktop1280','--config=custom.config.ts'])
    observed=[]
    monkeypatch.setattr(frontend_check,'browser_run',lambda arguments:(observed.append(arguments) or 7))
    assert frontend_check.main()==7
    assert observed==[['exec','--','playwright','test','--project=desktop1280','--config=custom.config.ts']]

@pytest.mark.parametrize('code',[0,1])
def test_child_exit_is_preserved_and_only_derived_outputs_are_published(tmp_path,monkeypatch,capsys,code):
    run=tmp_path/'verification/runs/test-run';run.mkdir(parents=True)
    monkeypatch.setattr(frontend_check,'ROOT',tmp_path);monkeypatch.setenv('PA_EVIDENCE_RUN_DIR',str(run))
    def execute(argv,cwd,env,**kwargs):
        output=Path(env['PA_BROWSER_OUTPUT']);assert output.is_relative_to(tmp_path/'data/private-evidence') and env['PA_EVIDENCE_RUN_DIR']==str(output)
        archive(output/'trace.zip');(output/'junit.xml').write_text('<testsuite tests="1" failures="'+str(code)+'"/>',encoding='utf-8')
        return SimpleNamespace(returncode=code,stdout='x-lab-token: '+SECRETS['token']+'\nchild result '+str(code)+'\n',stderr='')
    monkeypatch.setattr(frontend_check.subprocess,'run',execute)
    assert frontend_check.browser_run(['exec','playwright','test'])==code
    result=capsys.readouterr();assert SECRETS['token'] not in result.out+result.err and 'child result '+str(code) in result.out
    review=run/'browser';manifest=json.loads((review/'privacy-derivation.json').read_text(encoding='utf-8'));assert manifest['child_exit_code']==code
    assert all(v.encode() not in b'\n'.join(read(review/'trace.zip').values()) for v in SECRETS.values())
    private=list((tmp_path/'data/private-evidence/captures').iterdir());assert len(private)==1
    assert SECRETS['token'] in (private[0]/'runner-stdout.log').read_text(encoding='utf-8')

def test_sanitization_failure_does_not_echo_raw_child_diagnostics_or_claim_success(tmp_path,monkeypatch,capsys):
    run=tmp_path/'verification/runs/test-run';run.mkdir(parents=True)
    monkeypatch.setattr(frontend_check,'ROOT',tmp_path);monkeypatch.setenv('PA_EVIDENCE_RUN_DIR',str(run))
    def execute(*args,**kwargs):return SimpleNamespace(returncode=0,stdout=SECRETS['token'],stderr=SECRETS['provider_secret'])
    def fail(*args,**kwargs):raise frontend_check.PrivacyError('Authored failure')
    monkeypatch.setattr(frontend_check.subprocess,'run',execute);monkeypatch.setattr(frontend_check,'sanitize_capture',fail)
    assert frontend_check.browser_run(['exec','playwright','test'])==2
    text=capsys.readouterr();assert all(s not in text.out+text.err for s in SECRETS.values())
    metadata=json.loads((run/'browser/privacy-failure.json').read_text(encoding='utf-8'));assert metadata['child_exit_code']==0
    assert list((run/'browser').iterdir())==[run/'browser/privacy-failure.json']

def test_missing_runner_is_explicitly_not_an_executed_browser_pass(tmp_path,monkeypatch):
    run=tmp_path/'verification/runs/test-run';run.mkdir(parents=True)
    monkeypatch.setattr(frontend_check,'ROOT',tmp_path);monkeypatch.setenv('PA_EVIDENCE_RUN_DIR',str(run))
    def fail(*args,**kwargs):raise FileNotFoundError('Authored missing executable')
    monkeypatch.setattr(frontend_check.subprocess,'run',fail)
    assert frontend_check.browser_run(['exec','playwright','test'])==2
    assert json.loads((run/'browser/privacy-failure.json').read_text(encoding='utf-8'))['child_exit_code'] is None
