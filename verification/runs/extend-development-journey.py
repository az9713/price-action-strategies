"""Freeze a continuation ledger; read structured usage and public messages only.

No credential/configuration reads, database copies, or hidden-reasoning extraction.
The earlier journey/accounting are preserved byte for byte.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
ROLLOUT = Path('<user-home>/.codex/sessions/2026/11/07/rollout-2026-11-07T16-32-52-<chat-id>.jsonl')
START = '2026-11-09T18:36:32.512Z'
END = '2026-11-10T02:45:57Z'
DEST = ROOT / 'docs/development-journey-2'
PRIVATE = ROOT / 'data/private-evidence/development-journey-2'

def stamp(s):
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def duration(s):
    n = round(s)
    d, n = divmod(n, 86400)
    h, n = divmod(n, 3600)
    m, n = divmod(n, 60)
    return f'{d}d {h:02d}h {m:02d}m {n:02d}s'

def clean(s):
    for p, label in [(ROOT, '<workspace>'), (Path.home(), '<user-home>')]:
        s = s.replace(str(p), label).replace(p.as_posix(), label)
    s = re.sub(r'(?i)((?:ALPACA_(?:API|SECRET)_KEY|APCA_API_(?:KEY_ID|SECRET_KEY))\s*[=:]\s*)[^\s,;"\']+', r'\1<redacted>', s)
    return re.sub(r'\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]{16,}\b', '<redacted-token>', s)

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    rows, messages, events = [], [], []
    meta = None
    with ROLLOUT.open(encoding='utf-8') as handle:
        for line in handle:
            r = json.loads(line)
            at = r.get('timestamp')
            if not at or stamp(at) >= stamp(END):
                continue
            p, kind = r.get('payload', {}), r.get('type')
            if kind == 'session_meta' and meta is None:
                meta = {k: p.get(k) for k in ['id', 'timestamp']}
            elif kind == 'token_usage_record':
                rows.append(dict(timestamp=at, **{k: p.get(k) for k in ['response_id', 'turn_id', 'usage', 'thread_token_usage']}))
            elif kind == 'event_msg' and p.get('type') in ['task_started', 'task_complete', 'turn_aborted']:
                events.append(dict(timestamp=at, **{k: p.get(k) for k in ['type', 'turn_id']}))
            elif kind == 'response_item' and stamp(at) >= stamp(START) and p.get('type') == 'message':
                role, phase = p.get('role'), p.get('phase', p.get('channel'))
                if role == 'user' or (role == 'assistant' and phase in ['commentary', 'final', 'final_answer']):
                    text = '\n'.join(c.get('text', '') for c in p.get('content', []) if isinstance(c, dict))
                    if text and not text.startswith('<codex_internal_context'):
                        messages.append(dict(timestamp=at, role=role, phase=phase, text=clean(text)))
    totals, seen = Counter(), set()
    for r in rows:
        assert r['response_id'] not in seen
        seen.add(r['response_id'])
        u = r['usage']
        assert u['input_tokens'] + u['output_tokens'] == u['total_tokens']
        assert 0 <= u['cached_input_tokens'] <= u['input_tokens']
        assert 0 <= u['reasoning_output_tokens'] <= u['output_tokens']
        totals.update(u)
    assert dict(totals) == rows[-1]['thread_token_usage']
    old = json.loads((ROOT / 'docs/development-journey/ACCOUNTING.json').read_text())
    earlier = Counter()
    for r in rows:
        if stamp(r['timestamp']) < stamp(START):
            earlier.update(r['usage'])
    for k, n in earlier.items():
        assert n == old['tokens'][k]
    starts, intervals = {}, []
    for e in events:
        if e['type'] == 'task_started':
            assert e['turn_id'] not in starts
            starts[e['turn_id']] = stamp(e['timestamp'])
        elif e['turn_id'] in starts:
            intervals.append((starts.pop(e['turn_id']), stamp(e['timestamp'])))
    open_intervals = [(turn, start, stamp(END)) for turn, start in starts.items()]
    segments = []
    for a, b in sorted(intervals + [(a, b) for _, a, b in open_intervals]):
        assert a <= b
        if segments and a <= segments[-1][1]:
            segments[-1] = (segments[-1][0], max(b, segments[-1][1]))
        else:
            segments.append((a, b))
    wall = (stamp(END) - stamp(meta['timestamp'])).total_seconds()
    union = sum((b - a).total_seconds() for a, b in segments)
    closed_segments = []
    for a, b in sorted(intervals):
        if closed_segments and a <= closed_segments[-1][1]:
            closed_segments[-1] = (closed_segments[-1][0], max(b, closed_segments[-1][1]))
        else:
            closed_segments.append((a, b))
    closed_union = sum((b-a).total_seconds() for a,b in closed_segments)
    ledger = PRIVATE / 'response-usage.json'
    ledger.write_text(json.dumps(rows, indent=2), encoding='utf-8')
    (PRIVATE / 'task-events.json').write_text(json.dumps(events, indent=2), encoding='utf-8')
    (PRIVATE / 'public-messages.json').write_text(json.dumps(messages, indent=2), encoding='utf-8')
    account = dict(scope='Entire owning chat including documentation and later implementation; frozen before writing this continuation. Not build-only billing.',
        cutoff_utc=END, previous_cutoff_utc=START, thread_created_at_utc=meta['timestamp'], last_usage_at_utc=rows[-1]['timestamp'],
        response_records=len(rows), duplicate_response_ids=0, sum_matches_cumulative=True,
        calendar_seconds=wall, calendar_elapsed=duration(wall), turn_union_seconds=union, turn_union=duration(union),
        closed_turn_union_seconds=closed_union, closed_turn_union=duration(closed_union),
        completed_or_aborted_intervals=len(intervals), open_intervals_clipped_to_cutoff=[dict(turn_id=t, start=a.isoformat(), end=b.isoformat()) for t,a,b in open_intervals],
        tokens=dict(totals), uncached_input_tokens=totals['input_tokens']-totals['cached_input_tokens'],
        uncached_input_plus_output_tokens=totals['input_tokens']-totals['cached_input_tokens']+totals['output_tokens'],
        change_since_original={k: totals[k]-earlier[k] for k in totals},
        dollar_cost=None, dollar_cost_reason='No attributable project invoice, Codex credit debit ledger or applicable rate allocation. Token usage alone is insufficient.',
        private_ledger_sha256=sha(ledger),
        limitations=['Cached input is contained in input. Reasoning output is contained in output. Do not add either twice.',
          'Wall/turn clocks include tool waits and can include machine standby. No CPU or person-hour claim.',
          'Two task-start records lack terminal events before this cutoff. The all-turn envelope clips them to cutoff; it can overstate activity. Closed-only union is reported separately.',
          'Later documentation and implementation cannot be reliably separated by this thread ledger; this newer total explicitly includes both.'])
    (DEST / 'ACCOUNTING.json').write_text(json.dumps(account, indent=2), encoding='utf-8')
    manifest = dict(cutoff_utc=END, previous_documents=[], receipts=[], quoted_logs=[])
    for path in [ROOT / 'DEVELOPMENT-JOURNEY.md', *sorted((ROOT / 'docs/development-journey').glob('*'))]:
        if path.is_file():
            manifest['previous_documents'].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size))
    receipt_lines = ['# Continuation execution receipts', '', f'Checks started from {START} and finished before {END}. Historical, overlapping checks; not a unique test count.', '', '| Started | Receipt | Exit | Notes |', '|---|---|---:|---|']
    failure_lines = ['# Continuation failed checks', '', 'Nonzero command exits include authored counterexamples, environment failures and harness faults. They are not all product defects. Excerpts are bounded and sanitized; original logs remain linked.', '']
    for path in sorted((ROOT / 'verification/receipts').glob('*.json')):
        r = json.loads(path.read_text(encoding='utf-8'))
        start, end = r.get('started_at_utc'), r.get('finished_at_utc')
        if not start or not end or not (stamp(START) <= stamp(start) and stamp(end) < stamp(END)):
            continue
        rel = path.relative_to(ROOT).as_posix()
        code = r.get('command', {}).get('exit_code')
        manifest['receipts'].append(dict(path=rel, sha256=sha(path), exit_code=code, receipt_id=r['receipt_id']))
        notes = clean('; '.join(r.get('notes', []))).replace('|', '\\|').replace('\n', ' ')
        receipt_lines.append(f'| {start} | [{r["receipt_id"]}](../../{rel}) | {code} | {notes} |')
        if code == 0:
            continue
        failure_lines += [f'## {r["receipt_id"]}', '', f'[Original receipt](../../{rel}); command exit `{code}`.', '']
        for artifact in r.get('artifacts', []):
            log = ROOT / artifact['path']
            if log.name not in ['stdout.log', 'stderr.log'] or not log.is_file():
                continue
            manifest['quoted_logs'].append(dict(path=log.relative_to(ROOT).as_posix(), sha256=sha(log), bytes=log.stat().st_size))
            text = clean(log.read_text(encoding='utf-8', errors='replace'))
            lines = text.splitlines()
            # Tail contains the test summary/traceback; never extract raw tool inputs.
            excerpt = '\n'.join(lines[-24:])[:6500]
            failure_lines += [f'[Original {log.name}](../../{log.relative_to(ROOT).as_posix()})', '', '~~~~text', excerpt, '~~~~', '']
    (DEST / 'RECEIPT-LEDGER.md').write_text('\n'.join(receipt_lines)+'\n', encoding='utf-8')
    (DEST / 'FAILURE-LEDGER.md').write_text('\n'.join(failure_lines)+'\n', encoding='utf-8')
    timeline = ['# Continuation public-message timeline', '', 'Chronological public user messages and assistant updates only. No hidden reasoning or raw tool transcript. Identifiers are exact; local home paths/credential-shaped strings are redacted.', '']
    for m in messages:
        timeline += [f'## {m["timestamp"]} — {m["role"]} / {m["phase"]}', '', m['text'].replace('](<workspace>/', '](../../'), '']
    (DEST / 'MILESTONE-TIMELINE.md').write_text('\n'.join(timeline)+'\n', encoding='utf-8')
    manifest.update(receipt_count=len(manifest['receipts']), nonzero_receipts=sum(x['exit_code'] != 0 for x in manifest['receipts']), public_messages=len(messages),
        scope='Historical receipt JSON hashes and quoted log hashes; not every historical artifact revalidated. Original journey documents preserved.')
    (DEST / 'EVIDENCE-MANIFEST.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(accounting=account, receipt_count=manifest['receipt_count'], nonzero_receipts=manifest['nonzero_receipts'], public_messages=len(messages)), indent=2))

if __name__ == '__main__':
    main()
