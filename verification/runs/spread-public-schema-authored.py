"""Published machine-readable spread contract agrees with the actual API models."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_spread_probe import owned
from test_spread_api import client
from backend.lab.models import SpreadExperiment,SpreadContinuation
from backend.lab.spread import SpreadSettings

def test_spread_schemas_are_published_in_saved_contract_and_live_schema(owned):
 expected=dict(spread_settings=SpreadSettings.model_json_schema(),spread_run=SpreadExperiment.model_json_schema(),spread_continuation=SpreadContinuation.model_json_schema())
 saved=json.loads((Path.cwd()/'strategy.schema.json').read_text(encoding='utf-8'))
 assert {k:saved.get(k) for k in expected}==expected,'Saved spread machine-readable contracts are missing or differ from actual models'
 with client(owned[0]) as c:
  response=c.get('/api/schema');assert response.status_code==200
  assert {k:response.json().get(k) for k in expected}==expected
 settings=expected['spread_settings']['properties']
 assert settings['per_family']['default']==4000 and settings['batch_size']['default']==400 and settings['max_batches_per_family']['default']==8000
 assert settings['minimum_signals']['minimum']==40 and settings['seed']['type']=='integer'
 assert expected['spread_continuation']['additionalProperties'] is False
