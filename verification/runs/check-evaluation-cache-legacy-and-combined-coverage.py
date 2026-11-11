"""Validate original full-suite coverage, then append actual targeted legacy checks on identical source."""
from pathlib import Path
import coverage,hashlib,json,os,shutil,subprocess,sys,uuid
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);receipt_path=root/'verification/receipts/20261109T093337797327Z-evaluation-cache-current-full-regression-and-twenty-two-module-coverage.json';receipt=json.loads(receipt_path.read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0
for name,digest in receipt['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
artifacts=[a for a in receipt['artifacts'] if a['path'].endswith('coverage.json')];assert len(artifacts)==1;artifact=artifacts[0];original=root/artifact['path'];raw=original.read_bytes();assert hashlib.sha256(raw).hexdigest()==artifact['sha256'];base=json.loads(raw)
private=root/'data/private-evidence/coverage'/uuid.uuid4().hex;private.mkdir(parents=True);shutil.copyfile(root/'.coverage',private/'base.coverage')
check=coverage.Coverage(data_file=str(private/'base.coverage'));check.load();check.json_report(outfile=str(private/'base-rendered.json'));rendered=json.loads((private/'base-rendered.json').read_text(encoding='utf-8'))
def normalized(value):return {name.replace('\\','/'):entry for name,entry in value['files'].items()}
assert normalized(base)==normalized(rendered),'Live coverage DB does not exactly match the recorded full-suite coverage artifact'
# The raw databases stay private. The source is fixed, and pytest-cov appends
# genuinely executed lines/arcs rather than manufacturing or inferring coverage.
combined=out/'evaluation-cache-combined-coverage.json';junit=out/'legacy-supplement-junit.xml';env=os.environ.copy();env['PYTHONPATH']=str(root)+os.pathsep+str(root/'tests');env['COVERAGE_FILE']=str(root/'.coverage')
command=[sys.executable,'-m','pytest','-q','verification/runs/evaluation-cache-legacy-report-contract-tests.py','--cov=backend.lab','--cov-branch','--cov-append','--cov-report=json:'+str(combined),'--junitxml='+str(junit)]
result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
for suffix,value in [('stdout',result.stdout),('stderr',result.stderr)]:(out/('legacy-supplement-'+suffix+'.log')).write_text(value,encoding='utf-8')
print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr);assert result.returncode==0
for name,digest in receipt['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
value=dict(scope=__doc__,base_full_receipt=receipt_path.relative_to(root).as_posix(),base_full_receipt_sha256=hashlib.sha256(receipt_path.read_bytes()).hexdigest(),base_coverage_artifact=artifact,base_raw_coverage_matches_recorded_json=True,supplement_exit_code=0,source_unchanged=True,coverage_method='coverage.py/pytest-cov append of actual executed line/arc data; raw baseline backup retained privately',raw_data_publicly_exported=False)
(out/'combined-coverage-lineage.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
