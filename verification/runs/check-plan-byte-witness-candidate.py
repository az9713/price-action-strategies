"""Compare the original and candidate complete immutable-plan checks."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from threading import RLock
from time import perf_counter, process_time
from collections import OrderedDict

from backend.lab.config import Strategy, Costs, Portfolio, canonical
from backend.lab.store import Store, StateError
from backend.lab.trials import TrialLedger


root = Path.cwd().resolve()
candidate_path = root / "data/dev027/plan-byte-witness-candidate/trials.py"
spec = importlib.util.spec_from_file_location("backend.lab.plan_byte_witness", candidate_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
subject = json.loads((root / "verification/runs/20261111T004346953637Z-bounded-financial-stress-harness-60-original-account-smoke/research-stage-subject.json").read_text(encoding="utf-8"))
original_path = root / "data/dev027/research-src/backend/lab/trials.py"
original_hash = hashlib.sha256(original_path.read_bytes()).hexdigest()
assert original_hash == subject["source_files"]["backend/lab/trials.py"]


def fresh_ledger(cls, store):
    ledger = cls.__new__(cls)
    ledger.store = store
    ledger.error = StateError
    ledger.verification_lock = RLock()
    ledger.verification_proofs = OrderedDict()
    return ledger


owned = root / "data/dev027/capacity-market/f00ea201d8ad4776ace124d08f704cf7"
origin = json.loads((owned / "origin.json").read_text(encoding="utf-8"))
assert origin["fresh_provider_acquisition"] and not origin["original_user_store_copied"]
job_id = "e811eba6381746b884745b1eec51b6f9"
path = (owned / "data/lab.sqlite3").resolve()
assert path.is_relative_to(owned)
db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
db.row_factory = sqlite3.Row
ledgers = {"original": fresh_ledger(TrialLedger, Store.__new__(Store)),
           "candidate": fresh_ledger(module.TrialLedger, Store.__new__(Store))}
timings = []
try:
    db.execute("PRAGMA query_only=ON")
    assert db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()[0] == "canceled"
    for ledger in ledgers.values():
        ledger.verify(job_id, db)
    expected = [next(iter(ledger.verification_proofs.values())) for ledger in ledgers.values()]
    assert expected[0] == expected[1]
    for order in (("original", "candidate"), ("candidate", "original")):
        for name in order:
            start, cpu = perf_counter(), process_time()
            for _ in range(6):
                ledgers[name].verify(job_id, db)
                assert not db.in_transaction
            timings.append(dict(source=name, calls=6, wall_seconds=perf_counter()-start, cpu_seconds=process_time()-cpu))
finally:
    db.close()


with tempfile.TemporaryDirectory(prefix="price-action-plan-bytes-") as work:
    for encoding in ("UTF-8", "UTF-16le"):
        folder = Path(work) / encoding
        (folder / "data").mkdir(parents=True)
        with sqlite3.connect(folder / "data/lab.sqlite3") as init:
            init.execute(f"PRAGMA encoding='{encoding}'")
            init.execute("CREATE TABLE authored_encoding_fixture(id INTEGER)")
        init.close()
        store = Store(folder)
        payload = dict(dataset_id="a"*24, strategy=Strategy().model_dump(), costs=Costs().model_dump(),
                       portfolio=Portfolio().model_dump(), start="2026-10-05", end="2026-10-06",
                       seed=42, core_hash="b"*64, dataset_manifest_hash="c"*64, note="caf\u00e9 \u6e2c\u8a66")
        jid = store.create_job("experiment", payload)["id"]
        original = fresh_ledger(TrialLedger, store)
        candidate = fresh_ledger(module.TrialLedger, store)
        for ledger in (original, candidate):
            ledger.verify(jid)
        with store.db() as db:
            assert db.execute("PRAGMA encoding").fetchone()[0].lower() == encoding.lower()
            db.execute("UPDATE jobs SET payload=? WHERE id=?",
                       (json.dumps(payload, ensure_ascii=False, indent=2), jid))
        for ledger in (original, candidate):
            ledger.verify(jid)
        with store.db() as db:
            db.execute("UPDATE trial_plans SET config_id=? WHERE job_id=?", ("0"*64, jid))
        for ledger in (original, candidate):
            try:
                ledger.verify(jid)
            except StateError:
                pass
            else:
                raise AssertionError("A modified original row was accepted.")
        with store.db() as db:
            db.execute("UPDATE jobs SET payload=? WHERE id=?", (canonical(payload).encode(), jid))
        try:
            candidate.verify(jid)
        except StateError as error:
            assert "not stored as text" in str(error)
        else:
            raise AssertionError("Malformed original storage type was accepted.")

result = dict(
    scope="Candidate component timing only. No candidate adoption or worker capacity claim.",
    original_sha256=original_hash, candidate_sha256=hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    exact_owned_plan_proof_matches=True, original_plan_configurations=10_000,
    whitespace_and_unicode_in_both_encodings_match=True, changed_trial_refused=True,
    invalid_storage_type_refused=True, timings=timings,
)
out = Path(os.environ["PA_EVIDENCE_RUN_DIR"])
(out / "plan-byte-witness-candidate.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result), flush=True)
