"""Actual original-publication/view assertion mutations on real completed evidence.

Only source is copied into mutants. Existing authored synthetic financial stores
are cloned by the saved-evidence fixture, without finance or credential reads.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path.cwd()
stage = root/'data/dev026/evidence-src'
out = Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root))
from verification.record_check import source_paths

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

subject = {p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
home = root/'data/dev026/vmut'/out.name.split('-')[0]
home.mkdir(parents=True,exist_ok=False)
module = 'backend/lab/trade_twin_views.py'
mutations = [
    ('root-adjacency', 'or self.manifest_event_id+1!=self.result_event_id', 'or False'),
    ('part-before-result', "if self.manifest_event_id is not None and event['id']>=self.manifest_event_id:", 'if False:'),
    ('preparation-before-result', 'or self.manifest_event_id is not None and self.preparation_event_id>=self.manifest_event_id', 'or False'),
    ('computed-original-digest', "computed=computation_event(db,self.jid,trial,starts[0]['id'])", "computed=starts[0]['id']"),
    ('part-original-index', "if indexed is None or indexed['event_id']!=event['id'] or json.loads(indexed['details'])!=header:", 'if False:'),
    ('part-byte-identity', "if (force or part not in self.parts_used) and (path.stat().st_size>MAX_PART_BYTES or file_hash(path)!=header['sha256']):", 'if False:'),
    ('book-original-index', "if len(bindings)!=header['book_count'] or identity(bindings)!=header['book_bindings_sha256'] or dict(book_key=member['book_key'],book_offset=record['book_offset'],book_sha256=member['book_sha256']) not in bindings:", 'if False:'),
    ('chunk-original-records', "chunk=verify_chunk(evidence,kind,index,_unpack(record['value'],MAX_CHUNK_BYTES))", "chunk=_unpack(record['value'],MAX_CHUNK_BYTES)"),
]
results = []
faults = {
    'root-adjacency':['publication_order','manifest_order'],
    'part-before-result':['part_order'],
    'preparation-before-result':['prep_order'],
    'computed-original-digest':['missing_computation','computation_order','derived_and_trial'],
    'part-original-index':['part_index'],
    'part-byte-identity':['original_part'],
    'book-original-index':['book_index'],
    'chunk-original-records':['derived_chunk'],
}
baseline_golden = None
for number, (name, needle, replacement) in enumerate([('baseline',None,None),*mutations]):
    folder = home/name
    folder.mkdir()
    for relative in subject:
        target = folder/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(stage/relative,target)
    changed = None
    if needle:
        path = folder/module
        text = path.read_text(encoding='utf-8')
        assert text.count(needle) == 1, (name,text.count(needle))
        path.write_text(text.replace(needle,replacement),encoding='utf-8')
        ast.parse(path.read_text(encoding='utf-8'))
        changed = dict(path=module,original_sha256=subject[module],mutant_sha256=sha(path),needle=needle,replacement=replacement)
    case_out = out/(out.name.split('-')[0]+'_'+str(number))
    case_out.mkdir()
    env = os.environ.copy()
    env.update(PYTHONPATH=str(folder)+os.pathsep+str(folder/'tests'),PYTHONNOUSERSITE='1',
               PA_EVIDENCE_SUBJECT=str(folder), PA_EVIDENCE_RUN_DIR=str(case_out))
    if baseline_golden is not None:
        env['PA_EVIDENCE_SAVED_GOLDEN'] = str(baseline_golden)
    junit = case_out/'junit.xml'
    test = root/'verification/runs/twin-saved-evidence-positive.py'
    selected = [str(test)+'::test_actual_members_and_every_array_match_complete_original_books']
    if name == 'baseline':
        selected.append(str(test)+'::test_rehashed_derived_views_and_damaged_originals_are_refused')
    else:
        selected += [str(test)+'::test_rehashed_derived_views_and_damaged_originals_are_refused['+fault+']' for fault in faults[name]]
    result = subprocess.run([sys.executable,'-m','pytest','-q','-c',str(folder/'pyproject.toml'),
                             *selected,'--import-mode=importlib','--junitxml='+str(junit)],
                            cwd=folder,env=env,capture_output=True,text=True,timeout=300)
    (case_out/'stdout.txt').write_text(result.stdout,encoding='utf-8')
    (case_out/'stderr.txt').write_text(result.stderr,encoding='utf-8')
    suites = list(ET.parse(junit).iter('testsuite'))
    counts = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    assert counts['tests'] == (19 if name == 'baseline' else len(selected))
    if name == 'baseline':
        assert result.returncode == 0 and counts['errors'] == counts['failures'] == counts['skipped'] == 0, (counts,result.stdout[-2000:])
        baseline_golden = root/'data/dev026/view-checks'/case_out.name.split('-')[0]/'golden'
        assert baseline_golden.is_dir()
    else:
        assert result.returncode == 1 and counts['failures'] > 0 and counts['errors'] == counts['skipped'] == 0, (name,counts,result.stdout[-2000:])
        failures = [f.text or '' for f in ET.parse(junit).iter('failure')]
        assert any('AssertionError' in text or 'DID NOT RAISE' in text for text in failures), (name,'No assertion kill')
    row = dict(name=name,exit_code=result.returncode,counts=counts,mutation=changed,assertion_killed=name!='baseline')
    results.append(row)
    (out/'mutation-progress.json').write_text(json.dumps(dict(results=results,all_assertion_killed=False,complete=False),indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)
assert subject == {p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
(out/'saved-evidence-mutations.json').write_text(json.dumps(dict(source_files=subject,current_source_unchanged=True,
    results=results,actual_mutations=8,all_assertion_killed=True,errors_counted_as_kills=False,
    financial_recomputations=0,final_product_acceptance=False),indent=2),encoding='utf-8')
