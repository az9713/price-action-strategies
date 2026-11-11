"""Live counts from actual pytest reports; no result promotion or test changes."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import json,os,time

_results={}
_started=time.monotonic()
_total=0

def _write(terminal=False,exit_code=None):
    counts=Counter(_results.values())
    value=dict(scope='Actual pytest collection/report progress only; not product acceptance.',
        observed_at_utc=datetime.now(timezone.utc).isoformat(),collected=_total,reported=len(_results),
        passed=counts['passed'],failed=counts['failed'],skipped=counts['skipped'],errors=counts['error'],
        elapsed_seconds=time.monotonic()-_started,terminal=terminal,exit_code=exit_code)
    root=Path(os.environ['PA_EVIDENCE_RUN_DIR']);temporary=root/'full-regression-progress.partial'
    temporary.write_text(json.dumps(value,indent=2),encoding='utf-8')
    temporary.replace(root/'full-regression-progress.json')

def pytest_collection_finish(session):
    global _total
    _total=session.testscollected
    _write()

def pytest_runtest_logreport(report):
    state=None
    if report.when=='call':state='passed' if report.passed else 'failed' if report.failed else 'skipped'
    elif report.failed:state='error'
    elif report.skipped:state='skipped'
    if state is not None:
        _results[report.nodeid]=state
        _write()

def pytest_sessionfinish(session,exitstatus):
    _write(True,int(exitstatus))
