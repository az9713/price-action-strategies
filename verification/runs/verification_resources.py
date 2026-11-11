"""Observed current-process Windows memory; no resource limit is inferred."""
import ctypes
from ctypes import wintypes
import os,time


def current_resources():
    value=dict(process_cpu_seconds=time.process_time())
    if os.name!='nt':return value|dict(memory_available=False)
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),
            *[(name,ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage']]]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);psapi=ctypes.WinDLL('psapi',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype=wintypes.BOOL
    measured=Counters();measured.cb=ctypes.sizeof(measured)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(measured),measured.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return value|dict(memory_available=True,working_set_bytes=measured.WorkingSetSize,
        peak_working_set_bytes=measured.PeakWorkingSetSize,private_bytes=measured.PrivateUsage)
