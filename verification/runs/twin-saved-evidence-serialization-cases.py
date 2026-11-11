"""Serialization bounds are enforced before complete saved evidence is returned."""
import gzip
import hashlib
import json
import pytest
from backend.lab import trade_twin_views as views
from backend.lab.store import StateError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_original_compressed_file_size_hash_and_expansion_are_independent_requirements(tmp_path):
    path = tmp_path/'original.json.gz'
    raw = json.dumps({'preserved':'x'*5000}).encode()
    path.write_bytes(gzip.compress(raw,mtime=0))
    assert path.stat().st_size < 200 < len(raw)
    with pytest.raises(StateError, match='expansion'):
        views._load(path,200,sha(path))
    with pytest.raises(StateError, match='changed or oversized'):
        views._load(path,10000,'0'*64)
    with pytest.raises(StateError, match='changed or oversized'):
        views._load(path,10,sha(path))
    assert views._load(path,10000,sha(path)) == {'preserved':'x'*5000}


@pytest.mark.parametrize('value', [None, 'not compressed bytes', b'x'*1400])
def test_cached_chunk_wrong_type_or_compressed_size_is_refused(value):
    with pytest.raises(StateError, match='malformed or oversized'):
        views._unpack(value,200)


def test_cached_chunk_expansion_bound_and_complete_roundtrip():
    data = [{'amount':'0.000000000000001', 'detail':'x'*5000}]
    compressed = views._pack(data,6000)
    assert len(compressed) < 200
    with pytest.raises(StateError, match='expansion'):
        views._unpack(compressed,200)
    assert views._unpack(compressed,6000) == data
    with pytest.raises(StateError, match='serialization bound'):
        views._pack(data,200)


def test_response_bound_retains_canonical_amounts_and_refuses_oversized_full_page():
    value = {'rows':[{'amount':'10000000000.0000001'}]}
    assert views._bounded(value) == value
    with pytest.raises(StateError, match='response bound'):
        views._bounded({'rows':['x'*views.MAX_RESPONSE_BYTES]})


@pytest.mark.parametrize('value', [True, False, 1.0, '1', -1, 101, None])
def test_direct_saved_page_number_boundary_has_no_coercion(value):
    with pytest.raises(ValueError, match='strict integer'):
        views._number(value,0,100,'authored page')
    assert views._number(100,0,100,'authored page') == 100
