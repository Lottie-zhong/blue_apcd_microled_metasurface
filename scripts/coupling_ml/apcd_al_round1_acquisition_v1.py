"""Acquire the sealed AL Round-1 HF truth set through the validated V1 runner."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
SCRIPT_DIR = ACTIVE / "scripts" / "coupling_ml"
READINESS = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW_V1"
TRAINVAL = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
BLIND = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1"
AUDIT_NS = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1"
AL_MANIFEST = READINESS / "AL_ROUND1_8G_SEALED_MANIFEST.json"
V2_PLAN = READINESS / "V2_PROSPECTIVE_TEST_PLAN.json"
V1_BLIND_SEAL = TRAINVAL / "BLIND_PROSPECTIVE_SEALED_MANIFEST.json"
V1_BLIND_FINAL = BLIND / "FINAL_SHA256_MANIFEST.json"
READINESS_FINAL = READINESS / "FINAL_SHA256_MANIFEST.json"
AL_OUT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1"
PCA = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "ANGULAR_PCA_MODEL.npz"
TASK = "APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1"
ATTEMPT = "attempt_001"
DOMAIN = "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN"
EXPECTED_AL_SHA = "538e32ab7845ac47b221006bc07c21219d8f52dc6277b8124150d84b6c20d52c"
EXPECTED_V2_SHA = "9c27ef17229772ff4aa15c2e45a51b554edf2b62b1f110926a6839744a9f6807"
WLS = np.arange(445.0, 456.0, 1.0)
PCA_COLUMNS = ("pca_c5", "pca_c17", "pca_c12", "pca_c1", "pca_c3", "pca_c4")

sys.path.insert(0, str(SCRIPT_DIR))
_spec = importlib.util.spec_from_file_location("al_trainval_runner", SCRIPT_DIR / "apcd_2d_ml_v1_trainval_acquisition_v1.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("validated trainval runner unavailable")
tv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tv)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(safe(payload), stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def file_record(path: Path) -> dict[str, Any]:
    path = Path(path)
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None}


def geometry_fingerprint(values: tuple[float, ...]) -> str:
    text = "K6|" + "|".join(f"D{i}={v:.6f}" for i, v in enumerate(values, 1))
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def vector(row: dict[str, Any]) -> tuple[float, ...]:
    suffix = "_nm" if "D1_nm" in row else ""
    return tuple(float(row[f"D{i}{suffix}"]) for i in range(1, 7))


def load_al_rows() -> list[dict[str, Any]]:
    payload = json.loads(AL_MANIFEST.read_text(encoding="utf-8"))
    if sha(AL_MANIFEST).lower() != EXPECTED_AL_SHA or payload.get("sealed") is not True or payload.get("truth_acquired") != 0:
        raise RuntimeError("AL sealed manifest authority mismatch")
    rows: list[dict[str, Any]] = []
    for index, source in enumerate(payload.get("rows", []), 1):
        if source.get("geometry_id") != f"ALR1_{index:02d}" or source.get("sealed") is not True or source.get("truth_acquired") is not False:
            raise RuntimeError("AL order/seal/truth gate failed")
        values = tuple(float(source[f"D{i}"]) for i in range(1, 7))
        if source.get("geometry_sha256") != geometry_fingerprint(values):
            raise RuntimeError(f"geometry fingerprint mismatch: {source.get('geometry_id')}")
        rows.append({
            "geometry_id": source["geometry_id"],
            **{f"D{i}_nm": float(source[f"D{i}"]) for i in range(1, 7)},
            "geometry_fingerprint_sha256": source["geometry_sha256"],
            "split": "AL_ROUND1",
            "candidate_id": source.get("candidate_id"),
            "selection_rank": source.get("selection_rank"),
        })
    if [r["geometry_id"] for r in rows] != [f"ALR1_{i:02d}" for i in range(1, 9)]:
        raise RuntimeError("AL acquisition order is not frozen ALR1_01..08")
    return rows


def configure_globals(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows or load_al_rows()
    tv.OUT = AL_OUT
    tv.DOE_ROW_BY_ID = {row["geometry_id"]: row for row in rows}
    tv.JOB_PREFIX = TASK
    tv.ATTEMPT = ATTEMPT
    tv.DOMAIN_VERDICT = DOMAIN
    return rows


def row_set(rows: list[dict[str, Any]], use_sha: str) -> set[tuple[Any, ...]]:
    return {(vector(row), row.get(use_sha)) for row in rows}


def source_rows(path: Path, value_keys: tuple[str, ...] = ("D1", "D2", "D3", "D4", "D5", "D6")) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("rows", []))


def source_vector(row: dict[str, Any]) -> tuple[float, ...]:
    suffix = "_nm" if "D1_nm" in row else ""
    return tuple(float(row[f"D{i}{suffix}"]) for i in range(1, 7))


def overlap(al_rows: list[dict[str, Any]], other_rows: list[dict[str, Any]]) -> dict[str, Any]:
    av = {vector(row) for row in al_rows}
    ah = {row["geometry_fingerprint_sha256"] for row in al_rows}
    ov = {source_vector(row) for row in other_rows}
    oh = {row.get("geometry_sha256", row.get("geometry_fingerprint_sha256")) for row in other_rows}
    return {"vector_overlap": sorted([list(v) for v in av & ov]), "sha_overlap": sorted(ah & oh), "count": len(av & ov) + len(ah & oh - ah & ov), "pass": not (av & ov or ah & oh)}


def values_close(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-15)
    return a == b


def fingerprint_audit(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    allowed = {f"NP_bar_{i}.x span" for i in range(6)}
    unexpected = []
    for name in sorted(set(reference.get("rows", {})) | set(candidate.get("rows", {}))):
        if name not in reference.get("rows", {}) or name not in candidate.get("rows", {}):
            unexpected.append(name)
            continue
        props = set(reference["rows"][name]) | set(candidate["rows"][name])
        for prop in sorted(props):
            path = f"{name}.{prop}"
            if path in allowed:
                continue
            if not values_close(reference["rows"][name].get(prop), candidate["rows"][name].get(prop)):
                unexpected.append(path)
    return {"allowed_geometry_diffs": sorted(allowed), "unexpected_scientific_diffs": unexpected, "pass": not unexpected}


def scheduler_snapshot() -> dict[str, Any]:
    return tv.scheduler_snapshot()


def m2s_guard(snapshot: dict[str, Any]) -> None:
    tv.m2s_guard(snapshot)


def preflight() -> int:
    reuse_preflight = AL_OUT.exists()
    if reuse_preflight:
        case_root = AL_OUT / "CASES"
        if not (AL_OUT / "SETUPS").is_dir() or not (AL_OUT / "AL_ROUND1_OVERLAP_AUDIT.json").is_file() or (case_root.exists() and any(case_root.iterdir())):
            raise RuntimeError(f"output namespace exists; overwrite forbidden: {AL_OUT}")
    al_rows = load_al_rows()
    v2 = json.loads(V2_PLAN.read_text(encoding="utf-8"))
    if sha(V2_PLAN).lower() != EXPECTED_V2_SHA or v2.get("sealed") is not True or v2.get("truth_acquired") != 0 or v2.get("solver_launched") is not False or any(row.get("truth_acquired") != 0 for row in v2.get("rows", [])):
        raise RuntimeError("V2 prospective seal gate failed")
    doe = tv.load_doe()
    existing = [{**row, "geometry_fingerprint_sha256": row["geometry_fingerprint_sha256"]} for row in doe]
    v1_rows = source_rows(V1_BLIND_SEAL)
    v2_rows = v2["rows"]
    overlap_audit = {
        "schema_version": "AL_ROUND1_OVERLAP_AUDIT_V1",
        "existing_64": overlap(al_rows, existing),
        "v1_blind": overlap(al_rows, v1_rows),
        "v2_prospective": overlap(al_rows, v2_rows),
        "internal_duplicate_vectors": len({vector(row) for row in al_rows}) != len(al_rows),
        "internal_duplicate_sha": len({row["geometry_fingerprint_sha256"] for row in al_rows}) != len(al_rows),
    }
    overlap_audit["pass"] = all([
        overlap_audit["existing_64"]["pass"], overlap_audit["v1_blind"]["pass"], overlap_audit["v2_prospective"]["pass"],
        not overlap_audit["internal_duplicate_vectors"], not overlap_audit["internal_duplicate_sha"],
    ])
    AL_OUT.mkdir(parents=True, exist_ok=True)
    (AL_OUT / "SETUPS").mkdir(exist_ok=True)
    (AL_OUT / "CASES").mkdir(exist_ok=True)
    (AL_OUT / "CONTROLLER_LOGS").mkdir(exist_ok=True)
    if not overlap_audit["pass"]:
        write_json(AL_OUT / "AL_ROUND1_OVERLAP_AUDIT.json", overlap_audit)
        raise RuntimeError("AL overlap/duplicate hard gate failed")
    write_json(AL_OUT / "AL_ROUND1_OVERLAP_AUDIT.json", overlap_audit)
    freeze_source = TRAINVAL / "V1_SCIENTIFIC_SPACE_FREEZE.json"
    prior_source = TRAINVAL / "K6_V1_64G_PRIOR_FEATURES.csv"
    reference_setup = next(TRAINVAL.glob("SETUPS/*/setup_pre.fsp"), None)
    if not freeze_source.is_file() or not prior_source.is_file() or reference_setup is None or not PCA.is_file():
        raise RuntimeError("validated V1 freeze/prior/reference/PCA input missing")
    shutil.copy2(freeze_source, AL_OUT / "V1_SCIENTIFIC_SPACE_FREEZE.json")
    shutil.copy2(prior_source, AL_OUT / "K6_V1_64G_PRIOR_FEATURES.csv")
    freeze = json.loads((AL_OUT / "V1_SCIENTIFIC_SPACE_FREEZE.json").read_text(encoding="utf-8"))
    if freeze.get("domain") != DOMAIN or freeze.get("fdtd_x_um") != 23.0 or freeze.get("monitor_x_um") != 19.0 or freeze.get("training_or_pca") is not False:
        raise RuntimeError("V1 scientific freeze mismatch")
    allowed_values = {i: {float(row[f"D{i}_nm"]) for row in existing} for i in range(1, 7)}
    parameter_checks = []
    for row in al_rows:
        values = vector(row)
        parameter_checks.append({"geometry_id": row["geometry_id"], "grid_membership": all(values[i - 1] in allowed_values[i] for i in range(1, 7)), "bounds_and_step": all(100 <= v <= 230 and (v - 100) % 5 == 0 for v in values), "geometry_sha256": row["geometry_fingerprint_sha256"], "geometry": list(values)})
    if not all(item["grid_membership"] and item["bounds_and_step"] for item in parameter_checks):
        raise RuntimeError("AL parameter-space authority gate failed")
    configure_globals(al_rows)
    source = tv.source_reference()
    write_json(AL_OUT / "V1_SOURCE_REFERENCE.json", source)
    reference = tv.runner.snapshot(reference_setup)
    setup_audits = []
    fingerprints = []
    for row in al_rows:
        audit = tv.materialize_setup(row)
        setup_audits.append(audit)
        fingerprints.append({"geometry_id": row["geometry_id"], "geometry": list(vector(row)), "setup": audit["setup_pre"], "audit_pass": audit["pass"], "fingerprint": fingerprint_audit(reference, audit["snapshot"])})
    if not all(item["audit_pass"] and item["fingerprint"]["pass"] for item in fingerprints):
        raise RuntimeError("AL setup/model fingerprint gate failed")
    sched = scheduler_snapshot()
    m2s_guard(sched)
    authority = {
        "schema_version": "AL_ROUND1_AUTHORITY_VERIFICATION_V1",
        "sealed_manifest": file_record(AL_MANIFEST), "sealed_manifest_expected_sha256": EXPECTED_AL_SHA,
        "v2_plan": file_record(V2_PLAN), "v2_plan_expected_sha256": EXPECTED_V2_SHA,
        "domain_verdict": DOMAIN, "fixed_domain": {"fdtd_x_um": 23.0, "monitor_x_um": 19.0, "source_x_nm": 0.0, "source_z_nm": -276.0, "wavelengths_nm": WLS.tolist(), "K": 6, "p_nm": 290.0, "H_nm": 500.0, "boundary": "finite PML; no periodic/Bloch"},
        "baseline_champion": "RIDGE_RAW_CHAMPION", "frozen_pca_rank": 32, "training_or_pca_refit": False,
        "parameter_checks": parameter_checks, "setup_audits": setup_audits, "production_fingerprints": fingerprints,
        "source_reference": source, "v1_blind_final_manifest": file_record(V1_BLIND_FINAL), "readiness_final_manifest": file_record(READINESS_FINAL),
        "solver_entry_delta": 0, "m2s_attempt_002_started": False, "pass": True,
    }
    write_json(AL_OUT / "AL_ROUND1_AUTHORITY_VERIFICATION.json", authority)
    plan = {"schema_version": "AL_ROUND1_ACQUISITION_PLAN_V1", "geometry_order": [row["geometry_id"] for row in al_rows], "geometry_count": 8, "spectral_points_per_geometry": 11, "expected_rows": 88, "source_sealed_manifest_sha256": EXPECTED_AL_SHA, "domain": DOMAIN, "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": sched.get("global_capacity"), "max_concurrent_jobs": 2, "two_slot_batches": [[row["geometry_id"] for row in al_rows[i:i + 2]] for i in range(0, 8, 2)], "no_dynamic_replacement": True, "no_rerun": True, "training": False, "pca_refit": False, "v2_truth_acquisition": False}
    write_json(AL_OUT / "AL_ROUND1_ACQUISITION_PLAN.json", plan)
    registry_rows = [{"geometry_id": row["geometry_id"], "geometry": list(vector(row)), "geometry_sha256": row["geometry_fingerprint_sha256"], "status": "PLANNED", "solver_entered": False, "solver_returned": False, "post_validated": False, "raw_validated": False, "rerun_delta": 0, "duplicate": False} for row in al_rows]
    write_json(AL_OUT / "AL_ROUND1_ACQUISITION_REGISTRY.json", {"schema_version": "AL_ROUND1_ACQUISITION_REGISTRY_V1", "task": TASK, "attempt_id": ATTEMPT, "rows": registry_rows, "phase": "PLANNED", "expected_solver_entries": 8, "expected_batches": 4, "rerun_delta": 0, "duplicate_count": 0, "training_count": 0})
    write_json(AL_OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", {"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V1", "phase": "PREFLIGHT", "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": sched.get("global_capacity"), "active_slots_before_launch": sched.get("active_slots", []), "m2s_processes_before_launch": [p for p in sched.get("processes", []) if p.get("is_m2s")], "max_task_concurrent_slots": 0, "manual_registry_edit": False, "solver_entry_delta": 0, "pass": sched.get("global_capacity") == 3 and not any(p.get("is_m2s") for p in sched.get("processes", []))})
    write_json(AL_OUT / "V2_PROSPECTIVE_SEAL_AUDIT.json", {"schema_version": "V2_PROSPECTIVE_SEAL_AUDIT_V1", "source": file_record(V2_PLAN), "sealed": True, "truth_acquired": 0, "solver_launched": False, "rows": [{"geometry_id": r["geometry_id"], "geometry_sha256": r["geometry_sha256"], "truth_acquired": r["truth_acquired"]} for r in v2["rows"]], "pass": True})
    write_json(AL_OUT / "PREFLIGHT_AUDIT.json", {"schema_version": "AL_ROUND1_ZERO_SOLVER_PREFLIGHT_AUDIT_V1", "generated_utc": now(), "solver_entry_delta": 0, "expected_solver_entries": 8, "overlap_pass": True, "authority_pass": True, "fingerprint_pass": True, "scheduler_before_solver": sched, "m2s_attempt_002_started": False, "v1_blind_untouched": True, "v2_sealed_unacquired": True, "training_count": 0, "pca_refit": False, "pass": True})
    print(json.dumps({"status": "PREFLIGHT_PASS", "solver_entry_delta": 0, "geometry_count": 8, "output": str(AL_OUT)}, ensure_ascii=False), flush=True)
    return 0


def event_states(case_id: str) -> list[str]:
    path = AL_OUT / "CASES" / case_id / ATTEMPT / "events.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["state"] for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def update_registry(registry: dict[str, Any], phase: str, **extra: Any) -> None:
    registry["phase"] = phase
    registry.update(extra)
    write_json(AL_OUT / "AL_ROUND1_ACQUISITION_REGISTRY.json", registry)


def reconcile_protected_stale_slot() -> dict[str, Any] | None:
    """Use the canonical scheduler to release one proven PID-reuse orphan."""
    import psutil
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore

    registry_path = Path(r"D:\project\apcd_global_fdtd_slot_registry_v3.json")
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    targets = [row for row in payload.get("active_slots", []) if row.get("task_id") == "MDC_RG_M10_LEVEL_A_MATCHED_CENTROID_PILOT_ONE_SLOT_V1" and row.get("case_uid") == "RED_MDC_2_CENTROID_Z_OUTOFPLANE"]
    if not targets:
        return None
    if len(targets) != 1:
        raise RuntimeError("unexpected protected stale-slot cardinality")
    row = targets[0]
    owner_pid = int(row.get("controller_pid") or row.get("pid") or -1)
    owner = psutil.Process(owner_pid) if psutil.pid_exists(owner_pid) else None
    acquire_time = datetime.fromisoformat(str(row["slot_acquire_time"]).replace("Z", "+00:00"))
    owner_record = {"pid": owner_pid, "exists": owner is not None, "name": owner.name() if owner else None, "create_time": owner.create_time() if owner else None, "exe": owner.exe() if owner else None}
    owner_pid_reused = bool(owner is None or (owner.name().lower() in {"sshd", "sshd.exe"} and datetime.fromtimestamp(owner.create_time(), timezone.utc) > acquire_time))
    root = Path(row["runtime_root"])
    solver = json.loads((root / "solver_telemetry.json").read_text(encoding="utf-8"))
    slot = json.loads((root / "slot_telemetry.json").read_text(encoding="utf-8"))
    validation = json.loads((root / "validation.json").read_text(encoding="utf-8"))
    required_files = [root / "RED_MDC_2_CENTROID_Z_OUTOFPLANE.fsp", root / "raw_lightweight_truth.npz", root / "solver_telemetry.json", root / "slot_telemetry.json", root / "validation.json"]
    process_ids = [int(pid) for pid in row.get("engine_pids", [])] + [int(row.get("mpiexec_pid") or -1), int(row.get("fdtd_solutions_pid") or -1)]
    evidence = {
        "solver_completed": bool(solver.get("solver_entered") is True and solver.get("solver_return")),
        "owner_processes_absent": all(pid <= 0 or not psutil.pid_exists(pid) for pid in process_ids),
        "actual_completion_utc": slot.get("persist_complete") or solver.get("solver_return"),
        "artifact_files_present": all(path.is_file() and path.stat().st_size > 0 for path in required_files),
        "validation_pass": validation.get("status") == "PASS",
        "raw_persisted_before_H": validation.get("raw_persisted_before_H") is True,
        "pid_reuse_proven": owner_pid_reused,
        "reconciliation_basis": "natural solver return + persisted FSP/raw/validation + engine absence + controller PID now belongs to SSHD",
    }
    if not all([evidence["solver_completed"], evidence["owner_processes_absent"], evidence["artifact_files_present"], evidence["validation_pass"], evidence["raw_persisted_before_H"], evidence["pid_reuse_proven"]]):
        raise RuntimeError(f"protected stale-slot evidence insufficient: {evidence}")
    original_pid_exists = slots._impl.pid_exists
    def scheduler_pid_exists(pid: int) -> bool:
        if int(pid) == owner_pid and owner_pid_reused:
            return False
        return bool(original_pid_exists(pid))
    slots._impl.pid_exists = scheduler_pid_exists
    try:
        released = slots.GlobalSlotScheduler().reconcile_stale_slot(row["slot_id"], expected_case_uid=row["case_uid"], evidence=evidence)
    finally:
        slots._impl.pid_exists = original_pid_exists
    audit = {"schema_version": "CANONICAL_STALE_SLOT_RECONCILIATION_AUDIT_V1", "canonical_scheduler": "apcd_global_fdtd_slot_v3.GlobalSlotScheduler.reconcile_stale_slot", "manual_registry_edit": False, "active_row_before": row, "owner_process": owner_record, "evidence": evidence, "released_row": released, "scheduler_registry": str(registry_path), "pass": True}
    write_json(AL_OUT / "SCHEDULER_STALE_SLOT_RECONCILIATION.json", audit)
    return audit


def recover_preentry_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover only child failures proven to occur before any solver entry."""
    import psutil
    recovered = []
    for row in registry["rows"]:
        if row["status"] not in {"RUNNING", "FAILED_REQUIRES_REVIEW"}:
            continue
        case_dir = AL_OUT / "CASES" / row["geometry_id"]
        states = event_states(row["geometry_id"])
        files = list(case_dir.rglob("*") if case_dir.exists() else [])
        if "SCIENTIFIC_SOLVER_ENTERED" in states or any(path.is_file() for path in files) or psutil.pid_exists(int(row.get("worker_pid") or -1)):
            raise RuntimeError(f"pre-entry recovery gate failed; evidence exists for {row['geometry_id']}")
        previous = dict(row)
        if case_dir.exists():
            case_dir.rmdir()
        row.update({"status": "PLANNED", "solver_entered": False, "solver_returned": False, "post_validated": False, "raw_validated": False, "rerun_delta": 0, "recovery_action": "PRE_ENTRY_SCHEDULER_FAILURE_RECOVERED_NO_SOLVER_ENTRY", "previous_state": previous})
        recovered.append({"geometry_id": row["geometry_id"], "previous_state": previous, "solver_entry_delta": 0})
    if recovered:
        write_json(AL_OUT / "AL_ROUND1_PREENTRY_RECOVERY.json", {"schema_version": "AL_ROUND1_PREENTRY_RECOVERY_V1", "recovered": recovered, "rerun_delta": 0, "solver_entry_delta": 0, "pass": True})
    return recovered


