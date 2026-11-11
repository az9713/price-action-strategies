"""Frozen conditional-dial spread selection, before any selected-account P&L.

This core requires an authorized signal probe and a durable caller-owned event
sink. It does not by itself provide a worker/API or certify source-scale runs.
"""
from itertools import product
from pathlib import Path
import gzip,hashlib,json,re
import numpy as np
from pydantic import Field,model_validator
from .config import Contract,Strategy,FAMILIES,TIMEFRAMES,APPLICABILITY,canonical,identity
from .data import DataError,atomic_json
from .research import core_hash,require_current_source
from .sampling import DOMAINS,canonical_axes

VERSION=1
SCALE=60
class SpreadError(DataError):pass

class SpreadSettings(Contract):
    families:list[str]=Field(default_factory=lambda:list(FAMILIES),min_length=1,max_length=10)
    timeframes:list[str]=Field(default_factory=lambda:list(TIMEFRAMES),min_length=1,max_length=6)
    seed:int=Field(42,strict=True,ge=0,le=2**31-1)
    per_family:int=Field(4000,strict=True,ge=1,le=100000)
    batch_size:int=Field(400,strict=True,ge=1,le=400)
    max_batches_per_family:int=Field(8000,strict=True,ge=1,le=100000)
    minimum_signals:int=Field(40,strict=True,ge=40,le=1000000)
    include_news:bool=Field(False,strict=True)

    @model_validator(mode='after')
    def axes(self):
        families,frames=canonical_axes(self.families,self.timeframes)
        object.__setattr__(self,'families',families);object.__setattr__(self,'timeframes',frames)
        if len(families)*self.per_family>100000:raise ValueError('Selected spread exceeds the existing100000-configuration envelope.')
        return self

def recipe():
    return dict(version=VERSION,source_video='https://www.youtube.com/watch?v=z97PnFIPoFg',
        metric='prior_centered_squared_counts',score_scale=SCALE,ties='original_proposal_ordinal',
        filter_policy='independent_applicable_groups',public_fields=list(Strategy.model_fields),
        domains=DOMAINS,dial_rules=published_rules(),scope='Published equities adaptation. Exact host metric, private grid and named recipes are unknown. A configured40000 target is not an executed source-scale pool.')

def published_rules():
    rules={field:dict(mode='draw',values=DOMAINS[field]) for field in
        ['direction','swing_strength','level_tolerance','level_age','entry','stop_kind','stop_buffer','target','structure_exit','max_hold']}
    rules.update(family=dict(mode='stratum',values=list(FAMILIES)),timeframe=dict(mode='draw',values=list(TIMEFRAMES),restriction='Frozen selected chart subset'),
        trigger_timeframe=dict(mode='conditional',by_setup={tf:triggers(tf) for tf in TIMEFRAMES}),
        confirmation=dict(mode='conditional',when_lower_trigger=DOMAINS['confirmation'],otherwise=DOMAINS['confirmation'][:-1]),
        confirmation_window=dict(mode='conditional',values=DOMAINS['confirmation_window'],requires=dict(confirmation_not='none'),inactive=3),
        limit_expiry=dict(mode='conditional',values=DOMAINS['limit_expiry'],requires=dict(entry='limit'),inactive=3),
        stop_reference=dict(mode='conditional',by_family={family:DOMAINS['stop_reference'] if family=='fair_value_gap' else DOMAINS['stop_reference'][:-1] for family in FAMILIES}),
        flat_at_close=dict(mode='conditional',by_setup={tf:[False] if tf in {'4h','1d'} else [False,True] for tf in TIMEFRAMES}),
        trend_filter=dict(mode='draw',values=['none','setup','higher','daily']),session_filter=dict(mode='draw',values=['core','open']),
        news=dict(mode='conditional',when_enabled=['trade','skip','half'],when_disabled=['trade']),
        skip_run_days=dict(mode='draw',values=[0,3,5]),skip_choppy=dict(mode='draw',values=[False,True]))
    for field in ['fresh_breakout','gap_confluence']:
        families={'breakout','break_of_structure','change_of_character','flip_zone'} if field=='fresh_breakout' else APPLICABILITY[field]
        rules[field]=dict(mode='conditional',values=[False,True],families=[f for f in FAMILIES if f in families],inactive=False)
    for field in ['min_touches','level_shape','retest_window','impulse_bars','impulse_atr','sweep_required']:
        families=['change_of_character'] if field=='sweep_required' else [f for f in FAMILIES if f in APPLICABILITY[field]]
        rules[field]=dict(mode='conditional',values=DOMAINS[field],families=families,inactive=Strategy.model_fields[field].default)
    for field in ['sweep_depth','reclaim_bars']:
        rules[field]=dict(mode='conditional',values=DOMAINS[field],requires=dict(family_sweep_or_enabled_choch=True),inactive=Strategy.model_fields[field].default)
    for index,field in enumerate(['pullback_min','pullback_max']):
        rules[field]=dict(mode='conditional',values=[v[index] for v in DOMAINS['pullback_ranges']],families=['trend_pullback'],
            paired_values=[list(v) for v in DOMAINS['pullback_ranges']],inactive=Strategy.model_fields[field].default)
    if set(rules)!=set(Strategy.model_fields):raise SpreadError('Spread recipe must explicitly account for every public Strategy field.')
    return rules

