"""Exact saved-byte decoding and unchanged compressed/expanded safety bounds."""
import gzip,hashlib,io,json
from pathlib import Path
import pytest
from backend.lab import research_family_source as source
from backend.lab.store import StateError


def artifact(tmp_path,value):
    raw=json.dumps(value,separators=(',',':')).encode();compressed=gzip.compress(raw,mtime=0);path=tmp_path/'original.json.gz';path.write_bytes(compressed)
    return path,raw,compressed,hashlib.sha256(compressed).hexdigest()


def test_multiple_expansion_chunks_preserve_every_original_json_field(tmp_path):
    value={'large': 'x'*(3*1024*1024),'negative':-12.5,'missing':None,'exact':{'numerator':'-123456789012345678901','denominator':'7'}}
    path,raw,compressed,digest=artifact(tmp_path,value)
    assert source._load(path,digest)==value==json.loads(gzip.decompress(compressed))


def test_exact_expansion_limit_is_accepted_without_padding_or_truncation(tmp_path,monkeypatch):
    value={'payload':'x'*8192};path,raw,compressed,digest=artifact(tmp_path,value)
    monkeypatch.setattr(source,'MAX_ARTIFACT_BYTES',len(raw))
    assert source._load(path,digest)==value


def test_oversized_expansion_is_refused_at_one_extra_byte(tmp_path,monkeypatch):
    path,raw,compressed,digest=artifact(tmp_path,{'payload':'x'*8192});assert len(compressed)<128
    monkeypatch.setattr(source,'MAX_ARTIFACT_BYTES',128)
    with pytest.raises(StateError,match='expansion bound'):source._load(path,digest)


def test_oversized_compressed_original_is_refused_before_open(tmp_path,monkeypatch):
    path,raw,compressed,digest=artifact(tmp_path,{'payload':'abc'})
    monkeypatch.setattr(source,'MAX_ARTIFACT_BYTES',len(compressed)-1)
    def forbidden(*args,**kwargs):raise AssertionError('An oversized original cannot be read.')
    monkeypatch.setattr(Path,'open',forbidden)
    with pytest.raises(StateError,match='serialization bound'):source._load(path,digest)


def test_digest_refusal_precedes_any_decompression(tmp_path,monkeypatch):
    path,raw,compressed,digest=artifact(tmp_path,{'payload':'original'})
    def forbidden(*args,**kwargs):raise AssertionError('Wrong bytes cannot be decompressed as original evidence.')
    monkeypatch.setattr(gzip,'GzipFile',forbidden)
    with pytest.raises(StateError,match='bytes changed'):source._load(path,'0'*64)


def test_growth_after_stat_is_detected_from_the_same_observed_bytes(tmp_path,monkeypatch):
    path,raw,compressed,digest=artifact(tmp_path,{'payload':'original'});real=Path.open
    def grown(file,*args,**kwargs):return io.BytesIO(compressed+b'changed after stat') if file==path else real(file,*args,**kwargs)
    monkeypatch.setattr(Path,'open',grown)
    with pytest.raises(StateError,match='bytes changed'):source._load(path,digest)


def test_original_complete_object_contract_is_unchanged(tmp_path):
    path,raw,compressed,digest=artifact(tmp_path,['not','an','object'])
    with pytest.raises(StateError,match='complete object'):source._load(path,digest)
