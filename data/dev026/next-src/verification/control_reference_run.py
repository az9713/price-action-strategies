"""Execute default20 historical controls and independently audit the actual books.

Local storage/guard adapters supply primitive data only. Independent Decimal
candles/ATR, graph assignments/hash ranking and execution use no controls engine.
The historical fixture is explicitly action-free; corporate actions have separate
hand/reference tests. This does not independently certify source setup detection.
"""
from pathlib import Path
from decimal import Decimal
from collections import defaultdict
from types import SimpleNamespace
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.service import Lab
from backend.lab.research import core_hash
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute

D=lambda value:Decimal(str(value))


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def independent_features(regular):
    """Own hourly candles and Wilder prior ATR on primitive raw/factor rows."""
    groups=defaultdict(list)
    for row in regular.itertuples(index=False):
        bucket=int((row.timestamp-row.session_open).total_seconds()/60)//60
        groups[(row.symbol,row.session,bucket)].append(row)
    candles=defaultdict(list)
    for (symbol,day,bucket),rows in sorted(groups.items()):
        rows=sorted(rows,key=lambda r:r.timestamp);first=rows[0]
        end=min(first.session_open+__import__('pandas').Timedelta(minutes=(bucket+1)*60),first.session_close)
        start=first.session_open+__import__('pandas').Timedelta(minutes=bucket*60)
        duration=int((end-start).total_seconds()/60);assert len(rows)==duration
        candles[symbol].append(dict(at=end,close=D(rows[-1].close)*D(rows[-1].factor),
            high=max(D(r.high)*D(r.factor) for r in rows),low=min(D(r.low)*D(r.factor) for r in rows),duration=duration))
    features={}
    for symbol,rows in candles.items():
        ranges=[];atr=None
        for i,row in enumerate(rows):
            previous=rows[i-1]['close'] if i else row['close']
            ranges.append(max(row['high']-row['low'],abs(row['high']-previous),abs(row['low']-previous)))
            if i<14:continue
            atr=sum(ranges[:14])/14 if i==14 else (atr*13+ranges[i-1])/14
            local=row['at'].tz_convert('America/New_York')
            features[symbol+'|'+row['at'].isoformat()]=row|dict(symbol=symbol,atr=atr,
                bucket=(local.hour*60+local.minute-570)//30,band=sum(atr/row['close']>=D(b) for b in ['.0025','.005','.01','.02','.04']))
    return features


def independent_assign(source_ids,pools,rank):
    """Enumerate alternating paths breadth-first, storing complete paths."""
    assigned={}
    for root in source_ids:
        owners={moment:source for source,moment in assigned.items()}
        paths=[(root,[])];seen=set();visited={root};chosen=None
        while paths and chosen is None:
            following=[]
            for source,path in paths:
                for candidate in sorted(pools[source],key=lambda key:rank(source,key)):
                    if candidate in seen:continue
                    seen.add(candidate);extended=path+[(source,candidate)]
                    if candidate not in owners:chosen=extended;break
                    other=owners[candidate]
                    if other not in visited:visited.add(other);following.append((other,extended))
                if chosen is not None:break
            paths=following
        if chosen:
            for source,candidate in chosen:assigned[source]=candidate
    return assigned


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job-id');args=parser.parse_args()
    folder=Path(os.environ['PA_EVIDENCE_RUN_DIR']);folder.mkdir(parents=True,exist_ok=True)
    def request(path,value=None):
        headers={};body=None
        if value is not None:
            with urllib.request.urlopen('http://127.0.0.1:8765/api/session') as response:token=json.load(response)['token']
            headers={'Origin':'http://127.0.0.1:8765','X-Lab-Token':token,'Content-Type':'application/json'}
            body=json.dumps(value).encode()
        with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api'+path,data=body,headers=headers),timeout=10) as response:return json.load(response)
    if args.job_id:job=request('/jobs/'+args.job_id)
    else:
        # Omit replicas deliberately: execute the public default20, not a smaller
        # workload mislabeled as default coverage.
        job=request('/controls',dict(dataset_id='90f347229b2fb03ec112ee71',name='Default20 independent historical controls',
            strategy=Strategy().model_dump(),costs=Costs().model_dump(),portfolio=Portfolio().model_dump(),
            start='2022-01-03',end='2022-01-31',seed=42))
    (folder/'created-job.json').write_text(json.dumps(job,indent=2))
    started=time.monotonic()
    while job['status'] not in {'completed','failed','canceled'}:
        (folder/'progress.json').write_text(json.dumps({k:job[k] for k in ['id','status','progress','checkpoint','note']},indent=2))
        if time.monotonic()-started>900:raise TimeoutError('Keep the saved job ID; observation expired without canceling/restarting the job.')
        time.sleep(1);job=request('/jobs/'+job['id'])
    assert job['status']=='completed',job.get('error')
    lab=Lab(ROOT);report=lab.report(job['id']);assert report['core_hash']==core_hash() and report['replicas_requested']==20
    context=lab._evaluation_input(report['dataset_id'],report['start'],report['end'],expected_manifest=report['dataset_manifest_hash'])
    _,regular,actions,_=context;assert not actions,'This historical reference is scoped to the action-free January fixture.'
    features=independent_features(regular);full=lab.report(job['id'],0)
    sources={s['id']:s for s in full['signals'] if report['start']<=s['available_at'][:10]<=report['end']}
    actual_times={s['symbol']+'|'+s['available_at'] for s in sources.values()}
    pools={};geometry={}
    for sid,source in sorted(sources.items()):
        real=features[source['symbol']+'|'+source['available_at']]
        assert abs(real['atr']-D(source['atr']))<=D('1e-9')
        source_band=sum(D(source['atr'])/real['close']>=D(b) for b in ['.0025','.005','.01','.02','.04'])
        eligible=[]
        for key,candidate in features.items():
            if key in actual_times or (candidate['symbol'],candidate['bucket'],candidate['band'],candidate['duration'])!=(source['symbol'],real['bucket'],source_band,real['duration']):continue
            level=candidate['close']+(D(source['level'])-real['close'])/D(source['atr'])*candidate['atr']
            stop=candidate['close']-(real['close']-D(source['stop']))/D(source['atr'])*candidate['atr']
            target=None if source['target_swing'] is None else candidate['close']+(D(source['target_swing'])-real['close'])/D(source['atr'])*candidate['atr']
            if min([level,stop]+([] if target is None else [target]))<=0:continue
            eligible.append(key);geometry[(sid,key)]=(level,stop,target)
        pools[sid]=eligible
    canonical=independent_assign(sorted(sources),pools,lambda source,key:key)
    assert sorted(canonical)==report['matching']['matched_source_ids']
    cfg_id=digest(report['config']);assert cfg_id==report['config_id']
    for replica in report['matching']['replicas']:
        stream=dict(policy=1,seed=report['seed'],configuration=cfg_id,replica=replica['replica'])
        expected=independent_assign(sorted(canonical),pools,lambda source,key:digest(stream|dict(source=source,candidate=key)))
        assert {row['source_id']:row['candidate_key'] for row in replica['matches']}==expected
        for row in replica['matches']:
            level,stop,target=geometry[(row['source_id'],row['candidate_key'])]
            for key,value in [('level',level),('stop',stop),('target_swing',target)]:
                assert (row['signal'][key] is None if value is None else abs(D(row['signal'][key])-value)<=D('1e-9'))
    comparisons=[];primitive_rows=primitive(regular)
    for row in report['books']:
        book=lab.report(job['id'],row['part'])
        expected=execute(primitive_rows,[s|dict(config_id=cfg_id) for s in book['signals']],{cfg_id:book['config']},book['costs'],book['portfolio'],start=book['start'],end=book['end'])
        assert_parity(SimpleNamespace(**book),expected)
        artifact=folder/('reference-account-'+str(row['part'])+'.json.gz')
        artifact.write_bytes(gzip.compress(json.dumps(expected,default=str,separators=(',',':')).encode(),mtime=0))
        comparisons.append(dict(part=row['part'],role=row['role'],replica=row['replica'],trades=len(book['trades']),
            ledger_events=len(book['ledger']),equity_points=len(book['equity']),reference_file=artifact.name))
    assert len(comparisons)==22 and len(report['matching']['replicas'])==20
    output=dict(job_id=job['id'],core_hash=core_hash(),matched_sources=len(canonical),source_signals=len(sources),accounts=comparisons,
        independent_scope='Own Decimal hourly candles/prior ATR/volatility bands, maximal matching/hash ranks/geometry and supplied-signal execution. Setup detection and action completeness are not independently certified.',
        comparison=report['comparison'],observed_seconds=time.monotonic()-started)
    (folder/'default-control-reference.json').write_text(json.dumps(output,indent=2));print(json.dumps(output,indent=2))


if __name__=='__main__':main()
