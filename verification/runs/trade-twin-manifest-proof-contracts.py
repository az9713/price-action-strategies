"""Pure inspection-manifest reuse never replaces current hashes or authority."""
from collections import OrderedDict
from pathlib import Path
from copy import deepcopy
import hashlib,json
import pytest
from backend.lab import trade_twin_evidence as evidence,trade_twin_parts as parts
from backend.lab.config import identity
from backend.lab.store import StateError

@pytest.fixture
def books():
    raw=Path(__file__).with_name('authored-original-twin-manifest-books.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='9bf4e9d8c00965948a699d43bedca76c0cbfd9e2276cdd9eb8282d5b4cd3996a'
    value=json.loads(raw)
    assert value['input_kind']=='synthetic' and len(value['books'])==3 and not value['complete_control_comparison']
    return value['books']

@pytest.fixture
def validator(books):
    # Only this pure shape/manifest method is exercised here; actual ownership,
    # checkpoint and original-event authority are covered by the real parts suite.
    journal=object.__new__(parts.FinancialParts)
    journal.base={k:v for k,v in books[0]['inputs'].items() if k not in {'match','policy'}}
    journal.manifest_proofs=OrderedDict();journal._control=lambda:False
    return journal

def test_identical_complete_book_reuses_only_pure_manifest_calculation(books,validator,monkeypatch):
    calculate=evidence.book_manifest;verify=evidence.verify_manifest;calls=[];verified=[];controls=[]
    def calculated(*a,**k):calls.append(True);return calculate(*a,**k)
    def checked(*a,**k):verified.append(True);return verify(*a,**k)
    monkeypatch.setattr(evidence,'book_manifest',calculated);monkeypatch.setattr(evidence,'verify_manifest',checked)
    validator._control=lambda:controls.append(True) or False
    validator._book_shape(books[0]);first_verified=len(verified)
    validator._book_shape(deepcopy(books[0]))
    assert len(calls)==1 and first_verified>=1 and len(verified)==first_verified+1 and len(controls)>=2

@pytest.mark.parametrize('fault',['changed_book_old_digest','changed_manifest_old_digest','changed_manifest_rehashed','changed_descriptor','wrong_evidence_digest'])
def test_warm_proof_never_accepts_changed_book_manifest_or_inputs(books,validator,fault):
    validator._book_shape(books[0]);bad=deepcopy(books[0])
    if fault=='changed_book_old_digest':bad['book']['net_profit']='123456789'
    elif fault.startswith('changed_manifest'):
        bad['evidence']['unexpected_rehashed_data']=True
        if fault.endswith('rehashed'):bad['evidence_sha256']=identity(bad['evidence'])
    elif fault=='changed_descriptor':bad['inputs']['core_hash']='0'*64;bad['key']=identity(bad['inputs'])
    else:bad['evidence_sha256']='0'*64
    with pytest.raises((StateError,ValueError,TypeError)):validator._book_shape(bad)
    validator._book_shape(books[0])

def test_cached_manifest_digest_is_not_trusted_after_it_is_corrupted(books,validator):
    validator._book_shape(books[0]);validator.manifest_proofs[books[0]['sha256']]='0'*64
    validator._book_shape(books[0])
    assert validator.manifest_proofs[books[0]['sha256']]==books[0]['evidence_sha256']

def test_manifest_proof_eviction_revalidates_complete_books(books,validator,monkeypatch):
    monkeypatch.setattr(parts,'MANIFEST_PROOFS',2);calculate=evidence.book_manifest;calls=[]
    def calculated(*a,**k):calls.append(True);return calculate(*a,**k)
    monkeypatch.setattr(evidence,'book_manifest',calculated)
    for entry in [*books,books[0]]:
        validator._book_shape(entry);assert len(validator.manifest_proofs)<=2
    assert len(calls)==4

def test_cancel_or_lost_owner_is_checked_even_for_a_known_manifest(books,validator):
    validator._book_shape(books[0])
    def canceled():raise InterruptedError('Authored stop before cached manifest use')
    validator._control=canceled
    with pytest.raises(InterruptedError):validator._book_shape(books[0])
