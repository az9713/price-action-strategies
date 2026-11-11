"""Execute and reconcile the bounded synthetic financial stress on the production worker."""
import argparse
import gzip
import hashlib
import inspect
import json
import os
from pathlib import Path
from time import perf_counter

import pandas as pd

from backend.lab.data import save_dataset, schedule
from backend.lab.models import Search
from backend.lab.research import core_hash, require_current_source
from backend.lab.service import Lab
from backend.lab.worker import Worker
from verification_resources import current_resources


ROOT = Path.cwd().resolve()
STAGE = ROOT / "data/dev027/research-src"
CONTRACT_PATH = ROOT / "verification/runs/bounded-financial-stress-contract.json"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def dataset(lab, spec):
    fixture_path = STAGE / spec["baseline_fixture"]
    fixture = read(fixture_path)
    closes = fixture["common_closes"]
    session = spec["session"]
    opened, closed = schedule(session, session)[session]
    timestamps = pd.date_range(opened, closed, freq="min", inclusive="left")
    assert len(timestamps) == spec["regular_minute_rows"]
    values = [float(spec["base_price"])] * len(timestamps)
    intervals = sorted(
        [(start, closes) for start in spec["positive_start_minutes"]]
        + [(start, [fixture["mirror_about"] - close for close in closes])
           for start in spec["mirrored_start_minutes"]]
    )
    previous_end = 0
    for start, sequence in intervals:
        end = start + len(sequence)
        assert previous_end <= start < end <= len(values)
        values[start:end] = sequence
        previous_end = end
    frame = pd.DataFrame({
        "symbol": spec["symbol"], "timestamp": timestamps,
        "open": [x - .02 for x in values], "high": [x + .1 for x in values],
        "low": [x - .1 for x in values], "close": values, "volume": 10_000,
    })
    manifest = save_dataset(lab.datasets_root, frame, {
        "input_kind": spec["input_kind"],
        "source": "Bounded synthetic stress using prespecified positive and mirrored price paths",
        "authored_fixture_sha256": sha(fixture_path.read_bytes()),
        "stress_contract_sha256": sha(CONTRACT_PATH.read_bytes()),
    }, start=session, end=session)
    quality = manifest["quality"]
    assert quality["eligible"] and quality["regular_rows"] == len(timestamps)
    assert quality["symbols"] == [spec["symbol"]] and quality["start"] == quality["end"] == session
    return manifest


