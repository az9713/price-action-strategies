"""Published equity common recipes; no prices or outcome-dependent generation."""
from itertools import product
from collections import Counter
import json,math,re
from datetime import datetime,date
from zoneinfo import ZoneInfo
import numpy as np
from .config import Strategy,FAMILIES,TIMEFRAMES,APPLICABILITY,identity,canonical
from .data import DataError

POLICY_VERSION=1
MAX_PROPOSALS=200000
BREAKS={'breakout','break_of_structure','change_of_character'}
REACTION_ENTRIES=[('limit','none'),('next_open','close_back'),('next_open','rejection'),('next_open','engulfing')]
BREAK_ENTRIES=[('next_open','none'),('limit','none')]
FILTERS={'trend_filter':['setup','higher','daily'],'session_filter':['open'],'news':['skip','half'],
         'skip_run_days':[3,5],'skip_choppy':[True],'fresh_breakout':[True],'gap_confluence':[True]}
DOMAINS={
 'direction':['both','long','short'],'swing_strength':[2,3,5,8],'level_tolerance':[.1,.25,.5],
 'level_age':[24,96],'confirmation':['none','close_back','rejection','engulfing','either','lower_bos'],
 'confirmation_window':[1,3],'entry':['next_open','same_close','limit'],'limit_expiry':[1,3],
 'stop_reference':['swing','level','wick','gap'],'stop_kind':['hard','close'],'stop_buffer':[0.,.1,.25],
 'target':['1R','1.5R','2R','3R','4R','5R','swing'],'structure_exit':[False,True],
 'max_hold':[0,24,96],'flat_at_close':[False,True],'min_touches':[1,2,3,4],
 'level_shape':['line','zone'],'sweep_required':[False,True],'sweep_depth':[0.,.1,.25,.5],
 'reclaim_bars':[1,3,5],'retest_window':[6,12,24],'pullback_ranges':[(0.,3.),(.25,1.5),(.5,2.)],
 'impulse_bars':[2,3,4,5],'impulse_atr':[1.5,2.,3.],
}
SCOPE='Published equities common variants; the host private14016 grid and six named recipes are not reproduced. Initial gates do not replace twins, eras, replication or final testing.'

class CommonSamplingError(DataError):
    def __init__(self,message,configurations,sampling):
        super().__init__(message);self.configurations=configurations;self.sampling=sampling

def canonical_axes(families,frames):
    if (not isinstance(families,list) or not isinstance(frames,list) or not families or not frames or
        any(not isinstance(f,str) for f in families+frames) or len(set(families))!=len(families) or len(set(frames))!=len(frames) or
        set(families)-set(FAMILIES) or set(frames)-set(TIMEFRAMES)):
        raise DataError('Choose distinct supported, nonempty families and setup charts.')
    return [f for f in FAMILIES if f in families],[tf for tf in TIMEFRAMES if tf in frames]

def variants(family):
    if family in {'level_bounce','breakout','flip_zone'}:
        return [dict(level_shape=shape,min_touches=n) for shape,n in product(['line','zone'],range(1,5))]
    if family=='change_of_character':return [dict(sweep_required=v) for v in [False,True]]
    if family=='sweep_reclaim':return [dict(sweep_depth=d,reclaim_bars=n) for d,n in product([0.,.25],[1,3])]
    if family=='trend_pullback':return [dict(pullback_min=a,pullback_max=b) for a,b in DOMAINS['pullback_ranges']]
    if family=='supply_demand':return [dict(impulse_bars=n,impulse_atr=a) for n,a in product([2,3,4,5],[1.5,2.,3.])]
    return [{}]

def recipe():
    return dict(policy_version=POLICY_VERSION,random_domains=DOMAINS,filter_groups=FILTERS,
                common_variants={f:variants(f) for f in FAMILIES},reaction_entries=REACTION_ENTRIES,break_entries=BREAK_ENTRIES,
                source='https://www.youtube.com/watch?v=z97PnFIPoFg',scope=SCOPE)

