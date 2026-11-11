"""Audit real behavior records using own Decimal candles, outcomes and summaries.

Production adapters supply guarded primitive minutes and saved event geometry.
This does not independently certify feature detection, all omitted touches or
the completeness of the supplied birth-known interval set. Those need separate
fixture/causal/lifetime acceptance. No behavior/scoring/statistics helper is used.
"""
from pathlib import Path
from collections import defaultdict
from decimal import Decimal
import argparse
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.request
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from backend.lab.service import Lab
from backend.lab.research import core_hash
from backend.lab.config import Strategy
from verification.control_reference_run import independent_assign

D=lambda v:Decimal(str(v))
TOL=D('1e-9');STAT=D('1e-10')
TABLES=['levels_vs_shifted','touch_count','wall_target','shrinking_bounces','line_vs_zone','wick_vs_close','flip_zones','bos_forward','choch_forward','sweep_vs_close','sweep_started_trends','trend_lines','gap_hold_fill','supply_demand_returns','pullback_depth','engulfing_at_levels','rejection_at_levels']

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def request(path,value=None):
    headers={};body=None
    if value is not None:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/session') as r:token=json.load(r)['token']
        headers={'Origin':'http://127.0.0.1:8765','X-Lab-Token':token,'Content-Type':'application/json'};body=json.dumps(value).encode()
    with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8765/api'+path,data=body,headers=headers),timeout=30) as r:return json.load(r)

def candles(regular,tf):
    duration={'1m':1,'5m':5,'15m':15,'1h':60,'4h':240,'1d':10000}[tf];groups=defaultdict(list)
    for row in regular.itertuples(index=False):
        bucket=int((row.timestamp-row.session_open).total_seconds()/60)//duration
        groups[(row.symbol,row.session,bucket)].append(row)
    result=defaultdict(list)
    for (symbol,day,bucket),source in sorted(groups.items()):
        source=sorted(source,key=lambda x:x.timestamp);first=source[0];start=first.session_open+pd.Timedelta(minutes=bucket*duration)
        end=min(start+pd.Timedelta(minutes=duration),first.session_close)
        assert len(source)==int((end-start).total_seconds()/60)
        result[symbol].append(dict(at=end,session=day,open=D(first.open)*D(first.factor),close=D(source[-1].close)*D(source[-1].factor),
            high=max(D(x.high)*D(x.factor) for x in source),low=min(D(x.low)*D(x.factor) for x in source),atr=None))
    for rows in result.values():
        ranges=[];prior=None
        for i,row in enumerate(rows):
            previous=rows[i-1]['close'] if i else row['close'];ranges.append(max(row['high']-row['low'],abs(row['high']-previous),abs(row['low']-previous)))
            if i>=14:prior=sum(ranges[:14])/14 if i==14 else (prior*13+ranges[i-1])/14;row['atr']=prior
    return result

def outcomes(rows,t):
    i=t['index'];side=t['side'];atr=D(t['atr']);near=D(t['hi'] if side==1 else t['lo']);far=D(t['lo'] if side==1 else t['hi'])
    future=rows[i+1:i+51];complete=len(future)==50;outcome='unresolved';resolved=None
    if side*(rows[i]['close']-far)<-atr/4:outcome='break';resolved=0
    maximum=D(0);adverse=D(0)
    for n,b in enumerate(future,1):
        excursion=side*(b['high' if side==1 else 'low']-near)/atr
        maximum=max(maximum,excursion);adverse=max(adverse,-side*(b['low' if side==1 else 'high']-far)/atr)
        if outcome=='unresolved':
            if excursion>=1:outcome='hold';resolved=n
            elif side*(b['close']-far)<-atr/4:outcome='break';resolved=n
    return dict(outcome=outcome if complete else 'censored',observed_outcome=outcome,complete_horizon=complete,
        resolved_after_bars=resolved,followup_bars=len(future),max_favorable_atr=maximum,max_adverse_atr=adverse,
        forward_move_atr=side*(future[-1]['close']-rows[i]['close'])/atr if complete else None)

def parity(actual,expected,tol=TOL):
    if isinstance(expected,Decimal):assert actual is not None and abs(D(actual)-expected)<=tol,(actual,str(expected))
    else:assert actual==expected,(actual,expected)