def triggers(timeframe):
    frames=list(TIMEFRAMES);index=frames.index(timeframe)
    return ['1h'] if timeframe=='1d' else frames[max(0,index-2):index+1]

def specifications(value,settings):
    """Parent-first iterator; drawing updates value before the next yield."""
    yield 'timeframe',{},settings.timeframes
    tf=value['timeframe'];family=value['family']
    yield 'trigger_timeframe',dict(timeframe=tf),triggers(tf)
    lower=list(TIMEFRAMES).index(value['trigger_timeframe'])<list(TIMEFRAMES).index(tf)
    for key in ['direction','swing_strength','level_tolerance','level_age']:
        yield key,{},DOMAINS[key]
    yield 'confirmation',dict(lower_trigger=lower),DOMAINS['confirmation'] if lower else DOMAINS['confirmation'][:-1]
    if value['confirmation']!='none':yield 'confirmation_window',dict(confirmation=value['confirmation']),DOMAINS['confirmation_window']
    yield 'entry',{},DOMAINS['entry']
    if value['entry']=='limit':yield 'limit_expiry',dict(entry='limit'),DOMAINS['limit_expiry']
    yield 'stop_reference',{},DOMAINS['stop_reference'] if family=='fair_value_gap' else DOMAINS['stop_reference'][:-1]
    for key in ['stop_kind','stop_buffer','target','structure_exit','max_hold']:
        yield key,{},DOMAINS[key]
    yield 'flat_at_close',dict(timeframe=tf),[False] if tf in {'4h','1d'} else [False,True]
    for key,values in [('trend_filter',['none','setup','higher','daily']),('session_filter',['core','open']),
                       ('news',['trade','skip','half'] if settings.include_news else ['trade']),
                       ('skip_run_days',[0,3,5]),('skip_choppy',[False,True])]:
        yield key,{},values
    if family in {'breakout','break_of_structure','change_of_character','flip_zone'}:
        yield 'fresh_breakout',{},[False,True]
    if family in APPLICABILITY['gap_confluence']:yield 'gap_confluence',{},[False,True]
    if family in {'level_bounce','breakout','flip_zone'}:
        for key in ['min_touches','level_shape']:yield key,{},DOMAINS[key]
    if family=='flip_zone':yield 'retest_window',{},DOMAINS['retest_window']
    if family=='trend_pullback':yield '_pullback_pair',{},DOMAINS['pullback_ranges']
    if family=='supply_demand':
        for key in ['impulse_bars','impulse_atr']:yield key,{},DOMAINS[key]
    if family=='change_of_character':yield 'sweep_required',{},DOMAINS['sweep_required']
    if family=='sweep_reclaim' or value['sweep_required']:
        for key in ['sweep_depth','reclaim_bars']:
            yield key,dict(sweep_required=True) if family=='change_of_character' else {},DOMAINS[key]

