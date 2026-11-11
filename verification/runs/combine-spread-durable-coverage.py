"""Union actual successful coverage databases after independently matching each saved JSON."""
from pathlib import Path
import coverage,hashlib,json,os,shutil,sys
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);private=root/'data/private-evidence/spread-combined-coverage'/out.name;private.mkdir(parents=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def normalized(value):return {name.replace('\\','/'):entry for name,entry in value['files'].items()}
lineage=[];combined=coverage.CoverageData(basename=str(private/'.coverage'));backend=None
os.chdir(dev)
for arg in sys.argv[1:]:
 p=root/arg;r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==0
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 a=next(a for a in r['artifacts'] if a['path'].endswith('/spread-coverage.json'));original=root/a['path'];assert sha(original)==a['sha256']
 subject_artifact=next(a for a in r['artifacts'] if a['path'].endswith('/dev025-source-subject.json'));sp=root/subject_artifact['path'];assert sha(sp)==subject_artifact['sha256']
 subject=json.loads(sp.read_text(encoding='utf-8'));assert subject['changed_during_check']==[] and subject['child_exit_code']==0
 current={name:digest for name,digest in subject['source_files'].items() if name.startswith('backend/')}
 for name,digest in current.items():assert sha(dev/name)==digest
 if backend is None:backend=current
 else:assert backend==current
 raw=root/'data/private-evidence/development-coverage'/r['receipt_id']/'.coverage';assert raw.is_file()
 saved=private/(r['receipt_id']+'.coverage');shutil.copyfile(raw,saved)
 check=coverage.Coverage(data_file=str(saved));check.load();rendered=private/(r['receipt_id']+'.json');check.json_report(outfile=str(rendered))
 assert normalized(json.loads(original.read_text(encoding='utf-8')))==normalized(json.loads(rendered.read_text(encoding='utf-8')))
 combined.update(check.get_data());lineage.append(dict(receipt=arg,receipt_sha256=sha(p),coverage_artifact=a,raw_data_sha256=sha(raw),raw_database_exactly_matches_original_json=True))
combined.write();final=coverage.Coverage(data_file=str(private/'.coverage'));final.load();final.json_report(outfile=str(out/'spread-coverage.json'))
shutil.copyfile(sp,out/'dev025-source-subject.json')
value=dict(scope=__doc__,input_lineage=lineage,backend_sources_identical=True,method='coverage.py union of actual recorded executed lines/arcs; no inferred hits',raw_databases_exported=False,final_acceptance_certified=False)
(out/'combined-coverage-lineage.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
