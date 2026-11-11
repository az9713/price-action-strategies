"""OS-owned single-server lease. Persistent file existence is never ownership."""
import os
from pathlib import Path


class RuntimeOwnershipError(RuntimeError):pass


class StoreLease:
    def __init__(self,root):
        self.path=Path(root).resolve()/'data'/'server.lock'
        self.handle=None

    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        handle=self.path.open('a+b')
        os.set_inheritable(handle.fileno(),False)
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise RuntimeOwnershipError('Another application instance already owns this store. Use the running app or stop it before restarting.') from None
        self.handle=handle
        return self

    def __exit__(self,*exc):
        handle=self.handle
        if handle is not None:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
            finally:
                handle.close();self.handle=None
