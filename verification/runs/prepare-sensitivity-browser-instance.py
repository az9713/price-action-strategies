from pathlib import Path
import hashlib,json,sqlite3,shutil,sys
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.store import Store
instance=root/'data/sensitivity-browser-instance'
assert not instance.exists(),'Use a fresh isolated verification instance.'
store=Store(instance)
# Preserve the real research access boundaries without sharing the work queue.
with sqlite3.connect(root/'data/lab.sqlite3') as source,store.db() as target:
    for table in ['studies','viewed_windows','events']:
        fields=[r[1] for r in source.execute('PRAGMA table_info('+table+')')]
        target.executemany('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',source.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall())
source=root/'data/datasets/90f347229b2fb03ec112ee71'
assert source.is_dir()
shutil.copytree(source,instance/'data/datasets'/source.name)
shutil.copytree(root/'frontend/dist',instance/'frontend/dist')
assert not (instance/'.env').exists()
print(json.dumps(dict(instance=instance.relative_to(root).as_posix(),isolated_job_store=True,copied_guard_tables=['studies','viewed_windows','events'],dataset=source.name,credentials_copied=False)))
