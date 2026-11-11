"""Measure Python3.13 guard-arc reporting; no application acceptance claim."""
from pathlib import Path
import ast,json,os,subprocess,sys
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
source=root/'verification/fixtures/coverage-context-guard-probe.py'
private=root/'data/private-evidence/guard-probe'/out.name
private.mkdir(parents=True,exist_ok=False)
database=private/'.coverage';report=out/'actual-probe-coverage.json'
tree=ast.parse(source.read_text());functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
assert ast.dump(ast.Module(body=functions[0].body,type_ignores=[]))==ast.dump(ast.Module(body=functions[1].body,type_ignores=[]))
subprocess.run([sys.executable,'-m','coverage','run','--branch','--data-file='+str(database),str(source)],check=True)
subprocess.run([sys.executable,'-m','coverage','json','--data-file='+str(database),'-o',str(report)],check=True,capture_output=True)
value=json.loads(report.read_text());entry=next(v for k,v in value['files'].items() if k.replace('\\','/').endswith('coverage-context-guard-probe.py'))
results={name:entry['functions'][name] for name in ['compact','expanded']}
(out/'guard-format-observation.json').write_text(json.dumps(dict(ast_bodies_identical=True,both_paths_executed=True,results=results),indent=2))
print(json.dumps({k:dict(summary=v['summary'],executed_branches=v['executed_branches'],missing_branches=v['missing_branches']) for k,v in results.items()},indent=2))
