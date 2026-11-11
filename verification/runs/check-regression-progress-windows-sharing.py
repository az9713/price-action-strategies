"""Verify that a real Windows status-file reader cannot abort pytest."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from xml.etree import ElementTree


root = Path.cwd().resolve()
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"]).resolve()
assert os.name == "nt"
with tempfile.TemporaryDirectory(prefix="price-action-progress-") as folder:
    owned = Path(folder)
    fixture = owned / "test_locked_progress.py"
    fixture.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "held = None\n\n"
        "def test_hold_status_file_open():\n"
        "    global held\n"
        "    path = Path(os.environ['PA_EVIDENCE_RUN_DIR']) / 'full-regression-progress.json'\n"
        "    held = path.open('rb')\n"
        "    assert held.read(1) == b'{'\n\n"
        "def test_release_reader():\n"
        "    assert held is not None and not held.closed\n"
        "    held.close()\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        PA_EVIDENCE_RUN_DIR=str(owned),
        PYTHONPATH=str(root / "verification/runs"),
        PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
        PYTHONNOUSERSITE="1",
    )
    junit = owned / "reader-lock-junit.xml"
    result = subprocess.run([
        sys.executable, "-m", "pytest", "-q", "-p", "research_regression_progress",
        str(fixture), "--junitxml", str(junit),
    ], cwd=owned, env=environment)
    assert result.returncode == 0
    tests = list(ElementTree.parse(junit).iter("testcase"))
    assert len(tests) == 2 and all(len(test) == 0 for test in tests)
    status = json.loads((owned / "full-regression-progress.json").read_text(encoding="utf-8"))
    assert status["terminal"] and status["exit_code"] == 0
    assert status["passed"] == status["reported"] == 2
    assert status["prior_progress_publication_failures"] == 1
    (out / "windows-reader-lock-progress.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8",
    )
