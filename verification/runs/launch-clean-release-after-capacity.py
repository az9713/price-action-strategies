"""Start the fresh locked build and complete backend suite after the original capacity gate."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


root = Path.cwd().resolve()
identifier, core = sys.argv[1:]
assert re.fullmatch("[A-Za-z0-9-]+", identifier) and re.fullmatch("[a-f0-9]{64}", core)
receipt_path = root / "verification/receipts" / (identifier + ".json")
deadline = time.monotonic() + 1800
print(json.dumps({"awaiting_capacity_receipt": identifier}), flush=True)
while True:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        break
    except (FileNotFoundError, json.JSONDecodeError):
        if time.monotonic() >= deadline:
            raise TimeoutError("Capacity receipt is still unavailable. Preserve its active handle.")
        time.sleep(5)
assert receipt["receipt_id"] == identifier and receipt["command"]["exit_code"] == 0
assert not any("Source changed during command" in note for note in receipt["notes"])
manifest = {item["path"]: item for item in receipt["artifacts"]}
run = root / "verification/runs" / identifier


def verified(name):
    path = run / name
    record = manifest[path.relative_to(root).as_posix()]
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record["sha256"] and len(raw) == record["bytes"]
    return json.loads(raw)


capacity = verified("capacity-summary.json")
assert capacity["count"] == 10000 and capacity["core_hash"] == core
assert len(capacity["measurements"]) == 1
measurement = capacity["measurements"][0]
assert measurement["trial_attempts"] == measurement["count"] == 10000
assert measurement["worker_complete_seconds"] <= 900
assert measurement["resources"]["peak_working_set_bytes"] <= 3 * 1024**3
assert measurement["job_output_bytes"] <= 2 * 1024**3
subject = verified("research-stage-subject.json")
assert subject["child_exit_code"] == 0 and subject["changed_during_check"] == []
stage = root / subject["source_root"]
assert stage == root / "data/dev027/research-src"
for name, digest in subject["source_files"].items():
    path = (stage / name).resolve()
    assert path.is_relative_to(stage) and hashlib.sha256(path.read_bytes()).hexdigest() == digest
print("The original 10,000 capacity gate passed. Starting fresh installation and full backend verification.", flush=True)
inputs = [
    "verification/runs/verify-research-stage-locked-build.py",
    "verification/runs/clean-reproduction-offline-scenario.py",
    "verification/runs/launch-research-complete-regression.py",
    "verification/runs/launch-clean-release-after-capacity.py",
    "verification/runs/check-research-command-stage.py",
]
command = [sys.executable, "verification/record_check.py",
           "--label", "context-cache-fresh-locked-build-offline-and-complete-backend-suite",
           "--input", receipt_path.relative_to(root).as_posix()]
for path in inputs:
    command.extend(["--input", path])
command.extend([
    "--", sys.executable, "verification/runs/check-research-command-stage.py",
    sys.executable, "verification/runs/verify-research-stage-locked-build.py", "--release-suite",
])
raise SystemExit(subprocess.run(command, cwd=root).returncode)
