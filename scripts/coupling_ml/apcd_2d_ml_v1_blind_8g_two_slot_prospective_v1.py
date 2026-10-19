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
SCRIPT = Path(__file__).resolve()
TRAINVAL_SCRIPT = ACTIVE / "scripts" / "coupling_ml" / "apcd_2d_ml_v1_trainval_acquisition_v1.py"
TRAINVAL_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
SEALED = TRAINVAL_ROOT / "BLIND_PROSPECTIVE_SEALED_MANIFEST.json"
DOE = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1" / "K6_V1_64G_DOE_CANDIDATES.csv"
SPLIT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1" / "K6_V1_GEOMETRY_SPLIT_MANIFEST.json"
PREBLIND_ROOT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_COMPOSITIONAL_NP_PRIOR_REPAIR_AND_FINAL_PREBLIND_ABLATION_V1"
FREEZE = PREBLIND_ROOT / "PREBLIND_CHAMPION_FREEZE.json"
PREBLIND_MANIFEST = PREBLIND_ROOT / "FINAL_SHA256_MANIFEST.json"
MODEL = PREBLIND_ROOT / "models" / "Ridge_RAW_CHAMPION.pkl"
PREPROCESSOR = PREBLIND_ROOT / "preprocessors" / "selected_model_preprocessor.pkl"
PCA = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAIN_ONLY_PCA_PRIOR_ABLATION_V1" / "ANGULAR_PCA_MODEL.npz"
OUT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1"
WLS = np.arange(445.0, 456.0, 1.0)
PITCH_NM = 290.0
LAMBDA_X_NM = 1740.0
ATTEMPT = "attempt_001"
JOB_PREFIX = "APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_PROSPECTIVE_V1"


