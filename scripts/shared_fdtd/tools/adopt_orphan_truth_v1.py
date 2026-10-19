from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SCRIPTS = ROOT / "scripts"
DB_PATH = Path(r"D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3")
MANIFEST = ROOT / "reports/coupling/SHARED_V3_ATTEMPT004_RECOVERY_EVIDENCE_MANIFEST_V1.json"
SNAPSHOT = ROOT / "reports/coupling/SHARED_V3_STRICT_FENCED_ORPHAN_TRUTH_ADOPTION_V1_PRE_ADOPTION_SNAPSHOT.json"
RESULT = ROOT / "reports/coupling/SHARED_V3_STRICT_FENCED_ORPHAN_TRUTH_ADOPTION_V1_RUNTIME_RESULT.json"
EXPECTED_MANIFEST_SHA = "75e71812b670c5d09ff332aecf982ac3292a7278b97003867f8296e10ed16e92"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

from shared_fdtd.control_v3 import ControlDB, OrphanTruthAdoption, artifact_identity_sha256
from shared_fdtd.engine.persistence import sha256_file
from shared_fdtd.engine.process_identity import snapshot as process_snapshot
from shared_fdtd.engine.event_log import read_events
from shared_fdtd.tools.v3_g2_host import fresh_load_validate_path

def now():
    return datetime.now(timezone.utc).isoformat()

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")

def fail(reason, **details):
    result = {"status": reason, "details": details, "solver_invocations": 0, "scientific_entries": 0, "recovery_transaction_count": 0}
    write(RESULT, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0)

if not MANIFEST.is_file():
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="manifest_missing")
manifest_sha = sha256_file(MANIFEST)
if manifest_sha != EXPECTED_MANIFEST_SHA:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="manifest_sha_mismatch", expected=EXPECTED_MANIFEST_SHA, actual=manifest_sha)
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if (manifest.get("case_id"), manifest.get("attempt_id")) != ("K6V1_S14", "attempt_004"):
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="manifest_identity_mismatch")
attempt_root = ROOT / "outputs/coupling_ml/PW_K6_SEED_DB_V1_PRODUCTION_V1/K6V1_S14/attempt_004"
mismatches = []
for item in manifest.get("files", []):
    path = Path(item["path"])
    if not path.is_file():
        mismatches.append({"path": str(path), "reason": "missing"})
        continue
    actual_sha = sha256_file(path)
    actual_size = path.stat().st_size
    if actual_sha != item["sha256"] or actual_size != int(item["size_bytes"]):
        mismatches.append({"path": str(path), "expected_sha256": item["sha256"], "actual_sha256": actual_sha, "expected_size": item["size_bytes"], "actual_size": actual_size})
if mismatches:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="frozen_inventory_mismatch", mismatches=mismatches)

by_rel = {str(x["relative_to_attempt"]).replace("\\", "/"): Path(x["path"]) for x in manifest["files"]}
native_fsp = by_rel["native/K6V1_S14__attempt_004_runtime.fsp"]
post_fsp = by_rel["post/K6V1_S14__attempt_004_runtime.fsp"]
native_h5 = by_rel["native/K6V1_S14__attempt_004_runtime/K6V1_S14__attempt_004_runtime_output.h5"]
raw_json = by_rel["raw/K6V1_S14__attempt_004_raw.json"]
projection = by_rel["projection/K6V1_S14__attempt_004_projection.json"]
archive = by_rel["HF_ARCHIVE_MANIFEST.json"]
setup = by_rel["setup/runtime.fsp"]
ledger_path = by_rel["attempt_ledger.json"]
state_path = by_rel["attempt_state.json"]
ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
state = json.loads(state_path.read_text(encoding="utf-8"))
events = read_events(attempt_root / "events.jsonl")
event_counts = Counter(str(e.get("event_type")) for e in events)
if int(ledger.get("run_invocation_count", 0)) != 1 or not ledger.get("solver_entered") or not ledger.get("solver_returned") or int(ledger.get("replay", 0)) != 0:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="attempt_ledger_invalid", ledger=ledger)
if event_counts["SCIENTIFIC_SOLVER_ENTERED"] != 1 or event_counts["SOLVER_RETURNED"] != 1 or event_counts["SCIENTIFIC_VALID"] != 1 or event_counts["HF_ARCHIVED"] != 1:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="attempt_event_counts_invalid", event_counts=dict(event_counts))
try:
    json.loads(raw_json.read_text(encoding="utf-8"))
    json.loads(projection.read_text(encoding="utf-8"))
    json.loads(archive.read_text(encoding="utf-8"))