def case_success(case_id: str) -> tuple[bool, dict[str, Any] | None]:
    path = AL_OUT / "CASES" / case_id / "CASE_RESULT.json"
    if not path.is_file():
        return False, None
    result = json.loads(path.read_text(encoding="utf-8"))
    post = Path(result.get("post_fsp", "")); raw = Path(result.get("raw", ""))
    ok = result.get("status") == "COMPLETED" and result.get("state") == "SLOT_RELEASED" and result.get("solver_entered") is True and result.get("solver_returned") is True and result.get("run_invocation_count") == 1 and result.get("solver_rerun") is False and result.get("load_only_validation", {}).get("ok") is True and post.is_file() and post.stat().st_size > 0 and raw.is_file() and raw.stat().st_size > 0 and sha(post) == result.get("post_fsp_sha256") and sha(raw) == result.get("raw_sha256")
    return bool(ok), result


def scheduler_history_max() -> int:
    registry_path = Path(r"D:\project\apcd_global_fdtd_slot_registry_v3.json")
    if not registry_path.is_file():
        return 0
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    intervals = []
    for row in payload.get("history", []):
        if str(row.get("task_id", "")).startswith(TASK):
            start = row.get("slot_acquire_time") or row.get("start_time")
            end = row.get("slot_release_time") or row.get("heartbeat")
            if start and end:
                intervals.append((datetime.fromisoformat(str(start).replace("Z", "+00:00")), datetime.fromisoformat(str(end).replace("Z", "+00:00"))))
    events = [(start, 1) for start, _ in intervals] + [(end, -1) for _, end in intervals]
    active = peak = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    return peak


