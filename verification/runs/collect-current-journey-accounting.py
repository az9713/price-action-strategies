"""Reconcile project clocks and usage with the last published journey."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
ROLLOUT = Path.home() / '.codex/sessions/2026/11/07/rollout-2026-11-07T16-32-52-<chat-id>.jsonl'


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def union_seconds(intervals):
    merged = []
    for start, end in sorted(intervals):
        assert start <= end
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum((end - start).total_seconds() for start, end in merged)


def main():
    cutoff = timestamp(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(timezone.utc)
    previous = json.loads((ROOT / 'docs/development-journey-2/ACCOUNTING.json').read_text())
    previous_cutoff = timestamp(previous['cutoff_utc'])
    totals, prefix = Counter(), Counter()
    starts, completed, seen = {}, [], set()
    last_usage = None
    with ROLLOUT.open(encoding='utf-8') as stream:
        for line in stream:
            if not any(f'"{kind}"' in line for kind in ('token_usage_record', 'task_started', 'task_complete', 'turn_aborted')):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                assert not line.endswith('\n'), 'Invalid completed ledger line'
                break
            at = timestamp(record['timestamp'])
            if at >= cutoff:
                continue
            payload = record['payload']
            if record['type'] == 'token_usage_record':
                response_id = payload['response_id']
                assert response_id not in seen
                seen.add(response_id)
                usage = payload['usage']
                assert usage['input_tokens'] + usage['output_tokens'] == usage['total_tokens']
                assert 0 <= usage['cached_input_tokens'] <= usage['input_tokens']
                assert 0 <= usage['reasoning_output_tokens'] <= usage['output_tokens']
                totals.update(usage)
                if at < previous_cutoff:
                    prefix.update(usage)
                last_usage = (at, payload['thread_token_usage'])
            elif record['type'] == 'event_msg':
                event = payload['type']
                turn = payload.get('turn_id')
                if event == 'task_started':
                    assert turn not in starts
                    starts[turn] = at
                elif event in {'task_complete', 'turn_aborted'} and turn in starts:
                    completed.append((starts.pop(turn), at))
    assert dict(prefix) == previous['tokens']
    assert last_usage and dict(totals) == last_usage[1]
    created = timestamp(previous['thread_created_at_utc'])
    value = dict(
        cutoff_utc=cutoff.isoformat(), previous_cutoff_utc=previous_cutoff.isoformat(),
        thread_created_at_utc=created.isoformat(), last_usage_utc=last_usage[0].isoformat(),
        calendar_seconds=(cutoff - created).total_seconds(),
        completed_or_aborted_turn_union_seconds=union_seconds(completed),
        recorded_turn_envelope_seconds=union_seconds(completed + [(start, cutoff) for start in starts.values()]),
        completed_or_aborted_intervals=len(completed), open_intervals_at_cutoff=len(starts),
        tokens=dict(totals), change_since_previous={key: totals[key] - prefix[key] for key in totals},
        uncached_input_tokens=totals['input_tokens'] - totals['cached_input_tokens'],
        uncached_input_plus_output_tokens=totals['total_tokens'] - totals['cached_input_tokens'],
        unique_response_records=len(seen), previous_totals_reconciled=True, cumulative_totals_reconciled=True,
        dollar_cost=None, dollar_cost_reason='No attributable invoice or credit ledger in the usage records.',
    )
    encoded = json.dumps(value, indent=2) + '\n'
    output = Path(os.environ['PA_EVIDENCE_RUN_DIR']) / 'journey-accounting.json'
    output.write_text(encoded, encoding='utf-8')
    print(encoded, end='')


if __name__ == '__main__':
    main()
