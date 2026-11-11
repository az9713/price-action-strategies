"""Restartable preparation: real committed files, orphan retention and exact output bytes."""
from pathlib import Path
from copy import deepcopy
import hashlib,json
import pytest
from backend.lab.spread import SpreadSettings,SpreadError

@pytest.fixture
def preparation():
    from backend.lab import spread_preparation
    return spread_preparation

def settings():return SpreadSettings(families=['breakout','break_of_structure'],timeframes=['1m','5m'],per_family=2,batch_size=5,max_batches_per_family=3)
def run(module,folder,events,**kwargs):
    return module.prepare_plan(folder/'proposals',folder/'batches',settings(),binding='a'*64,committed=events,commit=events.append,**kwargs)
def files(plan):return {p.name:p.read_bytes() for p in plan.folder.iterdir()}

def test_complete_preparation_has_every_proposal_and_requires_no_prices(preparation,tmp_path):
    events=[];result=run(preparation,tmp_path/'one',events)
    assert result['generated_batches']==6 and result['reused_batches']==0
    plan=result['plan'];assert plan.manifest['planned_proposals']==30
    assert len(events)==6 and [(r['family'],r['batch']) for r in events]==[(f,n) for f in settings().families for n in range(3)]
    for family in settings().families:assert [len(c) for c in plan.batches(family)]==[5,5,5]
    repeated=run(preparation,tmp_path/'two',[])
    assert plan.plan_id==repeated['plan'].plan_id and files(plan)==files(repeated['plan'])

@pytest.mark.parametrize('after_commit',[False,True])
def test_batch_boundary_crash_does_not_redraw_committed_versions(preparation,tmp_path,monkeypatch,after_commit):
    events=[];crashed=[];folder=tmp_path/'interrupted'
    def commit(event):
        if after_commit:events.append(event)
        if not crashed:crashed.append(True);raise InterruptedError('Owned batch boundary crash')
        if not after_commit:events.append(event)
    with pytest.raises(InterruptedError):preparation.prepare_plan(folder/'proposals',folder/'batches',settings(),binding='a'*64,committed=events,commit=commit)
    old_files={p.relative_to(folder).as_posix():p.read_bytes() for p in folder.rglob('*.gz')}
    from backend.lab import spread
    original=spread.draw;drawn=[]
    def counted(s,f,b,o):drawn.append((f,b,o));return original(s,f,b,o)
    monkeypatch.setattr(spread,'draw',counted)
    result=run(preparation,folder,events)
    assert result['reused_batches']==int(after_commit) and result['generated_batches']==6-int(after_commit)
    assert len(drawn)==5*(6-int(after_commit))
    reference=run(preparation,tmp_path/'reference',[]);assert files(result['plan'])==files(reference['plan'])
    if after_commit:
        for name,raw in old_files.items():assert (folder/name).read_bytes()==raw
    else:
        preserved=list((folder/'preparation-orphans').rglob('*.gz'));assert preserved
        assert {p.read_bytes() for p in preserved}>={*old_files.values()}

def test_complete_resume_reuses_every_batch_and_checks_external_plan_identity(preparation,tmp_path,monkeypatch):
    events=[];folder=tmp_path/'owned';first=run(preparation,folder,events)
    from backend.lab import spread
    def forbidden(*a):raise AssertionError('A committed proposal was redrawn')
    monkeypatch.setattr(spread,'draw',forbidden)
    resumed=run(preparation,folder,events,expected_plan_id=first['plan'].plan_id)
    assert resumed['generated_batches']==0 and resumed['reused_batches']==6 and files(first['plan'])==files(resumed['plan'])
    with pytest.raises(SpreadError):run(preparation,folder,events,expected_plan_id='f'*64)

@pytest.mark.parametrize('fault',['bytes','missing','reorder','duplicate','binding','settings','source','foreign'])
def test_committed_corruption_or_changed_contract_rejects_before_new_draws(preparation,tmp_path,monkeypatch,fault):
    events=[];folder=tmp_path/'owned';first=run(preparation,folder,events);records=deepcopy(events)
    if fault in {'bytes','missing'}:
        p=folder/'batches'/records[0]['relative_path']
        if fault=='bytes':raw=p.read_bytes();p.write_bytes(b'X'+raw[1:])
        else:p.unlink()
    elif fault=='reorder':records=list(reversed(records))
    elif fault=='duplicate':records.append(records[0])
    elif fault=='binding':records[0]['contract_hash']='0'*64
    elif fault=='settings':records[0]['proposal_count']+=1
    elif fault=='source':records[0]['core_hash']='f'*64
    else:(folder/'batches/foreign.gz').write_bytes(b'foreign')
    from backend.lab import spread
    def forbidden(*a):raise AssertionError('Corrupt committed preparation reached draws')
    monkeypatch.setattr(spread,'draw',forbidden)
    with pytest.raises(SpreadError):run(preparation,folder,records,expected_plan_id=first['plan'].plan_id)

def test_cancel_during_assembly_keeps_committed_batches_and_resumes(preparation,tmp_path):
    events=[];folder=tmp_path/'owned'
    with pytest.raises(InterruptedError):run(preparation,folder,events,cancel=lambda:len(events)==6)
    assert len(events)==6 and not (folder/'proposals/manifest.json').exists()
    resumed=run(preparation,folder,events);assert resumed['generated_batches']==0 and resumed['reused_batches']==6
    reference=run(preparation,tmp_path/'reference',[]);assert files(resumed['plan'])==files(reference['plan'])

def test_uncommitted_manifest_is_verified_before_seal_and_never_replaces_a_frozen_plan(preparation,tmp_path):
    events=[];folder=tmp_path/'owned';first=run(preparation,folder,events)
    unanchored=run(preparation,folder,events);assert unanchored['plan'].plan_id==first['plan'].plan_id
    p=folder/'proposals/manifest.json';value=json.loads(p.read_text());value['planned_proposals']+=1;p.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(SpreadError):run(preparation,folder,events,expected_plan_id=first['plan'].plan_id)

def test_batch_changed_after_commit_validation_cannot_become_a_new_sealed_source(preparation,tmp_path):
    events=[];folder=tmp_path/'owned'
    def commit(record):
        events.append(record)
        if len(events)==6:
            path=folder/'batches'/events[0]['relative_path'];raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
    with pytest.raises(SpreadError):preparation.prepare_plan(folder/'proposals',folder/'batches',settings(),binding='a'*64,committed=events,commit=commit)
    assert not (folder/'proposals/manifest.json').exists()
