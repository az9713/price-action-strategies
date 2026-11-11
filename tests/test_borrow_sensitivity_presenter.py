"""Saved sensitivity projection, separate Decimal reader and actual export routes."""
from copy import deepcopy
from decimal import Decimal
import json
import pytest
from backend.lab.presenter import build_deck,render_html,PresentationError,format_value
from backend.lab.presentation_audit import audit_deck,independent_format,PresentationAuditError
from backend.lab.worker import Worker
from test_borrow_sensitivity import accounts
from test_reference_execution import CFG
from backend.lab.sensitivity import summarize_accounts
from test_api import client_lab,seed,payload


def source():
    costs,books=accounts();config=CFG
    return dict(report_type='borrow_sensitivity',start=books[0]['start'],end=books[0]['end'],
        costs=costs.model_dump(),original_costs=costs.model_dump(),config=config.model_dump(),
        provenance={'input_kind':'synthetic'},**summarize_accounts(books,costs,config))


def test_projection_preserves_four_absolute_accounts_daily_differences_and_every_applied_event():
    value=source();value['costs']['borrow_scenario']['name']='</script><img src=x onerror=alert(1)>'
    raw=json.dumps(value,allow_nan=False).encode();deck=build_deck([('comparison.json',raw)])
    assert audit_deck({'comparison.json':raw},deck)['facts_checked']==len(deck['facts'])
    paths={tuple(f['path']):f for f in deck['facts'].values()}
    for i,rate in enumerate([0,.03,.1,.3]):
        for field in ['annual_rate','net_profit','delta_from_zero','borrow_paid','fees_paid','trades','short_trades','no_short_trades','signals','account_id']:
            assert paths[('comparison_rows',i,field)]['value']==value['comparison_rows'][i][field]
        assert paths[('arms',i,'costs','borrow_annual')]['value']==rate
        for e in range(len(value['arms'][i]['costs']['borrow_scenario']['events'])):
            for key in ['annual_rate','available','recall','effective_at','symbol']:
                assert ('arms',i,'costs','borrow_scenario','events',e,key) in paths
        assert paths[('daily_differences',i,'rows',0,'difference')]['value']==value['daily_differences'][i]['rows'][0]['difference']
    assert any('Original input costs' in str(p) for p in deck['pages'])
    assert any('no difference interval' in p['conclusion'] for p in deck['pages'])
    assert '</script><img' not in render_html(deck)
    assert max(len(p['notes']) for p in deck['pages'])<=3
    changed=deepcopy(deck);key=next(k for k,f in changed['facts'].items() if f['path']==['comparison_rows',3,'net_profit'])
    changed['facts'][key]['value']=999
    with pytest.raises(PresentationAuditError):audit_deck({'comparison.json':raw},changed)


@pytest.mark.parametrize('fault',['missing_arm','missing_comparison','missing_daily','rate_order','arm_order','daily_order'])
def test_incomplete_or_wrong_order_saved_comparison_fails_closed(fault):
    value=source()
    if fault=='missing_arm':value['arms'].pop()
    elif fault=='missing_comparison':value['comparison_rows'].pop()
    elif fault=='missing_daily':value['daily_differences'].pop()
    elif fault=='rate_order':value['comparison_rows'][2]['annual_rate']=.03
    elif fault=='arm_order':value['arms'][2]['part']=1
    else:value['daily_differences'][2]['part']=1
    with pytest.raises(PresentationError):build_deck([('comparison.json',json.dumps(value).encode())])


@pytest.mark.parametrize('value,expected',[(.005,'0.005'),(.0000278,'0.0000278'),(0.,'0'),(-0.,'0'),(-.0001,'-0.0001'),(5.,'5'),(None,'Undefined')])
def test_small_fee_formats_do_not_round_nonzero_inputs_to_zero(value,expected):
    assert format_value(value,'exact_number')==expected
    assert independent_format(None if value is None else Decimal(str(value)),'exact_number')==expected


def test_actual_aggregate_and_each_account_presentation_exports(client_lab):
    client,lab=client_lab;m=seed(lab);response=client.post('/api/borrow-sensitivity',json=payload(m));assert response.status_code==202
    jid=response.json()['id'];Worker(lab).run_once();assert lab.store.job(jid)['status']=='completed'
    for part in [None,0,1,2,3]:
        params={} if part is None else {'part':part}
        saved=client.get('/api/jobs/'+jid+'/export/json',params=params);assert saved.status_code==200
        result=client.get('/api/jobs/'+jid+'/export/presentation.json',params=params);assert result.status_code==200,result.text
        deck=result.json()
        assert len(deck['sources'])==1
        source_name=deck['sources'][0]['name']
        assert audit_deck({source_name:saved.content},deck)['facts_checked']==len(deck['facts'])
        if part is not None:
            assert any(f['path']==['borrow_sensitivity','annual_rate'] and f['value']==[0,.03,.1,.3][part] for f in deck['facts'].values())
        html=client.get('/api/jobs/'+jid+'/export/html',params=params);assert html.status_code==200 and 'connect-src' in html.text
