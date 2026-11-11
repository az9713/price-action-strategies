"""Actual original-source authority omissions using the recorded assertion-only harness.

The complete base harness and this transform are receipt inputs. Clone source,
tests and deterministic fixtures only; never credentials, prices or live DBs.
"""
from pathlib import Path
import re
root=Path.cwd()
code=(root/'verification/runs/trade-twins-core-mutations.py').read_text(encoding='utf-8')
specs=[
 ('whole-executed-cohort', 'if set(trades)!=set(traces) or set(trades)!=set(entries) or len(trades)>MAX_SOURCE_TRADES:', 'if False:', 'typed_evidence and omitted_trade'),
 ('original-cost-identity', " or trace['costs_sha256']!=identity(report['costs'])", '', 'report_local_corruptions and trace_costs'),
 ('original-signal-identity', "if signal is None or trace['signal_sha256']!=identity(signal):", 'if signal is None:', 'report_local_corruptions and trace_signal_hash'),
 ('original-entry-ledger', "if trace['entry_ledger_sha256']!=identity(entry):", 'if False:', 'report_local_corruptions and trace_ledger'),
 ('original-event-loss', 'if len(matches)!=1:', 'if not matches:\n        return 0\n    if False:', 'missing_original_trial_events'),
 ('original-attempt-output', " or binding['attempt_computed_sha256']!=identity(report)", '', 'original_storage_guard and attempt_computation'),
 ('original-trial-output', " or binding['computed_sha256']!=identity(report)", '', 'original_storage_guard and trial_computation'),
 ('late-original-price', "if file_hash(lab.datasets_root/payload['dataset_id']/'minutes.parquet')!=current_manifest['parquet_sha256']:", 'if False:', 'late_original_changes and price_bytes'),
 ('late-original-manifest', "if identity(current_manifest)!=payload['dataset_manifest_hash']:", 'if False:', 'late_original_changes and manifest_and_price'),
 ('late-original-registry', '_,_,again=_saved_state(lab,jid,part)', 'again=binding', 'late_original_changes and (job_state or result_event)')]
pattern=r'specs=\[.*?\]\ninputs='
assert len(re.findall(pattern,code,re.DOTALL))==1
code=re.sub(pattern,lambda _: 'specs='+repr(specs)+'\ninputs=',code,count=1,flags=re.DOTALL)
for before,after in [
 ('Actual isolated D046 guard mutations','Actual isolated original-source authority guard mutations'),
 ('tests/test_trade_twins.py','tests/test_trade_twin_source.py'),
 ('backend/lab/trade_twins.py','backend/lab/trade_twin_source.py'),
 ('mutated-trade_twins.py','mutated-trade_twin_source.py'),
 ('trade-twins-core-mutations.json','trade-twins-source-authority-mutations.json')]:
 assert before in code,before
 code=code.replace(before,after)
needle="originals={p.relative_to(source).as_posix()"
assert code.count(needle)==1
code=code.replace(needle,"inputs += [*sorted((source/'tests').glob('*.py')), *sorted((source/'verification/fixtures').glob('*.json'))]\n"+needle)
exec(compile(code,'recorded-original-source-authority-mutation-harness','exec'))
