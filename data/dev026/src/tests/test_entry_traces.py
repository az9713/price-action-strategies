"""Original entry geometry is captured at execution, never rebuilt from exit stops."""
from decimal import Decimal
from dataclasses import replace, FrozenInstanceError
import json
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab.config import Strategy,Costs,Portfolio,identity
from backend.lab.data import Action,normalize,prepare,save_dataset
from backend.lab.engine import simulate
from backend.lab.service import Lab,compressed_read
from backend.lab import service
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from test_reference_execution import rows,sig,run_both,assert_parity,CFG,ZERO,ACCOUNT


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('entry',['next_open','same_close','limit'])
def test_execution_freezes_original_geometry_and_entry_ledger_before_any_exit(side,entry):
    frame=rows();signal=sig(frame,side);cfg=CFG.model_copy(update={'entry':entry})
    actual,expected=run_both(frame,[signal],cfg=cfg)
    assert_parity(actual,expected)
    assert hasattr(actual,'entry_traces'), 'Original entry-time traces are not implemented.'
    assert len(actual.entry_traces)==len(actual.trades)==1
    trace=actual.entry_traces[0];trade=actual.trades[0];ledger=next(e for e in actual.ledger if e['kind']=='entry')
    assert trace['version']==1 and trace['trade_id']==trade['id']==signal.id
    assert trace['symbol']==trade['symbol'] and trace['side']==side and trace['config_id']==identity(cfg)
    assert trace['entry_at']==trade['entry_at'] and trace['atr_available_at']==signal.available_at.isoformat()
    assert trace['entry_price']==trade['entry_price'] and trace['quantity']==trade['entry_quantity']
    assert trace['entry_atr']==1. and trace['price_factor']==1.
    assert trace['entry_stop']==(98. if side==1 else 102.)
    assert Decimal(str(trace['entry_target']))==Decimal(str(trace['entry_price']))+side*Decimal(2)
    assert trace['entry_reference']==100. and trace['reference_kind']=={'next_open':'open','same_close':'close','limit':'limit'}[entry]
    assert trace['entry_order_type']==entry and trace['entry_fee']==ledger['fee']
    assert trace['signal_sha256']==identity(signal.json()) and trace['entry_ledger_sha256']==identity(ledger)
    assert trace['costs_sha256']==identity(ZERO) and trace['portfolio_sha256']==identity(ACCOUNT)
    assert trace['trace_sha256']==identity({k:v for k,v in trace.items() if k!='trace_sha256'})


@pytest.mark.parametrize('side',[1,-1])
@pytest.mark.parametrize('ratio',[2.,.2])
def test_entry_trace_is_not_changed_by_later_split_dividend_or_borrow(side,ratio):
    first=minute_frame('2026-11-04').iloc[-3:]
    second=minute_frame('2026-11-05',close=[100/ratio]).iloc[:3]
    third=minute_frame('2026-11-06',close=[100/ratio]).iloc[:3]
    actions=[Action('SPY','2026-11-05','split',ratio),Action('SPY','2026-11-05','dividend',.25,'2026-11-06')]
    frame=prepare(normalize(pd.concat([first,second,third],ignore_index=True))[0],actions)
    signal=sig(frame,side);costs=ZERO.model_copy(update={'borrow_annual':.03})
    actual,expected=run_both(frame,[signal],costs=costs,actions=actions)
    assert_parity(actual,expected)
    trace=actual.entry_traces[0];trade=actual.trades[0]
    assert trace['entry_price']==100. and trace['quantity']==49 and trace['entry_atr']==1.
    assert trace['entry_stop']==(98. if side==1 else 102.)
    assert Decimal(str(trade['stop']))==Decimal(str(trace['entry_stop']))/Decimal(str(ratio))
    assert Decimal(str(trade['exit_quantity']))==Decimal(49)*Decimal(str(ratio))
    before=json.dumps(trace,sort_keys=True)
    frame.loc[:,'factor']=99.
    with pytest.raises(FrozenInstanceError):signal.atr=999.
    assert json.dumps(trace,sort_keys=True)==before


@pytest.mark.parametrize('side',[1,-1])
def test_entry_after_prior_split_records_atr_in_raw_entry_price_units(side):
    action=Action('SPY','2026-11-04','split',2.)
    frame=prepare(normalize(minute_frame('2026-11-04',close=[50.]).iloc[:5])[0],[action])
    signal=replace(sig(frame,side),atr=3.)
    actual,expected=run_both(frame,[signal],actions=[action])
    assert_parity(actual,expected)
    trace=actual.entry_traces[0]
    assert trace['entry_atr']==1.5 and trace['price_factor']==2. and trace['entry_price']==50.
    assert trace['entry_stop']==(49. if side==1 else 51.)


def test_rejected_orders_never_create_fictitious_entry_traces():
    frame=rows();s=sig(frame,-1)
    result=simulate(frame,[s],CFG,ZERO.model_copy(update={'borrow_available':False}),ACCOUNT)
    assert len(result.rejected)==1 and result.trades==[] and result.entry_traces==[]


@pytest.mark.parametrize('kind',['single','portfolio','control','durable_single'])
def test_complete_actual_reports_and_durable_original_parts_preserve_entry_trace(tmp_path,monkeypatch,kind):
    lab=Lab(tmp_path);day='2026-11-04';raw=minute_frame(day)
    manifest=save_dataset(lab.datasets_root,raw,dict(input_kind='synthetic',provider='D046 entry trace test',corporate_actions_complete=True))
    frame=prepare(normalize(raw)[0]);signal=sig(frame,at=20)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
    if kind=='single':report=lab.evaluate(manifest['id'],CFG,ZERO,ACCOUNT,day,day)
    elif kind=='portfolio':report=lab.evaluate_portfolio(manifest['id'],[CFG],ZERO,ACCOUNT,day,day)
    elif kind=='control':
        context=dict(regular=frame,actions=[],manifest=manifest,warmup=day,configuration=CFG,charts={})
        payload=dict(dataset_id=manifest['id'],start=day,end=day,costs=ZERO.model_dump(),portfolio=ACCOUNT.model_dump())
        report=lab.control_book(context,payload,[signal],'full_real')
    else:
        job=lab.create_experiment(Experiment(dataset_id=manifest['id'],start=day,end=day,strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
        assert Worker(lab).run_once()
        assert lab.store.job(job['id'])['status']=='completed'
        saved=lab.result(job['id'])
        original=compressed_read(lab.output_path(job['id']))
        assert original==saved and original['job_id']==job['id']
        report=saved['report']
        assert original['report']['entry_traces']==report['entry_traces']
    assert report['entry_trace_version']==1 and len(report['entry_traces'])==len(report['trades'])==1
    trace=report['entry_traces'][0]
    assert trace['config_id']==identity(CFG) and trace['entry_stop']==98.
    assert trace['entry_ledger_sha256']==identity(next(e for e in report['ledger'] if e['kind']=='entry'))