def draw(settings,family,batch,ordinal):
    if family not in settings.families or type(batch) is not int or batch<0 or type(ordinal) is not int or not 0<=ordinal<400:
        raise SpreadError('Invalid prespecified proposal coordinate.')
    key=identity(dict(version=VERSION,seed=settings.seed,family=family,batch=batch,ordinal=ordinal))
    rng=np.random.default_rng(int(key[:32],16));value=Strategy(family=family,timeframe=settings.timeframes[0]).model_dump()
    for field,context,values in specifications(value,settings):
        chosen=values[int(rng.integers(len(values)))]
        if field=='_pullback_pair':value['pullback_min'],value['pullback_max']=chosen
        else:value[field]=chosen
    return Strategy(**value).model_dump()

def describe(value,settings):
    result=[]
    for field,context,values in specifications(value,settings):
        if field=='_pullback_pair':
            for index,name in enumerate(['pullback_min','pullback_max']):
                result.append(dict(field=name,context=context,values=[v[index] for v in values],value=value[name]))
        else:result.append(dict(field=field,context=context,values=list(values),value=value[field]))
    return result

def group_key(group):return group['field'],canonical(group['context']),canonical(group['values'])

class Balance:
    def __init__(self,settings,family):
        self.settings=settings;self.family=family;self.cells={}
        # Enumerate every conditional parent context before any observations.
        for tf in settings.timeframes:
            for trigger in triggers(tf):
                lower=list(TIMEFRAMES).index(trigger)<list(TIMEFRAMES).index(tf)
                confirmations=DOMAINS['confirmation'] if lower else DOMAINS['confirmation'][:-1]
                for confirmation,entry,sweep in product(confirmations,DOMAINS['entry'],[False,True] if family=='change_of_character' else [False]):
                    value=Strategy(family=family,timeframe=tf,trigger_timeframe=trigger,confirmation=confirmation,entry=entry,sweep_required=sweep).model_dump()
                    for g in describe(value,settings):self.cells.setdefault(group_key(g),dict(field=g['field'],context=g['context'],values=g['values'],counts=[0]*len(g['values'])))

    def delta(self,value):
        total=0
        for g in describe(value,self.settings):
            cell=self.cells[group_key(g)];counts=cell['counts'];k=len(counts)
            if k>1:total+=(2*SCALE//(k-1))*(k*counts[g['values'].index(g['value'])]-sum(counts))
        return total

    def accept(self,value):
        if value['family']!=self.family:raise SpreadError('Balance belongs to a different setup family.')
        for g in describe(value,self.settings):self.cells[group_key(g)]['counts'][g['values'].index(g['value'])]+=1

    def rank(self,values):return sorted(range(len(values)),key=lambda i:(self.delta(values[i]),i))

    def score(self):
        result=0
        for cell in self.cells.values():
            counts=cell['counts'];k=len(counts);n=sum(counts)
            if k>1:result+=SCALE//(k-1)*(k*sum(c*c for c in counts)-n*n)-SCALE*n
        return result

    def groups(self):
        result=[]
        for key in sorted(self.cells):
            c=self.cells[key];n=sum(c['counts'])
            result.append(dict(field=c['field'],context=c['context'],values=c['values'].copy(),counts=c['counts'].copy(),
                exposures=n,shares=[count/n for count in c['counts']] if n else None,target_share_numerator=1,target_share_denominator=len(c['values'])))
        return result

def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):digest.update(chunk)
    return digest.hexdigest()