def audit(lab, jid, manifest, configuration_ids, payload_hash, subject, out):
    count = len(configuration_ids)
    directory = lab.root / "data/jobs" / jid
    root_bytes = (directory / "result.json.gz").read_bytes()
    root_hash = sha(root_bytes)
    result = json.loads(gzip.decompress(root_bytes))
    assert result["job_id"] == jid and result["payload_hash"] == payload_hash
    assert result["core_hash"] == subject and result["dataset_manifest_hash"] == identity(manifest)
    assert result["count"] == len(result["rows"]) == result["sampling"]["unique"] == count
    summary = lab.result_index.summary(jid)
    assert summary["index_integrity"] is True and summary["row_count"] == count
    assert summary["root_sha256"] == root_hash
    last = lab.result_index.rows(jid, limit=1, offset=count - 1)
    assert last["index_integrity"] is True and last["pagination"]["total"] == count
    assert last["root_sha256"] == root_hash and last["rows"] == result["rows"][-1:]
    manifest_file = out / "bounded-stress-original-parts.partial"
    accounts_with_trades = trades = signals = 0
    output_digest = hashlib.sha256()
    with lab.store.db() as db, manifest_file.open("wb") as stream:
        db.execute("BEGIN")
        events = db.execute(
            "SELECT kind,details FROM events WHERE entity_id=? AND kind IN ('result_saved','job_completed') ORDER BY id",
            (jid,),
        ).fetchall()
        assert [event["kind"] for event in events] == ["result_saved", "job_completed"]
        assert json.loads(events[0]["details"]) == {"sha256": root_hash}
        number_of_attempts = db.execute(
            "SELECT count(*) FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id WHERE t.job_id=?",
            (jid,),
        ).fetchone()[0]
        assert number_of_attempts == count
        trials = db.execute(
            "SELECT t.part,t.window,t.config_id,t.state,t.attempts,t.reuses,t.computed_sha256,t.artifact_sha256,"
            "a.state attempt_state,a.computed_sha256 attempt_computed,a.artifact_sha256 attempt_artifact "
            "FROM trial_plans t LEFT JOIN trial_attempts a ON a.trial_id=t.id AND a.ordinal=t.attempts "
            "WHERE t.job_id=? ORDER BY t.part,t.window",
            (jid,),
        )
        for part, (row, trial, config_id) in enumerate(zip(result["rows"], trials, configuration_ids, strict=True)):
            assert row["part"] == trial["part"] == part and trial["window"] == "report"
            assert row["config_id"] == trial["config_id"] == config_id == identity(row["config"])
            assert trial["state"] == "completed" and trial["attempt_state"] == "checkpointed"
            assert trial["attempts"] == 1 and trial["reuses"] == 0
            path = directory / "parts" / f"{part:06d}.json.gz"
            raw = path.read_bytes()
            digest = sha(raw)
            assert row["report_sha256"] == trial["artifact_sha256"] == trial["attempt_artifact"] == digest
            assert read(path.with_suffix(".sha256.json")) == {"sha256": digest}
            saved = json.loads(gzip.decompress(raw))
            report = saved["report"]
            computed = identity(report)
            assert trial["computed_sha256"] == trial["attempt_computed"] == computed
            assert saved["config_id"] == report["config_id"] == config_id
            assert saved["payload_hash"] == payload_hash and saved["core_hash"] == report["core_hash"] == subject
            assert report["dataset_manifest_hash"] == result["dataset_manifest_hash"]
            trade_count = len(report["trades"])
            signal_count = len(report["signals"])
            assert row["metrics"] == report["metrics"]
            accounts_with_trades += int(trade_count > 0)
            trades += trade_count
            signals += signal_count
            line = (json.dumps({
                "part": part, "config_id": config_id, "report_sha256": digest,
                "computed_sha256": computed, "bytes": len(raw),
                "signals": signal_count, "trades": trade_count,
            }, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
            stream.write(line)
            output_digest.update(line)
    manifest_file.replace(out / "bounded-stress-original-parts.jsonl")
    return {
        "root_sha256": root_hash, "all_parts_manifest_sha256": output_digest.hexdigest(),
        "original_parts": count, "original_trial_attempts": number_of_attempts,
        "verified_result_index_rows": summary["row_count"], "last_result_index_part": count - 1,
        "accounts_with_trades": accounts_with_trades, "zero_trade_accounts": count - accounts_with_trades,
        "total_signals": signals, "total_trades": trades,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", help="Exercise the evidence harness with 60 actual accounts.")
    args = parser.parse_args()
    assert Path(inspect.getfile(Worker)).resolve().is_relative_to(STAGE)
    require_current_source()
    contract = read(CONTRACT_PATH)
    assert contract["count"] == 100_000 and contract["smoke_count"] == 60 and contract["worker_count"] == 1
    count = contract["smoke_count"] if args.smoke else contract["count"]
    out = Path(os.environ["PA_EVIDENCE_RUN_DIR"]).resolve()
    owned = ROOT / "data/dev027/bounded-financial-stress" / out.name.split("-", 1)[0]
    owned.mkdir(parents=True, exist_ok=False)
    lab = Lab(owned)
    subject = core_hash()
    manifest = dataset(lab, contract["dataset"])
    session = contract["dataset"]["session"]
    request = Search(
        dataset_id=manifest["id"], name="Bounded synthetic financial stress", start=session, end=session,
        count=count, seed=contract["seed"], families=contract["families"], timeframes=contract["timeframes"],
        sampling_policy={"mode": contract["sampling"]},
    )
    summary = {
        "scope": "60-account harness smoke" if args.smoke else "100,000-account deterministic stress",
        "catalog_case": contract["case_id"], "owned_root": owned.relative_to(ROOT).as_posix(),
        "core_sha256": subject, "contract_sha256": sha(CONTRACT_PATH.read_bytes()), "worker_count": 1,
        "requested_count": count, "fixture": manifest,
    }
    dump(out / "bounded-stress-start.json", summary)
    started = perf_counter()
    job = lab.create_experiment(request)
    created = perf_counter()
    jid = job["id"]
    assert not job["payload"].get("sampling_failure")
    configuration_ids = [identity(config) for config in job["payload"]["configurations"]]
    assert len(configuration_ids) == len(set(configuration_ids)) == count
    payload_hash = identity(job["payload"])
    del job
    dump(out / "bounded-stress-registration.json", summary | {"job_id": jid, "payload_sha256": payload_hash})
    worker = Worker(lab)
    assert worker.run_once()
    worker_complete = perf_counter()
    worker_resources = current_resources()
    status = lab.store.job_status(jid)
    if status["status"] != "completed":
        dump(out / "bounded-stress-incomplete.json", summary | {
            "job_id": jid, "state": status, "worker_resources": worker_resources,
            "elapsed_seconds": worker_complete - started, "lease_failure": worker.last_lease_failure,
        })
        raise RuntimeError("The owned financial-stress job did not complete. Inspect the retained checkpoint.")
    evidence = audit(lab, jid, manifest, configuration_ids, payload_hash, subject, out)
    require_current_source()
    files = [p for p in (owned / "data").rglob("*") if p.is_file()]
    complete = summary | evidence | {
        "job_id": jid, "payload_sha256": payload_hash, "completed_count": count,
        "creation_seconds": created - started, "through_worker_seconds": worker_complete - started,
        "through_audit_seconds": perf_counter() - started,
        "worker_process_resources": worker_resources, "through_audit_process_resources": current_resources(),
        "owned_data_files": len(files), "owned_data_bytes": sum(p.stat().st_size for p in files),
        "full_stress_completed": not args.smoke,
    }
    dump(out / "bounded-stress-summary.json", complete)
    print(json.dumps({key: value for key, value in complete.items() if key != "fixture"}), flush=True)


if __name__ == "__main__":
    main()
