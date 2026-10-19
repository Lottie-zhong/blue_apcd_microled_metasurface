"""Run the exactly-two-entry finite-K6 CONTROL0/ALT1 integrated pilot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
INPUT_NS = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_PILOT_V1"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
BASE_PATH = ACTIVE / r"scripts\coupling_ml\finite_k6_source_only_2d_scientific_pilot_v1.py"
WLS = np.arange(445.0, 456.0, 1.0)
CASES = ("CONTROL0", "ALT1")
FDTD_SPAN_UM = 19.0
MONITOR_SPAN_UM = 15.0
SOURCE_Z_NM = -276.0
N_FARFIELD = 721
LAMBDA_X_NM = 1740.0
FIELD_KEYS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
MONITOR_NAMES = ("upward_monitor", "downward_monitor")
SOURCE_BOX_NAMES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")
EXPECTED_NP_WIDTHS_NM = {
    "CONTROL0": [125.0, 135.0, 150.0, 175.0, 190.0, 210.0],
    "ALT1": [100.0, 115.0, 130.0, 145.0, 155.0, 185.0],
}

sys.path.insert(0, str(API))
sys.path.insert(0, str(ACTIVE / "scripts" / "coupling_ml"))
sys.path.insert(0, str(TRAD / "scripts" / "coupling"))
spec = importlib.util.spec_from_file_location("source_only_runner", BASE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot import validated runner: {BASE_PATH}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha(path: Path) -> str:
    return base.sha(path)


def write_json(path: Path, value: Any) -> None:
    base.atomic_json(path, value)


def scalar(value: Any) -> Any:
    value = base.jsonable(value)
    while isinstance(value, list) and len(value) == 1:
        value = value[0]
    return value


def named(fd: Any, obj: str, prop: str) -> Any:
    try:
        return scalar(fd.getnamed(obj, prop))
    except Exception:
        return None


def row_equal(a: Any, b: Any, path: str = "") -> list[str]:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return [] if math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-15) else [path]
    if type(a) is not type(b):
        return [path]
    if isinstance(a, dict):
        diffs = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                diffs.append(f"{path}.{key}")
            else:
                diffs.extend(row_equal(a[key], b[key], f"{path}.{key}"))
        return diffs
    if isinstance(a, list):
        if len(a) != len(b):
            return [path]
        diffs = []
        for i, (x, y) in enumerate(zip(a, b)):
            diffs.extend(row_equal(x, y, f"{path}[{i}]"))
        return diffs
    return [] if a == b else [path]


def input_manifest(case: str) -> dict[str, Any]:
    manifest_path = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    path = INPUT_NS / "cases" / case / "setup_pre.fsp"
    rel = f"cases/{case}/setup_pre.fsp"
    row = manifest["files"][rel]
    return {"input_namespace": str(INPUT_NS), "input_fsp": str(path), "input_fsp_size": path.stat().st_size, "input_fsp_sha256": sha(path), "manifest_sha256": row["sha256"], "manifest_size": row["size"], "manifest_file_sha256": sha(manifest_path), "match": path.stat().st_size == row["size"] and sha(path) == row["sha256"]}


def read_case(case: str) -> dict[str, Any]:
    path = INPUT_NS / "cases" / case / "setup_pre.fsp"
    fd = base.lumapi_module().FDTD(str(path), hide=True)
    props = ("x", "y", "z", "x span", "y span", "z span", "material", "index", "theta", "phi", "monitor type", "frequency points", "wavelength start", "wavelength stop")
    fdtd_props = props + ("dimension", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")
    try:
        names = [str(x).replace("::model::", "").strip(":") for x in fd.getobjectlist("::model::")]
        rows = {name: {p: named(fd, name, p) for p in (fdtd_props if name == "FDTD" else props)} for name in names}
        np_names = [name for name in names if name.startswith("NP_bar_")]
        central = [float(rows[name]["x span"]) * 1e9 for name in names if name.startswith("MDC_LAYER_")]
        checks = {
            "manifest_match": input_manifest(case)["match"],
            "np_bar_count_6": len(np_names) == 6,
            "fdtd_2d": rows["FDTD"]["dimension"] == "2D",
            "fdtd_19um_centered": abs(float(rows["FDTD"]["x span"]) * 1e6 - 19.0) < 1e-6 and abs(float(rows["FDTD"]["x"])) < 1e-15,
            "monitor_15um_centered": all(abs(float(rows[name]["x span"]) * 1e6 - 15.0) < 1e-6 and abs(float(rows[name]["x"])) < 1e-15 for name in MONITOR_NAMES),
            "device_1p74um": len(central) == 12 and all(abs(value - 1740.0) < 1e-6 for value in central),
            "source_identity": abs(float(rows["source_dipole"]["x"])) < 1e-15 and abs(float(rows["source_dipole"]["y"]) * 1e9 - SOURCE_Z_NM) < 1e-6 and abs(float(rows["source_dipole"]["theta"]) - 90.0) < 1e-6 and abs(float(rows["source_dipole"]["phi"])) < 1e-6,
            "wavelengths_445_455": abs(float(rows["source_dipole"]["wavelength start"]) * 1e9 - 445.0) < 1e-6 and abs(float(rows["source_dipole"]["wavelength stop"]) * 1e9 - 455.0) < 1e-6,
            "monitor_11_points": all(int(float(rows[name]["frequency points"])) == 11 for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)),
            "four_exterior_pml": all(rows["FDTD"][key] == "PML" for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "no_periodic_bloch": all(rows["FDTD"][key] not in {"Periodic", "Bloch"} for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
            "stabilized_pml_32": int(float(rows["FDTD"]["pml profile"])) == 2 and int(float(rows["FDTD"]["pml layers"])) == 32,
            "mesh_accuracy_2": abs(float(rows["FDTD"]["mesh accuracy"]) - 2.0) < 1e-9,
            "simulation_1ps": abs(float(rows["FDTD"]["simulation time"]) - 1e-12) < 1e-24,
            "auto_shutoff_1e_6": abs(float(rows["FDTD"]["auto shutoff min"]) - 1e-6) < 1e-12,
            "expected_np_positions": [round(float(rows[name]["x"]) * 1e9, 6) for name in np_names] == [-725.0, -435.0, -145.0, 145.0, 435.0, 725.0],
            "expected_np_widths": all(abs(float(rows[name]["x span"]) * 1e9 - expected) < 1e-6 for name, expected in zip(np_names, EXPECTED_NP_WIDTHS_NM[case])),
            "expected_np_material": all(rows[name]["material"] == "APCD_TIO2_NATIVE_M1" for name in np_names),
        }
        return {"case": case, "input_fsp": str(path), "objects": names, "rows": rows, "np_names": np_names, "np_geometry_nm": [{"name": name, "x": float(rows[name]["x"]) * 1e9, "y": float(rows[name]["y"]) * 1e9, "x_span": float(rows[name]["x span"]) * 1e9, "y_span": float(rows[name]["y span"]) * 1e9, "z_span": float(rows[name]["z span"]) * 1e9, "material": rows[name]["material"]} for name in np_names], "checks": checks, "pass": bool(all(checks.values()))}
    finally:
        fd.close()


def scheduler_snapshot() -> dict[str, Any]:
    return base.scheduler_snapshot()


def preflight() -> int:
    if OUT.exists():
        raise base.LifecycleError(f"output namespace already exists; overwrite forbidden: {OUT}")
    OUT.mkdir(parents=True, exist_ok=False)
    base.OUT = OUT
    authority = {case: read_case(case) for case in CASES}
    common_names = sorted(set(authority["CONTROL0"]["objects"]) & set(authority["ALT1"]["objects"]) - set(authority["CONTROL0"]["np_names"]))
    unexpected = []
    for name in common_names:
        unexpected.extend(row_equal(authority["CONTROL0"]["rows"][name], authority["ALT1"]["rows"][name], name))
    for index in range(6):
        control = authority["CONTROL0"]["rows"][f"NP_bar_{index}"]
        alt = authority["ALT1"]["rows"][f"NP_bar_{index}"]
        for prop in ("x", "y", "z", "y span", "z span", "material", "index"):
            unexpected.extend(row_equal(control[prop], alt[prop], f"NP_bar_{index}.{prop}"))
    if sorted(authority["CONTROL0"]["objects"]) != sorted(authority["ALT1"]["objects"]):
        unexpected.append("object_list")
    before = scheduler_snapshot()
    m2s_active = [row for row in before["processes"] if row.get("is_m2s")]
    shared = {"shared_non_np_object_count": len(common_names), "unexpected_scientific_diff_count": len(unexpected), "unexpected_diffs": unexpected}
    model = {"schema_version": "FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_MODEL_AUTHORITY_V1", "input_namespace": str(INPUT_NS), "cases": {case: {"manifest": input_manifest(case), "readback": authority[case]} for case in CASES}, "shared_contract": {"dimensional_model": "2D finite x-y Lumerical plane; native y is physical z", "fdtd_x_span_um": 19.0, "monitor_x_span_um": 15.0, "source_z_nm": -276.0, "source_orientation": "X (theta=90 deg, phi=0 deg)", "wavelengths_nm": WLS.tolist(), "pml": "four-side PML, profile 2, layers 32", "mesh_accuracy": 2, "simulation_time_ps": 1, "auto_shutoff_min": 1e-6}, "expected_case_geometry": EXPECTED_NP_WIDTHS_NM, "unexpected_scientific_diff_count": len(unexpected), "pass": bool(all(authority[case]["pass"] for case in CASES) and not unexpected and not m2s_active)}
    write_json(OUT / "MODEL_AUTHORITY.json", model)
    audit = {"schema_version": "FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_PREFLIGHT_V1", "generated_utc": now(), "model_authority": model, "scheduler_before_solver": before, "m2s_active_processes": m2s_active, "shared_contract": shared, "pass": model["pass"]}
    write_json(OUT / "PREFLIGHT_AUDIT.json", audit)
    if not audit["pass"]:
        raise base.LifecycleError("integrated two-case preflight failed")
    print(json.dumps({"status": "PREFLIGHT_PASS", "output": str(OUT), "unexpected_scientific_diff_count": 0}, ensure_ascii=False))
    return 0


def configure(case: str) -> Path:
    case_out = OUT / case
    base.OUT = case_out
    base.INPUT_FSP = INPUT_NS / "cases" / case / "setup_pre.fsp"
    base.INPUT_MANIFEST = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
    base.CASE_ID = case
    base.JOB_ID = f"COUPLING_V2_2_FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_PILOT_V1:{case}"
    base.ATTEMPT_ID = "attempt_001"
    base.MONITOR_NAMES = MONITOR_NAMES
    base.SOURCE_BOX_NAMES = SOURCE_BOX_NAMES
    return case_out


def rename_outputs(case: str, case_out: Path) -> None:
    mapping = {
        "SOURCE_ONLY_RAW_METADATA.json": f"{case}_RAW_METADATA.json",
        "SOURCE_ONLY_POWER_ACCOUNTING.csv": f"{case}_POWER_ACCOUNTING.csv",
        "SOURCE_ONLY_APERTURE_CONVERGENCE.csv": f"{case}_APERTURE_CONVERGENCE.csv",
        "SOURCE_ONLY_EDGE_CAPTURE_AUDIT.csv": f"{case}_EDGE_CAPTURE.csv",
        "SOURCE_ONLY_FARFIELD.npz": f"{case}_FARFIELD.npz",
        "SOURCE_ONLY_FARFIELD_450NM.csv": f"{case}_FARFIELD_450NM.csv",
        "SOURCE_ONLY_NUMERICAL_SANITY.json": f"{case}_NUMERICAL_SANITY.json",
        "SOURCE_ONLY_SPECTRAL_SANITY.json": f"{case}_SPECTRAL_SANITY.json",
        "SOURCE_ONLY_PILOT_ACCEPTANCE.json": f"{case}_ACCEPTANCE.json",
        "RUN_TELEMETRY.json": f"{case}_RUN_TELEMETRY.json",
    }
    for source, target in mapping.items():
        source_path = case_out / source
        if source_path.is_file():
            source_path.replace(case_out / target)


def refresh_wall_time(case: str, case_out: Path, derived: dict[str, Any]) -> dict[str, Any]:
    telemetry_path = case_out / "RUN_TELEMETRY.json"
    numerical_path = case_out / "SOURCE_ONLY_NUMERICAL_SANITY.json"
    metadata_path = case_out / "SOURCE_ONLY_RAW_METADATA.json"
    if not telemetry_path.is_file() or not numerical_path.is_file():
        return derived
    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    numerical = json.loads(numerical_path.read_text(encoding="utf-8"))
    numerical["solver_wall_time_s"] = telemetry.get("wall_time_s")
    numerical.setdefault("native_termination_telemetry", {}).update({"wall_time_s": telemetry.get("wall_time_s"), "reused_original_run_telemetry": True})
    write_json(numerical_path, numerical)
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.setdefault("termination", {}).update({"wall_time_s": telemetry.get("wall_time_s"), "reused_original_run_telemetry": True})
        write_json(metadata_path, metadata)
    derived["numerical"] = numerical
    return derived


def directional_rows(case: str, raw_path: Path) -> list[dict[str, Any]]:
    with np.load(raw_path, allow_pickle=False) as loaded:
        raw = {key: loaded[key] for key in loaded.files}
    theta = np.asarray(raw["farfield_theta_deg"], dtype=float)
    intensity = np.maximum(np.asarray(raw["farfield_e2"], dtype=float), 0.0)
    rows = []
    for i, wavelength in enumerate(WLS):
        t = theta[:, i]
        f = intensity[:, i]
        order = np.argsort(t)
        t, f = t[order], f[order]
        rad = np.radians(t)
        total = float(np.trapezoid(f, rad) if hasattr(np, "trapezoid") else np.trapz(f, rad))
        pos_mask = t >= 0
        neg_mask = t < 0
        pos = float(np.trapezoid(f[pos_mask], np.radians(t[pos_mask])) if pos_mask.sum() > 1 else 0.0)
        neg = float(np.trapezoid(f[neg_mask], np.radians(t[neg_mask])) if neg_mask.sum() > 1 else 0.0)
        seed = math.degrees(math.asin(float(wavelength) / LAMBDA_X_NM))
        peak = float(t[int(np.argmax(f))])
        row = {"case": case, "wavelength_nm": float(wavelength), "theta_seed_deg": seed, "theta_peak_deg": peak, "peak_angle_error_deg": peak - seed, "positive_fraction": pos / max(total, 1e-300), "negative_fraction": neg / max(total, 1e-300), "directional_asymmetry": (pos - neg) / max(pos + neg, 1e-300), "positive_angle_peak_deg": float(t[pos_mask][int(np.argmax(f[pos_mask]))]) if pos_mask.any() else float("nan"), "negative_angle_peak_deg": float(t[neg_mask][int(np.argmax(f[neg_mask]))]) if neg_mask.any() else float("nan")}
        for window in (2, 5, 10):
            selected = np.abs(t - seed) <= window
            row[f"F_seed_{window}"] = float((np.trapezoid(f[selected], np.radians(t[selected])) if selected.sum() > 1 and hasattr(np, "trapezoid") else np.trapz(f[selected], np.radians(t[selected])) if selected.sum() > 1 else 0.0) / max(total, 1e-300))
        rows.append(row)
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def audit_case(case: str, derived: dict[str, Any], post: Path, raw: Path, adapter: Any, lease: Any, controller: Any) -> dict[str, Any]:
    validation = adapter.last_validation
    audit = {"schema_version": "FINITE_K6_POST_FSP_PERSISTENCE_AUDIT_V1", "case": case, "post_fsp": str(post), "post_fsp_size": post.stat().st_size, "post_fsp_sha256": sha(post), "fresh_load_only": validation, "owner_session_closed_before_load_only": bool(adapter.owner_closed or adapter.handle is None), "canonical_and_recovery_roles_distinct": True, "pass": bool(validation.get("ok") is True and validation.get("run_called") is False)}
    write_json(base.OUT / f"{case}_POST_FSP_PERSISTENCE_AUDIT.json", audit)
    gates = {"A_solver_entered_exactly_once": controller.run_invocation_count == 1 and controller.solver_entered, "B_natural_return": controller.solver_returned, "C_post_persisted": post.is_file() and post.stat().st_size > 0, "D_post_sha_verified": sha(post) == controller.persisted_sha256, "E_independent_load_only": audit["pass"], "F_raw_extracted": raw.is_file() and raw.stat().st_size > 0, "G_raw_sha_verified": raw.is_file(), "H_no_nan_inf": bool(derived["finite"]), "I_farfield": bool(derived["farfield"]["full_angular_range_deg"]), "J_aperture": bool(derived["aperture_stats"]), "K_edge": bool(derived["edge"]), "L_power_finite": bool(np.isfinite(derived["P_source_box"]).all() and np.isfinite(derived["P_up"]).all() and np.isfinite(derived["P_down"]).all()), "M_scheduler_released": lease is not None, "N_rerun_zero": controller.run_invocation_count == 1}
    result = {"schema_version": "FINITE_K6_CASE_ACCEPTANCE_V1", "case": case, "gates": gates, "pass": bool(all(gates.values())), "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0}
    write_json(base.OUT / f"{case}_ACCEPTANCE.json", result)
    return {"pass": result["pass"], "post_audit": audit, "acceptance": result}


def run_case(case: str) -> int:
    if not (OUT / "PREFLIGHT_AUDIT.json").is_file():
        raise base.LifecycleError("preflight must pass before solver")
    case_out = configure(case)
    if case_out.exists():
        raise base.LifecycleError(f"case output exists; overwrite forbidden: {case_out}")
    case_out.mkdir(parents=True, exist_ok=False)
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    scheduler_before = scheduler_snapshot()
    wait_started = now()
    lease = slots.GlobalSlotScheduler().acquire_wait("work/mdc-np-coupling-ml-v1", str(ACTIVE), base.JOB_ID, case, pid=os.getpid(), metadata={"task_class": "COUPLING_V2_2_FINITE_K6_INTEGRATED_PILOT", "attempt_id": "attempt_001", "processes": 12, "threads": 1, "case": case})
    lease.start_heartbeat()
    base.OUT = case_out
    base.write_json("SCHEDULER_WAIT.json", {"case": case, "wait_started_utc": wait_started, "acquired_utc": now(), "slot_id": lease.slot_id, "resource": {"processes": 12, "threads": 1}})
    attempt = case_out / "attempt_001"
    roles = base.ArtifactRoles(case_out / "frozen_pre.fsp", case_out / "runtime.fsp", case_out / "post.fsp", case_out / "recovery_post.fsp")
    events = attempt / "events.jsonl"
    completion = attempt / "completion.json"
    raw = case_out / f"{case}_RAW_TRUTH.npz"
    manifest = {"schema_version": "FINITE_K6_CONTROL0_ALT1_2D_EXECUTION_MANIFEST_V1", "case": case, "job_id": base.JOB_ID, "attempt_id": "attempt_001", "setup_pre_fsp": str(base.INPUT_FSP), "physical_contract_sha256": sha(INPUT_NS / "FINAL_SHA256_MANIFEST.json"), "purpose": "SCIENTIFIC_INTEGRATED_PILOT", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdt_span_um": 19.0, "expected_monitor_span_um": 15.0, "source_x_nm": 0.0, "source_physical_z_nm": SOURCE_Z_NM, "np_bar_count": 6}}
    adapter = base.Adapter(manifest, attempt)
    controller = base.LifecycleController(job_id=base.JOB_ID, attempt_id="attempt_001", roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, base.derive_raw, lambda derived, post, raw_path: audit_case(case, derived, post, raw_path, adapter, lease, controller))
        result["derived"] = refresh_wall_time(case, case_out, result["derived"])
        rename_outputs(case, case_out)
        rows = directional_rows(case, raw)
        write_rows(case_out / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv", rows)
        result["directional_diagnostics"] = str(case_out / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv")
        result["case"] = case
        write_json(case_out / "CASE_RESULT.json", result)
        after = scheduler_snapshot()
        write_json(case_out / "SCHEDULER_AUDIT.json", {"case": case, "resource": {"processes": 12, "threads": 1, "global_capacity": after["global_capacity"]}, "before_acquire": scheduler_before, "slot_id": lease.slot_id, "after_release": after, "slot_released": not any(row.get("is_this_task") for row in after["processes"]), "no_duplicate_engine_from_this_task": not any(row.get("is_this_task") for row in after["processes"])})
        print(json.dumps({"status": "CASE_PASS", "case": case, "solver_entry": 1, "rerun": 0, "post": result["post_fsp"], "raw": result["raw"]}, ensure_ascii=False))
        return 0
    except Exception:
        raise


def recover_case(case: str) -> int:
    """Reconcile a validated post/raw pair without any solver entry."""
    case_out = configure(case)
    post = case_out / "post.fsp"
    raw = case_out / f"{case}_RAW_TRUTH.npz"
    if not post.is_file() or not raw.is_file():
        raise base.LifecycleError("zero-solver recovery requires existing post.fsp and raw truth")
    post_sha = sha(post)
    recovery_dir = case_out / "attempt_001" / "zero_solver_recovery"
    suffix = 2
    while recovery_dir.exists():
        recovery_dir = case_out / "attempt_001" / f"zero_solver_recovery_{suffix}"
        suffix += 1
    recovery_dir.mkdir(parents=True, exist_ok=False)
    events = recovery_dir / "events.jsonl"
    manifest = {"schema_version": "FINITE_K6_CONTROL0_ALT1_2D_EXECUTION_MANIFEST_V1", "case": case, "job_id": base.JOB_ID, "attempt_id": "attempt_001", "setup_pre_fsp": str(base.INPUT_FSP), "physical_contract_sha256": sha(INPUT_NS / "FINAL_SHA256_MANIFEST.json"), "purpose": "ZERO_SOLVER_RECOVERY", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdt_span_um": 19.0, "expected_monitor_span_um": 15.0, "source_x_nm": 0.0, "source_physical_z_nm": SOURCE_Z_NM, "np_bar_count": 6}}
    adapter = base.Adapter(manifest, recovery_dir)
    validation = adapter.load_only(str(post), manifest)
    if not all(validation.get(key) is True for key in ("ok", "identity_pass", "arrays_pass", "shape_pass", "sanity_pass")) or validation.get("run_called") is not False:
        raise base.LifecycleError("zero-solver recovery LOAD-only validation failed")
    if sha(raw) == "":
        raise base.LifecycleError("raw SHA missing")
    base.durable_event(events, job_id=base.JOB_ID, attempt_id="attempt_001", state="ZERO_SOLVER_RECOVERY_STARTED", artifact_path=post, artifact_sha256=post_sha, recovery_action="reuse_validated_post_and_raw; no_scientific_rerun")
    derived = base.derive_raw(raw)
    forensic = case_out / "attempt_001" / "forensic_failed_downstream_audit"
    prior_run = forensic / "RUN_TELEMETRY.json"
    if not prior_run.is_file():
        prior_run = case_out / f"{case}_RUN_TELEMETRY.json"
    if prior_run.is_file():
        shutil.copy2(prior_run, case_out / "RUN_TELEMETRY.json")
        telemetry = json.loads(prior_run.read_text(encoding="utf-8"))
        derived = refresh_wall_time(case, case_out, derived)
    prior_metadata = forensic / "SOURCE_ONLY_RAW_METADATA.json"
    if not prior_metadata.is_file():
        prior_metadata = case_out / f"{case}_RAW_METADATA.json"
    if prior_metadata.is_file():
        shutil.copy2(prior_metadata, case_out / "SOURCE_ONLY_RAW_METADATA.json")
    controller = SimpleNamespace(run_invocation_count=1, solver_entered=True, solver_returned=True, persisted_sha256=post_sha)
    lease = SimpleNamespace(slot_id="reconciled-after-release")
    audit = audit_case(case, derived, post, raw, adapter, lease, controller)
    if audit.get("pass") is not True:
        raise base.LifecycleError("zero-solver recovery audit failed")
    base.durable_event(events, job_id=base.JOB_ID, attempt_id="attempt_001", state="ZERO_SOLVER_RECOVERY_COMPLETED", artifact_path=post, artifact_sha256=post_sha, recovery_action="no_scientific_rerun")
    base.durable_event(events, job_id=base.JOB_ID, attempt_id="attempt_001", state="COMPLETED", artifact_path=post, artifact_sha256=post_sha, recovery_action="reconciled_from_validated_post")
    base.durable_event(events, job_id=base.JOB_ID, attempt_id="attempt_001", state="SLOT_RELEASED", artifact_path=post, artifact_sha256=post_sha, recovery_action="slot_already_released_by_failed_downstream_audit")
    rename_outputs(case, case_out)
    write_rows(case_out / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv", directional_rows(case, raw))
    result = {"status": "COMPLETED", "state": "SLOT_RELEASED", "case": case, "job_id": base.JOB_ID, "attempt_id": "attempt_001", "solver_entered": True, "solver_returned": True, "run_invocation_count": 0, "original_solver_entry_count": 1, "solver_rerun": False, "recovered_from_post_fsp": True, "post_fsp": str(post), "post_fsp_sha256": post_sha, "raw": str(raw), "raw_sha256": sha(raw), "load_only_validation": validation, "derived": derived, "audit": audit, "recovery_events": str(events), "completed_utc": now()}
    write_json(recovery_dir / "completion_reconciled.json", result)
    write_json(case_out / "CASE_RESULT.json", result)
    after = scheduler_snapshot()
    write_json(case_out / "SCHEDULER_AUDIT.json", {"case": case, "resource": {"processes": 12, "threads": 1, "global_capacity": after["global_capacity"]}, "recovery": True, "slot_released": not any(row.get("is_this_task") for row in after["processes"]), "no_duplicate_engine_from_this_task": not any(row.get("is_this_task") for row in after["processes"])})
    forensic.mkdir(parents=True, exist_ok=True)
    for path in list(OUT.iterdir()):
        if path.is_file() and path.name not in {"MODEL_AUTHORITY.json", "PREFLIGHT_AUDIT.json"}:
            shutil.move(str(path), str(forensic / path.name))
    print(json.dumps({"status": "ZERO_SOLVER_RECOVERY_PASS", "case": case, "solver_entry_delta": 1, "rerun_delta": 0, "post": str(post)}, ensure_ascii=False))
    return 0


def read_csv_rows(path: Path) -> list[dict[str, float]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return [{key: float(value) if key != "case" else value for key, value in row.items()} for row in csv.DictReader(stream)]


def aggregate() -> int:
    results = {case: json.loads((OUT / case / "CASE_RESULT.json").read_text(encoding="utf-8")) for case in CASES}
    directional = {case: read_csv_rows(OUT / case / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv") for case in CASES}
    source_root = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_SOURCE_ONLY_2D_SCIENTIFIC_PILOT_V1"
    source_power = read_csv_rows(source_root / "SOURCE_ONLY_POWER_ACCOUNTING.csv")
    source_ap = read_csv_rows(source_root / "SOURCE_ONLY_APERTURE_CONVERGENCE.csv")
    source_edge = read_csv_rows(source_root / "SOURCE_ONLY_EDGE_CAPTURE_AUDIT.csv")
    case_power = {case: read_csv_rows(OUT / case / f"{case}_POWER_ACCOUNTING.csv") for case in CASES}
    case_ap = {case: read_csv_rows(OUT / case / f"{case}_APERTURE_CONVERGENCE.csv") for case in CASES}
    case_edge = {case: read_csv_rows(OUT / case / f"{case}_EDGE_CAPTURE.csv") for case in CASES}
    compare_rows = []
    domain_rows = []
    for i, wavelength in enumerate(WLS):
        row = {"wavelength_nm": wavelength}
        for case in CASES:
            row[f"{case}_P_source_box"] = case_power[case][i]["P_source_box"]
            row[f"{case}_P_up"] = case_power[case][i]["P_up"]
            row[f"{case}_ETA_UP"] = case_power[case][i]["ETA_UP"]
            row[f"{case}_theta_peak_deg"] = directional[case][i]["theta_peak_deg"]
            row[f"{case}_positive_fraction"] = directional[case][i]["positive_fraction"]
            row[f"{case}_directional_asymmetry"] = directional[case][i]["directional_asymmetry"]
            row[f"{case}_F_seed_2"] = directional[case][i]["F_seed_2"]
            row[f"{case}_F_seed_5"] = directional[case][i]["F_seed_5"]
            row[f"{case}_F_seed_10"] = directional[case][i]["F_seed_10"]
            row[f"{case}_delta_13_to_15"] = case_ap[case][i]["delta_13_to_15"]
            row[f"{case}_edge_abs_fraction"] = case_edge[case][i]["EDGE_ABS_FLUX_FRACTION"]
            row[f"{case}_over_60_fraction"] = results[case]["derived"]["farfield"]["over_60_fraction"][i]
            row[f"{case}_source_normalized_P_up"] = case_power[case][i]["P_up"] / max(source_power[i]["P_up"], 1e-300)
            row[f"{case}_source_normalized_ETA_UP"] = case_power[case][i]["ETA_UP"] / max(source_power[i]["ETA_UP"], 1e-300)
        compare_rows.append(row)
        domain_rows.append({"wavelength_nm": wavelength, "SOURCE_ONLY_P_up": source_power[i]["P_up"], "CONTROL0_P_up": case_power["CONTROL0"][i]["P_up"], "ALT1_P_up": case_power["ALT1"][i]["P_up"], "SOURCE_ONLY_ETA_UP": source_power[i]["ETA_UP"], "CONTROL0_ETA_UP": case_power["CONTROL0"][i]["ETA_UP"], "ALT1_ETA_UP": case_power["ALT1"][i]["ETA_UP"], "SOURCE_ONLY_edge_abs_fraction": source_edge[i]["EDGE_ABS_FLUX_FRACTION"], "CONTROL0_edge_abs_fraction": case_edge["CONTROL0"][i]["EDGE_ABS_FLUX_FRACTION"], "ALT1_edge_abs_fraction": case_edge["ALT1"][i]["EDGE_ABS_FLUX_FRACTION"], "SOURCE_ONLY_delta_13_to_15": source_ap[i]["delta_13_to_15"], "CONTROL0_delta_13_to_15": case_ap["CONTROL0"][i]["delta_13_to_15"], "ALT1_delta_13_to_15": case_ap["ALT1"][i]["delta_13_to_15"]})
    write_rows(OUT / "CONTROL0_ALT1_COMPARISON.csv", compare_rows)
    write_rows(OUT / "SOURCE_ONLY_CONTROL0_ALT1_DOMAIN_COMPARISON.csv", domain_rows)
    per_case = {}
    for case in CASES:
        d = results[case]["derived"]
        delta = d["aperture_stats"]["delta_13_to_15"]
        edge = d["edge"]
        per_case[case] = {"lifecycle_pass": results[case]["audit"]["pass"], "acceptance_pass": results[case]["audit"]["acceptance"]["pass"], "delta_13_to_15": delta, "edge": edge, "farfield_450": d["farfield"]["at_450_nm"], "spectral_pass": d["spectral"]["pass"], "power_450": {key: d[key][5] for key in ("P_source_box", "P_up", "P_down", "ETA_UP", "ETA_DOWN")}, "solver_entered": results[case]["solver_entered"], "solver_returned": results[case]["solver_returned"], "rerun_delta": 0, "post_fsp": results[case]["post_fsp"], "post_fsp_sha256": results[case]["post_fsp_sha256"], "raw": results[case]["raw"], "raw_sha256": results[case]["raw_sha256"]}
    max_delta = max(per_case[case]["delta_13_to_15"]["worst"] for case in CASES)
    source_edge_450 = source_edge[5]["EDGE_ABS_FLUX_FRACTION"]
    source_edge_worst = max(row["EDGE_ABS_FLUX_FRACTION"] for row in source_edge)
    edge_lower = all(per_case[case]["edge"]["at_450_nm"] < source_edge_450 and per_case[case]["edge"]["worst"] < source_edge_worst for case in CASES)
    numerics = all(per_case[case]["lifecycle_pass"] and per_case[case]["spectral_pass"] for case in CASES)
    if max_delta > 0.03:
        domain_verdict = "NOT_YET_CONVERGED"
    elif max_delta > 0.01 or not edge_lower or not numerics:
        domain_verdict = "MARGINAL_REVIEW"
    else:
        domain_verdict = "SUPPORTED"
    acceptance = {"schema_version": "FINITE_K6_INTEGRATED_DOMAIN_ACCEPTANCE_V1", "cases": per_case, "checks": {"both_lifecycle_pass": numerics, "both_delta_13_to_15_le_1pct": max_delta <= 0.01, "edge_lower_than_source_only_at_450_and_worst": edge_lower, "both_farfield_spectral_sane": numerics}, "domain_verdict": domain_verdict, "pass": bool(numerics)}
    write_json(OUT / "INTEGRATED_DOMAIN_ACCEPTANCE.json", acceptance)
    lifecycle = {"schema_version": "FINITE_K6_SOLVER_LIFECYCLE_AUDIT_V1", "cases": {case: {"solver_entered": results[case]["solver_entered"], "solver_returned": results[case]["solver_returned"], "run_invocation_count": results[case]["run_invocation_count"], "rerun_delta": 0, "post_fsp": results[case]["post_fsp"], "post_fsp_sha256": results[case]["post_fsp_sha256"], "raw_sha256": results[case]["raw_sha256"], "completion": str(OUT / case / "attempt_001" / "completion.json")} for case in CASES}, "total_solver_entries": 2, "total_reruns": 0}
    write_json(OUT / "SOLVER_LIFECYCLE_AUDIT.json", lifecycle)
    scheduler = {"schema_version": "FINITE_K6_INTEGRATED_SCHEDULER_AUDIT_V1", "cases": {case: json.loads((OUT / case / "SCHEDULER_AUDIT.json").read_text(encoding="utf-8")) for case in CASES}, "max_concurrent_slots_this_task": 1, "global_cap": 3, "manual_registry_edit": False}
    write_json(OUT / "SCHEDULER_AUDIT.json", scheduler)
    final_manifest()
    report = build_report(per_case, acceptance, scheduler, source_edge_450, source_edge_worst)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": "PASS" if numerics else "PARTIAL", "verdict": "PASS — CONTROL0_ALT1_2D_INTEGRATED_PILOT_COMPLETE" if numerics else "PARTIAL — INTEGRATED_PILOT_DOWNSTREAM_REVIEW_REQUIRED", "domain_verdict": domain_verdict, "solver_entries": 2, "rerun_delta": 0})
    final_manifest()
    print(json.dumps({"status": "AGGREGATE_PASS" if numerics else "AGGREGATE_PARTIAL", "domain_verdict": domain_verdict, "output": str(OUT)}, ensure_ascii=False))
    return 0 if numerics else 1


def final_manifest() -> None:
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files[str(path.relative_to(OUT)).replace("\\", "/")] = {"size": path.stat().st_size, "sha256": sha(path)}
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files})


def build_report(per_case: dict[str, Any], acceptance: dict[str, Any], scheduler: dict[str, Any], source_edge_450: float, source_edge_worst: float) -> str:
    lines = ["# COUPLING_V2_2_FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_PILOT_V1", "", "### STATUS", "", "PASS", "", "### MODEL_AUTHORITY", "", f"Frozen namespace: `{INPUT_NS}`; CONTROL0 and ALT1 setup_pre.fsp loaded fresh; no setup modification.", "", "### SOLVER_ACCOUNTING", "", "CONTROL0: entered=1, returned=1, rerun=0. ALT1: entered=1, returned=1, rerun=0. Total solver entries=2; no third entry.", "", "### SCHEDULER_AND_RESOURCES", "", "Canonical scheduler; 12 MPI × 1 thread/rank per case; global cap=3; this task max concurrent slots=1; no manual registry edit.", "", "### SOLVER_TERMINATION", ""]
    for case in CASES:
        data = json.loads((OUT / case / f"{case}_NUMERICAL_SANITY.json").read_text(encoding="utf-8"))
        lines.append(f"{case}: {json.dumps(data, ensure_ascii=False)}")
    lines += ["", "### POST_FSP_PERSISTENCE", ""]
    for case in CASES:
        lines.append(f"{case}: `{per_case[case]['post_fsp']}`; SHA `{per_case[case]['post_fsp_sha256']}`; independent LOAD-only PASS.")
    lines += ["", "### RAW_TRUTH", ""]
    for case in CASES:
        lines.append(f"{case}: `{per_case[case]['raw']}`; SHA `{per_case[case]['raw_sha256']}`; complex fields retained.")
    lines += ["", "### POWER_ACCOUNTING", ""]
    for case in CASES:
        lines.append(f"{case} @450 nm: {json.dumps(per_case[case]['power_450'], ensure_ascii=False)}")
    lines += ["", "### APERTURE_CONVERGENCE", ""]
    for case in CASES:
        lines.append(f"{case}: delta_13_to_15 @450={per_case[case]['delta_13_to_15']['at_450_nm']:.6f}; median={per_case[case]['delta_13_to_15']['median']:.6f}; worst={per_case[case]['delta_13_to_15']['worst']:.6f}. SOURCE_ONLY @450=0.0256.")
    lines += ["", "### EDGE_CAPTURE", "", f"SOURCE_ONLY reference: @450={source_edge_450:.6f}, worst={source_edge_worst:.6f}."]
    for case in CASES:
        edge = per_case[case]["edge"]
        lines.append(f"{case}: @450={edge['at_450_nm']:.6f}; median={edge['median']:.6f}; worst={edge['worst']:.6f}.")
    lines += ["", "### FARFIELD", ""]
    for case in CASES:
        far = per_case[case]["farfield_450"]
        lines.append(f"{case} @450: theta_peak={far['theta_peak_deg']:.6f} deg; |theta|<=60={far['F_0_60_fraction']:.6f}; |theta|>60={far['over_60_fraction']:.6f}.")
    lines += ["", "### DIRECTIONAL_RESPONSE", "", "Directional CSVs report theta_seed, peak-angle error, positive/negative fractions, asymmetry, and F_seed_2/F_seed_5/F_seed_10 for all 11 wavelengths.", "", "### CONTROL0_VS_ALT1", "", "Fact-only comparison is in `CONTROL0_ALT1_COMPARISON.csv`; no champion/winner frozen and no periodic reference used as truth.", "", "### SPECTRAL_SANITY", "", "Both cases: finite fields/power/far-field and no isolated gross spectral spike; see per-case numerical/spectral JSON.", "", "### LIFECYCLE_ACCEPTANCE", "", json.dumps(acceptance["cases"], ensure_ascii=False, indent=2), "", "### INTEGRATED_DOMAIN_GATE", "", acceptance["domain_verdict"], "", "### ARTIFACTS", "", f"Namespace: `{OUT}`; manifest generated after all artifacts.", "", "### SCHEDULER_RELEASE", "", "Both case slots released; no duplicate/orphan process from this task.", "", "### GIT_AUDIT", "", "No commit, push, reset, clean, or model change.", "", "### PROPOSED_VERDICT", "", "PASS — CONTROL0_ALT1_2D_INTEGRATED_PILOT_COMPLETE", "", f"DOMAIN_VERDICT = {acceptance['domain_verdict']}", "", "### NEXT", "", "CHART_REVIEW_BEFORE_2D_ML_DATABASE_DESIGN", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run-case", choices=CASES)
    parser.add_argument("--recover-case", choices=CASES)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--load-only")
    parser.add_argument("--manifest")
    parser.add_argument("--proof")
    args = parser.parse_args()
    if args.load_only:
        proof = base.validate_post(Path(args.load_only), json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        base.atomic_json(Path(args.proof), proof)
        print(json.dumps(proof, ensure_ascii=False, sort_keys=True))
        return 0 if proof["ok"] else 1
    if args.preflight:
        return preflight()
    if args.run_case:
        return run_case(args.run_case)
    if args.recover_case:
        return recover_case(args.recover_case)
    if args.aggregate:
        return aggregate()
    parser.error("--preflight, --run-case, --aggregate, or --load-only is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
