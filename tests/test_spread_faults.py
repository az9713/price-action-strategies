"""Explicit corrupt-input and lifecycle cases; no source/threshold exclusions."""
from copy import deepcopy
from types import SimpleNamespace
import gzip,json
import pytest
from backend.lab.config import Strategy,FAMILIES,identity,canonical
from backend.lab.data import atomic_json
from test_spread import spread,settings,context,evidence

@pytest.mark.parametrize('family,batch,ordinal',[('unknown',0,0),('break_of_structure',-1,0),('break_of_structure',True,0),('break_of_structure',0,-1),('break_of_structure',0,400),('break_of_structure',0,False)])
def test_invalid_proposal_coordinates_reject(spread,family,batch,ordinal):
    with pytest.raises(spread.SpreadError):spread.draw(settings(spread),family,batch,ordinal)

def test_selected_envelope_new_schema_and_wrong_family_fail_closed(spread,monkeypatch):
    with pytest.raises(ValueError):spread.SpreadSettings(per_family=100000,families=list(FAMILIES))
    b=spread.Balance(settings(spread),'break_of_structure')
    with pytest.raises(spread.SpreadError):b.accept(Strategy(family='breakout').model_dump())
    fields=Strategy.model_fields|{'unpublished_future_field':SimpleNamespace(default=0)}
    monkeypatch.setattr(spread,'Strategy',SimpleNamespace(model_fields=fields))
    with pytest.raises(spread.SpreadError):spread.published_rules()

@pytest.mark.parametrize('anchor',[None,False,'short','z'*64])
def test_reopen_rejects_invalid_external_anchor_before_files(spread,tmp_path,anchor):
    with pytest.raises(spread.SpreadError):spread.ProposalPlan.open(tmp_path/'absent',anchor)

def test_missing_or_malformed_manifest_and_cancelled_freeze_are_unsealed(spread,tmp_path):
    with pytest.raises(spread.SpreadError):spread.ProposalPlan.open(tmp_path/'absent','a'*64)
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));(plan.folder/'manifest.json').write_text('{broken',encoding='utf-8')
    with pytest.raises(spread.SpreadError):plan.verify()
    with pytest.raises(InterruptedError):spread.freeze_plan(tmp_path/'cancelled',settings(spread),cancel=lambda:True)
    assert not (tmp_path/'cancelled/manifest.json').exists()

@pytest.mark.parametrize('fault',['source','recipe','budget','family_inventory','missing_hash'])
def test_internally_invalid_publisher_manifest_rejects_even_under_its_own_new_anchor(spread,tmp_path,fault):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));manifest=deepcopy(plan.manifest)
    if fault=='source':manifest['core_hash']='f'*64
    elif fault=='recipe':manifest['recipe_hash']='0'*64
    elif fault=='budget':manifest['planned_proposals']+=1
    elif fault=='family_inventory':manifest['files']={}
    else:manifest['files']['break_of_structure'].pop('sha256')
    atomic_json(plan.folder/'manifest.json',manifest)
    # This is an independently constructed invalid publisher input, not a forged
    # claim that a changed plan retained its original external anchor.
    candidate=spread.ProposalPlan(plan.folder,manifest)
    with pytest.raises(spread.SpreadError):candidate.verify()

@pytest.mark.parametrize('fault',['early_end','bad_family','bad_ordinal','bad_count','missing_field','incomplete_config','wrong_config_family','extra_batch','bad_json','bad_gzip'])
def test_batch_parser_rejects_complete_and_partial_corrupt_records(spread,tmp_path,fault):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));path=plan.folder/'break_of_structure.jsonl.gz'
    rows=[dict(family='break_of_structure',batch=i,configurations=values) for i,values in enumerate(plan.batches('break_of_structure'))]
    if fault=='early_end':rows=rows[:-1]
    elif fault=='bad_family':rows[0]['family']='breakout'
    elif fault=='bad_ordinal':rows[0]['batch']=99
    elif fault=='bad_count':rows[0]['configurations'].pop()
    elif fault=='missing_field':rows[0].pop('configurations')
    elif fault=='incomplete_config':rows[0]['configurations'][0].pop('target')
    elif fault=='wrong_config_family':rows[0]['configurations'][0]=Strategy(family='breakout').model_dump()
    elif fault=='extra_batch':rows.append(rows[-1])
    raw=('\n'.join(canonical(row) for row in rows)+'\n').encode()
    if fault=='bad_json':raw=b'{broken\n'
    path.write_bytes(b'not gzip' if fault=='bad_gzip' else gzip.compress(raw,mtime=0))
    with pytest.raises(spread.SpreadError):list(plan.batches('break_of_structure'))

@pytest.mark.parametrize('patch',[
    {'extra':'ignored'}, {'dataset_id':'bad'}, {'dataset_manifest_hash':'bad'},
    {'primary_symbol':'lowercase'}, {'start':'2026-1-1'}, {'end':'2026-01-01'},
    {'news_calendar_id':'a'*64}, {'news_calendar_id':'a'*64,'news_calendar_hash':True},
])
def test_invalid_context_is_not_coerced_or_ignored(spread,patch):
    with pytest.raises(spread.SpreadError):spread.validated_context(context()|patch)

@pytest.mark.parametrize('fault',['not_structured','not_started','invalid_successor','extra_suffix'])
def test_bad_probe_replay_never_computes_new_signals(spread,tmp_path,fault):
    plan=spread.freeze_plan(tmp_path/'plan',settings(spread));events=[]
    spread.select(plan,context(),lambda cfg:evidence(40),events.append,authorize=lambda:None)
    bad=deepcopy(events)
    if fault=='not_structured':bad=[None]
    elif fault=='not_started':bad[3]['kind']='not_a_probe_start'
    elif fault=='invalid_successor':bad[4]['kind']='not_a_probe_result'
    else:bad.append(dict(kind='unconsumed_suffix'))
    calls=[]
    with pytest.raises(spread.SpreadError):spread.select(plan,context(),lambda cfg:calls.append(1),lambda e:None,authorize=lambda:None,replay=bad)
    assert calls==[]

def test_failed_and_within_batch_duplicates_are_not_recomputed_or_counted_as_success(spread,tmp_path,monkeypatch):
    s=spread.SpreadSettings(families=['break_of_structure'],timeframes=['1m'],per_family=2,batch_size=3,max_batches_per_family=2)
    a=spread.draw(s,'break_of_structure',0,0);b=deepcopy(a);b['direction']='short' if a['direction']!='short' else 'long'
    monkeypatch.setattr(spread,'draw',lambda settings,family,batch,ordinal:deepcopy([a,a,b][ordinal]))
    plan=spread.freeze_plan(tmp_path/'plan',s);calls=[];events=[]
    def probe(value):calls.append(identity(value));return evidence(0 if value==a else 40)
    result=spread.select(plan,context(),probe,events.append,authorize=lambda:None)
    assert calls==[identity(a),identity(b)]
    assert not result['complete'] and result['selected']==[b] and result['selection_manifest'] is None
    assert result['duplicate_proposals']==4 and result['probe_computations']==2 and result['visited_proposals']==6
    statuses=[v['status'] for e in events if e['kind']=='batch_finished' for v in e['outcomes']]
    assert statuses.count('duplicate')==4 and statuses.count('insufficient_signals')==1 and statuses.count('selected')==1
