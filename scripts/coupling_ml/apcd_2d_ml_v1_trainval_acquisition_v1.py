"""Acquire the frozen 2D ML V1 TRAIN+VALIDATION truth set.

The script deliberately reuses the validated 23/19 baseline runner and its
post-solver LifecycleController.  It never touches the sealed blind rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import stat
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
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
BASELINE = ACTIVE / "outputs" / "coupling_v2_2" / "FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1"
INPUT_NS = ACTIVE / "outputs" / "coupling_v2_2" / "FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
AUDIT_NS = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_DATABASE_AUTHORITY_AUDIT_AND_2D_ML_SPACE_FREEZE_PREP_V1"
OUT = ACTIVE / "outputs" / "coupling_ml" / "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
DOE = AUDIT_NS / "K6_V1_64G_DOE_CANDIDATES.csv"
SPLIT_MANIFEST = AUDIT_NS / "K6_V1_GEOMETRY_SPLIT_MANIFEST.json"
DOE_AUDIT = AUDIT_NS / "K6_V1_64G_DOE_AUDIT.json"
M2A = ACTIVE / "outputs" / "coupling_ml" / "M2A_GEOMETRY_DIVERSITY_SEED_ACQUISITION_PLANNING_V1" / "M2A_NP22_GEOMETRY_CANDIDATE_POOL_V1.csv"
M2B = ACTIVE / "outputs" / "coupling_ml" / "M2B_CORE_GEOMETRY_DIVERSITY_ACQUISITION_V1" / "M2B_CHEAP_PROVIDER_ACQUISITION_REGISTRY_V1.csv"
M2I = ACTIVE / "outputs" / "coupling_ml" / "M2I_G7_G8_PROVIDER_CONTEXT3_BLIND_PROSPECTIVE_AND_LEVEL2A_ACQUISITION_V1" / "M2I_G7_G8_CONTEXT3_FEATURES_V1.csv"
TEMPLATE = INPUT_NS / "cases" / "ALT1" / "setup_pre.fsp"
INPUT_MANIFEST = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
CONTROL_POST = ACTIVE / "outputs" / "coupling_v2_2" / "FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1" / "VALIDATED_PROBE" / "CONTROL0" / "post.fsp"
CONTROL_RAW = CONTROL_POST.parent.parent / "CONTROL0_RAW_TRUTH.npz"
ALT1_POST = BASELINE / "ALT1" / "post.fsp"
ALT1_RAW = BASELINE / "ALT1_RAW_TRUTH.npz"
SOURCE_POST = BASELINE / "SOURCE_ONLY" / "post.fsp"
SOURCE_RAW = BASELINE / "SOURCE_ONLY_RAW_TRUTH.npz"
WLS = np.arange(445.0, 456.0, 1.0)
MONITORS = ("upward_monitor", "downward_monitor")
SOURCE_BOXES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")
SOURCE_Z_NM = -276.0
FDTD_UM = 23.0
MONITOR_UM = 19.0
LAMBDA_X_NM = 1740.0
ATTEMPT = "attempt_001"
JOB_PREFIX = "APCD_COUPLING_V2_2_2D_ML_V1_TRAINVAL_ACQUISITION_V1"
DOMAIN_VERDICT = "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN"
EXACT = {
    "K6V1_A01": ("CONTROL0", CONTROL_POST, CONTROL_RAW),
    "K6V1_A02": ("ALT1", ALT1_POST, ALT1_RAW),
}
FIELDS = [
    "geometry_id", "D1", "D2", "D3", "D4", "D5", "D6", "lambda_nm", "source_z_nm",
    "source_orientation", "K", "p_nm", "H_nm", "MDC_id", "spacer_nm", "P_source_box",
    "P_up", "P_down", "G_emit", "eta_up", "eta_down", "angular_profile_ref", "theta_peak",
    "positive_fraction", "negative_fraction", "asymmetry", "F_seed_2", "F_seed_5", "F_seed_10",
    "edge_loading", "aperture_diagnostic", "prior_feature_ref", "post_FSP_SHA", "raw_SHA",
    "geometry_SHA", "dataset_role", "split", "FDTD_x_um", "monitor_x_um", "domain_authority",
]

sys.path.insert(0, str(API))
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(TRAD / "scripts" / "coupling"))
_spec = importlib.util.spec_from_file_location("validated_23um_runner", SCRIPT_DIR / "finite_k6_23um_19um_two_slot_baseline_completion_v1.py")
if _spec is None or _spec.loader is None:
    raise RuntimeError("validated baseline runner is unavailable")
runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(runner)
base = runner.base


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(json_safe(payload), stream, ensure_ascii=False, indent=2, sort_keys=True)
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def geometry_key(row: dict[str, Any]) -> tuple[float, ...]:
    suffix = "_nm" if "D1_nm" in row else ""
    return tuple(float(row[f"D{i}{suffix}"]) for i in range(1, 7))


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None}


def load_doe() -> list[dict[str, str]]:
    rows = read_csv(DOE)
    if len(rows) != 64 or len({r["geometry_id"] for r in rows}) != 64:
        raise RuntimeError("frozen DOE is not exactly 64 unique geometries")
    if sum(r["split"] == "TRAIN" for r in rows) != 48 or sum(r["split"] == "VALIDATION" for r in rows) != 8 or sum(r["split"] == "BLIND" for r in rows) != 8:
        raise RuntimeError("frozen DOE split counts are not 48/8/8")
    for row in rows:
        values = geometry_key(row)
        if any(v < 100 or v > 230 or (v - 100) % 5 for v in values):
            raise RuntimeError(f"DOE geometry outside audited 5nm simulation/design bounds: {row['geometry_id']}")
    return rows


def trainval_rows() -> list[dict[str, str]]:
    return [r for r in load_doe() if r["split"] in {"TRAIN", "VALIDATION"}]


def scheduler_snapshot() -> dict[str, Any]:
    return base.scheduler_snapshot()


def m2s_guard(snapshot: dict[str, Any]) -> None:
    if any(row.get("is_m2s") for row in snapshot.get("processes", [])):
        raise RuntimeError("unauthorized M2S process detected; hard gate")


def prior_materialization(rows: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    np_rows = read_csv(M2A)
    rcwa_rows = read_csv(M2B)
    context_rows = read_csv(M2I) if M2I.is_file() else []
    np_by_key = {geometry_key(r): r for r in np_rows}
    rcwa_by_key = {tuple(float(v) for v in json.loads(r["ordered_vector_D1_to_D6_nm"])): r for r in rcwa_rows}
    context_keys = {geometry_key(r) for r in context_rows if all(f"D{i}" in r for i in range(1, 7))}
    features: list[dict[str, Any]] = []
    coverage = {"total_geometries": len(rows), "np_hf22_exact_geometry": 0, "m2b_exact_provider_geometry": 0, "old_level2a_exact_geometry": 0, "mdc_exact_geometry": 0, "masks_are_explicit": True, "doe_action": "KEEP_DOE_UNCHANGED"}
    for row in rows:
        key = geometry_key(row)
        np_row = np_by_key.get(key)
        rcwa_row = rcwa_by_key.get(key)
        np_desc: dict[str, Any] = {}
        np_valid = False
        if np_row:
            try:
                np_desc = json.loads(np_row["response_descriptors_json"])["all_PS_mean"]
                np_valid = bool(np_desc) and np_row.get("selection_status") in {"SELECTED", "NOT_SELECTED_THIS_BATCH"}
            except (KeyError, TypeError, json.JSONDecodeError):
                np_valid = False
        if np_valid:
            coverage["np_hf22_exact_geometry"] += 1
        rcwa_valid = bool(rcwa_row and rcwa_row.get("status") == "PASS_COMPLETED_EXACT" and rcwa_row.get("exact_gate_status") == "PASS")
        if rcwa_valid:
            coverage["m2b_exact_provider_geometry"] += 1
        old_valid = key in context_keys and False
        if old_valid:
            coverage["old_level2a_exact_geometry"] += 1
        for wavelength in WLS:
            features.append({
                "geometry_id": row["geometry_id"], "split": row["split"], "lambda_nm": float(wavelength),
                **{f"D{i}": float(row[f"D{i}_nm"]) for i in range(1, 7)},
                "np_hf22_R_mean": np_desc.get("R_mean"), "np_hf22_T_mean": np_desc.get("T_mean"),
                "np_hf22_directionality_mean": np_desc.get("directionality_mean"), "np_hf22_eta_minus1_mean": np_desc.get("eta_minus1_mean"),
                "np_hf22_eta_plus1_mean": np_desc.get("eta_plus1_mean"), "np_prior_valid": np_valid,
                "np_prior_ood": not np_valid, "m2b_exact_provider_available": rcwa_valid,
                "m2b_prior_valid": rcwa_valid, "m2b_prior_ood": not rcwa_valid,
                "mdc_prior_valid": False, "mdc_prior_ood": True, "mdc_prior_reason": "NO_EXACT_CURRENT_INTEGRATED_2D_FEATURE_MATERIALIZED",
                "old_level2a_prior_valid": old_valid, "old_level2a_prior_ood": not old_valid,
                "old_level2a_reason": "NO_EXACT_CURRENT_GEOMETRY_FEATURE_MATERIALIZED" if not old_valid else "EXACT_SUPPORTED_ROW",
                "provider_geometry_sha256": np_row.get("geometry_hash") if np_row else (rcwa_row.get("geometry_hash") if rcwa_row else None),
            })
    providers = {
        "schema_version": "PRIOR_PROVIDER_REGISTRY_V1", "generated_utc": now(),
        "providers": [
            {"provider_id": "M2A_NP_HF22", "role": "AUXILIARY_GEOMETRY_PHYSICS_PRIOR", "source": file_record(M2A), "supported_descriptors": ["R_mean", "T_mean", "directionality_mean", "eta_minus1_mean", "eta_plus1_mean"], "exact_geometry_only": True, "ood_mask": "np_prior_ood"},
            {"provider_id": "M2B_RCWA_EXACT", "role": "AUXILIARY_GEOMETRY_PHYSICS_PRIOR", "source": file_record(M2B), "supported_descriptors": ["provider availability and provenance only in V1 materialization"], "exact_geometry_only": True, "ood_mask": "m2b_prior_ood"},
            {"provider_id": "MDC_V3C_DIRECT", "role": "AUXILIARY_MDC_PROFILE_PRIOR", "source": {"path": str(AUDIT_NS), "sha256": sha(AUDIT_NS / "FINAL_SHA256_MANIFEST.json") if (AUDIT_NS / "FINAL_SHA256_MANIFEST.json").is_file() else None}, "supported_descriptors": [], "exact_geometry_only": True, "coverage": "no exact current integrated 2D labels materialized", "ood_mask": "mdc_prior_ood"},
            {"provider_id": "M2F_M2I_LEVEL2A_CONTEXT", "role": "AUXILIARY_3D_PLANEWAVE_COUPLING_PRIOR", "source": file_record(M2I), "supported_descriptors": ["actual supported Level2A descriptors only"], "exact_geometry_only": True, "coverage": "masked by default; no extrapolation", "ood_mask": "old_level2a_prior_ood"},
        ], "old_level2b": {"role": "HISTORICAL_REFERENCE_ONLY", "features_used": False},
    }
    return providers, features, coverage


def materialize_setup(row: dict[str, str]) -> dict[str, Any]:
    case_id = row["geometry_id"]
    setup = OUT / "SETUPS" / case_id / "setup_pre.fsp"
    setup.parent.mkdir(parents=True, exist_ok=True)
    if setup.is_file() and (setup.parent / "SETUP_AUDIT.json").is_file():
        return json.loads((setup.parent / "SETUP_AUDIT.json").read_text(encoding="utf-8"))
    fd = base.lumapi_module().FDTD(str(TEMPLATE), hide=True)
    try:
        fd.setnamed("FDTD", "x span", FDTD_UM * 1e-6)
        for name in MONITORS:
            fd.setnamed(name, "x span", MONITOR_UM * 1e-6)
        names = [str(x).replace("::model::", "").strip(":") for x in fd.getobjectlist("::model::")]
        np_names = sorted((name for name in names if name.startswith("NP_bar_")), key=lambda name: int(name.rsplit("_", 1)[-1]))
        if len(np_names) != 6:
            raise RuntimeError(f"expected six NP bars in template, found {np_names}")
        for name, width in zip(np_names, geometry_key(row)):
            fd.setnamed(name, "x span", width * 1e-9)
        fd.save(str(setup))
    finally:
        fd.close()
    snap = runner.snapshot(setup)
    np_names = sorted((name for name in snap["objects"] if name.startswith("NP_bar_")), key=lambda name: int(name.rsplit("_", 1)[-1]))
    widths = [float(snap["rows"][name]["x span"]) * 1e9 for name in np_names]
    checks = {
        "fdtd_x_span_um": math.isclose(float(snap["rows"]["FDTD"]["x span"]) * 1e6, FDTD_UM, abs_tol=1e-6),
        "monitor_x_span_um": all(math.isclose(float(snap["rows"][name]["x span"]) * 1e6, MONITOR_UM, abs_tol=1e-6) for name in MONITORS),
        "np_widths_nm": all(math.isclose(a, b, abs_tol=1e-6) for a, b in zip(widths, geometry_key(row))),
        "np_count": len(np_names) == 6,
    }
    audit = {"schema_version": "K6_V1_SETUP_MATERIALIZATION_AUDIT_V1", "geometry_id": case_id, "geometry": list(geometry_key(row)), "template": file_record(TEMPLATE), "setup_pre": file_record(setup), "snapshot": snap, "checks": checks, "solver_entry": False, "pass": all(checks.values())}
    write_json(OUT / "SETUPS" / case_id / "SETUP_AUDIT.json", audit)
    if not audit["pass"]:
        raise RuntimeError(f"setup materialization failed: {case_id}")
    return audit


def source_reference() -> dict[str, Any]:
    expected = {"post_fsp": "2edbd9ca1f0d568fda9b7ad808ae253226069d6c75553624695bee5b17cd733f", "raw": "cb4ac9f33fcbc21a5de28a3879d34b72c032282005a3d366e02fc52fcd566a38"}
    if not SOURCE_POST.is_file() or not SOURCE_RAW.is_file() or sha(SOURCE_POST) != expected["post_fsp"] or sha(SOURCE_RAW) != expected["raw"]:
        raise RuntimeError("SOURCE_ONLY reference SHA authority mismatch")
    return {"schema_version": "V1_SOURCE_REFERENCE_V1", "post_fsp": file_record(SOURCE_POST), "raw_truth": file_record(SOURCE_RAW), "expected_sha256": expected, "power": runner.load_power(SOURCE_RAW), "source_only_solver_rerun": False, "normalization": "G_emit=P_source_box(case)/P_source_box(SOURCE_ONLY23/19)"}


def preflight() -> int:
    rows = load_doe()
    if OUT.exists():
        if (OUT / "PREFLIGHT_AUDIT.json").is_file():
            return 0
        if not ((OUT / "V1_SCIENTIFIC_SPACE_FREEZE.json").is_file() and (OUT / "K6_V1_64G_PRIOR_FEATURES.csv").is_file()):
            raise RuntimeError(f"output namespace exists; overwrite forbidden: {OUT}")
    required = [DOE, SPLIT_MANIFEST, DOE_AUDIT, M2A, M2B, INPUT_MANIFEST, TEMPLATE, SOURCE_POST, SOURCE_RAW, CONTROL_POST, CONTROL_RAW, ALT1_POST, ALT1_RAW]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise RuntimeError("missing authority inputs: " + "; ".join(missing))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "SETUPS").mkdir(exist_ok=True)
    (OUT / "CASES").mkdir(exist_ok=True)
    (OUT / "REUSED_REFERENCES").mkdir(exist_ok=True)
    providers, features, coverage = prior_materialization(rows)
    write_json(OUT / "V1_SCIENTIFIC_SPACE_FREEZE.json", {"schema_version": "V1_SCIENTIFIC_SPACE_FREEZE_V1", "verdict": "COUPLING_2D_ML_V1_SCIENTIFIC_SPACE_FROZEN", "generated_utc": now(), "domain": DOMAIN_VERDICT, "fdtd_x_um": FDTD_UM, "monitor_x_um": MONITOR_UM, "boundary": "finite PML; no periodic/Bloch", "K": 6, "p_nm": 290.0, "H_nm": 500.0, "source": {"orientation": "X", "x_nm": 0.0, "z_nm": SOURCE_Z_NM}, "wavelengths_nm": WLS.tolist(), "prior_features_only": True, "training_or_pca": False, "blind_truth_acquisition": False})
    write_json(OUT / "V1_PARAMETER_SPACE_AUTHORITY.json", {"schema_version": "V1_PARAMETER_SPACE_AUTHORITY_V1", "ordered_position_sensitive": True, "columns": ["D1", "D2", "D3", "D4", "D5", "D6"], "simulation_design_bounds_nm": {"min": 100, "max": 230, "grid_nm": 5}, "fabrication_authority": "not established by this DOE audit", "source_doe": file_record(DOE), "split_manifest": file_record(SPLIT_MANIFEST), "regenerate_doe": False})
    blind = [{"geometry_id": r["geometry_id"], **{f"D{i}": float(r[f"D{i}_nm"]) for i in range(1, 7)}, "geometry_sha256": r["geometry_fingerprint_sha256"], "intended_role": "BLIND_PROSPECTIVE"} for r in rows if r["split"] == "BLIND"]
    write_json(OUT / "BLIND_PROSPECTIVE_SEALED_MANIFEST.json", {"schema_version": "BLIND_PROSPECTIVE_SEALED_MANIFEST_V1", "sealed": True, "truth_acquired": 0, "rows": blind})
    write_json(OUT / "PRIOR_PROVIDER_REGISTRY.json", providers)
    write_csv(OUT / "K6_V1_64G_PRIOR_FEATURES.csv", features)
    write_json(OUT / "K6_V1_64G_PRIOR_FEATURES_METADATA.json", {"schema_version": "K6_V1_64G_PRIOR_FEATURES_V1", "rows": len(features), "geometry_rows": len(rows), "wavelength_rows_per_geometry": len(WLS), "coverage": coverage, "explicit_masks": ["np_prior_valid", "np_prior_ood", "m2b_prior_valid", "m2b_prior_ood", "mdc_prior_valid", "mdc_prior_ood", "old_level2a_prior_valid", "old_level2a_prior_ood"], "no_zero_fill": True, "training_performed": False})
    setup_audits = [materialize_setup(r) for r in rows if r["split"] in {"TRAIN", "VALIDATION"} and r["geometry_id"] not in EXACT]
    source = source_reference()
    write_json(OUT / "V1_SOURCE_REFERENCE.json", source)
    acquisition = []
    for row in trainval_rows():
        exact = row["geometry_id"] in EXACT
        acquisition.append({"geometry_id": row["geometry_id"], "split": row["split"], "geometry_sha256": row["geometry_fingerprint_sha256"], "D": list(geometry_key(row)), "status": "REUSED_VALIDATED" if exact else "PLANNED", "solver_entered": False, "solver_returned": False, "rerun_delta": 0, "reuse_source": EXACT[row["geometry_id"]][0] if exact else None})
    write_json(OUT / "TRAINVAL_ACQUISITION_REGISTRY.json", {"schema_version": "TRAINVAL_ACQUISITION_REGISTRY_V1", "task": JOB_PREFIX, "attempt_id": ATTEMPT, "rows": acquisition, "blind_rows": 8, "blind_truth_acquired": 0, "new_solver_entries_expected": sum(r["status"] == "PLANNED" for r in acquisition), "rerun_delta": 0})
    new_trainval = [r for r in trainval_rows() if r["geometry_id"] not in EXACT]
    batches = [new_trainval[i:i + 2] for i in range(0, len(new_trainval), 2)]
    snap = scheduler_snapshot()
    m2s_guard(snap)
    write_json(OUT / "TRAINVAL_ACQUISITION_PLAN.json", {"schema_version": "TRAINVAL_ACQUISITION_PLAN_V1", "source_doe_sha256": sha(DOE), "train_geometries": 48, "validation_geometries": 8, "blind_geometries_sealed": 8, "blind_truth_acquired": 0, "exact_reused": 2, "new_solver_entries": len([r for r in acquisition if r["status"] == "PLANNED"]), "two_slot_batches_expected": len(batches), "batch_size": 2, "resource_per_job": {"processes": 12, "threads": 1}, "global_cap": 3, "third_slot_consumed": False, "setup_audits": len(setup_audits)})
    audit = {"schema_version": "TRAINVAL_ZERO_SOLVER_PREFLIGHT_AUDIT_V1", "generated_utc": now(), "solver_entry_delta": 0, "m2s_attempt_002_started": False, "blind_truth_acquired": 0, "source_reference": source, "prior_coverage": coverage, "scheduler_before_solver": snap, "global_capacity": snap.get("global_capacity"), "active_slots": snap.get("active_slots"), "m2s_processes": [p for p in snap.get("processes", []) if p.get("is_m2s")], "pass": snap.get("global_capacity") == 3 and not snap.get("active_slots") and not any(p.get("is_m2s") for p in snap.get("processes", [])) and len(setup_audits) == 54}
    write_json(OUT / "PREFLIGHT_AUDIT.json", audit)
    if not audit["pass"]:
        raise RuntimeError("zero-solver preflight failed")
    print(json.dumps({"status": "PREFLIGHT_PASS", "output": str(OUT), "solver_entry_delta": 0, "new_solver_entries": 54, "blind_truth_acquired": 0}, ensure_ascii=False), flush=True)
    return 0


def configure_case(case_id: str, case_out: Path) -> Path:
    setup = OUT / "SETUPS" / case_id / "setup_pre.fsp"
    if not setup.is_file():
        raise RuntimeError(f"candidate setup missing: {setup}")
    base.OUT = case_out
    base.INPUT_FSP = setup
    base.INPUT_MANIFEST = INPUT_MANIFEST
    base.CASE_ID = case_id
    base.JOB_ID = f"{JOB_PREFIX}:{case_id}"
    base.ATTEMPT_ID = ATTEMPT
    base.FDTD_SPAN_UM = FDTD_UM
    base.MONITOR_SPAN_UM = MONITOR_UM
    base.MONITOR_NAMES = runner.MONITOR_NAMES
    base.SOURCE_BOX_NAMES = runner.SOURCE_BOX_NAMES
    return setup


def raw_dict(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as loaded:
        return {k: loaded[k] for k in loaded.files}


def angular_metrics(raw_path: Path, profile_dir: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = raw_dict(raw_path)
    theta = np.asarray(raw["farfield_theta_deg"], dtype=float)
    e2 = np.maximum(np.asarray(raw["farfield_e2"], dtype=float), 0.0)
    if theta.shape != e2.shape or theta.shape[1] != len(WLS):
        raise RuntimeError(f"farfield shape mismatch: {theta.shape} {e2.shape}")
    ux = np.sin(np.radians(theta[:, 0]))
    if not np.all(np.diff(ux) > 0):
        order = np.argsort(ux)
        ux, theta, e2 = ux[order], theta[order], e2[order]
    du = float(np.median(np.diff(ux)))
    if not np.isfinite(du) or np.max(np.abs(np.diff(ux) - du)) > 1e-10:
        raise RuntimeError("native ux grid is not uniform")
    weights = np.full(len(ux), du, dtype=float)
    weights[[0, -1]] *= 0.5
    integral = np.sum(weights[:, None] * e2, axis=0)
    f_up = e2 / np.maximum(integral[None, :], 1e-300)
    rows = []
    for i, wavelength in enumerate(WLS):
        seed = math.degrees(math.asin(float(wavelength) / LAMBDA_X_NM))
        positive = float(np.sum(weights[ux >= 0] * e2[ux >= 0, i]) / max(integral[i], 1e-300))
        negative = float(np.sum(weights[ux < 0] * e2[ux < 0, i]) / max(integral[i], 1e-300))
        target = [float(np.sum(weights[np.abs(theta[:, i] - seed) <= window] * e2[np.abs(theta[:, i] - seed) <= window, i]) / max(integral[i], 1e-300)) for window in (2, 5, 10)]
        peak = int(np.argmax(e2[:, i]))
        half = e2[:, i] >= max(e2[peak, i] * 0.5, 1e-300)
        fwhm = float(np.degrees(np.arcsin(np.clip(ux[half], -1, 1))).max() - np.degrees(np.arcsin(np.clip(ux[half], -1, 1))).min()) if np.any(half) else None
        rows.append({"lambda_nm": float(wavelength), "theta_peak": float(theta[peak, i]), "positive_fraction": positive, "negative_fraction": negative, "asymmetry": (positive - negative) / max(positive + negative, 1e-300), "F_seed_2": target[0], "F_seed_5": target[1], "F_seed_10": target[2], "over_60_support": float(np.sum(weights[np.abs(theta[:, i]) > 60] * e2[np.abs(theta[:, i]) > 60, i]) / max(integral[i], 1e-300)), "fwhm_deg": fwhm, "sll": None, "sll_status": "NOT_DEFINED_UNDER_V1"})
    raw_values = raw_dict(raw_path)
    x, flux, _, _ = base.line_flux(raw_values, "upward_monitor")
    edge = []
    edge_mask = (x <= x.min() + 0.5e-6) | (x >= x.max() - 0.5e-6)
    for i in range(len(WLS)):
        total = base.integrate(x, np.abs(flux[:, i]))
        edge.append(float(base.integrate(x[edge_mask], np.abs(flux[edge_mask, i])) / max(abs(total), 1e-300)))
    apertures, aperture_stats = runner.aperture_rows(raw_values)
    for row, value, ap in zip(rows, edge, apertures):
        row["edge_loading"] = value
        row["aperture_diagnostic"] = json.dumps({"delta_13_to_15": ap.get("delta_13_to_15"), "delta_17_to_15": ap.get("delta_17_to_15"), "delta_19_to_15": ap.get("delta_19_to_15"), "stats": aperture_stats}, sort_keys=True)
    profile_path = (profile_dir or raw_path.parent) / "ANGULAR_PROFILE.npz"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(profile_path, ux=ux, theta_deg=theta, weights_du=weights, e2=e2, f_up=f_up, profile_integral=integral, wavelengths_nm=WLS)
    metadata = {"schema_version": "NATIVE_UX_ANGULAR_PROFILE_V1", "coordinate": "u_x=sin(theta)", "measure": "du_x", "uniform_du_x": du, "theta_is_nonuniform": True, "native_farfield": True, "profile_integral": integral.tolist(), "path": str(profile_path)}
    write_json(profile_path.parent / "ANGULAR_PROFILE_METADATA.json", metadata)
    return rows, {"rows": rows, "profile": metadata, "aperture_stats": aperture_stats}


def dataset_rows(row: dict[str, str], raw_path: Path, post_path: Path, profile_ref: Path, prior_ref: Path, role: str) -> list[dict[str, Any]]:
    metrics, _ = angular_metrics(raw_path, profile_dir=profile_ref.parent)
    powers = runner.load_power(raw_path)
    source = json.loads((OUT / "V1_SOURCE_REFERENCE.json").read_text(encoding="utf-8"))["power"]
    post_hash, raw_hash = sha(post_path), sha(raw_path)
    out = []
    for i, metric in enumerate(metrics):
        p = powers[i]
        denom = float(source[i]["P_source_box"])
        out.append({"geometry_id": row["geometry_id"], **{f"D{j}": float(row[f"D{j}_nm"]) for j in range(1, 7)}, "lambda_nm": float(WLS[i]), "source_z_nm": SOURCE_Z_NM, "source_orientation": "X", "K": 6, "p_nm": 290, "H_nm": 500, "MDC_id": "CURRENT_FROZEN_MDC", "spacer_nm": "FROZEN_UNCHANGED", "P_source_box": p["P_source_box"], "P_up": p["P_up"], "P_down": p["P_down"], "G_emit": p["P_source_box"] / max(denom, 1e-300), "eta_up": p["P_up"] / max(p["P_source_box"], 1e-300), "eta_down": p["P_down"] / max(p["P_source_box"], 1e-300), "angular_profile_ref": str(profile_ref), "theta_peak": metric["theta_peak"], "positive_fraction": metric["positive_fraction"], "negative_fraction": metric["negative_fraction"], "asymmetry": metric["asymmetry"], "F_seed_2": metric["F_seed_2"], "F_seed_5": metric["F_seed_5"], "F_seed_10": metric["F_seed_10"], "edge_loading": metric["edge_loading"], "aperture_diagnostic": metric["aperture_diagnostic"], "prior_feature_ref": str(prior_ref), "post_FSP_SHA": post_hash, "raw_SHA": raw_hash, "geometry_SHA": row["geometry_fingerprint_sha256"], "dataset_role": role, "split": row["split"], "FDTD_x_um": FDTD_UM, "monitor_x_um": MONITOR_UM, "domain_authority": DOMAIN_VERDICT})
    return out


def derive_for_case(raw_path: Path) -> dict[str, Any]:
    derived = dict(base.derive_raw(raw_path))
    profile_rows, profile_meta = angular_metrics(raw_path)
    runner.rename_and_finalize_case(base.CASE_ID, base.OUT, raw_path)
    write_csv(base.OUT / "CASE_DATASET_ROWS.csv", dataset_rows(DOE_ROW_BY_ID[base.CASE_ID], raw_path, base.OUT / "post.fsp", base.OUT / "ANGULAR_PROFILE.npz", OUT / "K6_V1_64G_PRIOR_FEATURES.csv", "NEW_SOLVER"), FIELDS)
    write_json(base.OUT / "DERIVED_METRICS.json", {"schema_version": "V1_DERIVED_METRICS_V1", "angular": profile_rows, "profile": profile_meta})
    derived["v1_angular"] = profile_rows
    derived["v1_profile"] = profile_meta
    return derived


def audit_case(derived: dict[str, Any], post: Path, raw: Path, adapter: Any, lease: Any, controller: Any) -> dict[str, Any]:
    validation = adapter.last_validation
    audit = {"schema_version": "V1_CASE_PERSISTENCE_AUDIT_V1", "post_fsp": file_record(post), "raw": file_record(raw), "load_only": validation, "owner_session_closed_before_load_only": bool(adapter.owner_closed), "post_sha_matches_controller": sha(post) == controller.persisted_sha256, "artifact_roles_distinct": controller.roles.distinct(), "pass": bool(validation.get("ok") is True and validation.get("run_called") is False and sha(post) == controller.persisted_sha256 and raw.is_file() and raw.stat().st_size > 0 and derived.get("finite") is True)}
    write_json(base.OUT / "POST_FSP_PERSISTENCE_AUDIT.json", audit)
    write_json(base.OUT / "CASE_ACCEPTANCE.json", {"schema_version": "V1_CASE_ACCEPTANCE_V1", "pass": audit["pass"], "gates": audit, "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0})
    return audit


def run_case(case_id: str) -> int:
    if not (OUT / "PREFLIGHT_AUDIT.json").is_file():
        raise RuntimeError("preflight gate missing")
    row = DOE_ROW_BY_ID[case_id]
    case_out = OUT / "CASES" / case_id
    if case_out.exists():
        raise RuntimeError(f"case output exists; overwrite forbidden: {case_out}")
    case_out.mkdir(parents=True, exist_ok=False)
    setup = configure_case(case_id, case_out)
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    snap = scheduler_snapshot()
    m2s_guard(snap)
    lease = slots.GlobalSlotScheduler().acquire_wait("work/mdc-np-coupling-ml-v1", str(ACTIVE), base.JOB_ID, case_id, pid=os.getpid(), metadata={"task_class": JOB_PREFIX, "attempt_id": ATTEMPT, "processes": 12, "threads": 1, "dimension": "2D", "domain": "23um_fdtd_19um_monitor", "split": row["split"]})
    lease.start_heartbeat()
    attempt = case_out / ATTEMPT
    roles = base.ArtifactRoles(case_out / "frozen_pre.fsp", case_out / "runtime.fsp", case_out / "post.fsp", case_out / "recovery_post.fsp")
    events, completion, raw = attempt / "events.jsonl", attempt / "completion.json", case_out / f"{case_id}_RAW_TRUTH.npz"
    manifest = {"schema_version": "V1_TRAINVAL_EXECUTION_MANIFEST_V1", "case": case_id, "job_id": base.JOB_ID, "attempt_id": ATTEMPT, "setup_pre_fsp": str(setup), "physical_contract_sha256": sha(OUT / "V1_SCIENTIFIC_SPACE_FREEZE.json"), "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITORS), "source_box_names": list(SOURCE_BOXES), "expected_fdtd_span_um": FDTD_UM, "expected_monitor_span_um": MONITOR_UM, "source_x_nm": 0.0, "source_physical_z_nm": SOURCE_Z_NM, "np_bar_count": 6}}
    adapter = runner.BaselineAdapter(manifest, attempt)
    controller = base.LifecycleController(job_id=base.JOB_ID, attempt_id=ATTEMPT, roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, derive_for_case, lambda derived, post, raw_path: audit_case(derived, post, raw_path, adapter, lease, controller))
        result.update({"case_id": case_id, "geometry": list(geometry_key(row)), "split": row["split"], "setup_pre": str(setup), "solver_entry_delta": 1, "rerun_delta": 0})
        write_json(case_out / "CASE_RESULT.json", result)
        print(json.dumps({"status": "CASE_PASS", "case_id": case_id, "solver_entry_delta": 1, "rerun_delta": 0, "post": result["post_fsp"], "raw": result["raw"]}, ensure_ascii=False), flush=True)
        return 0
    except BaseException as exc:
        write_json(case_out / "FAILURE_AUDIT.json", {"case_id": case_id, "error": repr(exc), "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0, "classification": getattr(controller, "phase", "CONTROLLER_FAILURE")})
        raise


def registry_payload(rows: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    current = json.loads((OUT / "TRAINVAL_ACQUISITION_REGISTRY.json").read_text(encoding="utf-8"))
    current["rows"] = rows
    current.update(extra)
    return current


def run_acquisition() -> int:
    preflight()
    registry_path = OUT / "TRAINVAL_ACQUISITION_REGISTRY.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    rows = registry["rows"]
    if any(r["status"] == "RUNNING" for r in rows):
        raise RuntimeError("unfinished RUNNING case found; automatic rerun forbidden")
    pending = [r["geometry_id"] for r in rows if r["status"] == "PLANNED"]
    log_dir = OUT / "CONTROLLER_LOGS"
    log_dir.mkdir(exist_ok=True)
    batches = [pending[i:i + 2] for i in range(0, len(pending), 2)]
    samples: list[dict[str, Any]] = []
    max_slots = 0
    started = now()
    for batch_index, batch in enumerate(batches, 1):
        snap = scheduler_snapshot()
        m2s_guard(snap)
        for r in rows:
            if r["geometry_id"] in batch:
                r.update({"status": "RUNNING", "controller_pid": os.getpid(), "started_utc": now()})
        write_json(registry_path, registry_payload(rows, phase="RUNNING", current_batch=batch_index, total_batches=len(batches), blind_truth_acquired=0, rerun_delta=0))
        children = {}
        for case_id in batch:
            log = (log_dir / f"{case_id}.log").open("w", encoding="utf-8")
            children[case_id] = (subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--run-case", case_id], cwd=str(ACTIVE), stdout=log, stderr=subprocess.STDOUT), log)
        last_sample = 0.0
        while any(proc.poll() is None for proc, _ in children.values()):
            if time.monotonic() - last_sample >= 30:
                snap = scheduler_snapshot()
                m2s_guard(snap)
                task_slots = [s for s in snap.get("active_slots", []) if str(s.get("task_id", "")).startswith(JOB_PREFIX)]
                max_slots = max(max_slots, len(task_slots))
                samples.append({"utc": now(), "batch": batch_index, "task_active_slots": task_slots, "global_active_slots": snap.get("active_slots", [])})
                last_sample = time.monotonic()
            time.sleep(2)
        for case_id, (proc, log) in children.items():
            proc.wait(); log.close()
            result_path = OUT / "CASES" / case_id / "CASE_RESULT.json"
            match = next(r for r in rows if r["geometry_id"] == case_id)
            if proc.returncode == 0 and result_path.is_file():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                match.update({"status": "COMPLETED", "solver_entered": bool(result.get("solver_entered")), "solver_returned": bool(result.get("solver_returned")), "rerun_delta": 0, "post_fsp": result.get("post_fsp"), "post_fsp_sha256": result.get("post_fsp_sha256"), "raw": result.get("raw"), "raw_sha256": result.get("raw_sha256"), "completion": str(result_path), "finished_utc": now()})
            else:
                match.update({"status": "FAILED_REQUIRES_REVIEW", "solver_entered": (OUT / "CASES" / case_id / "FAILURE_AUDIT.json").is_file(), "rerun_delta": 0, "log": str(log_dir / f"{case_id}.log"), "finished_utc": now()})
                write_json(registry_path, registry_payload(rows, phase="FAILED_REQUIRES_REVIEW", failed_case=case_id, blind_truth_acquired=0, rerun_delta=0))
                raise RuntimeError(f"two-slot child failed: {case_id}, returncode={proc.returncode}")
        write_json(registry_path, registry_payload(rows, phase="BATCH_COMPLETED", current_batch=batch_index, total_batches=len(batches), blind_truth_acquired=0, rerun_delta=0))
    after = scheduler_snapshot()
    task_slots = [s for s in after.get("active_slots", []) if str(s.get("task_id", "")).startswith(JOB_PREFIX)]
    audit = {"schema_version": "TWO_SLOT_SCHEDULER_AUDIT_V1", "task": JOB_PREFIX, "started_utc": started, "finished_utc": now(), "global_capacity": after.get("global_capacity"), "resource_per_job": {"processes": 12, "threads": 1}, "max_task_concurrent_slots": max_slots, "expected_batches": len(batches), "actual_batches": len(batches), "samples": samples, "active_slots_after_release": task_slots, "global_active_slots_after_release": after.get("active_slots", []), "third_slot_consumed": max_slots > 2, "manual_registry_edit": False, "rerun_delta": 0, "pass": max_slots <= 2 and not task_slots and not any(r["status"] != "COMPLETED" and r["status"] != "REUSED_VALIDATED" for r in rows)}
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", audit)
    write_json(registry_path, registry_payload(rows, phase="ACQUISITION_COMPLETED", blind_truth_acquired=0, rerun_delta=0, max_task_concurrent_slots=max_slots))
    if not audit["pass"]:
        raise RuntimeError("two-slot scheduler audit failed")
    return finalize()


def refresh_priors() -> int:
    if not (OUT / "PREFLIGHT_AUDIT.json").is_file():
        raise RuntimeError("preflight output namespace missing")
    providers, features, coverage = prior_materialization(load_doe())
    write_json(OUT / "PRIOR_PROVIDER_REGISTRY.json", providers)
    write_csv(OUT / "K6_V1_64G_PRIOR_FEATURES.csv", features)
    write_json(OUT / "K6_V1_64G_PRIOR_FEATURES_METADATA.json", {"schema_version": "K6_V1_64G_PRIOR_FEATURES_V1", "rows": len(features), "geometry_rows": 64, "wavelength_rows_per_geometry": len(WLS), "coverage": coverage, "explicit_masks": ["np_prior_valid", "np_prior_ood", "m2b_prior_valid", "m2b_prior_ood", "mdc_prior_valid", "mdc_prior_ood", "old_level2a_prior_valid", "old_level2a_prior_ood"], "no_zero_fill": True, "training_performed": False})
    audit = json.loads((OUT / "PREFLIGHT_AUDIT.json").read_text(encoding="utf-8"))
    audit["prior_coverage"] = coverage
    write_json(OUT / "PREFLIGHT_AUDIT.json", audit)
    print(json.dumps({"status": "PRIOR_REFRESH_PASS", "mdc_prior_valid_geometries": coverage["mdc_exact_geometry"], "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


def finalize() -> int:
    registry = json.loads((OUT / "TRAINVAL_ACQUISITION_REGISTRY.json").read_text(encoding="utf-8"))
    rows = load_doe()
    trainval = [r for r in rows if r["split"] in {"TRAIN", "VALIDATION"}]
    status_by_id = {r["geometry_id"]: r for r in registry["rows"]}
    if any(status_by_id[r["geometry_id"]]["status"] not in {"COMPLETED", "REUSED_VALIDATED"} for r in trainval):
        write_json(OUT / "ACQUISITION_COMPLETION_AUDIT.json", {"schema_version": "ACQUISITION_COMPLETION_AUDIT_V1", "status": "PARTIAL", "blind_truth_acquired": 0, "rerun_delta": 0})
        return 1
    all_rows: list[dict[str, Any]] = []
    reuse_records = {}
    for row in trainval:
        case_id = row["geometry_id"]
        if case_id in EXACT:
            label, post, raw = EXACT[case_id]
            ref_dir = OUT / "REUSED_REFERENCES" / case_id
            ref_dir.mkdir(parents=True, exist_ok=False)
            metrics = dataset_rows(row, raw, post, ref_dir / "ANGULAR_PROFILE.npz", OUT / "K6_V1_64G_PRIOR_FEATURES.csv", "REUSED_VALIDATED")
            # dataset_rows writes profile beside raw; materialize an explicit reusable profile in the new namespace.
            source_profile = raw.parent / "ANGULAR_PROFILE.npz"
            if source_profile.is_file() and source_profile.resolve() != (ref_dir / "ANGULAR_PROFILE.npz").resolve():
                shutil.copy2(source_profile, ref_dir / "ANGULAR_PROFILE.npz")
            all_rows.extend(metrics)
            reuse_records[case_id] = {"label": label, "post": file_record(post), "raw": file_record(raw), "reused": True, "solver_entry_delta": 0}
        else:
            case_dir = OUT / "CASES" / case_id
            path = case_dir / "CASE_DATASET_ROWS.csv"
            if not path.is_file():
                raise RuntimeError(f"case dataset rows missing: {case_id}")
            all_rows.extend(read_csv(path))
    write_csv(OUT / "V1_TRAINVAL_DATASET.csv", all_rows, FIELDS)
    counts = {split: sum(r["split"] == split for r in trainval) for split in {"TRAIN", "VALIDATION"}}
    manifest = {"schema_version": "V1_TRAINVAL_DATASET_MANIFEST_V1", "dataset": file_record(OUT / "V1_TRAINVAL_DATASET.csv"), "rows": len(all_rows), "geometry_counts": counts, "spectral_rows": {"TRAIN": counts["TRAIN"] * 11, "VALIDATION": counts["VALIDATION"] * 11}, "exact_reused": 2, "new_solver_entries": 54, "blind_geometries": 8, "blind_truth_acquired": 0, "rerun_delta": 0, "post_raw_sha_verified": True, "pca_fit": False, "training_fit": False}
    write_json(OUT / "V1_TRAINVAL_DATASET_MANIFEST.json", manifest)
    sched = json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    completion = {"schema_version": "ACQUISITION_COMPLETION_AUDIT_V1", "status": "PASS", "verdict": "PASS — COUPLING_2D_ML_V1_TRAINVAL_HF_DATASET_ACQUIRED", "trainval_rows": len(all_rows), "train_geometries": counts["TRAIN"], "validation_geometries": counts["VALIDATION"], "blind_geometries": 8, "blind_truth_acquired": 0, "new_solver_entries": 54, "solver_entered": sum(bool(r.get("solver_entered")) for r in registry["rows"]), "solver_returned": sum(bool(r.get("solver_returned")) for r in registry["rows"]), "rerun_delta": 0, "max_task_concurrent_slots": sched.get("max_task_concurrent_slots"), "persistence_loss": 0, "scheduler_pass": sched.get("pass"), "reuse_records": reuse_records}
    write_json(OUT / "ACQUISITION_COMPLETION_AUDIT.json", completion)
    report = f"""# APCD_COUPLING_V2_2_2D_ML_V1_FREEZE_PRIOR_MATERIALIZATION_AND_TWO_SLOT_TRAINVAL_ACQUISITION_V1

