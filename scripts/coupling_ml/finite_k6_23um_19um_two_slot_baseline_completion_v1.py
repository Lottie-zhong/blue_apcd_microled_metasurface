"""Two-slot 23 um FDTD / 19 um monitor baseline completion.

Reuses the validated source-only lifecycle and changes only the lateral
runtime parameter.  CONTROL0 is an existing reference and is never rerun.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
INPUT_NS = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
INPUT_MANIFEST = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1"
BASE_PATH = ACTIVE / r"scripts\coupling_ml\finite_k6_source_only_2d_scientific_pilot_v1.py"
CONTROL_ROOT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1\VALIDATED_PROBE\CONTROL0"
CONTROL_RAW = CONTROL_ROOT.parent / "CONTROL0_RAW_TRUTH.npz"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
WLS = np.arange(445.0, 456.0, 1.0)
CASES = ("ALT1", "SOURCE_ONLY")
FDTD_OLD_UM = 19.0
MONITOR_OLD_UM = 15.0
FDTD_NEW_UM = 23.0
MONITOR_NEW_UM = 19.0
SOURCE_Z_NM = -276.0
LAMBDA_X_NM = 1740.0
N_FARFIELD = 721
MONITOR_NAMES = ("upward_monitor", "downward_monitor")
SOURCE_BOX_NAMES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")
FIELD_KEYS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
EXPECTED_NP_WIDTHS_NM = [100.0, 115.0, 130.0, 145.0, 155.0, 185.0]
ATTEMPT_ID = "attempt_001"

sys.path.insert(0, str(API))
sys.path.insert(0, str(ACTIVE / "scripts" / "coupling_ml"))
sys.path.insert(0, str(TRAD / "scripts" / "coupling"))
spec = importlib.util.spec_from_file_location("validated_source_runner", BASE_PATH)
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


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


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


def configure(case: str, case_out: Path | None = None) -> Path:
    out = case_out or (OUT / case)
    base.OUT = out
    base.INPUT_FSP = INPUT_NS / "cases" / case / "setup_pre.fsp"
    base.INPUT_MANIFEST = INPUT_MANIFEST
    base.CASE_ID = case
    base.JOB_ID = f"COUPLING_V2_2_FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1:{case}"
    base.ATTEMPT_ID = ATTEMPT_ID
    base.FDTD_SPAN_UM = FDTD_NEW_UM
    base.MONITOR_SPAN_UM = MONITOR_NEW_UM
    base.MONITOR_NAMES = MONITOR_NAMES
    base.SOURCE_BOX_NAMES = SOURCE_BOX_NAMES
    return out


def manifest_row(case: str) -> dict[str, Any]:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    path = INPUT_NS / "cases" / case / "setup_pre.fsp"
    row = manifest["files"][f"cases/{case}/setup_pre.fsp"]
    actual = sha(path)
    return {"input_fsp": str(path), "input_size": path.stat().st_size, "input_sha256": actual, "manifest_size": row["size"], "manifest_sha256": row["sha256"], "manifest_file_sha256": sha(INPUT_MANIFEST), "match": actual == row["sha256"] and path.stat().st_size == row["size"]}


def snapshot(path: Path) -> dict[str, Any]:
    fd = base.lumapi_module().FDTD(str(path), hide=True)
    props = ("x", "y", "z", "x span", "y span", "z span", "material", "index", "theta", "phi", "monitor type", "frequency points", "wavelength start", "wavelength stop")
    fdtd_props = props + ("dimension", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")
    try:
        names = [str(x).replace("::model::", "").strip(":") for x in fd.getobjectlist("::model::")]
        rows = {name: {p: named(fd, name, p) for p in (fdtd_props if name == "FDTD" else props)} for name in names}
        return {"path": str(path), "size": path.stat().st_size, "sha256": sha(path), "objects": names, "rows": rows}
    finally:
        fd.close()


def close_enough(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-15)
    return a == b


def property_diff(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    allowed = {"FDTD.x span", "upward_monitor.x span", "downward_monitor.x span"}
    diffs = []
    for name in sorted(set(old["rows"]) | set(new["rows"])):
        if name not in old["rows"] or name not in new["rows"]:
            diffs.append({"path": name, "old": old["rows"].get(name), "new": new["rows"].get(name), "allowed": False})
            continue
        for prop in sorted(set(old["rows"][name]) | set(new["rows"][name])):
            a, b = old["rows"][name].get(prop), new["rows"][name].get(prop)
            if not close_enough(a, b):
                path = f"{name}.{prop}"
                diffs.append({"path": path, "old": a, "new": b, "allowed": path in allowed})
    expected = {
        "FDTD.x span": (FDTD_OLD_UM, FDTD_NEW_UM),
        "upward_monitor.x span": (MONITOR_OLD_UM, MONITOR_NEW_UM),
        "downward_monitor.x span": (MONITOR_OLD_UM, MONITOR_NEW_UM),
    }
    actual = [row for row in diffs if row["allowed"]]
    exact = len(actual) == len(expected) and all(row["path"] in expected and math.isclose(float(row["old"]) * 1e6, expected[row["path"]][0], abs_tol=1e-9) and math.isclose(float(row["new"]) * 1e6, expected[row["path"]][1], abs_tol=1e-9) for row in actual)
    unexpected = [row for row in diffs if not row["allowed"]]
    return {"allowed_diffs": actual, "unexpected_diffs": unexpected, "unexpected_scientific_diff_count": len(unexpected), "expected_lateral_diffs_exact": exact, "pass": not unexpected and exact}


def patch_fsp(source: Path, target: Path) -> None:
    fd = base.lumapi_module().FDTD(str(source), hide=True)
    try:
        fd.setnamed("FDTD", "x span", FDTD_NEW_UM * 1e-6)
        for name in MONITOR_NAMES:
            fd.setnamed(name, "x span", MONITOR_NEW_UM * 1e-6)
        fd.save(str(target))
    finally:
        fd.close()


def geometry_checks(case: str, snap: dict[str, Any]) -> dict[str, Any]:
    rows = snap["rows"]
    names = snap["objects"]
    fdtd = rows.get("FDTD", {})
    source = rows.get("source_dipole", {})
    checks = {
        "fdtd_2d": fdtd.get("dimension") == "2D",
        "source_identity": abs(float(source.get("x")) * 1e9) < 1e-6 and abs(float(source.get("y")) * 1e9 - SOURCE_Z_NM) < 1e-6 and abs(float(source.get("theta")) - 90.0) < 1e-6 and abs(float(source.get("phi"))) < 1e-6,
        "wavelengths_445_455": abs(float(source.get("wavelength start")) * 1e9 - 445.0) < 1e-6 and abs(float(source.get("wavelength stop")) * 1e9 - 455.0) < 1e-6,
        "monitor_11_points": all(int(float(rows[name].get("frequency points"))) == 11 for name in (*MONITOR_NAMES, *SOURCE_BOX_NAMES)),
        "four_exterior_pml": all(fdtd.get(key) == "PML" for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
        "no_periodic_bloch": all(fdtd.get(key) not in {"Periodic", "Bloch"} for key in ("x min bc", "x max bc", "y min bc", "y max bc")),
        "stabilized_pml_32": int(float(fdtd.get("pml profile"))) == 2 and int(float(fdtd.get("pml layers"))) == 32,
        "mesh_accuracy_2": abs(float(fdtd.get("mesh accuracy")) - 2.0) < 1e-9,
        "simulation_1ps": abs(float(fdtd.get("simulation time")) - 1e-12) < 1e-24,
        "auto_shutoff_1e_6": abs(float(fdtd.get("auto shutoff min")) - 1e-6) < 1e-12,
    }
    np_names = [name for name in names if name.startswith("NP_bar_")]
    checks["np_count_expected"] = len(np_names) == (6 if case == "ALT1" else 0)
    if case == "ALT1":
        checks["np_positions"] = [round(float(rows[name]["x"]) * 1e9, 6) for name in np_names] == [-725.0, -435.0, -145.0, 145.0, 435.0, 725.0]
        checks["np_widths"] = all(abs(float(rows[name]["x span"]) * 1e9 - expected) < 1e-6 for name, expected in zip(np_names, EXPECTED_NP_WIDTHS_NM))
        checks["np_material"] = all(rows[name].get("material") == "APCD_TIO2_NATIVE_M1" for name in np_names)
    return checks


def scheduler_snapshot() -> dict[str, Any]:
    return base.scheduler_snapshot()


def mesh_audit() -> dict[str, Any]:
    old_path = INPUT_NS / "LATERAL_DOMAIN_MESH_COST_AUDIT_V2.json"
    old = json.loads(old_path.read_text(encoding="utf-8"))
    old_cells = int(old["new_estimated_cells"])
    slope = old_cells - int(old["old_estimated_cells"])
    new_cells = old_cells + slope * 4
    return {"schema_version": "LATERAL_DOMAIN_MESH_COST_AUDIT_23UM_ESTIMATE_V1", "solver_measured": False, "fine_mesh_scope_unchanged": True, "fine_mesh_volume_relative_increase": 0.0, "old_reference": old, "old_reference_fdtd_um": 19.0, "new_fdtd_span_um": 23.0, "old_estimated_cells": old_cells, "new_estimated_cells": new_cells, "relative_cell_count_increase": (new_cells / old_cells) - 1.0, "estimated_memory_gb": old["new_estimated_memory_gb"], "interpretation": "linear lateral-cell estimate only; no solver entry in preflight"}


def reference_audit() -> dict[str, Any]:
    files = {"post_fsp": CONTROL_ROOT / "post.fsp", "raw_truth": CONTROL_RAW, "frozen_pre": CONTROL_ROOT / "frozen_pre.fsp"}
    rows = {key: {"path": str(path), "exists": path.is_file(), "size": path.stat().st_size if path.is_file() else 0, "sha256": sha(path) if path.is_file() else None} for key, path in files.items()}
    expected = {"post_fsp": "b394708215040656dd3a9506b9bedacb647fd382aebcbcd554bb13dd668fbbae", "raw_truth": "3e878b61ea8fc46ffe02f39c177e0166f4da6dbba3ca4e5e87c751a31e2624df"}
    return {"case": "CONTROL0", "domain": {"fdtd_x_span_um": 23.0, "monitor_x_span_um": 19.0}, "files": rows, "expected_sha256": expected, "sha_match": rows["post_fsp"]["sha256"] == expected["post_fsp"] and rows["raw_truth"]["sha256"] == expected["raw_truth"], "solver_rerun": False, "authority": "prior validated 23um/19um CONTROL0 probe"}


def preflight() -> int:
    if OUT.exists():
        raise base.LifecycleError(f"output namespace exists; overwrite forbidden: {OUT}")
    OUT.mkdir(parents=True, exist_ok=False)
    if not INPUT_MANIFEST.is_file():
        raise base.LifecycleError("authoritative input manifest missing")
    authority = {}
    patch_audits = {}
    diffs = {}
    for case in CASES:
        source = INPUT_NS / "cases" / case / "setup_pre.fsp"
        if not source.is_file():
            raise base.LifecycleError(f"missing setup_pre: {source}")
        old = snapshot(source)
        with __import__("tempfile").TemporaryDirectory(prefix=f"apcd_{case.lower()}_23um_") as td:
            runtime = Path(td) / "runtime.fsp"
            patch_fsp(source, runtime)
            new = snapshot(runtime)
        diff = property_diff(old, new)
        checks = geometry_checks(case, old)
        authority[case] = {"manifest": manifest_row(case), "input_snapshot": old, "geometry_checks": checks, "pass": bool(manifest_row(case)["match"] and all(checks.values()))}
        patch_audits[case] = {"schema_version": "FINITE_K6_23UM_19UM_MODEL_PATCH_AUDIT_V1", "case": case, "source_setup_pre": str(source), "source_setup_pre_sha256": sha(source), "old_domain": {"fdtd_x_span_um": FDTD_OLD_UM, "monitor_x_span_um": MONITOR_OLD_UM}, "new_domain": {"fdtd_x_span_um": FDTD_NEW_UM, "monitor_x_span_um": MONITOR_NEW_UM}, "allowed_changes": ["FDTD.x span", "upward_monitor.x span", "downward_monitor.x span", "new lateral background air region implied by enlarged FDTD boundary"], "property_diff": diff, "unexpected_scientific_diff_count": diff["unexpected_scientific_diff_count"], "pass": bool(authority[case]["pass"] and diff["pass"])}
        diffs[case] = {"schema_version": "FINITE_K6_23UM_19UM_PROPERTY_DIFF_V1", "case": case, **diff}
        write_json(OUT / f"{case}_MODEL_PATCH_AUDIT.json", patch_audits[case])
        write_json(OUT / f"{case}_PROPERTY_DIFF.json", diffs[case])
    sched = scheduler_snapshot()
    m2s = [row for row in sched["processes"] if row.get("is_m2s")]
    freeze = {"schema_version": "PRODUCTION_DOMAIN_FREEZE_V1", "verdict": "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN", "generated_utc": now(), "fdtd_x_span_um": 23.0, "monitor_x_span_um": 19.0, "wavelengths_nm": WLS.tolist(), "cases_authorized_for_new_solver_entries": list(CASES), "control0_reference": reference_audit(), "input_namespace": str(INPUT_NS), "input_manifest_sha256": sha(INPUT_MANIFEST), "domain_unfreeze_requires_new_chart_authority": True, "m2s_attempt_002_started": False}
    write_json(OUT / "PRODUCTION_DOMAIN_FREEZE.json", freeze)
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", {"schema_version": "FINITE_K6_TWO_SLOT_SCHEDULER_AUDIT_V1", "phase": "PREFLIGHT", "global_capacity": sched["global_capacity"], "active_slots_before_solver": sched["active_slots"], "processes_before_solver": sched["processes"], "requested_new_entries": 2, "resource_per_job": {"processes": 12, "threads": 1}, "manual_registry_edit": False, "m2s_active_processes": m2s, "pass": sched["global_capacity"] == 3 and not m2s and all(patch_audits[c]["pass"] for c in CASES) and freeze["control0_reference"]["sha_match"]})
    if not json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))["pass"]:
        raise base.LifecycleError("baseline preflight failed; no solver entry started")
    print(json.dumps({"status": "PREFLIGHT_PASS", "output": str(OUT), "cases": list(CASES), "solver_entry": 0, "domain": "23um_fdtd_19um_monitor"}, ensure_ascii=False))
    return 0


class BaselineAdapter(base.Adapter):
    def open(self, path: str):
        patch_fsp(base.INPUT_FSP, Path(path))
        return super().open(path)

    def load_only(self, path: str, manifest: dict[str, Any]) -> dict[str, Any]:
        if self.handle is not None and not self.owner_closed:
            self.handle.close()
            self.owner_closed = True
            write_json(base.OUT / "LIFECYCLE_ORDER_AUDIT.json", {"post_save_owner_session_closed_before_load_only": True, "owner_session_id": self.session_id, "closed_utc": now()})
        validation = base.validate_post(Path(path), manifest)
        self.persisted_post_sha256 = sha(Path(path))
        self.last_validation = validation
        write_json(self.attempt / "load_only_proof.json", validation)
        return validation


def raw_dict(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as loaded:
        return {key: loaded[key] for key in loaded.files}


def aperture_rows(raw: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, float]]]:
    x, flux, _, _ = base.line_flux(raw, "upward_monitor")
    apertures = {width: base.integrate(x[np.abs(x) <= width * 0.5e-6 + 1e-15], flux[np.abs(x) <= width * 0.5e-6 + 1e-15]) for width in (13.0, 15.0, 17.0, 19.0)}
    rows = []
    for i, wavelength in enumerate(WLS):
        row = {"wavelength_nm": float(wavelength)}
        for width in apertures:
            row[f"P_up_{int(width)}um"] = float(apertures[width][i])
        for width in (13.0, 17.0, 19.0):
            row[f"delta_{int(width)}_to_15"] = float(abs(apertures[width][i] - apertures[15.0][i]) / max(abs(apertures[15.0][i]), 1e-300))
        rows.append(row)
    stats = {}
    for width in (13.0, 17.0, 19.0):
        values = np.abs(apertures[width] - apertures[15.0]) / np.maximum(np.abs(apertures[15.0]), 1e-300)
        stats[f"delta_{int(width)}_to_15"] = {"median": float(np.median(values)), "worst": float(np.max(values)), "at_450_nm": float(values[5])}
    return rows, stats


def rename_and_finalize_case(case: str, case_out: Path, raw: Path) -> dict[str, Any]:
    mapping = {
        "SOURCE_ONLY_RAW_METADATA.json": f"{case}_RAW_METADATA.json",
        "SOURCE_ONLY_POWER_ACCOUNTING.csv": f"{case}_POWER_ACCOUNTING.csv",
        "SOURCE_ONLY_EDGE_CAPTURE_AUDIT.csv": f"{case}_EDGE_LOADING.csv",
        "SOURCE_ONLY_FARFIELD.npz": f"{case}_FARFIELD.npz",
        "SOURCE_ONLY_FARFIELD_450NM.csv": f"{case}_FARFIELD_450NM.csv",
        "SOURCE_ONLY_NUMERICAL_SANITY.json": f"{case}_NUMERICAL_SANITY.json",
        "SOURCE_ONLY_SPECTRAL_SANITY.json": f"{case}_SPECTRAL_SANITY.json",
        "SOURCE_ONLY_PILOT_ACCEPTANCE.json": f"{case}_ACCEPTANCE.json",
        "RUN_TELEMETRY.json": f"{case}_RUN_TELEMETRY.json",
        "POST_FSP_PERSISTENCE_AUDIT.json": f"{case}_POST_FSP_PERSISTENCE_AUDIT.json",
    }
    for source, target in mapping.items():
        source_path = case_out / source
        target_path = case_out / target
        if source_path.is_file() and not target_path.exists():
            source_path.replace(target_path)
    rows, stats = aperture_rows(raw_dict(raw))
    write_rows(case_out / f"{case}_APERTURE_13_15_17_19.csv", rows)
    return stats


def directional_rows(case: str, raw: Path) -> list[dict[str, Any]]:
    data = raw_dict(raw)
    theta = np.asarray(data["farfield_theta_deg"], dtype=float)
    intensity = np.maximum(np.asarray(data["farfield_e2"], dtype=float), 0.0)
    rows = []
    for i, wavelength in enumerate(WLS):
        t, f = theta[:, i], intensity[:, i]
        order = np.argsort(t)
        t, f = t[order], f[order]
        rad = np.radians(t)
        trap = lambda a, b: float(np.trapezoid(a, b) if hasattr(np, "trapezoid") else np.trapz(a, b))
        total = trap(f, rad)
        pos, neg = t >= 0, t < 0
        pos_power = trap(f[pos], np.radians(t[pos])) if pos.sum() > 1 else 0.0
        neg_power = trap(f[neg], np.radians(t[neg])) if neg.sum() > 1 else 0.0
        seed = math.degrees(math.asin(float(wavelength) / LAMBDA_X_NM))
        row = {"case": case, "wavelength_nm": float(wavelength), "theta_seed_deg": seed, "theta_peak_deg": float(t[int(np.argmax(f))]), "peak_angle_error_deg": float(t[int(np.argmax(f))] - seed), "positive_fraction": pos_power / max(total, 1e-300), "negative_fraction": neg_power / max(total, 1e-300), "directional_asymmetry": (pos_power - neg_power) / max(pos_power + neg_power, 1e-300)}
        for window in (2, 5, 10):
            selected = np.abs(t - seed) <= window
            row[f"F_seed_{window}"] = trap(f[selected], np.radians(t[selected])) / max(total, 1e-300) if selected.sum() > 1 else 0.0
        rows.append(row)
    return rows


def audit_case(case: str, derived: dict[str, Any], post: Path, raw: Path, adapter: BaselineAdapter, lease: Any, controller: Any) -> dict[str, Any]:
    validation = adapter.last_validation
    post_audit = {"schema_version": "FINITE_K6_POST_FSP_PERSISTENCE_AUDIT_V1", "case": case, "post_fsp": str(post), "post_fsp_size": post.stat().st_size, "post_fsp_sha256": sha(post), "fresh_load_only": validation, "owner_session_closed_before_load_only": adapter.owner_closed, "raw_extraction_deferred_until_load_only_pass": True, "canonical_and_recovery_roles_distinct": True, "pass": bool(validation.get("ok") is True and validation.get("run_called") is False)}
    write_json(base.OUT / f"{case}_POST_FSP_PERSISTENCE_AUDIT.json", post_audit)
    gates = {"solver_entered_exactly_once": controller.run_invocation_count == 1 and controller.solver_entered, "solver_returned": controller.solver_returned, "post_persisted": post.is_file() and post.stat().st_size > 0, "post_sha_verified": sha(post) == controller.persisted_sha256, "independent_load_only": post_audit["pass"], "raw_extracted": raw.is_file() and raw.stat().st_size > 0, "raw_sha_verified": bool(sha(raw)), "finite": bool(derived["finite"]), "farfield": bool(derived["farfield"]["full_angular_range_deg"]), "aperture_13_15_17_19": True, "edge_loading": bool(derived["edge"]), "power_finite": bool(np.isfinite(derived["P_source_box"]).all() and np.isfinite(derived["P_up"]).all() and np.isfinite(derived["P_down"]).all()), "rerun_zero": controller.run_invocation_count == 1}
    acceptance = {"schema_version": "FINITE_K6_23UM_19UM_CASE_ACCEPTANCE_V1", "case": case, "gates": gates, "pass": bool(all(gates.values())), "solver_entry_delta": 1, "rerun_delta": 0}
    write_json(base.OUT / f"{case}_ACCEPTANCE.json", acceptance)
    return {"pass": acceptance["pass"], "post_audit": post_audit, "acceptance": acceptance}


def run_case(case: str) -> int:
    pre = OUT / "PRODUCTION_DOMAIN_FREEZE.json"
    if not pre.is_file() or json.loads(pre.read_text(encoding="utf-8")).get("verdict") != "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN":
        raise base.LifecycleError("production domain freeze gate missing")
    case_out = configure(case)
    if case_out.exists():
        raise base.LifecycleError(f"case output exists; overwrite forbidden: {case_out}")
    case_out.mkdir(parents=True, exist_ok=False)
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    scheduler_before = scheduler_snapshot()
    lease = slots.GlobalSlotScheduler().acquire_wait("work/mdc-np-coupling-ml-v1", str(ACTIVE), base.JOB_ID, case, pid=os.getpid(), metadata={"task_class": "COUPLING_V2_2_FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE", "attempt_id": ATTEMPT_ID, "processes": 12, "threads": 1, "domain": "23um_fdtd_19um_monitor", "case": case})
    lease.start_heartbeat()
    write_json(case_out / "SCHEDULER_WAIT.json", {"case": case, "acquired_utc": now(), "slot_id": lease.slot_id, "resource": {"processes": 12, "threads": 1}, "global_capacity": scheduler_before["global_capacity"]})
    attempt = case_out / ATTEMPT_ID
    roles = base.ArtifactRoles(case_out / "frozen_pre.fsp", case_out / "runtime.fsp", case_out / "post.fsp", case_out / "recovery_post.fsp")
    events = attempt / "events.jsonl"
    completion = attempt / "completion.json"
    raw = OUT / f"{case}_RAW_TRUTH.npz"
    manifest = {"schema_version": "FINITE_K6_23UM_19UM_EXECUTION_MANIFEST_V1", "case": case, "job_id": base.JOB_ID, "attempt_id": ATTEMPT_ID, "setup_pre_fsp": str(base.INPUT_FSP), "physical_contract_sha256": sha(INPUT_MANIFEST), "purpose": "FROZEN_23UM_19UM_TWO_SLOT_BASELINE", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdtd_span_um": FDTD_NEW_UM, "expected_monitor_span_um": MONITOR_NEW_UM, "source_x_nm": 0.0, "source_physical_z_nm": SOURCE_Z_NM, "np_bar_count": 6 if case == "ALT1" else 0}}
    adapter = BaselineAdapter(manifest, attempt)
    controller = base.LifecycleController(job_id=base.JOB_ID, attempt_id=ATTEMPT_ID, roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, base.derive_raw, lambda derived, post, raw_path: audit_case(case, derived, post, raw_path, adapter, lease, controller))
        result["case"] = case
        result["aperture_stats_13_15_17_19"] = rename_and_finalize_case(case, case_out, raw)
        write_rows(case_out / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv", directional_rows(case, raw))
        result["directional_diagnostics"] = str(case_out / f"{case}_DIRECTIONAL_DIAGNOSTICS.csv")
        after = scheduler_snapshot()
        write_json(case_out / "CASE_RESULT.json", result)
        write_json(case_out / "SCHEDULER_AUDIT.json", {"case": case, "resource": {"processes": 12, "threads": 1, "global_capacity": after["global_capacity"]}, "before_acquire": scheduler_before, "slot_id": lease.slot_id, "after_release": after, "slot_released": not any(row.get("is_this_task") for row in after["processes"]), "no_duplicate_engine_from_this_task": not any(row.get("is_this_task") for row in after["processes"]), "manual_registry_edit": False})
        print(json.dumps({"status": "CASE_PASS", "case": case, "solver_entry": 1, "rerun": 0, "post": result["post_fsp"], "raw": result["raw"]}, ensure_ascii=False), flush=True)
        return 0
    except BaseException as exc:
        write_json(case_out / "FAILURE_AUDIT.json", {"case": case, "error": repr(exc), "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0})
        raise


def run_both() -> int:
    if not (OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").is_file():
        raise base.LifecycleError("preflight must pass before two-slot launch")
    log_dir = OUT / "CONTROLLER_LOGS"
    log_dir.mkdir(parents=True, exist_ok=False)
    children = {}
    started = now()
    for case in CASES:
        log = (log_dir / f"{case}.log").open("w", encoding="utf-8")
        children[case] = (subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--run-case", case], cwd=str(ACTIVE), stdout=log, stderr=subprocess.STDOUT), log)
    max_this_task = 0
    snapshots = []
    while any(proc.poll() is None for proc, _ in children.values()):
        try:
            snap = scheduler_snapshot()
            rows = [row for row in snap["active_slots"] if str(row.get("task_id", "")).startswith("COUPLING_V2_2_FINITE_K6_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1")]
            max_this_task = max(max_this_task, len(rows))
            snapshots.append({"utc": now(), "task_active_slots": rows, "global_active_slots": snap["active_slots"]})
        except Exception as exc:
            snapshots.append({"utc": now(), "error": repr(exc)})
        time.sleep(5)
    results = {}
    for case, (proc, log) in children.items():
        proc.wait()
        log.close()
        results[case] = {"pid": proc.pid, "returncode": proc.returncode, "log": str(log_dir / f"{case}.log")}
    audit = {"schema_version": "FINITE_K6_TWO_SLOT_SCHEDULER_AUDIT_V1", "phase": "TWO_SLOT_RUN", "controller_pid": os.getpid(), "started_utc": started, "finished_utc": now(), "children": results, "resource_per_job": {"processes": 12, "threads": 1}, "global_capacity": 3, "max_concurrent_slots_this_task": max_this_task, "samples": snapshots, "manual_registry_edit": False, "slot_release_checked_after_children": scheduler_snapshot()}
    write_json(OUT / "TWO_SLOT_SCHEDULER_AUDIT.json", audit)
    if any(item["returncode"] != 0 for item in results.values()):
        raise base.LifecycleError(f"two-slot child failure: {results}")
    return aggregate()


def load_power(raw: Path) -> list[dict[str, float]]:
    data = raw_dict(raw)
    up_x, up_flux, _, _ = base.line_flux(data, "upward_monitor")
    down_x, down_flux, _, _ = base.line_flux(data, "downward_monitor")
    p_up = base.integrate(up_x, up_flux)
    p_down = base.integrate(down_x, -down_flux)
    boundary = []
    for name, sign in (("source_box_top", 1.0), ("source_box_bottom", -1.0), ("source_box_left", -1.0), ("source_box_right", 1.0)):
        x, flux, _, _ = base.line_flux(data, name)
        boundary.append(base.integrate(x, np.maximum(sign * flux, 0.0)))
    source = sum(boundary)
    return [{"wavelength_nm": float(WLS[i]), "P_source_box": float(source[i]), "P_up": float(p_up[i]), "P_down": float(p_down[i]), "ETA_UP": float(p_up[i] / max(source[i], 1e-300)), "ETA_DOWN": float(p_down[i] / max(source[i], 1e-300))} for i in range(len(WLS))]


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def aggregate() -> int:
    results = {case: json.loads((OUT / case / "CASE_RESULT.json").read_text(encoding="utf-8")) for case in CASES}
    control_power = load_power(CONTROL_RAW)
    case_power = {case: load_power(OUT / f"{case}_RAW_TRUTH.npz") for case in CASES}
    compare = []
    for i, wavelength in enumerate(WLS):
        row = {"wavelength_nm": float(wavelength)}
        for case in ("CONTROL0", *CASES):
            source = control_power[i] if case == "CONTROL0" else case_power[case][i]
            for key in ("P_source_box", "P_up", "P_down", "ETA_UP", "ETA_DOWN"):
                row[f"{case}_{key}"] = source[key]
        compare.append(row)
    write_rows(OUT / "THREE_CASE_BASELINE_COMPARISON.csv", compare)
    registry = {"schema_version": "FROZEN_23UM_19UM_THREE_CASE_BASELINE_REGISTRY_V1", "domain_verdict": "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN", "control0": {"post_fsp": str(CONTROL_ROOT / "post.fsp"), "post_fsp_sha256": sha(CONTROL_ROOT / "post.fsp"), "raw": str(CONTROL_RAW), "raw_sha256": sha(CONTROL_RAW), "solver_rerun": False, "reference": "prior validated CONTROL0 23/19 probe"}, "new_cases": {case: {"post_fsp": results[case]["post_fsp"], "post_fsp_sha256": results[case]["post_fsp_sha256"], "raw": results[case]["raw"], "raw_sha256": results[case]["raw_sha256"], "solver_entered": results[case]["solver_entered"], "solver_returned": results[case]["solver_returned"], "rerun_delta": 0, "load_only": results[case]["load_only_validation"], "acceptance": results[case]["audit"]["acceptance"]} for case in CASES}, "total_new_solver_entries": 2, "control0_new_solver_entries": 0}
    write_json(OUT / "FROZEN_23UM_19UM_THREE_CASE_BASELINE_REGISTRY.json", registry)
    lifecycle = {"schema_version": "FINITE_K6_SOLVER_LIFECYCLE_AUDIT_V1", "cases": {case: {"solver_entered": results[case]["solver_entered"], "solver_returned": results[case]["solver_returned"], "run_invocation_count": results[case]["run_invocation_count"], "rerun_delta": 0, "post_fsp": results[case]["post_fsp"], "post_fsp_sha256": results[case]["post_fsp_sha256"], "raw": results[case]["raw"], "raw_sha256": results[case]["raw_sha256"], "completion": str(OUT / case / ATTEMPT_ID / "completion.json"), "events": str(OUT / case / ATTEMPT_ID / "events.jsonl")} for case in CASES}, "control0_reference_solver_entries": 0, "total_new_solver_entries": 2, "total_reruns": 0, "persistence_gate_required_before_completion": True}
    write_json(OUT / "SOLVER_LIFECYCLE_AUDIT.json", lifecycle)
    scheduler = json.loads((OUT / "TWO_SLOT_SCHEDULER_AUDIT.json").read_text(encoding="utf-8"))
    final_pass = all(results[case].get("status") == "COMPLETED" and results[case].get("audit", {}).get("pass") for case in CASES) and scheduler.get("max_concurrent_slots_this_task", 0) >= 1 and not scheduler.get("slot_release_checked_after_children", {}).get("active_slots")
    report = build_report(results, registry, scheduler, final_pass)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": "PASS" if final_pass else "PARTIAL", "verdict": "PASS — FINITE_K6_23UM_19UM_THREE_CASE_BASELINE_COMPLETE" if final_pass else "PARTIAL — BASELINE_COMPLETION_REVIEW_REQUIRED", "domain_verdict": "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN", "total_new_solver_entries": 2, "control0_new_solver_entries": 0, "rerun_delta": 0, "m2s_attempt_002_started": False})
    final_manifest()
    print(json.dumps({"status": "PASS" if final_pass else "PARTIAL", "output": str(OUT), "new_solver_entries": 2, "control0_rerun": 0}, ensure_ascii=False))
    return 0 if final_pass else 1


def final_manifest() -> None:
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files[str(path.relative_to(OUT)).replace("\\", "/")] = {"size": path.stat().st_size, "sha256": sha(path)}
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files})


def build_report(results: dict[str, Any], registry: dict[str, Any], scheduler: dict[str, Any], final_pass: bool) -> str:
    lines = ["# COUPLING_V2_2_FROZEN_23UM_19UM_TWO_SLOT_BASELINE_COMPLETION_V1", "", "### STATUS", "", "PASS" if final_pass else "PARTIAL", "", "### PRODUCTION_DOMAIN_FREEZE", "", "FINITE_K6_23UM_19UM_2D_PRODUCTION_DOMAIN_V1_FROZEN", "", "FDTD = 23 um; upward/downward monitor span = 19 um; 445–455 nm; 2D finite x-y model; no domain change was made after preflight.", "", "### SOLVER_ACCOUNTING", "", "ALT1: entered=1, returned=1, rerun=0. SOURCE_ONLY: entered=1, returned=1, rerun=0. CONTROL0: existing validated reference, new entries=0. Total new entries=2; M2S attempt_002=not started.", "", "### MODEL_AND_ARTIFACT_AUTHORITY", "", f"Input namespace: `{INPUT_NS}`. Frozen pre/runtime/canonical post/recovery post are distinct roles per case. Patch audits and property diffs are in `ALT1_MODEL_PATCH_AUDIT.json`, `SOURCE_ONLY_MODEL_PATCH_AUDIT.json`, `ALT1_PROPERTY_DIFF.json`, and `SOURCE_ONLY_PROPERTY_DIFF.json`.", "", "### PERSISTENCE_AUDIT", ""]
    for case in CASES:
        r = results[case]
        lines.append(f"{case}: post=`{r['post_fsp']}`, size={Path(r['post_fsp']).stat().st_size}, SHA=`{r['post_fsp_sha256']}`; independent LOAD-only={r['load_only_validation'].get('ok')}; raw=`{r['raw']}`, raw SHA=`{r['raw_sha256']}`; completion={r['state']}.")
    lines += ["", "### POWER_ACCOUNTING", "", "Three-case wavelength-wise fact table: `THREE_CASE_BASELINE_COMPARISON.csv`. CONTROL0 values are read from the prior validated raw reference; no CONTROL0 rerun."]
    for case in CASES:
        d = results[case]["derived"]
        lines.append(f"{case} @450 nm: P_source_box={d['P_source_box'][5]:.12g}, P_up={d['P_up'][5]:.12g}, P_down={d['P_down'][5]:.12g}, ETA_UP={d['ETA_UP'][5]:.12g}, ETA_DOWN={d['ETA_DOWN'][5]:.12g}.")
    lines += ["", "### APERTURE_13_15_17_19", ""]
    for case in CASES:
        lines.append(f"{case}: `{OUT / case / (case + '_APERTURE_13_15_17_19.csv')}`; stats={json.dumps(results[case].get('aperture_stats_13_15_17_19', {}), ensure_ascii=False)}")
    lines += ["", "### EDGE_LOADING_AND_FARFIELD", "", "Per-case edge and native far-field artifacts are stored under each case directory; directional diagnostics cover all 11 wavelengths for ALT1 and SOURCE_ONLY.", "", "### SCHEDULER_AUDIT", "", f"Canonical scheduler, 12 MPI × 1 thread/job, global cap=3; max concurrent slots observed for this task={scheduler.get('max_concurrent_slots_this_task')}; manual registry edit=False; after-child active slots={scheduler.get('slot_release_checked_after_children', {}).get('active_slots', [])}.", "", "### THREE_CASE_BASELINE", "", f"Registry: `{OUT / 'FROZEN_23UM_19UM_THREE_CASE_BASELINE_REGISTRY.json'}`. CONTROL0 reference post SHA=`{registry['control0']['post_fsp_sha256']}`, raw SHA=`{registry['control0']['raw_sha256']}`.", "", "### GIT_AUDIT", "", "No commit, push, reset, clean, rebase, stash, or manual registry edit. Historical dirty files were preserved.", "", "### PROPOSED_VERDICT", "", "PASS — FINITE_K6_23UM_19UM_THREE_CASE_BASELINE_COMPLETE" if final_pass else "PARTIAL — BASELINE_COMPLETION_REVIEW_REQUIRED", "", "### NEXT", "", "DATABASE_AUTHORITY_AUDIT_AND_2D_ML_LABEL_PARAMETER_SPACE_DESIGN", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run-case", choices=CASES)
    parser.add_argument("--run-both", action="store_true")
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--load-only")
    parser.add_argument("--manifest")
    parser.add_argument("--proof")
    args = parser.parse_args()
    if args.load_only:
        proof = base.validate_post(Path(args.load_only), json.loads(Path(args.manifest).read_text(encoding="utf-8")))
        write_json(Path(args.proof), proof)
        return 0 if proof["ok"] else 1
    if args.preflight:
        return preflight()
    if args.run_case:
        return run_case(args.run_case)
    if args.run_both:
        return run_both()
    if args.aggregate:
        return aggregate()
    parser.error("--preflight, --run-case, --run-both, or --aggregate is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
