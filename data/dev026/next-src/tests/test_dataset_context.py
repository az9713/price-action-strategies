"""Frozen minimal dataset provenance: independent expected values, workers and saved exports."""
from copy import deepcopy
from io import StringIO
import csv,json,shutil
import pytest
from backend.lab.config import Strategy,identity
from backend.lab.data import DataError
from backend.lab.models import Search,PortfolioExperiment,BenchmarkExperiment,ControlsExperiment,BehaviorExperiment,AblationExperiment,BorrowSensitivity
from backend.lab.worker import Worker
from backend.lab.presenter import build_deck
from test_api import client_lab,seed,payload
from test_portfolio_studies import study_data,request,run

def expected(m):
 return dict(policy_version=1,dataset_id=m['id'],dataset_manifest_hash=identity(m),input_kind=m['metadata'].get('input_kind','unknown'),source=m['metadata'].get('provider',m['metadata'].get('source','Not recorded')),symbols=sorted(m['quality']['symbols']))

def make(client_lab,kind):
 client,lab=client_lab;m=seed(lab);base=payload(m)
 table={
  'experiment':('/api/experiments',base),
  'search':('/api/searches',base|dict(count=1,families=['break_of_structure'],timeframes=['1m'],sampling_policy=dict(mode='common_random'),statistics=dict(effective_trials=[1]))),
  'portfolio':('/api/portfolios',{k:v for k,v in base.items() if k!='strategy'}|dict(configurations=[Strategy().model_dump()])),
  'benchmark':('/api/benchmarks',{k:v for k,v in base.items() if k!='strategy'}),
  'controls':('/api/controls',base|dict(replicas=2)),
  'behavior':('/api/behavior',{k:v for k,v in base.items() if k not in {'strategy','costs','portfolio','news_dates','news_calendar_id'}}|dict(timeframes=['1m'],shift_replicas=2)),
  'ablation':('/api/ablations',base|dict(field='target',alternatives=['3R'])),
  'borrow_sensitivity':('/api/borrow-sensitivity',base),
 }
 path,body=table[kind];response=client.post(path,json=body);assert response.status_code==202,response.text
 return client,lab,m,response.json()

@pytest.mark.parametrize('kind',['experiment','search','portfolio','benchmark','controls','behavior','ablation','borrow_sensitivity'])
def test_every_analysis_freezes_before_queue_and_publishes_exact_context(client_lab,kind):
 client,lab,m,job=make(client_lab,kind);context=expected(m)
 assert job['payload']['dataset_context']==context
 assert Worker(lab).run_once();state=lab.store.job(job['id']);assert state['status']=='completed',state['error']
 saved=lab.result(job['id']);assert saved['dataset_context']==context
 if 'report' in saved:assert saved['report']['dataset_context']==context
 for row in saved.get('rows',[]):assert lab.report(job['id'],row['part'])['dataset_context']==context
 document=saved.get('report',saved);deck=build_deck([('original.json',json.dumps(document).encode())])
 facts={tuple(f['path']):f['value'] for f in deck['facts'].values()}
 for key in ['input_kind','source','dataset_manifest_hash']:assert facts[('dataset_context',key)]==context[key]
 assert facts[('dataset_context','symbols',0)]=='SPY'
 assert facts[('dataset_context','symbols')]==['SPY']
 # Reread/export solely from committed evidence after removing live dataset files.
 target=(lab.datasets_root/m['id']).resolve();assert target.is_relative_to(lab.datasets_root.resolve())
 shutil.rmtree(target)
 assert client.get('/api/jobs/'+job['id']+'/export/presentation.json').status_code==200
 assert lab.result(job['id'])['dataset_context']==context
 if kind=='search':
  for diagnostic in ['search-screen','search-statistics']:
   response=client.get('/api/jobs/'+job['id']+'/'+diagnostic+'/export/csv');assert response.status_code==200
   rows=list(csv.DictReader(StringIO(response.text)));assert rows
   for row in rows:assert (row['input_kind'],row['data_source'],json.loads(row['symbols']),row['dataset_manifest_hash'])==('synthetic',context['source'],['SPY'],context['dataset_manifest_hash'])
 if kind in ['ablation','borrow_sensitivity']:
  rows=list(csv.DictReader(StringIO(client.get('/api/jobs/'+job['id']+'/export/csv').text)));assert rows
  assert all(row['input_kind']=='synthetic' and json.loads(row['symbols'])==['SPY'] for row in rows)

