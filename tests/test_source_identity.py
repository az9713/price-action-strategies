import pytest
from backend.lab import research

def test_loaded_identity_does_not_silently_follow_edited_disk(monkeypatch):
    original=research.core_hash()
    monkeypatch.setattr(research,'current_core_hash',lambda:'edited-files')
    assert research.core_hash()==original
    with pytest.raises(research.ResearchError,match='Restart'): research.require_current_source()

def test_numerical_subject_includes_rulebook_schema_locks_and_actual_runtime():
    from backend.lab.config import identity
    subject=research.core_subject()
    assert research.core_hash()==identity(subject)
    assert {'RULEBOOK.md','strategy.schema.json','requirements.lock','backend/lab/engine.py'}<=set(subject['source_files'])
    assert {'python','numpy','pandas','exchange_calendars','pydantic','fastapi'}<=set(subject['runtime'])
    subject['runtime']['python']='caller mutation'
    assert research.core_subject()['runtime']['python']!='caller mutation'

def test_changed_rule_contract_invalidates_current_source_check(monkeypatch):
    subject=research.core_subject();subject['source_files']['RULEBOOK.md']='0'*64
    monkeypatch.setattr(research,'current_core_subject',lambda:subject)
    with pytest.raises(research.ResearchError,match='Restart'): research.require_current_source()

def test_corrupt_saved_numerical_subject_is_not_silently_reused(tmp_path):
    import json
    from backend.lab.service import Lab
    from backend.lab.store import StateError
    lab=Lab(tmp_path);path=tmp_path/'data/subjects'/(research.core_hash()+'.json')
    value=json.loads(path.read_text());value['runtime']['python']='altered'
    path.write_text(json.dumps(value))
    with pytest.raises(StateError,match='subject was modified'): Lab(tmp_path)
