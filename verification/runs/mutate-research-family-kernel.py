"""Actual assertion mutations of prespecified research axes and all-version means."""
from pathlib import Path
import ast,hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subject={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
fixtures={name:sha(stage/name) for name in ['verification/fixtures/execution-reference-contract.json']}
home=root/'data/dev027/family-mutations'/out.name.split('-')[0];home.mkdir(parents=True,exist_ok=False)
module='backend/lab/research_funnel.py'
mutations=[
    ('drop-losing-daily-pnl','marked[index]+=value-previous','marked[index]+=max(value-previous,0)'),
    ('failed-member-complete',"return base | dict(state='incomplete',failed_members=failed", "return base | dict(state='complete',failed_members=failed"),
    ('trade-count-denominator','marked=[value/len(ids) for value in marked];realized=[value/len(ids) for value in realized]',"marked=[value/max(1,sum(len(r['trades']) for r in reports.values())) for value in marked];realized=[value/max(1,sum(len(r['trades']) for r in reports.values())) for value in realized]"),
    ('conflate-realized-and-marked','realized=[value/len(ids) for value in realized]','realized=list(marked)'),
    ('population-deviation','root = math.sqrt(count-1)','root = math.sqrt(count)'),
    ('naive-exit-clock','if exited.tzinfo is None or exited.utcoffset() is None:','if False:'),
    ('erase-era-ordering',"if not (self.discovery.start <= self.era_one.start <= self.era_one.end\n                < self.era_two.start <= self.era_two.end <= self.discovery.end):",'if False:'),
    ('ignore-complete-calendar',"if any(not isinstance(row,dict) for row in equity) or [row.get('date') for row in equity]!=days:",'if False:'),
]
results=[]
tests=['tests/test_research_funnel.py','tests/test_research_funnel_accounts.py','tests/test_research_funnel_boundaries.py']
for name,needle,replacement in [('baseline',None,None),*mutations]:
    folder=home/name;folder.mkdir()
    for relative in subject|fixtures:
        target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/relative,target)
    mutation=None
    if needle:
        path=folder/module;text=path.read_text(encoding='utf-8');assert text.count(needle)==1,(name,text.count(needle))
        path.write_text(text.replace(needle,replacement),encoding='utf-8');ast.parse(path.read_text())
        mutation=dict(path=module,original_sha256=subject[module],mutant_sha256=sha(path),needle=needle,replacement=replacement)
    env=os.environ.copy();env.update(PYTHONPATH=str(folder)+os.pathsep+str(folder/'tests'),PYTHONNOUSERSITE='1')
    case_out=out/name;case_out.mkdir();env['PA_EVIDENCE_RUN_DIR']=str(case_out)
    junit=case_out/'junit.xml'
    result=subprocess.run([sys.executable,'-m','pytest','-q',*tests,'--junitxml='+str(junit)],cwd=folder,env=env,capture_output=True,text=True,timeout=180)
    (case_out/'stdout.txt').write_text(result.stdout,encoding='utf-8');(case_out/'stderr.txt').write_text(result.stderr,encoding='utf-8')
    suites=list(ET.parse(junit).iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    assert counts['tests']==59
    if name=='baseline':assert result.returncode==0 and counts['failures']==counts['errors']==counts['skipped']==0,(counts,result.stdout[-2000:])
    else:
        failures=[f.text or '' for f in ET.parse(junit).iter('failure')]
        assert result.returncode==1 and counts['failures']>0 and counts['errors']==counts['skipped']==0,(name,counts,result.stdout[-2000:])
        assert any('AssertionError' in value or 'DID NOT RAISE' in value for value in failures),(name,'No assertion kill')
    results.append(dict(name=name,exit_code=result.returncode,counts=counts,mutation=mutation,assertion_killed=name!='baseline'))
    (out/'family-mutation-progress.json').write_text(json.dumps(dict(results=results,complete=False),indent=2),encoding='utf-8')
    print(json.dumps(results[-1]),flush=True)
assert subject=={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
assert fixtures=={name:sha(stage/name) for name in fixtures}
(out/'family-mutation-summary.json').write_text(json.dumps(dict(scope=__doc__,source_files=subject,current_source_unchanged=True,
    original_fixture_hashes=fixtures,results=results,actual_mutations=8,all_assertion_killed=True,errors_counted_as_kills=False,final_product_acceptance=False),indent=2),encoding='utf-8')
