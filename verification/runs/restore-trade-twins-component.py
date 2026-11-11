"""Actual fresh restoration of D046 source and all new matching/entry tests.

The byte/path/source-preservation restorer is a separately recorded explicit
input. Adapt only archive names, expected isolated core, owned destination and
the additional tests. This is not a fresh installation or final acceptance.
"""
from pathlib import Path
root=Path.cwd()
code=(root/'verification/runs/restore-integrated025-checkpoint.py').read_text(encoding='utf-8')
replacements=[
 ('20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint.json','20261109T183428847989Z-trade-twins-current-434-cases-fourteen-mutations-original-traces-and-recoverable-source-checkpoint.json'),
 ('integrated025-component-checkpoint.json','trade-twins-component-checkpoint.json'),
 ('integrated025-source-manifest.json','trade-twins-source-manifest.json'),
 ('integrated025-source-checkpoint.zip','trade-twins-source-checkpoint.zip'),
 ("checkpoint['core_hash']","checkpoint['isolated_core']['current']"),
 ('data/dev025/reconstructions','data/dev026/reconstructions'),
 ("'tests/test_spread_public_schema.py', 'tests/test_coverage_gate.py',","'tests/test_spread_public_schema.py', 'tests/test_coverage_gate.py', 'tests/test_trade_twins.py', 'tests/test_entry_traces.py',"),
 ('integrated-source-reconstruction.json','trade-twins-source-reconstruction.json'),
 ('Actually restore the complete integrated source archive and test its catalog/schema.','Actually restore the D046 component source archive and test all new matching/entry behavior plus catalog/schema.')]
for before,after in replacements:
 assert before in code,before
 code=code.replace(before,after)
exec(compile(code,'recorded-d046-source-restorer','exec'))
