"""Preserve all seven critical mutations and add the proven accidental universe-cap regression."""
from pathlib import Path
source=Path('verification/runs/dataset-context-critical-mutations.py').read_text(encoding='utf-8')
before="mutations=[\n"
after="mutations=[\n ('restore-unintended-twenty-instrument-cap','dataset_context','len(symbols)>0','1<=len(symbols)<=20'),\n"
assert source.count(before)==1;source=source.replace(before,after)
before='or health_responds or complete_twenty'
assert source.count(before)==1;source=source.replace(before,before+' or existing_twenty_one')
exec(compile(source,'dataset-context-universe-mutants-resolved.py','exec'))
