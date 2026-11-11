"""Fault injection against isolated, explicitly synthetic release evidence.

Nothing here creates or certifies product receipts in the real workspace.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from verification import check_evidence as gate


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    monkeypatch.setattr(gate, 'V', tmp_path / 'verification')
    verification = tmp_path / 'verification'
    write(verification / 'receipt.schema.json', json.loads(
        (Path(__file__).resolve().parents[1] /
         'verification/receipt.schema.json').read_text(encoding='utf-8')))
    for name in ['PLAN.md', 'VERIFICATION_PLAN.md', 'RULEBOOK.md', 'requirements.lock',
                 'backend/example.py', 'tests/example.py', 'fixtures/input.json', 'run.log']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Synthetic gate fixture only\n', encoding='utf-8')
    catalog = dict(requirements=[dict(id='REQ-1', case_ids=['CASE-1'])],
                   cases=[dict(id='CASE-1', requirement_id='REQ-1', mandatory=True)])
    write(verification / 'catalog.json', catalog)
    mapping = dict(requirements=[dict(id='REQ-1', implementation=['backend/example.py'],
                                      tests=['tests/example.py'], rulebook_sections=['Fixture'])])
    write(verification / 'implementation-map.json', mapping)
    sha = lambda name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
    subject = dict(plan_sha256=sha('PLAN.md'), verification_plan_sha256=sha('VERIFICATION_PLAN.md'),
                   catalog_sha256=sha('verification/catalog.json'),
                   source_files={name: sha(name) for name in ['backend/example.py', 'tests/example.py']},
                   rulebook=dict(path='RULEBOOK.md', sha256=sha('RULEBOOK.md')),
                   dependency_locks=[dict(path='requirements.lock', sha256=sha('requirements.lock'))],
                   input_manifests=[dict(path='fixtures/input.json', sha256=sha('fixtures/input.json'))])
    write(verification / 'release-subject.json', subject)
    receipt = dict(version=1, receipt_id='synthetic-pass', kind='verification',
                   started_at_utc='2026-11-08T00:01:00Z', finished_at_utc='2026-11-08T00:02:00Z',
                   timezone='UTC', subject=subject,
                   environment=dict(os='synthetic', python='synthetic', runner='synthetic'),
                   command=dict(argv=['synthetic'], cwd='.', exit_code=0, seed=42),
                   artifacts=[dict(path='run.log', sha256=sha('run.log'),
                                   bytes=(tmp_path / 'run.log').stat().st_size, purpose='Execution log')],
                   results=[dict(case_id='CASE-1', status='pass', expected='Synthetic expected',
                                 observed='Synthetic observed', assertions=['Synthetic assertion'],
                                 artifact_paths=['run.log'])])
    write(verification / 'receipts/pass.json', receipt)
    return tmp_path, receipt, mapping, catalog


def outcome(capsys):
    code = gate.check_release()
    return code, json.loads(capsys.readouterr().out)


def test_complete_synthetic_evidence_passes(evidence, capsys):
    code, report = outcome(capsys)
    assert code == 0 and report['ready'] and report['verified_cases'] == 1


@pytest.mark.parametrize('fault', ['subject', 'receipt', 'artifact', 'implementation', 'test'])
def test_missing_required_evidence_blocks(evidence, capsys, fault):
    root, receipt, mapping, _ = evidence
    paths = dict(subject='verification/release-subject.json', receipt='verification/receipts/pass.json',
                 artifact='run.log', implementation='backend/example.py', test='tests/example.py')
    (root / paths[fault]).unlink()
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('fault', ['source', 'plan', 'artifact', 'input', 'rulebook', 'lock'])
def test_changed_evidence_blocks(evidence, capsys, fault):
    root, _, _, _ = evidence
    name = dict(source='backend/example.py', plan='PLAN.md', artifact='run.log',
                input='fixtures/input.json', rulebook='RULEBOOK.md', lock='requirements.lock')[fault]
    (root / name).write_text('Changed after execution\n', encoding='utf-8')
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('kind', ['planning', 'implementation'])
def test_component_or_planning_receipt_cannot_certify_product(evidence, capsys, kind):
    root, receipt, _, _ = evidence
    receipt['kind'] = kind
    write(root / 'verification/receipts/pass.json', receipt)
    code, report = outcome(capsys)
    assert code == 1 and report['verified_cases'] == 0


@pytest.mark.parametrize('fault', ['failed_command', 'no_case_artifact', 'unknown_case', 'duplicate_case',
                                 'backwards_time', 'unsafe_path', 'credential_path'])
def test_invalid_receipt_cannot_certify(evidence, capsys, fault):
    root, receipt, _, _ = evidence
    if fault == 'failed_command': receipt['command']['exit_code'] = 1
    elif fault == 'no_case_artifact': receipt['results'][0]['artifact_paths'] = ['absent.log']
    elif fault == 'unknown_case': receipt['results'][0]['case_id'] = 'UNKNOWN'
    elif fault == 'duplicate_case': receipt['results'].append(copy.deepcopy(receipt['results'][0]))
    elif fault == 'backwards_time': receipt['finished_at_utc'] = '2026-11-07T00:00:00Z'
    else:
        name = '../outside.log' if fault == 'unsafe_path' else '.env'
        receipt['artifacts'][0]['path'] = name
        receipt['results'][0]['artifact_paths'] = [name]
    write(root / 'verification/receipts/pass.json', receipt)
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('status', ['fail', 'blocked', 'not_run', 'inconclusive', 'stale'])
def test_current_nonpass_needs_explicit_later_supersession(evidence, capsys, status):
    root, receipt, _, _ = evidence
    failed = copy.deepcopy(receipt)
    failed.update(receipt_id='synthetic-earlier', started_at_utc='2026-11-08T00:00:00Z',
                  finished_at_utc='2026-11-08T00:01:00Z')
    failed['results'][0]['status'] = status
    write(root / 'verification/receipts/earlier.json', failed)
    code, report = outcome(capsys)
    assert code == 1 and 'Unresolved current non-pass: CASE-1' in report['errors']
    receipt['supersedes'] = ['synthetic-earlier']
    write(root / 'verification/receipts/pass.json', receipt)
    code, report = outcome(capsys)
    assert code == 0 and report['ready']


@pytest.mark.parametrize('fault', ['omitted', 'duplicate', 'unknown'])
def test_incomplete_requirement_mapping_blocks(evidence, capsys, fault):
    root, _, mapping, _ = evidence
    if fault == 'omitted': mapping['requirements'] = []
    elif fault == 'duplicate': mapping['requirements'].append(copy.deepcopy(mapping['requirements'][0]))
    else: mapping['requirements'][0]['id'] = 'UNKNOWN'
    write(root / 'verification/implementation-map.json', mapping)
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('field', ['implementation', 'tests', 'rulebook_sections'])
def test_requirement_needs_code_tests_and_rulebook(evidence, capsys, field):
    root, _, mapping, _ = evidence
    mapping['requirements'][0][field] = []
    write(root / 'verification/implementation-map.json', mapping)
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('fault', ['empty', 'duplicate_case', 'duplicate_requirement', 'orphan'])
def test_invalid_catalog_cannot_be_frozen_into_a_pass(evidence, capsys, fault):
    root, receipt, _, catalog = evidence
    if fault == 'empty': catalog = dict(requirements=[], cases=[])
    elif fault == 'duplicate_case': catalog['cases'].append(copy.deepcopy(catalog['cases'][0]))
    elif fault == 'duplicate_requirement': catalog['requirements'].append(copy.deepcopy(catalog['requirements'][0]))
    else: catalog['cases'][0]['requirement_id'] = 'UNKNOWN'
    write(root / 'verification/catalog.json', catalog)
    # A fresh hash cannot legitimize a structurally incomplete inventory.
    receipt['subject']['catalog_sha256'] = gate.digest(root / 'verification/catalog.json')
    write(root / 'verification/release-subject.json', receipt['subject'])
    write(root / 'verification/receipts/pass.json', receipt)
    code, report = outcome(capsys)
    assert code == 1 and not report['ready']


@pytest.mark.parametrize('kind',['private_root','raw_zip','renamed_raw_zip'])
def test_private_or_raw_trace_artifact_cannot_certify_even_with_valid_hash(evidence,capsys,kind):
    from test_trace_privacy import archive
    root,receipt,_,_=evidence
    name={'private_root':'data/private-evidence/fixture.log','raw_zip':'review/raw.zip','renamed_raw_zip':'review/raw.bin'}[kind]
    target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
    if kind=='private_root':target.write_text('Authored private fixture, no real credentials.',encoding='utf-8')
    else:archive(target)
    receipt['artifacts'].append(dict(path=name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,purpose='Synthetic invalid artifact'))
    receipt['results'][0]['artifact_paths']=[name];write(root/'verification/receipts/pass.json',receipt)
    code,report=outcome(capsys);assert code==1 and not report['ready'] and report['verified_cases']==0


def test_independently_audited_derived_trace_can_be_a_scoped_artifact(evidence,capsys):
    from test_trace_privacy import archive
    from verification.trace_privacy import sanitize_archive
    root,receipt,_,_=evidence;raw=root/'data/private-evidence/raw.zip';raw.parent.mkdir(parents=True);archive(raw)
    target=root/'review/derived.zip';target.parent.mkdir();sanitize_archive(raw,target)
    name=target.relative_to(root).as_posix()
    receipt['artifacts'].append(dict(path=name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),bytes=target.stat().st_size,purpose='Synthetic sanitized trace fixture'))
    receipt['results'][0]['artifact_paths']=[name];write(root/'verification/receipts/pass.json',receipt)
    code,report=outcome(capsys);assert code==0 and report['ready']
