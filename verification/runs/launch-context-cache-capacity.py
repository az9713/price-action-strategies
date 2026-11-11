"""Reconcile the context-cache numerical run and execute the original capacity sequence."""
import json
from pathlib import Path
import runpy
import subprocess
import sys


root = Path.cwd()
numerical_id, core = sys.argv[1:]
launcher = root / "verification/runs/launch-adopted-numerical-capacity.py"
helpers = runpy.run_path(str(launcher))
numerical, _ = helpers["wait_for_receipts"]((numerical_id,))[numerical_id]
reconcile = root / "verification/runs/reconcile-strategy-matrix-evidence.py"
command = [
    sys.executable, "verification/record_check.py",
    "--label", "context-cache-120-matrix-case-evidence-reconciliation",
    "--input", numerical.as_posix(),
    "--input", reconcile.relative_to(root).as_posix(),
    "--input", "data/dev027/research-src/verification/fixtures/strategy-baselines.json",
    "--", sys.executable, str(reconcile), numerical_id, core,
]
result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8")
print(result.stdout, end="", flush=True)
if result.stderr:
    print(result.stderr, end="", file=sys.stderr, flush=True)
if result.returncode:
    raise SystemExit(result.returncode)
observed = json.loads(result.stdout.splitlines()[-1])
assert observed["exit_code"] == 0 and observed["coherent_subject"] and observed["requested_artifacts_present"]
matrix_id = Path(observed["receipt"]).stem
# The current numerical run includes real worker cache cleanup, guard, manifest,
# source and cancellation cases. The full release suite remains a separate gate.
raise SystemExit(subprocess.run([
    sys.executable, str(launcher), numerical_id, matrix_id, numerical_id, core,
], cwd=root).returncode)
