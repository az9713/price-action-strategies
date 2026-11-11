"""Saved-only source boundaries must reject edits and never leak across requests."""
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
import pytest
from backend.lab import research

@pytest.fixture
def checks(monkeypatch):
    values=dict(calls=0,changed=False)
    def current():
        values['calls']+=1
        return 'edited source' if values['changed'] else research.core_hash()
    monkeypatch.setattr(research,'current_core_hash',current)
    return values

def test_saved_read_checks_full_source_at_entry_and_exit_but_never_caches_between_calls(checks):
    @research.checked_saved_read
    def read():
        for _ in range(100):research.require_current_source()
        with research.saved_source_read():research.require_current_source()
        return 'complete original'
    assert read()=='complete original' and checks['calls']==2
    assert read()=='complete original' and checks['calls']==4
    research.require_current_source();assert checks['calls']==5

def test_changed_source_refuses_entry_before_any_saved_read_body(checks):
    checks['changed']=True;entered=[]
    @research.checked_saved_read
    def read():entered.append(True)
    with pytest.raises(research.ResearchError,match='Restart'):read()
    assert entered==[] and not research._active_saved_source_read()

def test_edit_during_nested_saved_inspection_refuses_return_at_outer_closing_boundary(checks):
    @research.checked_saved_read
    def read():
        with research.saved_source_read():
            checks['changed']=True
            research.require_current_source()
        return 'must never be certified'
    with pytest.raises(research.ResearchError,match='Restart'):read()
    assert checks['calls']==2 and not research._active_saved_source_read()
    with pytest.raises(research.ResearchError):research.require_current_source()
    assert checks['calls']==3

@pytest.mark.parametrize('error',[ValueError('corrupt original'),InterruptedError('canceled saved read'),KeyboardInterrupt()])
def test_failure_and_cancellation_close_source_scope_and_preserve_original_exception(checks,error):
    @research.checked_saved_read
    def read():raise error
    with pytest.raises(type(error)):read()
    assert checks['calls']==2 and not research._active_saved_source_read()
    checks['changed']=True
    with pytest.raises(research.ResearchError):research.require_current_source()

def test_context_inherited_by_another_thread_does_not_suppress_its_checks(checks):
    with research.saved_source_read():
        context=copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(context.run,research.require_current_source).result()
        assert checks['calls']==2
    assert checks['calls']==3

def test_context_copy_cannot_keep_a_completed_scope_active(checks):
    with research.saved_source_read():context=copy_context()
    checks['changed']=True
    with pytest.raises(research.ResearchError):context.run(research.require_current_source)
    assert checks['calls']==3 and not research._active_saved_source_read()

def test_caught_nested_failure_still_checks_source_before_outer_return(checks):
    with pytest.raises(research.ResearchError):
        with research.saved_source_read():
            try:
                with research.saved_source_read():
                    checks['changed']=True
                    raise ValueError('original failure caught by outer reader')
            except ValueError:pass
    assert checks['calls']==2 and not research._active_saved_source_read()
