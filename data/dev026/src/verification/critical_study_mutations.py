"""Five isolated mutations of frozen-study selection, dates and prespecified gates.

This supplements the release mutation inventory; it does not certify every
execution/accounting/security domain or any strategy's financial performance.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);output.mkdir(parents=True,exist_ok=True)
    sources=sorted((ROOT/'backend').rglob('*.py'))+sorted((ROOT/'verification/fixtures').glob('*.json'))
    sources += [ROOT/name for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py',
        'tests/test_reference_execution.py','tests/test_portfolio_studies.py','tests/test_study_gates.py','verification/reference_execution.py','verification/strategy_fixtures.py']]
    baseline={p.relative_to(ROOT).as_posix():sha(p) for p in sources};records=[]
    mutations=[
        ('registration-binding-disabled','backend/lab/research.py',"if event is None or json.loads(event['details']).get('spec_hash')!=study_input_hash(study['spec']):",'if False:'),
        ('portfolio-member-dropped','backend/lab/worker.py','configs=[Strategy(**c) for c in configuration]','configs=[Strategy(**c) for c in configuration[:1]]'),
        ('discovery-reused-as-final','backend/lab/worker.py',"window=payload['holdout'] if final else", "window=payload['discovery'] if final else"),
        ('zero-loss-profit-gate-disabled','backend/lab/research.py',"m['net_profit']>0",'True'),
        ('either-window-instead-of-both','backend/lab/research.py','return all(type(', 'return any(type('),
    ]
    with tempfile.TemporaryDirectory(prefix='priceaction-study-mutation-') as temporary:
        working=Path(temporary).resolve();parent=Path(tempfile.gettempdir()).resolve()
        assert working.is_relative_to(parent) and working.name.startswith('priceaction-study-mutation-') and working!=parent
        for p in sources:
            target=working/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        environment=os.environ.copy();environment.update(PYTHONPATH=str(working),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        environment.pop('PA_EVIDENCE_RUN_DIR',None)
        state=working/'pytest-state';assert state.resolve().is_relative_to(working)
        def run(name):
            xml=output/(name+'-junit.xml')
            result=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_portfolio_studies.py','tests/test_study_gates.py','--basetemp',str(state),'--junitxml',str(xml)],
                cwd=working,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace')
            for suffix,text in [('stdout',result.stdout),('stderr',result.stderr)]:
                (output/(name+'-'+suffix+'.log')).write_text(text.replace(str(working),'<isolated-study-mutant>'),encoding='utf-8')
            suites=list(ET.parse(xml).iter('testsuite'))
            return dict(exit_code=result.returncode,**{field:sum(int(s.attrib.get(field,0)) for s in suites) for field in ['tests','failures','errors','skipped']})
        first=run('baseline');assert first['exit_code']==0 and first['tests']==44 and first['failures']==first['errors']==first['skipped']==0,first
        for name,file,before,after in mutations:
            target=working/file;original=(ROOT/file).read_text(encoding='utf-8');assert original.count(before)==1
            changed=original.replace(before,after);target.write_text(changed,encoding='utf-8')
            (output/(name+'-source.py')).write_text(changed,encoding='utf-8')
            result=run(name)
            assert result['exit_code']==1 and result['tests']==44 and result['failures']>0 and result['errors']==result['skipped']==0,(name,result)
            records.append(dict(name=name,path=file,baseline_sha256=baseline[file],mutant_sha256=sha(target),
                replacement=dict(before=before,after=after),result=result,status='killed_by_assertions'))
            target.write_bytes((ROOT/file).read_bytes())
    assert all(sha(ROOT/name)==digest for name,digest in baseline.items())
    (output/'study-mutation-results.json').write_text(json.dumps(dict(scope=__doc__,baseline=first,source_manifest=baseline,mutations=records,original_source_unchanged=True),indent=2),encoding='utf-8')
    print(json.dumps(dict(baseline_tests=first['tests'],mutants=len(records),killed=len(records),original_source_unchanged=True)))


if __name__=='__main__':main()
