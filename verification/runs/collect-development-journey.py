"""Read only the owning rollout's usage/public messages and receipt metadata.

Never reads .env, configuration/auth files, raw tool outputs or assistant analysis.
Private extraction is evidence for a narrative, not a raw transcript publication.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,re
root=Path.cwd()
rollout=Path('<user-home>/.codex/sessions/2026/11/07/rollout-2026-11-07T16-32-52-<chat-id>.jsonl')
cutoff=datetime.now(timezone.utc).isoformat()
BUILD_CUTOFF='2026-11-09T18:36:32.512Z'
private=root/'data/private-evidence/development-journey';private.mkdir(parents=True,exist_ok=True)
types=Counter();events=Counter();tools=Counter();models=Counter();channels=Counter()
usage=[];public=[];meta={};first=last=None;turns=0;bad=0;ledger=[];task_events=[];nested_tools=Counter();build_cutoff=BUILD_CUTOFF
def scrub(value):
    value=value.replace(str(root),'<workspace>').replace(root.as_posix(),'<workspace>').replace(str(Path.home()),'<user-home>').replace(Path.home().as_posix(),'<user-home>')
    value=re.sub(r'(?i)((?:ALPACA_(?:API|SECRET)_KEY|APCA_API_(?:KEY_ID|SECRET_KEY)|api[_ -]?key|secret[_ -]?key)\s*[=:]\s*)[^\s,;"\']+',r'\1<redacted>',value)
    return re.sub(r'\b(?:sk|ghp|github_pat)-[A-Za-z0-9_-]{16,}\b','<redacted-token>',value)
with rollout.open(encoding='utf-8') as handle:
    for line in handle:
        try:r=json.loads(line)
        except json.JSONDecodeError:bad+=1;continue
        at=r.get('timestamp')
        if at and at>=BUILD_CUTOFF:continue
        first=first or at;last=at or last;kind=r.get('type','?');types[kind]+=1;p=r.get('payload',{})
        if kind=='session_meta' and not meta:
            meta={k:p.get(k) for k in ['id','timestamp','originator','source','model_provider']}
        if kind=='turn_context':
            turns+=1;models[str(p.get('model'))]+=1
        if kind=='token_usage_record':
            ledger.append(dict(timestamp=at,**{k:p.get(k) for k in ['thread_id','turn_id','response_id','usage','thread_token_usage']}))
        if kind=='event_msg':
            events[p.get('type','?')]+=1
            if p.get('type') in ['task_started','task_complete','turn_aborted']:
                task_events.append(dict(timestamp=at,**{k:p.get(k) for k in ['type','turn_id','started_at','completed_at','duration_ms']}))
            if p.get('type')=='token_count' and p.get('info'):
                info=p['info'];usage.append(dict(timestamp=at,total=info.get('total_token_usage'),last=info.get('last_token_usage'),context_window=info.get('model_context_window')))
        if kind=='response_item':
            item=p.get('type')
            if item in ['function_call','custom_tool_call']:
                tools[p.get('name','?')]+=1
                arguments=p.get('arguments',p.get('input',''))
                if p.get('name')=='exec' and isinstance(arguments,str):nested_tools.update(re.findall(r'\btools\.([A-Za-z0-9_]+)\s*\(',arguments))
            if item=='message':
                role=p.get('role');channel=p.get('phase',p.get('channel'));channels[str((role,channel))]+=1
                if role=='user' or (role=='assistant' and channel in ['commentary','final','final_answer']):
                    content='\n'.join(v.get('text','') for v in p.get('content',[]) if isinstance(v,dict))
                    if content:
                        public.append(dict(timestamp=at,role=role,channel=channel,text=scrub(content)))
                        if role=='user' and content.startswith('Write a complete development journey, capturing the entire development process.'):
                            build_cutoff=at
resets=[];prior=None;unique=[]
for i,row in enumerate(usage):
    if not row['total']:continue
    total=row['total'].get('total_tokens',0)
    if prior is not None and total<prior:resets.append(dict(index=i,before=prior,after=total,timestamp=row['timestamp']))
    prior=total
    if not unique or row['total']!=unique[-1]['total']:unique.append(row)
receipts=[]
for p in sorted((root/'verification/receipts').glob('*.json')):
    try:r=json.loads(p.read_text(encoding='utf-8'))
    except (json.JSONDecodeError,UnicodeError):continue
    command=r.get('command',{});receipts.append(dict(id=r.get('receipt_id',p.stem),kind=r.get('kind'),started=r.get('started_at_utc'),finished=r.get('finished_at_utc'),exit_code=command.get('exit_code'),notes=r.get('notes',[]),artifacts=len(r.get('artifacts',[])),path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
value=dict(captured_at_utc=cutoff,rollout_basename=rollout.name,rollout_bytes=rollout.stat().st_size,metadata=meta,first_record=first,last_record=last,
 record_types=dict(types),event_types=dict(events),tool_counts=dict(tools),model_turn_context_counts=dict(models),turn_contexts=turns,message_channels=dict(channels),
 malformed_lines=bad,usage_events=len(usage),unique_cumulative_usage_events=len(unique),usage_counter_resets=resets,first_usage=usage[0] if usage else None,last_usage=usage[-1] if usage else None,
 receipts=len(receipts),receipt_exit_counts=dict(Counter(str(r['exit_code']) for r in receipts)),scope='One owning rollout, public user/assistant commentary/final messages and structured usage; no analysis/tool-output extraction. Receipt metadata, not verification of every historical artifact.')
assert build_cutoff
selected=[r for r in ledger if r['timestamp']<build_cutoff];ids=set();total=Counter();duplicates=0
for row in selected:
    if row['response_id'] in ids:duplicates+=1;continue
    ids.add(row['response_id']);u=row['usage']
    assert u['total_tokens']==u['input_tokens']+u['output_tokens'] and 0<=u['cached_input_tokens']<=u['input_tokens'] and 0<=u['reasoning_output_tokens']<=u['output_tokens']
    total.update(u)
assert dict(total)==selected[-1]['thread_token_usage']
parse=lambda t:datetime.fromisoformat(t.replace('Z','+00:00'))
elapsed=(parse(build_cutoff)-parse(meta['timestamp'])).total_seconds()
starts={};intervals=[]
for event in task_events:
    if event['timestamp']>=build_cutoff:continue
    if event['type']=='task_started':starts[event['turn_id']]=parse(event['timestamp'])
    elif event['turn_id'] in starts:intervals.append((starts.pop(event['turn_id']),parse(event['timestamp'])))
# The documentation turn starts just before its user-message record. Do not count it.
open_before=[(turn,at.isoformat()) for turn,at in starts.items() if (parse(build_cutoff)-at).total_seconds()>1]
ordered=sorted(intervals);union=[]
for start,end in ordered:
    if union and start<=union[-1][1]:union[-1]=(union[-1][0],max(end,union[-1][1]))
    else:union.append((start,end))
value.update(build_cutoff_utc=build_cutoff,build_last_usage_timestamp=selected[-1]['timestamp'],primary_usage_records=len(selected),primary_duplicate_response_ids=duplicates,
 primary_summed_usage=dict(total),primary_sum_matches_cumulative=True,uncached_input_tokens=total['input_tokens']-total['cached_input_tokens'],
 uncached_input_plus_output_tokens=total['input_tokens']-total['cached_input_tokens']+total['output_tokens'],
 calendar_elapsed_seconds=elapsed,completed_or_aborted_turn_intervals=len(intervals),recorded_turn_union_seconds=sum((b-a).total_seconds() for a,b in union),unmatched_pre_documentation_turn_starts=open_before,
 nested_tool_call_expression_counts=dict(nested_tools),dollar_charge_available=False,
 accounting_notes=['Primary per-response ledger is summed once per response_id and exactly matches its last cumulative thread ledger before the documentation request.',
 'Cached input is already included in input tokens; reasoning output is already included in output tokens. Neither is added again.',
 'Elapsed goal/task/receipt wall time includes waits and can include host standby. No CPU/person-hours/invoice equivalence is asserted.',
 'The shared account usage-limits tool does not establish a project-specific bill. No API price was substituted for Codex billing.'])
(private/'accounting-and-inventory.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
(private/'usage-events.json').write_text(json.dumps(usage,indent=2),encoding='utf-8')
(private/'public-message-timeline.json').write_text(json.dumps(public,indent=2),encoding='utf-8')
(private/'receipt-inventory.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
(private/'primary-response-usage-build-cutoff.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
(private/'task-clock-events.json').write_text(json.dumps(task_events,indent=2),encoding='utf-8')
print(json.dumps(value,indent=2))