class ProposalPlan:
    def __init__(self,folder,manifest):
        self.folder=Path(folder);self.manifest=manifest;self.plan_id=identity(manifest)

    @classmethod
    def open(cls,folder,expected_plan_id):
        if not isinstance(expected_plan_id,str) or not re.fullmatch('[a-f0-9]{64}',expected_plan_id):
            raise SpreadError('Reopening requires the externally frozen proposal identity.')
        try:manifest=json.loads((Path(folder)/'manifest.json').read_text(encoding='utf-8'))
        except (OSError,ValueError) as error:raise SpreadError('Frozen proposal manifest is unavailable.') from error
        plan=cls(folder,manifest)
        if plan.plan_id!=expected_plan_id:raise SpreadError('Proposal identity differs from the external frozen anchor.')
        plan.verify();return plan

    def verify(self):
        require_current_source()
        try:
            disk=json.loads((self.folder/'manifest.json').read_text(encoding='utf-8'))
            if identity(disk)!=self.plan_id or identity(self.manifest)!=self.plan_id:raise SpreadError('Frozen proposal manifest changed.')
            if disk['core_hash']!=core_hash() or disk['recipe_hash']!=identity(recipe()):raise SpreadError('Frozen spread source or recipe differs.')
            settings=SpreadSettings(**disk['settings'])
            if disk['planned_proposals']!=len(settings.families)*settings.max_batches_per_family*settings.batch_size:raise SpreadError('Frozen proposal budget changed.')
            expected={'manifest.json',*[f+'.jsonl.gz' for f in settings.families]}
            if {p.name for p in self.folder.iterdir()}!=expected:raise SpreadError('Missing or unplanned proposal file.')
            if set(disk['files'])!=set(settings.families):raise SpreadError('Frozen proposal family inventory changed.')
            for family,record in disk['files'].items():
                path=self.folder/(family+'.jsonl.gz')
                if path.is_symlink() or path.stat().st_size!=record['bytes'] or file_hash(path)!=record['sha256']:raise SpreadError('Frozen proposal file changed.')
        except SpreadError:raise
        except (OSError,KeyError,ValueError,TypeError) as error:raise SpreadError('Frozen proposal plan is invalid or unavailable.') from error
        return settings

    def batches(self,family):
        settings=SpreadSettings(**self.manifest['settings']);path=self.folder/(family+'.jsonl.gz')
        try:
            with gzip.open(path,'rt',encoding='utf-8') as stream:
                for batch in range(settings.max_batches_per_family):
                    raw=stream.readline()
                    if not raw:raise SpreadError('Frozen proposal file ended early.')
                    row=json.loads(raw)
                    if row['family']!=family or row['batch']!=batch or len(row['configurations'])!=settings.batch_size:raise SpreadError('Frozen proposal batch inventory changed.')
                    for value in row['configurations']:
                        cfg=Strategy(**value)
                        if cfg.family!=family or cfg.timeframe not in settings.timeframes or canonical(cfg)!=canonical(value):raise SpreadError('Frozen proposal is not a complete supported configuration.')
                    yield row['configurations']
                if stream.read(1):raise SpreadError('Frozen proposal file contains extra batches.')
        except SpreadError:raise
        except (OSError,KeyError,ValueError,TypeError) as error:raise SpreadError('Frozen proposal batches are malformed.') from error

def freeze_plan(folder,settings,cancel=None):
    require_current_source();folder=Path(folder);folder.mkdir(parents=True,exist_ok=False);files={}
    for family in settings.families:
        path=folder/(family+'.jsonl.gz');temporary=path.with_suffix('.tmp')
        with temporary.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
            for batch in range(settings.max_batches_per_family):
                if cancel and cancel():raise InterruptedError('Proposal freezing canceled before any signal probe.')
                configurations=[draw(settings,family,batch,ordinal) for ordinal in range(settings.batch_size)]
                zipped.write((canonical(dict(family=family,batch=batch,configurations=configurations))+'\n').encode())
        temporary.replace(path);files[family]=dict(bytes=path.stat().st_size,sha256=file_hash(path))
    manifest=dict(version=VERSION,settings=settings.model_dump(),core_hash=core_hash(),recipe=recipe(),recipe_hash=identity(recipe()),
        planned_proposals=len(settings.families)*settings.max_batches_per_family*settings.batch_size,files=files)
    atomic_json(folder/'manifest.json',manifest);plan=ProposalPlan(folder,manifest);plan.verify();return plan

