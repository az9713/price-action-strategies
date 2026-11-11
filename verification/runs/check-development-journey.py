"""Verify journey arithmetic, preserved source/receipt/log hashes and local links.

Documentation verification only. No application acceptance or billing claim.
"""
from pathlib import Path
from collections import Counter
from datetime import datetime
import hashlib,json,os,re,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);docs=root/'docs/development-journey';private=root/'data/private-evidence/development-journey'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(t):return datetime.fromisoformat(t.replace('Z','+00:00'))
accounting=read(docs/'ACCOUNTING.json');manifest=read(docs/'EVIDENCE-MANIFEST.json');ledger=read(private/'primary-response-usage-build-cutoff.json');goal=read(private/'goal-observation.json')
assert sha(private/'primary-response-usage-build-cutoff.json')==accounting['primary_response_ledger_sha256']
assert sha(private/'goal-observation.json')==accounting['clock']['goal_snapshot']['observation_artifact_sha256']
totals=Counter();seen=set()
for r in ledger:
 assert r['response_id'] not in seen and stamp(r['timestamp'])<stamp(accounting['build_cutoff_utc']);seen.add(r['response_id']);totals.update(r['usage'])
assert len(seen)==accounting['response_records']==2818 and dict(totals)==ledger[-1]['thread_token_usage']
for key,value in totals.items():assert accounting['tokens'][key]==value
assert totals['total_tokens']==totals['input_tokens']+totals['output_tokens']==643913470
assert totals['input_tokens']-totals['cached_input_tokens']==accounting['tokens']['uncached_input_tokens']==4610687
assert accounting['tokens']['uncached_input_plus_output_tokens']==8446334
assert totals['reasoning_output_tokens']==2216009<=totals['output_tokens']==3835647
assert accounting['dollar_cost'] is None and accounting['sum_matches_cumulative_thread_ledger']
assert goal['goal']['timeUsedSeconds']==142874 and goal['goal']['tokensUsed']==7993870
assert goal['goal']['updatedAt']-goal['goal']['createdAt']==142874
assert abs((stamp(accounting['build_cutoff_utc'])-stamp(accounting['thread_created_at_utc'])).total_seconds()-151419.978)<.0001
starts={};intervals=[]
for event in read(private/'task-clock-events.json'):
 if stamp(event['timestamp'])>=stamp(accounting['build_cutoff_utc']):continue
 if event['type']=='task_started':starts[event['turn_id']]=stamp(event['timestamp'])
 elif event['turn_id'] in starts:
  start=starts.pop(event['turn_id']);end=stamp(event['timestamp']);assert start<=end;intervals.append((start,end))
segments=[]
for start,end in sorted(intervals):
 if segments and start<=segments[-1][1]:segments[-1]=(segments[-1][0],max(end,segments[-1][1]))
 else:segments.append((start,end))
assert len(intervals)==35 and abs(sum((b-a).total_seconds() for a,b in segments)-147749.941)<.0001
assert accounting['clock']['recorded_turn_union_seconds']==147749.941
assert manifest['receipt_count']==941 and manifest['nonzero_receipts']==241 and manifest['milestone_excerpts']==537
for entry in manifest['source_files']:
 p=root/entry['path'];assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],entry['path']
for entry in manifest['receipts']:
 assert sha(root/entry['path'])==entry['sha256'],entry['path']
for entry in manifest['quoted_logs']:
 p=root/entry['path'];assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],entry['path']
assert len(manifest['quoted_logs'])==558
expected=[
 ('20261109T101405014361Z-current-clean-locked-install-frontend-byte-rebuild-and-full-backend-reproduction','clean-junit.xml',1893),
 ('20261109T160028110170Z-spread-version025-current-full-backend-regression-and-twenty-seven-module-coverage','dev025-junit.xml',2239),
 ('20261109T182720056824Z-trade-twins-current-entry-traces-original-wrapper-aware-split-and-independent-execution-parity','dev026-junit.xml',434),
 ('20261109T183516288576Z-trade-twins-complete-component-archive-actual-restoration-and-new-matching-entry-schema-catalog-checks','restored-source-junit.xml',143)]
