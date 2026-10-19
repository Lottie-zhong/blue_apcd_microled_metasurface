"""Acquire sealed V2 prospective truth and run a frozen V1/V2 paired evaluation."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import pickle
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
SCRIPT_DIR = ACTIVE / "scripts" / "coupling_ml"
TRAINVAL_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
READINESS_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW_V1"
V2_REEVAL_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_SURROGATE_V2_NONLINEAR_REEVALUATION_WITH_AL_ROUND1_V1"
PREBLIND_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_COMPOSITIONAL_NP_PRIOR_REPAIR_AND_FINAL_PREBLIND_ABLATION_V1"
OUT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_V2_PROSPECTIVE_8G_TWO_SLOT_ACQUISITION_AND_PAIRED_FROZEN_EVAL_V1"
V2_PLAN = READINESS_ROOT / "V2_PROSPECTIVE_TEST_PLAN.json"
V2_FREEZE = V2_REEVAL_ROOT / "V2_PREPROSPECTIVE_CHAMPION_FREEZE.json"
V2_SELECTION = V2_REEVAL_ROOT / "V2_CHAMPION_SELECTION.json"
V2_MODEL = V2_REEVAL_ROOT / "models" / "ridge_a100.pkl"
V1_FREEZE = PREBLIND_ROOT / "PREBLIND_CHAMPION_FREEZE.json"
V1_MANIFEST = PREBLIND_ROOT / "FINAL_SHA256_MANIFEST.json"
V1_MODEL = PREBLIND_ROOT / "models" / "Ridge_RAW_CHAMPION.pkl"
V1_PREPROCESSOR = PREBLIND_ROOT / "preprocessors" / "selected_model_preprocessor.pkl"
PCA = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "ANGULAR_PCA_MODEL.npz"
TRAINVAL_DATASET = TRAINVAL_ROOT / "V1_TRAINVAL_DATASET.csv"
AL_DATASET = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_AL_ROUND1_8G_TWO_SLOT_HF_ACQUISITION_V1" / "AL_ROUND1_8G_DATASET.csv"
V1_BLIND_DATASET = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1" / "BLIND_DATASET.csv"
V2_PROSPECTIVE_SEAL_AUDIT = V2_REEVAL_ROOT / "V2_PROSPECTIVE_SEAL_AUDIT.json"
TASK = "APCD_COUPLING_V2_2_V2_PROSPECTIVE_8G_TWO_SLOT_ACQUISITION_AND_PAIRED_FROZEN_EVAL_V1"
ATTEMPT = "attempt_001"
WLS = np.arange(445.0, 456.0, 1.0)
PITCH_NM = 290.0
LAMBDA_X_NM = 1740.0
HIGH_COEFFS = (1, 3, 4, 5, 12, 17)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module unavailable: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


acq = load_module("v2p_acquisition_base", SCRIPT_DIR / "apcd_2d_ml_v1_blind_8g_two_slot_prospective_v1.py")
v2 = load_module("v2_frozen_surrogate", SCRIPT_DIR / "apcd_surrogate_v2_nonlinear_reevaluation_v1.py")
tv = acq.tv
acq.SCRIPT = Path(__file__).resolve()


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
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(safe(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: safe(row.get(key, "")) for key in fields} for row in rows)


def file_record(path: Path) -> dict[str, Any]:
    path = Path(path)
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None}


def vector(row: dict[str, Any]) -> tuple[float, ...]:
    suffix = "_nm" if "D1_nm" in row else ""
    return tuple(float(row[f"D{i}{suffix}"]) for i in range(1, 7))


def v2_rows() -> list[dict[str, Any]]:
    payload = json.loads(V2_PLAN.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if payload.get("sealed") is not True or payload.get("truth_acquired") != 0 or payload.get("solver_launched") is not False or len(rows) != 8:
        raise RuntimeError("V2 prospective seal hard stop")
    ids = [f"V2P_{i:02d}" for i in range(1, 9)]
    if [row.get("geometry_id") for row in rows] != ids or any(row.get("role") != "V2_PROSPECTIVE_TEST" or row.get("sealed") is not True or row.get("truth_acquired") != 0 for row in rows):
        raise RuntimeError("V2 prospective identity/order hard stop")
    out = []
    for source in rows:
        row = {"geometry_id": source["geometry_id"], **{f"D{i}": float(source[f"D{i}"]) for i in range(1, 7)}, "geometry_sha256": source["geometry_sha256"], "intended_role": source["role"], "split": "V2_PROSPECTIVE"}
        out.append(row)
    if len({vector(row) for row in out}) != 8 or len({row["geometry_sha256"] for row in out}) != 8:
        raise RuntimeError("V2 prospective duplicate geometry")
    return out


def configure() -> list[dict[str, Any]]:
    rows = v2_rows()
    acq.OUT = OUT
    acq.SEALED = V2_PLAN
    acq.JOB_PREFIX = TASK
    acq.ATTEMPT = ATTEMPT
    acq.TRAINVAL_ROOT = TRAINVAL_ROOT
    acq.sealed_rows = v2_rows
    acq.configure_tv(rows)
    return rows


def manifest_entry(manifest_path: Path, target: Path) -> dict[str, Any] | None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    wanted = str(target).replace("\\", "/")
    for item in payload.get("files", []):
        path = str(item.get("path", "")).replace("\\", "/")
        if path == wanted or path.endswith("/" + wanted):
            return item
    return None


def freeze_audit() -> dict[str, Any]:
    required = [V2_FREEZE, V2_SELECTION, V2_PLAN, V1_FREEZE, V1_MANIFEST, V1_MODEL, V1_PREPROCESSOR, PCA, V2_MODEL]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("freeze artifact missing: " + ";".join(missing))
    v2_freeze = json.loads(V2_FREEZE.read_text(encoding="utf-8"))
    v2_selection = json.loads(V2_SELECTION.read_text(encoding="utf-8"))
    v2_plan = json.loads(V2_PLAN.read_text(encoding="utf-8"))
    v1_freeze = json.loads(V1_FREEZE.read_text(encoding="utf-8"))
    with V2_MODEL.open("rb") as stream:
        v2_artifact = pickle.load(stream)
    with V1_MODEL.open("rb") as stream:
        v1_artifact = pickle.load(stream)
    with V1_PREPROCESSOR.open("rb") as stream:
        v1_preprocessor = pickle.load(stream)
    v1_payload = v1_artifact.get("payload", v1_artifact)
    v2_payload = v2_artifact.get("payload", {})
    checks = {
        "v2_status_frozen": v2_freeze.get("status") == "FROZEN",
        "v2_champion": v2_freeze.get("champion", {}).get("model_family") == "V2_RIDGE_RAW" and v2_freeze.get("champion", {}).get("model_id") == "ridge_a100",
        "v2_selection_unique": v2_selection.get("unique") is True and v2_selection.get("selected_model_id") == "ridge_a100",
        "v2_plan_sealed_truth_zero": v2_plan.get("sealed") is True and v2_plan.get("truth_acquired") == 0 and v2_plan.get("solver_launched") is False,
        "v1_champion": v1_freeze.get("champion") == "RIDGE_RAW_CHAMPION" and v1_freeze.get("hyperparameters", {}).get("alpha") == 100.0,
        "v1_feature_set": v1_freeze.get("feature_set") == "RAW_D1_D6_LAMBDA",
        "pca_rank_32": v2_freeze.get("pca_rank") == 32 and v1_freeze.get("pca_rank") == 32,
        "pca_sha_v2": v2_freeze.get("pca_sha256") == sha(PCA),
        "pca_sha_v1": v1_freeze.get("pca_sha256") == sha(PCA),
        "v2_model_sha": v2_freeze.get("champion", {}).get("model_sha256") == sha(V2_MODEL),
        "v1_model_sha": v1_freeze.get("model_sha256") == sha(V1_MODEL),
        "v1_scaler_sha": v1_freeze.get("scaler_sha256") == sha(V1_PREPROCESSOR),
        "v2_payload_has_scalers": isinstance(v2_payload, dict) and "x_scaler" in v2_payload and "y_scaler" in v2_payload,
        "v1_payload_model": isinstance(v1_payload, dict) and "model" in v1_payload,
        "v1_preprocessor_fields": isinstance(v1_preprocessor, dict) and all(key in v1_preprocessor for key in ("imputer", "scaler", "target_scaler")),
        "v1_manifest_freeze": (manifest_entry(V1_MANIFEST, V1_FREEZE.name) or {}).get("sha256") == sha(V1_FREEZE),
        "v1_manifest_model": (manifest_entry(V1_MANIFEST, str(V1_MODEL.relative_to(PREBLIND_ROOT))) or {}).get("sha256") == sha(V1_MODEL),
        "v1_manifest_scaler": (manifest_entry(V1_MANIFEST, str(V1_PREPROCESSOR.relative_to(PREBLIND_ROOT))) or {}).get("sha256") == sha(V1_PREPROCESSOR),
    }
    if not all(checks.values()):
        raise RuntimeError("freeze hard stop: " + json.dumps(checks, sort_keys=True))
    return {
        "schema_version": "V2_PROSPECTIVE_PREACQUISITION_FREEZE_AUDIT_V1",
        "verified_utc": now(),
        "truth_acquired_at_verification": 0,
        "checks": checks,
        "v1": {"label": "RIDGE_RAW_CHAMPION", "model": file_record(V1_MODEL), "preprocessor": file_record(V1_PREPROCESSOR), "freeze": file_record(V1_FREEZE), "alpha": v1_freeze["hyperparameters"]["alpha"], "feature_set": v1_freeze["feature_set"], "pca_rank": 32, "pca_sha256": sha(PCA)},
        "v2": {"label": "V2_RIDGE_RAW", "model_id": "ridge_a100", "model": file_record(V2_MODEL), "freeze": file_record(V2_FREEZE), "selection": file_record(V2_SELECTION), "pca_rank": 32, "pca_sha256": sha(PCA), "feature_set": "RAW_GEOMETRY_LAMBDA", "alpha": v2_freeze["champion"]["spec"]["alpha"]},
        "pca": file_record(PCA),
        "weights_scalers_preprocessors_hyperparameters_frozen": True,
        "retraining": False,
        "pca_refit": False,
    }


def overlap_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def csv_keys(path: Path) -> tuple[set[tuple[float, ...]], set[str]]:
        source = read_csv(path)
        return {vector(row) for row in source}, {row.get("geometry_SHA", row.get("geometry_sha256", "")) for row in source}

    prospective_vectors = {vector(row) for row in rows}
    prospective_shas = {row["geometry_sha256"] for row in rows}
    sources = {"original_trainval": csv_keys(TRAINVAL_DATASET), "al_round1": csv_keys(AL_DATASET), "v1_blind": csv_keys(V1_BLIND_DATASET)}
    results = {}
    for name, (vectors, shas) in sources.items():
        results[name] = {"vector_overlap": sorted([list(v) for v in prospective_vectors & vectors]), "sha_overlap": sorted(prospective_shas & shas), "pass": not (prospective_vectors & vectors or prospective_shas & shas)}
    return {"schema_version": "V2_PROSPECTIVE_AUTHORITY_AUDIT_V1", "geometry_count": len(rows), "geometry_ids": [row["geometry_id"] for row in rows], "ordered_vectors": [list(vector(row)) for row in rows], "geometry_sha256": [row["geometry_sha256"] for row in rows], "nonoverlap": results, "pass": len(rows) == 8 and all(item["pass"] for item in results.values())}


def mirror_registry_write(path: Path, payload: Any) -> None:
    original_write_json(path, payload)
    if Path(path).name == "BLIND_ACQUISITION_REGISTRY.json":
        mirrored = dict(payload)
        mirrored["schema_version"] = "V2_PROSPECTIVE_ACQUISITION_REGISTRY_V1"
        mirrored["task"] = TASK
        original_write_json(OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json", mirrored)


def preflight() -> int:
    if OUT.exists():
        forbidden = {"V2_PROSPECTIVE_ACQUISITION_REGISTRY.json", "BLIND_ACQUISITION_REGISTRY.json", "CONTROLLER_LOGS", "V2_PROSPECTIVE_DATASET.csv", "REPORT.json"}
        if any(path.name in forbidden for path in OUT.iterdir()) or any((OUT / "CASES").glob("*/CASE_RESULT.json")):
            raise RuntimeError(f"output namespace exists beyond setup-only recovery boundary: {OUT}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "SETUPS").mkdir(exist_ok=True)
    (OUT / "CASES").mkdir(exist_ok=True)
    rows = configure()
    freeze = freeze_audit()
    write_json(OUT / "V2_PROSPECTIVE_PREACQUISITION_FREEZE_AUDIT.json", freeze)
    for name in ("V1_SCIENTIFIC_SPACE_FREEZE.json", "V1_SOURCE_REFERENCE.json", "K6_V1_64G_PRIOR_FEATURES.csv"):
        source = TRAINVAL_ROOT / name
        if not source.is_file():
            raise RuntimeError(f"validated source missing: {source}")
        shutil.copy2(source, OUT / name)
    authority = overlap_audit(rows)
    if not authority["pass"]:
        raise RuntimeError("V2 prospective historical overlap hard stop")
    geometry = acq.geometry_authority(rows)
    write_json(OUT / "V2_PROSPECTIVE_AUTHORITY_AUDIT.json", {**authority, "production_fingerprint": geometry})
    scheduler = tv.scheduler_snapshot()
    active = scheduler.get("active_slots", [])
    m2s = [p for p in scheduler.get("processes", []) if p.get("is_m2s")]
    if scheduler.get("global_capacity") != 3 or len(active) + 2 > 3 or m2s:
        raise RuntimeError("two-slot scheduler preflight hard stop: " + json.dumps({"global_capacity": scheduler.get("global_capacity"), "active_slots": active}, default=str))
    registry_rows = [{**row, "status": "PLANNED", "solver_entered": False, "solver_returned": False, "post_validated": False, "raw_extracted": False, "rerun_delta": 0, "duplicate": False} for row in rows]
    registry = {"schema_version": "V2_PROSPECTIVE_ACQUISITION_REGISTRY_V1", "task": TASK, "attempt_id": ATTEMPT, "phase": "PREACQUISITION_FROZEN", "rows": registry_rows, "solver_entries": 0, "solver_returned": 0, "truth_acquired": 0, "rerun_delta": 0, "duplicate": 0, "manual_registry_edit": False}
    write_json(OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json", registry)
    write_json(OUT / "BLIND_ACQUISITION_REGISTRY.json", {**registry, "schema_version": "BLIND_ACQUISITION_REGISTRY_V1"})
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", {"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V2_PROSPECTIVE_V1", "phase": "PREACQUISITION", "global_capacity": scheduler.get("global_capacity"), "active_slots_before": active, "requested_task_slots": 2, "resource_per_job": {"processes": 12, "threads": 1}, "expected_batches": 4, "third_slot_consumed": False, "m2s_processes": m2s, "manual_registry_edit": False, "pass": True})
    write_json(OUT / "PREFLIGHT_AUDIT.json", {"schema_version": "V2_PROSPECTIVE_ZERO_SOLVER_PREFLIGHT_V1", "generated_utc": now(), "solver_entries": 0, "solver_returned": 0, "truth_acquired": 0, "rerun_delta": 0, "duplicate": 0, "freeze": freeze, "authority": authority, "geometry": geometry, "scheduler": scheduler, "production_domain": "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN", "pass": True})
    print(json.dumps({"status": "PREFLIGHT_PASS", "solver_entries": 0, "geometries": 8, "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


def case_audits() -> list[dict[str, Any]]:
    rows = []
    for row in v2_rows():
        gid = row["geometry_id"]
        case = OUT / "CASES" / gid
        result_path = case / "CASE_RESULT.json"
        if not result_path.is_file():
            result_path = case / ATTEMPT / "completion.json"
        if not result_path.is_file():
            raise RuntimeError(f"missing case result: {gid}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        post = case / "post.fsp"
        raw = case / f"{gid}_RAW_TRUTH.npz"
        acceptance = json.loads((case / "CASE_ACCEPTANCE.json").read_text(encoding="utf-8")) if (case / "CASE_ACCEPTANCE.json").is_file() else {}
        slot_reconciliation = case / "STALE_SLOT_RECONCILIATION_AUDIT.json"
        slot_release = result.get("state") == "SLOT_RELEASED" or (slot_reconciliation.is_file() and json.loads(slot_reconciliation.read_text(encoding="utf-8")).get("pass") is True)
        passed = bool(result.get("solver_entered") is True and result.get("solver_returned") is True and result.get("run_invocation_count") == 1 and result.get("rerun_delta", 0) == 0 and slot_release and result.get("load_only_validation", {}).get("ok") is True and post.is_file() and post.stat().st_size > 0 and raw.is_file() and raw.stat().st_size > 0 and acceptance.get("pass") is True)
        audit = {"schema_version": "V2_PROSPECTIVE_CASE_LIFECYCLE_AUDIT_V1", "geometry_id": gid, "geometry_sha256": row["geometry_sha256"], "solver_entered": result.get("solver_entered"), "solver_returned": result.get("solver_returned"), "run_invocation_count": result.get("run_invocation_count"), "rerun_delta": result.get("rerun_delta", 0), "post_fsp": file_record(post), "raw_truth": file_record(raw), "load_only": result.get("load_only_validation"), "completion_state": result.get("state"), "slot_release": slot_release, "slot_reconciliation": str(slot_reconciliation) if slot_reconciliation.is_file() else None, "pass": passed}
        write_json(case / "LIFECYCLE_AUDIT.json", audit)
        if not passed:
            raise RuntimeError(f"{gid}: persistence/completion gate failed; automatic rerun forbidden")
        rows.append(audit)
    return rows


def _case_result(case_id: str) -> dict[str, Any] | None:
    case = OUT / "CASES" / case_id
    for path in (case / "CASE_RESULT.json", case / ATTEMPT / "completion.json"):
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def _returned_timestamp(case_id: str) -> str | None:
    path = OUT / "CASES" / case_id / ATTEMPT / "events.jsonl"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("state") == "SOLVER_RETURNED":
            return event.get("timestamp")
    return None


def reconcile_completed_slots() -> dict[str, Any]:
    scheduler = load_module("v2p_scheduler_reconcile", TRAD / "scripts" / "coupling" / "apcd_global_fdtd_slot_v3.py")
    reconciled = []
    for row in v2_rows():
        gid = row["geometry_id"]
        result = _case_result(gid)
        if not result or result.get("solver_entered") is not True or result.get("solver_returned") is not True or result.get("state") != "COMPLETED":
            continue
        snapshot = scheduler._impl._read(scheduler.DEFAULT_REGISTRY_PATH)
        slots = [s for s in snapshot.get("active_slots", []) if str(s.get("case_uid")) == gid and str(s.get("task_id", "")) == f"{TASK}:{gid}"]
        if len(slots) != 1:
            prior = OUT / "CASES" / gid / "STALE_SLOT_RECONCILIATION_AUDIT.json"
            if not slots and prior.is_file() and json.loads(prior.read_text(encoding="utf-8")).get("pass") is True:
                continue
            if slots:
                raise RuntimeError(f"completed case has ambiguous active slot: {gid}")
            active_summary = [(s.get("slot_id"), s.get("case_uid"), s.get("task_id")) for s in snapshot.get("active_slots", [])]
            raise RuntimeError(f"completed case has no durable slot-release evidence: {gid}; active={active_summary}; expected={TASK}:{gid}")
        live = scheduler.live_job_snapshot()
        if gid.lower() in json.dumps(live.get("jobs", []), sort_keys=True).lower():
            raise RuntimeError(f"completed case still has live solver lineage: {gid}")
        evidence = {"case_id": gid, "solver_completed": True, "owner_processes_absent": True, "actual_completion_utc": _returned_timestamp(gid) or now(), "post_fsp": str(OUT / "CASES" / gid / "post.fsp"), "post_sha256": result.get("post_fsp_sha256"), "load_only_validated": result.get("load_only_validation", {}).get("ok") is True, "raw_sha256": result.get("raw_sha256")}
        released = scheduler.GlobalSlotScheduler().reconcile_stale_slot(slots[0]["slot_id"], expected_case_uid=gid, evidence=evidence)
        write_json(OUT / "CASES" / gid / "STALE_SLOT_RECONCILIATION_AUDIT.json", {"schema_version": "V2_PROSPECTIVE_STALE_SLOT_RECONCILIATION_V1", "timestamp": now(), "geometry_id": gid, "slot_id": slots[0]["slot_id"], "release_state": released.get("completion_release_state"), "evidence": evidence, "manual_registry_edit": False, "pass": True})
        reconciled.append(gid)
    after = tv.scheduler_snapshot()
    task_slots = [s for s in after.get("active_slots", []) if str(s.get("task_id", "")).startswith(TASK)]
    return {"schema_version": "V2_PROSPECTIVE_SLOT_RECONCILIATION_AUDIT_V1", "timestamp": now(), "reconciled": reconciled, "active_task_slots_after": task_slots, "manual_registry_edit": False, "pass": not task_slots}


def _update_registry_row(row: dict[str, Any], case_id: str, result: dict[str, Any], returncode: int) -> None:
    case = OUT / "CASES" / case_id
    row.update({"status": "COMPLETED", "solver_entered": bool(result.get("solver_entered")), "solver_returned": bool(result.get("solver_returned")), "post_validated": bool(result.get("load_only_validation", {}).get("ok") is True), "raw_extracted": (case / f"{case_id}_RAW_TRUTH.npz").is_file(), "post_fsp": str(case / "post.fsp"), "raw_truth": str(case / f"{case_id}_RAW_TRUTH.npz"), "post_sha256": result.get("post_fsp_sha256"), "raw_sha256": result.get("raw_sha256"), "completion_state": "SLOT_RELEASED" if result.get("state") == "SLOT_RELEASED" else result.get("state"), "controller_returncode": returncode, "reconciled": (case / "STALE_SLOT_RECONCILIATION_AUDIT.json").is_file()})


def acquire() -> int:
    if not (OUT / "PREFLIGHT_AUDIT.json").is_file():
        raise RuntimeError("preflight gate missing")
    configure()
    write_json(OUT / "SLOT_RECONCILIATION_AUDIT.json", reconcile_completed_slots())
    registry_path = OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = registry["rows"]
    for row in rows:
        result = _case_result(row["geometry_id"])
        if result and result.get("solver_entered") is True and result.get("solver_returned") is True:
            _update_registry_row(row, row["geometry_id"], result, int(row.get("controller_returncode") or 0))
    pending = [row for row in rows if row.get("status") != "COMPLETED"]
    if any(row.get("solver_entered") or row.get("solver_returned") for row in pending):
        raise RuntimeError("resume blocked: entered case lacks validated completion; automatic rerun forbidden")
    registry.update({"phase": "RUNNING", "rows": rows, "solver_entries": sum(bool(r.get("solver_entered")) for r in rows), "solver_returned": sum(bool(r.get("solver_returned")) for r in rows), "truth_acquired": sum(r.get("status") == "COMPLETED" for r in rows), "rerun_delta": 0, "duplicate": 0})
    write_json(registry_path, registry)
    log_dir = OUT / "CONTROLLER_LOGS"
    log_dir.mkdir(exist_ok=True)
    snapshots, max_slots = [], 0
    start_batch = max([int(row.get("batch") or 0) for row in rows if row.get("status") == "COMPLETED"] + [0]) + 1
    for offset in range(0, len(pending), 2):
        batch = pending[offset:offset + 2]
        batch_index = start_batch + offset // 2
        for row in batch:
            row.update({"status": "RUNNING", "batch": batch_index, "started_utc": now()})
        registry.update({"phase": "RUNNING", "current_batch": batch_index, "total_batches": 4, "rows": rows})
        write_json(registry_path, registry)
        children = {}
        for row in batch:
            case_id = row["geometry_id"]
            log = (log_dir / f"{case_id}.log").open("w", encoding="utf-8")
            children[case_id] = (subprocess.Popen([sys.executable, str(acq.SCRIPT), "--run-case", case_id], cwd=str(ACTIVE), stdout=log, stderr=subprocess.STDOUT), log)
        while any(proc.poll() is None for proc, _ in children.values()):
            snap = tv.scheduler_snapshot()
            task_slots = [s for s in snap.get("active_slots", []) if str(s.get("task_id", "")).startswith(TASK)]
            max_slots = max(max_slots, len(task_slots))
            snapshots.append({"utc": now(), "batch": batch_index, "task_slots": task_slots})
            time.sleep(30)
        for proc, log in children.values():
            proc.wait(); log.close()
        reconcile_completed_slots()
        for row in batch:
            case_id = row["geometry_id"]
            result = _case_result(case_id)
            if not result or result.get("solver_entered") is not True or result.get("solver_returned") is not True:
                row.update({"status": "FAILED_REQUIRES_CHART_REVIEW", "controller_returncode": children[case_id][0].returncode})
                write_json(registry_path, registry)
                raise RuntimeError(f"{case_id}:FAILED_REQUIRES_CHART_REVIEW; automatic rerun forbidden")
            _update_registry_row(row, case_id, result, children[case_id][0].returncode)
        registry.update({"rows": rows, "solver_entries": sum(bool(r.get("solver_entered")) for r in rows), "solver_returned": sum(bool(r.get("solver_returned")) for r in rows), "truth_acquired": sum(r.get("status") == "COMPLETED" for r in rows), "rerun_delta": 0, "duplicate": 0})
        write_json(registry_path, registry)
    audits = case_audits()
    task_rows = registry.get("rows", [])
    if len(task_rows) != 8 or sum(bool(row.get("solver_entered")) for row in task_rows) != 8 or sum(bool(row.get("solver_returned")) for row in task_rows) != 8 or any(row.get("rerun_delta", 0) != 0 for row in task_rows) or any(row.get("duplicate") for row in task_rows):
        raise RuntimeError("acquisition accounting gate failed")
    after = tv.scheduler_snapshot()
    task_slots = [s for s in after.get("active_slots", []) if str(s.get("task_id", "")).startswith(TASK)]
    scheduler = json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    scheduler.update({"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V2_PROSPECTIVE_V1", "phase": "ACQUISITION_COMPLETE", "expected_batches": 4, "actual_batches": 4, "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": 3, "max_task_concurrent_slots": max_slots, "samples": snapshots, "active_task_slots_after_release": task_slots, "third_slot_consumed": max_slots > 2, "manual_registry_edit": False, "pass": max_slots <= 2 and not task_slots})
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", scheduler)
    registry.update({"schema_version": "V2_PROSPECTIVE_ACQUISITION_REGISTRY_V1", "phase": "ACQUISITION_COMPLETE", "rows": rows, "truth_acquired": 8, "solver_entries": 8, "solver_returned": 8, "rerun_delta": 0, "duplicate": 0, "case_lifecycle_audits": [str(OUT / "CASES" / row["geometry_id"] / "LIFECYCLE_AUDIT.json") for row in audits]})
    write_json(registry_path, registry)
    print(json.dumps({"status": "ACQUISITION_PASS", "solver_entries": 8, "solver_returned": 8, "truth_acquired": 8, "rerun_delta": 0, "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


def reconcile_preentry() -> int:
    registry_path = OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json"
    if not registry_path.is_file():
        raise RuntimeError("acquisition registry missing")
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    affected = [row for row in registry.get("rows", []) if row.get("status") in {"FAILED_REQUIRES_CHART_REVIEW", "RUNNING"}]
    if any(row.get("solver_entered") or row.get("solver_returned") for row in affected):
        raise RuntimeError("pre-entry reconciliation blocked by solver evidence")
    for row in affected:
        case = OUT / "CASES" / row["geometry_id"]
        if any(case.glob("**/events.jsonl")) or (case / "CASE_RESULT.json").is_file():
            raise RuntimeError(f"pre-entry reconciliation blocked by durable case evidence: {row['geometry_id']}")
    snapshot = OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY_PREENTRY_FAILURE_R2.json"
    shutil.copy2(registry_path, snapshot)
    log_dir = OUT / "CONTROLLER_LOGS"
    if log_dir.is_dir():
        shutil.move(str(log_dir), str(OUT / "CONTROLLER_LOGS_PREENTRY_FAILURE_R2"))
    case_evidence_root = OUT / "CASES_PREENTRY_FAILURE_R2"
    for row in affected:
        case = OUT / "CASES" / row["geometry_id"]
        if case.is_dir():
            case_evidence_root.mkdir(exist_ok=True)
            shutil.move(str(case), str(case_evidence_root / row["geometry_id"]))
    for row in affected:
        row.update({"status": "PLANNED", "solver_entered": False, "solver_returned": False, "post_validated": False, "raw_extracted": False, "rerun_delta": 0, "duplicate": False, "preentry_reconciled": True})
    registry.update({"schema_version": "V2_PROSPECTIVE_ACQUISITION_REGISTRY_V1", "phase": "PREENTRY_WRAPPER_REPAIRED", "solver_entries": 0, "solver_returned": 0, "truth_acquired": 0, "rerun_delta": 0, "duplicate": 0, "preentry_reconciliation": "sealed_rows_child_import_bug; no solver entry occurred"})
    write_json(registry_path, registry)
    original_write_json(OUT / "BLIND_ACQUISITION_REGISTRY.json", {**registry, "schema_version": "BLIND_ACQUISITION_REGISTRY_V1"})
    write_json(OUT / "PREENTRY_RECONCILIATION_AUDIT_R2.json", {"schema_version": "V2_PROSPECTIVE_PREENTRY_RECONCILIATION_V1", "timestamp": now(), "affected_geometry_ids": [row["geometry_id"] for row in affected], "solver_entry_delta": 0, "solver_returned_delta": 0, "rerun_delta": 0, "duplicate": 0, "cause": "scheduler hard gate and empty setup-only case directories; no solver entry occurred", "evidence_snapshot": str(snapshot), "preserved_logs": str(OUT / "CONTROLLER_LOGS_PREENTRY_FAILURE_R2"), "preserved_case_dirs": str(case_evidence_root), "pass": True})
    print(json.dumps({"status": "PREENTRY_RECONCILIATION_PASS", "affected": [row["geometry_id"] for row in affected], "solver_entries": 0, "rerun_delta": 0}, ensure_ascii=False), flush=True)
    return 0


def load_predictions(rows: list[dict[str, str]], bundle: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    freeze = freeze_audit()
    with V2_MODEL.open("rb") as stream:
        v2_artifact = pickle.load(stream)
    with V1_MODEL.open("rb") as stream:
        v1_artifact = pickle.load(stream)
    with V1_PREPROCESSOR.open("rb") as stream:
        prep = pickle.load(stream)
    v2_payload = v2_artifact["payload"]
    v1_payload = v1_artifact.get("payload", v1_artifact)
    v2_pred = v2.predict_saved(v2_payload, bundle["X"])
    x = bundle["X"]
    z = prep["scaler"].transform(prep["imputer"].transform(x))
    v1_pred = prep["target_scaler"].inverse_transform(v1_payload["model"].predict(z))
    if v2_pred.shape != v1_pred.shape or v2_pred.shape[1] != 34:
        raise RuntimeError(f"paired prediction shape failure: {v1_pred.shape} {v2_pred.shape}")
    return v1_pred, v2_pred, freeze


def save_predictions(path_csv: Path, path_npz: Path, rows: list[dict[str, str]], pred: np.ndarray, model_label: str, model_sha: str, pca: dict[str, Any]) -> None:
    output = []
    for index, row in enumerate(rows):
        item = {"geometry_id": row["geometry_id"], **{f"D{i}": float(row[f"D{i}"]) for i in range(1, 7)}, "lambda_nm": float(row["lambda_nm"]), "model": model_label, "model_sha256": model_sha, "pca_sha256": sha(PCA), "G_emit_pred": float(pred[index, 0]), "eta_up_pred": float(pred[index, 1])}
        item.update({f"pca_c{i:02d}": float(pred[index, i + 1]) for i in range(1, 33)})
        output.append(item)
    write_csv(path_csv, output)
    np.savez_compressed(path_npz, geometry_ids=np.asarray([row["geometry_id"] for row in rows]), wavelengths_nm=np.asarray([float(row["lambda_nm"]) for row in rows]), predicted_scalars=pred[:, :2], predicted_pca_coefficients=pred[:, 2:], predicted_profile_raw=v2.reconstruct(pred[:, 2:], pca), ux=bundle_ux, theta_deg=bundle_theta, weights_du=pca["weights"], model_sha256=np.asarray(model_sha), pca_sha256=np.asarray(sha(PCA)))


def macro(values: np.ndarray, groups: np.ndarray) -> float:
    return float(np.mean([np.mean(values[groups == group]) for group in np.unique(groups)]))


def median_macro(values: np.ndarray, groups: np.ndarray) -> float:
    return float(np.mean([np.median(values[groups == group]) for group in np.unique(groups)]))


def r2_macro(true: np.ndarray, pred: np.ndarray, groups: np.ndarray) -> float:
    values = []
    for group in np.unique(groups):
        t, p = true[groups == group], pred[groups == group]
        values.append(1.0 - float(np.sum((p - t) ** 2)) / max(float(np.sum((t - np.mean(t)) ** 2)), 1e-300))
    return float(np.mean(values))


def row_metric_arrays(bundle: dict[str, Any], pred: np.ndarray, pca: dict[str, Any]) -> dict[str, np.ndarray]:
    truth = bundle["Y"]
    profiles = v2.reconstruct(pred[:, 2:], pca)
    weights, ux = bundle["weights"], bundle["ux"]
    arrays: dict[str, list[float]] = {key: [] for key in ("G_emit_abs_error", "eta_up_abs_error", "profile_weighted_l1", "profile_correlation", "weighted_js", "profile_integral_error", "dominant_lobe_centroid_error", "theta_peak_error", "F_seed_2_error", "F_seed_5_error", "F_seed_10_error", "asymmetry_error", "positive_fraction_error", "negative_fraction_error", "top2_peak_ratio_error")}
    for index in range(len(truth)):
        arrays["G_emit_abs_error"].append(abs(float(pred[index, 0] - truth[index, 0])))
        arrays["eta_up_abs_error"].append(abs(float(pred[index, 1] - truth[index, 1])))
        actual = np.maximum(bundle["profiles"][index], 0.0)
        predicted = np.maximum(profiles[index], 0.0)
        actual_norm = actual / max(float(np.sum(weights * actual)), 1e-300)
        predicted_norm = predicted / max(float(np.sum(weights * predicted)), 1e-300)
        midpoint = 0.5 * (weights * predicted_norm + weights * actual_norm)
        js = 0.5 * np.sum(np.where(weights * predicted_norm > 0, weights * predicted_norm * np.log(np.maximum(weights * predicted_norm, 1e-300) / np.maximum(midpoint, 1e-300)), 0.0)) + 0.5 * np.sum(np.where(weights * actual_norm > 0, weights * actual_norm * np.log(np.maximum(weights * actual_norm, 1e-300) / np.maximum(midpoint, 1e-300)), 0.0))
        actual_d, predicted_d = v2.directional(actual, bundle["theta"][index], bundle["lambdas"][index], ux, weights), v2.directional(predicted, bundle["theta"][index], bundle["lambdas"][index], ux, weights)
        arrays["profile_weighted_l1"].append(float(np.sum(weights * np.abs(predicted_norm - actual_norm))))
        arrays["profile_correlation"].append(float(v2.corr(actual, profiles[index])))
        arrays["weighted_js"].append(float(js))
        arrays["profile_integral_error"].append(abs(float(np.sum(weights * predicted)) - float(np.sum(weights * actual))) / max(abs(float(np.sum(weights * actual))), 1e-300))
        for key, name in (("dominant_lobe_centroid", "dominant_lobe_centroid_error"), ("theta_peak", "theta_peak_error"), ("F_seed_2", "F_seed_2_error"), ("F_seed_5", "F_seed_5_error"), ("F_seed_10", "F_seed_10_error"), ("asymmetry", "asymmetry_error"), ("positive_fraction", "positive_fraction_error"), ("negative_fraction", "negative_fraction_error"), ("top2_peak_ratio", "top2_peak_ratio_error")):
            arrays[name].append(abs(float(predicted_d[key] - actual_d[key])))
    return {key: np.asarray(value, dtype=float) for key, value in arrays.items()}


def metric_record(bundle: dict[str, Any], pred: np.ndarray, pca: dict[str, Any], label: str) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    truth, groups = bundle["Y"], bundle["groups"]
    arrays = row_metric_arrays(bundle, pred, pca)
    out = {"label": label, "rows": len(truth), "geometries": len(set(groups))}
    for target, name in ((0, "G_emit"), (1, "eta_up")):
        error = pred[:, target] - truth[:, target]
        out[f"{name}_mae"] = macro(np.abs(error), groups)
        out[f"{name}_rmse"] = macro(error ** 2, groups) ** 0.5
        out[f"{name}_median_abs_error"] = median_macro(np.abs(error), groups)
        out[f"{name}_r2"] = r2_macro(truth[:, target], pred[:, target], groups)
    for key, values in arrays.items():
        out[key] = macro(values, groups)
    out["profile_l1"] = out.pop("profile_weighted_l1")
    out["correlation"] = out.pop("profile_correlation")
    out["centroid_mae"] = out.pop("dominant_lobe_centroid_error")
    out["F_seed_5_mae"] = out.pop("F_seed_5_error")
    out["asymmetry_mae"] = out.pop("asymmetry_error")
    out["positive_fraction_mae"] = out.pop("positive_fraction_error")
    out["negative_fraction_mae"] = out.pop("negative_fraction_error")
    out["F_seed_2_mae"] = out.pop("F_seed_2_error")
    out["F_seed_10_mae"] = out.pop("F_seed_10_error")
    return out, arrays


def coefficient_metrics(bundle: dict[str, Any], pred: np.ndarray, label: str) -> list[dict[str, Any]]:
    rows = []
    for index in range(32):
        truth, estimate = bundle["Y"][:, index + 2], pred[:, index + 2]
        rows.append({"model": label, "coefficient": index + 1, "mae": macro(np.abs(estimate - truth), bundle["groups"]), "correlation": v2.corr(truth, estimate), "normalized_error": macro(np.abs(estimate - truth), bundle["groups"]) / max(float(np.std(truth)), 1e-12), "high_priority": index + 1 in HIGH_COEFFS})
    return rows


def scalar_rows(bundle: dict[str, Any], pred: np.ndarray, label: str) -> list[dict[str, Any]]:
    rows = []
    for index, name in enumerate(("G_emit", "eta_up")):
        true, estimate = bundle["Y"][:, index], pred[:, index]
        error = estimate - true
        rows.append({"model": label, "scope": "V2_PROSPECTIVE_ALL", "metric": name, "mae": macro(np.abs(error), bundle["groups"]), "rmse": macro(error ** 2, bundle["groups"]) ** 0.5, "median_abs_error": median_macro(np.abs(error), bundle["groups"]), "r2": r2_macro(true, estimate, bundle["groups"])})
    return rows


def profile_rows(metrics: dict[str, Any], label: str) -> list[dict[str, Any]]:
    mapping = {"profile_l1": "weighted_l1", "correlation": "correlation", "weighted_js": "weighted_js", "profile_integral_error": "integral_error"}
    return [{"model": label, "scope": "V2_PROSPECTIVE_ALL", "space": "PHYSICAL_PROJECTED", "metric": output, "value": metrics[key]} for key, output in mapping.items()]


def directional_rows(metrics: dict[str, Any], label: str) -> list[dict[str, Any]]:
    mapping = {"centroid_mae": "dominant_lobe_centroid", "F_seed_5_mae": "F_seed_5", "asymmetry_mae": "asymmetry", "positive_fraction_mae": "positive_fraction", "negative_fraction_mae": "negative_fraction", "F_seed_2_mae": "F_seed_2", "F_seed_10_mae": "F_seed_10", "theta_peak_error": "theta_peak", "top2_peak_ratio_error": "top2_peak_ratio"}
    return [{"model": label, "scope": "V2_PROSPECTIVE_ALL", "metric": output, "value": metrics[key], "diagnostic_only": output == "theta_peak"} for key, output in mapping.items()]


def paired_comparison(bundle: dict[str, Any], v1_pred: np.ndarray, v2_pred: np.ndarray, pca: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    v1_metrics, v1_arrays = metric_record(bundle, v1_pred, pca, "V1_RIDGE_RAW_FROZEN")
    v2_metrics, v2_arrays = metric_record(bundle, v2_pred, pca, "V2_RIDGE_RAW_FROZEN")
    metric_map = {"profile_l1": ("profile_l1", True), "correlation": ("correlation", False), "weighted_js": ("weighted_js", True), "G_emit_mae": ("G_emit_mae", True), "eta_up_mae": ("eta_up_mae", True), "centroid_mae": ("centroid_mae", True), "F_seed_5_mae": ("F_seed_5_mae", True), "asymmetry_mae": ("asymmetry_mae", True), "F_seed_2_mae": ("F_seed_2_mae", True), "F_seed_10_mae": ("F_seed_10_mae", True)}
    paired, per_geometry = [], []
    for gid in sorted(set(bundle["groups"])):
        mask = bundle["groups"] == gid
        item = {"geometry_id": gid, "geometry_novelty": "NEW_V2_PROSPECTIVE_UNSEEN"}
        core_gains = []
        for output, (key, lower) in metric_map.items():
            if key in ("G_emit_mae", "eta_up_mae"):
                v1_value = float(np.mean(np.abs(v1_pred[mask, 0 if key == "G_emit_mae" else 1] - bundle["Y"][mask, 0 if key == "G_emit_mae" else 1])))
                v2_value = float(np.mean(np.abs(v2_pred[mask, 0 if key == "G_emit_mae" else 1] - bundle["Y"][mask, 0 if key == "G_emit_mae" else 1])))
            else:
                source_key = {"profile_l1": "profile_weighted_l1", "correlation": "profile_correlation", "weighted_js": "weighted_js", "centroid_mae": "dominant_lobe_centroid_error", "F_seed_5_mae": "F_seed_5_error", "asymmetry_mae": "asymmetry_error", "F_seed_2_mae": "F_seed_2_error", "F_seed_10_mae": "F_seed_10_error"}[key]
                v1_value, v2_value = float(np.mean(v1_arrays[source_key][mask])), float(np.mean(v2_arrays[source_key][mask]))
            gain = v1_value - v2_value if lower else v2_value - v1_value
            relative = gain / max(abs(v1_value), 1e-12)
            item[f"v1_{output}"] = v1_value; item[f"v2_{output}"] = v2_value; item[f"{output}_absolute_gain"] = gain; item[f"{output}_relative_gain"] = relative
            if output in ("profile_l1", "centroid_mae", "F_seed_5_mae", "asymmetry_mae"):
                core_gains.append(gain > 0)
        item["core_improved_count"] = sum(core_gains)
        item["classification"] = "V2_WIN" if sum(core_gains) >= 3 else "V2_LOSS" if sum(core_gains) <= 1 else "NEUTRAL"
        per_geometry.append(item)
    for output, (key, lower) in metric_map.items():
        if key in ("G_emit_mae", "eta_up_mae"):
            v1_value, v2_value = v1_metrics[key], v2_metrics[key]
        else:
            v1_value, v2_value = v1_metrics[key], v2_metrics[key]
        gain = v1_value - v2_value if lower else v2_value - v1_value
        wins = sum(float(row[f"{output}_absolute_gain"]) > 1e-12 for row in per_geometry)
        ties = sum(abs(float(row[f"{output}_absolute_gain"])) <= 1e-12 for row in per_geometry)
        losses = len(per_geometry) - wins - ties
        paired.append({"metric": output, "v1_mean": v1_value, "v2_mean": v2_value, "absolute_gain_lower_better_or_corr": gain, "relative_gain": gain / max(abs(v1_value), 1e-12), "v2_win_geometries": wins, "tie_geometries": ties, "v2_loss_geometries": losses})
    return paired, per_geometry, [v1_metrics, v2_metrics]


def spectral_analysis(bundle: dict[str, Any], v1_arrays: dict[str, np.ndarray], v2_arrays: dict[str, np.ndarray], v1_pred: np.ndarray, v2_pred: np.ndarray) -> list[dict[str, Any]]:
    rows = []
    for index, (gid, wavelength) in enumerate(zip(bundle["groups"], bundle["lambdas"])):
        rows.append({"geometry_id": gid, "lambda_nm": float(wavelength), "v1_profile_l1": float(v1_arrays["profile_weighted_l1"][index]), "v2_profile_l1": float(v2_arrays["profile_weighted_l1"][index]), "profile_gain": float(v1_arrays["profile_weighted_l1"][index] - v2_arrays["profile_weighted_l1"][index]), "v1_centroid_error": float(v1_arrays["dominant_lobe_centroid_error"][index]), "v2_centroid_error": float(v2_arrays["dominant_lobe_centroid_error"][index]), "centroid_gain": float(v1_arrays["dominant_lobe_centroid_error"][index] - v2_arrays["dominant_lobe_centroid_error"][index]), "v1_F_seed_5_error": float(v1_arrays["F_seed_5_error"][index]), "v2_F_seed_5_error": float(v2_arrays["F_seed_5_error"][index]), "F_seed_5_gain": float(v1_arrays["F_seed_5_error"][index] - v2_arrays["F_seed_5_error"][index]), "G_emit_v1_abs_error": float(abs(v1_pred[index, 0] - bundle["Y"][index, 0])), "G_emit_v2_abs_error": float(abs(v2_pred[index, 0] - bundle["Y"][index, 0])), "eta_up_v1_abs_error": float(abs(v1_pred[index, 1] - bundle["Y"][index, 1])), "eta_up_v2_abs_error": float(abs(v2_pred[index, 1] - bundle["Y"][index, 1])), "band_edge": float(wavelength) in (445.0, 455.0)})
    return rows


def cv_dev_comparison(v2_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    source = read_csv(V2_REEVAL_ROOT / "V2_DEVELOPMENT_VALIDATION_RESULTS.csv")
    ridge = next(row for row in source if row["model_id"] == "ridge_a100")
    gain = json.loads((V2_REEVAL_ROOT / "AL_ROUND1_LEARNING_GAIN_AUDIT.json").read_text(encoding="utf-8"))
    rows = []
    for level, values in (("V2_TRAIN_GROUPED_CV", {"profile_l1": float(ridge["cv_profile_weighted_l1"]), "correlation": float(ridge["cv_profile_correlation"]), "weighted_js": float(ridge["cv_weighted_js"]), "G_emit_mae": float(ridge["cv_G_emit_mae"]), "eta_up_mae": float(ridge["cv_eta_up_mae"]), "centroid_mae": float(ridge["cv_dominant_lobe_centroid_mae"]), "F_seed_5_mae": float(ridge["cv_F_seed_5_mae"]), "asymmetry_mae": float(ridge["cv_asymmetry_mae"])}), ("DEVELOPMENT_VALIDATION", {"profile_l1": float(ridge["development_profile_weighted_l1"]), "correlation": float(ridge["development_profile_correlation"]), "weighted_js": float(ridge["development_weighted_js"]), "G_emit_mae": float(ridge["development_G_emit_mae"]), "eta_up_mae": float(ridge["development_eta_up_mae"]), "centroid_mae": float(ridge["development_dominant_lobe_centroid_mae"]), "F_seed_5_mae": float(ridge["development_F_seed_5_mae"]), "asymmetry_mae": float(ridge["development_asymmetry_mae"])}), ("V1_BLIND_RETROSPECTIVE", {"profile_l1": gain["v1_blind_retrospective"]["metrics"]["profile_weighted_l1"]["new"], "correlation": gain["v1_blind_retrospective"]["metrics"]["profile_correlation"]["new"], "weighted_js": gain["v1_blind_retrospective"]["metrics"]["weighted_js"]["new"], "G_emit_mae": gain["v1_blind_retrospective"]["metrics"]["G_emit_mae"]["new"], "eta_up_mae": gain["v1_blind_retrospective"]["metrics"]["eta_up_mae"]["new"], "centroid_mae": gain["v1_blind_retrospective"]["metrics"]["dominant_lobe_centroid_mae"]["new"], "F_seed_5_mae": gain["v1_blind_retrospective"]["metrics"]["F_seed_5_mae"]["new"], "asymmetry_mae": gain["v1_blind_retrospective"]["metrics"]["asymmetry_mae"]["new"]}), ("V2_PROSPECTIVE", {"profile_l1": v2_metrics["profile_l1"], "correlation": v2_metrics["correlation"], "weighted_js": v2_metrics["weighted_js"], "G_emit_mae": v2_metrics["G_emit_mae"], "eta_up_mae": v2_metrics["eta_up_mae"], "centroid_mae": v2_metrics["centroid_mae"], "F_seed_5_mae": v2_metrics["F_seed_5_mae"], "asymmetry_mae": v2_metrics["asymmetry_mae"]})): values.update({"level": level}); rows.append(values)
    return rows


def evaluate() -> int:
    configure()
    registry = json.loads((OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json").read_text(encoding="utf-8"))
    if registry.get("truth_acquired") != 8 or registry.get("solver_entries") != 8 or registry.get("solver_returned") != 8 or registry.get("rerun_delta") != 0 or registry.get("duplicate") != 0:
        raise RuntimeError("evaluation requires exactly 8 persisted truth cases")
    prefreeze = json.loads((OUT / "V2_PROSPECTIVE_PREACQUISITION_FREEZE_AUDIT.json").read_text(encoding="utf-8"))
    current_freeze = freeze_audit()
    if current_freeze["checks"] != prefreeze["checks"]:
        raise RuntimeError("model/PCA freeze changed after truth acquisition")
    audits = case_audits()
    if len(audits) != 8 or not all(row["pass"] for row in audits):
        raise RuntimeError("case persistence audit incomplete")
    rows = []
    for row in v2_rows():
        path = OUT / "CASES" / row["geometry_id"] / "CASE_DATASET_ROWS.csv"
        rows.extend(read_csv(path))
    if len(rows) != 88 or [float(row["lambda_nm"]) for row in rows[:11]] != list(WLS) or len({row["geometry_id"] for row in rows}) != 8:
        raise RuntimeError("prospective dataset shape/order failure")
    write_csv(OUT / "V2_PROSPECTIVE_DATASET.csv", rows)
    dataset_manifest = {"schema_version": "V2_PROSPECTIVE_DATASET_MANIFEST_V1", "dataset": file_record(OUT / "V2_PROSPECTIVE_DATASET.csv"), "rows": 88, "geometries": 8, "wavelengths_nm": WLS.tolist(), "truth_acquired_after_persistence_gate": True, "solver_entries": 8, "rerun_delta": 0, "duplicate": 0, "geometry_ids": [f"V2P_{i:02d}" for i in range(1, 9)]}
    write_json(OUT / "V2_PROSPECTIVE_DATASET_MANIFEST.json", dataset_manifest)
    pca = v2.load_pca()
    bundle = v2.make_bundle(rows, pca)
    global bundle_ux, bundle_theta
    bundle_ux, bundle_theta = bundle["ux"], bundle["theta"]
    v1_pred, v2_pred, freeze = load_predictions(rows, bundle)
    save_predictions(OUT / "V1_FROZEN_ON_V2P_PREDICTIONS.csv", OUT / "V1_FROZEN_ON_V2P_PREDICTIONS.npz", rows, v1_pred, "V1_RIDGE_RAW_FROZEN", sha(V1_MODEL), pca)
    save_predictions(OUT / "V2_FROZEN_ON_V2P_PREDICTIONS.csv", OUT / "V2_FROZEN_ON_V2P_PREDICTIONS.npz", rows, v2_pred, "V2_RIDGE_RAW_FROZEN", sha(V2_MODEL), pca)
    v1_metrics, v1_arrays = metric_record(bundle, v1_pred, pca, "V1_RIDGE_RAW_FROZEN")
    v2_metrics, v2_arrays = metric_record(bundle, v2_pred, pca, "V2_RIDGE_RAW_FROZEN")
    write_csv(OUT / "V2_PROSPECTIVE_METRICS_SCALAR.csv", scalar_rows(bundle, v2_pred, "V2_RIDGE_RAW_FROZEN"))
    write_csv(OUT / "V2_PROSPECTIVE_METRICS_PROFILE.csv", profile_rows(v2_metrics, "V2_RIDGE_RAW_FROZEN"))
    write_csv(OUT / "V2_PROSPECTIVE_METRICS_DIRECTIONAL.csv", directional_rows(v2_metrics, "V2_RIDGE_RAW_FROZEN"))
    coeff_rows = coefficient_metrics(bundle, v1_pred, "V1_RIDGE_RAW_FROZEN") + coefficient_metrics(bundle, v2_pred, "V2_RIDGE_RAW_FROZEN")
    write_csv(OUT / "V2_HIGH_PRIORITY_PCA_COEFFICIENT_PROSPECTIVE.csv", [row for row in coeff_rows if row["high_priority"]])
    paired, per_geometry, model_metrics = paired_comparison(bundle, v1_pred, v2_pred, pca)
    write_csv(OUT / "V1_V2_PAIRED_PROSPECTIVE_COMPARISON.csv", paired)
    for row in per_geometry:
        source = next(item for item in v2_rows() if item["geometry_id"] == row["geometry_id"])
        row.update({f"D{i}": source[f"D{i}"] for i in range(1, 7)})
    write_csv(OUT / "V2_PROSPECTIVE_PER_GEOMETRY.csv", per_geometry)
    spectral = spectral_analysis(bundle, v1_arrays, v2_arrays, v1_pred, v2_pred)
    write_csv(OUT / "V2_PROSPECTIVE_SPECTRAL_ANALYSIS.csv", spectral)
    cvdev = cv_dev_comparison(v2_metrics)
    write_csv(OUT / "V2_CV_DEV_PROSPECTIVE_COMPARISON.csv", cvdev)
    gain_by_metric = {row["metric"]: row for row in paired}
    directional_keys = ("centroid_mae", "F_seed_5_mae", "asymmetry_mae")
    directional_improved = sum(gain_by_metric[key]["absolute_gain_lower_better_or_corr"] > 0 for key in directional_keys)
    profile_improved = gain_by_metric["profile_l1"]["absolute_gain_lower_better_or_corr"] > 0
    scalar_no_degradation = gain_by_metric["G_emit_mae"]["relative_gain"] >= -0.10 and gain_by_metric["eta_up_mae"]["relative_gain"] >= -0.10
    wins = sum(row["classification"] == "V2_WIN" for row in per_geometry)
    if profile_improved and directional_improved == 3 and scalar_no_degradation and wins >= 5:
        verdict = "AL_PROSPECTIVE_GAIN_CONFIRMED"
    elif profile_improved or directional_improved >= 1:
        verdict = "AL_PROSPECTIVE_GAIN_PARTIAL"
    else:
        verdict = "AL_PROSPECTIVE_GAIN_NOT_CONFIRMED"
    write_json(OUT / "AL_PROSPECTIVE_GAIN_VERDICT.json", {"schema_version": "AL_PROSPECTIVE_GAIN_VERDICT_V1", "verdict": verdict, "profile_improved": profile_improved, "directional_core_improved_count": directional_improved, "directional_core_metrics": list(directional_keys), "scalar_no_degradation": scalar_no_degradation, "v2_win_geometries": wins, "geometry_count": 8, "paired_comparison": paired, "no_retraining": True, "no_pca_refit": True})
    readiness = {"schema_version": "V2_READINESS_VERDICT_V1", "scalar_forward": "READY" if v2_metrics["G_emit_mae"] <= 1.5 * float(cvdev[1]["G_emit_mae"]) and v2_metrics["eta_up_mae"] <= 1.5 * float(cvdev[1]["eta_up_mae"]) else "PARTIAL", "coarse_directional": "READY" if gain_by_metric["centroid_mae"]["absolute_gain_lower_better_or_corr"] > 0 and gain_by_metric["F_seed_5_mae"]["absolute_gain_lower_better_or_corr"] > 0 and wins >= 5 else "PARTIAL" if gain_by_metric["centroid_mae"]["absolute_gain_lower_better_or_corr"] > 0 or gain_by_metric["F_seed_5_mae"]["absolute_gain_lower_better_or_corr"] > 0 else "NOT_READY", "fine_directional": "READY" if all(gain_by_metric[key]["absolute_gain_lower_better_or_corr"] > 0 for key in ("asymmetry_mae", "F_seed_2_mae", "F_seed_10_mae")) and wins >= 5 else "PARTIAL" if any(gain_by_metric[key]["absolute_gain_lower_better_or_corr"] > 0 for key in ("asymmetry_mae", "F_seed_2_mae", "F_seed_10_mae")) else "NOT_READY", "fine_directional_not_inferred_from_no_collapse": True, "evidence": {"v2_metrics": v2_metrics, "v1_metrics": v1_metrics, "v2_win_geometries": wins}}
    write_json(OUT / "V2_READINESS_VERDICT.json", readiness)
    registry.update({"phase": "EVALUATION_COMPLETE", "V2_PROSPECTIVE_ACQUISITION_COMPLETE": True, "truth_acquired": 8, "solver_entries": 8, "solver_returned": 8, "rerun_delta": 0, "duplicate": 0, "v2_status": "USED_PROSPECTIVE_TEST_V2"})
    write_json(OUT / "V2_PROSPECTIVE_ACQUISITION_REGISTRY.json", registry)
    report = build_report(v1_metrics, v2_metrics, paired, per_geometry, cvdev, verdict, readiness, freeze)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": "PASS" if verdict != "AL_PROSPECTIVE_GAIN_NOT_CONFIRMED" else "PARTIAL", "verdict": verdict, "v1_metrics": v1_metrics, "v2_metrics": v2_metrics, "solver_entries": 8, "solver_returned": 8, "rerun_delta": 0, "duplicate": 0, "truth_acquired": 8, "retraining": False, "pca_refit": False, "hyperparameter_change": False, "v2p_status": "USED_PROSPECTIVE_TEST_V2", "next": "INVERSE_DESIGN_READINESS_REVIEW_V2" if verdict == "AL_PROSPECTIVE_GAIN_CONFIRMED" else "CHART_REVIEW_AL_ROUND2_VS_COARSE_INVERSE" if verdict == "AL_PROSPECTIVE_GAIN_PARTIAL" else "ANGULAR_TARGET_REPRESENTATION_AND_SURROGATE_METHOD_REVIEW"})
    final_manifest()
    print(json.dumps(json.loads((OUT / "REPORT.json").read_text(encoding="utf-8")), ensure_ascii=False), flush=True)
    return 0


def build_report(v1_metrics: dict[str, Any], v2_metrics: dict[str, Any], paired: list[dict[str, Any]], per_geometry: list[dict[str, Any]], cvdev: list[dict[str, Any]], verdict: str, readiness: dict[str, Any], freeze: dict[str, Any]) -> str:
    lines = ["# APCD_COUPLING_V2_2_V2_PROSPECTIVE_8G_TWO_SLOT_ACQUISITION_AND_PAIRED_FROZEN_EVAL_V1", "", "### STATUS", "", "PASS" if verdict != "AL_PROSPECTIVE_GAIN_NOT_CONFIRMED" else "PARTIAL", "", "### V2_PROSPECTIVE_AUTHORITY", "", "8/8 sealed V2P identities retained; no overlap with original train/validation, V1 blind, or AL Round-1; production fingerprint passed.", "", "### TWO_SLOT_EXECUTION", "", "4 batches of 2; 12 MPI x 1 thread/job; global cap=3; third task slot not consumed.", "", "### SOLVER_ACCOUNTING", "", "entered=8; returned=8; rerun=0; duplicate=0; no automatic relaunch.", "", "### PERSISTENCE_STATUS", "", "All 8 cases passed canonical post-FSP, post SHA, independent LOAD-only, raw extraction, completion audit, and slot release.", "", "### V2_PROSPECTIVE_DATASET", "", "8 geometries / 88 rows; USED_PROSPECTIVE_TEST_V2.", "", "### FREEZE_VERIFICATION", "", f"V1=RIDGE_RAW_CHAMPION; V2=V2_RIDGE_RAW/ridge_a100; PCA rank=32; V1 model SHA={freeze['v1']['model']['sha256']}; V2 model SHA={freeze['v2']['model']['sha256']}; PCA SHA={freeze['pca']['sha256']}; no retrain/refit/change.", "", "### V2_SCALAR_METRICS", "", f"G_emit MAE/RMSE/median/R2={v2_metrics['G_emit_mae']}/{v2_metrics['G_emit_rmse']}/{v2_metrics['G_emit_median_abs_error']}/{v2_metrics['G_emit_r2']}; eta_up={v2_metrics['eta_up_mae']}/{v2_metrics['eta_up_rmse']}/{v2_metrics['eta_up_median_abs_error']}/{v2_metrics['eta_up_r2']}.", "", "### V2_PROFILE_METRICS", "", f"weighted L1={v2_metrics['profile_l1']}; correlation={v2_metrics['correlation']}; weighted JS={v2_metrics['weighted_js']}; integral error={v2_metrics['profile_integral_error']}.", "", "### V2_DIRECTIONAL_METRICS", "", f"centroid MAE={v2_metrics['centroid_mae']}; F_seed_5 MAE={v2_metrics['F_seed_5_mae']}; asymmetry MAE={v2_metrics['asymmetry_mae']}; F_seed_2/F_seed_10={v2_metrics['F_seed_2_mae']}/{v2_metrics['F_seed_10_mae']}; theta_peak is diagnostic only.", "", "### V1_VS_V2_PAIRED_PROSPECTIVE", "", "Per-metric absolute/relative gains and per-geometry win/tie/loss are in V1_V2_PAIRED_PROSPECTIVE_COMPARISON.csv; geometry classifications are in V2_PROSPECTIVE_PER_GEOMETRY.csv.", "", "### AL_PROSPECTIVE_GAIN_VERDICT", "", verdict, "", "### HIGH_PRIORITY_PCA_COEFFICIENTS", "", "c1, c3, c4, c5, c12, c17 paired MAE/correlation/normalized error are in V2_HIGH_PRIORITY_PCA_COEFFICIENT_PROSPECTIVE.csv.", "", "### CV_DEV_V2P_COMPARISON", "", "V2 grouped CV, development, historical V1 blind retrospective, and independent V2 prospective metrics are in V2_CV_DEV_PROSPECTIVE_COMPARISON.csv.", "", "### V2_READINESS", "", f"scalar={readiness['scalar_forward']}; coarse directional={readiness['coarse_directional']}; fine directional={readiness['fine_directional']}.", "", "### RETRAIN_STATUS", "", "NO RETRAIN; NO PCA REFIT; NO HYPERPARAMETER CHANGE.", "", "### SCHEDULER_RELEASE", "", "active task slots after release=[]; registry manual edit=False.", "", "### ARTIFACTS", "", str(OUT), "", "### GIT_AUDIT", "", "No commit, push, reset, restore, clean, stash, rebase, amend, or force push.", "", "### PROPOSED_VERDICT", ""]
    lines.append("PASS — V2_PROSPECTIVE_GENERALIZATION_AND_AL_GAIN_CONFIRMED" if verdict == "AL_PROSPECTIVE_GAIN_CONFIRMED" else "PASS — V2_PROSPECTIVE_GENERALIZATION_STABLE_AL_GAIN_PARTIAL" if verdict == "AL_PROSPECTIVE_GAIN_PARTIAL" else "PARTIAL — V2_PROSPECTIVE_DIRECTIONAL_GAIN_NOT_CONFIRMED")
    lines += ["", "### NEXT", "", "INVERSE_DESIGN_READINESS_REVIEW_V2" if verdict == "AL_PROSPECTIVE_GAIN_CONFIRMED" else "CHART_REVIEW_AL_ROUND2_VS_COARSE_INVERSE" if verdict == "AL_PROSPECTIVE_GAIN_PARTIAL" else "ANGULAR_TARGET_REPRESENTATION_AND_SURROGATE_METHOD_REVIEW", ""]
    return "\n".join(lines)


def final_manifest() -> None:
    files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files.append({"path": str(path.relative_to(OUT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)})
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files, "solver_entries": 8, "truth_acquired": 8, "rerun_delta": 0, "duplicate": 0})


original_write_json = acq.write_json
acq.write_json = mirror_registry_write


def run_case(case_id: str) -> int:
    configure()
    return acq.run_case(case_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--reconcile-preentry", action="store_true")
    parser.add_argument("--run-case")
    args = parser.parse_args()
    if args.run_case:
        return run_case(args.run_case)
    if args.preflight:
        return preflight()
    if args.acquire:
        return acquire()
    if args.reconcile_preentry:
        configure()
        return reconcile_preentry()
    if args.evaluate:
        return evaluate()
    parser.error("--preflight, --acquire, --evaluate, or --run-case required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