def validated_context(context):
    from datetime import date
    try:
        required={'dataset_id','dataset_manifest_hash','primary_symbol','start','end'}
        news={'news_calendar_id','news_calendar_hash'}
        if set(context) not in (required,required|news):raise ValueError()
        if not re.fullmatch('[a-f0-9]{24}',context['dataset_id']) or not re.fullmatch('[a-f0-9]{64}',context['dataset_manifest_hash']):raise ValueError()
        if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',context['primary_symbol']):raise ValueError()
        for k in ['start','end']:
            if date.fromisoformat(context[k]).isoformat()!=context[k]:raise ValueError()
        if context['start']>context['end']:raise ValueError()
        for field in news&set(context):
            if not isinstance(context[field],str) or not re.fullmatch('[a-f0-9]{64}',context[field]):raise ValueError()
    except (ValueError,TypeError,KeyError):raise SpreadError('Spread requires an exact frozen primary dataset/instrument/date context.') from None
    return json.loads(canonical(context))

class ReplayPrefix:
    """One-event lookahead; never materialize an unbounded journal iterator."""
    def __init__(self,events):self.iterator=iter(events);self.empty=object();self.cached=self.empty;self.finished=False
    def peek(self):
        if self.finished:return None
        if self.cached is self.empty:
            try:self.cached=next(self.iterator)
            except StopIteration:self.finished=True;return None
            if not isinstance(self.cached,dict):raise SpreadError('Replay events must be structured original records.')
        return self.cached
    def consume(self):self.cached=self.empty

