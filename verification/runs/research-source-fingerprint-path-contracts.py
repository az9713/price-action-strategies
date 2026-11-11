"""Exact old/new source subjects and uncached edits, additions and removals."""
from pathlib import Path
import hashlib,os
import pytest
from backend.lab import research
from backend.lab.config import identity

def reference_subject():
    folder=Path(research.__file__).resolve().parent;root=folder.parents[1]
    files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.py')}
    for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock']:
        files[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    return dict(source_files=files,runtime=research._RUNTIME.copy())

@pytest.fixture
def source_tree(tmp_path,monkeypatch):
    folder=tmp_path/'backend/lab';folder.mkdir(parents=True)
    for name in ['research.py','engine.py','MixedCase.PY','.hidden.py','notes.txt']:
        (folder/name).write_bytes(('source '+name).encode())
    for name in ['RULEBOOK.md','strategy.schema.json','requirements.lock']:
        (tmp_path/name).write_bytes(('contract '+name).encode())
    monkeypatch.setattr(research,'__file__',str(folder/'research.py'))
    return tmp_path,folder

def test_actual_complete_subject_matches_original_path_algorithm():
    assert research.current_core_subject()==reference_subject()

def test_mixed_case_hidden_files_and_runtime_match_original_platform_rules(source_tree):
    assert research.current_core_subject()==reference_subject()
    assert 'backend/lab/.hidden.py' in research.current_core_subject()['source_files']

@pytest.mark.parametrize('name',['backend/lab/engine.py','RULEBOOK.md','strategy.schema.json','requirements.lock'])
def test_same_size_same_timestamp_edits_are_rehashed_and_refused(source_tree,monkeypatch,name):
    root,_=source_tree;before=research.current_core_subject()
    monkeypatch.setattr(research,'_LOADED_CORE_HASH',identity(before))
    research.require_current_source()
    path=root/name;stamp=path.stat();old=path.read_bytes();path.write_bytes(bytes([old[0]^1])+old[1:])
    os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
    assert path.stat().st_size==stamp.st_size and path.stat().st_mtime_ns==stamp.st_mtime_ns
    assert research.current_core_subject()==reference_subject()!=before
    with pytest.raises(research.ResearchError,match='Restart'):research.require_current_source()

def test_added_and_removed_numerical_sources_change_the_complete_subject(source_tree):
    _,folder=source_tree;before=research.current_core_subject()
    added=folder/'added.py';added.write_bytes(b'new numerical source')
    assert research.current_core_subject()==reference_subject()!=before
    added.unlink();assert research.current_core_subject()==before
    (folder/'engine.py').unlink();assert research.current_core_subject()==reference_subject()!=before

def test_source_directory_or_missing_contract_cannot_be_silently_omitted(source_tree):
    root,folder=source_tree;(folder/'invalid.py').mkdir()
    with pytest.raises(OSError):research.current_core_subject()
    (folder/'invalid.py').rmdir();(root/'requirements.lock').unlink()
    with pytest.raises(OSError):research.current_core_subject()

def test_returned_subject_remains_detached_and_every_call_rereads_source(source_tree):
    root,folder=source_tree;value=research.current_core_subject()
    value['runtime']['python']='caller mutation';value['source_files'].clear()
    assert research.current_core_subject()==reference_subject()
    path=folder/'engine.py';original=path.read_bytes();path.write_bytes(b'changed')
    assert research.current_core_subject()==reference_subject()
    path.write_bytes(original);assert research.current_core_subject()==reference_subject()

@pytest.mark.parametrize('name',['backend/lab/engine.py','RULEBOOK.md','strategy.schema.json','requirements.lock'])
def test_saved_read_refuses_actual_same_timestamp_file_edit_before_return(source_tree,monkeypatch,name):
    root,_=source_tree
    monkeypatch.setattr(research,'_LOADED_CORE_HASH',identity(research.current_core_subject()))
    @research.checked_saved_read
    def read():
        path=root/name;stamp=path.stat();old=path.read_bytes()
        path.write_bytes(bytes([old[0]^1])+old[1:]);os.utime(path,ns=(stamp.st_atime_ns,stamp.st_mtime_ns))
        with research.saved_source_read():research.require_current_source()
        return 'must not leave the source-check boundary'
    with pytest.raises(research.ResearchError,match='Restart'):read()
    assert not research._active_saved_source_read()
