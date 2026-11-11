"""Independent execution parity. No golden output is generated from production."""
from dataclasses import replace
from decimal import Decimal,localcontext
from pathlib import Path
import json
import math
import random
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import normalize,prepare,Action
from backend.lab.signals import Signal
from backend.lab.engine import simulate
from verification.reference_execution import execute

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'verification/fixtures/execution-reference-contract.json').read_text())
ZERO=Costs(commission_per_share=0,spread_bps=0,slippage_bps=0,borrow_annual=0)
ACCOUNT=Portfolio(capital=10000,risk_fraction=.01,symbol_exposure=1,total_exposure=1,participation=1)
CFG=Strategy(timeframe='1m',swing_strength=2,max_hold=0,stop_buffer=0)

def rows(count=5,symbol='SPY',day='2026-11-04'):
    return prepare(normalize(minute_frame(day,symbol).iloc[:count])[0])

def sig(frame,side=1,at=1,stop=None,name='known',symbol=None,target=None):
    return Signal(name,symbol or frame.iloc[0].symbol,frame.iloc[at].timestamp,side,100.,1.,
        (98. if side==1 else 102.) if stop is None else stop,target,1.,frame.iloc[at].timestamp,0)

def primitive(frame):
    return [{k:(v.isoformat() if isinstance(v,pd.Timestamp) else v) for k,v in row.items()}
        for row in frame.to_dict('records')]

def run_both(frame,signals,cfg=CFG,costs=ZERO,account=ACCOUNT,actions=(),strategy_map=None,start=None,end=None):
    mapping=strategy_map or {s.id:cfg for s in signals}
    configurations={identity(c):c.model_dump() for c in [cfg,*mapping.values()]}
    requests=[s.json()|{'config_id':identity(mapping[s.id])} for s in signals]
    expected=execute(primitive(frame),requests,configurations,costs.model_dump(),account.model_dump(),
        [a.__dict__ for a in actions],start,end)
    actual=simulate(frame,signals,cfg,costs,account,actions,start,end,strategy_map=mapping)
    return actual,expected

def assert_parity(actual,expected):
    # Prices and quantities get tighter tolerances; enum/time/order/count exact.
    def compare(a,b,path=''):
        if isinstance(b,dict):
            assert set(a)==set(b),path
            for k in b: compare(a[k],b[k],path+'/'+k)
        elif isinstance(b,list):
            assert len(a)==len(b),(path,len(a),len(b))
            for i,(left,right) in enumerate(zip(a,b)): compare(left,right,path+'/'+str(i))
        elif isinstance(b,(Decimal,float,int)) and not isinstance(b,bool):
            assert math.isfinite(float(a)) and math.isfinite(float(b)),path
            key=path.rsplit('/',1)[-1]
            tolerance=1e-9 if key in {'price','entry_price','split_adjusted_entry','exit_price','stop','target','entry_quantity','exit_quantity','quantity'} else 1e-7
            assert abs(Decimal(str(a))-Decimal(str(b)))<=Decimal(str(tolerance)),(path,a,str(b))
        else: assert a==b,(path,a,b)
    compare({k:getattr(actual,k) for k in ['trades','ledger','equity','rejected']},expected)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['target','stop','ambiguous','gap_stop','gap_target','end'])
def test_independent_basic_order_cases(side,mode):
    frame=rows();signal=sig(frame,side)
    if mode=='target': frame.loc[2,['high','low']]=[103,99.9] if side>0 else [100.1,97]
    elif mode in {'stop','ambiguous'}: frame.loc[2,['high','low']]=[103 if mode=='ambiguous' else 100.1,97] if side>0 else [103,97 if mode=='ambiguous' else 99.9]
    elif mode=='gap_stop': frame.loc[2,['open','high','low','close']]=[95,96,94,95] if side>0 else [105,106,104,105]
    elif mode=='gap_target': frame.loc[2,['open','high','low','close']]=[105,106,104,105] if side>0 else [95,96,94,95]
    actual,expected=run_both(frame,[signal]);assert len(expected['trades'])==1
    assert_parity(actual,expected)

def test_reference_changing_short_notional_has_hand_computed_borrow():
    frame=rows(4)
    frame.loc[1,['open','high','low','close']]=[100,101.1,99.9,101]
    frame.loc[2,['open','high','low','close']]=[101,102.1,100.9,102]
    frame.loc[3,['open','high','low','close']]=[102,102.1,101.9,102]
    actual,expected=run_both(frame,[sig(frame,-1,stop=105)],CFG.model_copy(update={'target':'5R'}),ZERO.model_copy(update={'borrow_annual':.365}))
    case=CONTRACT['cases']['changing_short_notional']
    assert expected['trades'][0]['entry_quantity']==case['quantity']
    assert abs(expected['trades'][0]['borrow']-Decimal(case['expected_borrow']))<Decimal('1e-35')
    assert_parity(actual,expected)

