"""Real frozen joint-account screening/final fixtures; no fabricated passing metrics."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
import json
import pandas as pd
import pytest
from pydantic import ValidationError
from conftest import minute_frame
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import save_dataset,normalize,prepare,load_window
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.service import Lab
from backend.lab.worker import Worker
from verification.reference_execution import execute
from verification.strategy_fixtures import SPEC
from test_reference_execution import primitive,assert_parity

DAYS=['2026-10-05','2026-10-06','2026-10-07','2026-10-08','2026-10-09','2026-10-12']
CONFIGS=[Strategy(family='break_of_structure',timeframe='1m',direction='long',swing_strength=2,
    stop_reference='level',stop_buffer=0,max_hold=0,target=t) for t in ['4R','5R']]
ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=10000,risk_fraction=.1,symbol_exposure=1,total_exposure=1,participation=1)


@pytest.fixture
def study_data(tmp_path):
    frames=[]
    for day in DAYS:
        frame=minute_frame(day)
        for i,value in enumerate(SPEC['common_closes']):
            close=Decimal(str(value));frame.loc[i,['open','high','low','close']]=[float(close-Decimal('.02')),float(close+Decimal('.1')),float(close-Decimal('.1')),float(close)]
        frame.loc[21:,['open','high','low','close']]=[199.98,200.1,199.9,200.]
        frames.append(frame)
    raw=pd.concat(frames,ignore_index=True);lab=Lab(tmp_path)
    manifest=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Authored portfolio study geometry; every session complete'},start=DAYS[0],end=DAYS[-1])
    return lab,manifest,raw


def request(manifest,mode='portfolio',configs=None):
    return Study(name='Frozen whole portfolio',dataset_id=manifest['id'],study_mode=mode,
        discovery={'start':DAYS[0],'end':DAYS[1]},validation={'start':DAYS[2],'end':DAYS[3]},
        holdout={'start':DAYS[4],'end':DAYS[5]},configurations=[c.model_copy(deep=True) for c in (CONFIGS if configs is None else configs)],
        costs=ZERO,portfolio=ACCOUNT,minimum_trades=1,minimum_sharpe=0)


def run(lab,job):
    assert Worker(lab).run_once()
    state=lab.store.job(job['id']);assert state['status']=='completed',state['error']
    return lab.result(job['id'])


def reference(lab,report):
    context=report['study_context'];sid=context['study_id'];study=lab.guard.study(sid)
    phase='holdout' if context['phase']=='final' else context['phase']
    assert {'start':report['start'],'end':report['end']}==study['spec'][phase]
    assert [c['config'] for c in report['configurations']]==study['spec']['configurations']
    assert report['config_id']==context['selection_unit_id']
    lab.guard.access(['SPY'],report['start'],report['end'],'portfolio_study_independent_reference',sid,
        study['spec'].get('final_job_id') if context['phase']=='final' else None)
    frame,_=load_window(lab.datasets_root,report['dataset_id'],report['start'],report['end'])
    actual=prepare(normalize(frame)[0]);configs={r['config_id']:r['config'] for r in report['configurations']}
    expected=execute(primitive(actual),report['signals'],configs,report['costs'],report['portfolio'],start=report['start'],end=report['end'])
    assert_parity(SimpleNamespace(**report),expected)
    assert report['config_id']==identity([c['config'] for c in report['configurations']])
    assert sum(r['trades'] for r in report['attribution'])==len(expected['trades'])
    assert sum(r['closed_trade_net_profit'] for r in report['attribution'])==pytest.approx(report['metrics']['net_profit'],abs=1e-7)
    return expected


def test_explicit_mode_and_canonical_set_are_frozen_at_registration(study_data):
    lab,m,_=study_data;value=request(m,configs=list(reversed(CONFIGS)));before=value.model_dump(mode='json')
    study=lab.register_study(value);spec=study['spec']
    assert spec['study_mode']=='portfolio'
    assert spec['configurations']==sorted(before['configurations'],key=identity)
    assert identity(spec)==lab.store.events(study['id'])[0]['details']['spec_hash']
    value.configurations[0].target='2R';assert lab.guard.study(study['id'])['spec']==spec


def test_default_independent_mode_retains_distinct_selection_unit(study_data):
    _,m,_=study_data;body=request(m,mode='independent').model_dump();body.pop('study_mode')
    assert Study(**body).study_mode=='independent'
    for mode in ['shared','',None,True]:
        with pytest.raises(ValidationError):Study(**(body|dict(study_mode=mode)))
    with pytest.raises(ValidationError):request(m,configs=CONFIGS+[CONFIGS[0]])
    many=[Strategy(level_age=i+2) for i in range(65)]
    with pytest.raises(ValidationError):request(m,configs=many)
    assert len(request(m,mode='independent',configs=many).configurations)==65


def test_real_joint_screening_and_final_match_independent_accounts(study_data):
    lab,m,_=study_data;study=lab.register_study(request(m));sid=study['id'];screen=lab.screen(sid)
    planned=lab.store.registry(job_id=screen['id']);assert planned['totals']['planned_occurrences']==2
    assert planned['totals']['roles']=={'portfolio':dict(occurrences=2,distinct_configurations=1)}
    screened=run(lab,screen);assert screened['study_mode']=='portfolio' and screened['count']==1
    frozen=lab.guard.study(sid);assert frozen['status']=='screened'
    assert frozen['spec']['candidates']==[frozen['spec']['configurations']]
    for window in ['discovery','validation']:
        report=lab.report(screen['id'],0,window);assert report['report_type']=='shared_capital_portfolio'
        assert report['metrics']['trades']>=1 and report['metrics']['net_profit']>0 and report['metrics']['marked_sharpe'] is not None
        assert report['study_context']['phase']==window;reference(lab,report)
    final=lab.final(sid);assert lab.store.registry(job_id=final['id'])['totals']['roles']=={'portfolio':dict(occurrences=1,distinct_configurations=1)}
    result=run(lab,final);assert result['count']==1 and result['study_mode']=='portfolio'
    report=lab.report(final['id'],0);assert report['study_context']['phase']=='final'
    assert report['study_context']['candidate_hash']==frozen['spec']['candidate_hash'];reference(lab,report)
    assert lab.guard.study(sid)['status']=='final_complete'
    assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
    with pytest.raises(ResearchError):lab.final(sid)
    with pytest.raises(ResearchError):lab.evaluate_portfolio(m['id'],CONFIGS,ZERO,ACCOUNT,DAYS[4],DAYS[5])


@pytest.mark.parametrize('fault',['membership','costs','account','window','mode'])
def test_registered_inputs_cannot_be_rewritten_then_refrozen(study_data,monkeypatch,fault):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];spec=lab.guard.study(sid)['spec']
    if fault=='membership':spec['configurations']=spec['configurations'][:1]
    elif fault=='costs':spec['costs']['slippage_bps']=9
    elif fault=='account':spec['portfolio']['capital']+=1
    elif fault=='window':spec['validation']['start']=DAYS[1]
    else:spec['study_mode']='independent'
    with lab.store.db() as db:db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(spec),sid))
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Amended frozen study read raw prices.'))
    with pytest.raises(ResearchError):lab.screen(sid)
    assert lab.store.jobs()==[]


def test_portfolio_candidate_cannot_drop_a_member_even_with_a_fresh_candidate_hash(study_data):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];spec=lab.guard.study(sid)['spec']
    with pytest.raises(ResearchError):lab.guard.screened(sid,'not-complete-joint-evidence',[spec['configurations'][:1]])
    assert lab.guard.study(sid)['status']=='registered'


@pytest.mark.parametrize('kind',['flat','losing','weak_target'])
def test_real_no_candidate_outcomes_do_not_unlock_final(study_data,kind):
    lab,m,raw=study_data;configs=CONFIGS
    if kind=='weak_target':configs=[c.model_copy(update={'target':t}) for c,t in zip(CONFIGS,['1R','5R'])]
    else:
        if kind=='flat':raw[['open','high','low','close']]=[100,100.1,99.9,100]
        else:
            for day in DAYS:
                mask=(raw.timestamp.dt.date.astype(str)==day)&(raw.timestamp.dt.hour*60+raw.timestamp.dt.minute>=13*60+51)
                raw.loc[mask,['open','high','low','close']]=[96,96.1,95.9,96]
        m=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Explicit '+kind+' portfolio study control'},start=DAYS[0],end=DAYS[-1])
    sid=lab.register_study(request(m,configs=configs))['id'];job=lab.screen(sid);result=run(lab,job)
    assert result['count']==1 and result['candidates']==[] and lab.guard.study(sid)['status']=='no_candidates'
    accounts=[lab.report(job['id'],0,w) for w in ['discovery','validation']]
    for account in accounts:reference(lab,account)
    if kind=='flat':assert all(r['metrics']['trades']==0 for r in accounts)
    else:assert any(r['metrics']['net_profit']<0 for r in accounts)
    with pytest.raises(ResearchError):lab.final(sid)
    assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']


def test_final_job_reservation_survives_cancel_before_any_consumption(study_data):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];run(lab,lab.screen(sid))
    first=lab.final(sid);lab.store.cancel(first['id'])
    assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
    with pytest.raises((ResearchError,ValueError),match='already|reserved'):lab.final(sid)
    lab.store.resume(first['id']);run(lab,lab.store.job(first['id']))
    assert lab.guard.study(sid)['spec']['final_job_id']==first['id']
    assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