except Exception as exc:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="truth_json_invalid", error=repr(exc))

load_cfg = json.loads((attempt_root / "setup/runtime.fsp").with_suffix(".json").read_text(encoding="utf-8")) if False else {}
with ControlDB(DB_PATH).connect(readonly=True) as con:
    queue = con.execute("SELECT * FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004'").fetchone()
    control = con.execute("SELECT * FROM admission_control WHERE control_id=1").fetchone()
    slot = con.execute("SELECT * FROM slots WHERE slot_id=?", (queue["slot_id"],)).fetchone() if queue else None
    s15 = con.execute("SELECT * FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S15' AND attempt_id='attempt_001'").fetchone()
    s16 = con.execute("SELECT * FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S16' AND attempt_id='attempt_001'").fetchone()
    db_entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
    s15_entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S15' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
    s16_entries = con.execute("SELECT COUNT(*) FROM lease_events WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S16' AND event_type='SCIENTIFIC_SOLVER_ENTERED'").fetchone()[0]
    foreign = con.execute("SELECT metric_value FROM health_metrics WHERE metric_name='FOREIGN_MUTATION_COUNT'").fetchone()[0]
    duplicate = con.execute("SELECT metric_value FROM health_metrics WHERE metric_name='DUPLICATE_SCIENTIFIC_ENTRY_COUNT'").fetchone()[0]
    newer = [dict(r) for r in con.execute("SELECT attempt_id,state FROM branch_queue WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id NOT IN ('attempt_001','attempt_002','attempt_003','attempt_004')")]
    active_resources = []
    for table in ("resource_reservations", "gpu_capacity_leases"):
        active_resources.extend([dict(r) for r in con.execute(f"SELECT * FROM {table} WHERE branch_id='coupling_ml' AND logical_case_id='K6V1_S14' AND attempt_id='attempt_004' AND state IN ('RESERVED','LIVE','RELEASE_PENDING','OWNER_QUARANTINED')")])
if queue is None or queue["state"] != "AMBIGUOUS_QUARANTINED":
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="queue_state", state=queue["state"] if queue else None)
if control is None or int(control["new_entry_hold"]) != 1:
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="hold_not_true")
if queue["slot_id"] is None or slot is None or slot["state"] != "FREE" or any(slot[k] is not None for k in ("owner_branch","logical_case_id","attempt_id","lease_token")):
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="slot_not_free")
if active_resources or newer or db_entries != 1 or s15_entries or s16_entries or int(foreign) or int(duplicate):
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="control_counts", active_resources=active_resources, newer=newer, db_entries=db_entries, s15_entries=s15_entries, s16_entries=s16_entries, foreign=foreign, duplicate=duplicate)
if s15 is None or s16 is None or s15["state"] != "WAIT_RESOURCE_CAPACITY" or s16["state"] != "WAIT_RESOURCE_CAPACITY":
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="s15_s16_queue_state", s15=dict(s15) if s15 else None, s16=dict(s16) if s16 else None)

live = []
for p in process_snapshot() or []:
    name = str(p.get("Name") or "").lower()
    command = str(p.get("CommandLine") or "").lower()
    if ("k6v1_s14" in command or "attempt_004" in command or "runtime.fsp" in command) and ("fdtd-engine" in name or "mpiexec" in name):
        live.append(p)
if live:
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="live_attempt_process", processes=live)
markers = {"PERSISTENCE_PENDING","NATIVE_TRUTH_PERSISTING","FRESH_LOAD_PENDING"}
persistence_active = bool(markers.intersection(event_counts))
if persistence_active:
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="persistence_active", markers=sorted(markers.intersection(event_counts)))

payload = json.loads(queue["payload_json"])
load_cfg = dict(payload)
load_cfg.update({"db": str(DB_PATH), "branch": "coupling_ml", "case": "K6V1_S14", "attempt": "attempt_004", "task": payload.get("task", "PW_K6_SEED_DB_V1_PRODUCTION_V1"), "attempt_root": str(attempt_root), "runtime": payload.get("runtime", "")})
try:
    native_load = fresh_load_validate_path(native_fsp, load_cfg, True)
    post_load = fresh_load_validate_path(post_fsp, load_cfg, True)
