"""Scope/identity/race authority boundaries, supplementing real joint accounts."""
import pytest
from backend.lab.models import Study
from backend.lab.data import save_dataset
from backend.lab.research import ResearchError
from test_portfolio_studies import study_data,request,run,DAYS


def test_unknown_study_lookup_and_final_start_never_create_an_access_record(study_data):
    lab,m,_=study_data
    with pytest.raises(ResearchError):lab.guard.study('missing')
    with pytest.raises(ResearchError):lab.guard.begin_final('missing','not-a-job',m)
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==0


def test_reversed_authority_read_is_rejected_without_recording_it(study_data):
    lab,_,_=study_data
    with pytest.raises(ResearchError):lab.guard.access(['SPY'],DAYS[1],DAYS[0],'invalid-reversed-read')
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM viewed_windows').fetchone()[0]==0


@pytest.mark.parametrize('side',['start','end'])
def test_authority_itself_rejects_outside_manifest_windows(study_data,side):
    lab,m,_=study_data;body=request(m).model_dump(mode='json')
    if side=='start':body['discovery']['start']='2026-10-02'
    else:body['holdout']['end']='2026-10-13'
    with pytest.raises(ResearchError):lab.guard.register(Study(**body),m)
    assert lab.guard.studies()==[]


def test_different_instruments_can_have_independently_protected_windows(study_data):
    lab,m,raw=study_data;first=lab.register_study(request(m))
    raw=raw.copy();raw['symbol']='QQQ'
    other=save_dataset(lab.datasets_root,raw,{'input_kind':'synthetic','source':'Second explicit instrument scope'},start=DAYS[0],end=DAYS[-1])
    second=lab.register_study(request(other));assert first['id']!=second['id'] and len(lab.guard.studies())==2
    for symbol in ['SPY','QQQ']:
        with pytest.raises(ResearchError):lab.guard.access([symbol],DAYS[4],DAYS[5],'protected-preview')


def test_duplicate_completed_screen_cannot_replace_the_candidate_event(study_data):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];job=lab.screen(sid);run(lab,job);before=lab.guard.study(sid)
    with pytest.raises(ResearchError):lab.guard.screened(sid,before['spec']['screening_report_hash'],before['spec']['candidates'])
    assert lab.guard.study(sid)==before
    assert len([e for e in lab.store.events(sid) if e['kind']=='candidates_frozen'])==1


def test_core_change_between_registration_and_screen_completion_cannot_freeze_candidates(study_data,monkeypatch):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];spec=lab.guard.study(sid)['spec']
    monkeypatch.setattr('backend.lab.research.core_hash',lambda:'changed-after-computation')
    with pytest.raises(ResearchError):lab.guard.screened(sid,'transition-only-not-a-winning-account',[spec['configurations']])
    assert lab.guard.study(sid)['status']=='registered'


def test_wrong_job_cannot_mark_final_complete(study_data):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id']
    with pytest.raises(ResearchError):lab.guard.finish_final(sid,'unrelated-job',True)
    assert lab.guard.study(sid)['status']=='registered'


def test_public_reservation_audit_matches_actual_reserved_identity_without_consuming(study_data):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];run(lab,lab.screen(sid));job=lab.final(sid);spec=lab.guard.study(sid)['spec']
    lab.guard.verify_final_reservation(spec,sid,job['id'])
    assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
