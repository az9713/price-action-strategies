"""Retire a failed owned capacity continuation and prove original records survive."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from backend.lab.result_index import file_hash
from backend.lab.store import Store


root = Path.cwd().resolve()
identifier = sys.argv[1]
assert re.fullmatch("[A-Za-z0-9-]+", identifier)
receipt = json.loads((root / "verification/receipts" / (identifier + ".json")).read_text(encoding="utf-8"))
assert receipt["command"]["exit_code"] != 0
diagnostic = root / "verification/runs" / identifier / "capacity-incomplete-diagnostic.json"
entry = next(row for row in receipt["artifacts"] if row["path"] == diagnostic.relative_to(root).as_posix())
assert file_hash(diagnostic) == entry["sha256"]
failed = json.loads(diagnostic.read_text(encoding="utf-8"))
assert failed["completed_capacity"] is False and failed["status"] == "queued"
folder = root / "data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7"
store = Store(folder)
jid, expected = failed["job_id"], failed["checkpoint"]
job = store.job_status(jid)
assert job["kind"] == "search" and job["status"] == "queued" and job["checkpoint"] == expected
with store.db() as db:
    assert db.execute("SELECT owner FROM jobs WHERE id=?", (jid,)).fetchone()[0] is None
    assert [r[0] for r in db.execute("SELECT id FROM jobs WHERE status IN ('queued','running','canceling')")] == [jid]


def original_records():
    with store.db() as db:
        rows = [dict(row) for row in db.execute(
            "SELECT t.id,t.part,t.window,t.state,t.attempts,t.computed_sha256,t.artifact_sha256,"
            "a.state attempt_state,a.computed_sha256 attempt_computed,a.artifact_sha256 attempt_artifact "
            "FROM trial_plans t JOIN trial_attempts a ON a.trial_id=t.id AND a.ordinal=t.attempts "
            "WHERE t.job_id=? AND t.artifact_sha256 IS NOT NULL ORDER BY t.part,t.window", (jid,),
        )]
    assert len(rows) == expected
    for row in rows:
        path = folder / "data/jobs" / jid / "parts" / f"{row['part']:06d}.json.gz"
        row["actual_file_sha256"] = file_hash(path)
        assert row["actual_file_sha256"] == row["artifact_sha256"] == row["attempt_artifact"]
        assert row["computed_sha256"] == row["attempt_computed"]
    return rows


before = original_records()
store.cancel(jid)
after = original_records()
assert after == before and store.job_status(jid)["status"] == "canceled"
with store.db() as db:
    assert db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0] == 0
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
result = dict(
    failed_execution=identifier, job_id=jid, original_committed_accounts=len(after),
    original_trials_attempts_and_files_unchanged=True,
    original_record_sha256=hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
    final_state="canceled", owned_benchmark_registry_has_no_runnable_jobs=True,
)
(out / "owned-capacity-original-preservation.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
print(json.dumps(result), flush=True)
