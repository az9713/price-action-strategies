"""Compare UTF-8 bytes and text materialization on a retained owned 10,000-row plan."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from time import perf_counter, process_time


ROOT = Path.cwd().resolve()
OWNED = ROOT / "data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7"
JOB_ID = "e811eba6381746b884745b1eec51b6f9"
PLAN = (
    "SELECT json_group_array(json_array(id,part,window,role,config_id,plan_hash,provenance)) "
    "FROM (SELECT id,part,window,role,config_id,plan_hash,provenance FROM trial_plans "
    "WHERE job_id=? ORDER BY part,window)"
)
PLAN_BLOB = PLAN.replace("json_group_array(json_array(id,part,window,role,config_id,plan_hash,provenance))",
                         "CAST(json_group_array(json_array(id,part,window,role,config_id,plan_hash,provenance)) AS BLOB)")
PAYLOAD = "SELECT payload FROM jobs WHERE id=?"
PAYLOAD_BLOB = "SELECT CAST(payload AS BLOB) FROM jobs WHERE id=?"


def measure(db, encoding, payload_sql, plan_sql):
    wall, cpu = perf_counter(), process_time()
    payload = db.execute(payload_sql, (JOB_ID,)).fetchone()[0]
    plan = db.execute(plan_sql, (JOB_ID,)).fetchone()[0]
    if encoding == "text":
        payload, plan = payload.encode("utf-8"), plan.encode("utf-8")
    digests = {"payload_sha256": hashlib.sha256(payload).hexdigest(),
               "projection_sha256": hashlib.sha256(plan).hexdigest()}
    return {
        "representation": encoding, "wall_seconds": perf_counter() - wall,
        "cpu_seconds": process_time() - cpu, "payload_bytes": len(payload), "projection_bytes": len(plan),
        **digests,
    }


def main():
    origin = json.loads((OWNED / "origin.json").read_text(encoding="utf-8"))
    assert origin["fresh_provider_acquisition"] and not origin["original_user_store_copied"]
    path = (OWNED / "data/lab.sqlite3").resolve()
    assert path.is_relative_to(OWNED)
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        assert db.execute("PRAGMA encoding").fetchone()[0] == "UTF-8"
        assert db.execute(
            "SELECT status,typeof(payload),length(CAST(payload AS BLOB)) FROM jobs WHERE id=?", (JOB_ID,),
        ).fetchone() == ("canceled", "text", 8_575_239)
        assert db.execute("SELECT count(*) FROM trial_plans WHERE job_id=?", (JOB_ID,)).fetchone()[0] == 10_000
        options = {"text": (PAYLOAD, PLAN), "blob": (PAYLOAD_BLOB, PLAN_BLOB)}
        results = [
            measure(db, option, *options[option])
            for pair in (("text", "blob"), ("blob", "text"), ("text", "blob"))
            for option in pair
        ]
    finally:
        db.close()
    assert len({(item["payload_sha256"], item["projection_sha256"]) for item in results}) == 1
    output = {
        "scope": "Read-only owned-plan query and hash timing. No worker capacity claim.",
        "sqlite_version": sqlite3.sqlite_version, "original_trial_rows": 10_000,
        "same_original_digests": True, "samples": results,
    }
    out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
    (out / "frozen-plan-hash-materialization.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output), flush=True)


if __name__ == "__main__":
    main()
