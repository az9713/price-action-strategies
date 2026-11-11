"""Price-free complete generation and original-navigation contract edges."""
import importlib.util
from pathlib import Path
import pytest
from backend.lab.config import identity
from backend.lab.research import ResearchError
from backend.lab.store import StateError
from backend.lab.research_funnel_registration import register_generated_funnel,prepare_registration,workflow_status
from test_search_statistics_integration import client,headers

spec=importlib.util.spec_from_file_location('generation_boundary_public_fixtures',Path(__file__).with_name('research-funnel-public-api.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs;counts=fixtures.counts;blueprint=fixtures.blueprint


def test_generation_rejects_unvalidated_call_before_any_original_work(inputs):
    lab,request,*_=inputs;before=counts(lab)
    with pytest.raises(ResearchError):register_generated_funnel(lab,request)
    assert counts(lab)==before


@pytest.mark.parametrize('fault',['universe','outcomes','host_claim'])
def test_internal_generation_provenance_cannot_mislabel_the_frozen_cohort(inputs,fault):
    lab,request,*_=inputs;before=counts(lab)
    provenance=dict(configuration_universe_hash=identity([c.model_dump(mode='json') for c in request.configurations]),price_or_outcome_dependent=False,host_private_recipe_reproduced=False)
    provenance[dict(universe='configuration_universe_hash',outcomes='price_or_outcome_dependent',host_claim='host_private_recipe_reproduced')[fault]]=True
    with pytest.raises(ResearchError,match='provenance'):prepare_registration(lab,request,cohort_generation=provenance)
    assert counts(lab)==before


@pytest.mark.parametrize('page',[{'limit':0},{'limit':101},{'offset':-1},{'limit':True}])
def test_internal_workflow_navigation_retains_its_own_page_boundary(inputs,page):
    lab,request,*_=inputs;before=counts(lab)
    with pytest.raises(StateError,match='bounded'):workflow_status(lab,'invalid',**page)
    assert counts(lab)==before


@pytest.mark.parametrize('value',['not an object',[],23])
def test_public_generation_rejects_nonobject_json_without_creating_work(inputs,value):
    lab,request,*_=inputs;before=counts(lab)
    with client(lab) as c:
        response=c.post('/api/funnel-studies/generated',headers=headers(c),json=value)
        assert response.status_code==422,response.text
    assert counts(lab)==before


def test_complete_grid_public_registration_keeps_all_exact_variants_without_prices(inputs,monkeypatch):
    from backend.lab.sampling import common_grid
    from backend.lab.service import Lab
    lab,request,*_=inputs;payload=blueprint(request);payload['generation'].update(mode='common_grid',count=48)
    def forbidden(*args,**kwargs):raise AssertionError('Complete-grid registration must not decode prices.')
    monkeypatch.setattr(Lab,'_evaluation_input',forbidden)
    with client(lab) as c:
        response=c.post('/api/funnel-studies/generated',headers=headers(c),json=payload)
        assert response.status_code==201,response.text
        saved=lab.guard.study(response.json()['id'])['spec']
        expected=list(common_grid(['break_of_structure'],['1m']))
        assert saved['configurations']==expected and len(expected)==48
        assert saved['cohort_generation']['sampling']['unique']==48
        before=counts(lab);status=c.get('/api/studies/'+response.json()['id']+'/funnel-workflow')
        assert status.status_code==200 and status.json()['version_count']==48
        assert counts(lab)==before
    assert before['jobs']==before['trial_plans']==before['trial_attempts']==before['viewed_windows']==0
