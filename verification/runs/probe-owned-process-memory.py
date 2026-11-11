"""Verify Windows native RSS/high-water measurement on this owned process with a known touched allocation."""
from pathlib import Path
import ctypes,ctypes.wintypes as w,json,os
class Counters(ctypes.Structure):
 _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD),*[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]]
kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True);kernel.GetCurrentProcess.restype=w.HANDLE
read=psapi.GetProcessMemoryInfo;read.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD];read.restype=w.BOOL
handle=kernel.GetCurrentProcess()
def measure():
 value=Counters();value.cb=ctypes.sizeof(value)
 if not read(handle,ctypes.byref(value),value.cb):raise ctypes.WinError(ctypes.get_last_error())
 return dict(working_set_bytes=value.WorkingSetSize,peak_working_set_bytes=value.PeakWorkingSetSize,private_bytes=value.PrivateUsage)
before=measure();allocation=bytearray(64*1024*1024)
for i in range(0,len(allocation),4096):allocation[i]=1
after=measure();assert after['working_set_bytes']-before['working_set_bytes']>=48*1024*1024 and after['peak_working_set_bytes']>=after['working_set_bytes']
value=dict(scope=__doc__,pid=os.getpid(),known_touched_bytes=len(allocation),before=before,after=after,working_set_growth=after['working_set_bytes']-before['working_set_bytes'],other_process_inventory_certified=False)
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'owned-memory-probe.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
