"""A forced parent death must not leave a numerical queue consumer behind."""
import ctypes
import multiprocessing
import os
import time

import pytest


def parent_with_worker(root,announcements):
    from backend.lab.worker import run_worker
    context=multiprocessing.get_context('spawn')
    stop=context.Event();ready=context.Event()
    worker=context.Process(target=run_worker,args=(root,stop,ready),daemon=True)
    worker.start()
    announcements.put({'worker_pid':worker.pid,'parent_pid':os.getpid()})
    announcements.put({'ready':ready.wait(60)})
    # The test terminates this process abruptly. Python's normal daemon cleanup
    # and API lifespan shutdown therefore cannot supply the expected outcome.
    while True: time.sleep(1)


@pytest.mark.skipif(os.name!='nt',reason='Actual forced-parent-death gate for the supported Windows host.')
def test_worker_stops_after_actual_forced_parent_death(tmp_path,record_property):
    from ctypes import wintypes as W
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];kernel.WaitForSingleObject.restype=W.DWORD
    kernel.TerminateProcess.argtypes=[W.HANDLE,W.UINT];kernel.CloseHandle.argtypes=[W.HANDLE]
    context=multiprocessing.get_context('spawn');messages=context.Queue()
    parent=context.Process(target=parent_with_worker,args=(str(tmp_path),messages))
    handle=None
    try:
        parent.start();identity=messages.get(timeout=60)
        assert identity['parent_pid']==parent.pid
        # Keep a handle to this exact owned process, avoiding PID-reuse races.
        handle=kernel.OpenProcess(0x00100000|0x1000|0x0001,False,identity['worker_pid'])
        assert handle,ctypes.get_last_error()
        assert messages.get(timeout=60)['ready']
        assert kernel.WaitForSingleObject(handle,0)==258 # WAIT_TIMEOUT: alive
        begun=time.monotonic();parent.terminate();parent.join(5)
        assert not parent.is_alive()
        assert kernel.WaitForSingleObject(handle,10000)==0, 'Worker survived its actual parent termination.'
        record_property('forced_parent_death_to_worker_exit_seconds',time.monotonic()-begun)
    finally:
        if parent.is_alive(): parent.terminate();parent.join(5)
        if handle:
            if kernel.WaitForSingleObject(handle,0)==258:
                kernel.TerminateProcess(handle,1);kernel.WaitForSingleObject(handle,3000)
            kernel.CloseHandle(handle)
        messages.close();messages.join_thread()
