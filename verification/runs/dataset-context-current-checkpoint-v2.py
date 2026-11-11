"""Current unrestricted-universe subject; preserve the first checkpoint and all additional failures."""
from pathlib import Path
source=Path('verification/runs/dataset-context-current-checkpoint.py').read_text(encoding='utf-8')
labels=[
 'dataset-context-unrestricted-universe-current-92-focused-regression',
 'dataset-context-unrestricted-universe-and-original-four-desktop-workflows',
 'dataset-context-unrestricted-universe-eight-isolated-source-mutations',
 'dataset-context-unrestricted-universe-four-account-independent-facts-and-all-pages',
 'dataset-context-unrestricted-universe-original-authored-api-csv-offline-contract',
 'dataset-context-universe-preserving-authoritative-label-typed-build',
 'dataset-context-unrestricted-universe-managed-owner-after-own-contract-job-completed',
 'dataset-context-unrestricted-universe-83-422-120-plan-inventory',
]
start=source.index('labels=[');end=source.index('\nselected=',start)
source=source[:start]+'labels='+repr(labels)+source[end:]
source=source.replace('inputs={Path(__file__).resolve()}','inputs={Path(__file__).resolve(),root/"verification/runs/dataset-context-current-checkpoint.py"}')
needle=" 'dataset-context-two-desktop-independent-manifest-account-csv-whole-list-and-offline-evidence',\n]:"
extra=" 'dataset-context-current-existing-api-http-import-export-and-study-protocol-regression',\n 'dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression',\n 'dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal',\n"
assert source.count(needle)==1;source=source.replace(needle,needle[:-2]+extra+']:')
exec(compile(source,'dataset-context-universe-checkpoint-resolved.py','exec'))