except Exception as exc:
    fail("BLOCKED_EVIDENCE_DRIFT", reason_detail="fresh_load_only_failed", error=repr(exc))

artifact_hashes = {
    "fsp": sha256_file(native_fsp),
    "h5": sha256_file(native_h5),
    "raw": sha256_file(raw_json),
    "projection": sha256_file(projection),
    "hf_archive": sha256_file(archive),
    "setup": sha256_file(setup),
    "solver_entry": sha256_file(ledger_path),
    "provenance": sha256_file(state_path),
}
artifact_identity = artifact_identity_sha256(artifact_hashes)
truth_validation = manifest.get("truth_validation", {})
truth_valid = all(str(truth_validation.get(k, "")).upper() in {"PASS", "DURABLE", "TRUE"} for k in ("fresh_load_only_native","fresh_load_only_post","raw_projection_orders_state","hf_archive_manifest","post_fsp_verification"))
controller_status_path = Path(r"D:\apcd_runtime\global_fdtd_control_v3\PW_K6_SEED_DB_V1_PRODUCTION_V1_controller_status.json")
controller_status = json.loads(controller_status_path.read_text(encoding="utf-8")) if controller_status_path.is_file() else {}
autofill_disabled = bool(control["new_entry_hold"]) and not controller_status.get("launched_last_tick") and s15["state"] == "WAIT_RESOURCE_CAPACITY" and s16["state"] == "WAIT_RESOURCE_CAPACITY"
evidence = {
    "scientific_entry_count": 1, "solver_invocation_count": 1, "replay_count": 0,
    "duplicate_scientific_entry_count": int(duplicate), "newer_attempt_exists": False,
    "live_process": False, "persistence_active": False, "truth_valid": bool(truth_valid and native_load.get("passed") and post_load.get("passed")),
    "conflicting_truth": False, "autofill_enabled": not autofill_disabled,
    "s15_s16_non_entered": True, "foreign_mutation_count": int(foreign), "runtime_owner_created": False,
    "evidence_manifest_sha256": manifest_sha, "artifact_hashes": artifact_hashes, "artifact_identity_sha256": artifact_identity,
}
if not evidence["truth_valid"] or not autofill_disabled:
    fail("BLOCKED_CONTROL_PRECONDITION", reason_detail="evidence_gate", truth_valid=evidence["truth_valid"], autofill_disabled=autofill_disabled)

pre_snapshot = {
    "created_utc": now(), "manifest_sha256": manifest_sha, "artifact_hashes": artifact_hashes,
    "artifact_identity_sha256": artifact_identity, "fresh_load_only_native": native_load, "fresh_load_only_post": post_load,
    "attempt_ledger": {"solver_entered": ledger.get("solver_entered"), "solver_returned": ledger.get("solver_returned"), "run_invocation_count": ledger.get("run_invocation_count"), "replay": ledger.get("replay")},
    "event_counts": dict(event_counts), "queue": dict(queue), "control": dict(control), "slot": dict(slot), "s15": dict(s15), "s16": dict(s16),
    "live_attempt_processes": live, "persistence_active": persistence_active, "autofill_disabled": autofill_disabled,
    "solver_invocations": 0, "scientific_entries": 0, "recovery_transaction_count_before": 0,
}
write(SNAPSHOT, pre_snapshot)
rec = OrphanTruthAdoption(ControlDB(DB_PATH))
fence = rec.issue_fence(evidence=evidence, control_generation=int(control["control_generation"]), metadata={"manifest_path": str(MANIFEST), "pre_adoption_snapshot": str(SNAPSHOT)})
adoption = rec.adopt(fence_id=fence["fence_id"], evidence=evidence, control_generation=int(control["control_generation"]), metadata={"manifest_path": str(MANIFEST), "pre_adoption_snapshot": str(SNAPSHOT)})
result = {"status": "PASS_ORPHAN_TRUTH_ADOPTED", "fence": fence, "adoption": adoption, "evidence_manifest_sha256": manifest_sha, "artifact_hashes": artifact_hashes, "artifact_identity_sha256": artifact_identity, "fresh_load_only_native": native_load, "fresh_load_only_post": post_load, "solver_invocations": 0, "scientific_entries": 0, "recovery_transaction_count": 1}
write(RESULT, result)
print(json.dumps(result, ensure_ascii=False, indent=2))

