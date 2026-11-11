"""Actual isolated source mutations of six declared signal/input contracts.

This checks the supplied selector/filter acceptance tests, not every detector,
execution/accounting invariant or the complete release mutation requirement.
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
SCOPE=['tests/test_confirmation_filters.py','tests/test_data_service_boundaries.py']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR']);folder.mkdir(parents=True,exist_ok=True)
    sources=sorted((ROOT/'backend').rglob('*.py'))+sorted((ROOT/'verification/fixtures').glob('*.json'))
    sources += [ROOT/name for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py','tests/test_reference_execution.py',*SCOPE,
        'verification/strategy_fixtures.py','verification/reference_execution.py']]
    records=[]
    with tempfile.TemporaryDirectory(prefix='priceaction-mutation-') as temporary:
        working=Path(temporary).resolve();parent=Path(tempfile.gettempdir()).resolve()
        # Verify the absolute cleanup/test-output targets before any recursive
        # TemporaryDirectory or pytest basetemp cleanup on Windows.
        assert working.is_relative_to(parent) and working.name.startswith('priceaction-mutation-') and working!=parent
        baseline={}
        for source in sources:
            name=source.relative_to(ROOT);target=working/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target);baseline[name.as_posix()]=sha(source)
        environment=os.environ.copy();environment.update(PYTHONPATH=str(working),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
        environment.pop('PA_EVIDENCE_RUN_DIR',None)
        state=working/'pytest-state';assert state.resolve().is_relative_to(working)
        def run(name,expression):
            xml=folder/(name+'-junit.xml')
            result=subprocess.run([sys.executable,'-m','pytest','-q',*SCOPE,'-k',expression,'--basetemp',str(state),'--junitxml',str(xml)],cwd=working,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace')
            for suffix,text in [('stdout',result.stdout),('stderr',result.stderr)]:
                (folder/(name+'-'+suffix+'.log')).write_text(text.replace(str(working),'<isolated-mutant>'),encoding='utf-8')
            tree=ET.parse(xml);suites=list(tree.iter('testsuite'))
            return dict(exit_code=result.returncode,tests=sum(int(s.attrib.get('tests',0)) for s in suites),failures=sum(int(s.attrib.get('failures',0)) for s in suites),errors=sum(int(s.attrib.get('errors',0)) for s in suites),skipped=sum(int(s.attrib.get('skipped',0)) for s in suites))
        expressions=['overnight','every_waiting_window','all_modes_have_authored or either_accepts_rejection_without_directional_engulfing','trend_filter','run_filter','unsupported_control_news']
        first=run('baseline',' or '.join(expressions));assert first['exit_code']==0 and first['tests']>100 and not any(first[k] for k in ['failures','errors','skipped']),first
        mutations=[
            ('setup-day-regression','backend/lab/signals.py','day=local.date().isoformat()','day=row.session',1,expressions[0]),
            ('short-waiting-window','backend/lab/signals.py','range(start,min(start+cfg.confirmation_window,len(trigger)))','range(start,min(start+cfg.confirmation_window-1,len(trigger)))',1,expressions[1]),
            ('strict-half-wick','backend/lab/signals.py','>=.5','>.5',2,expressions[2]),
            ('future-trend-leak','backend/lab/signals.py','filter_chart.available_at<=when','filter_chart.available_at<=when+pd.Timedelta(days=1)',1,expressions[3]),
            ('reject-equal-run','backend/lab/signals.py','side*(chosen.close-known.iloc[-offset].close)>0','side*(chosen.close-known.iloc[-offset].close)>=0',1,expressions[4])]
        for name,file,before,after,count,expression in mutations:
            target=working/file;original=(ROOT/file).read_text(encoding='utf-8');assert original.count(before)==count
            changed=original.replace(before,after);target.write_text(changed,encoding='utf-8')
            (folder/(name+'-source.py')).write_text(changed,encoding='utf-8')
            outcome=run(name,expression)
            assert outcome['exit_code']==1 and outcome['failures']>0 and outcome['errors']==0 and outcome['skipped']==0,(name,outcome)
            records.append(dict(name=name,path=file,baseline_sha256=baseline[file],mutant_sha256=sha(target),replacement=dict(before=before,after=after,occurrences=count),result=outcome,status='killed_by_assertions'))
            target.write_bytes((ROOT/file).read_bytes())
        file='backend/lab/service.py';target=working/file;original=(ROOT/file).read_text(encoding='utf-8')
        begin=original.index('    def control_context(');finish=original.index('        signals=generate_signals',begin)
        current=original[begin:finish]
        header="    def control_context(self,payload,cancel=None):\n"
        loader="        manifest,regular,actions,warmup=self._evaluation_input(payload['dataset_id'],payload['start'],payload['end'],\n            expected_manifest=payload.get('dataset_manifest_hash'))\n"
        assert current.startswith(header) and current.endswith(loader)
        validation=current[len(header):-len(loader)]
        changed=original[:begin]+header+loader+validation+original[finish:];target.write_text(changed,encoding='utf-8')
        (folder/'late-control-validation-source.py').write_text(changed,encoding='utf-8')
        outcome=run('late-control-validation',expressions[5]);assert outcome['exit_code']==1 and outcome['failures']==2 and outcome['errors']==outcome['skipped']==0,outcome
        records.append(dict(name='late-control-validation',path=file,baseline_sha256=baseline[file],mutant_sha256=sha(target),result=outcome,status='killed_by_assertions'))
        # Original working tree is never mutated. Temporary code is discarded
        # only inside the verified named temporary root above.
    output=dict(status='pass',baseline=first,source_manifest=baseline,mutations=records,
        scope=__doc__.strip())
    (folder/'mutation-results.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(dict(baseline_tests=first['tests'],mutants=len(records),killed=sum(r['status']=='killed_by_assertions' for r in records),original_source_unchanged=True)))

if __name__=='__main__':main()
