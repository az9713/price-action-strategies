"""Reconcile completed probe timing records with the actual six-case JUnit receipt."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from xml.etree import ElementTree


root = Path.cwd().resolve()
run_id, pytest_directory = sys.argv[1:]
assert re.fullmatch("[a-zA-Z0-9-]+", run_id) and re.fullmatch("pytest-[0-9]+", pytest_directory)
receipt_path = root / "verification/receipts" / (run_id + ".json")
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
assert receipt["command"]["exit_code"] == 0
run = root / "verification/runs" / run_id
junit_path = run / "research-stage-junit.xml"
entry = next(item for item in receipt["artifacts"] if item["path"] == junit_path.relative_to(root).as_posix())
assert hashlib.sha256(junit_path.read_bytes()).hexdigest() == entry["sha256"]
cases = list(ElementTree.parse(junit_path).iter("testcase"))
assert len(cases) == 6 and not any(child.tag in {"failure", "error", "skipped"} for case in cases for child in case)
started = datetime.fromisoformat(receipt["started_at_utc"]).timestamp()
finished = datetime.fromisoformat(receipt["finished_at_utc"]).timestamp()
folder = Path(tempfile.gettempdir()) / "pytest-of-user" / pytest_directory
boundaries = ["after_first_checkpoint", "after_second_checkpoint", "after_part_receipt", "inside_root_transaction", "after_root_commit"]
observations = []
for index, boundary in enumerate(boundaries):
    name = f"test_actual_arm_death_reuses_o{index}"
    controller = folder / name / "actual-death-ready.controller.json"
    marker = folder / name / "actual-death.json"
    assert started <= controller.stat().st_mtime <= finished
    assert started <= marker.stat().st_mtime <= finished
    value = json.loads(controller.read_text(encoding="utf-8"))
    death = json.loads(marker.read_text(encoding="utf-8"))
    assert value["actual_process_exited"] and not value["timed_out"]
    assert 0 <= value["startup_seconds"] <= 120
    assert 0 <= value["elapsed_seconds"] - value["startup_seconds"] <= 90
    assert value["exit_code"] == death["exit_code"] == 111 + index
    assert death["boundary"] == boundary
    observations.append(dict(boundary=boundary, **value, original_death_marker=death))
timeout = folder / "test_actual_timeout_joins_the_0/waiting-ready.controller.json"
value = json.loads(timeout.read_text(encoding="utf-8"))
assert started <= timeout.stat().st_mtime <= finished
assert value["timed_out"] and value["actual_process_exited"] and value["phase"] == "crash boundary"
observations.append(dict(boundary="deliberate_timeout", **value))
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
(out / "owned-arm-death-phase-times.json").write_text(json.dumps({
    "execution_receipt": receipt_path.relative_to(root).as_posix(),
    "executed_cases": 6, "observations": observations,
    "all_actual_processes_exited": True,
}, indent=2) + "\n", encoding="utf-8")
print("Reconciled five actual exit boundaries and one owned timeout with the six-case execution receipt.")
