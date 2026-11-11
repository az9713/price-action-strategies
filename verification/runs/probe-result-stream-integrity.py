"""Owned SQLite TEXT/UTF-8 incremental-hash capability; no application data or credentials."""
from pathlib import Path
import hashlib,json,os,sqlite3,tempfile,tracemalloc
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
with tempfile.TemporaryDirectory(prefix='pa-result-text-stream-probe-') as directory:
 path=Path(directory)/'probe.sqlite3';db=sqlite3.connect(path)
 db.execute('CREATE TABLE probe(id TEXT PRIMARY KEY,payload TEXT)')
 value=dict(note=chr(0x6e2c),n=1.0,items=['x'*1000000]);raw=json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True)
 db.execute('INSERT INTO probe VALUES(?,?)',('one',raw));db.commit();rowid=db.execute('SELECT rowid FROM probe WHERE id=?',('one',)).fetchone()[0]
 def stream():
  digest=hashlib.sha256();size=0;chunks=0;maximum=0
  with db.blobopen('probe','payload',rowid,readonly=True) as blob:
   while chunk:=blob.read(65536):digest.update(chunk);size+=len(chunk);chunks+=1;maximum=max(maximum,len(chunk))
  return dict(sha256=digest.hexdigest(),bytes=size,chunks=chunks,maximum_chunk_bytes=maximum)
 tracemalloc.start();before=stream();_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 assert before['sha256']==hashlib.sha256(raw.encode('utf-8')).hexdigest() and before['bytes']==len(raw.encode('utf-8'))
 changed=raw.replace('x','y',1);assert len(changed.encode('utf-8'))==before['bytes']
 db.execute('UPDATE probe SET payload=? WHERE id=?',(changed,'one'));db.commit();after=stream()
 assert after['sha256']!=before['sha256'] and after['sha256']==hashlib.sha256(changed.encode()).hexdigest()
 assert before['maximum_chunk_bytes']<=65536 and peak<1024*1024
 db.close()
result=dict(scope=__doc__,sqlite_version=sqlite3.sqlite_version,original=before,changed=after,python_peak_bytes=peak,same_length_change_detected=True,application_data_read=False,credentials_read=False,sources=['https://docs.python.org/3.13/library/sqlite3.html','https://www.sqlite.org/c3ref/blob_open.html'])
(out/'sqlite-text-stream-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
