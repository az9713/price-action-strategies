"""Reuse the recorded assertion-only harness for four original-entry trace defects.

The complete base harness is an explicit receipt input. Only the declared target,
tests, fixture support and four preflighted mutations differ; all cleanup,
green-baseline, original-byte, compile and assertion-only requirements remain.
"""
from pathlib import Path
import re
root=Path.cwd()
code=(root/'verification/runs/trade-twins-core-mutations.py').read_text(encoding='utf-8')
specs=[
 ('raw-entry-atr', 'entry_atr=float(Decimal(str(signal.atr))/Decimal(str(factor)))', 'entry_atr=float(signal.atr)', 'entry_after_prior_split'),
 ('original-raw-stop', 'entry_stop=stop,entry_target=target', 'entry_stop=signal.stop,entry_target=target', 'entry_after_prior_split'),
 ('original-entry-ledger', 'entry_ledger_sha256=identity(result.ledger[-1])', 'entry_ledger_sha256=identity({})', 'execution_freezes'),
 ('missing-entry-capture', 'result.entry_traces.append(trace|dict(trace_sha256=identity(trace)))', 'if False: result.entry_traces.append(trace|dict(trace_sha256=identity(trace)))', 'execution_freezes')]
pattern=r'specs=\[.*?\]\ninputs='
assert len(re.findall(pattern,code,re.DOTALL))==1
code=re.sub(pattern,lambda _: 'specs='+repr(specs)+'\ninputs=',code,count=1,flags=re.DOTALL)
replacements=[
 ('Actual isolated D046 guard mutations','Actual isolated original-entry trace mutations'),
 ('tests/test_trade_twins.py','tests/test_entry_traces.py'),
 ('backend/lab/trade_twins.py','backend/lab/engine.py'),
 ('mutated-trade_twins.py','mutated-engine.py'),
 ('trade-twins-core-mutations.json','trade-twins-entry-trace-mutations.json')]
for before,after in replacements:
 assert before in code,before
 code=code.replace(before,after)
needle="originals={p.relative_to(source).as_posix()"
assert code.count(needle)==1
code=code.replace(needle,"inputs += [source/'tests/test_reference_execution.py', *sorted((source/'verification/fixtures').glob('*.json'))]\n"+needle)
exec(compile(code,'recorded-entry-trace-mutation-harness','exec'))
