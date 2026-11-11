"""Real OS store ownership and spawned-process lifecycle; no stale PID authority."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import pytest
from fastapi.testclient import TestClient
from backend.lab.api import create_app


PROBE_STARTUP_SECONDS = 120


def test_same_resolved_store_rejects_second_owner_and_releases_after_error(tmp_path):
    from backend.lab.runtime import StoreLease,RuntimeOwnershipError
    with pytest.raises(ValueError,match='authored exit'):
        with StoreLease(tmp_path):
            with pytest.raises(RuntimeOwnershipError,match='already owns'):StoreLease(tmp_path/'.').__enter__()
            with StoreLease(tmp_path/'separate'):pass
            raise ValueError('authored exit')
    assert (tmp_path/'data/server.lock').exists()
    with StoreLease(tmp_path):pass


def test_actual_os_process_exit_releases_lease_without_deleting_stale_file(tmp_path):
    from backend.lab.runtime import StoreLease,RuntimeOwnershipError
    # Exit the actual interpreter without finally. On Windows the venv launcher
    # is another process, so terminating just Popen.pid would leave the owner.
    code="from pathlib import Path;from backend.lab.runtime import StoreLease;import sys,os;lease=StoreLease(Path(sys.argv[1]));lease.__enter__();print('LOCKED',flush=True);sys.stdin.readline();os._exit(17)"
    process=subprocess.Popen([sys.executable,'-u','-c',code,str(tmp_path)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        assert process.stdout.readline().strip()=='LOCKED'
        with pytest.raises(RuntimeOwnershipError):StoreLease(tmp_path).__enter__()
    finally:
        process.communicate('CRASH\n',timeout=10)
    assert process.returncode==17
    assert (tmp_path/'data/server.lock').exists()
    with StoreLease(tmp_path):pass


def test_live_api_rejects_second_worker_owner_and_can_restart(tmp_path):
    from backend.lab.runtime import RuntimeOwnershipError
    first=create_app(tmp_path,run_worker=True)
    with TestClient(first,base_url='http://localhost:8765',client=('127.0.0.1',51000)) as client:
        process=first.state.worker_process;assert process.is_alive()
        health=client.get('/api/health').json()
        assert health['server_pid']==os.getpid() and health['worker_pid']==process.pid and health['store_lease_held'] is True
        with pytest.raises(RuntimeOwnershipError,match='already owns'):
            with TestClient(create_app(tmp_path,run_worker=True)):pass
        assert process.is_alive()
    assert not process.is_alive()
    with TestClient(create_app(tmp_path,run_worker=True)) as client:assert client.app.state.worker_process.is_alive()
    assert not client.app.state.worker_process.is_alive()
    assert first.state.store_lease.handle is None


def test_lifespan_exception_still_stops_actual_spawned_worker(tmp_path):
    app=create_app(tmp_path,run_worker=True);captured=[]
    async def execute():
        with pytest.raises(ValueError,match='authored lifespan failure'):
            async with app.router.lifespan_context(app):
                captured.append(app.state.worker_process)
                assert captured[-1].is_alive()
                raise ValueError('authored lifespan failure')
    asyncio.run(execute());assert not captured[0].is_alive()
    from backend.lab.runtime import StoreLease
    with StoreLease(tmp_path):pass


def test_failed_worker_start_releases_store_ownership(tmp_path,monkeypatch):
    from backend.lab import api
    class BrokenProcess:
        def start(self):raise RuntimeError('authored spawn failure')
    context=api.multiprocessing.get_context('spawn')
    monkeypatch.setattr(context,'Process',lambda **kw:BrokenProcess())
    app=create_app(tmp_path,run_worker=True)
    async def execute():
        with pytest.raises(RuntimeError,match='authored spawn failure'):
            async with app.router.lifespan_context(app):raise AssertionError('must not start')
    asyncio.run(execute())
    from backend.lab.runtime import StoreLease
    with StoreLease(tmp_path):pass


def test_worker_entry_point_ignores_console_interrupt_and_restores_handler(tmp_path):
    code="""
from pathlib import Path
from threading import Event
import signal,sys
from backend.lab import worker
class Probe:
 def __init__(self,*a):pass
 def serve(self,stop):
  signal.raise_signal(signal.SIGINT)
  stop.set()
worker.Worker=Probe;worker.Lab=lambda root:None
before=signal.getsignal(signal.SIGINT)
worker.run_worker(Path(sys.argv[1]),Event())
assert signal.getsignal(signal.SIGINT)==before
print('INTERRUPT_IGNORED_AND_HANDLER_RESTORED')
"""
    result=subprocess.run(
        [sys.executable, '-c', code, str(tmp_path)],
        capture_output=True, text=True, timeout=PROBE_STARTUP_SECONDS,
    )
    assert result.returncode==0 and result.stdout.strip()=='INTERRUPT_IGNORED_AND_HANDLER_RESTORED',result.stderr


def test_actual_parent_crash_releases_lease_and_spawned_worker_exits(tmp_path):
    # Keep a handle to the precise child object before crashing its parent;
    # completion is not inferred from a stale PID or a briefly closed port.
    assert os.name=='nt','This required runtime target is Windows.'
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];kernel.TerminateProcess.restype=wintypes.BOOL
    kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
    code="""
import multiprocessing,os,sys,json
from pathlib import Path
from backend.lab.runtime import StoreLease
from backend.lab.worker import run_worker
if __name__=='__main__':
 with StoreLease(Path(sys.argv[1])):
  context=multiprocessing.get_context('spawn');stop=context.Event();ready=context.Event()
  child=context.Process(target=run_worker,args=(sys.argv[1],stop,ready),daemon=True);child.start()
  assert ready.wait(int(sys.argv[2])), 'Spawned worker did not signal readiness'
  print(json.dumps({'worker_pid':child.pid}),flush=True)
  sys.stdin.readline();os._exit(17)
"""
    args = [sys.executable, '-u', '-c', code, str(tmp_path), str(PROBE_STARTUP_SECONDS)]
    with subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ) as process:
        handle=None
        try:
            line = process.stdout.readline()
            if not line:
                _, stderr = process.communicate(timeout=10)
                pytest.fail(f'Crash probe exited before worker readiness ({process.returncode}): {stderr}')
            pid=json.loads(line)['worker_pid'];handle=kernel.OpenProcess(0x00100001,False,pid);assert handle
            assert kernel.WaitForSingleObject(handle,0)==258
            process.communicate('CRASH\n',timeout=10);assert process.returncode==17
            assert kernel.WaitForSingleObject(handle,15000)==0,'Worker survived its actual parent crash'
            from backend.lab.runtime import StoreLease
            with StoreLease(tmp_path):pass
        finally:
            if process.poll() is None:process.communicate('CRASH\n',timeout=10)
            if handle:
                if kernel.WaitForSingleObject(handle,0)==258:kernel.TerminateProcess(handle,1);kernel.WaitForSingleObject(handle,5000)
                kernel.CloseHandle(handle)