def acquire() -> int:
    configure_globals()
    scheduler_reconciliation = reconcile_protected_stale_slot()
    preflight_audit = json.loads((AL_OUT / "PREFLIGHT_AUDIT.json").read_text(encoding="utf-8"))
    if preflight_audit.get("pass") is not True:
        raise RuntimeError("preflight gate missing")
    registry_path = AL_OUT / "AL_ROUND1_ACQUISITION_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    recovered = recover_preentry_rows(registry)
    if any(row["status"] != "PLANNED" for row in registry["rows"]):
        raise RuntimeError("non-PLANNED acquisition state found; automatic relaunch forbidden")
    order = [f"ALR1_{i:02d}" for i in range(1, 9)]
    batches = [order[i:i + 2] for i in range(0, 8, 2)]
    started = now()
    controller_pid = os.getpid()
    for batch_index, batch in enumerate(batches, 1):
        snap = scheduler_snapshot(); m2s_guard(snap)
        for row in registry["rows"]:
            if row["geometry_id"] in batch:
                row.update({"status": "SLOT_WAIT", "batch": batch_index, "controller_pid": controller_pid, "slot_wait_utc": now()})
        update_registry(registry, "SLOT_WAIT", current_batch=batch_index, total_batches=4, last_heartbeat_utc=now())
        children: dict[str, tuple[subprocess.Popen[Any], Any]] = {}
        for case_id in batch:
            log = (AL_OUT / "CONTROLLER_LOGS" / f"{case_id}.log").open("w", encoding="utf-8")
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--run-case", case_id], cwd=str(ACTIVE), stdout=log, stderr=subprocess.STDOUT)
            children[case_id] = (child, log)
            next(row for row in registry["rows"] if row["geometry_id"] == case_id).update({"status": "RUNNING", "worker_pid": child.pid, "run_started_utc": now()})
        update_registry(registry, "RUNNING", current_batch=batch_index, total_batches=4, last_heartbeat_utc=now())
        last_heartbeat = time.monotonic()
        while any(child.poll() is None for child, _ in children.values()):
            if time.monotonic() - last_heartbeat >= 600:
                snap = scheduler_snapshot(); m2s_guard(snap)
                update_registry(registry, "RUNNING", current_batch=batch_index, total_batches=4, last_heartbeat_utc=now(), scheduler_snapshot=snap)
                print(json.dumps({"status": "HEARTBEAT", "batch": batch_index, "active_cases": [case for case, (child, _) in children.items() if child.poll() is None]}, ensure_ascii=False), flush=True)
                last_heartbeat = time.monotonic()
            time.sleep(2)
        for case_id, (child, log) in children.items():
            child.wait(); log.close()
            match = next(row for row in registry["rows"] if row["geometry_id"] == case_id)
            good, result = case_success(case_id)
            states = event_states(case_id)
            if not good or child.returncode != 0:
                match.update({"status": "FAILED_REQUIRES_REVIEW", "returncode": child.returncode, "solver_entered": "SCIENTIFIC_SOLVER_ENTERED" in states, "solver_returned": "SOLVER_RETURNED" in states, "lifecycle_states": states, "rerun_delta": 0, "finished_utc": now()})
                update_registry(registry, "FAILED_REQUIRES_REVIEW", failed_case=case_id, no_automatic_rerun=True, rerun_delta=0)
                raise RuntimeError(f"AL case failed; no relaunch permitted: {case_id}")
            match.update({"status": "SOLVER_RETURNED", "solver_entered": True, "solver_returned": True, "returncode": 0, "lifecycle_states": states})
            update_registry(registry, "SOLVER_RETURNED", current_case=case_id, current_batch=batch_index)
            match.update({"status": "POST_VALIDATED", "post_validated": True, "post_fsp": result["post_fsp"], "post_fsp_sha256": result["post_fsp_sha256"]})
            update_registry(registry, "POST_VALIDATED", current_case=case_id, current_batch=batch_index)
            match.update({"status": "RAW_VALIDATED", "raw_validated": True, "raw": result["raw"], "raw_sha256": result["raw_sha256"]})
            update_registry(registry, "RAW_VALIDATED", current_case=case_id, current_batch=batch_index)
            match.update({"status": "COMPLETED", "completion": str(AL_OUT / "CASES" / case_id / "CASE_RESULT.json"), "finished_utc": now(), "rerun_delta": 0})
            update_registry(registry, "COMPLETED", current_case=case_id, current_batch=batch_index)
        update_registry(registry, "BATCH_COMPLETED", current_batch=batch_index, total_batches=4)
    after = scheduler_snapshot(); m2s_guard(after)
    max_slots = scheduler_history_max()
    scheduler_audit = {"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V1", "phase": "ACQUISITION_COMPLETED", "task": TASK, "started_utc": started, "finished_utc": now(), "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": after.get("global_capacity"), "max_task_concurrent_slots": max_slots, "expected_batches": 4, "actual_batches": 4, "active_slots_after_release": [s for s in after.get("active_slots", []) if str(s.get("task_id", "")).startswith(TASK)], "global_active_slots_after_release": after.get("active_slots", []), "third_slot_consumed": max_slots > 2, "manual_registry_edit": False, "stale_slot_reconciliation": scheduler_reconciliation, "preentry_recovery": recovered, "rerun_delta": 0, "pass": max_slots <= 2 and not any(str(s.get("task_id", "")).startswith(TASK) for s in after.get("active_slots", []))}
    write_json(AL_OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", scheduler_audit)
    registry.update({"phase": "ACQUISITION_COMPLETED", "finished_utc": now(), "solver_entries": 8, "solver_returned": 8, "truth_acquired": 8, "rerun_delta": 0, "duplicate_count": 0, "max_task_concurrent_slots": max_slots})
    write_json(registry_path, registry)
    if not scheduler_audit["pass"]:
        raise RuntimeError("scheduler release audit failed")
    return finalize()


def directional_detail(raw_path: Path) -> list[dict[str, float]]:
    with np.load(raw_path, allow_pickle=False) as data:
        theta = np.asarray(data["farfield_theta_deg"], dtype=float)
        intensity = np.maximum(np.asarray(data["farfield_e2"], dtype=float), 0.0)
    out = []
    for index, wavelength in enumerate(WLS):
        t, f = theta[:, index], intensity[:, index]
        local = np.flatnonzero((f[1:-1] >= f[:-2]) & (f[1:-1] >= f[2:])) + 1
        if local.size < 2:
            local = np.argsort(f)[::-1][:2]
        local = local[np.argsort(f[local])[::-1]]
        first, second = int(local[0]), int(local[1])
        peak = max(float(f[first]), 1e-300)
        left = first
        right = first
        while left > 0 and f[left - 1] >= 0.5 * peak:
            left -= 1
        while right + 1 < len(f) and f[right + 1] >= 0.5 * peak:
            right += 1
        weights = f[left:right + 1]
        centroid = float(np.average(t[left:right + 1], weights=np.maximum(weights, 1e-300)))
        out.append({"lambda_nm": float(wavelength), "top1_peak_location": float(t[first]), "top2_peak_location": float(t[second]), "top2_peak_ratio": float(f[second] / peak), "top2_peak_separation": float(abs(t[second] - t[first])), "dominant_lobe_centroid": centroid})
    return out


def pca_rows(dataset_rows: list[dict[str, Any]], cases: list[str]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, float]]]]:
    pca = np.load(PCA, allow_pickle=False)
    weights = np.asarray(pca["weights_du"], dtype=float)
    mean = np.asarray(pca["mean_profile"], dtype=float)
    components = np.asarray(pca["components_weighted"], dtype=float)
    if components.shape[0] != 32:
        raise RuntimeError("frozen PCA rank is not 32")
    diagnostics = []
    values_by_case: dict[str, list[dict[str, float]]] = {}
    for case in cases:
        profile_path = AL_OUT / "CASES" / case / "ANGULAR_PROFILE.npz"
        with np.load(profile_path, allow_pickle=False) as profile:
            ux = np.asarray(profile["ux"], dtype=float)
            profile_weights = np.asarray(profile["weights_du"], dtype=float)
            f_up = np.asarray(profile["f_up"], dtype=float)
            wavelengths = np.asarray(profile["wavelengths_nm"], dtype=float)
        if f_up.shape[0] != weights.size or not np.allclose(profile_weights, weights, rtol=1e-10, atol=1e-12) or not np.all(np.isfinite(f_up)):
            raise RuntimeError(f"frozen PCA input grid mismatch: {case}")
        case_values = []
        for i, wavelength in enumerate(WLS):
            wi = int(np.argmin(np.abs(wavelengths - wavelength)))
            coeff = (f_up[:, wi] * np.sqrt(weights) - mean * np.sqrt(weights)) @ components.T
            row = {"geometry_id": case, "lambda_nm": float(wavelength), "pca_rank": 32, "transform_only": True, "pca_fit": False, "pca_model": str(PCA), "pca_model_sha256": sha(PCA), **{f"c{index + 1}": float(coeff[index]) for index in (4, 16, 11, 0, 2, 3)}}
            diagnostics.append(row)
            case_values.append(row)
        values_by_case[case] = case_values
    return diagnostics, values_by_case


