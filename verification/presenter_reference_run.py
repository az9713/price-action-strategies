"""Derive actual historical review decks from integrity-checked saved outputs only.

The source accounts may be older builds; their saved output hashes remain explicit.
This does not rerun strategies or certify all detectors or final acceptance.
"""
from pathlib import Path
import os
import sys
import json
import hashlib

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from backend.lab.config import canonical
from backend.lab.service import Lab
from backend.lab.presenter import build_deck,render_html
from backend.lab.presentation_audit import audit_deck

JOBS={
    'account':'d7ef4d13eb3d4fb39c35799b49ac045b',
    'portfolio':'563dc788030047e3b71e010c95ccb95a',
    'passive':'527f8aa325e2458f83cf5d1ab93e1e5a',
    'controls':'64e62e70a5214e35b9f96a4a8c156472',
    'behavior':'37ce9886b50245bab64b10a815ce2450',
    'ablations':'f918e610e0854982a5aafd31c46de20d',
}


def main():
    output=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'presenter';output.mkdir()
    lab=Lab(ROOT);sources=[];observations=[]
    for label,jid in JOBS.items():
        report=lab.report(jid);raw=canonical(report).encode();name=jid+'/report.json'
        deck=build_deck([(name,raw)]);document=render_html(deck)
        # A second invocation rereads original bytes; no data-source access needed.
        check=audit_deck({name:raw},deck)
        path=output/(label+'.html');path.write_text(document,encoding='utf-8')
        (output/(label+'-manifest.json')).write_text(json.dumps(deck,indent=2),encoding='utf-8')
        # Retain a narrow oracle-input snapshot: cells only, never raw candles/ledger.
        facts=deck['facts'];observations.append(dict(label=label,job_id=jid,source_sha256=hashlib.sha256(raw).hexdigest(),
            saved_core_hash=report.get('core_hash'),pages=len(deck['pages']),facts=len(facts),audit=check,
            html_sha256=hashlib.sha256(document.encode()).hexdigest()))
        sources.append((name,raw))
    combined=build_deck(sources)
    (output/'combined.html').write_text(render_html(combined),encoding='utf-8')
    (output/'combined-manifest.json').write_text(json.dumps(combined,indent=2),encoding='utf-8')
    result=dict(scope='Actual integrity-checked saved historical outputs; presentation provenance only, no new final test.',
        sources=observations,combined_pages=len(combined['pages']),combined_facts=len(combined['facts']))
    (output/'observations.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
