"""Historical paired accounts: independent Decimal supplied-signal execution.

Production adapters supply guarded primitive minute rows and saved signals only.
This is not an independent strategy detector, omitted-event or edge certificate.
"""
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.request
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.lab.config import Strategy,Costs,Portfolio
from backend.lab.service import Lab
from backend.lab.research import core_hash
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute
from verification.reference_statistics import linear_quantile

D=lambda x:Decimal(str(x))
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def request(path,value=None):
    headers={};body=None
    if value is not None:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/session') as r:token=json.load(r)['token']
        headers={'Origin':'http://127.0.0.1:8765','X-Lab-Token':token,'Content-Type':'application/json'};body=json.dumps(value).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api'+path,data=body,headers=headers),timeout=15) as r:return json.load(r)

def decisions(report):
    result=set()
    for row in report['signals']:
        at=datetime.fromisoformat(row['available_at']);assert at.tzinfo is not None
        if report['start']<=at.astimezone(ZoneInfo('America/New_York')).date().isoformat()<=report['end']:
            result.add((row['symbol'],at.astimezone(ZoneInfo('UTC')).isoformat(),row['side']))
    return result

def interval(values,seed):
    # NumPy supplies only reproducible random indices. Decimal summation and
    # stdlib order statistics independently implement the estimator.
    rng=np.random.default_rng(seed);n=len(values);totals=[]
    for starts in rng.integers(0,n,size=(2000,(n+4)//5)):
        indices=[(int(s)+i)%n for s in starts for i in range(5)][:n]
        totals.append(sum((values[i] for i in indices),D(0)))
    return [linear_quantile(totals,D('.025')),linear_quantile(totals,D('.975'))]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job-id');args=parser.parse_args()
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR']);folder.mkdir(parents=True,exist_ok=True)
    job=request('/jobs/'+args.job_id) if args.job_id else request('/ablations',dict(
        dataset_id='90f347229b2fb03ec112ee71',name='Independent historical four-account paired target audit',
        strategy=Strategy().model_dump(),costs=Costs().model_dump(),portfolio=Portfolio().model_dump(),
        start='2022-01-03',end='2022-01-31',seed=42,field='target',alternatives=['2R','3R','4R']))
    (folder/'created-job.json').write_text(json.dumps(job,indent=2),encoding='utf-8');began=time.monotonic()
    while job['status'] not in {'completed','failed','canceled'}:
        (folder/'progress.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
        if time.monotonic()-began>900:raise TimeoutError('Observation deadline reached; job remains intact: '+job['id'])
        time.sleep(1);job=request('/jobs/'+job['id'])
    assert job['status']=='completed',job.get('error')
    lab=Lab(ROOT);root=lab.report(job['id']);assert root['core_hash']==core_hash() and root['report_type']=='paired_ablations'
    (folder/'study.json').write_text(json.dumps(root,indent=2),encoding='utf-8')
    manifest,regular,actions,_=lab._evaluation_input(root['dataset_id'],root['start'],root['end'],expected_manifest=root['dataset_manifest_hash'])
    assert not actions,'This historical reference is deliberately action-free; actions have separate fixtures.'
    (folder/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    bars=primitive(regular);books=[];references=[];audits=[]
    for arm in root['arms']:
        book=lab.report(job['id'],arm['part']);assert digest(book['config'])==arm['config_id']==book['config_id']
        assert book['metrics']==arm['metrics'] and book['core_hash']==root['core_hash']
        supplied=[s|dict(config_id=digest(book['config'])) for s in book['signals']]
        expected=execute(bars,supplied,{digest(book['config']):book['config']},book['costs'],book['portfolio'],[],book['start'],book['end'])
        assert_parity(SimpleNamespace(**book),expected)
        values=[D(book['portfolio']['capital']),*[e['equity'] for e in expected['equity']]]
        daily=[b-a for a,b in zip(values,values[1:])]
        assert abs(sum(daily)-D(book['metrics']['net_profit']))<=D('1e-7')
        assert len(daily)==len(book['metrics']['daily_pnl'])
        for a,b in zip(daily,book['metrics']['daily_pnl']):assert abs(a-D(b))<=D('1e-7')
        with gzip.open(folder/('account-'+str(arm['part'])+'.json.gz'),'wt',encoding='utf-8') as f:json.dump(dict(actual=book,reference=expected),f,default=str)
        books.append(book);references.append(daily)
        audits.append(dict(part=arm['part'],config_id=book['config_id'],trades=len(expected['trades']),ledger_events=len(expected['ledger']),sessions=len(daily),net_profit=str(sum(daily))))
    comparisons=[];largest=D(0)
    for actual,flat in zip(root['comparisons'],root['comparison_rows']):
        part=actual['alternative_part'];base=books[0];other=books[part]
        assert [k for k,v in base['config'].items() if v!=other['config'][k]]==[root['field']]
        delta=[b-a for a,b in zip(references[0],references[part])];net=sum(delta)
        seed=int(digest(dict(policy=1,seed=root['seed'],baseline=base['config_id'],alternative=other['config_id'],field=root['field']))[:8],16)%(2**31)
        assert flat['seed']==seed and actual['sessions']==len(delta)
        assert abs(net-D(actual['net_difference']))<=D('1e-7')
        for day,difference,point in zip(base['equity'],delta,actual['daily_differences']):
            assert day['date']==point['date'] and abs(difference-D(point['difference']))<=D('1e-7')
        a,b=decisions(base),decisions(other)
        for key,value in dict(baseline_signals=len(a),alternative_signals=len(b),common_decision_signals=len(a&b),baseline_only_signals=len(a-b),alternative_only_signals=len(b-a),baseline_trades=len(base['trades']),alternative_trades=len(other['trades'])).items():assert actual[key]==value
        enough=len(delta)>5 and bool(base['trades']) and bool(other['trades'])
        bounds=interval(delta,seed) if enough else None
        if bounds is None:assert actual['paired_pnl_interval'] is None
        else:
            for key,expected in zip(['low','high'],bounds):
                difference=abs(expected-D(actual['paired_pnl_interval'][key]));largest=max(largest,difference);assert difference<=D('1e-7')
        comparisons.append(dict(part=part,seed=seed,net_difference=str(net),reference_interval=None if bounds is None else [str(x) for x in bounds]))
    registry=lab.store.registry(limit=200,job_id=job['id'])
    assert len(registry['rows'])==len(books) and all(r['state']=='completed' and r['provenance']=='prespecified' and r['attempts']==1 and r['artifact_sha256'] for r in registry['rows'])
    events=lab.store.events(job['id']);frozen=next(e for e in events if e['kind']=='trial_plan_frozen')
    assert all(frozen['at']<=a['started'] for r in registry['rows'] for a in r['attempt_history'])
    result=dict(status='pass',job_id=job['id'],core_hash=root['core_hash'],dataset_manifest_hash=root['dataset_manifest_hash'],accounts=audits,comparisons=comparisons,maximum_interval_difference=str(largest),elapsed_seconds=time.monotonic()-began,
        scope='Own Decimal supplied-signal account execution, complete-calendar daily pairing, signal-overlap counts and2000-draw intervals. Not independent detector/omitted-event, all-options, edge or final-product certification.')
    (folder/'reference-audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
