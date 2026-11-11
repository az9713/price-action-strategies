"""Actual assertion-killed mutations in an authored-source-only isolated copy."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
before={p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(stage)}
copy=root/'data/dev027/qualification-mutations'/uuid.uuid4().hex
for name in before:
    src=stage/name;dst=copy/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for src in (stage/'verification/fixtures').glob('*.json'):
    dst=copy/'verification/fixtures'/src.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
module=copy/'backend/lab/research_qualification.py';original=module.read_text(encoding='utf-8')
contracts=root/'verification/runs/research-qualification-contracts.py';reference=root/'verification/runs/research-stability-reference-contracts.py'
mutations=[
 ('strict-five-percent','20*counts[-1]<TOTAL_SETS','20*counts[-1]<=TOTAL_SETS',contracts,'test_both_original_control_interpretations_require_strict_five_percent'),
 ('both-interpretations',"passed=all(r['passed'] for r in results.values())","passed=any(r['passed'] for r in results.values())",contracts,'test_both_original_control_interpretations_require_strict_five_percent'),
 ('strict-positive-profit',"observed>threshold if comparison=='>'","observed>=threshold if comparison=='>'",contracts,'test_each_source_or_explicit_adaptation_gate_removes_only_its_original_version'),
 ('complete-family-membership','members=[c for c in configurations if c.family==family]','members=[c for c in configurations if c.family==family][:1]',contracts,'test_family_is_not_replaced_by_profitable_subset_or_candidate_members'),
 ('missing-not-zero','if value is None:return None','if value is None:return (Fraction(),None)',contracts,'test_stability_uses_actual_one_coordinate_neighbors_with_losses_zeros_and_missing'),
 ('retain-neighbor-losses',"profit=_amount(value['net_profit']);sharpe=value['marked_sharpe']","profit=abs(_amount(value['net_profit']));sharpe=value['marked_sharpe']",contracts,'test_stability_uses_actual_one_coordinate_neighbors_with_losses_zeros_and_missing'),
 ('inactive-coordinate',"if key=='confirmation_window' and c.confirmation=='none':return False","if key=='confirmation_window' and c.confirmation=='none':return True",contracts,'test_stability_does_not_invent_cross_family_chart_or_inactive_neighbors'),
 ('effective-trigger-alias',"value['trigger_timeframe']=c.trigger","value['trigger_timeframe']=c.trigger_timeframe",reference,'test_effective_trigger_aliases_are_not_changed_coordinates_or_duplicate_neighbors'),
]
env=os.environ.copy();env.update(PYTHONPATH=str(copy)+os.pathsep+str(copy/'tests'),PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1')


def execute(label,path,node):
    junit=out/(label+'.xml')
    command=[sys.executable,'-B','-m','pytest','-q','-c',str(copy/'pyproject.toml'),str(path)+'::'+node,'--import-mode=importlib','--junitxml='+str(junit)]
    result=subprocess.run(command,cwd=copy,env=env,capture_output=True,text=True)
    (out/(label+'.stdout.log')).write_text(result.stdout,encoding='utf-8');(out/(label+'.stderr.log')).write_text(result.stderr,encoding='utf-8')
    suites=list(ET.parse(junit).iter('testsuite'))
    counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
    return dict(label=label,exit_code=result.returncode,counts=counts,module_sha256=hashlib.sha256(module.read_bytes()).hexdigest())


records=[]
try:
    for label,old,new,path,node in mutations:
        assert original.count(old)==1,(label,'Mutation target must be unambiguous.')
        module.write_text(original,encoding='utf-8');baseline=execute(label+'-baseline',path,node)
        assert baseline['exit_code']==0 and not any(baseline['counts'][k] for k in ['errors','failures','skipped']),baseline
        module.write_text(original.replace(old,new,1),encoding='utf-8');mutant=execute(label+'-mutant',path,node)
        assert mutant['exit_code']==1 and mutant['counts']['failures']>0 and mutant['counts']['errors']==0 and mutant['counts']['skipped']==0,mutant
        records.append(dict(name=label,baseline=baseline,mutant=mutant,actual_assertion_kill=True));print(label+' assertion-killed',flush=True)
finally:module.write_text(original,encoding='utf-8')
assert before=={p.relative_to(stage).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(stage)}
(out/'qualification-mutations.json').write_text(json.dumps(dict(scope=__doc__,mutations=records,actual_assertion_kills=len(records),
    source_root='data/dev027/research-src',source_unchanged=True,user_credentials_prices_or_database_copied=False,
    source_only_isolated_copy=copy.relative_to(root).as_posix(),final_acceptance=False),indent=2),encoding='utf-8')