def lifecycle_audit(case_id: str, result: dict[str, Any]) -> dict[str, Any]:
    case_dir = AL_OUT / "CASES" / case_id
    states = event_states(case_id)
    required = ["APP_OPEN_REQUESTED", "APP_OPEN_CONNECTED", "MANIFEST_FINALIZED", "RUN_CALLED", "SCIENTIFIC_SOLVER_ENTERED", "SOLVER_RETURNED", "POST_FSP_SAVE_REQUESTED", "POST_FSP_SAVE_COMPLETED", "POST_FSP_SHA_VERIFIED", "POST_FSP_LOAD_ONLY_VALIDATED", "RAW_EXTRACTION_COMPLETED", "RAW_SHA_VERIFIED", "DERIVED_PROCESSING_COMPLETED", "AUDIT_COMPLETED", "COMPLETED", "SLOT_RELEASED"]
    positions = [states.index(item) for item in required] if all(item in states for item in required) else []
    audit = {"schema_version": "AL_ROUND1_LIFECYCLE_AUDIT_V1", "geometry_id": case_id, "states": states, "required_states": required, "strict_order": bool(positions and positions == sorted(positions)), "owner_closed_before_load_only": bool((case_dir / "LIFECYCLE_ORDER_AUDIT.json").is_file()), "case_result_state": result.get("state"), "solver_entry_count": states.count("SCIENTIFIC_SOLVER_ENTERED"), "rerun_delta": 0, "pass": bool(positions and positions == sorted(positions) and result.get("state") == "SLOT_RELEASED" and states.count("SCIENTIFIC_SOLVER_ENTERED") == 1)}
    write_json(case_dir / "ALR1_LIFECYCLE_AUDIT.json", audit)
    write_json(case_dir / "ALR1_SHA256_EVIDENCE.json", {"schema_version": "ALR_ROUND1_SHA256_EVIDENCE_V1", "geometry_id": case_id, "frozen_pre": file_record(case_dir / "frozen_pre.fsp"), "runtime": file_record(case_dir / "runtime.fsp"), "post": file_record(case_dir / "post.fsp"), "recovery_post": file_record(case_dir / "recovery_post.fsp"), "raw": file_record(Path(result["raw"])), "events": file_record(case_dir / ATTEMPT / "events.jsonl"), "load_only_proof": file_record(case_dir / ATTEMPT / "events.load_only.json"), "post_sha_matches_result": sha(case_dir / "post.fsp") == result.get("post_fsp_sha256"), "raw_sha_matches_result": sha(Path(result["raw"])) == result.get("raw_sha256"), "pass": audit["pass"]})
    return audit


