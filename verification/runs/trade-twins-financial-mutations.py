"""Actual isolated financial twin mutations; require assertion-only kills."""
from pathlib import Path
import re
root=Path.cwd();code=(root/'verification/runs/trade-twins-core-mutations.py').read_text(encoding='utf-8')
specs=[
 ('original-quantity', "side=match['side'];qty=D(match['quantity'])", "side=match['side'];qty=D(match['quantity'])/2", 'hand_elapsed_accounts'),
 ('sell-value-fee', "quantity*price*D(cost.sell_fee_per_dollar) if direction==-1 else zero", "zero", 'each_fee_has_a_hand'),
 ('stop-first-ambiguity', "if cfg.stop_kind=='hard' and (D(bar['low'])<=p['stop'] if side==1 else D(bar['high'])>=p['stop']):hits.append('stop')", "if False:hits.append('stop')", 'barrier_precedence and ambiguous and barrier_capped'),
 ('one-tick-through', "if (D(bar['high'])>=p['target']+tick if side==1 else D(bar['low'])<=p['target']-tick):hits.append('target')", "if (D(bar['high'])>=p['target'] if side==1 else D(bar['low'])<=p['target']):hits.append('target')", 'barrier_precedence and target_touch and barrier_capped'),
 ('opening-cutoff-priority', "elif at==cutoff and match['exit_boundary']=='open':close(bar['open'],'elapsed_cutoff',at)", "elif False:close(bar['open'],'elapsed_cutoff',at)", 'opening_cutoff_precedes and barrier_capped'),
 ('fixed-duration-barriers', "if policy=='barrier_capped_elapsed_v1' and hits:", "if hits:", 'barrier_precedence and stop and fixed_elapsed'),
 ('fractional-split-quantity', "ratio=D(action.value);position['quantity']*=ratio", "ratio=D(1);position['quantity']*=ratio", 'split_fractional_shares'),
 ('short-dividend-sign', "amount=side*position['quantity']*D(action.value)", "amount=position['quantity']*D(action.value)", 'split_fractional_shares'),
 ('unpaid-marked-entitlement', 'equity=cash+side*exposure+outstanding', 'equity=cash+side*exposure', 'split_fractional_shares and False'),
 ('elapsed-calendar-borrow', "weighted+=rate*D((at-cursor).total_seconds())", "weighted+=rate*D(min(60,(at-cursor).total_seconds()))", 'calendar_borrow_has_an_independent_hand'),
 ('stale-volume-reference', "before=prior[-1] if prior and prior[-1]['timestamp']==previous_expected else None", "before=prior[-1] if prior else None", 'stale_or_missing and True')]
pattern=r'specs=\[.*?\]\ninputs='
assert len(re.findall(pattern,code,re.DOTALL))==1
code=re.sub(pattern,lambda _: 'specs='+repr(specs)+'\ninputs=',code,count=1,flags=re.DOTALL)
for before,after in [
 ('Actual isolated D046 guard mutations','Actual isolated financial twin accounting and execution mutations'),
 ('tests/test_trade_twins.py','tests/test_trade_twin_execution.py'),
 ('backend/lab/trade_twins.py','backend/lab/trade_twin_execution.py'),
 ('mutated-trade_twins.py','mutated-trade_twin_execution.py'),
 ('trade-twins-core-mutations.json','trade-twins-financial-mutations.json')]:
 assert before in code,before
 code=code.replace(before,after)
needle="originals={p.relative_to(source).as_posix()"
assert code.count(needle)==1
code=code.replace(needle,"inputs += [*sorted((source/'tests').glob('*.py')), *sorted((source/'verification/fixtures').glob('*.json'))]\n"+needle)
exec(compile(code,'recorded-financial-twin-mutation-harness','exec'))
