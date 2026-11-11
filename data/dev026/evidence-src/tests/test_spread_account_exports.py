"""Strict frozen spread inputs and complete primary discovery/account exports."""
from pathlib import Path
import csv,io,json,os
import pytest
from pydantic import ValidationError
from test_spread_probe import owned
from test_spread_worker import request
from test_spread_account_handoff import qualified
from test_spread_api import client
from backend.lab.worker import Worker

@pytest.mark.parametrize('updates',[dict(seed=True),dict(seed=1.0),dict(seed=1,settings={'seed':True}),dict(seed=1,settings={'seed':1.0}),dict(settings={'minimum_signals':39})])
def test_frozen_spread_inputs_reject_coerced_seeds_and_less_than_forty_signals(updates):
 with pytest.raises(ValidationError):request(dict(id='a'*24),**updates)

def test_complete_saved_statistics_screen_and_all_trade_exports_keep_original_cohort(owned,monkeypatch):
 lab,parent,selection=qualified(owned);child=lab.create_spread_accounts(parent['id']);assert Worker(lab).run_once();result=lab.result(child['id']);report=lab.report(child['id'],0)
 def forbidden(*a,**k):raise AssertionError('Saved exports reopened raw prices or qualification')
 monkeypatch.setattr('backend.lab.service.load_window',forbidden);monkeypatch.setattr(lab,'spread_signal_probe',forbidden)
 with client(lab) as c:
  captures={}
  for name in ['search-statistics','search-screen']:
   for format in ['json','csv']:
    response=c.get('/api/jobs/'+child['id']+'/'+name+'/export/'+format);assert response.status_code==200,response.text;captures[name+'.'+format]=response.text
   saved=json.loads(captures[name+'.json']);assert saved==result[name.replace('-','_')]
   rows=list(csv.DictReader(io.StringIO(captures[name+'.csv'])));assert rows and {int(r['part']) for r in rows}=={0}
   assert all(r['config_id']==report['config_id'] and r['dataset_id']==parent['payload']['dataset_id'] for r in rows)
  screen=result['search_screen'];assert screen['settings']['mode']=='spread_selected' and screen['settings']['minimum_signals']==40
  assert screen['accounts'][0]['signal_count']>=40 and screen['accounts'][0]['net_profit']==report['metrics']['net_profit']
  assert screen['accounts'][0]['initial_gates_passed'] is False and report['metrics']['net_profit']<0
  response=c.get('/api/jobs/'+child['id']+'/export/csv',params={'part':0});assert response.status_code==200,response.text;captures['trades.csv']=response.text
  rows=list(csv.DictReader(io.StringIO(response.text)));assert len(rows)==len(report['trades'])>0
  assert [r['id'] for r in rows]==[t['id'] for t in report['trades']]
  assert sum(float(r['net_pnl']) for r in rows)==pytest.approx(sum(t['net_pnl'] for t in report['trades']),abs=1e-7)
  if os.environ.get('PA_EVIDENCE_RUN_DIR'):
   p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-spread-account-exports';p.mkdir()
   captures.update({'account.json':json.dumps(report),'complete-result.json':json.dumps(result),'frozen-inputs.json':json.dumps(lab.store.job_inputs(child['id']))})
   for name,text in captures.items():(p/name).write_text(text,encoding='utf-8')