def audit_chart(chart,primitive):
    for symbol,saved in chart['bars'].items():
        own=[b for b in primitive[symbol] if chart['start']<=b['session']<=chart['end']];assert len(own)==len(saved)
        for a,b in zip(saved,own):
            assert pd.Timestamp(a['available_at'])==b['at']
            for name in ['open','high','low','close']:parity(a[name],b[name])
    checked=defaultdict(int)
    for event in chart['touches']:
        own=primitive[event['symbol']];assert own[event['index']]['at']==pd.Timestamp(event['available_at'])
        parity(event['atr'],own[event['index']]['atr'])
        for key,value in outcomes(own,event).items():parity(event[key],value)
        checked['touches']+=1
    for f in chart['features']:
        assert primitive[f['symbol']][f['born']]['at']==pd.Timestamp(f['available_at'])
        parity(f['atr'],primitive[f['symbol']][f['born']]['atr'])
        screen=(D(f['lo'])-(D('.25')*D(f['atr']) if f['kind']=='level' else 0),D(f['hi'])+(D('.25')*D(f['atr']) if f['kind']=='level' else 0))
        assert f['matchable']==all(x is not None for x in f['shift_draws'])
        for replica,actual in enumerate(f['shift_draws']):
            expected=None
            for attempt in range(128):
                key=digest(dict(seed=chart['seed'],feature=f['id'],replica=replica,attempt=attempt,policy=1));bits=int(key,16)
                offset=(1+D(bits%1000001)/500000)*D(f['atr'])*(1 if (bits>>24)&1 else -1)
                left,right=screen[0]+offset,screen[1]+offset
                if left>0 and all(max(D(a)-right,left-D(b),D(0))>=D(f['atr'])/2 for a,b in f['screening_intervals']):
                    expected=dict(offset=offset,attempts=attempt+1,stream_key=key);break
            assert (actual is None)==(expected is None)
            if expected:
                for key,value in expected.items():parity(actual[key],value)
            checked['shift_draws']+=1
    for fill in chart['gap_fills']:
        rows=primitive[fill['symbol']];i=fill['index'];future=rows[i+1:i+51];far=D(fill['lo'] if fill['side']==1 else fill['hi']);side=fill['side']
        when=0 if side*(rows[i]['close']-far)<=0 else next((n for n,b in enumerate(future,1) if side*(b['low' if side==1 else 'high']-far)<=0),None)
        assert fill['filled_after_bars']==when and fill['observed_fill']==(when is not None)
        assert fill['filled']==((when is not None) if len(future)==50 else None);checked['gap_fills']+=1
    for e in chart['moment_pairs']+chart['moment_assessments']:
        rows=primitive[e['symbol']];i=e['index'];h=e['horizon'];complete=i+h<len(rows)
        parity(e['atr'],rows[i]['atr']);assert rows[i]['at']==pd.Timestamp(e['available_at'])
        parity(e['value'],e['side']*(rows[i+h]['close']-rows[i]['close'])/D(e['atr']) if complete else None)
        if 'complete_horizon' in e:assert e['complete_horizon']==complete
        checked['forward_measurements']+=1
    for symbol,rows in primitive.items():
        for kind in sorted({e['kind'] for e in chart['moments'] if e['symbol']==symbol}):
            for h in [10,20,50]:
                sources={e['id']:e for e in chart['moments'] if e['symbol']==symbol and e['kind']==kind and e['index']+h<len(rows)}
                if not sources:continue
                config=digest(Strategy(timeframe=chart['timeframe'],target='2R').model_dump());seed=int(digest(dict(seed=chart['seed'],timeframe=chart['timeframe'],symbol=symbol,kind=kind,horizon=h))[:8],16)%(2**31)
                pool={symbol+'|'+b['at'].isoformat():(i,b) for i,b in enumerate(rows) if b['atr'] is not None and i+h<len(rows) and chart['start']<=b['session']<=chart['end']}
                actual_times={symbol+'|'+e['available_at'] for e in sources.values()}
                def strata(b,atr):
                    local=b['at'].tz_convert('America/New_York')
                    # Session-open anchoring gives the actual short final bar.
                    minutes={'5m':5,'15m':15,'1h':60,'4h':240,'1d':390,'1m':1}[chart['timeframe']]
                    elapsed=local.hour*60+local.minute-570;duration=min(minutes,elapsed) if elapsed%minutes==0 else elapsed%minutes
                    return ((local.hour*60+local.minute-570)//30,sum(atr/b['close']>=D(x) for x in ['.0025','.005','.01','.02','.04']),duration)
                pools={}
                for sid,e in sources.items():
                    source=rows[e['index']];s=strata(source,D(e['atr']));side=e['side']
                    pools[sid]=[key for key,(_,b) in pool.items() if key not in actual_times and strata(b,b['atr'])==s and b['close']-side*b['atr']>0] if source['close']-side*D(e['atr'])>0 else []
                matched=independent_assign(sorted(sources),pools,lambda source,key:key)
                actual_sources={e['id'] for e in chart['moment_pairs'] if e['symbol']==symbol and e['kind']==kind and e['horizon']==h and e['group']=='real'}
                assert actual_sources==set(matched)
                for replica in range(chart['shift_replicas']):
                    stream=dict(policy=1,seed=seed,configuration=config,replica=replica)
                    expected=independent_assign(sorted(matched),pools,lambda source,key:digest(stream|dict(source=source,candidate=key)))
                    actual={e['id']:symbol+'|'+e['available_at'] for e in chart['moment_pairs'] if e['symbol']==symbol and e['kind']==kind and e['horizon']==h and e['group']=='control' and e['replica']==replica}
                    assert actual==expected,(symbol,kind,h,replica)
                    checked['matched_assignments']+=len(expected)
    return dict(checked)

def observations(charts):
    result={key:[] for key in TABLES};prior={}
    def put(key,e,value,metric,category='all',h=50):
        result[key].append(dict(e=e,value=None if value is None else D(value),metric=metric,category=category,horizon=h))
        if metric in ['hold_fraction','wall_hold_fraction']:put(key,e,None if e.get('outcome')=='unresolved' else value,metric+'_resolved_only',category,h)
    for chart in charts:
        for e in chart['touches']:
            value=int(e['outcome']=='hold') if e['complete_horizon'] else None;bucket=str(e['visit']) if e['visit']<4 else '4+'
            kind=e['kind']
            if kind=='level':
                if e['shape']=='line':
                    put('levels_vs_shifted',e,value,'hold_fraction');put('touch_count',e,value,'hold_fraction',bucket)
                    put('wall_target',e,value,'wall_hold_fraction',bucket);put('wall_target',e,e['max_adverse_atr'] if e['complete_horizon'] else None,'through_excursion_ATR',bucket)
                    key=(e['feature_id'],e['group'],e['replica'],e['shape']);old=prior.get(key)
                    if old and old['visit']==e['visit']-1 and old['complete_horizon'] and e['complete_horizon']:put('shrinking_bounces',e,D(e['max_favorable_atr'])-D(old['max_favorable_atr']),'successive_excursion_change_ATR',bucket)
                    prior[key]=e
                put('line_vs_zone',e,value,'hold_fraction',e['shape'])
            elif kind in ['flip','trend_line','gap','supply_demand']:
                key={'flip':'flip_zones','trend_line':'trend_lines','gap':'gap_hold_fill','supply_demand':'supply_demand_returns'}[kind]
                put(key,e,value,'hold_fraction',('first' if e['visit']==1 else 'later') if kind=='supply_demand' else 'all')
        for e in chart['gap_fills']:put('gap_hold_fill',e,None if e['filled'] is None else int(e['filled']),'full_fill_fraction')
        for e in chart['moment_pairs']+[x for x in chart['moment_assessments'] if x['status']!='matched']:
            e=e|dict(complete_horizon=e.get('complete_horizon',True));kind=e['kind'];targets=[]
            if kind in ['wick_break','close_break']:targets.append(('wick_vs_close',kind))
            if kind in ['bos','choch']:targets.extend([(kind+'_forward','all'),('sweep_started_trends','recent sweep' if e.get('recent_sweep') else 'no recent sweep')])
            if kind in ['sweep','close_break']:targets.append(('sweep_vs_close',kind))
            if kind=='pullback':targets.append(('pullback_depth','<1' if e['depth_atr']<1 else '1–2' if e['depth_atr']<2 else '2–3' if e['depth_atr']<3 else '3+'))
            if kind in ['engulfing','rejection']:targets.append((kind+'_at_levels','all'))
            for key,category in targets:put(key,e,e['value'],'forward_close_move_ATR',category,e['horizon'])
    return result

def audit_tables(report,charts):
    all_rows=observations(charts);sessions=sorted({d for c in charts for d in c['sessions']});max_error=0.;checked=0
    for key,table in report['tables'].items():
        for r in table['rows']:
            def member(x):
                e=x['e'];subset={'pooled':'All instruments/charts','timeframe':e['timeframe'],'instrument':e['symbol'],'era':'early' if e['session']<report['era_split'] else 'late'}[r['scope']]
                return subset==r['subset'] and (x['metric'],x['category'],x['horizon'])==(r['metric'],r['category'],r['horizon'])
            group=[x for x in all_rows[key] if member(x)]
            if r['metric']=='not_observed':assert not all_rows[key] and r['real_n']==r['control_n']==0;checked+=1;continue
            used=[x for x in group if x['value'] is not None and x['e']['complete_horizon'] and x['e'].get('matchable',True)]
            selected=[d for d in sessions if r['scope']!='era' or ('early' if d<report['era_split'] else 'late')==r['subset']]
            sums={g:sum((x['value'] for x in used if x['e']['group']==g),D(0)) for g in ['real','control']}
            counts={g:sum(x['e']['group']==g for x in used) for g in ['real','control']}
            means={g:sums[g]/counts[g] if counts[g] else None for g in counts}
            for g in counts:
                assert r[g+'_n']==counts[g];parity(r[g+'_mean'],means[g],STAT)
                assert r[g+'_censored']==sum(x['e']['group']==g and not x['e']['complete_horizon'] for x in group)
                assert r[g+'_unresolved']==sum(x['e']['group']==g and x['e'].get('outcome')=='unresolved' for x in group)
            assert r['real_full_sample_n']==sum(x['e']['group']=='real' and x['e']['complete_horizon'] for x in group)
            difference=means['real']-means['control'] if all(v is not None for v in means.values()) else None;parity(r['difference'],difference,STAT)
            attempted=2000 if difference is not None and len(selected)>=2 else 0;assert r['attempted_resamples']==attempted
            values=[]
            if attempted:
                # Count session multiplicities rather than concatenating the
                # production matrix rows. Same declared seeded draws.
                daily=np.array([[float(sum((x['value'] for x in used if x['e']['session']==d and x['e']['group']==g),D(0))) for g in ['real','control']]+[sum(x['e']['session']==d and x['e']['group']==g for x in used) for g in ['real','control']] for d in selected])
                draws=np.random.default_rng(r['seed']).integers(0,len(selected),size=(2000,len(selected)))
                multiplicity=np.array([np.bincount(draw,minlength=len(selected)) for draw in draws]);totals=multiplicity@daily
                for a,b,n,m in totals:
                    if n>0 and m>0:values.append(a/n-b/m)
            assert r['valid_resamples']==len(values)
            if len(values)==2000:
                values.sort()
                def quantile(p):
                    at=(len(values)-1)*p;lo=int(at);return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(at-lo)
                for name,p in [('interval_low',.025),('interval_high',.975)]:
                    expected=quantile(p);parity(r[name],D(expected),STAT);max_error=max(max_error,abs(r[name]-expected))
            else:assert r['interval_low'] is None and r['interval_high'] is None
            checked+=1
    return dict(table_rows=checked,largest_interval_difference=max_error)

def main():
    p=argparse.ArgumentParser();p.add_argument('--job-id');args=p.parse_args();folder=Path(os.environ['PA_EVIDENCE_RUN_DIR']);started=time.monotonic()
    if args.job_id:job=request('/jobs/'+args.job_id)
    else:
        # Explicit newly audited SPY-only child: no claim this is the full
        # five-instrument/default-workload operating-envelope test.
        child=request('/datasets/90f347229b2fb03ec112ee71/select',dict(symbols=['SPY'],start='2022-01-03',end='2022-01-31'))
        (folder/'selected-dataset.json').write_text(json.dumps(child,indent=2),encoding='utf-8')
        job=request('/behavior',dict(dataset_id=child['id'],name='Default20 five-chart SPY behavior audit',start='2022-01-03',end='2022-01-31',seed=42))
    (folder/'created-job.json').write_text(json.dumps(job,indent=2),encoding='utf-8')
    while job['status'] not in ['completed','failed','canceled']:
        (folder/'progress.json').write_text(json.dumps({k:job[k] for k in ['id','status','progress','checkpoint','note']},indent=2),encoding='utf-8')
        if time.monotonic()-started>900:raise TimeoutError('Keep saved job ID; observation timeout does not cancel or restart work.')
        time.sleep(1);job=request('/jobs/'+job['id'])
    assert job['status']=='completed',job.get('error');lab=Lab(ROOT);report=lab.report(job['id']);assert report['core_hash']==core_hash()
    assert report['settings']['shift_replicas']==20 and report['settings']['timeframes']==['5m','15m','1h','4h','1d']
    manifest,regular,actions,_=lab._evaluation_input(report['dataset_id'],report['start'],report['end'],expected_manifest=report['dataset_manifest_hash']);assert not actions
    (folder/'dataset-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');parts=[];audits=[]
    for row in report['charts']:
        chart=lab.report(job['id'],row['part']);parts.append(chart);audits.append(dict(timeframe=chart['timeframe'],**audit_chart(chart,candles(regular,chart['timeframe']))))
        (folder/('chart-'+chart['timeframe']+'.json.gz')).write_bytes(gzip.compress(json.dumps(chart,separators=(',',':'),ensure_ascii=True).encode(),mtime=0))
        (folder/'audit-progress.json').write_text(json.dumps(audits,indent=2),encoding='utf-8')
    statistics=audit_tables(report,parts);(folder/'behavior-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    output=dict(job_id=job['id'],dataset_id=report['dataset_id'],core_hash=report['core_hash'],counts=report['counts'],charts=audits,statistics=statistics,
        observed_seconds=time.monotonic()-started,scope=__doc__.strip(),workload='Default20/five charts, explicitly selected SPY-only January2022 child; already viewed discovery dates, action-free. Not full five-symbol scale or independent detector completeness certification.')
    (folder/'behavior-reference.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print(json.dumps(output,indent=2))

if __name__=='__main__':main()