checked_counts=[]
for identifier,name,total in expected:
 r=read(root/'verification/receipts'/(identifier+'.json'));assert r['command']['exit_code']==0
 assert not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 a=next(a for a in r['artifacts'] if a['path'].endswith('/'+name));p=root/a['path'];assert p.stat().st_size==a['bytes'] and sha(p)==a['sha256']
 suites=list(ET.parse(p).iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
 assert counts==dict(tests=total,failures=0,errors=0,skipped=0),(identifier,counts)
 checked_counts.append(dict(receipt=identifier,counts=counts))
capacity=read(root/'verification/runs/20261109T092058859168Z-numerical-capacity-current-10000-real-one-session-execution/capacity-summary.json')
assert capacity['count']==10000 and capacity['sample_sessions']==1 and capacity['regular_minute_rows']==390
m=capacity['measurements'][0]
assert abs(m['total_seconds']-706.2571080999915)<1e-9 and m['absolute_process_peak_working_set_bytes']==341573632 and m['job_output_bytes']==90361861 and m['job_output_files']==20002
files=[root/'DEVELOPMENT-JOURNEY.md',root/'README.md',*sorted(docs.glob('*.md'))]
links=[];privacy_flags=[]
for path in files:
 text=path.read_text(encoding='utf-8');fence=None;visible=[]
 for number,line in enumerate(text.splitlines(),1):
  marker=re.match(r'^\s*(`{3,}|~{3,})',line)
  if marker:
   if fence is None:fence=marker.group(1)
   elif marker.group(1)[0]==fence[0] and len(marker.group(1))>=len(fence):fence=None
   continue
  if fence is None:visible.append(line)
  if re.search(r'\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',line):privacy_flags.append(dict(path=path.relative_to(root).as_posix(),line=number,rule='credential-shaped token'))
  for value in re.findall(r'ALPACA_(?:API|SECRET)_KEY\s*=\s*([^\s,;"\']+)',line):
   if not value.startswith(('<redacted>','...','your_')):privacy_flags.append(dict(path=path.relative_to(root).as_posix(),line=number,rule='unredacted Alpaca assignment'))
 assert fence is None,('Unclosed code fence',path.name)
 for target in re.findall(r'\[[^\]\n]+\]\(([^\n)]+)\)','\n'.join(visible)):
  target=target.strip().strip('<>')
  if target.startswith(('https://','http://','#','mailto:')):continue
  target=target.split('#',1)[0]
  p=(path.parent/target).resolve();assert p.is_relative_to(root.resolve()) and p.exists(),(path.relative_to(root).as_posix(),target)
  assert not any(part.lower().startswith('.env') for part in p.relative_to(root).parts)
  links.append(dict(document=path.relative_to(root).as_posix(),target=p.relative_to(root).as_posix()))
assert not privacy_flags,privacy_flags
main=(root/'DEVELOPMENT-JOURNEY.md').read_text(encoding='utf-8')
for item in ['643,913,470','8,446,334','635,467,136','2,818','941','241','537','434','143','1,893','2,239','zero financial twin sets','still in development']:
 assert item in main,item
assert not (root/'.git').exists()
value=dict(scope=__doc__,documents=[dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in files],
 response_records_checked=len(seen),primary_usage_matches_cumulative=True,goal_observation_checked=True,clock_intervals_checked=35,
 receipt_json_hashes_checked=941,quoted_log_hashes_checked=558,local_links_checked=len(links),selected_actual_junit_counts=checked_counts,
 bounded_capacity_values_checked=True,privacy_pattern_flags=[],dollar_charge_available=False,
 documentation_cost_excluded_by_fixed_cutoff=True,all_historical_artifacts_revalidated=False,application_final_acceptance_certified=False)
(out/'development-journey-verification.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in value.items() if k!='documents'},indent=2))
