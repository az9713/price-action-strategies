"""Financial twin contracts: full independent Decimal books and hand calculations."""
import ast,copy,hashlib,importlib,importlib.util,json,math,os
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
    inputs=dict(bars=primitive(data),match=copy.deepcopy(match),configuration=cfg.model_dump(mode='json'),costs=costs.model_dump(mode='json'),account=account.model_dump(mode='json'),actions=[asdict(a) for a in actions],policy=policy)
    before=json.dumps(inputs,sort_keys=True,default=str)
    actual=module.execute_twin(data,match,cfg,costs,account,actions,policy=policy)
    parity(actual,expected)
    assert abs(actual['accounting_residual'])<=1e-7
    after=dict(bars=primitive(data),match=match,configuration=cfg.model_dump(mode='json'),costs=costs.model_dump(mode='json'),account=account.model_dump(mode='json'),actions=[asdict(a) for a in actions],policy=policy)
    assert before==json.dumps(after,sort_keys=True,default=str),'Execution mutated frozen inputs.'
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        folder=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'financial-books';folder.mkdir(exist_ok=True)
        identifier=hashlib.sha256(before.encode()).hexdigest()
        (folder/(identifier+'.json')).write_text(json.dumps(dict(inputs=inputs,actual=actual,independent_reference=expected,all_fields_compared=True,unchanged_inputs=True),sort_keys=True,indent=2,default=str),encoding='utf-8')
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
    costs=Costs(**(ZERO.model_dump()|dict(borrow_scenario=scenario)))
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


@pytest.mark.parametrize('drop_prior',[True,False])
def test_stale_or_missing_immediately_prior_completed_volume_cannot_fund_entry(drop_prior):
    data=frame();match=match_for(data,start=3,end=5)
    if drop_prior:data=data.drop(index=2)
    else:data.loc[2,'timestamp']=data.loc[2,'timestamp']-pd.Timedelta(seconds=30)
    module=importlib.import_module('backend.lab.trade_twin_execution')
    if drop_prior:
        actual=module.execute_twin(data,match,CFG,ZERO,ACCOUNT)
        assert actual['status']=='failed' and actual['failure']=='Original quantity exceeds prior-minute liquidity'
        parity(actual,reference(data,match))
    else:
        with pytest.raises(ValueError):module.execute_twin(data,match,CFG,ZERO,ACCOUNT)


