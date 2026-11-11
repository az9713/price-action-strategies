"""Add metric/job/part context to the unchanged first financial tolerance assertion."""
from pathlib import Path
source=Path('verification/runs/check-common-browser-accounts.py').read_text(encoding='utf-8')
before='(a,str(b),tolerance)'
after="(globals().get('jid'),globals().get('part'),globals().get('k'),a,str(b),tolerance)"
assert source.count(before)==1
exec(compile(source.replace(before,after),'check-common-browser-accounts-v2-resolved.py','exec'))
