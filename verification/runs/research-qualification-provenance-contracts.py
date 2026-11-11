"""Original authority is distinct from use of a derived source-row locator."""
from contextlib import contextmanager
import importlib.util
from pathlib import Path
from backend.lab.research_qualification_source import qualification_snapshot

spec=importlib.util.spec_from_file_location('provenance_authored_store',Path(__file__).with_name('research-owned-qualification-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
positive_originals=fixtures.positive_originals;clone_authored=fixtures.clone_authored


def test_actual_diagnostic_source_locator_usage_is_reported_without_granting_cache_authority(positive_originals,tmp_path,monkeypatch):
    lab=clone_authored(positive_originals['ready'],tmp_path);snapshot=lab.result_index.snapshot;observed=[]
    @contextmanager
    def locate(*args,**kwargs):
        observed.append(args[0])
        with snapshot(*args,**kwargs) as original:yield original
    monkeypatch.setattr(lab.result_index,'snapshot',locate)
    report=qualification_snapshot(lab,positive_originals['study_id'])
    assert observed and report['state']=='awaiting_controls' and report['candidate_ids']==[]
    authority=report['source_authority']
    assert authority['derived_result_views_used'] is True
    assert authority['diagnostic_source_locator_derived_views_used'] is True
    assert authority['derived_result_views_used_for_authority'] is False
    assert authority['original_saved_accounts_verified'] is True
