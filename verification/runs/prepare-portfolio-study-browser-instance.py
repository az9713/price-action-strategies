from pathlib import Path
import sqlite3,shutil,json,sys
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.store import Store
instance=root/'data/portfolio-study-browser-instance';assert not instance.exists()
store=Store(instance)
with sqlite3.connect(root/'data/lab.sqlite3') as source,store.db() as target:
 for table in ['studies','viewed_windows','events']:
  fields=[r[1] for r in source.execute('PRAGMA table_info('+table+')')]
  target.executemany('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',source.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall())
shutil.copytree(root/'data/datasets/90f347229b2fb03ec112ee71',instance/'data/datasets/90f347229b2fb03ec112ee71')
shutil.copytree(root/'frontend/dist',instance/'frontend/dist')
assert not (instance/'.env').exists()
print(json.dumps(dict(instance=instance.relative_to(root).as_posix(),isolated_store=True,prior_protected_dates_preserved=True,credentials_copied=False)))