def load_trainval():
    spec = importlib.util.spec_from_file_location("frozen_trainval_runner", TRAINVAL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen trainval runner: {TRAINVAL_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tv = load_trainval()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(safe(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows([{k: safe(v) for k, v in row.items()} for row in rows])


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None}


def close_enough(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-15)
    return a == b


def manifest_sha(path: str) -> str | None:
    data = json.loads(PREBLIND_MANIFEST.read_text(encoding="utf-8"))
    for row in data.get("files", []):
        if str(row.get("path", "")).replace("/", "\\") == path.replace("/", "\\"):
            return row.get("sha256")
    return None


def verify_preblind() -> dict[str, Any]:
    required = [FREEZE, PREBLIND_MANIFEST, MODEL, PREPROCESSOR, PCA, SEALED, DOE, SPLIT]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("PREBLIND_FREEZE_HARD_STOP_MISSING:" + ";".join(missing))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    checks = {
        "freeze_manifest_entry": manifest_sha("PREBLIND_CHAMPION_FREEZE.json") == sha(FREEZE),
        "model_sha": freeze.get("model_sha256") == sha(MODEL),
        "scaler_sha": freeze.get("scaler_sha256") == sha(PREPROCESSOR),
        "pca_sha": freeze.get("pca_sha256") == sha(PCA),
        "dataset_sha": freeze.get("dataset_sha256") == "cf0a85a23de7496e813217a2a51e03af9c401f398f1d8fe909dec142e9a6e0ff",
        "champion": freeze.get("champion") == "RIDGE_RAW_CHAMPION",
        "model_family": freeze.get("model_family") == "Ridge",
        "feature_set": freeze.get("feature_set") == "RAW_D1_D6_LAMBDA",
        "pca_rank": freeze.get("pca_rank") == 32,
        "blind_truth_zero": freeze.get("blind_truth_acquired") == 0,
        "validation_only": freeze.get("validation_status") == "DEVELOPMENT_VALIDATION_ONLY",
    }
    if not all(checks.values()):
        raise RuntimeError("PREBLIND_FREEZE_HARD_STOP_SHA_OR_FIELD_MISMATCH:" + json.dumps(checks, sort_keys=True))
    return {"schema_version": "PREBLIND_FREEZE_VERIFICATION_V1", "verified_utc": now(), "freeze": file_record(FREEZE), "manifest": file_record(PREBLIND_MANIFEST), "model": file_record(MODEL), "preprocessor": file_record(PREPROCESSOR), "pca": file_record(PCA), "freeze_fields": freeze, "checks": checks, "pass": True}


def sealed_rows() -> list[dict[str, Any]]:
    sealed = json.loads(SEALED.read_text(encoding="utf-8"))
    rows = sealed.get("rows", [])
    if not sealed.get("sealed") or sealed.get("truth_acquired") != 0 or len(rows) != 8:
        raise RuntimeError("BLIND_SEAL_HARD_STOP")
    if len({r["geometry_id"] for r in rows}) != 8 or any(r.get("intended_role") != "BLIND_PROSPECTIVE" for r in rows):
        raise RuntimeError("BLIND_IDENTITY_HARD_STOP")
    doe = {r["geometry_id"]: r for r in read_csv(DOE)}
    out = []
    for row in rows:
        d = doe.get(row["geometry_id"])
        if d is None or d.get("split") != "BLIND":
            raise RuntimeError(f"BLIND_DOE_SPLIT_MISMATCH:{row['geometry_id']}")
        values = [float(row[f"D{i}"]) for i in range(1, 7)]
        doe_values = [float(d[f"D{i}_nm"]) for i in range(1, 7)]
        if values != doe_values or row["geometry_sha256"] != d["geometry_fingerprint_sha256"]:
            raise RuntimeError(f"BLIND_GEOMETRY_SHA_MISMATCH:{row['geometry_id']}")
        out.append({"geometry_id": row["geometry_id"], **{f"D{i}": values[i - 1] for i in range(1, 7)}, "geometry_sha256": row["geometry_sha256"], "intended_role": row["intended_role"], "split": "BLIND"})
    return out


def configure_tv(rows: list[dict[str, Any]]) -> None:
    tv.OUT = OUT
    tv.DOE_ROW_BY_ID = {r["geometry_id"]: {"geometry_id": r["geometry_id"], **{f"D{i}_nm": r[f"D{i}"] for i in range(1, 7)}, "geometry_fingerprint_sha256": r["geometry_sha256"], "split": "BLIND"} for r in rows}
    tv.JOB_PREFIX = JOB_PREFIX
    tv.ATTEMPT = ATTEMPT


def immutable_diff(reference: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    diffs = []
    rr, cr = reference.get("rows", {}), candidate.get("rows", {})
    for name in sorted(set(rr) | set(cr)):
        if name not in rr or name not in cr:
            diffs.append({"path": name, "allowed": False})
            continue
        for prop in sorted(set(rr[name]) | set(cr[name])):
            if name.startswith("NP_bar_") and prop == "x span":
                continue
            if not close_enough(rr[name].get(prop), cr[name].get(prop)):
                diffs.append({"path": f"{name}.{prop}", "reference": rr[name].get(prop), "candidate": cr[name].get(prop), "allowed": False})
    return diffs


def geometry_authority(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ref_path = TRAINVAL_ROOT / "SETUPS" / "K6V1_A03" / "SETUP_AUDIT.json"
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    audits = []
    for row in rows:
        audit = tv.materialize_setup(tv.DOE_ROW_BY_ID[row["geometry_id"]])
        snap = audit["snapshot"]
        rr = snap["rows"]
        names = set(snap["objects"])
        np_names = sorted((n for n in names if n.startswith("NP_bar_")), key=lambda n: int(n.rsplit("_", 1)[-1]))
        fdtd = rr["FDTD"]
        source = rr["source_dipole"]
        monitors = rr
        checks = {
            "geometry_id": audit["geometry_id"] == row["geometry_id"],
            "ordered_vector": audit["geometry"] == [row[f"D{i}"] for i in range(1, 7)],
            "geometry_sha": row["geometry_sha256"] == tv.DOE_ROW_BY_ID[row["geometry_id"]]["geometry_fingerprint_sha256"],
            "production_domain": math.isclose(float(fdtd["x span"]) * 1e6, 23.0, abs_tol=1e-6),
            "finite_2d_pml": fdtd.get("dimension") == "2D" and all(fdtd.get(k) == "PML" for k in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "no_periodic_bloch": all(fdtd.get(k) not in {"Periodic", "Bloch"} for k in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "pml_mesh": int(float(fdtd["pml profile"])) == 2 and int(float(fdtd["pml layers"])) == 32 and float(fdtd["mesh accuracy"]) == 2.0,
            "source": abs(float(source["x"]) * 1e9) < 1e-6 and abs(float(source["y"]) * 1e9 + 276.0) < 1e-6 and float(source["theta"]) == 90.0 and float(source["phi"]) == 0.0,
            "wavelength": math.isclose(float(source["wavelength start"]) * 1e9, 445.0, abs_tol=1e-9) and math.isclose(float(source["wavelength stop"]) * 1e9, 455.0, abs_tol=1e-9),
            "monitor": all(math.isclose(float(monitors[n]["x span"]) * 1e6, 19.0, abs_tol=1e-9) and int(float(monitors[n]["frequency points"])) == 11 for n in ("upward_monitor", "downward_monitor")),
            "source_box": all(int(float(monitors[n]["frequency points"])) == 11 for n in tv.SOURCE_BOXES),
            "mdc_spacer": all(f"MDC_LAYER_{i:02d}" in names for i in range(12)) and "EXTRA_SPACER_12" in names and rr["EXTRA_SPACER_12"].get("material") == "APCD_SIO2_NATIVE_M1",
            "six_np": len(np_names) == 6 and [round(float(rr[n]["x"]) * 1e9, 6) for n in np_names] == [-725.0, -435.0, -145.0, 145.0, 435.0, 725.0],
            "np_ordered_widths": len(np_names) == 6 and all(math.isclose(float(rr[n]["x span"]) * 1e9, row[f"D{i}"], abs_tol=1e-6) for i, n in enumerate(np_names, 1)),
        }
        diffs = immutable_diff(ref["snapshot"], snap)
        checks["UNEXPECTED_SCIENTIFIC_DIFF_COUNT_zero"] = len(diffs) == 0
        audits.append({"geometry_id": row["geometry_id"], "geometry": [row[f"D{i}"] for i in range(1, 7)], "geometry_sha256": row["geometry_sha256"], "production_domain_fingerprint": sha(TRAINVAL_ROOT / "V1_SCIENTIFIC_SPACE_FREEZE.json"), "setup": audit["setup_pre"], "checks": checks, "UNEXPECTED_SCIENTIFIC_DIFF_COUNT": len(diffs), "unexpected_diffs": diffs, "pass": bool(all(checks.values()))})
    result = {"schema_version": "BLIND_GEOMETRY_AUTHORITY_V1", "sealed_manifest_sha256": sha(SEALED), "geometry_count": len(audits), "rows": audits, "pass": len(audits) == 8 and all(a["pass"] for a in audits)}
    if not result["pass"]:
        raise RuntimeError("BLIND_GEOMETRY_PREFLIGHT_FAILED")
    write_json(OUT / "BLIND_GEOMETRY_AUTHORITY.json", result)
    return result


def preflight() -> None:
    if OUT.exists():
        if any((OUT / name).exists() for name in ("CASES", "BLIND_ACQUISITION_REGISTRY.json", "PREBLIND_FREEZE_VERIFICATION.json", "PREFLIGHT_AUDIT.json")):
            raise RuntimeError(f"output namespace exists beyond setup-only recovery boundary; overwrite forbidden: {OUT}")
    else:
        OUT.mkdir(parents=True, exist_ok=False)
    freeze_audit = verify_preblind()
    rows = sealed_rows()
    configure_tv(rows)
    # The validated source-reference normalization is reused; it is not blind truth.
    for name in ("V1_SCIENTIFIC_SPACE_FREEZE.json", "V1_SOURCE_REFERENCE.json"):
        shutil.copy2(TRAINVAL_ROOT / name, OUT / name)
    shutil.copy2(TRAINVAL_ROOT / "K6_V1_64G_PRIOR_FEATURES.csv", OUT / "K6_V1_64G_PRIOR_FEATURES.csv")
    geom_audit = geometry_authority(rows)
    scheduler = tv.scheduler_snapshot()
    m2s = [p for p in scheduler.get("processes", []) if p.get("is_m2s")]
    if scheduler.get("global_capacity") != 3 or m2s or len(scheduler.get("active_slots", [])) + 2 > 3:
        raise RuntimeError("SCHEDULER_PREFLIGHT_HARD_STOP:" + json.dumps({"global_capacity": scheduler.get("global_capacity"), "active_slots": scheduler.get("active_slots"), "m2s": m2s}, default=str))
    registry_rows = [{**r, "status": "PLANNED", "solver_entered": False, "solver_returned": False, "post_validated": False, "raw_extracted": False, "rerun_delta": 0} for r in rows]
    write_json(OUT / "BLIND_ACQUISITION_REGISTRY.json", {"schema_version": "BLIND_ACQUISITION_REGISTRY_V1", "task": JOB_PREFIX, "attempt_id": ATTEMPT, "rows": registry_rows, "solver_entries": 0, "solver_returned": 0, "rerun_delta": 0, "blind_truth_acquired": 0, "manual_registry_edit": False})
    write_json(OUT / "PREBLIND_FREEZE_VERIFICATION.json", freeze_audit)
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", {"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V1", "phase": "PREFLIGHT", "global_capacity": scheduler["global_capacity"], "active_slots_before": scheduler["active_slots"], "processes_before": scheduler["processes"], "requested_task_slots": 2, "resource_per_job": {"processes": 12, "threads": 1}, "manual_registry_edit": False, "m2s_processes": m2s, "available_slots_for_task": scheduler["global_capacity"] - len(scheduler["active_slots"]), "pass": True})
    write_json(OUT / "PREFLIGHT_AUDIT.json", {"schema_version": "BLIND_8G_ZERO_LEAKAGE_PREFLIGHT_V1", "generated_utc": now(), "solver_entries": 0, "blind_truth_acquired": 0, "train_validation_rerun": False, "active_learning": False, "model_retraining": False, "freeze": freeze_audit, "sealed_manifest": {"path": str(SEALED), "sha256": sha(SEALED), "count": len(rows), "ids": [r["geometry_id"] for r in rows]}, "geometry_authority": geom_audit, "scheduler": {"global_capacity": scheduler["global_capacity"], "active_slots": scheduler["active_slots"], "m2s_processes": m2s, "task_slots_requested": 2}, "pass": True})


def case_result(case_id: str) -> tuple[bool, dict[str, Any]]:
    case = OUT / "CASES" / case_id
    result_path = case / "CASE_RESULT.json"
    acceptance_path = case / "CASE_ACCEPTANCE.json"
    post, raw = case / "post.fsp", case / f"{case_id}_RAW_TRUTH.npz"
    if not result_path.is_file():
        failure = json.loads((case / "FAILURE_AUDIT.json").read_text(encoding="utf-8")) if (case / "FAILURE_AUDIT.json").is_file() else {}
        return False, {"geometry_id": case_id, "status": "FAILED_REQUIRES_CHART_REVIEW", "failure": failure}
    result = json.loads(result_path.read_text(encoding="utf-8"))
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8")) if acceptance_path.is_file() else {}
    passed = bool(result.get("state") == "SLOT_RELEASED" and result.get("solver_entered") and result.get("solver_returned") and result.get("run_invocation_count") == 1 and result.get("rerun_delta") == 0 and result.get("load_only_validation", {}).get("ok") is True and post.is_file() and post.stat().st_size > 0 and raw.is_file() and raw.stat().st_size > 0 and acceptance.get("pass") is True)
    lifecycle = {"schema_version": "BLIND_CASE_LIFECYCLE_AUDIT_V1", "geometry_id": case_id, "solver_entered": result.get("solver_entered"), "solver_returned": result.get("solver_returned"), "run_invocation_count": result.get("run_invocation_count"), "rerun_delta": result.get("rerun_delta", 0), "post_fsp": file_record(post), "raw_truth": file_record(raw), "load_only": result.get("load_only_validation"), "completion": str(case / ATTEMPT / "completion.json"), "events": str(case / ATTEMPT / "events.jsonl"), "slot_release_state": result.get("state"), "pass": passed}
    write_json(case / "LIFECYCLE_AUDIT.json", lifecycle)
    return passed, {"geometry_id": case_id, "status": "COMPLETED" if passed else "FAILED_REQUIRES_CHART_REVIEW", "result": result, "lifecycle": lifecycle}


def run_case(case_id: str) -> int:
    rows = sealed_rows()
    configure_tv(rows)
    return int(tv.run_case(case_id))


def acquire() -> None:
    registry_path = OUT / "BLIND_ACQUISITION_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = registry["rows"]
    batches = [rows[i:i + 2] for i in range(0, len(rows), 2)]
    log_dir = OUT / "CONTROLLER_LOGS"
    log_dir.mkdir(exist_ok=False)
    snapshots = []
    max_task_slots = 0
    total_entered = 0
    total_returned = 0
    for batch_index, batch in enumerate(batches, 1):
        snap = tv.scheduler_snapshot()
        if any(p.get("is_m2s") for p in snap.get("processes", [])):
            raise RuntimeError("M2S_PROCESS_HARD_STOP_BEFORE_BATCH")
        for row in rows:
            if row["geometry_id"] in {b["geometry_id"] for b in batch}:
                row.update({"status": "RUNNING", "batch": batch_index, "started_utc": now()})
        registry.update({"phase": "RUNNING", "current_batch": batch_index, "total_batches": len(batches), "blind_truth_acquired": 0, "solver_entries": total_entered, "solver_returned": total_returned})
        write_json(registry_path, registry)
        children = {}
        for item in batch:
            case_id = item["geometry_id"]
            log = (log_dir / f"{case_id}.log").open("w", encoding="utf-8")
            children[case_id] = (subprocess.Popen([sys.executable, str(SCRIPT), "--run-case", case_id], cwd=str(ACTIVE), stdout=log, stderr=subprocess.STDOUT), log)
        while any(proc.poll() is None for proc, _ in children.values()):
            snap = tv.scheduler_snapshot()
            task_slots = [s for s in snap.get("active_slots", []) if str(s.get("task_id", "")).startswith(JOB_PREFIX)]
            max_task_slots = max(max_task_slots, len(task_slots))
            snapshots.append({"utc": now(), "batch": batch_index, "task_slots": task_slots, "global_active_slots": snap.get("active_slots", [])})
            time.sleep(30)
        for case_id, (proc, log) in children.items():
            proc.wait(); log.close()
            passed, detail = case_result(case_id)
            row = next(r for r in rows if r["geometry_id"] == case_id)
            result = detail.get("result", {})
            entered = bool(result.get("solver_entered", detail.get("failure", {}).get("solver_entered", False)))
            returned = bool(result.get("solver_returned", detail.get("failure", {}).get("solver_returned", False)))
            total_entered += int(entered); total_returned += int(returned)
            row.update({"status": "COMPLETED" if passed else "FAILED_REQUIRES_CHART_REVIEW", "solver_entered": entered, "solver_returned": returned, "post_validated": bool(result.get("load_only_validation", {}).get("ok") is True), "raw_extracted": bool(detail.get("lifecycle", {}).get("raw_truth", {}).get("exists")), "post_fsp": str(OUT / "CASES" / case_id / "post.fsp"), "raw_truth": str(OUT / "CASES" / case_id / f"{case_id}_RAW_TRUTH.npz"), "post_sha256": detail.get("lifecycle", {}).get("post_fsp", {}).get("sha256"), "raw_sha256": detail.get("lifecycle", {}).get("raw_truth", {}).get("sha256"), "completion_state": detail.get("lifecycle", {}).get("slot_release_state"), "controller_returncode": proc.returncode, "log": str(log_dir / f"{case_id}.log")})
            registry.update({"rows": rows, "solver_entries": total_entered, "solver_returned": total_returned, "rerun_delta": 0, "blind_truth_acquired": sum(r["status"] == "COMPLETED" for r in rows)})
            write_json(registry_path, registry)
            if not passed:
                raise RuntimeError(f"{case_id}:FAILED_REQUIRES_CHART_REVIEW; automatic rerun forbidden")
    final_snap = tv.scheduler_snapshot()
    task_active = [s for s in final_snap.get("active_slots", []) if str(s.get("task_id", "")).startswith(JOB_PREFIX)]
    registry.update({"phase": "ACQUISITION_COMPLETE", "finished_utc": now(), "rows": rows, "solver_entries": total_entered, "solver_returned": total_returned, "rerun_delta": 0, "blind_truth_acquired": sum(r["status"] == "COMPLETED" for r in rows), "active_task_slots": task_active})
    write_json(registry_path, registry)
    sched = json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    sched.update({"phase": "ACQUISITION_COMPLETE", "batches": len(batches), "max_concurrent_task_slots": max_task_slots, "samples": snapshots, "active_task_slots_after": task_active, "global_active_slots_after": final_snap.get("active_slots", []), "manual_registry_edit": False, "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": 3, "pass": max_task_slots == 2 and not task_active and total_entered == 8 and total_returned == 8})
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", sched)


def normalize(z: np.ndarray, w: np.ndarray) -> np.ndarray:
    return np.maximum(z, 0.0) / max(float(np.sum(w * np.maximum(z, 0.0))), 1e-300)


def corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) < 1e-14 or np.std(b) < 1e-14:
        return 1.0 if np.allclose(a, b) else 0.0
    return float(np.corrcoef(a, b)[0, 1])


def profile_row(true: np.ndarray, pred_raw: np.ndarray, theta: np.ndarray, lam: float, ux: np.ndarray, w: np.ndarray) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    truth = normalize(true, w)
    physical = normalize(pred_raw, w)
    raw_integral = float(np.sum(w * pred_raw)); truth_integral = float(np.sum(w * true))
    m = 0.5 * (physical + truth); q, r = w * physical, w * truth
    js = 0.5 * np.sum(np.where(q > 0, q * np.log(np.maximum(q, 1e-300) / np.maximum(w * m, 1e-300)), 0.0)) + 0.5 * np.sum(np.where(r > 0, r * np.log(np.maximum(r, 1e-300) / np.maximum(w * m, 1e-300)), 0.0))
    physical_metrics = {"profile_l1": float(np.sum(w * np.abs(physical - truth))), "profile_corr": corr(physical, truth), "profile_js": float(js), "profile_integral_error": abs(float(np.sum(w * physical)) - truth_integral) / max(abs(truth_integral), 1e-300)}
    raw_metrics = {"raw_pca_l1": float(np.sum(w * np.abs(pred_raw - true))), "raw_pca_corr": corr(pred_raw, true), "raw_pca_integral_error": abs(raw_integral - truth_integral) / max(abs(truth_integral), 1e-300)}
    seed = math.degrees(math.asin(lam / LAMBDA_X_NM))
    def derived(z: np.ndarray) -> dict[str, float]:
        pos = float(np.sum(w[ux >= 0] * z[ux >= 0])); neg = float(np.sum(w[ux < 0] * z[ux < 0])); total = max(pos + neg, 1e-300)
        return {"theta_peak": float(theta[int(np.argmax(z))]), "positive_fraction": pos, "negative_fraction": neg, "asymmetry": (pos - neg) / total, **{f"F_seed_{qv}": float(np.sum(w[np.abs(theta - seed) <= qv] * z[np.abs(theta - seed) <= qv])) for qv in (2, 5, 10)}}
    td, pd = derived(truth), derived(physical)
    decision = {f"{k}_error": abs(pd[k] - td[k]) for k in td}
    return physical_metrics, raw_metrics, decision


def aggregate(values: list[float]) -> dict[str, float]:
    return {"mean": float(np.mean(values)), "median": float(np.median(values)), "worst": float(np.max(values))}


def evaluate() -> None:
    registry = json.loads((OUT / "BLIND_ACQUISITION_REGISTRY.json").read_text(encoding="utf-8"))
    if registry.get("blind_truth_acquired") != 8 or registry.get("solver_entries") != 8 or registry.get("solver_returned") != 8 or registry.get("rerun_delta") != 0:
        raise RuntimeError("EVALUATION_GATE_REQUIRES_8_VALIDATED_CASES")
    prediction_csv, prediction_npz = OUT / "BLIND_PREDICTIONS_FROZEN_CHAMPION.csv", OUT / "BLIND_PREDICTIONS_FROZEN_CHAMPION.npz"
    if prediction_csv.exists() or prediction_npz.exists():
        raise RuntimeError("PREDICTION_ARTIFACT_ALREADY_EXISTS_NO_OVERWRITE")
    freeze = verify_preblind()["freeze_fields"]
    with MODEL.open("rb") as f: model_bundle = pickle.load(f)
    with PREPROCESSOR.open("rb") as f: prep = pickle.load(f)
    if model_bundle.get("family") != "Ridge" or model_bundle.get("feature_set") != "RAW" or prep.get("feature_set") != "RAW":
        raise RuntimeError("CHAMPION_PAYLOAD_MISMATCH")
    model = model_bundle["payload"]["model"]
    all_rows = []
    for case_id in [r["geometry_id"] for r in registry["rows"]]:
        all_rows.extend(read_csv(OUT / "CASES" / case_id / "CASE_DATASET_ROWS.csv"))
    if len(all_rows) != 88 or {r["geometry_id"] for r in all_rows} != {r["geometry_id"] for r in registry["rows"]}:
        raise RuntimeError("BLIND_DATASET_SHAPE_OR_IDENTITY_FAILURE")
    write_csv(OUT / "BLIND_DATASET.csv", all_rows)
    write_json(OUT / "BLIND_DATASET_MANIFEST.json", {"schema_version": "BLIND_DATASET_MANIFEST_V1", "rows": len(all_rows), "geometry_count": 8, "wavelengths_nm": WLS.tolist(), "source_case_rows": [str(OUT / "CASES" / r["geometry_id"] / "CASE_DATASET_ROWS.csv") for r in registry["rows"]], "dataset_sha256": sha(OUT / "BLIND_DATASET.csv"), "truth_acquired_after_persistence_gate": True, "blind_truth_used_for_model_selection": False})
    pca = np.load(PCA, allow_pickle=False); grid = np.load(TRAINVAL_ROOT / "CASES" / "K6V1_A03" / "ANGULAR_PROFILE.npz", allow_pickle=False); grid_ux = grid["ux"].astype(float); grid_theta = grid["theta_deg"].astype(float); sqrt_w = np.sqrt(pca["weights_du"].astype(float)); mean_weighted = pca["mean_profile"].astype(float) * sqrt_w; components = pca["components_weighted"].astype(float)
    profile_cache: dict[str, dict[str, np.ndarray]] = {}
    x = np.asarray([[float(r[f"D{i}"]) / 290.0 for i in range(1, 7)] + [(float(r["lambda_nm"]) - 450.0) / 5.0] for r in all_rows])
    z = prep["scaler"].transform(prep["imputer"].transform(x))
    pred_y = prep["target_scaler"].inverse_transform(model.predict(z))
    pred_coeff = pred_y[:, 2:]
    pred_raw = (mean_weighted[None, :] + pred_coeff @ components) / sqrt_w[None, :]
    pred_physical = np.asarray([normalize(row, pca["weights_du"].astype(float)) for row in pred_raw])
    pred_rows = []
    for i, r in enumerate(all_rows):
        item = {"geometry_id": r["geometry_id"], **{f"D{j}": float(r[f"D{j}"]) for j in range(1, 7)}, "lambda_nm": float(r["lambda_nm"]), "G_emit_pred": float(pred_y[i, 0]), "eta_up_pred": float(pred_y[i, 1])}
        item.update({f"pca_{j:02d}": float(pred_coeff[i, j]) for j in range(pred_coeff.shape[1])})
        pred_rows.append(item)
    write_csv(prediction_csv, pred_rows)
    np.savez_compressed(prediction_npz, geometry_ids=np.asarray([r["geometry_id"] for r in all_rows]), wavelengths_nm=np.asarray([float(r["lambda_nm"]) for r in all_rows]), predicted_scalars=pred_y[:, :2], predicted_pca_coefficients=pred_coeff, predicted_profile_raw=pred_raw, predicted_profile_physical=pred_physical, ux=grid_ux, theta_deg=grid_theta, weights_du=pca["weights_du"], model_sha256=np.asarray(sha(MODEL)), pca_sha256=np.asarray(sha(PCA)))
    scalar_rows = []; profile_rows = []; decision_rows = []; spectral_rows = []; per_geometry = []
    grouped: dict[str, dict[str, list[Any]]] = {}
    ux, weights = grid_ux, pca["weights_du"].astype(float)
    for i, r in enumerate(all_rows):
        ref = str(r["angular_profile_ref"]); profile_cache.setdefault(ref, {k: np.asarray(v) for k, v in np.load(ref, allow_pickle=False).items()}); prof = profile_cache[ref]; wi = int(np.argmin(np.abs(prof["wavelengths_nm"] - float(r["lambda_nm"])))) ; theta = prof["theta_deg"][:, wi].astype(float); truth_profile = prof["f_up"][:, wi].astype(float)
        pm, rm, dm = profile_row(truth_profile, pred_raw[i], theta, float(r["lambda_nm"]), ux, weights)
        gid = r["geometry_id"]; grouped.setdefault(gid, {"scalar": {"G_emit": [], "eta_up": []}, "profile": {k: [] for k in pm}, "raw": {k: [] for k in rm}, "decision": {k: [] for k in dm}})
        for name, true_key, pred_key in (("G_emit", "G_emit", "G_emit_pred"), ("eta_up", "eta_up", "eta_up_pred")):
            grouped[gid]["scalar"][name].append((float(r[true_key]), float(pred_y[i, 0 if name == "G_emit" else 1])))
        for k, v in pm.items(): grouped[gid]["profile"][k].append(v)
        for k, v in rm.items(): grouped[gid]["raw"][k].append(v)
        for k, v in dm.items(): grouped[gid]["decision"][k].append(v)
        spectral_rows.append({"geometry_id": gid, "lambda_nm": float(r["lambda_nm"]), "G_emit_true": float(r["G_emit"]), "G_emit_pred": float(pred_y[i, 0]), "eta_up_true": float(r["eta_up"]), "eta_up_pred": float(pred_y[i, 1]), **pm, **rm, **dm})
    decision_macro: dict[str, list[float]] = {}
    for gid, data in grouped.items():
        for name, pairs in data["scalar"].items():
            true = np.asarray([p[0] for p in pairs]); pred = np.asarray([p[1] for p in pairs]); err = pred - true
            scalar_rows.append({"scope": gid, "metric": name, "mae": float(np.mean(np.abs(err))), "rmse": float(np.sqrt(np.mean(err ** 2))), "median_abs_error": float(np.median(np.abs(err))), "r2": float(1.0 - np.sum(err ** 2) / max(np.sum((true - np.mean(true)) ** 2), 1e-300)), "relative_error_mean_safe": float(np.mean(np.abs(err) / np.maximum(np.abs(true), 1e-12)))})
        for k, vals in data["profile"].items(): profile_rows.append({"scope": gid, "space": "PHYSICAL_PROJECTED", "metric": k, **aggregate(vals)})
        for k, vals in data["raw"].items(): profile_rows.append({"scope": gid, "space": "RAW_PCA_RECONSTRUCTION", "metric": k, **aggregate(vals)})
        for k, vals in data["decision"].items():
            decision_rows.append({"scope": gid, "metric": k, **aggregate(vals)})
            decision_macro.setdefault(k, []).extend(vals)
        per_geometry.append({"geometry_id": gid, "G_emit_mae": scalar_rows[-2]["mae"], "eta_up_mae": scalar_rows[-1]["mae"], "profile_l1": float(np.mean(data["profile"]["profile_l1"])), "profile_js": float(np.mean(data["profile"]["profile_js"])), "profile_corr": float(np.mean(data["profile"]["profile_corr"])), "theta_peak_mae_deg": float(np.mean(data["decision"]["theta_peak_error"])), "F_seed_5_mae": float(np.mean(data["decision"]["F_seed_5_error"])), "post_fsp": str(OUT / "CASES" / gid / "post.fsp"), "post_fsp_sha256": sha(OUT / "CASES" / gid / "post.fsp"), "raw_truth": str(OUT / "CASES" / gid / f"{gid}_RAW_TRUTH.npz"), "raw_sha256": sha(OUT / "CASES" / gid / f"{gid}_RAW_TRUTH.npz"), "completion_state": "SLOT_RELEASED"})
    # Geometry-macro rows are computed from the eight per-geometry summaries.
    for name, key in (("G_emit", "G_emit_mae"), ("eta_up", "eta_up_mae")):
        vals = [r[key] for r in per_geometry]; scalar_rows.append({"scope": "BLIND_PROSPECTIVE_GEOMETRY_MACRO", "metric": name, "mae": float(np.mean(vals)), "rmse": float(np.sqrt(np.mean(np.asarray(vals) ** 2))), "median_abs_error": float(np.median(vals)), "r2": None, "relative_error_mean_safe": None})
    for key in ("profile_l1", "profile_js", "profile_corr", "theta_peak_mae_deg", "F_seed_5_mae"):
        vals = [r[key] for r in per_geometry]; profile_rows.append({"scope": "BLIND_PROSPECTIVE_GEOMETRY_MACRO", "space": "PHYSICAL_PROJECTED", "metric": key, **aggregate(vals)})
    for k, vals in decision_macro.items():
        decision_rows.append({"scope": "BLIND_PROSPECTIVE_GEOMETRY_MACRO", "metric": k, **aggregate(vals)})
    write_csv(OUT / "BLIND_METRICS_SCALAR.csv", scalar_rows); write_csv(OUT / "BLIND_METRICS_PROFILE.csv", profile_rows); write_csv(OUT / "BLIND_METRICS_DECISION.csv", decision_rows); write_csv(OUT / "BLIND_SPECTRAL_DIAGNOSTICS.csv", spectral_rows); write_csv(OUT / "BLIND_SPECTRAL_ERROR_ANALYSIS.csv", spectral_rows)
    train_rows = [r for r in read_csv(DOE) if r["split"] == "TRAIN"]; train_vectors = np.asarray([[float(r[f"D{i}_nm"]) for i in range(1, 7)] for r in train_rows]); scale = np.ptp(train_vectors, axis=0); scale[scale == 0] = 1.0
    ood = []
    for row in registry["rows"]:
        v = np.asarray([float(row[f"D{i}"]) for i in range(1, 7)]); distances = np.sqrt(np.sum(((train_vectors - v) / scale) ** 2, axis=1)); ood.append({"geometry_id": row["geometry_id"], "nearest_train_normalized_distance": float(np.min(distances)), "train_geometry_count": len(train_rows), "within_train_axis_bounds": bool(np.all((v >= np.min(train_vectors, axis=0)) & (v <= np.max(train_vectors, axis=0))))})
    write_csv(OUT / "BLIND_OOD_DISTANCE_AUDIT.csv", ood)
    cv = next(r for r in read_csv(PREBLIND_ROOT / "NP_PRIOR_GROUPED_CV_RESULTS.csv") if r["candidate"] == "Ridge_A_RAW"); val = next(r for r in read_csv(PREBLIND_ROOT / "NP_PRIOR_DEVELOPMENT_VALIDATION_RESULTS.csv") if r["candidate"] == "Ridge_A_RAW"); macro_profile = next(r for r in profile_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO" and r["metric"] == "profile_l1"); macro_js = next(r for r in profile_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO" and r["metric"] == "profile_js"); macro_corr = next(r for r in profile_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO" and r["metric"] == "profile_corr"); macro_scalar = {r["metric"]: r for r in scalar_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO"}
    comparison = [{"level": "TRAIN_GROUPED_CV", "profile_l1": float(cv["profile_l1"]), "profile_corr": float(cv["profile_corr"]), "profile_js": float(cv["profile_js"]), "G_emit_mae": float(cv["G_emit_mae"]), "eta_up_mae": float(cv["eta_up_mae"]), "theta_peak_mae": float(cv["theta_peak_mae_deg"]), "F_seed_5_mae": float(cv["F_seed_5_mae"])}, {"level": "DEVELOPMENT_VALIDATION", "profile_l1": float(val["profile_l1"]), "profile_corr": float(val["profile_corr"]), "profile_js": float(val["profile_js"]), "G_emit_mae": float(val["G_emit_mae"]), "eta_up_mae": float(val["eta_up_mae"]), "theta_peak_mae": float(val["theta_peak_mae_deg"]), "F_seed_5_mae": float(val["F_seed_5_mae"])}, {"level": "BLIND_PROSPECTIVE", "profile_l1": macro_profile["mean"], "profile_corr": macro_corr["mean"], "profile_js": macro_js["mean"], "G_emit_mae": macro_scalar["G_emit"]["mae"], "eta_up_mae": macro_scalar["eta_up"]["mae"], "theta_peak_mae": next(r for r in profile_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO" and r["metric"] == "theta_peak_mae_deg")["mean"], "F_seed_5_mae": next(r for r in profile_rows if r["scope"] == "BLIND_PROSPECTIVE_GEOMETRY_MACRO" and r["metric"] == "F_seed_5_mae")["mean"]}]
    write_csv(OUT / "CV_VALIDATION_BLIND_COMPARISON.csv", comparison)
    catastrophic = [r["geometry_id"] for r in per_geometry if r["profile_l1"] > 2.5 * float(val["profile_l1"]) or r["G_emit_mae"] > 3.0 * float(val["G_emit_mae"]) or r["eta_up_mae"] > 3.0 * float(val["eta_up_mae"])]
    scalar_collapse = macro_scalar["G_emit"]["mae"] > 3.0 * float(val["G_emit_mae"]) or macro_scalar["eta_up"]["mae"] > 3.0 * float(val["eta_up_mae"])
    profile_collapse = macro_profile["mean"] > 2.0 * float(val["profile_l1"]) or macro_js["mean"] > 2.0 * float(val["profile_js"]) or macro_corr["mean"] < float(val["profile_corr"]) - 0.25
    verdict = "BLIND_PROSPECTIVE_FAIL" if scalar_collapse or profile_collapse or len(catastrophic) >= 4 else ("BLIND_PROSPECTIVE_PARTIAL" if catastrophic else "BLIND_PROSPECTIVE_PASS")
    write_csv(OUT / "BLIND_PER_GEOMETRY_RESULTS.csv", per_geometry)
    write_json(OUT / "BLIND_ERROR_DIAGNOSTIC_FOR_AL.json", {"schema_version": "BLIND_ERROR_DIAGNOSTIC_FOR_AL_V1", "analysis_only": True, "solver_launched": False, "retraining": False, "high_error_geometries": sorted(per_geometry, key=lambda r: r["profile_l1"], reverse=True), "ood_distance": ood, "spectral_rows": len(spectral_rows), "no_automatic_active_learning": True})
    write_json(OUT / "BLIND_PROSPECTIVE_VERDICT.json", {"schema_version": "BLIND_PROSPECTIVE_VERDICT_V1", "verdict": verdict, "evaluation_timestamp": now(), "model_sha256": sha(MODEL), "pca_sha256": sha(PCA), "dataset_sha256": sha(OUT / "BLIND_DATASET.csv"), "blind_manifest_sha256": sha(SEALED), "scalar_collapse": scalar_collapse, "profile_collapse": profile_collapse, "catastrophic_geometry_ids": catastrophic, "geometry_count": 8, "wavelength_count": 11, "retraining": False, "hyperparameter_change": False, "pca_refit": False, "numerical_floor_context": "approximately 1 percent lateral-aperture numerical-scale evidence; not subtracted from ML error", "comparison": comparison})
    final_sched = json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    report = build_report(verdict, freeze, final_sched, registry, comparison, per_geometry, ood)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": verdict, "verdict": verdict, "champion": "RIDGE_RAW_CHAMPION", "solver_entries": 8, "solver_returned": 8, "rerun_delta": 0, "blind_truth_acquired": 8, "pca_rank": 32, "next": "ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW" if verdict == "BLIND_PROSPECTIVE_PASS" else "TARGETED_ACTIVE_LEARNING_PLAN_FROM_BLIND_ERRORS" if verdict == "BLIND_PROSPECTIVE_PARTIAL" else "SURROGATE_METHOD_REVISION_BEFORE_FURTHER_HF"})


def build_report(verdict: str, freeze: dict[str, Any], scheduler: dict[str, Any], registry: dict[str, Any], comparison: list[dict[str, Any]], per_geometry: list[dict[str, Any]], ood: list[dict[str, Any]]) -> str:
    lines = ["# APCD_COUPLING_V2_2_2D_ML_V1_BLIND_8G_TWO_SLOT_PROSPECTIVE_ACQUISITION_AND_ONESHOT_EVAL_V1", "", "### STATUS", "", verdict, "", "### PREBLIND_FREEZE_VERIFICATION", "", f"PASS; champion=RIDGE_RAW_CHAMPION; model SHA={freeze['model_sha256']}; PCA rank=32; PCA SHA={freeze['pca_sha256']}; no retraining/refit.", "", "### BLIND_GEOMETRIES", "", "8/8 sealed identity + geometry SHA verified; 8/8 retained.", "", "### TWO_SLOT_EXECUTION", "", f"peak task concurrency={scheduler.get('max_concurrent_task_slots')}; batches={scheduler.get('batches')}; resource=12 MPI x 1 thread/job; active task slots after={scheduler.get('active_task_slots_after')}; unrelated global slots may remain occupied.", "", "### SOLVER_ACCOUNTING", "", f"entered={registry.get('solver_entries')}; returned={registry.get('solver_returned')}; failed=0; rerun={registry.get('rerun_delta')}; exactly 8 new entries.", "", "### PERSISTENCE_STATUS", "", "All 8 cases passed canonical post-FSP SHA, independent LOAD-only, raw extraction, completion audit, and scheduler release.", "", "### BLIND_DATASET", "", "8 geometries x 11 wavelengths = 88 rows; blind truth acquired only after persistence validation.", "", "### CHAMPION", "", "RIDGE_RAW_CHAMPION; inputs D1...D6 and lambda only.", "", "### PCA", "", "rank 32; transform-only; no fit/refit/partial_fit.", "", "### CV_VALIDATION_BLIND_COMPARISON", ""]
    lines += [f"{r['level']}: profile_L1={r['profile_l1']}, correlation={r['profile_corr']}, JS={r['profile_js']}, G_emit_MAE={r['G_emit_mae']}, eta_up_MAE={r['eta_up_mae']}, theta_peak_MAE={r['theta_peak_mae']}, F_seed_5_MAE={r['F_seed_5_mae']}." for r in comparison]
    lines += ["", "### PER_GEOMETRY_RESULTS", "", f"{len(per_geometry)} geometry rows in `BLIND_PER_GEOMETRY_RESULTS.csv`; OOD audit rows={len(ood)}.", "", "### GENERALIZATION_GAP", "", "Blind is compared hierarchically with grouped CV and development validation; no single weighted score used.", "", "### NUMERICAL_FLOOR_CONTEXT", "", "Approximately 1% lateral-aperture numerical-scale evidence is reported separately and was not subtracted from ML error.", "", "### RETRAIN_STATUS", "", "NO RETRAINING; NO HYPERPARAMETER CHANGE; NO PCA REFIT.", "", "### AL_DIAGNOSTIC", "", "Analysis-only `BLIND_ERROR_DIAGNOSTIC_FOR_AL.json`; no AL solver launched.", "", "### ARTIFACTS", "", f"Output namespace: `{OUT}`; post/raw/lifecycle artifacts are under `CASES/<geometry_id>/`.", "", "### SCHEDULER_RELEASE", "", f"active task slots={scheduler.get('active_task_slots_after')}; manual registry edit=False.", "", "### GIT_AUDIT", "", "No commit, push, reset, restore, clean, stash, rebase, amend, or force push.", "", "### PROPOSED_VERDICT", "", f"PASS — BLIND_8G_PROSPECTIVE_ACQUISITION_RECOVERED_AND_EVALUATED" if verdict == "BLIND_PROSPECTIVE_PASS" else verdict, "", "### NEXT", "", "ACTIVE_LEARNING_AND_INVERSE_DESIGN_READINESS_REVIEW" if verdict == "BLIND_PROSPECTIVE_PASS" else "TARGETED_ACTIVE_LEARNING_PLAN_FROM_BLIND_ERRORS" if verdict == "BLIND_PROSPECTIVE_PARTIAL" else "SURROGATE_METHOD_REVISION_BEFORE_FURTHER_HF", ""]
    return "\n".join(lines)


def final_manifest() -> None:
    files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files.append({"path": str(path.relative_to(OUT)).replace("\\", "/"), "size": path.stat().st_size, "sha256": sha(path)})
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--evaluate", action="store_true")
    parser.add_argument("--run-case")
    args = parser.parse_args()
    if args.run_case:
        return run_case(args.run_case)
    if args.preflight:
        preflight(); print(json.dumps({"status": "PREFLIGHT_PASS", "solver_entries": 0, "blind_truth_acquired": 0}, ensure_ascii=False)); return 0
    if args.acquire:
        acquire(); return 0
    if args.evaluate:
        evaluate(); final_manifest(); print(json.dumps(json.loads((OUT / "REPORT.json").read_text(encoding="utf-8")), ensure_ascii=False)); return 0
    parser.error("--preflight, --acquire, --evaluate, or --run-case required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
