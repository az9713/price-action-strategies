"""Run a death probe with a native process handle and separate phase deadlines."""
from contextlib import redirect_stderr, redirect_stdout
import json
import multiprocessing
from pathlib import Path
import runpy
import subprocess
import sys
import time
import traceback


def _execute(script, arguments, stdout_path, stderr_path):
    with open(stdout_path, "w", encoding="utf-8") as stdout, open(stderr_path, "w", encoding="utf-8") as stderr:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            sys.argv = [script, *arguments]
            try:
                runpy.run_path(script, run_name="__main__")
            except BaseException:
                traceback.print_exc(file=stderr)
                raise


def run_probe(script, arguments, ready_path, *, startup_seconds=120, boundary_seconds=90):
    script, ready_path = Path(script).resolve(), Path(ready_path).resolve()
    assert not ready_path.exists()
    stdout_path = ready_path.with_suffix(".stdout.log")
    stderr_path = ready_path.with_suffix(".stderr.log")
    command = [str(script), *map(str, arguments)]
    process = multiprocessing.get_context("spawn").Process(
        target=_execute, args=(str(script), list(map(str, arguments)), str(stdout_path), str(stderr_path)),
    )
    started = time.monotonic()
    process.start()
    pid = process.pid
    phase = "startup"
    limit = started + startup_seconds
    startup = None
    timed_out = False
    try:
        while process.is_alive():
            if phase == "startup" and ready_path.exists():
                ready = json.loads(ready_path.read_text(encoding="utf-8"))
                assert ready["pid"] == pid, "Ready marker belongs to another probe process."
                startup = time.monotonic() - started
                phase = "crash boundary"
                limit = time.monotonic() + boundary_seconds
            if time.monotonic() >= limit:
                timed_out = True
                break
            process.join(timeout=.05)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
        assert not process.is_alive(), "Owned probe process did not exit after termination."
        process.join()
        exit_code = process.exitcode
        process.close()
    stdout = stdout_path.read_bytes() if stdout_path.exists() else b""
    stderr = stderr_path.read_bytes() if stderr_path.exists() else b""
    observation = dict(
        pid=pid, startup_seconds=startup, elapsed_seconds=time.monotonic()-started,
        phase=phase, exit_code=exit_code, timed_out=timed_out, actual_process_exited=True,
    )
    ready_path.with_suffix(".controller.json").write_text(json.dumps(observation, indent=2)+"\n", encoding="utf-8")
    if timed_out:
        raise subprocess.TimeoutExpired(command, startup_seconds if phase == "startup" else boundary_seconds,
                                        output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(command, exit_code, stdout, stderr)