def select(plan,context,probe,record,*,authorize,cancel=None,replay=(),verify_evidence=None):
    """Caller must supply verified original replay events and durable record()."""
    settings=plan.verify();context=validated_context(context)
    if settings.include_news!=('news_calendar_id' in context):raise SpreadError('Frozen spread news inclusion and calendar identity/hash must agree.')
    prior=ReplayPrefix(replay);prior.peek();new_events=0
    selected=[];known={};duplicates=0;computations=0;reused=0;attempts=0;visited=0;unprobed=0;groups=[];exhausted=[]
    def access():
        require_current_source()
        if cancel and cancel():raise InterruptedError('Spread selection canceled before a probe or reused decision.')
        authorize()
    def emit(event):
        nonlocal new_events
        # Copy caller-owned objects so subsequent edits cannot alter committed events.
        event=json.loads(canonical(event))
        if prior.peek() is not None:
            if prior.peek()!=event:raise SpreadError('Saved spread replay prefix differs from the frozen computation.')
            prior.consume()
        else:record(event);new_events+=1
    def validate_answer(answer):
        if not isinstance(answer,dict) or set(answer)!={'signal_count','evidence_sha256'} or type(answer['signal_count']) is not int or answer['signal_count']<0 or not isinstance(answer['evidence_sha256'],str) or not re.fullmatch('[a-f0-9]{64}',answer['evidence_sha256']):
            raise SpreadError('Signal probe requires a nonnegative integer count and full saved evidence hash.')
    def qualified_probe(coordinate,value):
        nonlocal attempts,computations,reused
        emit(dict(kind='probe_planned',**coordinate));ordinal=0
        # A start without a committed result is an interrupted attempt. Retain
        # it and start a distinct ordinal before any recomputation.
        while prior.peek() is not None:
            if prior.peek().get('kind')!='probe_started':raise SpreadError('Saved probe attempt prefix is inconsistent.')
            ordinal+=1;attempts+=1;emit(dict(kind='probe_started',**coordinate,attempt=ordinal))
            if prior.peek() is not None and prior.peek().get('kind')=='probe_completed':
                answer=prior.peek().get('evidence');validate_answer(answer)
                emit(dict(kind='probe_completed',**coordinate,attempt=ordinal,evidence=answer))
                if verify_evidence is not None:verify_evidence(coordinate,answer)
                reused+=1;return answer
            if prior.peek() is not None and prior.peek().get('kind')!='probe_started':raise SpreadError('An unfinished probe has an invalid replay successor.')
        access();ordinal+=1;attempts+=1;emit(dict(kind='probe_started',**coordinate,attempt=ordinal))
        answer=probe(json.loads(canonical(value)));computations+=1;validate_answer(answer)
        access();emit(dict(kind='probe_completed',**coordinate,attempt=ordinal,evidence=answer));return answer
    access();emit(dict(kind='selection_started',plan_id=plan.plan_id,context=context))
    for family in settings.families:
        balance=Balance(settings,family);accepted=0
        for batch,values in enumerate(plan.batches(family)):
            access();emit(dict(kind='batch_started',family=family,batch=batch,configuration_hash=identity(values)))
            classified={};unique={}
            for ordinal,value in enumerate(values):
                cid=identity(value)
                if cid in known or cid in unique:classified[ordinal]='duplicate';duplicates+=1
                else:unique[cid]=ordinal
            winner=None
            for ordinal in balance.rank(values):
                if ordinal in classified:continue
                value=values[ordinal];cid=identity(value);access()
                coordinate=dict(family=family,batch=batch,ordinal=ordinal,config_id=cid)
                answer=qualified_probe(coordinate,value);known[cid]=answer
                if answer['signal_count']<settings.minimum_signals:classified[ordinal]='insufficient_signals';continue
                classified[ordinal]='selected';winner=ordinal;balance.accept(value);selected.append(value);accepted+=1
                emit(dict(kind='version_selected',**coordinate,signal_count=answer['signal_count'],score=balance.score(),configuration=value));break
            outcomes=[]
            for ordinal,value in enumerate(values):
                status=classified.get(ordinal,'not_probed');unprobed+=status=='not_probed'
                outcomes.append(dict(ordinal=ordinal,config_id=identity(value),status=status))
            visited+=len(values);emit(dict(kind='batch_finished',family=family,batch=batch,outcomes=outcomes,selected_ordinal=winner))
            if accepted==settings.per_family:break
        if accepted!=settings.per_family:exhausted.append(family)
        groups.append(dict(family=family,selected=accepted,score=balance.score(),groups=balance.groups()))
    access();plan.verify();complete=not exhausted
    selection_manifest=dict(plan_id=plan.plan_id,context=context,configurations=selected,minimum_signals=settings.minimum_signals) if complete else None
    selection_hash=identity(selection_manifest) if complete else None
    emit(dict(kind='selection_finished',complete=complete,selected_count=len(selected),selection_manifest_hash=selection_hash,exhausted_families=exhausted))
    if prior.peek() is not None:raise SpreadError('Saved spread replay contains an unconsumed suffix.')
    return dict(complete=complete,selected=selected,selection_manifest=selection_manifest,selection_manifest_hash=selection_hash,
        planned_proposals=plan.manifest['planned_proposals'],visited_proposals=visited,unused_frozen_proposals=plan.manifest['planned_proposals']-visited,
        unprobed_proposals=unprobed,duplicate_proposals=duplicates,probe_computations=computations,reused_probes=reused,total_probe_attempts=attempts,
        exhausted_families=exhausted,family_balance=groups,new_events=new_events,
        scope='Spread signal qualification only; selected-account P&L, durable worker/API/UI integration and full source-scale verification remain separate.')