def preview_recipe(families,frames,include_news=False):
    families,frames=canonical_axes(families,frames)
    if type(include_news) is not bool:raise DataError('News inclusion must be an explicit boolean.')
    cells=[dict(family=f,timeframe=tf,count=len(variants(f))*(2 if f in BREAKS else 4)*2*4*(4 if include_news else 3)) for f in families for tf in frames]
    value=recipe()
    return dict(grid_count=sum(c['count'] for c in cells),cells=cells,recipe_hash=identity(value),
                include_news=include_news,**json.loads(canonical(value)))

def common_grid(families,frames,include_news=False):
    families,frames=canonical_axes(families,frames)
    filters=[{},dict(trend_filter='setup'),dict(session_filter='open')]+([dict(news='skip')] if include_news else [])
    for family,tf in product(families,frames):
        for variant,(entry,confirmation),stop,target,filtered in product(variants(family),BREAK_ENTRIES if family in BREAKS else REACTION_ENTRIES,['level','swing'],['1R','2R','3R','swing'],filters):
            yield Strategy(family=family,timeframe=tf,swing_strength=3,direction='both',entry=entry,confirmation=confirmation,
                stop_reference=stop,stop_kind='hard',stop_buffer=.1,max_hold=96,target=target,**variant,**filtered).model_dump()

def active_filters(configuration):
    neutral={'trend_filter':'none','session_filter':'core','news':'trade','skip_run_days':0,'skip_choppy':False,'fresh_breakout':False,'gap_confluence':False}
    return {k:configuration[k] for k,value in neutral.items() if configuration[k]!=value}

def slot_key(seed,family,timeframe,filters,slot,retry,include_news):
    return identity(dict(recipe_hash=identity(recipe()),seed=seed,family=family,timeframe=timeframe,filters=filters,slot=slot,retry=retry,include_news=include_news))

def draw_configuration(seed,family,timeframe,filters,slot,retry=0,include_news=False):
    rng=np.random.default_rng(int(slot_key(seed,family,timeframe,filters,slot,retry,include_news)[:32],16))
    def choose(values):return values[int(rng.integers(len(values)))]
    value=Strategy(family=family,timeframe=timeframe).model_dump()
    for key in ['direction','swing_strength','level_tolerance','level_age','entry','stop_kind','stop_buffer','target','structure_exit','max_hold']:
        value[key]=choose(DOMAINS[key])
    charts=list(TIMEFRAMES);index=charts.index(timeframe);triggers=['1h'] if timeframe=='1d' else charts[max(0,index-2):index+1]
    value['trigger_timeframe']=choose(triggers)
    confirmations=DOMAINS['confirmation'] if charts.index(value['trigger_timeframe'])<index else DOMAINS['confirmation'][:-1]
    value['confirmation']=choose(confirmations)
    if value['confirmation']!='none':value['confirmation_window']=choose(DOMAINS['confirmation_window'])
    if value['entry']=='limit':value['limit_expiry']=choose(DOMAINS['limit_expiry'])
    value['stop_reference']=choose(DOMAINS['stop_reference'] if family=='fair_value_gap' else DOMAINS['stop_reference'][:-1])
    if timeframe not in {'4h','1d'}:value['flat_at_close']=choose(DOMAINS['flat_at_close'])
    if family in {'level_bounce','breakout','flip_zone'}:
        for key in ['min_touches','level_shape']:value[key]=choose(DOMAINS[key])
    if family=='flip_zone':value['retest_window']=choose(DOMAINS['retest_window'])
    if family=='trend_pullback':value['pullback_min'],value['pullback_max']=choose(DOMAINS['pullback_ranges'])
    if family=='supply_demand':
        for key in ['impulse_bars','impulse_atr']:value[key]=choose(DOMAINS[key])
    if family=='change_of_character':value['sweep_required']=choose(DOMAINS['sweep_required'])
    if family=='sweep_reclaim' or value['sweep_required']:
        for key in ['sweep_depth','reclaim_bars']:value[key]=choose(DOMAINS[key])
    groups=[k for k in FILTERS if (k!='news' or include_news) and
            (k!='fresh_breakout' or family in {'breakout','break_of_structure','change_of_character','flip_zone'}) and
            (k!='gap_confluence' or family in APPLICABILITY['gap_confluence'])]
    for index in rng.choice(len(groups),size=filters,replace=False):
        key=groups[int(index)];value[key]=choose(FILTERS[key])
    return value

