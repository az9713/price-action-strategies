"""Identical executed cash flows cannot become a spurious strict comparison win."""
from decimal import Decimal
import pytest

from conftest import minute_frame
from backend.lab import service
from backend.lab.service import Lab
from backend.lab.data import normalize,prepare as prepare_data,save_dataset
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from backend.lab.trade_twin_source import read_saved_source
from backend.lab.trade_twin_preparation import prepare
from backend.lab.trade_twin_jobs import create
from backend.lab.trade_twins import draw_set
from backend.lab.trade_twin_execution import execute_twin
from test_reference_execution import CFG,ZERO,ACCOUNT,sig


@pytest.mark.parametrize('closing_price',[99.9,100.1])
def test_original_and_twin_identical_filled_cashflows_have_the_same_exact_baseline(tmp_path,monkeypatch,closing_price):
    lab=Lab(tmp_path);closes=[100.]*390
    closes[379:]=[closing_price]*11
    frame=minute_frame('2026-11-04',close=closes)
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='exact source-baseline counterexample',corporate_actions_complete=True))
    regular=prepare_data(normalize(frame)[0]);signal=sig(regular,at=20)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
    parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    original=read_saved_source(lab,parent['id'])
    child=create(lab,parent['id']);owner='baseline-proof';job=lab.store.claim(owner)
    prepared=prepare(lab,job,owner);draw=draw_set(prepared['plan'],job['payload']['seed'],0)
    book=execute_twin(prepared['regular'],draw['matches'][0],job['payload']['strategy'],job['payload']['costs'],job['payload']['portfolio'],prepared['actions'])
    assert book['status']=='complete'
    real=lab.report(parent['id'])['trades'][0]
    assert Decimal(str(real['entry_price']))==book['trade']['entry_price']
    assert Decimal(str(real['exit_price']))==book['trade']['exit_price']
    assert Decimal(str(real['entry_quantity']))==book['trade']['entry_quantity']
    assert Decimal(original['source_profit'])==book['net_profit'], 'Identical filled prices/quantity/costs must tie under the exact grading contract.'
    lab.store.release(child['id'],owner)


@pytest.mark.parametrize('side,annual,fees',[(1,0,0),(-1,0,0),(1,0,.017),(-1,0,.017),(-1,.12,0),(-1,.12,.017)])
def test_actual_original_and_twin_flat_cashflows_tie_with_fees_and_short_financing(tmp_path,monkeypatch,side,annual,fees):
    from backend.lab.config import Costs
    lab=Lab(tmp_path);frame=minute_frame('2026-11-04')
    frame[['open','high','low','close']]=[100.,100.1,99.9,100.]
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Independent original/twin fee and borrow tie fixture',corporate_actions_complete=True))
    regular=prepare_data(normalize(frame)[0]);signal=sig(regular,side=side,at=20)
    costs=Costs(commission_per_share=fees,spread_bps=3 if fees else 0,slippage_bps=2 if fees else 0,borrow_annual=annual)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
    parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=costs,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    original=read_saved_source(lab,parent['id'])
    child=create(lab,parent['id']);owner='cashflow-tie';job=lab.store.claim(owner)
    prepared=prepare(lab,job,owner);draw=draw_set(prepared['plan'],job['payload']['seed'],0)
    book=execute_twin(prepared['regular'],draw['matches'][0],job['payload']['strategy'],job['payload']['costs'],job['payload']['portfolio'],prepared['actions'])
    real=lab.report(parent['id'])['cashflow_audit']['trades'][0]
    assert book['status']=='complete'
    for field in ['entry_price','exit_price','entry_quantity','exit_quantity','fees','borrow','net_pnl']:
        assert Decimal(real[field])==book['trade'][field],field
    assert Decimal(original['source_profit'])==book['net_profit']
    lab.store.release(child['id'],owner)