def test_reference_last_minute_borrow_appears_in_its_own_session_equity():
    frame=prepare(normalize(pd.concat([minute_frame('2026-11-04'),minute_frame('2026-11-05').iloc[:2]],ignore_index=True))[0])
    signal=sig(frame,-1,at=389,stop=105)
    actual,expected=run_both(frame,[signal],CFG.model_copy(update={'target':'5R'}),ZERO.model_copy(update={'borrow_annual':.365}))
    first_borrow=Decimal(CONTRACT['cases']['last_session_minute']['first_close_borrow'])
    with localcontext() as context:
        context.prec=50
        assert abs(expected['equity'][0]['equity']-(Decimal('10000')-first_borrow))<Decimal('1e-30')
    assert_parity(actual,expected)

def test_reference_enumerated_sizing_with_large_per_share_fees():
    actual,expected=run_both(rows(),[sig(rows())],costs=ZERO.model_copy(update={'commission_per_share':1}))
    case=CONTRACT['cases']['large_per_share_fees']
    assert expected['trades'][0]['entry_quantity']==case['quantity']
    assert expected['trades'][0]['net_pnl']==case['net_profit']
    assert_parity(actual,expected)

def test_reference_older_pending_order_beats_newer_alphabetically_earlier_symbol():
    a=rows(symbol='AAA');b=rows(symbol='BBB');b.loc[1,'low']=100.
    frame=pd.concat([a,b],ignore_index=True)
    newer=sig(a,at=2,stop=99,name='newer');older=sig(b,stop=99,name='older')
    cfg=CFG.model_copy(update={'target':'5R'});limit=cfg.model_copy(update={'entry':'limit'})
    account=ACCOUNT.model_copy(update={'risk_fraction':.1,'symbol_exposure':.5,'total_exposure':.5})
    actual,expected=run_both(frame,[newer,older],cfg,account=account,strategy_map={newer.id:cfg,older.id:limit})
    assert len(expected['trades'])==1 and expected['trades'][0]['symbol']=='BBB'
    assert expected['trades'][0]['entry_quantity']==50
    assert_parity(actual,expected)

def test_reference_config_identity_priority_is_not_opaque_signal_id():
    frame=rows();configs=[CFG.model_copy(update={'family':f,'target':'5R'}) for f in ['change_of_character','breakout']]
    configs.sort(key=identity)
    first=sig(frame,stop=99,name='zz');second=replace(first,id='aa')
    account=ACCOUNT.model_copy(update={'risk_fraction':.1,'symbol_exposure':.5,'total_exposure':.5})
    actual,expected=run_both(frame,[first,second],configs[0],account=account,strategy_map={'zz':configs[0],'aa':configs[1]})
    assert expected['trades'][0]['id']=='zz' and len(expected['trades'])==1
    assert_parity(actual,expected)

def test_reference_same_close_uses_the_known_closing_mark():
    frame=rows();frame.loc[0,['open','high','low','close']]=[110,110.1,99.9,100]
    actual,expected=run_both(frame,[sig(frame)],CFG.model_copy(update={'entry':'same_close'}),
        account=ACCOUNT.model_copy(update={'risk_fraction':.1,'symbol_exposure':.5,'total_exposure':.5}))
    assert expected['trades'][0]['entry_quantity']==CONTRACT['cases']['same_close_mark']['quantity']
    assert_parity(actual,expected)

def test_reference_same_close_marks_other_positions_before_sizing():
    a=rows(symbol='AAA');b=rows(symbol='BBB')
    b.loc[2,['open','high','low','close']]=[100,201,99.9,200]
    b.loc[3:,['open','high','low','close']]=[200,200.1,199.9,200]
    frame=pd.concat([a,b],ignore_index=True)
    carried=sig(b,target=1000,name='carried');closing=sig(a,at=3,stop=99,name='closing')
    old=CFG.model_copy(update={'target':'swing'});new=CFG.model_copy(update={'entry':'same_close','target':'5R'})
    actual,expected=run_both(frame,[carried,closing],old,account=ACCOUNT.model_copy(update={'risk_fraction':.1,'symbol_exposure':.25}),
        strategy_map={'carried':old,'closing':new})
    assert next(t for t in expected['trades'] if t['id']=='closing')['entry_quantity']==31
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
def test_reference_limit_new_entry_stop_gap_uses_opening_price(side):
    frame=rows();frame.loc[1,['open','high','low','close']]=[95,96,94,95] if side>0 else [105,106,104,105]
    actual,expected=run_both(frame,[sig(frame,side)],CFG.model_copy(update={'entry':'limit'}))
    assert expected['trades'][0]['exit_reason']=='gap_stop'
    if side>0:
        assert expected['trades'][0]['net_pnl']==Decimal(str(CONTRACT['cases']['new_limit_gap']['net_profit']))
    assert_parity(actual,expected)