@pytest.mark.parametrize('fault',['extra','side_bool','quantity_bool','quantity_float','quantity_zero','bad_symbol','bad_id','bad_key','duration_zero','duration_mismatch','bad_boundary','bad_policy','bad_time','naive_time','reference_changed','atr_zero','distance_reversed','huge_geometry','long_geometry','rational_zero_denominator','empty','missing_columns','duplicate','naive_bars','bad_second','nonfinite','negative_volume','bad_ohlc','missing_minute','bad_session','bad_session_open','cutoff_weekend','duplicate_action','borrow_coverage','bad_cost','bad_config'])
def test_invalid_frozen_inputs_and_incomplete_clocks_refuse_before_financial_output(fault):
    data=frame();match=match_for(data);cfg=CFG;costs=ZERO;actions=[];policy='barrier_capped_elapsed_v1'
    if fault=='extra':match['unexpected']=1
    elif fault=='side_bool':match['side']=True
    elif fault=='quantity_bool':match['quantity']=True
    elif fault=='quantity_float':match['quantity']=10.
    elif fault=='quantity_zero':match['quantity']=0
    elif fault=='bad_symbol':match['symbol']='../SPY'
    elif fault=='bad_id':match['source_id']='../source'
    elif fault=='bad_key':match['candidate_key']='other'
    elif fault=='duration_zero':match['holding_minutes']=0
    elif fault=='duration_mismatch':match['holding_minutes']=9
    elif fault=='bad_boundary':match['exit_boundary']='nearest'
    elif fault=='bad_policy':policy='host_unknown'
    elif fault=='bad_time':match['entry_at']='not a clock'
    elif fault=='naive_time':match['entry_at']='2026-11-04T14:31:00'
    elif fault=='reference_changed':match['entry_reference']='99'
    elif fault=='atr_zero':match['atr']='0'
    elif fault=='distance_reversed':match['stop']='101'
    elif fault=='huge_geometry':match['stop']=str(-10**20)
    elif fault=='long_geometry':match['stop']='9'*1025
    elif fault=='rational_zero_denominator':match['stop']='1/0'
    elif fault=='empty':data=data.iloc[:0]
    elif fault=='missing_columns':data=data.drop(columns=['close'])
    elif fault=='duplicate':data=pd.concat([data,data.iloc[[2]]])
    elif fault=='naive_bars':data['timestamp']=data.timestamp.dt.tz_localize(None)
    elif fault=='bad_second':data.loc[2,'timestamp']+=pd.Timedelta(seconds=1)
    elif fault=='nonfinite':data.loc[2,'open']=float('nan')
    elif fault=='negative_volume':data.loc[2,'volume']=-1
    elif fault=='bad_ohlc':data.loc[2,'high']=90.
    elif fault=='missing_minute':data=data.drop(index=2)
    elif fault=='bad_session':data.loc[2,'session']='2026-11-03'
    elif fault=='bad_session_open':data.loc[2,'session_open']+=pd.Timedelta(minutes=1)
    elif fault=='cutoff_weekend':
        match['cutoff_at']='2026-11-07T14:31:00+00:00';match['holding_minutes']=int((pd.Timestamp(match['cutoff_at'])-pd.Timestamp(match['entry_at']))//pd.Timedelta(minutes=1))
    elif fault=='duplicate_action':actions=[Action('SPY','2026-11-05','split',2)]*2
    elif fault=='borrow_coverage':costs=Costs(**(ZERO.model_dump()|dict(borrow_scenario=dict(name='outside',start='2026-11-05',end='2026-11-05',symbols=['SPY'],complete=True))))
    elif fault=='bad_cost':costs=ZERO.model_copy(update=dict(spread_bps=-1))
    else:cfg=CFG.model_copy(update=dict(timeframe='unsupported'))
    module=importlib.import_module('backend.lab.trade_twin_execution')
    with pytest.raises((ValueError,ZeroDivisionError)):module.execute_twin(data,match,cfg,costs,ACCOUNT,actions,policy=policy)


@pytest.mark.parametrize('point',[1,2,3])
def test_cancellation_before_work_during_minutes_and_before_return(point):
    data=frame();match=match_for(data);calls=0
    def cancel():
        nonlocal calls
        calls+=1
        return calls==point
    module=importlib.import_module('backend.lab.trade_twin_execution')
    with pytest.raises(InterruptedError):module.execute_twin(data,match,CFG,ZERO,ACCOUNT,cancel=cancel)
    assert calls==point


@pytest.mark.parametrize('side',[1,-1])
def test_fractional_geometry_is_rounded_outward_on_exact_tick_grid(side):
    data=frame();match=match_for(data,side)
    match['stop']='299/3' if side==1 else '301/3';match['target']='901/9' if side==1 else '899/9'
    result=execute(data,match)
    assert result['geometry']['stop']==Decimal('99.66' if side==1 else '100.34')
    assert result['geometry']['target']==Decimal('100.12' if side==1 else '99.88')


@pytest.mark.parametrize('side',[1,-1])
def test_first_session_minute_uses_actual_previous_exchange_close_volume(side):
    data=frame(('2026-11-04','2026-11-05'));match=match_for(data,side,start=390,end=392)
    assert execute(data,match)['financing']['liquidity_reference_at']==data.iloc[389].timestamp.isoformat()
    data=data.drop(index=389)
    assert execute(data,match)['status']=='failed'


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
def test_opening_cutoff_precedes_new_opening_gap_barriers(side,policy):
    data=frame();match=match_for(data,side,end=4,boundary='open')
    value=100-side*10;data.loc[4,['open','high','low','close']]=[value,value+.1,value-.1,value]
    result=execute(data,match,policy=policy)
    assert result['trade']['exit_reason']=='elapsed_cutoff'
    assert result['trade']['exit_price']==value


@pytest.mark.parametrize('side',[1,-1])
def test_close_stop_waits_for_the_original_complete_trigger_boundary(side):
    data=frame();match=match_for(data,side,start=1,end=7);cfg=CFG.model_copy(update=dict(timeframe='5m',stop_kind='close'))
    value=100-side*3
    for i in [2,3,4]:data.loc[i,['open','high','low','close']]=[100,max(100,value)+.1,min(100,value)-.1,value]
    result=execute(data,match,cfg=cfg)
    assert result['trade']['exit_reason']=='close_stop' and result['trade']['exit_at']==data.iloc[5].timestamp.isoformat()


@pytest.mark.parametrize('side',[1,-1])
def test_early_close_exact_boundary_and_weekend_calendar_clock(side):
    data=frame(('2026-11-25','2026-11-27'));match=match_for(data,side,start=389,end=len(data)-1)
    match.update(stop=str(100-side*90),target=str(100+side*90))
    result=execute(data,match)
    assert result['trade']['exit_at']=='2026-11-27T18:00:00+00:00'
    assert len(result['equity'])==2


@pytest.mark.parametrize('seed',range(32))
def test_deterministic_random_complete_financial_books(seed):
    import random
    rng=random.Random(seed);data=frame();price=Decimal('100')
    for index in range(1,21):
        opened=price+Decimal(rng.randrange(-30,31))/100
        closed=opened+Decimal(rng.randrange(-30,31))/100
        high=max(opened,closed)+Decimal(rng.randrange(0,90))/100
        low=min(opened,closed)-Decimal(rng.randrange(0,90))/100
        data.loc[index,['open','high','low','close']]=list(map(float,[opened,high,low,closed]));price=closed
    side=rng.choice([-1,1]);match=match_for(data,side,start=1,end=20,boundary=rng.choice(['open','close']))
    match['quantity']=rng.randrange(1,100)
    costs=Costs(commission_per_share=rng.choice([0,.005,.01]),minimum_commission=rng.choice([0,.1]),fixed_fee_per_order=rng.choice([0,.2]),sell_fee_per_dollar=.00001,spread_bps=rng.choice([0,1,3]),slippage_bps=rng.choice([0,1]),borrow_annual=rng.choice([0,.03,.2]))
    result=execute(data,match,costs=costs,policy=rng.choice(['barrier_capped_elapsed_v1','fixed_elapsed_v1']))
    assert result['trade'] is not None


@pytest.mark.parametrize('side',[1,-1])
def test_ex_date_new_entry_has_no_prior_close_entitlement(side):
    data=frame();match=match_for(data,side)
    result=execute(data,match,actions=[Action('SPY','2026-11-04','dividend',2,'2026-11-04')])
    assert result['trade']['distributions']==0
    assert not any(e['kind'].startswith('distribution') for e in result['ledger'])


@pytest.mark.parametrize('side',[1,-1])
def test_dividend_pays_after_an_early_barrier_exit_within_frozen_window(side):
    data=frame(('2026-11-04','2026-11-05','2026-11-06'));match=match_for(data,side,start=388,end=781)
    value=100-side*3;data.loc[390,['open','high','low','close']]=[value,value+.1,value-.1,value]
    result=execute(data,match,actions=[Action('SPY','2026-11-05','dividend',2,'2026-11-06')])
    assert result['trade']['exit_reason']=='gap_stop' and result['trade']['distributions']==side*20
    assert result['final_receivables']==0
    assert any(e['kind']=='distribution_payment' and e['timestamp']==data.iloc[780].timestamp.isoformat() for e in result['ledger'])


@pytest.mark.parametrize('policy',['barrier_capped_elapsed_v1','fixed_elapsed_v1'])
def test_coincident_closing_cutoff_retains_declared_barrier_precedence(policy):
    data=frame();match=match_for(data,end=3);data.loc[3,'low']=98.
    result=execute(data,match,policy=policy)
    assert result['trade']['exit_at']==match['cutoff_at']
    assert result['trade']['exit_reason']==('stop' if policy=='barrier_capped_elapsed_v1' else 'elapsed_cutoff')


def test_calendar_borrow_has_an_independent_hand_computed_weekend_total():
    data=frame(('2026-10-30','2026-11-02'));match=match_for(data,-1,start=389,end=391);match.update(stop='190',target='10')
    scenario=dict(name='hand calendar rate',mode='synthetic',start='2026-10-30',end='2026-11-02',symbols=['SPY'],complete=True,
        events=[dict(symbol='SPY',effective_at='2026-11-01T00:00:00+00:00',available=True,annual_rate=.2,recall=False)])
    costs=Costs(**(ZERO.model_dump()|dict(borrow_annual=.1,borrow_scenario=scenario)))
    result=execute(data,match,costs=costs)
    numerator=Decimal(1000)*Decimal('.1')*60+Decimal(1010)*(Decimal('.1')*100800+Decimal('.2')*138600)+Decimal(1000)*Decimal('.2')*60+Decimal(1000)*Decimal('.2')*60
    expected=numerator/Decimal(365*86400)
    assert abs(result['trade']['borrow']-expected)<Decimal('1e-25')


@pytest.mark.parametrize('side',[1,-1])
def test_each_fee_has_a_hand_calculated_total_without_borrow(side):
    data=frame();match=match_for(data,side)
    costs=Costs(commission_per_share=.007,minimum_commission=.17,fixed_fee_per_order=.23,sell_fee_per_dollar=.0001,spread_bps=3,slippage_bps=2,borrow_annual=0)
    result=execute(data,match,costs=costs)
    assert result['trade']['net_pnl']==Decimal('8.29904' if side==1 else '-11.69996')


def test_internal_decimal_books_keep_large_capital_and_fractional_cents():
    data=frame();match=match_for(data);account=ACCOUNT.model_copy(update=dict(capital=1e10))
    result=execute(data,match,account=account,costs=ZERO.model_copy(update=dict(fixed_fee_per_order=.00000013)))
    assert result['final_cash']==Decimal('10000000009.99999974')
    assert result['accounting_residual']==0


def test_nonpositive_modeled_stop_is_an_explicit_computation_failure_not_a_new_draw():
    data=frame();data[['open','high','low','close']]=[.02,.025,.015,.02]
    match=match_for(data);match.update(stop='0.01',target='0.04');data.loc[2,'low']=.01
    module=importlib.import_module('backend.lab.trade_twin_execution')
    with pytest.raises(ValueError,match='nonpositive'):module.execute_twin(data,match,CFG,ZERO,ACCOUNT)
    with pytest.raises(ValueError,match='nonpositive'):reference(data,match)
