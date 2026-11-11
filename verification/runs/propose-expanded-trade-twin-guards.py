"""Propose only simple-suite line expansion, proving complete AST equivalence.

Print an apply_patch patch; do not edit the measured source while tests run.
"""
from pathlib import Path
import ast
import difflib
import hashlib
import json

root=Path.cwd();stage=root/'data/dev026/evidence-src'
dest=root/'data/dev026/expanded-guard-proposal';dest.mkdir(parents=True,exist_ok=True)
subjects=['trade_twin_views.py','trade_twin_parts.py','trade_twin_worker.py']
patch=['*** Begin Patch'];records=[]
for name in subjects:
    path=stage/'backend/lab'/name
    original=path.read_text(encoding='utf-8');tree=ast.parse(original)
    prior=dest/'original'/name;prior.parent.mkdir(exist_ok=True);prior.write_bytes(path.read_bytes())
    lines=original.splitlines(keepends=True);edits={}
    for node in ast.walk(tree):
        if not isinstance(node,ast.If) or not node.body:
            continue
        statement=node.body[0];number=statement.lineno-1
        # A true simple suite starts on its header's final colon line. Only
        # whitespace is inserted; semicolon suites and comments stay intact.
        line=lines[number];encoded=line.encode('utf-8')
        prefix=encoded[:statement.col_offset].decode('utf-8')
        tail=encoded[statement.col_offset:].decode('utf-8')
        if not prefix.rstrip().endswith(':') or number in edits:
            continue
        indent=' '*(node.col_offset+4)
        edits[number]=prefix.rstrip()+'\n'+indent+tail
    for number,replacement in edits.items():lines[number]=replacement
    proposed=''.join(lines)
    assert ast.dump(tree)==ast.dump(ast.parse(proposed)),name
    (dest/name).write_text(proposed,encoding='utf-8')
    digest=lambda text:hashlib.sha256(text.encode()).hexdigest()
    records.append(dict(path=path.relative_to(root).as_posix(),expanded_simple_suites=len(edits),
                        original_file_bytes_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        original_utf8_sha256=digest(original),proposed_utf8_sha256=digest(proposed),
                        entire_ast_identical=True))
    if proposed!=original:
        patch.append('*** Update File: '+path.as_posix())
        diff=list(difflib.unified_diff(original.splitlines(),proposed.splitlines(),n=3))
        patch.extend('@@' if line.startswith('@@') else line for line in diff[2:])
patch.append('*** End Patch')
(dest/'ast-equivalence.json').write_text(json.dumps(dict(scope=__doc__,records=records,thresholds_unchanged=True,exclusions_added=0),indent=2),encoding='utf-8')
print('\n'.join(patch))
