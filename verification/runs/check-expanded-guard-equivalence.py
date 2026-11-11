"""Verify installed staged guard expansion against original bytes and complete ASTs."""
from pathlib import Path
import ast,hashlib,json,os
root=Path.cwd();proposal=root/'data/dev026/expanded-guard-proposal'
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
value=json.loads((proposal/'ast-equivalence.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for row in value['records']:
    current=root/row['path'];prior=proposal/'original'/current.name;proposed=proposal/current.name
    assert sha(prior)==row['original_file_bytes_sha256']
    assert current.read_text(encoding='utf-8')==proposed.read_text(encoding='utf-8')
    assert ast.dump(ast.parse(prior.read_text(encoding='utf-8')))==ast.dump(ast.parse(current.read_text(encoding='utf-8')))
    row['current_file_bytes_sha256']=sha(current)
    row['actual_current_ast_identical_to_original']=True
assert value['exclusions_added']==0 and value['thresholds_unchanged']
(out/'verified-guard-expansion.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
