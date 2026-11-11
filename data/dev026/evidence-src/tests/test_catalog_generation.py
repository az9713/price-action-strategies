"""Regeneration must preserve the entire normative acceptance inventory."""
import json
import hashlib
from pathlib import Path
from verification import build_catalog


def test_generated_catalog_preserves_every_required_case_and_matrix(tmp_path,monkeypatch):
    root=Path(__file__).resolve().parents[1]
    canonical=json.loads((root/'verification/catalog.json').read_text(encoding='utf-8'))
    monkeypatch.setattr(build_catalog,'ROOT',tmp_path)
    build_catalog.build()
    actual=json.loads((tmp_path/'catalog.json').read_text(encoding='utf-8'))
    assert actual==canonical
    assert len(actual['cases'])==422
    assert len([x for x in actual['cases'] if x['id'].startswith('MATRIX-')])==120
    # Existing implementation references must never be erased by regeneration.
    mapping=tmp_path/'implementation-map.json'
    mapping.write_text('{"sentinel":"keep existing references"}',encoding='utf-8')
    build_catalog.build()
    assert json.loads(mapping.read_text())=={'sentinel':'keep existing references'}


def test_expansion_preserves_prior351_and378_catalogs_byte_for_byte():
    root=Path(__file__).resolve().parents[1]
    current=json.loads((root/'verification/catalog.json').read_text(encoding='utf-8'))
    records=[('catalog-v4-original351.json','20261108T083402678603Z-full-backend-matched-controls-coverage.json'),
             ('catalog-v5-prior378.json','20261108T100203771424Z-utf8-restored-full-701-backend-coverage.json'),
             ('catalog-v6-prior397.json','20261108T141545788080Z-presenter-fixed-current-full-regression-and-coverage.json'),
             ('catalog-v7-prior411.json','20261108T153959895989Z-news-strict-recovery-and-release-artifact-current-full-regression.json')]
    for filename,receipt in records:
        raw=(root/'verification/fixtures'/filename).read_bytes();prior=json.loads(raw)
        expected=json.loads((root/'verification/receipts'/receipt).read_text(encoding='utf-8'))['subject']['catalog_sha256']
        assert hashlib.sha256(raw).hexdigest()==expected
        reqs={r['id'] for r in prior['requirements']};cases={c['id'] for c in prior['cases']}
        requirements=[r|dict(case_ids=[c for c in r['case_ids'] if c in cases]) for r in current['requirements'] if r['id'] in reqs]
        projected=current|dict(version=prior['version'],requirements=requirements,cases=[c for c in current['cases'] if c['id'] in cases])
        assert hashlib.sha256(json.dumps(projected,indent=2).replace('\n','\r\n').encode()).hexdigest()==expected


def test_main_ui_and_rulebook_keep_the_expected_unicode_labels():
    root=Path(__file__).resolve().parents[1]
    app=(root/'frontend/src/App.tsx').read_text(encoding='utf-8')
    assert 'Shared-capital portfolio \u00b7 ' in app
    assert '\u00c2\u00b7' not in app
    assert (root/'RULEBOOK.md').read_text(encoding='utf-8').startswith('# Numerical rulebook \u2014 version 0.25')
