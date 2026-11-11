"""Hold an idle-sleep lease only while the identified existing check remains alive."""
from pathlib import Path
import ctypes,json,os,sys,time
from verification_awake import awake
kernel=ctypes.windll.kernel32;kernel.OpenProcess.argtypes=[ctypes.c_uint,ctypes.c_bool,ctypes.c_uint];kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];kernel.WaitForSingleObject.restype=ctypes.c_uint
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
pid=int(sys.argv[1]);handle=kernel.OpenProcess(0x100000,False,pid)
if not handle:raise OSError('The explicitly identified running check is unavailable')
started=time.time();reason='check_exited'
try:
 with awake():
  deadline=time.monotonic()+7200
  while kernel.WaitForSingleObject(handle,1000)==258:
   if time.monotonic()>deadline:reason='two_hour_lease_limit';break
finally:
 kernel.CloseHandle(handle)
 value=dict(parent_check_pid=pid,scope=__doc__,started_utc_epoch=started,finished_utc_epoch=time.time(),release_reason=reason,power_plan_changed=False,thread_execution_state_restored=True)
 (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'temporary-wake-lease.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
