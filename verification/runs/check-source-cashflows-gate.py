"""Reconcile actual coverage DB bytes and current audited numerical modules."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
identifier='20261110T001935855967Z-source-cashflows-canonical-tampering-independent-components-and-production-baseline-current'
receipt=json.loads((root/'verification/receipts'/(identifier+'.json')).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def artifact(name):
    entry=next(e for e in receipt['artifacts'] if e['path'].endswith('/'+name));path=root/entry['path']
    assert path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256']
    return path
assert receipt['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
subject=json.loads(artifact('next-stage-source-subject.json').read_text())
assert subject['child_exit_code']==0 and not subject['changed_during_check'] and subject['frozen_baseline_unchanged']
suites=list(ET.parse(artifact('next-stage-junit.xml')).iter('testsuite'))
counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
assert counts==dict(tests=93,failures=0,errors=0,skipped=0)
recorded=json.loads(artifact('cashflow-and-grade-coverage.json').read_text())
database=root/'data/private-evidence/development-coverage'/identifier/'.coverage';database_sha=sha(database)
rendered=out/'cashflow-and-grade-actual-db.json'
result=subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(database),'--rcfile='+str(source/'pyproject.toml'),'-o',str(rendered)],cwd=source,capture_output=True,text=True,timeout=60)
assert result.returncode==0,result.stderr
actual=json.loads(rendered.read_text());assert actual['files']==recorded['files'] and sha(database)==database_sha
assert {n.replace('\\','/') for n in actual['files']}=={'backend/lab/source_cashflows.py','backend/lab/trade_twin_results.py'}
modules=[]
for name,value in actual['files'].items():
    name=name.replace('\\','/');assert sha(source/name)==subject['source_files'][name]
    summary=value['summary'];assert summary['excluded_lines']==0
    assert 100*summary['covered_lines']>=95*summary['num_statements']
    assert 100*summary['covered_branches']>=90*summary['num_branches']
    modules.append(dict(path=name,sha256=sha(source/name),summary=summary))
value=dict(scope=__doc__,original_receipt=identifier,actual_database_sha256=database_sha,actual_database_unchanged=True,
           coverage_json_exactly_reconciled=True,current_measured_modules=modules,cases=counts,
           minimum_statements=95,minimum_branches=90,exclusions=0,
           scope_limit='Module-specific gate: later unrelated API changes are not covered by this numerical receipt.',
           all38_global_modules_certified=False,final_product_acceptance=False)
(out/'cashflow-numerical-gate.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
