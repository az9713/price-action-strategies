"""Owned SQLite row layout/metadata-update probe; not strategy or numerical capacity evidence."""
from pathlib import Path
import hashlib,json,os,sqlite3,tempfile,time
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);contract=json.loads((root/'verification/fixtures/sqlite-job-hot-row-probe.json').read_text(encoding='utf-8'));records=[]
def digest(db):
 result=hashlib.sha256()
 with db.blobopen('jobs','payload',1,readonly=True) as blob:
  while part:=blob.read(65536):result.update(part)
 return result.hexdigest()
with tempfile.TemporaryDirectory(prefix='owned-hot-row-probe-',dir=root/'data') as directory:
 owned=Path(directory).resolve();assert owned.is_relative_to((root/'data').resolve())
 for size in contract['payload_sizes']:
  payload='X'*size;expected=hashlib.sha256(payload.encode()).hexdigest()
  for layout in contract['layouts']:
   path=owned/(str(size)+'-'+layout+'.sqlite3');db=sqlite3.connect(path,isolation_level=None)
   try:
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');db.execute('PRAGMA wal_autocheckpoint=0')
    columns='id TEXT PRIMARY KEY,payload TEXT,status TEXT,owner TEXT,cancel_requested INTEGER,progress REAL' if layout.startswith('payload_before_live_fields') else 'id TEXT PRIMARY KEY,status TEXT,owner TEXT,cancel_requested INTEGER,progress REAL,payload TEXT'
    db.execute('CREATE TABLE jobs('+columns+')');db.execute('INSERT INTO jobs(id,payload,status,owner,cancel_requested,progress) VALUES(?,?,?,?,?,?)',('owned',payload,'running','owner',0,0.0))
    if 'covering_index' in layout:db.execute('CREATE INDEX owned_live_control ON jobs(id,status,owner,cancel_requested)')
    if layout.endswith('analyzed'):db.execute('ANALYZE')
    query='SELECT status,owner,cancel_requested FROM jobs'+(' INDEXED BY owned_live_control' if layout.endswith('covering_index') else '')+' WHERE id=?'
    plan=[row[-1] for row in db.execute('EXPLAIN QUERY PLAN '+query,('owned',))]
    if layout.endswith('covering_index'):assert any('COVERING INDEX owned_live_control' in row for row in plan)
    assert digest(db)==expected;db.execute('PRAGMA wal_checkpoint(TRUNCATE)');started=time.perf_counter()
    for _ in range(contract['reads']):assert db.execute(query,('owned',)).fetchone()==('running','owner',0)
    read_seconds=time.perf_counter()-started;started=time.perf_counter()
    for ordinal in range(contract['updates']):db.execute('UPDATE jobs SET progress=? WHERE id=?',((ordinal+1)/contract['updates'],'owned'))
    write_seconds=time.perf_counter()-started;wal=Path(str(path)+'-wal');wal_bytes=wal.stat().st_size;assert digest(db)==expected and db.execute('SELECT progress FROM jobs').fetchone()[0]==1
    records.append(dict(payload_bytes=size,layout=layout,query_plan=plan,reads=contract['reads'],read_seconds=read_seconds,updates=contract['updates'],update_seconds=write_seconds,update_wal_bytes=wal_bytes,payload_sha256=expected,original_fixture_payload_unchanged=True))
   finally:db.close()
value=dict(scope=__doc__,sqlite_version=sqlite3.sqlite_version,contract=contract,observations=records,numerical_accounts_executed=0,app_database_modified=False);(out/'sqlite-job-hot-row-probe.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
