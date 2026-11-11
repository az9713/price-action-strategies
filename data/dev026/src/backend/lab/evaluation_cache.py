"""Bounded job-local verified inputs/base candles; never memoize strategy outcomes."""
from collections import OrderedDict
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from threading import get_ident
import hashlib
from .config import canonical
from .data import aggregate,DataError

_active=ContextVar('price_action_evaluation_cache',default=None)
DEFAULT_BYTES=128*1024*1024
CHUNK=65536

class EvaluationCache:
    def __init__(self,root,max_bytes=DEFAULT_BYTES,cancel=None):
        if type(max_bytes) is not int or max_bytes<0:raise ValueError('Cache bytes must be a nonnegative integer.')
        self.root=Path(root).resolve();self.owner_thread=get_ident();self.max_bytes=max_bytes;self.cancel=cancel
        self.entries=OrderedDict();self.cache_bytes=0;self.current_frame=None;self.current_key=None

    def check_cancel(self):
        if self.cancel and self.cancel():raise InterruptedError('Evaluation cache work canceled.')

    def verify(self,path,expected):
        self.check_cancel();digest=hashlib.sha256()
        try:
            with Path(path).open('rb') as stream:
                ordinal=0
                while chunk:=stream.read(CHUNK):
                    digest.update(chunk);ordinal+=1
                    if ordinal%1024==0:self.check_cancel()
        except InterruptedError:raise
        except OSError as error:raise DataError('Dataset source file is unavailable.') from error
        if digest.hexdigest()!=expected:raise DataError('Dataset file hash mismatch.')
        self.check_cancel()

    def get(self,key):
        value=self.entries.get(key)
        if value is not None:self.entries.move_to_end(key);return value[0]
        return None

    def put(self,key,value,size):
        if not self.max_bytes or size>self.max_bytes:return False
        while self.cache_bytes+size>self.max_bytes:
            _,(_,old_size)=self.entries.popitem(last=False);self.cache_bytes-=old_size
        self.entries[key]=(value,size);self.cache_bytes+=size;return True

    def prepared(self,key,path,expected,load):
        # Recheck every source byte even on a hit, after the caller's live access
        # guard. Current working frames are separate from retained-cache accounting.
        self.verify(path,expected);cached=self.get(('prepared',key))
        if cached is None:
            regular,actions=load()
            size=int(regular.memory_usage(index=True,deep=True).sum())+2048
            size+=len(canonical([a.__dict__ for a in actions]).encode())+len(actions)*1024
            retained=self.put(('prepared',key),(regular,actions),size)
        else:regular,actions=cached;retained=True
        self.current_frame=regular;self.current_key=key if retained else None
        return regular,actions

    def provider(self,regular):
        if self.current_frame is not regular or self.current_key is None:return None
        snapshot=self.current_key
        def chart(symbol,timeframe):
            self.check_cancel();key=('chart',snapshot,symbol,timeframe);value=self.get(key)
            if value is None:
                group=regular[regular.symbol==symbol]
                if group.empty:raise DataError('Unknown verified snapshot instrument.')
                value=aggregate(group,timeframe)
                self.put(key,value,int(value.memory_usage(index=True,deep=True).sum())+2048)
            return value
        return chart

    def clear(self):
        self.entries.clear();self.cache_bytes=0;self.current_frame=None;self.current_key=None

def current_cache(root):
    cache=_active.get()
    return cache if cache is not None and cache.owner_thread==get_ident() and cache.root==Path(root).resolve() else None

@contextmanager
def evaluation_cache(root,max_bytes=DEFAULT_BYTES,cancel=None):
    cache=EvaluationCache(root,max_bytes,cancel);token=_active.set(cache)
    try:yield cache
    finally:
        cache.clear();_active.reset(token)
