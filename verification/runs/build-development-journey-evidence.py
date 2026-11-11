"""Build bounded, credential-free journey appendices from the frozen audit extraction."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib,json,re
root=Path.cwd();private=root/'data/private-evidence/development-journey';dest=root/'docs/development-journey';dest.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def duration(seconds):
 n=round(seconds);days,rest=divmod(n,86400);hours,rest=divmod(rest,3600);minutes,seconds=divmod(rest,60)
 return f'{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s'
def clean(s):
 s=s.replace(str(root),'<workspace>').replace(root.as_posix(),'<workspace>').replace(str(Path.home()),'<user-home>').replace(Path.home().as_posix(),'<user-home>')
 s=re.sub(r'(?i)((?:ALPACA_(?:API|SECRET)_KEY|APCA_API_(?:KEY_ID|SECRET_KEY)|X-Lab-Session|Authorization)\s*[=:]\s*)[^\s,;"\']+',r'\1<redacted>',s)
 return s
def cell(s):return str(s).replace('|','\\|').replace('\n',' ')
audit=read(private/'accounting-and-inventory.json');receipts=read(private/'receipt-inventory.json');messages=read(private/'public-message-timeline.json');ledger=read(private/'primary-response-usage-build-cutoff.json')
cutoff=audit['build_cutoff_utc'];receipts=[r for r in receipts if r['started'] and r['started']<cutoff]
usage=Counter();ids=set()
for r in ledger:
 assert r['timestamp']<cutoff and r['response_id'] not in ids;ids.add(r['response_id']);usage.update(r['usage'])
assert dict(usage)==audit['primary_summed_usage'] and len(ids)==2818
goal_original=read(private/'goal-observation.json');assert goal_original['goal']['tokensUsed']==7993870 and goal_original['goal']['timeUsedSeconds']==142874 and goal_original['goal']['createdAt']==1794106525
goal=dict(observed_at_utc=goal_original['timestamp'],created_at_utc='2026-11-08T02:55:25Z',elapsed_seconds=142874,tokens_used=7993870,observation_artifact_sha256=sha(private/'goal-observation.json'),
 provenance='Observed get_goal response at the beginning of documentation; narrower scope than the full primary response ledger. It is not added to that ledger.')
accounting=dict(scope='Entire owning project chat up to the documentation request; later documentation tokens are excluded.',build_cutoff_utc=cutoff,
 thread_created_at_utc=audit['metadata']['timestamp'],last_usage_at_utc=audit['build_last_usage_timestamp'],
 clock=dict(calendar_elapsed_seconds=audit['calendar_elapsed_seconds'],calendar_elapsed=duration(audit['calendar_elapsed_seconds']),
 recorded_turn_union_seconds=audit['recorded_turn_union_seconds'],recorded_turn_union=duration(audit['recorded_turn_union_seconds']),
 recorded_completed_or_aborted_turns=audit['completed_or_aborted_turn_intervals'],goal_snapshot=goal,
 limitation='Wall/turn/goal clocks include tool waits and can include host standby. They are not CPU time, uninterrupted attention or human person-hours.'),
 tokens=dict(**dict(usage),uncached_input_tokens=usage['input_tokens']-usage['cached_input_tokens'],
 uncached_input_plus_output_tokens=usage['input_tokens']-usage['cached_input_tokens']+usage['output_tokens']),
 response_records=len(ledger),duplicate_response_ids=0,sum_matches_cumulative_thread_ledger=True,
 model_identifiers=audit['model_turn_context_counts'],compacted_records=audit['record_types']['compacted'],
 dollar_cost=None,dollar_cost_status='Not available: no project invoice, credit debits or applicable Codex rate allocation in the evidence. No API price substituted.',
 primary_response_ledger_sha256=sha(private/'primary-response-usage-build-cutoff.json'),
 accounting_notes=audit['accounting_notes'])
(dest/'ACCOUNTING.json').write_text(json.dumps(accounting,indent=2),encoding='utf-8')
turns=defaultdict(Counter);times=defaultdict(list)
for r in ledger:turns[r['turn_id']].update(r['usage']);times[r['turn_id']].append(r['timestamp'])
lines=['# Work-clock and token audit','',f'Frozen build cutoff: `{cutoff}`. This excludes writing this journey.','',
 'The primary source is the owning Codex response-usage ledger, not a guessed tokenization of source files. Every response identity is counted once; its summed fields exactly match the last cumulative thread ledger before the cutoff. No raw prompt, hidden analysis, credential or account invoice is reproduced here.','',
 '| Clock | Measured value | Meaning |','|---|---|---|',
 f'| Full project span | {duration(audit["calendar_elapsed_seconds"])} | Thread creation to documentation request |',
 f'| Union of 35 recorded work-turn intervals | {duration(audit["recorded_turn_union_seconds"])} | Includes tools, waits and possible host standby |',
 f'| Active-goal counter at18:36:39UTC | {duration(goal["elapsed_seconds"])} | Goal began after investigation/planning |','',
 'The user’s lower-bound estimate was1 day15 hours17 minutes. All three measured spans exceed it. These are different clocks; they must not be added. Receipt durations must not be added either, because checks overlap and sometimes run in parallel.','',
 '| Token category | Tokens | Accounting |','|---|---:|---|',
 f'| All input | {usage["input_tokens"]:,} | Includes cached input |',
 f'| Cached input | {usage["cached_input_tokens"]:,} | Subset of input, not additional |',
 f'| Uncached input | {usage["input_tokens"]-usage["cached_input_tokens"]:,} | Input minus cached input |',
 f'| All output | {usage["output_tokens"]:,} | Includes reasoning output |',
 f'| Reasoning output | {usage["reasoning_output_tokens"]:,} | Subset of output, not additional |',
 f'| Input plus output | {usage["total_tokens"]:,} | Total including cached context |',
 f'| Uncached input plus output | {accounting["tokens"]["uncached_input_plus_output_tokens"]:,} | Useful separate measure; not a dollar charge |','',
 '**Dollar charge: not available.** A subscription/credits allocation or applicable per-response billing rates would be needed. Cached input is not assumed free. The model identifier recorded in the turn contexts is `gpt-6.1-sol`; no other model’s public price is used as its invoice.','',
 'For actual uniform API-style rates in dollars per million, the arithmetic would be4.610687×uncached-input-rate +635.467136×cached-input-rate +3.835647×output-rate. This is a formula, not an estimate of a Codex bill. Different context tiers or account terms require per-response rates instead.','',
 'The earlier goal observation was7,993,870 tokens. Its start/scope differs from the complete primary ledger. It is retained as a historical observation and is neither substituted for nor added to the full-project total.','',
 '## Per-turn response usage','',
 'These rows aggregate response records by turn identity. A response-usage turn can also contain internal accounting such as a compaction; this table is not the35 work-clock intervals.','',
 '| First response UTC | Last response UTC | Response-turn ID | Input | Cached input | Output | Total |','|---|---|---|---:|---:|---:|---:|']
for turn,u in sorted(turns.items(),key=lambda x:min(times[x[0]])):
 lines.append(f'| {min(times[turn])} | {max(times[turn])} | `{turn}` | {u["input_tokens"]:,} | {u["cached_input_tokens"]:,} | {u["output_tokens"]:,} | {u["total_tokens"]:,} |')
(dest/'WORK-CLOCK-AND-TOKENS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
exit_counts=Counter(str(r['exit_code']) for r in receipts)
lines=['# Complete implementation-receipt ledger','',f'{len(receipts)} structured receipts existed before `{cutoff}`. This is a chronological index, not a claim that every historical artifact was independently revalidated for this document. Each receipt retains its exact subject, command, logs, artifacts and notes.','',
 'Command exit counts: '+', '.join(f'`{k}`: {v}' for k,v in sorted(exit_counts.items()))+'. A zero command exit can still have incoherence notes. A nonzero exit can be an intentionally authored red test, verifier fault, environment failure or actual product defect. Neither count is an acceptance-test total.','',
 '| Started UTC | Receipt | Command exit | Artifacts | Notes |','|---|---|---:|---:|---|']
for r in receipts:
 lines.append(f'| {r["started"]} | [{r["id"]}](../../{r["path"]}) | {r["exit_code"]} | {r["artifacts"]} | {cell("; ".join(r["notes"]))} |')
(dest/'RECEIPT-LEDGER.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
failures=[];diagnostic_hashes=[]
for r in receipts:
 if r['exit_code']==0:continue
 original=read(root/r['path']);logs=[a for a in original['artifacts'] if a['path'].endswith(('stdout.log','stderr.log'))]
 samples=[];links=[]
 for a in logs:
  p=root/a['path'];links.append(f'[{p.name}](../../{a["path"]})')
  if not p.is_file():continue
  raw=p.read_bytes();assert len(raw)==a['bytes'] and hashlib.sha256(raw).hexdigest()==a['sha256'],a['path']
  diagnostic_hashes.append(dict(path=a['path'],bytes=len(raw),sha256=a['sha256']))
  text=raw.decode('utf-8',errors='replace')
  for line in text.splitlines():
   if re.match(r'^\s*(?:E\s+|FAILED\s|ERROR\s|AssertionError|ValueError|TypeError|RuntimeError|Traceback|Error:|npm ERR)',line):
    value=clean(line)
    if value not in samples:samples.append(value[:400]+(' [line clipped]' if len(value)>400 else ''))
  if not samples:
   for line in text.splitlines():
    if any(word in line for word in ['Error:','error:','Timeout','exceeded','DID NOT RAISE']):
     samples.append(clean(line)[:400]);break
 failures.append((r,links,samples[:3]))
lines=['# Retained nonzero-command attempts','',
 'This appendix indexes every nonzero top-level command receipt before the build cutoff. It does not classify all of them as product bugs. Intentional preimplementation failures, malformed verifier fixtures, environment/standby timeouts and genuine defects coexist here. Successful mutation harnesses usually have top-level exit0; their expected inner test failures remain inside their own receipts.','',
 'Up to three original diagnostic lines are shown per attempt. Long lines are explicitly clipped, and local paths/credential-shaped contexts are redacted. Full preserved review logs are linked; no private raw trace or hidden analysis is copied. Hashes of the quoted stdout/stderr files were checked against their owning receipts during generation.','']
for r,links,samples in failures:
 lines.extend([f'## {r["id"]}','',f'[Receipt](../../{r["path"]}) · command exit `{r["exit_code"]}` · '+ ' · '.join(links),''])
 if samples:lines.extend(['````text',*samples,'````',''])
 else:lines.extend(['No recognized diagnostic signature selected; inspect the preserved logs.',''])
(dest/'FAILURE-LEDGER.md').write_text('\n'.join(lines),encoding='utf-8')
lines=['# Chronological public-message milestones','',
 'UTC throughout. This covers the public progress/final messages and substantive user messages in the owning rollout before the documentation request. Each excerpt is deliberately bounded; the main journey explains the causal story and the receipt ledger supplies execution evidence. This is not a publication of raw hidden reasoning or the source video transcript. System/context/automatic-goal and companion-page boilerplate are excluded.','']
milestones=0
for m in messages:
 if m['timestamp']>=cutoff:continue
 text=m['text'].strip()
 if m['role']=='user' and text.startswith(('<external_','<environment_context>','# AGENTS.md instructions','<codex_internal_context')):continue
 label='User' if m['role']=='user' else ('Checkpoint response' if m['channel']=='final_answer' else 'Progress')
 if text.startswith('<send_user_message_question_reply>'):
  try:
   answers=json.loads(text[text.index('['):text.rindex(']')+1]);text=' '.join('Question: '+a['question']+' Answer: '+a['answer'] for a in answers)
  except (ValueError,KeyError,TypeError):pass
 # Excerpts are quotations of progress, not a second set of potentially stale
 # absolute links. The authoritative files/receipts are linked in the narrative.
 text=re.sub(r'\[([^\]\n]+)\]\([^\n]*?\)',r'\1',clean(text)).replace('\n',' ')
 text=text[:600]+(' … [excerpt]' if len(text)>600 else '')
 lines.extend([f'### {m["timestamp"]} — {label}','',text,'']);milestones+=1
(dest/'MILESTONE-TIMELINE.md').write_text('\n'.join(lines),encoding='utf-8')
sources=['PLAN.md','VERIFICATION_PLAN.md','RULEBOOK.md','decisions.md','STATUS.md','VIDEO_REVIEW.md','SCREENSHOT_FINDINGS.md','requirements.lock','frontend/package.json','verification/catalog.json','verification/fixtures/trade-twins-contract.json']
manifest=dict(build_cutoff_utc=cutoff,accounting=accounting,receipt_count=len(receipts),receipt_exit_counts=dict(exit_counts),nonzero_receipts=len(failures),quoted_log_files_hash_checked=len(diagnostic_hashes),milestone_excerpts=milestones,
 source_files=[dict(path=name,sha256=sha(root/name),bytes=(root/name).stat().st_size) for name in sources],
 receipts=[dict(path=r['path'],sha256=r['sha256']) for r in receipts],quoted_logs=diagnostic_hashes,
 limitations=['Indexing941 receipts is not rerunning941 checks or validating every screenshot/archive.','Primary usage is exact to the frozen request cutoff, not an invoice.','Private raw evidence, .env, prices/databases and hidden reasoning are excluded.'])
(dest/'EVIDENCE-MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(receipts=len(receipts),nonzero=len(failures),quoted_logs_checked=len(diagnostic_hashes),milestones=milestones,token_total=usage['total_tokens'],uncached_plus_output=accounting['tokens']['uncached_input_plus_output_tokens'],calendar_clock=accounting['clock']['calendar_elapsed'],turn_clock=accounting['clock']['recorded_turn_union'],dollar_cost=None),indent=2))