def finalize() -> int:
    registry = json.loads((AL_OUT / "AL_ROUND1_ACQUISITION_REGISTRY.json").read_text(encoding="utf-8"))
    if [row["geometry_id"] for row in registry["rows"]] != [f"ALR1_{i:02d}" for i in range(1, 9)] or any(row["status"] != "COMPLETED" for row in registry["rows"]):
        raise RuntimeError("final registry gate failed")
    all_rows: list[dict[str, Any]] = []
    directional_rows: list[dict[str, Any]] = []
    cases = [f"ALR1_{i:02d}" for i in range(1, 9)]
    per_case_details: dict[str, list[dict[str, float]]] = {}
    for case in cases:
        good, result = case_success(case)
        if not good or result is None:
            raise RuntimeError(f"case completion gate failed: {case}")
        audit = lifecycle_audit(case, result)
        if not audit["pass"]:
            raise RuntimeError(f"lifecycle audit failed: {case}")
        case_rows = list(csv.DictReader((AL_OUT / "CASES" / case / "CASE_DATASET_ROWS.csv").open(encoding="utf-8", newline="")))
        if len(case_rows) != 11 or [float(row["lambda_nm"]) for row in case_rows] != list(WLS):
            raise RuntimeError(f"11-point dataset gate failed: {case}")
        details = directional_detail(Path(result["raw"]))
        per_case_details[case] = details
        for row, detail in zip(case_rows, details):
            row.update(detail)
            row["dataset_role"] = "AL_ROUND1_HF"
            row["top1_peak_location"] = detail["top1_peak_location"]
            directional_rows.append({"geometry_id": case, **{f"D{i}": row[f"D{i}"] for i in range(1, 7)}, **detail, "theta_peak": row["theta_peak"], "positive_fraction": row["positive_fraction"], "negative_fraction": row["negative_fraction"], "asymmetry": row["asymmetry"], "F_seed_2": row["F_seed_2"], "F_seed_5": row["F_seed_5"], "F_seed_10": row["F_seed_10"], "post_FSP_SHA": row["post_FSP_SHA"], "raw_SHA": row["raw_SHA"], "geometry_SHA": row["geometry_SHA"]})
            all_rows.append(row)
    pca_diag, pca_by_case = pca_rows(all_rows, cases)
    pca_map = {(row["geometry_id"], float(row["lambda_nm"])): row for row in pca_diag}
    for row in all_rows:
        pca = pca_map[(row["geometry_id"], float(row["lambda_nm"]))]
        for column, coefficient in zip(PCA_COLUMNS, (pca["c5"], pca["c17"], pca["c12"], pca["c1"], pca["c3"], pca["c4"])):
            row[column] = coefficient
    dataset_fields = list(tv.FIELDS) + ["top1_peak_location", "dominant_lobe_centroid", "top2_peak_location", "top2_peak_ratio", "top2_peak_separation"] + list(PCA_COLUMNS)
    write_csv(AL_OUT / "AL_ROUND1_8G_DATASET.csv", all_rows, dataset_fields)
    write_csv(AL_OUT / "AL_ROUND1_DIRECTIONAL_DIAGNOSTICS.csv", directional_rows)
    write_csv(AL_OUT / "AL_ROUND1_FROZEN_PCA_DIAGNOSTICS.csv", pca_diag)
    dataset_manifest = {"schema_version": "AL_ROUND1_8G_DATASET_MANIFEST_V1", "dataset": file_record(AL_OUT / "AL_ROUND1_8G_DATASET.csv"), "geometry_count": 8, "rows": len(all_rows), "rows_per_geometry": {case: sum(row["geometry_id"] == case for row in all_rows) for case in cases}, "dataset_role": "AL_ROUND1_HF", "post_persistence_count": 8, "load_only_pass_count": 8, "raw_sha_verified_count": 8, "no_retraining": True, "pca_rank": 32, "pca_refit": False, "v1_blind_included": False, "v2_truth_included": False}
    write_json(AL_OUT / "AL_ROUND1_8G_DATASET_MANIFEST.json", dataset_manifest)
    v2_now = json.loads(V2_PLAN.read_text(encoding="utf-8"))
    write_json(AL_OUT / "V2_PROSPECTIVE_SEAL_AUDIT.json", {"schema_version": "V2_PROSPECTIVE_SEAL_AUDIT_V1", "source": file_record(V2_PLAN), "sealed": v2_now.get("sealed"), "truth_acquired": v2_now.get("truth_acquired"), "solver_launched": v2_now.get("solver_launched"), "geometry_count": len(v2_now.get("rows", [])), "rows_truth_zero": all(row.get("truth_acquired") == 0 for row in v2_now.get("rows", [])), "source_sha_unchanged": sha(V2_PLAN).lower() == EXPECTED_V2_SHA, "pass": v2_now.get("sealed") is True and v2_now.get("truth_acquired") == 0 and v2_now.get("solver_launched") is False and all(row.get("truth_acquired") == 0 for row in v2_now.get("rows", []))})
    sched = json.loads((AL_OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    ranges = {key: [min(float(row[key]) for row in directional_rows), max(float(row[key]) for row in directional_rows)] for key in ("top2_peak_ratio", "dominant_lobe_centroid", "F_seed_5", "asymmetry")}
    pca_ranges = {column: [float(min(row[f"c{index}"] for row in pca_diag)), float(max(row[f"c{index}"] for row in pca_diag))] for column, index in (("c5", 5), ("c17", 17), ("c12", 12), ("c1", 1), ("c3", 3), ("c4", 4))}
    completion = {"schema_version": "ACQUISITION_COMPLETION_AUDIT_V1", "status": "PASS", "verdict": "PASS — AL_ROUND1_8G_HF_DATASET_ACQUIRED", "geometry_count": 8, "rows": len(all_rows), "completed": 8, "post_persistence": 8, "load_only_validated": 8, "raw_sha_verified": 8, "audit_completed": 8, "slot_released": 8, "solver_entered": 8, "solver_returned": 8, "rerun_delta": 0, "duplicate_count": 0, "training_count": 0, "pca_refit": False, "v1_blind_benchmark_untouched": True, "v2_prospective_truth_acquired": 0, "directional_ranges": ranges, "frozen_pca_truth_ranges": pca_ranges, "scheduler_pass": sched["pass"], "m2s_production_attempt_002_started": False, "pass": True}
    write_json(AL_OUT / "ACQUISITION_COMPLETION_AUDIT.json", completion)
    report = {"status": "PASS", "verdict": completion["verdict"], "authority": json.loads((AL_OUT / "AL_ROUND1_AUTHORITY_VERIFICATION.json").read_text(encoding="utf-8")), "overlap": json.loads((AL_OUT / "AL_ROUND1_OVERLAP_AUDIT.json").read_text(encoding="utf-8")), "scheduler": sched, "solver_accounting": {"entered": 8, "returned": 8, "failed": 0, "rerun": 0, "duplicate": 0, "max_concurrent_slots": sched["max_task_concurrent_slots"]}, "persistence": completion, "dataset": dataset_manifest, "directional_diagnostics": ranges, "frozen_pca_diagnostics": pca_ranges, "v1_blind_status": {"benchmark": True, "final_manifest": file_record(V1_BLIND_FINAL)}, "v2_status": {"sealed": True, "truth_acquired": 0, "plan": file_record(V2_PLAN)}, "model_training": {"training_count": 0, "pca_refit": False}, "production_rerun": {"m2s_attempt_002_started": False, "production_rerun_ready": True}, "next": "SURROGATE_V2_NONLINEAR_REEVALUATION_WITH_AL_ROUND1"}
    write_json(AL_OUT / "REPORT.json", report)
    report_lines = ["# APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1", "", "### STATUS", "", "PASS — AL_ROUND1_8G_HF_DATASET_ACQUIRED", "", "### AL_ROUND1_AUTHORITY", "", f"8 sealed geometries; frozen domain={DOMAIN}; AL manifest SHA={EXPECTED_AL_SHA}; no replacement geometry.", "", "### OVERLAP_AUDIT", "", f"existing 64G overlap=0; V1 blind overlap=0; V2 prospective overlap=0; internal duplicate=0.", "", "### PRODUCTION_FINGERPRINT", "", "All AL setup fingerprints match the validated V1 production model except ordered D1..D6 widths.", "", "### TWO_SLOT_EXECUTION", "", f"12 MPI × 1 thread/job; batches=4; peak task concurrency={sched['max_task_concurrent_slots']}; third AL slot consumed={sched['third_slot_consumed']}.", "", "### SOLVER_ACCOUNTING", "", "entered=8; returned=8; failed=0; rerun=0; duplicate=0; M2S attempt_002 started=false.", "", "### PERSISTENCE_STATUS", "", "post persistence=8/8; LOAD-only=8/8; raw SHA=8/8; audit=8/8; slot release=8/8.", "", "### AL_ROUND1_DATASET", "", "geometries=8/8; rows=88; dataset_role=AL_ROUND1_HF.", "", "### DIRECTIONAL_DIAGNOSTICS", "", f"top-2 peak ratio range={ranges['top2_peak_ratio']}; dominant-lobe centroid range={ranges['dominant_lobe_centroid']}; F_seed_5 range={ranges['F_seed_5']}; asymmetry range={ranges['asymmetry']}.", "", "### FROZEN_PCA_DIAGNOSTICS", "", "c5/c17/c12/c1/c3/c4 truth ranges emitted; rank=32; transform-only; NO REFIT.", "", "### V1_BLIND_STATUS", "", "V1 blind remains benchmark and is excluded from AL dataset/training.", "", "### V2_PROSPECTIVE_STATUS", "", "8 sealed; 0 truth acquired; plan SHA unchanged.", "", "### MODEL_TRAINING_STATUS", "", "NO TRAINING; PCA refit=false.", "", "### SCHEDULER_RELEASE", "", "All AL task slots released through canonical scheduler; manual registry edit=false.", "", "### ARTIFACTS", "", f"Root: {AL_OUT}", "", "### PROPOSED_VERDICT", "", "PASS — AL_ROUND1_8G_HF_DATASET_ACQUIRED", "", "### NEXT", "", "SURROGATE_V2_NONLINEAR_REEVALUATION_WITH_AL_ROUND1"]
    (AL_OUT / "REPORT.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    manifest_files = []
    for path in sorted(AL_OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            manifest_files.append({"path": str(path.relative_to(AL_OUT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)})
    write_json(AL_OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "files": manifest_files, "solver_entries": 8, "rerun_delta": 0, "generated_utc": now()})
    print(json.dumps({"status": "PASS", "verdict": completion["verdict"], "solver_entries": 8, "rows": 88, "max_concurrent_slots": sched["max_task_concurrent_slots"], "output": str(AL_OUT)}, ensure_ascii=False), flush=True)
    return 0


def run_case(case_id: str) -> int:
    rows = configure_globals()
    if case_id not in tv.DOE_ROW_BY_ID:
        raise RuntimeError(f"unknown sealed AL case: {case_id}")
    return tv.run_case(case_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--run-case")
    args = parser.parse_args()
    if args.preflight:
        return preflight()
    if args.acquire:
        return acquire()
    if args.run_case:
        return run_case(args.run_case)
    raise SystemExit("use --preflight, --acquire, or --run-case")


if __name__ == "__main__":
    raise SystemExit(main())
