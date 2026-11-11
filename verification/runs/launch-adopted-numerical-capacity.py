"""Run the frozen real-data capacity sequence after both adopted-stage regressions."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


root = Path.cwd()
stage = root / "data/dev027/research-src"
checks = Path("verification/runs")
origin = Path("data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7/origin.json")
contract_path = checks / "capacity-real-sample-contract.json"
record = [sys.executable, "verification/record_check.py"]
OWNERSHIP_PROBE_CHANGES = {"PLAN.md", "VERIFICATION_PLAN.md", "tests/test_runtime_ownership.py"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def wait_for_receipts(ids, limit=2400):
    waiting = set(ids)
    found = {}
    deadline = time.monotonic() + limit
    print(json.dumps({"awaiting_terminal_receipts": list(ids)}), flush=True)
    while waiting:
        for identifier in list(waiting):
            path = Path("verification/receipts") / (identifier + ".json")
            try:
                receipt = load(path)
            except (FileNotFoundError, json.JSONDecodeError):
                continue
            assert receipt["receipt_id"] == identifier
            assert receipt["command"]["exit_code"] == 0, f"Regression failed: {identifier}"
            assert not any("Source changed during command" in n for n in receipt["notes"]), identifier
            artifacts = {a["path"]: a for a in receipt["artifacts"]}
            for name in ("research-stage-subject.json", "research-stage-junit.xml"):
                output = checks / identifier / name
                metadata = artifacts[output.as_posix()]
                content = output.read_bytes()
                assert len(content) == metadata["bytes"]
                assert hashlib.sha256(content).hexdigest() == metadata["sha256"]
            snapshot = load(checks / identifier / "research-stage-subject.json")
            assert snapshot["source_root"] == stage.relative_to(root).as_posix()
            assert snapshot["child_exit_code"] == 0 and snapshot["changed_during_check"] == []
            found[identifier] = path, snapshot["source_files"]
            waiting.remove(identifier)
            print(json.dumps({"terminal_execution_passed": identifier}), flush=True)
        if waiting:
            if time.monotonic() >= deadline:
                raise TimeoutError("No terminal receipt within the coordination wait for " + ", ".join(sorted(waiting)))
            time.sleep(5)
    return found


def run(args):
    result = subprocess.run(args, cwd=root)
    if result.returncode:
        raise SystemExit(result.returncode)


def matrix_evidence(identifier, numerical, core):
    path = Path("verification/receipts") / (identifier + ".json")
    receipt = load(path)
    assert receipt["receipt_id"] == identifier and receipt["command"]["exit_code"] == 0
    assert not any("Source changed during command" in note for note in receipt["notes"])
    inputs = {row["path"]: row["sha256"] for row in receipt["subject"]["input_manifests"]}
    assert inputs[numerical.as_posix()] == hashlib.sha256(numerical.read_bytes()).hexdigest()
    fixture = stage / "verification/fixtures/strategy-baselines.json"
    assert inputs[fixture.relative_to(root).as_posix()] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    output = checks / identifier / "strategy-matrix-reconciliation.json"
    entry = next(row for row in receipt["artifacts"] if row["path"] == output.as_posix())
    raw = output.read_bytes()
    assert len(raw) == entry["bytes"] and hashlib.sha256(raw).hexdigest() == entry["sha256"]
    result = json.loads(raw)
    assert result["core_sha256"] == core and result["execution_receipt"] == numerical.as_posix()
    assert result["reconciled_case_count"] == len({row["case_id"] for row in result["cases"]}) == 120
    return path


def main():
    numerical_id, matrix_id, publication_id, core = sys.argv[1:]
    assert all(identifier and Path(identifier).name == identifier for identifier in (numerical_id, matrix_id, publication_id))
    numerical, before = wait_for_receipts((numerical_id,))[numerical_id]
    matrix = matrix_evidence(matrix_id, numerical, core)
    publication, publication_before = wait_for_receipts((publication_id,))[publication_id]
    differences = {name for name in before.keys() | publication_before.keys()
                   if before.get(name) != publication_before.get(name)}
    assert differences <= OWNERSHIP_PROBE_CHANGES, f"Unexpected source differences: {sorted(differences)}"
    print(json.dumps({"retained_matrix_receipt": matrix_id, "test_or_plan_differences": sorted(differences)}), flush=True)
    contract = load(contract_path)
    assert contract["counts"] == [100, 1000, 10000]
    this = checks / Path(__file__).name
    runner = checks / "measure-fresh-market-capacity-current-stage.py"
    stage_check = checks / "check-research-command-stage.py"
    for count in contract["counts"]:
        assert all(hashlib.sha256((stage / name).read_bytes()).hexdigest() == digest
                   for name, digest in publication_before.items()), "Stage changed after publication regression."
        current = subprocess.check_output(
            [sys.executable, "-c", "from backend.lab.research import core_hash; print(core_hash())"],
            cwd=stage, text=True,
        ).strip()
        assert current == core, "Stage source changed before the capacity run."
        run(record + ["--label", f"adopted-numerical-real-market-{count}-capacity",
                      "--input", str(this), "--input", str(runner), "--input", str(stage_check),
                      "--input", str(contract_path), "--input", str(origin),
                      "--input", str(numerical), "--input", str(matrix), "--input", str(publication),
                      "--", sys.executable, str(stage_check), sys.executable, str(runner),
                      origin.as_posix(), str(count)])


if __name__ == "__main__":
    main()
