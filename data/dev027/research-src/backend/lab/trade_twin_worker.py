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
    if path.stat().st_size>MAX_PART_BYTES:
        raise StateError('Saved trade-twin publication exceeds its serialization bound.')
    with gzip.open(path,'rb') as stream:raw=stream.read(MAX_PART_BYTES+1)
    if len(raw)>MAX_PART_BYTES:
        raise StateError('Saved trade-twin publication expansion bound exceeded.')
    return json.loads(raw)


def _publication(db,job_id):
    """One original atomic manifest/result pair, or no committed publication.

    A renamed file without these events can be a real transaction-death orphan.
    A surviving half-pair, duplicate, changed order or later view is evidence
    that original publication authority was lost; it must never be replaced.
    """
    rows=db.execute("SELECT id,kind,substr(details,1,16385) details,length(CAST(details AS BLOB)) bytes FROM events WHERE entity_id=? AND kind IN ('twin_financial_manifest_saved','result_saved') ORDER BY id LIMIT 3",(job_id,)).fetchall()
    if not rows:
        if db.execute("SELECT 1 FROM events WHERE entity_id=? AND kind='trade_twin_view_saved' LIMIT 1",(job_id,)).fetchone():
            raise StateError('Original financial publication is missing behind a saved inspection view.')
        return None
    if (len(rows)!=2 or rows[0]['kind']!='twin_financial_manifest_saved'
            or rows[1]['kind']!='result_saved' or rows[0]['id']+1!=rows[1]['id']
            or any(row['bytes']>16384 for row in rows)):
        raise StateError('Exactly one original atomic financial manifest/result pair is required; replacement is refused.')
    try:
        manifest=json.loads(rows[0]['details']);saved=json.loads(rows[1]['details'])
    except (ValueError,TypeError) as error:
        raise StateError('Original financial publication metadata is malformed.') from error
    if (not isinstance(manifest,dict) or set(manifest)!={'filename','sha256','content_hash'}
            or not isinstance(manifest['filename'],str)
            or re.fullmatch(r'pub-[a-f0-9]{32}\.manifest\.json\.gz',manifest['filename']) is None
            or any(not isinstance(manifest[key],str) or re.fullmatch('[a-f0-9]{64}',manifest[key]) is None for key in ('sha256','content_hash'))
            or not isinstance(saved,dict) or set(saved)!={'sha256'}
            or not isinstance(saved['sha256'],str) or re.fullmatch('[a-f0-9]{64}',saved['sha256']) is None):
        raise StateError('Original financial publication bindings are malformed.')
    return dict(manifest_event_id=rows[0]['id'],result_event_id=rows[1]['id'],manifest=manifest,sha256=saved['sha256'])


def _same_publication(lab,db,job_id,expected):
    if _publication(db,job_id)!=expected or file_hash(lab.output_path(job_id))!=expected['sha256']:
        raise StateError('Original financial publication changed during owned work; replacement is refused.')


def execute_trade_twins(worker,job,cancel):
    lab=worker.lab
    with lab.store.db() as db:
        db.execute('BEGIN');published=_publication(db,job['id'])
        if published is not None:
            _same_publication(lab,db,job['id'],published)
    prepared=prepare(lab,job,worker.owner,cancel)
    journal=FinancialParts(lab,job,worker.owner,prepared,cancel)
    if journal.plan.eligible:
        for part in range(journal.spec['part_count']):
            journal.execute(part)
            worker._progress(job,(part+1)/(journal.spec['part_count']+1),
                str(part+1)+' / '+str(journal.spec['part_count'])+' paired financial batches saved.',part+1)
    report,manifest=journal.finish();journal._control()
    from .trade_twin_views import Originals,build_view,VIEW_EVENT
    inspection=Originals(lab,job['id'],building=(report,manifest),owner=worker.owner,cancel=cancel)
    view=build_view(inspection)
    context=dict(job_id=job['id'],kind='trade_twins',payload_hash=identity(job['payload']),core_hash=job['payload']['core_hash'])
    destination=lab.output_path(job['id']);folder=destination.parent/'twins/results'
    if published is not None:
        saved=_read(destination)
        if any(saved.get(k)!=v for k,v in context.items()) or canonical(saved.get('report'))!=canonical(report):
            raise StateError('Original trade-twin publication differs from its complete saved financial evidence.')
        reference=saved.get('financial_manifest',{})
        if reference!=published['manifest']:
            raise StateError('Original manifest event differs from the committed result reference.')
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
            if _publication(db,job['id']) is not None:
                raise StateError('An original final publication already exists; no replacement is authorized.')
            if destination.exists():
                orphan=destination.parent/'twins/orphans'/('result-'+file_hash(destination)+'.json.gz')
                orphan.parent.mkdir(parents=True,exist_ok=True)
                if orphan.exists():
                    if file_hash(orphan)!=file_hash(destination):
                        raise StateError('Preserved orphan publication changed.')
                else:orphan.write_bytes(destination.read_bytes())
            temporary.replace(destination)
            if file_hash(destination)!=digest:
                raise StateError('Financial publication bytes changed before commit.')
            lab.store.event('twin_financial_manifest_saved',job['id'],value['financial_manifest'],db)
            lab.store.event('result_saved',job['id'],dict(sha256=digest),db)
            published=_publication(db,job['id'])
            journal._control();db.execute('COMMIT')
        saved=value
    journal._control();inspection.guard();journal._authority()
    with lab.store.db() as db:
        db.execute('BEGIN IMMEDIATE');journal._owned(db);_checked_source(lab,journal.source,db,journal._control)
        _same_publication(lab,db,job['id'],published)
        lab.store.event(VIEW_EVENT,job['id'],view|dict(root_sha256=published['sha256']),db)
        journal._control();db.execute('COMMIT')
    lab.result_index.build(job['id'],saved,cancel,owner=worker.owner)
    journal._authority()
    with lab.store.db() as db:
        db.execute('BEGIN');journal._owned(db);_same_publication(lab,db,job['id'],published)
    worker._progress(job,1,'Both original paired comparisons saved and verified.',journal.spec['part_count'])
