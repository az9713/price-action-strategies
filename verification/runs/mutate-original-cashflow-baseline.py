"""Actual assertion kills for original cash-flow precision and financial omissions."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();stage=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
subject={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
home=root/'data/dev026/cfm'/out.name.split('-')[0];home.mkdir(parents=True,exist_ok=False)
tests=['tests/test_source_cashflows.py','tests/test_trade_twin_results.py','tests/test_trade_twin_baseline_precision.py','tests/test_valid_original_cashflow_contract.py']
changes=[
 ('float-baseline','backend/lab/source_cashflows.py','net = gross+distributions-borrow-entry_fee-exit_fee',"net = _number(trade['net_pnl'])"),
 ('drop-fees','backend/lab/source_cashflows.py','net = gross+distributions-borrow-entry_fee-exit_fee','net = gross+distributions-borrow'),
 ('drop-borrow','backend/lab/source_cashflows.py','borrow += quantity*mark*weighted/Decimal(365*86400)','borrow += Decimal(0)'),
 ('reverse-split','backend/lab/source_cashflows.py','quantity *= ratio; basis /= ratio; mark /= ratio','quantity /= ratio; basis /= ratio; mark /= ratio'),
 ('drop-dividend','backend/lab/source_cashflows.py','distributions += side*quantity*_number(action.value)','distributions += Decimal(0)'),
 ('grading-epsilon','backend/lab/trade_twin_results.py','Decimal(row.net_profit)>=real',"Decimal(row.net_profit)>=real-Decimal('0.0000001')"),
 ('ignore-input-binding','backend/lab/source_cashflows.py',"or value['input_hash'] != _input_hash(trades, traces, costs, manifest_hash)",'or False'),
 ('legacy-float-source','backend/lab/trade_twin_source.py',"source_profit=str(exact_total(audited.values()))",'source_profit=str(closed)')]
results=[]
for name,module,needle,replacement in [('baseline',None,None,None),*changes]:
    folder=home/name;folder.mkdir()
    for relative in subject:
        destination=folder/relative;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/relative,destination)
    fixture=stage/'verification/fixtures/execution-reference-contract.json'
    target=folder/'verification/fixtures/execution-reference-contract.json';target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(fixture,target)
    probe=root/'verification/fixtures/cashflow-valid-account-probes.py'
    shutil.copy2(probe,folder/'tests/test_valid_original_cashflow_contract.py')
    mutation=None
    if module:
        path=folder/module;text=path.read_text(encoding='utf-8');assert text.count(needle)==1,(name,text.count(needle))
        path.write_text(text.replace(needle,replacement),encoding='utf-8')
        mutation=dict(path=module,original_sha256=subject[module],mutant_sha256=sha(path),needle=needle,replacement=replacement)
    env=os.environ.copy();env.update(PYTHONPATH=str(folder),PYTHONNOUSERSITE='1')
    junit=out/(name+'-junit.xml')
    result=subprocess.run([sys.executable,'-m','pytest','-q',*tests,'--junitxml='+str(junit)],cwd=folder,env=env,capture_output=True,text=True,timeout=240)
    (out/(name+'-stdout.txt')).write_text(result.stdout,encoding='utf-8')
    (out/(name+'-stderr.txt')).write_text(result.stderr,encoding='utf-8')
    suites=list(ET.parse(junit).iter('testsuite'))
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')}
    failures=[f.text or '' for f in ET.parse(junit).iter('failure')]
    if name=='baseline':assert result.returncode==0 and counts['failures']==counts['errors']==counts['skipped']==0,counts
    else:
        assert result.returncode==1 and counts['failures']>0 and counts['errors']==counts['skipped']==0,(name,counts,result.stderr[-1000:])
        assert any('AssertionError' in text or 'DID NOT RAISE' in text for text in failures),(name,'No assertion kill',failures[:1])
    results.append(dict(name=name,exit_code=result.returncode,counts=counts,mutation=mutation,assertion_killed=name!='baseline'))
    print(json.dumps(results[-1]),flush=True)
assert subject=={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
value=dict(scope=__doc__,source_files=subject,current_source_unchanged=True,results=results,actual_mutations=8,
           positive_capability_probe_sha256=sha(probe),all_assertion_killed=True,errors_counted_as_kills=False,final_product_acceptance=False)
(out/'cashflow-mutation-summary.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
