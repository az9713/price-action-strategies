"""A small original artifact must not request a512 MiB temporary read buffer."""
import gzip,hashlib
from pathlib import Path
from backend.lab import research_family_source as source


def test_small_original_file_reads_use_observed_file_size_and_bounded_expansion(tmp_path,monkeypatch):
    data=b'{"original":"complete"}';compressed=gzip.compress(data,mtime=0);path=tmp_path/'original.json.gz';path.write_bytes(compressed)
    real_open=Path.open;real_gzip=gzip.GzipFile;reads=[]
    class File:
        def __init__(self,stream,maximum,kind):self.stream=stream;self.maximum=maximum;self.kind=kind
        def __enter__(self):self.stream.__enter__();return self
        def __exit__(self,*args):return self.stream.__exit__(*args)
        def read(self,size=-1):
            reads.append((self.kind,size));assert 0<=size<=self.maximum,'Unnecessary oversized '+self.kind+' read request: '+str(size)
            return self.stream.read(size)
    def open_observed(file,*args,**kwargs):
        stream=real_open(file,*args,**kwargs)
        return File(stream,len(compressed)+1,'compressed') if file==path else stream
    def expand(*args,**kwargs):return File(real_gzip(*args,**kwargs),1024*1024,'expanded')
    monkeypatch.setattr(Path,'open',open_observed);monkeypatch.setattr(gzip,'GzipFile',expand)
    assert source._load(path,hashlib.sha256(compressed).hexdigest())=={'original':'complete'}
    assert reads and {kind for kind,_ in reads}=={'compressed','expanded'}
