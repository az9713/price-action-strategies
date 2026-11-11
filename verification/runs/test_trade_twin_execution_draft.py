"""Financial twin contracts: full independent Decimal books and hand calculations."""
import ast,copy,importlib,importlib.util,math
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Costs,Portfolio,Strategy
from backend.lab.data import normalize,prepare,Action
from verification.trade_twin_reference import execute_reference

ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=100000,participation=.05)
CFG=Strategy(timeframe='1m',max_hold=0)

def frame(days=('2026-11-04',)):
    data=pd.concat([minute_frame(day,'SPY') for day in days],ignore_index=True)
    data['open']=100.;data['close']=101.;data['high']=101.5;data['low']=99.5;data['volume']=10000.
    return prepare(normalize(data)[0])

def match_for(data,side=1,start=1,end=3,boundary='close'):
    entered=data.iloc[start].timestamp;cutoff=data.iloc[end].timestamp+(pd.Timedelta(minutes=1) if boundary=='close' else pd.Timedelta(0))
    reference=float(data.iloc[start].open)
    return dict(source_id='source-1',symbol='SPY',side=side,quantity=10,candidate_key='SPY|'+entered.isoformat(),
        entry_at=entered.isoformat(),entry_reference=str(reference),atr='1',stop=str(reference-side*2),target=str(reference+side*4),
        holding_minutes=int((cutoff-entered)//pd.Timedelta(minutes=1)),exit_boundary=boundary,cutoff_at=cutoff.isoformat())

def primitive(data):
    return [{k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()} for row in data.to_dict('records')]

def reference(data,match,cfg=CFG,costs=ZERO,account=ACCOUNT,actions=(),policy='barrier_capped_elapsed_v1'):
    return execute_reference(primitive(data),match,cfg.model_dump(mode='json'),costs.model_dump(mode='json'),account.model_dump(mode='json'),[asdict(a) for a in actions],policy)

def parity(actual,expected,path='root'):
    if isinstance(expected,dict):
        assert set(actual)==set(expected),path
        for key in expected:parity(actual[key],expected[key],path+'.'+key)
    elif isinstance(expected,list):
        assert len(actual)==len(expected),path
        for i,(a,b) in enumerate(zip(actual,expected)):parity(a,b,path+f'[{i}]')
    elif isinstance(expected,Decimal):
        assert math.isfinite(actual) and abs(Decimal(str(actual))-expected)<=Decimal('0.0000001'),(path,actual,expected)
    else:assert type(actual) is type(expected) and actual==expected,(path,actual,expected)

def execute(data,match,cfg=CFG,costs=ZERO,account=ACCOUNT,actions=(),policy='barrier_capped_elapsed_v1'):
    module=importlib.import_module('backend.lab.trade_twin_execution')
    expected=reference(data,match,cfg,costs,account,actions,policy)
    actual=module.execute_twin(data,match,cfg,costs,account,actions,policy=policy)
    parity(actual,expected)
    assert abs(actual['accounting_residual'])<=1e-7
    return actual

def test_financial_twin_execution_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_execution') is not None,'Financial twin execution has not been implemented.'

def test_reference_has_no_production_numerical_imports():
    tree=ast.parse((Path(__file__).parents[1]/'verification/trade_twin_reference.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module or '']
            assert all(not name.startswith(('backend','numpy','pandas','verification.reference_execution')) for name in names)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('boundary',['open','close'])
@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
def test_hand_elapsed_accounts(side,boundary,policy):
    data=frame();match=match_for(data,side,boundary=boundary)
    expected=reference(data,match,policy=policy)
    profit=Decimal(side*10 if boundary=='close' else 0)
    assert expected['trade']['net_pnl']==profit
    assert expected['final_cash']==Decimal(100000)+profit
    assert expected['trade']['exit_at']==match['cutoff_at'] and expected['status']=='complete'
    assert expected['accounting_residual']==0
    execute(data,match,policy=policy)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('kind',['stop','target_touch','target_through','ambiguous','gap_stop','gap_target','close_stop'])
@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
def test_barrier_precedence_and_diagnostic_encounters(side,kind,policy):
    data=frame();match=match_for(data,side,end=5);cfg=CFG
    stop=float(match['stop']);target=float(match['target'])
    if kind in {'stop','ambiguous'}:data.loc[2,'low' if side==1 else 'high']=stop
    if kind in {'target_touch','target_through','ambiguous'}:data.loc[2,'high' if side==1 else 'low']=target+(side*.01 if kind!='target_touch' else 0)
    if kind in {'gap_stop','gap_target'}:
        value=stop-side if kind=='gap_stop' else target+side
        data.loc[2,['open','high','low','close']]=[value,value+.1,value-.1,value]
    if kind=='close_stop':
        cfg=CFG.model_copy(update=dict(stop_kind='close'));value=stop-side*.5
        data.loc[2,['open','high','low','close']]=[100,max(100,value)+.1,min(100,value)-.1,value]
    result=execute(data,match,cfg=cfg,policy=policy)
    reason=kind if kind not in {'ambiguous','target_through','target_touch'} else {'ambiguous':'stop','target_through':'target','target_touch':'elapsed_cutoff'}[kind]
    assert result['trade']['exit_reason']==(reason if policy=='barrier_capped_elapsed_v1' else 'elapsed_cutoff')
    assert not any(e['kind']=='target' for e in result['encounters']) if kind=='target_touch' else True

@pytest.mark.parametrize('side',[1,-1])
def test_every_fee_and_transport_centered_on_cost_adjusted_entry(side):
    data=frame();match=match_for(data,side)
    costs=Costs(commission_per_share=.007,minimum_commission=.17,fixed_fee_per_order=.23,sell_fee_per_dollar=.0001,spread_bps=3,slippage_bps=2,borrow_annual=.12)
    result=execute(data,match,costs=costs)
    assert result['geometry']['entry_fill']!=100 and result['trade']['fees']>0
    assert side*(result['geometry']['entry_fill']-result['geometry']['stop'])==pytest.approx(2)

@pytest.mark.parametrize('side,fault',[(side,fault) for side in [1,-1] for fault in ['prior_volume','no_prior','invalid_target']]+[(-1,'unavailable')])
def test_failed_candidates_are_preserved_and_never_resized(side,fault):
    data=frame();match=match_for(data,side);costs=ZERO
    if fault=='unavailable':
        costs=ZERO.model_copy(update=dict(borrow_available=False))
    elif fault=='prior_volume':data.loc[0,'volume']=100.
    elif fault=='no_prior':data=data.iloc[1:].reset_index(drop=True)
    else:
        if side==1:match['stop']='-1'
        else:match['target']='-1'
    result=execute(data,match,costs=costs)
    assert result['status']=='failed' and result['net_profit'] is None and result['trade'] is None
    assert result['ledger']==[] and match['quantity']==10

@pytest.mark.parametrize('side',[1,-1])
def test_diagnostic_funding_and_participation_boundary(side):
    data=frame();match=match_for(data,side);match['quantity']=500
    result=execute(data,match,account=ACCOUNT.model_copy(update=dict(capital=100)))
    assert result['financing']['initial_cash']==50000 and result['financing']['capital_top_up']==49900
    match['quantity']=501
    assert execute(data,match)['status']=='failed'

@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
@pytest.mark.parametrize('at_cutoff',[False,True])
def test_short_recall_retains_liquidation_and_failed_duration(policy,at_cutoff):
    data=frame();match=match_for(data,-1,boundary='open',end=5)
    when=match['cutoff_at'] if at_cutoff else data.iloc[3].timestamp.isoformat()
    scenario=dict(name='authored recall',mode='synthetic',start='2026-11-04',end='2026-11-04',symbols=['SPY'],complete=True,
        events=[dict(symbol='SPY',effective_at=when,available=False,annual_rate=.1,recall=True)])
    costs=ZERO.model_copy(update=dict(borrow_scenario=scenario))
    # Validate nested assumptions rather than bypass their declared schema.
    costs=Costs(**costs.model_dump())
    result=execute(data,match,costs=costs,policy=policy)
    assert result['trade']['exit_reason']=='borrow_recall'
    assert result['status']==('failed' if policy=='fixed_elapsed_v1' and not at_cutoff else 'complete')

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('paid',[False,True])
def test_split_fractional_shares_dividend_entitlement_and_unpaid_cash(side,paid):
    data=frame(('2026-11-04','2026-11-05'));data.loc[data.session=='2026-11-05',['open','high','low','close']]=[200,201,199,200.5]
    match=match_for(data,side,start=388,end=393);match['quantity']=3
    # Wide transported barriers keep the split account alive until the cutoff.
    match['stop']=str(100-side*90);match['target']=str(100+side*90)
    actions=[Action('SPY','2026-11-05','split',.5),Action('SPY','2026-11-05','dividend',2,'2026-11-05' if paid else '2026-11-10')]
    result=execute(data,match,actions=actions,costs=ZERO.model_copy(update=dict(borrow_annual=.12)))
    assert result['trade']['exit_quantity']==1.5 and result['trade']['distributions']==side*3
    assert result['final_receivables']==(0 if paid else side*3)

def test_calendar_borrow_spans_weekend_and_dst_with_changing_rate():
    data=frame(('2026-10-30','2026-11-02'));match=match_for(data,-1,start=389,end=391)
    match.update(stop='190',target='10')
    scenario=dict(name='weekend rate',mode='synthetic',start='2026-10-30',end='2026-11-02',symbols=['SPY'],complete=True,
        events=[dict(symbol='SPY',effective_at='2026-11-01T00:00:00+00:00',available=True,annual_rate=.2,recall=False)])
    costs=Costs(**(ZERO.model_dump()|dict(borrow_annual=.1,borrow_scenario=scenario)))
    result=execute(data,match,costs=costs)
    assert match['holding_minutes']>60*66 and result['trade']['borrow']>0
    assert result['accounting_residual']==pytest.approx(0,abs=1e-7)
