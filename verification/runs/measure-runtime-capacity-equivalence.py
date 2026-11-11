"""Measured production search plus exact complete0.16/0.17 account comparison."""
from pathlib import Path
import hashlib,json,os,runpy,sys
root=Path.cwd();sys.path.insert(0,str(root));count=int(sys.argv[1]);out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
contract=json.loads((root/'verification/runs/runtime-capacity-equivalence-contract.json').read_text(encoding='utf-8'))
sys.argv=[str(root/'verification/runs/measure-capacity-real-sample.py'),str(count)]
runpy.run_path(sys.argv[0],run_name='__main__')
from backend.lab.service import Lab
from backend.lab.research import core_hash
from backend.lab.config import identity
lab=Lab(root/'data/capacity-real-instance');summary=json.loads((out/'capacity-summary.json').read_text(encoding='utf-8'))
old_id=contract['baseline_job_ids'][str(count)];old_result=lab.result(old_id);new_id=summary['measurements'][0]['job_id'];new_result=lab.result(new_id)
assert old_result['count']==new_result['count']==count and core_hash()!=contract['baseline_core_hash'];checked=[]
for old_row,new_row in zip(old_result['rows'],new_result['rows']):
 assert old_row['part']==new_row['part'] and old_row['config_id']==new_row['config_id'] and old_row['metrics']==new_row['metrics']
 old=lab.report(old_id,old_row['part']);new=lab.report(new_id,new_row['part'])
 assert old['core_hash']==contract['baseline_core_hash'] and new['core_hash']==core_hash()
 assert identity(old['numerical_contract'])==old['core_hash'] and identity(new['numerical_contract'])==new['core_hash']
 left={k:v for k,v in old.items() if k not in contract['allowed_report_differences']};right={k:v for k,v in new.items() if k not in contract['allowed_report_differences']}
 assert left==right,('Complete account changed',old_row['part'],[k for k in left if left[k]!=right.get(k)])
 checked.append(dict(part=old_row['part'],config_id=old_row['config_id'],complete_numerical_and_other_field_hash=identity(left),fields_checked=sorted(left),trades=len(left['trades']),signals=len(left['signals'])))
result=dict(scope=__doc__,baseline_job_id=old_id,current_job_id=new_id,baseline_core_hash=contract['baseline_core_hash'],current_core_hash=core_hash(),complete_accounts_equal=count,only_allowed_differences=contract['allowed_report_differences'],accounts=checked)
(out/'complete-account-equivalence.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='accounts'},indent=2))
