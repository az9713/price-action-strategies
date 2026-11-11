"""Authored aggregate entry-liquidity budgets; money is not the only shared resource."""
from decimal import Decimal
import pandas as pd
import pytest
from test_reference_execution import rows,sig,run_both,assert_parity,ZERO,ACCOUNT,CFG

@pytest.mark.parametrize('backend',['production','reference'])
@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('mode',['next_open','limit','same_close','boundary','reset','new_sample','gap_stop'])
def test_shared_symbol_volume_is_not_reused_by_multiple_rules(backend,side,mode):
    frame=rows(5);frame['volume']=100.
    first=CFG.model_copy(update={'target':'1R','entry':'next_open'})
    second=CFG.model_copy(update={'target':'5R','entry':'next_open'})
    if mode in {'limit','gap_stop'}:
        first=first.model_copy(update={'entry':'limit'});second=second.model_copy(update={'entry':'limit'})
    if mode in {'same_close','boundary'}: first=first.model_copy(update={'entry':'same_close'})
    if mode=='same_close': second=second.model_copy(update={'entry':'same_close'})
    first_signal=sig(frame,side,at=1,name='first');second_signal=sig(frame,side,at=2 if mode=='new_sample' else 1,name='second')
    if mode=='new_sample': second=second.model_copy(update={'entry':'same_close'})
    mapping={first_signal.id:first,second_signal.id:second};signals=[first_signal,second_signal]
    if mode=='reset':
        third=CFG.model_copy(update={'target':'2R'});third_signal=sig(frame,side,at=2,name='third')
        signals.append(third_signal);mapping[third_signal.id]=third
    if mode=='gap_stop':
        frame.loc[1,['open','high','low','close']]=[95,101,94,96] if side>0 else [105,106,99,104]
    account=ACCOUNT.model_copy(update={'risk_fraction':.1,'participation':.29})
    actual,expected=run_both(frame,signals,first,ZERO,account,strategy_map=mapping)
    trades=actual.trades if backend=='production' else expected['trades']
    #100 prior shares ×0.29 participation =29 whole entry shares for that
    #instrument/reference bar across all rules. A genuinely new volume sample
    #permits another29; a synthetic close and the following open share a sample.
    quantity=Decimal(58 if mode in {'reset','new_sample'} else 29)
    assert sum(Decimal(str(t['entry_quantity'])) for t in trades)==quantity
    entries=[e for e in actual.ledger if e['kind']=='entry']
    for entry in entries:
        assert entry['entry_volume_before']+entry['quantity']==entry['entry_volume_after']<=entry['entry_volume_limit']
        assert entry['entry_volume_limit']==29 and entry['liquidity_reference_volume']==100
    assert_parity(actual,expected)


def test_entry_participation_is_separate_per_instrument():
    a=rows(3,symbol='AAA');b=rows(3,symbol='BBB');frame=pd.concat([a,b],ignore_index=True);frame['volume']=100.
    signals=[sig(a,at=1,name='A'),sig(b,at=1,name='B')]
    actual,expected=run_both(frame,signals,CFG,ZERO,ACCOUNT.model_copy(update={'risk_fraction':.1,'participation':.29}))
    assert {t['symbol']:t['entry_quantity'] for t in actual.trades}=={'AAA':29,'BBB':29}
    assert_parity(actual,expected)
