"""Original member-bound manifests and bounded financial evidence chunks."""
import importlib,importlib.util,json,hashlib,copy
import pytest


def test_original_book_evidence_manifest_is_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_evidence') is not None,'Original-bound book inspection manifests are not implemented.'


@pytest.fixture
def evidence():return importlib.import_module('backend.lab.trade_twin_evidence')


@pytest.fixture
def book():
    from test_trade_twin_execution import frame,match_for,CFG,ZERO,ACCOUNT
    from backend.lab.trade_twin_execution import execute_twin
    from backend.lab.trade_twin_parts import freeze
    data=frame();match=match_for(data,start=20,end=50)
    return freeze(execute_twin(data,match,CFG,ZERO,ACCOUNT))


def independent_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def test_complete_actual_financial_book_has_independent_flat_chunk_hashes(evidence,book):
    manifest=evidence.book_manifest(book)
    assert manifest['book_sha256']==independent_hash(book)
    assert manifest['scalar_fields']=={k:v for k,v in book.items() if k not in evidence.ARRAYS}
    assert manifest['counts']=={k:len(book[k]) for k in evidence.ARRAYS}
    for kind in evidence.ARRAYS:
        chunks=[book[kind][i:i+25] for i in range(0,len(book[kind]),25)]
        assert manifest['arrays'][kind]==[independent_hash(c) for c in chunks]
        for index,chunk in enumerate(chunks):
            assert evidence.verify_chunk(manifest,kind,index,chunk)==chunk
    assert evidence.verify_manifest(manifest,independent_hash(manifest),independent_hash(book))==manifest


@pytest.mark.parametrize('fault',['scalar','hash','count','chunks','policy','kind','extra','bool'])
def test_self_rehashed_or_malformed_manifest_cannot_replace_original_member(evidence,book,fault):
    good=evidence.book_manifest(book);bad=copy.deepcopy(good)
    if fault=='scalar':bad['scalar_fields']['net_profit']='1000000'
    elif fault=='hash':bad['book_sha256']='0'*64
    elif fault=='count':bad['counts']['ledger']+=1
    elif fault=='chunks':bad['arrays']['ledger']=[]
    elif fault=='policy':bad['version']=2
    elif fault=='kind':bad['arrays']['invented']=[]
    elif fault=='extra':bad['extra']=1
    else:bad['counts']['ledger']=True
    with pytest.raises(ValueError):evidence.verify_manifest(bad,independent_hash(good),independent_hash(book))


@pytest.mark.parametrize('fault',['changed','missing','extra','wrong_array','wrong_index','boolean_index'])
def test_requested_chunk_cannot_be_substituted_or_sliced(evidence,book,fault):
    manifest=evidence.book_manifest(book);kind='ledger';index=0;chunk=copy.deepcopy(book[kind][:25])
    if fault=='changed':chunk[0]['cash_after']='123456'
    elif fault=='missing':chunk=chunk[:-1]
    elif fault=='extra':chunk=chunk+[chunk[0]]
    elif fault=='wrong_array':kind='equity'
    elif fault=='wrong_index':index=1
    else:index=True
    with pytest.raises(ValueError):evidence.verify_chunk(manifest,kind,index,chunk)


def test_chunk_boundary_last_page_and_empty_array_are_complete(evidence,book):
    book['ledger']=[dict(sequence=i,amount=str(i)) for i in range(53)]
    manifest=evidence.book_manifest(book)
    assert len(manifest['arrays']['ledger'])==3
    assert evidence.verify_chunk(manifest,'ledger',2,book['ledger'][50:])==book['ledger'][50:]
    assert manifest['counts']['rejected']==0 and manifest['arrays']['rejected']==[]
    with pytest.raises(ValueError):evidence.verify_chunk(manifest,'rejected',0,[])


def test_oversized_or_nonfinite_evidence_and_cancellation_refuse_whole_book(evidence,book):
    bad=copy.deepcopy(book);bad['ledger']=[dict(oversized='x'*(2*1024*1024))]
    with pytest.raises(ValueError):evidence.book_manifest(bad)
    bad=copy.deepcopy(book);bad['trade']['entry_price']=float('nan')
    with pytest.raises(ValueError):evidence.book_manifest(bad)
    with pytest.raises(InterruptedError):evidence.book_manifest(book,lambda:True)
