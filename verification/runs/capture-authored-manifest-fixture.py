"""Capture three authored original books as a portable, non-market test fixture."""
from contextlib import closing
from pathlib import Path
import gzip,hashlib,json,os,sqlite3
root=Path.cwd();folder=root/'data/dev027/funnel-positive/e4930345acd847bba17352f24c6565d7';jid='b6d29c1d3f6e4d9bbc426637c8ae8ca9'
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    records=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='twin_part_committed' AND json_extract(details,'$.part')=0",(jid,)).fetchall()
assert len(records)==1;event_id,encoded=records[0];header=json.loads(encoded)
path=folder/'data/jobs'/jid/'twins/parts'/header['filename'];raw=path.read_bytes()
assert hashlib.sha256(raw).hexdigest()==header['sha256']
part=json.loads(gzip.decompress(raw));unique={}
for entry in part['books']:
    unique.setdefault(entry['sha256'],entry)
    if len(unique)==3:break
assert len(unique)==3
value=dict(scope=__doc__,input_kind='synthetic',market_edge_claimed=False,complete_control_comparison=False,
    original_job_id=jid,original_part=0,original_part_event_id=event_id,original_part_sha256=header['sha256'],books=list(unique.values()))
target=root/'verification/runs/authored-original-twin-manifest-books.json'
target.write_text(json.dumps(value,indent=2),encoding='utf-8')
receipt=dict(scope=__doc__,fixture=target.relative_to(root).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    bytes=target.stat().st_size,original_part_sha256=header['sha256'],book_sha256=list(unique),
    actual_credentials_user_cache_or_user_database_copied=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'portable-manifest-fixture-capture.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
