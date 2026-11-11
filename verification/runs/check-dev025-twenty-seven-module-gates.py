"""Current isolated27-module95/90 gate after raw-database/JSON reconciliation."""
from pathlib import Path
import hashlib,importlib.util,json,os,sys
root=Path.cwd();dev=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((root/sys.argv[1]).read_text(encoding='utf-8'));assert receipt['command']['exit_code']==0 and not any(n.startswith(('Source changed','Missing requested')) for n in receipt['notes'])
def artifact(name):
 a=next(a for a in receipt['artifacts'] if a['path'].endswith('/'+name));p=root/a['path'];assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256'];return json.loads(p.read_text(encoding='utf-8'))
lineage=artifact('combined-coverage-lineage.json');assert lineage['backend_sources_identical'] and lineage['input_lineage'] and all(r['raw_database_exactly_matches_original_json'] for r in lineage['input_lineage'])
subject=artifact('dev025-source-subject.json');assert subject['changed_during_check']==[] and subject['child_exit_code']==0
for name,digest in subject['source_files'].items():assert sha(dev/name)==digest,name
coverage=artifact('spread-coverage.json')
spec=importlib.util.spec_from_file_location('current_declared_numerical_modules',dev/'verification/check_numerical_coverage.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert len(module.MODULES)==27 and len(set(module.MODULES))==27
rows=[]
for name in module.MODULES:
 matches=[v for k,v in coverage['files'].items() if k.replace('\\','/').endswith(name)];assert len(matches)==1,name
 s=matches[0]['summary'];n=s['num_statements'];b=s['num_branches'];c=s['covered_lines'];cb=s['covered_branches'];assert n>0 and b>0 and 0<=c<=n and 0<=cb<=b
 statements=100*c/n;branches=100*cb/b
 rows.append(dict(path=name,source_sha256=subject['source_files'][name],statement_percent=statements,branch_percent=branches,required_statements=95,required_branches=90,ready=statements>=95 and branches>=90))
value=dict(scope=__doc__,modules=rows,ready=all(r['ready'] for r in rows),coverage_lineage=lineage,final_acceptance_certified=False)
(out/'dev025-twenty-seven-module-gates.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='coverage_lineage'},indent=2));raise SystemExit(0 if value['ready'] else 1)
