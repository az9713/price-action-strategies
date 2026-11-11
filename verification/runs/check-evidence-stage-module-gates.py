"""Actual-DB/source reconciliation for explicitly named current-stage modules.

This never promotes component gates to global/final acceptance.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path.cwd()
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
p = argparse.ArgumentParser()
p.add_argument('--source', choices=['data/dev026/evidence-src','data/dev027/research-src'], default='data/dev026/evidence-src')
p.add_argument('--receipt', required=True)
p.add_argument('--coverage', required=True)
p.add_argument('--expected-tests', type=int, required=True)
p.add_argument('--module', action='append', required=True)
args = p.parse_args()
source = root / args.source
research = args.source == 'data/dev027/research-src'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

r = json.loads((root/'verification/receipts'/(args.receipt+'.json')).read_text())
assert r['command']['exit_code'] == 0
assert not any(n.startswith(('Source changed', 'Missing requested')) for n in r['notes'])
def artifact(name):
    entries = [x for x in r['artifacts'] if x['path'].endswith('/'+name)]
    assert len(entries) == 1
    item = entries[0]
    path = root / item['path']
    assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    return path
subject = json.loads(artifact('research-stage-subject.json' if research else 'evidence-stage-subject.json').read_text())
assert subject['source_root'] == args.source
assert subject['child_exit_code'] == 0 and not subject['changed_during_check']
assert subject['earlier_financial_sources_unchanged' if research else 'frozen_financial_sources_unchanged']
suites = list(ET.parse(artifact('research-stage-junit.xml' if research else 'evidence-stage-junit.xml')).iter('testsuite'))
counts = {key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
assert counts == dict(tests=args.expected_tests, errors=0, failures=0, skipped=0)
recorded = json.loads(artifact(args.coverage).read_text())
database = root/'data/private-evidence/development-coverage'/args.receipt/'.coverage'
database_sha = sha(database)
rendered = out/'actual-database-coverage.json'
result = subprocess.run([sys.executable, '-m', 'coverage', 'json', '--data-file='+str(database),
                         '--rcfile='+str(source/'pyproject.toml'), '-o', str(rendered)],
                        cwd=source, capture_output=True, text=True, timeout=60)
assert result.returncode == 0, result.stderr
actual = json.loads(rendered.read_text())
assert actual['files'] == recorded['files'] and sha(database) == database_sha
files = {key.replace('\\','/'):value for key,value in actual['files'].items()}
assert set(args.module) <= set(files)
modules = []
for name in args.module:
    path = (source/name).resolve()
    assert path.is_relative_to(source) and sha(path) == subject['source_files'][name]
    summary = files[name]['summary']
    assert summary['excluded_lines'] == 0
    assert 100*summary['covered_lines'] >= 95*summary['num_statements'], (name,summary)
    assert 100*summary['covered_branches'] >= 90*summary['num_branches'], (name,summary)
    modules.append(dict(path=name, sha256=sha(path), summary=summary))
value = dict(scope=__doc__, source_root=args.source, original_receipt=args.receipt, actual_database_sha256=database_sha,
             actual_database_unchanged=True, coverage_json_exactly_reconciled=True,
             measured_modules=modules, original_junit=counts,
             minimum_statements=95, minimum_branches=90, exclusions=0,
             global_numerical_modules_certified=False, final_product_acceptance=False)
(out/'current-module-gates.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