def test_reference_rejects_zero_target_after_tick_rounding():
    frame=rows();frame[['open','high','low','close']]=[.08,.081,.079,.08]
    signal=replace(sig(frame,-1,stop=.13),level=.08)
    actual,expected=run_both(frame,[signal],CFG.model_copy(update={'target':'1.5R'}),account=ACCOUNT.model_copy(update={'capital':10,'risk_fraction':.1}))
    assert not expected['trades'] and expected['rejected'][0]['reason']=='Target is not a positive tradable price'
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('ratio',[2,.2])
def test_reference_splits_distributions_and_payable_cash(side,ratio):
    first=minute_frame('2026-11-04').iloc[-3:]
    second=minute_frame('2026-11-05',close=[100/ratio]).iloc[:3]
    third=minute_frame('2026-11-06',close=[100/ratio]).iloc[:3]
    actions=[Action('SPY','2026-11-05','split',ratio),Action('SPY','2026-11-05','dividend',.25,'2026-11-06')]
    frame=prepare(normalize(pd.concat([first,second,third],ignore_index=True))[0],actions)
    actual,expected=run_both(frame,[sig(frame,side)],costs=ZERO.model_copy(update={'borrow_annual':.03}),actions=actions)
    assert expected['trades'][0]['exit_quantity']==Decimal(49)*Decimal(str(ratio))
    assert expected['trades'][0]['distributions']==side*Decimal(49)*Decimal(str(ratio))*Decimal('.25')
    assert_parity(actual,expected)

def test_reference_module_has_no_production_numerical_imports():
    import ast,inspect
    from verification import reference_execution
    tree=ast.parse(inspect.getsource(reference_execution))
    for item in ast.walk(tree):
        if isinstance(item,ast.ImportFrom): assert not (item.module or '').startswith(('backend','numpy','pandas'))
        if isinstance(item,ast.Import): assert all(not x.name.startswith(('backend','numpy','pandas')) for x in item.names)

def test_reference_prior_volume_participation_decimal_boundary():
    frame=rows();frame['volume']=100
    account=ACCOUNT.model_copy(update={'risk_fraction':.1,'participation':.29})
    actual,expected=run_both(frame,[sig(frame,stop=99)],account=account)
    assert expected['trades'][0]['entry_quantity']==29
    assert_parity(actual,expected)

def test_reference_marked_exposure_decimal_boundary():
    frame=rows();frame[['open','high','low','close']]=[1,1.01,.99,1]
    account=ACCOUNT.model_copy(update={'capital':100,'risk_fraction':.1,'symbol_exposure':.29,'total_exposure':.29})
    actual,expected=run_both(frame,[replace(sig(frame,stop=.9),level=1)],CFG.model_copy(update={'target':'5R'}),account=account)
    assert expected['trades'][0]['entry_quantity']==29
    assert_parity(actual,expected)

def test_reference_target_exactly_one_tick_through_is_fillable():
    frame=rows();frame[['open','high','low','close']]=[100.01,100.02,100,100.01]
    frame.loc[2,'high']=101.02
    actual,expected=run_both(frame,[replace(sig(frame,stop=99.01),level=100.01)])
    assert expected['trades'][0]['exit_reason']=='target'
    assert expected['trades'][0]['target']==Decimal('101.01')
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
def test_reference_limit_is_rounded_to_a_permitted_grid_price(side):
    frame=rows();signal=replace(sig(frame,side),level=100.015)
    actual,expected=run_both(frame,[signal],CFG.model_copy(update={'entry':'limit'}))
    assert expected['trades'][0]['entry_price']==Decimal('100.01' if side>0 else '100.02')
    assert_parity(actual,expected)

@pytest.mark.parametrize('side',[1,-1])
def test_reference_limit_exactly_one_tick_through_is_fillable(side):
    frame=rows();frame[['open','high','low','close']]=[100.01,100.02,100.01,100.01] if side<0 else [100.02,100.02,100.01,100.02]
    level=100.01 if side<0 else 100.02
    actual,expected=run_both(frame,[replace(sig(frame,side),level=level)],CFG.model_copy(update={'entry':'limit'}))
    assert len(expected['trades'])==1
    assert_parity(actual,expected)