def quotas(total,weights):
    # Integer arithmetic keeps remainder ties exact, including large totals.
    denominator=sum(weights);result=[total*w//denominator for w in weights]
    for i in sorted(range(len(weights)),key=lambda i:(-(total*weights[i]%denominator),i))[:total-sum(result)]:result[i]+=1
    return result

def sample_common(request):
    policy=request.sampling_policy;families,frames=canonical_axes(request.families,request.timeframes)
    metadata=preview_recipe(families,frames,policy.include_news);configs=[];seen=set();proposals=[];duplicates=rejected=0
    def record():return dict(attempts=len(proposals),unique=len(configs),duplicates=duplicates,rejected=rejected,proposals=proposals,
                             seed=request.seed,policy_version=POLICY_VERSION,mode=policy.mode,recipe_hash=metadata['recipe_hash'],recipe=metadata,
                             method='Complete explicit equity common grid' if policy.mode=='common_grid' else 'Unique seeded family quotas with accepted40/40/20 filter groups; canonical chart rotation')
    if policy.mode=='common_grid':
        if request.count!=metadata['grid_count']:raise CommonSamplingError(f'Complete common grid requires exactly {metadata["grid_count"]} configurations; use the recipe preview.',configs,record())
        slots=((c,None,None,None) for c in common_grid(families,frames,policy.include_news))
    elif policy.mode=='common_random':
        def random_slots():
            for family,total in zip(families,quotas(request.count,[1]*len(families))):
                cursor=0
                for filtered,n in enumerate(quotas(total,[4,4,2])):
                    for _ in range(n):
                        yield None,family,frames[cursor%len(frames)],(filtered,cursor)
                        cursor+=1
        slots=random_slots()
    else:raise DataError('Choose a common_grid or common_random mode.')
    for configuration,family,tf,slot in slots:
        retry=0
        while True:
            if len(proposals)>=MAX_PROPOSALS:raise CommonSamplingError('Common sampling exhausted the bounded200000-proposal allowance; no partial search will run.',configs,record())
            filtered=len(active_filters(configuration)) if slot is None else slot[0];ordinal=len(configs) if slot is None else slot[1]
            key=slot_key(request.seed,configuration['family'] if configuration is not None else family,configuration['timeframe'] if configuration is not None else tf,filtered,ordinal,retry,policy.include_news)
            proposed=configuration if configuration is not None else draw_configuration(request.seed,family,tf,filtered,ordinal,retry,policy.include_news)
            entry=dict(attempt=len(proposals)+1,configuration=proposed,stream_key=key,slot=ordinal,filter_count=filtered)
            try:cfg=Strategy(**proposed);cid=identity(cfg)
            except (ValueError,TypeError) as error:
                rejected+=1;proposals.append(entry|dict(status='invalid',reason=str(error)[:500]));retry+=1;continue
            duplicate=cid in seen
            proposals.append(entry|dict(status='duplicate' if duplicate else 'accepted',config_id=cid,family=cfg.family,timeframe=cfg.timeframe))
            if duplicate:duplicates+=1;retry+=1;continue
            seen.add(cid);configs.append(cfg.model_dump());break
    return configs,record()

def count_discovery_signals(signals,start,end):
    """Count saved primary decisions in equity session dates, excluding warm-up."""
    if not isinstance(signals,list):raise DataError('Saved signals require a complete list.')
    try:
        if not isinstance(start,str) or not isinstance(end,str):raise ValueError('Invalid date window.')
        first,last=date.fromisoformat(start),date.fromisoformat(end)
        if first.isoformat()!=start or last.isoformat()!=end or first>last:raise ValueError('Invalid date window.')
    except ValueError as error:raise DataError('Discovery dates must be explicit ordered ISO dates.') from error
    counted=0
    for signal in signals:
        try:
            raw=signal['available_at']
            if not isinstance(raw,str):raise ValueError('Timestamp must be explicit text.')
            at=datetime.fromisoformat(raw)
            if at.tzinfo is None:raise ValueError('Timestamp requires a timezone.')
            day=at.astimezone(ZoneInfo('America/New_York')).date().isoformat()
        except (ValueError,TypeError,KeyError,OverflowError) as error:raise DataError('Saved signal has an invalid decision timestamp.') from error
        counted+=start<=day<=end
    return counted

def initial_screen(rows,policy,cancel=None,strata=None):
    if not isinstance(rows,list) or not rows:raise DataError('Initial discovery screening requires saved complete accounts.')
    accounts=[];groups={};seen=set();config_ids=set()
    def empty():return dict(generated=0,signal_qualified=0,enough_trades=0,profitable=0,sharpe_passed=0)
    if strata is not None:
        if not isinstance(strata,list) or not strata:raise DataError('Frozen discovery strata require explicit cells.')
        for cell in strata:
            if not isinstance(cell,dict) or cell.get('family') not in FAMILIES or cell.get('timeframe') not in TIMEFRAMES:
                raise DataError('Invalid frozen discovery stratum.')
            key=(cell['family'],cell['timeframe'])
            if key in groups:raise DataError('Duplicate frozen discovery stratum.')
            groups[key]=empty()
    total=empty()
    for index,row in enumerate(rows):
        if cancel and index%64==0 and cancel():raise InterruptedError('Initial discovery grading canceled before publication.')
        if not isinstance(row,dict) or not isinstance(row.get('metrics'),dict):raise DataError('Malformed saved discovery row.')
        metrics=row['metrics'];signals=row.get('signal_count');trades=metrics.get('trades');profit=metrics.get('net_profit');sharpe=metrics.get('marked_sharpe')
        if (type(signals) is not int or signals<0 or type(trades) is not int or trades<0 or
            type(profit) not in (int,float) or not math.isfinite(profit) or
            sharpe is not None and (type(sharpe) not in (int,float) or not math.isfinite(sharpe))):raise DataError('Discovery counts/profit/Sharpe must be valid saved values.')
        if (type(row.get('part')) is not int or row['part']<0 or row['part'] in seen or
            any(not isinstance(row.get(k),str) or not re.fullmatch('[a-f0-9]{64}',row[k]) for k in ['config_id','report_sha256'])):raise DataError('Malformed discovery account identity.')
        try:cfg=Strategy(**row['config'])
        except (KeyError,TypeError,ValueError) as error:raise DataError('Malformed discovery configuration.') from error
        if identity(cfg)!=row['config_id'] or row['config_id'] in config_ids:raise DataError('Discovery configuration identity is inconsistent or duplicated.')
        seen.add(row['part']);config_ids.add(row['config_id'])
        flags=dict(signal_qualified=signals>=policy.minimum_signals,enough_trades=trades>=policy.minimum_trades,profitable=profit>0,
                   sharpe_passed=sharpe is not None and sharpe>=policy.minimum_sharpe)
        failures=[k for k,v in flags.items() if not v];failures=['undefined_sharpe' if k=='sharpe_passed' and sharpe is None else k for k in failures]
        key=(cfg.family,cfg.timeframe)
        if strata is not None and key not in groups:raise DataError('Saved account lies outside frozen discovery strata.')
        group=groups.setdefault(key,empty());total['generated']+=1;group['generated']+=1;passed=True
        for key,flag in flags.items():
            passed=passed and flag
            if passed:total[key]+=1;group[key]+=1
        accounts.append(dict(part=row['part'],config_id=row['config_id'],source_part_sha256=row['report_sha256'],family=cfg.family,timeframe=cfg.timeframe,
                             signal_count=signals,trades=trades,net_profit=profit,marked_sharpe=sharpe,**flags,initial_gates_passed=passed,failures=failures))
    return dict(policy_version=POLICY_VERSION,role='initial_discovery_only',settings=policy.model_dump(),counts=total,
                groups=[dict(family=f,timeframe=tf,counts=groups[(f,tf)]) for f in FAMILIES for tf in TIMEFRAMES if (f,tf) in groups],accounts=accounts,
                later_stages={k:'not_run' for k in ['trade_twins','eras','instrument_replication','family_ensemble','final_window']},
                signal_definition='Primary decisions whose available_at New York session date lies within the requested discovery window; warm-up signals excluded.',
                scope='Initial discovery gates are not a surviving strategy, frozen candidate, independence estimate or final validation. All complete accounts remain saved.')
