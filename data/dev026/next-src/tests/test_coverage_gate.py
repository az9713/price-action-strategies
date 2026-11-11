"""Known threshold, drift and tampering cases for the numerical release gate."""
import copy
import hashlib
import json
import pytest
from verification.check_numerical_coverage import MODULES,evaluate


def fixture(root):
    hashes={};files={}
    for name in MODULES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic gate fixture\n')
        hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        files[name]={'summary':dict(num_statements=100,covered_lines=95,num_branches=10,covered_branches=9)}
    artifact=root/'coverage.json';artifact.write_text(json.dumps({'files':files}))
    return {'command':{'exit_code':0},'notes':[],'subject':{'source_files':hashes},
        'artifacts':[{'path':'coverage.json','bytes':artifact.stat().st_size,'sha256':hashlib.sha256(artifact.read_bytes()).hexdigest()}]},files


def replace_coverage(root,receipt,files):
    path=root/'coverage.json';path.write_text(json.dumps({'files':files}))
    receipt['artifacts'][0].update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def test_exact95_line90_branch_boundary_passes(tmp_path):
    receipt,_=fixture(tmp_path);result=evaluate(receipt,tmp_path)
    assert result['ready'] and all(r['line_percent']==95 and r['branch_percent']==90 for r in result['modules'])


@pytest.mark.parametrize('field,value',[('covered_lines',94),('covered_branches',8)])
def test_below_either_threshold_does_not_round_up_to_pass(tmp_path,field,value):
    receipt,files=fixture(tmp_path);files[MODULES[-1]]['summary'][field]=value;replace_coverage(tmp_path,receipt,files)
    assert not evaluate(receipt,tmp_path)['ready']


def test_source_drift_prevents_a_green_coverage_claim(tmp_path):
    receipt,_=fixture(tmp_path);(tmp_path/MODULES[0]).write_text('changed code\n')
    result=evaluate(receipt,tmp_path)
    assert not result['ready'] and not result['modules'][0]['source_current']


def test_changed_artifact_or_failing_command_is_rejected(tmp_path):
    receipt,_=fixture(tmp_path);failed=copy.deepcopy(receipt);failed['command']['exit_code']=1
    with pytest.raises(ValueError,match='failing'): evaluate(failed,tmp_path)
    (tmp_path/'coverage.json').write_text('{}')
    with pytest.raises(ValueError,match='integrity'): evaluate(receipt,tmp_path)


def test_missing_module_and_unsafe_artifact_cannot_pass(tmp_path):
    receipt,files=fixture(tmp_path);del files[MODULES[-1]];replace_coverage(tmp_path,receipt,files)
    with pytest.raises(ValueError,match='counts'): evaluate(receipt,tmp_path)
    receipt['artifacts'][0]['path']='../coverage.json'
    with pytest.raises(ValueError): evaluate(receipt,tmp_path)
