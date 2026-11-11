"""Freeze complete research axes and both protected final instruments before accounts."""
from typing import Literal
from pydantic import Field,model_validator
from .config import Contract,Strategy,identity
from .models import Search,SearchSampling
from .data import read_manifest
from .dataset_context import freeze_context
from .research import ResearchError,require_current_source
from .research_funnel import FunnelStudy,freeze_specification
from .research_qualification import STABILITY_POLICY,CONTROL_SCHEDULING_POLICY


class FunnelGeneration(Contract):
    mode:Literal['common_grid','common_random']='common_random'
    count:int=Field(100,strict=True,ge=1,le=100000)
    families:list[str]=Field(default_factory=lambda:['change_of_character'],min_length=1,max_length=10)
    timeframes:list[str]=Field(default_factory=lambda:['1h','1d'],min_length=1,max_length=6)
    include_news:bool=Field(False,strict=True)

    @model_validator(mode='after')
    def valid_axes(self):
        from .sampling import canonical_axes
        # Input validation errors belong to the public422 boundary, before any
        # registration or dataset access. The sampler retains canonical order.
        try:canonical_axes(self.families,self.timeframes)
        except ValueError as error:raise ValueError(str(error)) from error
        return self


class FunnelContinuation(Contract):
    """All settings come from the original registration; no overrides."""
    pass


class GeneratedFunnel(FunnelStudy):
    """Validate study axes before generating its real, price-free cohort.

    The inherited chronology validator accepts the internal empty list. It is
    never registered: generation produces a normal, nonempty FunnelStudy, which
    validates the complete unique cohort and news requirements again.
    """
    configurations:list[Strategy]=Field(default_factory=list,max_length=0,exclude=True)
    generation:FunnelGeneration=Field(default_factory=FunnelGeneration)

    @model_validator(mode='before')
    @classmethod
    def no_supplied_cohort(cls,value):
        if isinstance(value,dict) and 'configurations' in value:
            raise ValueError('Use explicit funnel registration for supplied configurations; generated cohorts take only generation settings.')
        return value

    @model_validator(mode='after')
    def generated_news_calendar(self):
        if self.generation.include_news and self.news_calendar_id is None:
            raise ValueError('News-filter variants require a versioned news calendar before cohort generation.')
        return self


def register_generated_funnel(lab,request):
    from .service import sample_configurations
    require_current_source()
    if not isinstance(request,GeneratedFunnel):raise ResearchError('Use validated generated-cohort registration settings.')
    # Detach caller-owned mutable values before sampling or original registration.
    request=GeneratedFunnel(**request.model_dump(mode='json'))
    settings=request.generation
    policy=SearchSampling(mode=settings.mode,include_news=settings.include_news,
        minimum_signals=request.minimum_signals,minimum_trades=request.minimum_trades,minimum_sharpe=request.minimum_sharpe)
    search=Search(dataset_id=request.dataset_id,start=request.discovery.start,end=request.discovery.end,
        seed=request.seed,count=settings.count,families=settings.families,timeframes=settings.timeframes,
        sampling_policy=policy,news_calendar_id=request.news_calendar_id,costs=request.costs,portfolio=request.portfolio)
    configurations,sampling=sample_configurations(search)
    study=FunnelStudy(**(request.model_dump(mode='json',exclude={'generation'})|dict(configurations=configurations)))
    provenance=dict(settings=settings.model_dump(mode='json'),sampling=sampling,
        configuration_universe_hash=identity([c.model_dump(mode='json') for c in study.configurations]),
        price_or_outcome_dependent=False,host_private_recipe_reproduced=False)
    return register_funnel(lab,study,cohort_generation=provenance)