@pytest.mark.parametrize('mode',['independent','portfolio'])
def test_actual_screen_and_consumed_final_keep_registered_context(study_data,mode):
 lab,m,_=study_data;context=expected(m);study=lab.register_study(request(m,mode))
 assert study['spec']['dataset_context']==context
 screen=lab.screen(study['id']);assert screen['payload']['dataset_context']==context
 result=run(lab,screen);assert result['dataset_context']==context and result['candidates']
 for row in result['rows']:
  for phase in ['discovery','validation']:assert lab.report(screen['id'],row['part'],phase)['dataset_context']==context
 final=lab.final(study['id']);assert final['payload']['dataset_context']==context
 result=run(lab,final);assert result['dataset_context']==context
 assert lab.guard.study(study['id'])['status']=='final_complete'
 # This frozen positive control exercises metadata on actual trade rows, in
 # addition to the unchanged zero-trade browser controls.
 from fastapi.testclient import TestClient
 from backend.lab.api import create_app
 with TestClient(create_app(lab.root,run_worker=False),base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
  report=lab.report(final['id'],0);assert report['trades']
  response=client.get('/api/jobs/'+final['id']+'/export/csv?part=0');assert response.status_code==200
  rows=list(csv.DictReader(StringIO(response.text)));assert len(rows)==len(report['trades'])
  assert all(row['dataset_id']==m['id'] and row['dataset_manifest_hash']==context['dataset_manifest_hash'] and row['input_kind']=='synthetic' and row['data_source']==context['source'] and json.loads(row['symbols'])==context['symbols'] for row in rows)

@pytest.mark.parametrize('field,value',[('symbols',['QQQ']),('input_kind','historical'),('source','other'),('dataset_id','0'*24),('dataset_manifest_hash','0'*64),('policy_version',2)])
def test_corrupt_context_is_rejected_before_financing_or_price_reads(client_lab,monkeypatch,field,value):
 _,lab,m,job=make(client_lab,'search');p=deepcopy(lab.store.job(job['id'])['payload']);p['dataset_context'][field]=value
 bad=lab.store.create_job('search',p)
 # Retire the valid unexecuted sibling, so the worker reaches this exact control.
 lab.store.cancel(job['id'])
 def forbidden(*a,**k):raise AssertionError('Numerical or financing input was read before context validation')
 monkeypatch.setattr(lab,'borrow_input',forbidden);monkeypatch.setattr(lab,'_evaluation_input',forbidden)
 assert Worker(lab).run_once();state=lab.store.job(bad['id']);assert state['status']=='failed'
 assert 'dataset context' in state['error'].lower(),state['error']

@pytest.mark.parametrize('kind',['synthetic','historical','historical_market_data','user_import','unrecognized'])
def test_context_whitelist_and_raw_kind_are_preserved(client_lab,kind):
 from backend.lab.dataset_context import freeze_context,validate_context,csv_context
 _,lab=client_lab;m=seed(lab);m=deepcopy(m);m['metadata'].update(input_kind=kind,source='=1+1',future_dividend='SECRET-FUTURE',password='SECRET-PASSWORD');m['actions']=[dict(future='DO-NOT-EXPORT')]
 context=freeze_context(m)
 assert set(context)=={'policy_version','dataset_id','dataset_manifest_hash','input_kind','source','symbols'}
 assert context==expected(m) and validate_context(context,manifest=m)==context
 serialized=json.dumps(context);assert not any(v in serialized for v in ['SECRET-FUTURE','SECRET-PASSWORD','DO-NOT-EXPORT'])
 assert csv_context(context)['data_source']=="'=1+1"

@pytest.mark.parametrize('change',[dict(extra='forbidden'),dict(symbols=[]),dict(symbols=['SPY','SPY']),dict(symbols=['spy']),dict(source=3),dict(input_kind=None),dict(policy_version=True),dict(dataset_id='bad'),dict(dataset_manifest_hash='bad'),dict(source='a\nsecret')])
def test_malformed_present_context_fails_closed(client_lab,change):
 from backend.lab.dataset_context import validate_context
 _,lab=client_lab;context=expected(seed(lab))|change
 with pytest.raises(DataError,match='[Dd]ataset context'):validate_context(context)

def test_absent_metadata_is_unknown_and_legacy_is_not_fabricated(client_lab):
 from backend.lab.dataset_context import freeze_context,csv_context
 _,lab=client_lab;m=seed(lab);m=deepcopy(m);m['metadata']={}
 assert freeze_context(m)['input_kind']=='unknown' and freeze_context(m)['source']=='Not recorded'
 assert csv_context(None)==dict(input_kind='not_recorded',data_source='not_recorded',symbols='not_recorded',dataset_manifest_hash='not_recorded')

@pytest.mark.parametrize('value',[None,[],True,'bad'])
def test_non_object_context_rejects(value):
 from backend.lab.dataset_context import validate_context
 with pytest.raises(DataError,match='Dataset context'):validate_context(value)

@pytest.mark.parametrize('change',[dict(source='x'*241),dict(input_kind='x'*129),dict(source=''),dict(symbols=['Z','A']),dict(symbols=['A']*21)])
def test_context_limits_and_canonical_order(client_lab,change):
 from backend.lab.dataset_context import validate_context
 _,lab=client_lab
 with pytest.raises(DataError,match='Dataset context'):validate_context(expected(seed(lab))|change)

def test_legacy_and_corrupt_presenter_context_are_explicit(client_lab):
 from backend.lab.presenter import PresentationError
 client,lab,m,job=make(client_lab,'experiment');Worker(lab).run_once();report=lab.report(job['id'])
 original=deepcopy(report);original.pop('dataset_context')
 deck=build_deck([('legacy.json',json.dumps(original).encode())]);assert any(p['title']=='Dataset context not recorded' for p in deck['pages'])
 assert all(not f['path'] or f['path'][0]!='dataset_context' for f in deck['facts'].values())
 report['dataset_context']['policy_version']=True
 with pytest.raises(PresentationError,match='Dataset context'):build_deck([('corrupt.json',json.dumps(report).encode())])

def test_missing_context_remains_absent_for_original_jobs(client_lab):
 _,lab,m,job=make(client_lab,'experiment');p=deepcopy(lab.store.job(job['id'])['payload']);p.pop('dataset_context')
 assert lab.dataset_context_input(p) is None
 assert lab.dataset_context_input(p|dict(dataset_context=expected(m)))==expected(m)
 p['dataset_manifest_hash']='0'*64
 with pytest.raises(DataError,match='Dataset context'):lab.dataset_context_input(p|dict(dataset_context=expected(m)))

@pytest.mark.parametrize('symbols',[None,{},[],['bad symbol'],[5],['A'*16],['SPY']*21])
def test_instrument_list_formatters_reject_malformed_values_independently(symbols):
 from backend.lab.presenter import format_value,PresentationError
 from backend.lab.presentation_audit import independent_format,PresentationAuditError
 with pytest.raises(PresentationError):format_value(symbols,'symbol_list')
 with pytest.raises(PresentationAuditError):independent_format(symbols,'symbol_list')

def test_complete_twenty_instrument_list_has_exact_independent_rendering():
 from backend.lab.presenter import format_value
 from backend.lab.presentation_audit import independent_format
 symbols=['T'+str(i).zfill(2) for i in range(20)];wanted=', '.join(symbols)
 assert format_value(symbols,'symbol_list')==wanted==independent_format(symbols,'symbol_list')

def test_existing_twenty_one_instrument_import_is_not_restricted_by_metadata(client_lab):
 import pandas as pd
 from conftest import minute_frame
 client,lab=client_lab
 base=minute_frame('2026-11-02');symbols=['U'+str(i).zfill(2) for i in range(21)]
 frame=pd.concat([base.assign(symbol=symbol) for symbol in symbols],ignore_index=True)
 response=client.post('/api/imports',files={'file':('synthetic-universe.csv',frame.to_csv(index=False).encode(),'text/csv')},data={'start':'2026-11-02','end':'2026-11-02','input_kind':'synthetic'})
 assert response.status_code==201 and response.json()['quality']['eligible']
 manifest=response.json();created=client.post('/api/experiments',json=dict(dataset_id=manifest['id'],start='2026-11-02',end='2026-11-02'))
 assert created.status_code==202,created.text
 assert created.json()['payload']['dataset_context']['symbols']==symbols
 assert Worker(lab).run_once();jid=created.json()['id'];assert lab.store.job(jid)['status']=='completed'
 report=lab.report(jid);assert report['dataset_context']['symbols']==symbols
 deck=build_deck([('large-universe.json',json.dumps(report).encode())]);facts={tuple(f['path']):f for f in deck['facts'].values()}
 assert facts[('dataset_context','symbols')]['value']==symbols
 assert facts[('dataset_context','symbols')]['text']=='21 instruments; see indexed pages'
 for index,symbol in enumerate(symbols):assert facts[('dataset_context','symbols',index)]['value']==symbol
