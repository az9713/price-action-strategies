"""Process-scoped system-idle request for owned verification work only."""
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import ctypes,json,os,sys

@contextmanager
def verification_awake(out):
    record=dict(scope=__doc__,pid=os.getpid(),platform=sys.platform,requested=False,active=False,
        display_requested=False,away_mode_requested=False,persistent_power_plan_changed=False,
        manual_sleep_override=False,started_at_utc=datetime.now(timezone.utc).isoformat(),release_succeeded=None)
    api=None;previous=0
    if sys.platform=='win32':
        api=ctypes.WinDLL('kernel32',use_last_error=True).SetThreadExecutionState
        api.argtypes=[ctypes.c_uint];api.restype=ctypes.c_uint
        record['requested']=True;previous=api(0x80000001)
        record['active']=bool(previous)
        if not previous:record['acquire_error']=ctypes.get_last_error()
    path=Path(out)/'verification-power-request.json'
    path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    try:yield
    finally:
        if record['active']:
            record['release_succeeded']=bool(api(previous|0x80000000))
            if not record['release_succeeded']:record['release_error']=ctypes.get_last_error()
        record['active']=False;record['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(record,indent=2),encoding='utf-8')
