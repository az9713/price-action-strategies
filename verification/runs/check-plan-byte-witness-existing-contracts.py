"""Run the existing original-plan integrity contracts against the isolated candidate."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest
import backend.lab
from backend.lab import store


root = Path.cwd().resolve()
candidate = root / "data/dev027/plan-byte-witness-candidate/trials.py"
receipt = root / "verification/receipts/20261111T010815617942Z-compare-byte-witness-candidate-full-original-plan-checks.json"
proof = json.loads(receipt.read_text(encoding="utf-8"))
assert proof["command"]["exit_code"] == 0
entry = next(item for item in proof["subject"]["input_manifests"] if item["path"] == candidate.relative_to(root).as_posix())
digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
assert digest == entry["sha256"]
original = store.TrialLedger
spec = importlib.util.spec_from_file_location("backend.lab.trials", candidate)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
backend.lab.trials = module
store.TrialLedger = module.TrialLedger
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
sys.path.insert(0, str(root / "data/dev027/research-src/tests"))
try:
    code = pytest.main([
        "-q", "-c", str(root / "data/dev027/research-src/pyproject.toml"),
        str(root / "verification/runs/plan-projection-integrity-contracts.py"),
        "--import-mode=importlib", "--junitxml=" + str(out / "candidate-plan-integrity-junit.xml"),
        "-W", "error::ResourceWarning",
        "-W", "error::pytest.PytestUnraisableExceptionWarning",
        "-W", "error::pytest.PytestUnhandledThreadExceptionWarning",
    ])
    (out / "candidate-injection-subject.json").write_text(json.dumps({
        "scope": "Original integrity assertions executed with the hash-bound candidate in an isolated process.",
        "candidate_path": candidate.relative_to(root).as_posix(), "candidate_sha256": digest,
        "runtime_ledger_source": Path(module.__file__).relative_to(root).as_posix(), "pytest_exit_code": int(code),
        "production_files_edited": False,
    }, indent=2) + "\n", encoding="utf-8")
finally:
    store.TrialLedger = original
raise SystemExit(int(code))
