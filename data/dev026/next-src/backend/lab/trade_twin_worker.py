"""Complete owned paired execution and atomic original final publication."""
import gzip
import json
import re
import uuid

from .config import canonical,identity
from .result_index import file_hash
from .service import compressed_write
from .store import StateError
from .trade_twin_jobs import _checked_source
from .trade_twin_parts import FinancialParts,MAX_PART_BYTES
from .trade_twin_preparation import prepare


def _read(path):
    if path.stat().st_size>MAX_PART_BYTES:raise StateError('Saved trade-twin publication exceeds its serialization bound.')
    with gzip.open(path,'rb') as stream:raw=stream.read(MAX_PART_BYTES+1)
    if len(raw)>MAX_PART_BYTES:raise StateError('Saved trade-twin publication expansion bound exceeded.')
    return json.loads(raw)


def execute_trade_twins(worker,job,cancel):
    lab=worker.lab;prepared=prepare(lab,job,worker.owner,cancel)
    journal=FinancialParts(lab,job,worker.owner,prepared,cancel)
    if journal.plan.eligible:
        for part in range(journal.spec['part_count']):
            journal.execute(part)
            worker._progress(job,(part+1)/(journal.spec['part_count']+1),
                str(part+1)+' / '+str(journal.spec['part_count'])+' paired financial batches saved.',part+1)
    report,manifest=journal.finish();journal._control()
    context=dict(job_id=job['id'],kind='trade_twins',payload_hash=identity(job['payload']),core_hash=job['payload']['core_hash'])
    destination=lab.output_path(job['id']);folder=destination.parent/'twins/results'
    with lab.store.db() as db:
        originals=list(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved' ORDER BY id LIMIT 2",(job['id'],)))
    if originals:
        if len(originals)!=1 or file_hash(destination)!=json.loads(originals[0]['details']).get('sha256'):
            raise StateError('Original saved trade-twin publication is missing or changed.')
        saved=_read(destination)
        if any(saved.get(k)!=v for k,v in context.items()) or canonical(saved.get('report'))!=canonical(report):
            raise StateError('Original trade-twin publication differs from its complete saved financial evidence.')
        reference=saved.get('financial_manifest',{})
        if not isinstance(reference.get('filename'),str) or re.fullmatch(r'pub-[a-f0-9]{32}\.manifest\.json\.gz',reference['filename']) is None:
            raise StateError('Original financial manifest location changed.')
        path=folder/reference['filename']
        if file_hash(path)!=reference.get('sha256') or identity(_read(path))!=identity(manifest):
            raise StateError('Original committed financial manifest changed.')
        journal._authority()
    else:
        publication=uuid.uuid4().hex
        manifest_path=folder/('pub-'+publication+'.manifest.json.gz')
        compressed_write(manifest_path,manifest)
        value=context|dict(report=report,trade_twin_summary=report['summaries'],
            financial_manifest=dict(filename=manifest_path.name,sha256=file_hash(manifest_path),content_hash=identity(manifest)))
        temporary=folder/('pub-'+publication+'.result.json.gz');compressed_write(temporary,value)
        digest=file_hash(temporary);journal._authority();journal._control()
        with lab.store.db() as db:
            db.execute('BEGIN IMMEDIATE');journal._owned(db);_checked_source(lab,journal.source,db,journal._control)
            if db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='result_saved' LIMIT 1",(job['id'],)).fetchone():
                raise StateError('An original final publication already exists; no replacement is authorized.')
            if destination.exists():
                orphan=destination.parent/'twins/orphans'/('result-'+file_hash(destination)+'.json.gz')
                orphan.parent.mkdir(parents=True,exist_ok=True)
                if orphan.exists():
                    if file_hash(orphan)!=file_hash(destination):raise StateError('Preserved orphan publication changed.')
                else:orphan.write_bytes(destination.read_bytes())
            temporary.replace(destination)
            if file_hash(destination)!=digest:raise StateError('Financial publication bytes changed before commit.')
            lab.store.event('twin_financial_manifest_saved',job['id'],value['financial_manifest'],db)
            lab.store.event('result_saved',job['id'],dict(sha256=digest),db)
            journal._control();db.execute('COMMIT')
        saved=value
    journal._control()
    lab.result_index.build(job['id'],saved,cancel,owner=worker.owner)
    journal._authority()
    worker._progress(job,1,'Both original paired comparisons saved and verified.',journal.spec['part_count'])
