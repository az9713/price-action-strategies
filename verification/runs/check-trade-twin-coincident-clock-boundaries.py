"""Hand-checked preceding-close versus exact-opening cutoff chronology.

The previous minute's completed close stage precedes the next minute's opening
stage, even though their UTC timestamps are identical. This does not infer a
tick sequence within an OHLC minute or the private host engine's convention.
"""
from pathlib import Path
from decimal import Decimal
import json,os,sys
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path[:0]=[str(source),str(source/'tests')]
from test_trade_twin_execution import frame,match_for,execute
records=[]
for side in [1,-1]:
 for kind in ['stop','target']:
  for policy in ['barrier_capped_elapsed_v1','fixed_elapsed_v1']:
   data=frame();match=match_for(data,side,end=4,boundary='open')
   if kind=='stop':data.loc[3,'low' if side==1 else 'high']=100-side*2
   else:data.loc[3,'high' if side==1 else 'low']=100+side*4+side*.01
   value=100-side*10;data.loc[4,['open','high','low','close']]=[value,value+.1,value-.1,value]
   result=execute(data,match,policy=policy)
   expected=Decimal('-100') if policy=='fixed_elapsed_v1' else Decimal('-20.10') if kind=='stop' else Decimal('40')
   assert result['trade']['net_pnl']==expected and result['trade']['exit_at']==match['cutoff_at']
   assert result['trade']['exit_reason']==('elapsed_cutoff' if policy=='fixed_elapsed_v1' else kind)
   records.append(dict(side=side,preceding_close_encounter=kind,policy=policy,expected_net=str(expected),actual=result['trade']))
value=dict(scope=__doc__,cases=len(records),all_hand_calculated_and_full_reference_parity=True,new_jobs=0,staged_source_edited=False,final_acceptance_certified=False,records=records)
(out/'coincident-boundary-audit.json').write_text(json.dumps(value,indent=2,default=str),encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='records'},indent=2))