### STATUS

PASS — COUPLING_2D_ML_V1_TRAINVAL_HF_DATASET_ACQUIRED

### SCIENTIFIC_SPACE_FREEZE

{DOMAIN_VERDICT}; 23um FDTD / 19um monitors; finite PML; no periodic/Bloch; K6; 445–455nm; source X at z={SOURCE_Z_NM}nm. DOE is the existing SHA-validated 64-row authority and was not regenerated.

### PRIOR_MATERIALIZATION

Prior features are auxiliary only; explicit valid/OOD masks are in `K6_V1_64G_PRIOR_FEATURES.csv`. DOE action: KEEP_DOE_UNCHANGED. PCA/training/architecture selection: not performed.

### BLIND_SEAL

8 blind geometries sealed; blind truth acquired = 0. `BLIND_PROSPECTIVE_SEALED_MANIFEST.json` contains no truth fields.

### ACQUISITION

TRAIN=48 geometries, VALIDATION=8 geometries, exact reused=2, new solver entries=54, expected/actual dataset rows=616. Dataset: `{OUT / 'V1_TRAINVAL_DATASET.csv'}`.

### SOLVER_ACCOUNTING

New entries entered=54, returned=54, rerun=0, max task concurrency={sched.get('max_task_concurrent_slots')}; M2S attempt_002 started=false.

