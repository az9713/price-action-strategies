"""Actual timeout of an owned interpreter must leave its native process exited."""
import json
from pathlib import Path
import subprocess

import pytest

from owned_death_probe import run_probe


def test_actual_timeout_joins_the_precise_probe_process(tmp_path):
    script = tmp_path / "authored_waiting_probe.py"
    script.write_text(
        "import json,os,sys,time\n"
        "from pathlib import Path\n"
        "ready=Path(sys.argv[1])\n"
        "temporary=ready.with_suffix('.tmp')\n"
        "temporary.write_text(json.dumps({'pid':os.getpid()}),encoding='utf-8')\n"
        "temporary.replace(ready)\n"
        "while True: time.sleep(.05)\n",
        encoding="utf-8",
    )
    ready = tmp_path / "waiting-ready.json"
    with pytest.raises(subprocess.TimeoutExpired):
        run_probe(script, [str(ready)], ready, boundary_seconds=.15)
    observation = json.loads(ready.with_suffix(".controller.json").read_text(encoding="utf-8"))
    assert observation["phase"] == "crash boundary" and observation["timed_out"]
    assert observation["startup_seconds"] is not None and observation["actual_process_exited"]
    assert observation["pid"] == json.loads(ready.read_text(encoding="utf-8"))["pid"]
