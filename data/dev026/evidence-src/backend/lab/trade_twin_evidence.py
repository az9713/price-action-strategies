"""Original member-bound, flat chunk manifests for complete financial books.

The manifest is produced with the original book, before its part is committed.
Readers additionally require its digest from an original computed set member.
Neither a manifest's self-consistency nor a derived view is original authority.
"""
import json
import re
from .config import canonical, identity
from .trade_twin_amounts import read_amount

ARRAYS = ('ledger', 'equity', 'rejected', 'encounters')
CHUNK_RECORDS = 25
MAX_CHUNK_BYTES = 2*1024*1024
MAX_MANIFEST_BYTES = 16*1024*1024
BOOK_FIELDS = {'status', 'failure', 'trade', 'ledger', 'equity', 'rejected',
               'encounters', 'geometry', 'financing', 'net_profit', 'final_cash',
               'final_receivables', 'accounting_residual'}
MANIFEST_FIELDS = {'version', 'chunk_records', 'book_sha256', 'scalar_fields', 'counts', 'arrays'}


def _cancel(cancel):
    if cancel and cancel():
        raise InterruptedError('Saved financial evidence canceled.')


def _bytes(value, maximum):
    data = canonical(value).encode('utf-8')
    if len(data) > maximum:
        raise ValueError('Saved financial evidence expansion bound exceeded; no subset accepted.')
    return data


def _digest(value):
    return isinstance(value, str) and re.fullmatch('[a-f0-9]{64}', value) is not None


def book_manifest(book, cancel=None):
    """Describe every original array record; never select a profitable subset."""
    _cancel(cancel)
    if not isinstance(book, dict) or set(book) != BOOK_FIELDS:
        raise ValueError('The complete financial book schema is required.')
    counts = {}; arrays = {}
    for kind in ARRAYS:
        records = book[kind]
        if not isinstance(records, list):
            raise ValueError('Saved financial book arrays must be complete lists.')
        counts[kind] = len(records); arrays[kind] = []
        for offset in range(0, len(records), CHUNK_RECORDS):
            _cancel(cancel)
            chunk = records[offset:offset+CHUNK_RECORDS]
            _bytes(chunk, MAX_CHUNK_BYTES)
            arrays[kind].append(identity(chunk))
    value = dict(version=1, chunk_records=CHUNK_RECORDS, book_sha256=identity(book),
                 scalar_fields={k: v for k, v in book.items() if k not in ARRAYS},
                 counts=counts, arrays=arrays)
    _bytes(value, MAX_MANIFEST_BYTES)
    checked = verify_manifest(value, identity(value), value['book_sha256'])
    _cancel(cancel)
    return checked


def verify_manifest(value, original_manifest_hash, original_book_hash):
    """Require externally verified original member digests, not caller authority."""
    if (not _digest(original_manifest_hash) or not _digest(original_book_hash)
            or not isinstance(value, dict) or set(value) != MANIFEST_FIELDS
            or type(value['version']) is not int or value['version'] != 1
            or type(value['chunk_records']) is not int or value['chunk_records'] != CHUNK_RECORDS
            or value['book_sha256'] != original_book_hash
            or not isinstance(value['scalar_fields'], dict)
            or set(value['scalar_fields']) != BOOK_FIELDS-set(ARRAYS)
            or not isinstance(value['counts'], dict) or set(value['counts']) != set(ARRAYS)
            or not isinstance(value['arrays'], dict) or set(value['arrays']) != set(ARRAYS)):
        raise ValueError('Original financial inspection manifest is missing or malformed.')
    encoded = _bytes(value, MAX_MANIFEST_BYTES)
    if identity(value) != original_manifest_hash:
        raise ValueError('Inspection manifest differs from its original member binding.')
    scalar = value['scalar_fields']
    if scalar['status'] == 'complete':
        read_amount(scalar['net_profit'])
        if not isinstance(scalar['trade'], dict) or scalar['failure'] is not None:
            raise ValueError('Completed inspection evidence requires its complete trade.')
    elif scalar['status'] != 'failed' or scalar['net_profit'] is not None or not scalar['failure']:
        raise ValueError('Inspection evidence cannot hide a failed financial book.')
    for kind in ARRAYS:
        count = value['counts'][kind]; hashes = value['arrays'][kind]
        if (type(count) is not int or count < 0 or not isinstance(hashes, list)
                or len(hashes) != (count+CHUNK_RECORDS-1)//CHUNK_RECORDS
                or any(not _digest(digest) for digest in hashes)):
            raise ValueError('Original inspection count or complete chunk sequence differs.')
    return json.loads(encoded)


def verify_chunk(manifest, kind, index, records):
    """Verify a complete bounded chunk against an already authorized manifest."""
    if (kind not in ARRAYS or type(index) is not int or index < 0
            or not isinstance(records, list) or index >= len(manifest['arrays'][kind])):
        raise ValueError('Choose an original financial array chunk.')
    expected = min(CHUNK_RECORDS, manifest['counts'][kind]-index*CHUNK_RECORDS)
    encoded = _bytes(records, MAX_CHUNK_BYTES)
    if len(records) != expected or identity(records) != manifest['arrays'][kind][index]:
        raise ValueError('Saved financial chunk differs from its complete original records.')
    return json.loads(encoded)