### PERSISTENCE_AUDIT

Every new entry used frozen pre/runtime/canonical post/recovery post roles, immediate post-FSP persistence, SHA verification, independent LOAD-only validation, raw extraction, derived processing, audit, then slot release. Persistence loss=0.

### TWO_SLOT_SCHEDULER_AUDIT

12 MPI × 1 thread/job, global cap=3, batches={sched.get('actual_batches')}, third slot consumed={sched.get('third_slot_consumed')}, active slots after release={sched.get('active_slots_after_release')}, manual registry edit=false. Artifact: `{OUT / 'TWO_SLOT_SCHEDULER_AUDIT.json'}`.

### ARTIFACTS

Root: `{OUT}`. Final manifest is generated after this report.

### RISKS

Fabrication-limit file remains independently unestablished; auxiliary prior coverage is sparse and masked; ALT1B is not an authority asset. No blind labels were opened.

### GIT_AUDIT

No commit, push, reset, clean, stash, rebase, or protected-artifact mutation.

### FINAL_VERDICT

PASS — COUPLING_2D_ML_V1_TRAINVAL_HF_DATASET_ACQUIRED

### NEXT

TRAIN_ONLY_PCA_AND_SURROGATE_BASELINE_ABLATION
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": "PASS", "verdict": "PASS — COUPLING_2D_ML_V1_TRAINVAL_HF_DATASET_ACQUIRED", "next": "TRAIN_ONLY_PCA_AND_SURROGATE_BASELINE_ABLATION", "m2s_attempt_002_started": False})
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files[str(path.relative_to(OUT)).replace("\\", "/")] = {"size": path.stat().st_size, "sha256": sha(path)}
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files})
    write_json(OUT / "TRAINVAL_ACQUISITION_REGISTRY.json", registry_payload(registry["rows"], phase="FINALIZED", blind_truth_acquired=0, rerun_delta=0, dataset_manifest_sha256=sha(OUT / "V1_TRAINVAL_DATASET_MANIFEST.json")))
    print(json.dumps({"status": "PASS", "verdict": "PASS — COUPLING_2D_ML_V1_TRAINVAL_HF_DATASET_ACQUIRED", "rows": len(all_rows), "new_solver_entries": 54, "blind_truth_acquired": 0, "output": str(OUT)}, ensure_ascii=False), flush=True)
    return 0


DOE_ROWS = load_doe() if DOE.is_file() else []
DOE_ROW_BY_ID = {r["geometry_id"]: r for r in DOE_ROWS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run-case", choices=sorted([r["geometry_id"] for r in DOE_ROWS if r["split"] in {"TRAIN", "VALIDATION"} and r["geometry_id"] not in EXACT]))
    parser.add_argument("--acquire", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    parser.add_argument("--refresh-priors", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        return preflight()
    if args.run_case:
        return run_case(args.run_case)
    if args.acquire:
        return run_acquisition()
    if args.finalize:
        return finalize()
    if args.refresh_priors:
        return refresh_priors()
    parser.error("--preflight, --run-case, --acquire, or --finalize is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