def prepare_registration(lab,request,*,cohort_generation=None):
    require_current_source()
    if not isinstance(request,FunnelStudy):
        raise ResearchError('Use the complete research-funnel registration contract.')
    request=FunnelStudy(**request.model_dump(mode='json'))
    primary=read_manifest(lab.datasets_root,request.dataset_id)
    replica=read_manifest(lab.datasets_root,request.replication_dataset_id or request.dataset_id)
    start=str(request.discovery.start);end=str(request.holdout.end)
    contexts={}
    for name,manifest,symbol in [('primary',primary,request.primary_symbol),('replica',replica,request.replication_symbol)]:
        if symbol not in manifest['quality']['symbols']:
            raise ResearchError('The declared '+name+' instrument is absent from its original dataset.')
        lab._validate_window(manifest,start,end)
        lab.borrow_input(manifest['id'],request.costs,start,end,symbols=[symbol])
        contexts[name]=freeze_context(manifest)
    frozen=freeze_specification(request)
    universe=[configuration.model_dump(mode='json') for configuration in request.configurations]
    universe_hash=identity(universe)
    if cohort_generation is not None:
        if (cohort_generation.get('configuration_universe_hash')!=universe_hash
            or cohort_generation.get('price_or_outcome_dependent') is not False
            or cohort_generation.get('host_private_recipe_reproduced') is not False):
            raise ResearchError('Generated cohort provenance must bind the complete original universe before outcomes.')
        frozen['cohort_generation']=cohort_generation
    def arm(context,symbol,window,role,*,final=False):
        return dict(dataset_context=contexts[context],symbol=symbol,start=str(window.start),end=str(window.end),role=role,
            configuration_universe_hash=universe_hash,configuration_count=len(universe),
            configuration_scope='all_frozen_versions_with_candidate_and_family_flags' if final else 'all_frozen_versions')
    development=dict(
        primary_discovery=arm('primary',request.primary_symbol,request.discovery,'primary_discovery'),
        era_one=arm('primary',request.primary_symbol,request.era_one,'primary_discovery_era_one'),
        era_two=arm('primary',request.primary_symbol,request.era_two,'primary_discovery_era_two'),
        instrument_replication=arm('replica',request.replication_symbol,request.discovery,'instrument_discovery_replication_not_untouched_validation'),
        chronological_validation=arm('primary',request.primary_symbol,request.validation,'later_primary_chronological_validation'))
    final=dict(primary_final=arm('primary',request.primary_symbol,request.holdout,'protected_final_all_versions',final=True),
        replication_final=arm('replica',request.replication_symbol,request.holdout,'protected_final_all_versions',final=True))
    frozen.update(replication_dataset_id=replica['id'],dataset_context=contexts['primary'],replication_dataset_context=contexts['replica'],
        stability_policy=STABILITY_POLICY.copy(),control_scheduling_policy=CONTROL_SCHEDULING_POLICY.copy(),
        configuration_universe_hash=universe_hash,development_arms=development,final_arms=final,
        qualification_policy=dict(discovery=dict(minimum_signals=request.minimum_signals,minimum_trades=request.minimum_trades,positive_net_profit=True,minimum_sharpe=request.minimum_sharpe),
            eras=dict(positive_net_profit_each_era=True),replication=dict(positive_net_profit=True,minimum_sharpe=request.replication_minimum_sharpe),
            chronological_validation=dict(minimum_trades=request.minimum_trades,positive_net_profit=True,minimum_sharpe=request.minimum_sharpe,source_role='Additional prespecified chronological validation adaptation'),
            matched_entries=dict(sets_per_interpretation=10000,strict_fraction_below=.05,require_both_declared_interpretations=True),
            family=dict(all_versions_equal_weight=True,positive_annualized_profit=True,minimum_sharpe=request.family_minimum_sharpe,positive_profit_in_both_eras=True),
            final_version=dict(positive_net_profit=True,minimum_sharpe=.5)),
        source_thresholds_unmodified=(request.minimum_signals==40 and request.minimum_trades==30 and request.minimum_sharpe==.5 and request.replication_minimum_sharpe==.3 and request.family_minimum_sharpe==.5),
        instrument_replication_adaptation='US-stock/ETF replication; not the host ES futures market',
        host_engine_parity_verified=False,registration_contains_outcomes=False,
        final_cohort_policy='All frozen versions on both declared instruments; candidates and families separately identified.')
    frozen.update(lab.freeze_news(frozen,request.configurations,start,end))
    protected=sorted(set(primary['quality']['symbols'])|set(replica['quality']['symbols']))
    return request,primary,frozen,protected


def register_funnel(lab,request,*,cohort_generation=None):
    request,primary,frozen,protected=prepare_registration(lab,request,cohort_generation=cohort_generation)
    return lab.guard.register(request,primary,frozen,protected_symbols=protected)


def workflow_status(lab,sid,*,limit=50,offset=0):
    """Bounded original job/dependency navigation, without computing outcomes."""
    from .research_funnel_arms import _study
    from . import research_funnel_jobs as qualification,research_funnel_final as final
    from .store import StateError
    if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or offset<0:
        raise StateError('Use a bounded workflow dependency page.')
    require_current_source()
    with lab.store.db() as db:
        db.execute('BEGIN');study=_study(lab,db,sid)
        q=qualification._reservation(lab,db,study);f=final._reservation(lab,db,sid)
        ids=[];counts={};total=0
        if q:
            qualification._job(lab,db,q['job_id'])
            total=db.execute('SELECT COUNT(*) FROM funnel_dependencies WHERE parent_id=?',(q['job_id'],)).fetchone()[0]
            counts={r['status']:r['n'] for r in db.execute('SELECT j.status,COUNT(*) n FROM funnel_dependencies d JOIN jobs j ON j.id=d.child_id WHERE d.parent_id=? GROUP BY j.status',(q['job_id'],))}
            ids=[(r['role'],r['child_id']) for r in db.execute('SELECT role,child_id FROM funnel_dependencies WHERE parent_id=? ORDER BY role LIMIT ? OFFSET ?',(q['job_id'],limit,offset))]
        if f:final._job(lab,db,f['job_id'])
        result=dict(study_id=sid,status=study['status'],funnel_version=1,
            source_video=study['spec']['source_video'],version_count=len(study['spec']['configurations']),
            primary_symbol=study['spec']['primary_symbol'],replication_symbol=study['spec']['replication_symbol'],
            registration_source_verified=True,original_job_bindings_verified=True,
            qualification_job_id=q['job_id'] if q else None,final_job_id=f['job_id'] if f else None,
            final_consumed=bool(study['spec'].get('final_job_id')),
            dependencies=dict(total=total,limit=limit,offset=offset,counts=counts))
    result['qualification']=lab.store.job_status(q['job_id']) if q else None
    result['final']=lab.store.job_status(f['job_id']) if f else None
    result['dependencies']['rows']=[dict(role=role,job=lab.store.job_status(jid)) for role,jid in ids]
    return result
