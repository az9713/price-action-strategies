"""Verify retrospective arithmetic, original records, evidence hashes and links.

Documentation audit only; no financial rerun and no application acceptance claim.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'docs/development-journey-2'
PRIVATE = ROOT / 'data/private-evidence/development-journey-2'
OUT = Path(os.environ['PA_EVIDENCE_RUN_DIR'])

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def stamp(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def main():
    a = read(DEST / 'ACCOUNTING.json')
    m = read(DEST / 'EVIDENCE-MANIFEST.json')
    rows = read(PRIVATE / 'response-usage.json')
    assert sha(PRIVATE / 'response-usage.json') == a['private_ledger_sha256']
    seen, total, old = set(), Counter(), Counter()
    for row in rows:
        assert row['response_id'] not in seen and stamp(row['timestamp']) < stamp(a['cutoff_utc'])
        seen.add(row['response_id'])
        u = row['usage']
        assert u['input_tokens'] + u['output_tokens'] == u['total_tokens']
        assert 0 <= u['cached_input_tokens'] <= u['input_tokens']
        assert 0 <= u['reasoning_output_tokens'] <= u['output_tokens']
        total.update(u)
        if stamp(row['timestamp']) < stamp(a['previous_cutoff_utc']):
            old.update(u)
    assert len(seen) == a['response_records'] == 3326
    assert dict(total) == a['tokens'] == rows[-1]['thread_token_usage']
    assert total['total_tokens'] == 774216918
    assert total['input_tokens']-total['cached_input_tokens'] == a['uncached_input_tokens'] == 5876065
    assert a['uncached_input_plus_output_tokens'] == 10617430
    previous = read(ROOT / 'docs/development-journey/ACCOUNTING.json')
    for k, v in old.items():
        assert v == previous['tokens'][k]
        assert total[k]-v == a['change_since_original'][k]
    assert a['dollar_cost'] is None
    assert (stamp(a['cutoff_utc'])-stamp(a['thread_created_at_utc'])).total_seconds() == a['calendar_seconds'] == 180784.466
    starts, closed = {}, []
    for e in read(PRIVATE / 'task-events.json'):
        if e['type'] == 'task_started':
            assert e['turn_id'] not in starts
            starts[e['turn_id']] = stamp(e['timestamp'])
        elif e['turn_id'] in starts:
            closed.append((starts.pop(e['turn_id']), stamp(e['timestamp'])))
    def union(intervals):
        result = []
        for start, end in sorted(intervals):
            assert start <= end
            if result and start <= result[-1][1]:
                result[-1] = (result[-1][0], max(end, result[-1][1]))
            else:
                result.append((start, end))
        return sum((end-start).total_seconds() for start,end in result)
    assert len(closed) == 42 and len(starts) == 2
    assert union(closed) == a['closed_turn_union_seconds'] == 170161.36
    assert union(closed+[(s,stamp(a['cutoff_utc'])) for s in starts.values()]) == a['turn_union_seconds'] == 177111.99
    assert len(m['receipts']) == m['receipt_count'] == 145
    assert sum(r['exit_code'] != 0 for r in m['receipts']) == m['nonzero_receipts'] == 60
    for group in ['previous_documents', 'receipts', 'quoted_logs']:
        for entry in m[group]:
            path = ROOT / entry['path']
            assert path.is_file() and sha(path) == entry['sha256'], entry['path']
            if 'bytes' in entry:
                assert path.stat().st_size == entry['bytes']
    # Read the original workload measurements, not copied prose or a new run.
    run = ROOT / 'verification/runs/20261110T010321700433Z-protocol-two-original-book-manifests-computation-events-actual-10000-worker-and-retained-peak-memory'
    worker = read(run / 'worker-runtime-measurement.json')
    audit = read(run / 'owned-10000-financial-audit.json')
    assert worker['absolute_process_peak_working_set_bytes'] == 235708416
    assert audit['absolute_process_peak_working_set_bytes'] == 275861504
    assert worker['worker_seconds'] == audit['worker_seconds'] == 2895.5855771000206
    for k, v in dict(verified_occurrences=20000, verified_original_trial_checkpoints=20001, original_committed_parts=100, independently_replayed_complete_books=28, output_files=104, output_bytes=1409314).items():
        assert audit[k] == v, k
    identifier = '20261110T023415845767Z-trade-twins-current-complete-saved-evidence-positive-20000-pages-zip-csv-offline-and-all-origin-faults'
    r = read(ROOT / 'verification/receipts' / (identifier+'.json'))
    assert r['command']['exit_code'] == 0 and not any(n.startswith('Source changed') for n in r['notes'])
    artifact = next(x for x in r['artifacts'] if x['path'].endswith('/evidence-stage-junit.xml'))
    path = ROOT / artifact['path']
    assert sha(path) == artifact['sha256']
    suites = list(ET.parse(path).iter('testsuite'))
    counts = {k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    assert counts == dict(tests=127,errors=0,failures=0,skipped=0)
    docs = [ROOT/'DEVELOPMENT-JOURNEY-2.md', ROOT/'README.md', *DEST.glob('*.md')]
    links, historical_missing = [], []
    for path in docs:
        content = path.read_text(encoding='utf-8')
        assert not re.search(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}\b', content)
        assert not re.search(r'ALPACA_(?:API|SECRET)_KEY\s*=\s*(?!<redacted>)[^\s,;"\']+', content)
        fence, visible = None, []
        for line in content.splitlines():
            marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
            if marker:
                if fence is None:
                    fence = marker.group(1)
                elif marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                    fence = None
                continue
            if fence is None:
                visible.append(line)
        assert fence is None, path
        for target in re.findall(r'\[[^\]\n]+\]\(([^\n)]+)\)', '\n'.join(visible)):
            target = target.strip().strip('<>')
            if target.startswith(('https://','http://','#','mailto:')):
                continue
            p = (path.parent/target.split('#',1)[0]).resolve()
            if path.name == 'MILESTONE-TIMELINE.md' and not p.exists():
                historical_missing.append(dict(document=path.name,target=target))
                continue
            assert p.is_relative_to(ROOT) and p.exists(), (path.name,target)
            assert not any(part.lower().startswith('.env') for part in p.relative_to(ROOT).parts)
            links.append(dict(document=path.relative_to(ROOT).as_posix(), target=p.relative_to(ROOT).as_posix()))
    text = (ROOT/'DEVELOPMENT-JOURNEY-2.md').read_text(encoding='utf-8')
    for item in ['774,216,918','10,617,430','50h 13m 04s','235,708,416','275,861,504','127 passed','still active and incomplete','same named strategy families']:
        if item == 'same named strategy families':
            assert item in text.lower()
        elif item == 'still active and incomplete':
            assert item in text.replace('**','')
        else:
            assert item in text
    result = dict(scope=__doc__, response_records_verified=len(seen), response_sum_equals_cumulative=True,
        original_accounting_prefix_verified=True, original_documents_preserved=len(m['previous_documents']),
        continuation_receipt_hashes_verified=len(m['receipts']), quoted_log_hashes_verified=len(m['quoted_logs']),
        actual_workload_peak_boundaries_verified=True, latest_original_junit=counts, local_links_checked=len(links),
        historical_message_links_missing=historical_missing, billing_charge_available=False,
        application_acceptance_certified=False, documents=[dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in docs])
    (OUT/'development-journey-continuation-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'documents'},indent=2))

if __name__ == '__main__':
    main()
