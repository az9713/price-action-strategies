"""Reconcile the 120 authored strategy cases with a recorded current-stage pytest run."""
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from xml.etree import ElementTree


root = Path.cwd().resolve()
stage = root / "data/dev027/research-src"
receipts = root / "verification/receipts"
runs = root / "verification/runs"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def attest_case(case, evidence, fixture, fixture_hash, expected_core):
    family, clock, direction = (case[key] for key in ("family", "timeframe", "direction"))
    configuration, signal, trade, geometry = (
        evidence[key] for key in ("config", "signal", "matched_trade", "geometry")
    )
    authored = fixture["families"][family]
    side = {"long": 1, "short": -1}[direction]
    level = Decimal(str(authored["level"]))
    if side != authored["base_side"]:
        level = Decimal(str(fixture["mirror_about"])) - level
    assert evidence["case_id"] == case["id"]
    assert evidence["input_kind"] == "synthetic_fixture"
    assert evidence["core_hash"] == expected_core
    assert evidence["fixture_sha256"] == fixture_hash
    assert type(evidence["minute_rows"]) is int and evidence["minute_rows"] > 0
    assert re.fullmatch("[a-f0-9]{64}", evidence["minute_sha256"])
    assert (configuration["family"], configuration["timeframe"], configuration["direction"]) == (family, clock, direction)
    assert (trade["family"], trade["timeframe"]) == (family, clock)
    assert all(configuration[key] == value for key, value in fixture["config"].items())
    assert signal["id"] == trade["id"] and signal["symbol"] == trade["symbol"]
    assert signal["side"] == geometry["side"] == trade["side"] == side
    assert signal["source_index"] == geometry["index"] == authored["candidate_index"]
    assert geometry["reason"] == authored["independent_reason"]
    assert Decimal(str(geometry["level"])) == level
    assert math.isclose(signal["level"], float(level), rel_tol=0, abs_tol=1e-8)
    assert signal["available_at"] == geometry["available_at"] == trade["signal_at"]
    assert datetime.fromisoformat(trade["signal_at"]) <= datetime.fromisoformat(trade["entry_at"])
    assert datetime.fromisoformat(trade["entry_at"]) <= datetime.fromisoformat(trade["exit_at"])
    assert evidence["execution_start"] == geometry["start"] <= geometry["end"] == evidence["execution_end"]
    assert evidence["signal_count"] > 0 and evidence["trade_count"] > 0
    assert evidence["negative_signal_count"] == 0
    assert evidence["reference_parity"] is True and evidence["prefix_invariance"] is True
    return {
        "case_id": case["id"],
        "requirement_id": case["requirement_id"],
        "expected": case["expected"],
        "observed": {
            "signal": signal,
            "matched_trade": trade,
            "negative_signal_count": evidence["negative_signal_count"],
            "execution_reference_parity_assertion": evidence["reference_parity"],
            "prefix_invariance_assertion": evidence["prefix_invariance"],
        },
    }


def main():
    receipt_id, expected_core = sys.argv[1:]
    assert re.fullmatch("[a-zA-Z0-9-]+", receipt_id)
    assert re.fullmatch("[a-f0-9]{64}", expected_core)
    receipt_path = receipts / (receipt_id + ".json")
    receipt = read(receipt_path)
    assert receipt["receipt_id"] == receipt_id and receipt["command"]["exit_code"] == 0
    assert not any("Source changed during command" in note for note in receipt["notes"])
    run = runs / receipt_id
    manifest = {entry["path"]: entry for entry in receipt["artifacts"]}
    assert len(manifest) == len(receipt["artifacts"])

    def verified_artifact(relative):
        path = run / relative
        entry = manifest[path.relative_to(root).as_posix()]
        assert path.stat().st_size == entry["bytes"] and sha(path) == entry["sha256"], relative
        return path

    recorded_stage = read(verified_artifact("research-stage-subject.json"))
    assert recorded_stage["source_root"] == stage.relative_to(root).as_posix()
    assert recorded_stage["child_exit_code"] == 0 and recorded_stage["changed_during_check"] == []
    for name, expected in recorded_stage["source_files"].items():
        path = (stage / name).resolve()
        assert path.is_relative_to(stage) and sha(path) == expected, name

    fixture_path = stage / "verification/fixtures/strategy-baselines.json"
    fixture_hash = sha(fixture_path)
    fixture = read(fixture_path)
    catalog_path = root / "verification/catalog.json"
    assert sha(catalog_path) == receipt["subject"]["catalog_sha256"]
    cases = {c["id"]: c for c in read(catalog_path)["cases"] if c["id"].startswith("MATRIX-")}
    assert len(cases) == 120 and all(case["mandatory"] for case in cases.values())
    xml_path = verified_artifact("research-stage-junit.xml")
    xml = ElementTree.parse(xml_path)
    observed = {}
    for result in xml.iter("testcase"):
        match = re.fullmatch(r"test_full_baseline_strategy_matrix\[(MATRIX-[^\]]+)\]", result.get("name", ""))
        if match:
            case_id = match.group(1)
            assert case_id not in observed and result.get("classname", "").endswith("test_strategy_matrix")
            assert not any(child.tag in {"failure", "error", "skipped"} for child in result)
            observed[case_id] = result
    assert observed.keys() == cases.keys()
    assert {p.stem for p in (run / "strategy-matrix").glob("*.json")} == cases.keys()

    rows = []
    for case_id, case in sorted(cases.items()):
        artifact = verified_artifact("strategy-matrix/" + case_id + ".json")
        row = attest_case(case, read(artifact), fixture, fixture_hash, expected_core)
        row.update(test_id=observed[case_id].get("name"), artifact=artifact.relative_to(root).as_posix(), artifact_sha256=sha(artifact))
        rows.append(row)
    result = {
        "scope": "Current-stage 120-case matrix evidence reconciliation. Final acceptance requires the frozen release subject and remaining cases.",
        "core_sha256": expected_core,
        "fixture_sha256": fixture_hash,
        "execution_receipt": receipt_path.relative_to(root).as_posix(),
        "junit": xml_path.relative_to(root).as_posix(),
        "reconciled_case_count": len(rows),
        "cases": rows,
    }
    out = Path(os.environ["PA_EVIDENCE_RUN_DIR"]) / "strategy-matrix-reconciliation.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Reconciled {len(rows)} current-stage cases with JUnit, authored geometry, and receipt artifacts.")


if __name__ == "__main__":
    main()
