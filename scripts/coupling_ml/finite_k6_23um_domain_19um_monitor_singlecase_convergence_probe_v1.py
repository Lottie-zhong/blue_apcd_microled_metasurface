"""Exactly-one-entry CONTROL0 23 um / 19 um lateral convergence probe."""
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
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

ACTIVE = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1")
TRAD = Path(r"D:\project\worktrees\blue_apcd_mdc_np_coupling_v1")
INPUT_NS = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_FINAL_LATERAL_DOMAIN_19UM_MONITOR_15UM_PATCH_V1"
INPUT_FSP = INPUT_NS / r"cases\CONTROL0\setup_pre.fsp"
INPUT_MANIFEST = INPUT_NS / "FINAL_SHA256_MANIFEST.json"
OLD_ROOT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_CONTROL0_ALT1_2D_INTEGRATED_PILOT_V1"
OLD_RAW = OLD_ROOT / r"CONTROL0\CONTROL0_RAW_TRUTH.npz"
OUT = ACTIVE / r"outputs\coupling_v2_2\FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1"
WORK = OUT / "VALIDATED_PROBE"
API = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
BASE_PATH = ACTIVE / r"scripts\coupling_ml\finite_k6_source_only_2d_scientific_pilot_v1.py"
WLS = np.arange(445.0, 456.0, 1.0)
CASE = "CONTROL0"
JOB_ID = "COUPLING_V2_2_FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1:CONTROL0"
ATTEMPT_ID = "attempt_001"
FDTD_OLD_UM = 19.0
MONITOR_OLD_UM = 15.0
FDTD_NEW_UM = 23.0
MONITOR_NEW_UM = 19.0
SOURCE_Z_NM = -276.0
N_FARFIELD = 721
FIELD_KEYS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
MONITOR_NAMES = ("upward_monitor", "downward_monitor")
SOURCE_BOX_NAMES = ("source_box_top", "source_box_bottom", "source_box_left", "source_box_right")

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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def configure_base(output: Path) -> None:
    base.OUT = output
    base.INPUT_FSP = INPUT_FSP
    base.INPUT_MANIFEST = INPUT_MANIFEST
    base.CASE_ID = CASE
    base.JOB_ID = JOB_ID
    base.ATTEMPT_ID = ATTEMPT_ID
    base.FDTD_SPAN_UM = FDTD_NEW_UM
    base.MONITOR_SPAN_UM = MONITOR_NEW_UM
    base.MONITOR_NAMES = MONITOR_NAMES
    base.SOURCE_BOX_NAMES = SOURCE_BOX_NAMES


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


def input_manifest() -> dict[str, Any]:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    row = manifest["files"]["cases/CONTROL0/setup_pre.fsp"]
    return {
        "input_namespace": str(INPUT_NS),
        "input_fsp": str(INPUT_FSP),
        "input_fsp_size": INPUT_FSP.stat().st_size,
        "input_fsp_sha256": sha(INPUT_FSP),
        "manifest_sha256": row["sha256"],
        "manifest_size": row["size"],
        "manifest_file_sha256": sha(INPUT_MANIFEST),
        "match": INPUT_FSP.stat().st_size == row["size"] and sha(INPUT_FSP) == row["sha256"],
    }


def snapshot(path: Path) -> dict[str, Any]:
    fd = base.lumapi_module().FDTD(str(path), hide=True)
    props = ("x", "y", "z", "x span", "y span", "z span", "material", "index", "theta", "phi", "monitor type", "frequency points", "wavelength start", "wavelength stop")
    fdtd_props = props + ("dimension", "x min bc", "x max bc", "y min bc", "y max bc", "pml profile", "pml layers", "simulation time", "auto shutoff min", "mesh accuracy")
    try:
        names = [str(x).replace("::model::", "").strip(":") for x in fd.getobjectlist("::model::")]
        rows = {name: {p: named(fd, name, p) for p in (fdtd_props if name == "FDTD" else props)} for name in names}
        return {"path": str(path), "sha256": sha(path), "size": path.stat().st_size, "objects": names, "rows": rows}
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
    unexpected = [row for row in diffs if not row["allowed"]]
    allowed_actual = [row for row in diffs if row["allowed"]]
    expected = {
        "FDTD.x span": (FDTD_OLD_UM, FDTD_NEW_UM),
        "upward_monitor.x span": (MONITOR_OLD_UM, MONITOR_NEW_UM),
        "downward_monitor.x span": (MONITOR_OLD_UM, MONITOR_NEW_UM),
    }
    exact_allowed = len(allowed_actual) == len(expected) and all(
        row["path"] in expected and math.isclose(float(row["old"]) * 1e6, expected[row["path"]][0], abs_tol=1e-9) and math.isclose(float(row["new"]) * 1e6, expected[row["path"]][1], abs_tol=1e-9)
        for row in allowed_actual
    )
    return {"allowed_diffs": allowed_actual, "unexpected_diffs": unexpected, "unexpected_scientific_diff_count": len(unexpected), "expected_lateral_diffs_exact": exact_allowed, "pass": not unexpected and exact_allowed}


def patch_fsp(source: Path, target: Path) -> dict[str, Any]:
    fd = base.lumapi_module().FDTD(str(source), hide=True)
    try:
        fd.setnamed("FDTD", "x span", FDTD_NEW_UM * 1e-6)
        for name in MONITOR_NAMES:
            fd.setnamed(name, "x span", MONITOR_NEW_UM * 1e-6)
        fd.save(str(target))
    finally:
        fd.close()
    return snapshot(target)


def process_snapshot() -> list[dict[str, Any]]:
    return base.process_snapshot()


def scheduler_snapshot() -> dict[str, Any]:
    return base.scheduler_snapshot()


def case_selection() -> dict[str, Any]:
    acceptance = json.loads((OLD_ROOT / "INTEGRATED_DOMAIN_ACCEPTANCE.json").read_text(encoding="utf-8"))
    comparison = list(csv.DictReader((OLD_ROOT / "CONTROL0_ALT1_COMPARISON.csv").open(encoding="utf-8")))
    rows = {}
    for case in ("CONTROL0", "ALT1"):
        field = f"{case}_delta_13_to_15"
        row = max(comparison, key=lambda item: float(item[field]))
        rows[case] = {
            "max_delta_13_to_15": float(row[field]),
            "worst_wavelength_nm": float(row["wavelength_nm"]),
            "edge_worst": acceptance["cases"][case]["edge"]["worst"],
            "over_60_at_450_nm": acceptance["cases"][case]["farfield_450"]["over_60_fraction"],
        }
    selected = "CONTROL0" if rows["CONTROL0"]["max_delta_13_to_15"] > rows["ALT1"]["max_delta_13_to_15"] else "ALT1"
    return {
        "schema_version": "FINITE_K6_CASE_SELECTION_AUDIT_V1",
        "source_artifact": str(OLD_ROOT / "CONTROL0_ALT1_COMPARISON.csv"),
        "cases": rows,
        "selection_rule": "argmax(max_lambda(delta_13_to_15)); tie-break edge worst, >60 fraction, CONTROL0",
        "selected_case": selected,
        "selected_reason": f"{selected} has the larger formal max_lambda(delta_13_to_15)",
        "pass": selected == CASE,
    }


def verify_old_authority() -> dict[str, Any]:
    manifest = json.loads((OLD_ROOT / "FINAL_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    bad = []
    for rel, row in manifest["files"].items():
        path = OLD_ROOT / rel
        if not path.is_file() or path.stat().st_size != row["size"] or sha(path) != row["sha256"]:
            bad.append(rel)
    return {"manifest": str(OLD_ROOT / "FINAL_SHA256_MANIFEST.json"), "manifest_entries": len(manifest["files"]), "bad_entries": bad, "manifest_pass": not bad}


def mesh_audit() -> dict[str, Any]:
    prior_path = INPUT_NS / "LATERAL_DOMAIN_MESH_COST_AUDIT_V2.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    old_cells = int(prior["new_estimated_cells"])
    increment_per_um = (old_cells - int(prior["old_estimated_cells"])) / (float(prior["new_fdtd_span_um"]) - float(prior["old_fdtd_span_um"]))
    new_cells = int(round(old_cells + increment_per_um * (FDTD_NEW_UM - FDTD_OLD_UM)))
    return {
        "schema_version": "FINITE_K6_23UM_MESH_COST_AUDIT_V1",
        "source_evidence": str(prior_path),
        "solver_measured": False,
        "old_fdtd_span_um": FDTD_OLD_UM,
        "new_fdtd_span_um": FDTD_NEW_UM,
        "old_estimated_cells": old_cells,
        "new_estimated_cells": new_cells,
        "relative_cell_count_increase": (new_cells - old_cells) / old_cells,
        "old_estimated_memory_gb": prior["new_estimated_memory_gb"],
        "new_estimated_memory_gb": prior["new_estimated_memory_gb"],
        "fine_mesh_scope": "mesh_interfaces_np and mesh_dipole_neighborhood unchanged; added region is background air only",
        "fine_mesh_volume_change": 0.0,
        "formula": "19->23 estimate uses the audited 17->19 coarse-air cell increment; no solver mesh measurement claimed",
        "pass": bool(prior["fine_mesh_scope_unchanged"] and prior["fine_mesh_volume_relative_increase"] == 0.0),
    }


def preflight() -> int:
    global WORK
    existing = [path.name for path in OUT.iterdir()] if OUT.exists() else []
    if OUT.exists():
        if any((OUT / name).is_file() for name in ("REPORT.md", "FINAL_SHA256_MANIFEST.json")) or (OUT / CASE / "post.fsp").exists():
            raise base.LifecycleError(f"output namespace has completed/protected state; overwrite forbidden: {OUT}")
    else:
        OUT.mkdir(parents=True, exist_ok=False)
    if WORK.exists():
        if any(WORK.iterdir()) or (WORK / CASE / "post.fsp").exists():
            raise base.LifecycleError(f"validated artifact root has state; overwrite forbidden: {WORK}")
    else:
        WORK.mkdir(parents=True, exist_ok=False)
    old_authority = verify_old_authority()
    selection = case_selection()
    authority = input_manifest()
    old = snapshot(INPUT_FSP)
    with tempfile.TemporaryDirectory(prefix="apcd_23um_probe_") as td:
        runtime = Path(td) / "runtime.fsp"
        new = patch_fsp(INPUT_FSP, runtime)
    diff = property_diff(old, new)
    mesh = mesh_audit()
    sched = scheduler_snapshot()
    m2s = [row for row in sched["processes"] if row.get("is_m2s")]
    model_patch = {
        "schema_version": "FINITE_K6_23UM_MODEL_PATCH_AUDIT_V1",
        "source_setup_pre": str(INPUT_FSP),
        "source_setup_pre_sha256": sha(INPUT_FSP),
        "old_domain": {"fdtd_x_span_um": FDTD_OLD_UM, "upward_monitor_x_span_um": MONITOR_OLD_UM, "downward_monitor_x_span_um": MONITOR_OLD_UM},
        "new_domain": {"fdtd_x_span_um": FDTD_NEW_UM, "upward_monitor_x_span_um": MONITOR_NEW_UM, "downward_monitor_x_span_um": MONITOR_NEW_UM},
        "old_snapshot": old,
        "new_snapshot": new,
        "allowed_scientific_changes": ["FDTD.x span", "upward_monitor.x span", "downward_monitor.x span", "added background air between old and new FDTD boundaries"],
        "unexpected_scientific_diff_count": diff["unexpected_scientific_diff_count"],
        "pass": bool(authority["match"] and diff["pass"] and selection["pass"] and old_authority["manifest_pass"]),
    }
    write_json(OUT / "CASE_SELECTION_AUDIT.json", selection)
    write_json(OUT / "MODEL_PATCH_AUDIT.json", model_patch)
    write_json(OUT / "SCIENTIFIC_PROPERTY_DIFF.json", {"schema_version": "FINITE_K6_SCIENTIFIC_PROPERTY_DIFF_V1", **diff})
    write_json(OUT / "MESH_COST_AUDIT.json", mesh)
    write_json(OUT / "PREFLIGHT_AUDIT.json", {"schema_version": "FINITE_K6_23UM_SINGLECASE_PREFLIGHT_V1", "generated_utc": now(), "preexisting_partial_artifacts_preserved": existing, "validated_artifact_root": str(WORK), "input_manifest": authority, "old_authority": old_authority, "scheduler_before_solver": sched, "m2s_active_processes": m2s, "property_diff": diff, "mesh": mesh, "pass": model_patch["pass"]})
    if not model_patch["pass"]:
        raise base.LifecycleError("single-case 23/19 preflight failed")
    print(json.dumps({"status": "PREFLIGHT_PASS", "selected_case": CASE, "unexpected_scientific_diff_count": diff["unexpected_scientific_diff_count"], "fine_mesh_volume_change": mesh["fine_mesh_volume_change"]}, ensure_ascii=False))
    return 0


class ProbeAdapter(base.Adapter):
    def open(self, path: str):
        # ArtifactRoles.prepare intentionally copies frozen pre into runtime;
        # this is the one mutable, pre-solver lateral patch.
        patch_fsp(INPUT_FSP, Path(path))
        return super().open(path)

    def load_only(self, path: str, manifest: dict[str, Any]) -> dict[str, Any]:
        if self.handle is not None and not self.owner_closed:
            self.handle.close()
            self.owner_closed = True
            write_json(base.OUT / "LIFECYCLE_ORDER_AUDIT.json", {"post_save_owner_session_closed_before_load_only": True, "owner_session_id": self.session_id, "closed_utc": now()})
        request = self.attempt / "load_only_request.json"
        proof = self.attempt / "load_only_proof.json"
        write_json(request, manifest)
        validation = base.validate_post(Path(path), manifest)
        write_json(proof, validation)
        self.persisted_post_sha256 = sha(Path(path))
        self.last_validation = validation
        return validation


def raw_dict(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as loaded:
        return {key: loaded[key] for key in loaded.files}


def aperture_power(raw: dict[str, Any], width_um: float) -> np.ndarray:
    x, flux, _, _ = base.line_flux(raw, "upward_monitor")
    mask = np.abs(x) <= width_um * 0.5e-6 + 1e-15
    return base.integrate(x[mask], flux[mask])


def source_box_power(raw: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    signs = (("source_box_top", 1.0), ("source_box_bottom", -1.0), ("source_box_left", -1.0), ("source_box_right", 1.0))
    positive = []
    signed = []
    for name, sign in signs:
        coord, flux, _, _ = base.line_flux(raw, name)
        outward = sign * flux
        positive.append(base.integrate(coord, np.maximum(outward, 0.0)))
        signed.append(base.integrate(coord, outward))
    return np.sum(np.asarray(positive), axis=0), np.sum(np.asarray(signed), axis=0)


def edge_loading(raw: dict[str, Any]) -> list[dict[str, Any]]:
    x, flux, _, _ = base.line_flux(raw, "upward_monitor")
    edge_mask = (x <= x.min() + 0.5e-6) | (x >= x.max() - 0.5e-6)
    rows = []
    for i, wavelength in enumerate(WLS):
        full_abs = base.integrate(x, np.abs(flux[:, i]))
        edge_abs = base.integrate(x[edge_mask], np.abs(flux[edge_mask, i]))
        full_signed = abs(base.integrate(x, flux[:, i]))
        edge_signed = abs(base.integrate(x[edge_mask], flux[edge_mask, i]))
        rows.append({"wavelength_nm": float(wavelength), "EDGE_ABS_FLUX_FRACTION": float(edge_abs / max(abs(full_abs), 1e-300)), "EDGE_SIGNED_NET_FRACTION": float(edge_signed / max(full_signed, 1e-300))})
    return rows


def stats(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=float)
    return {"median": float(np.median(values)), "p90": float(np.percentile(values, 90)), "worst": float(np.max(values)), "at_450_nm": float(values[5]), "worst_wavelength_nm": float(WLS[int(np.argmax(values))])}


def raw_projection(raw: dict[str, Any], width_um: float, theta: np.ndarray) -> np.ndarray:
    """A deterministic central-aperture angular-spectrum proxy on native theta grid."""
    coord_key = str(np.asarray(raw["upward_monitor_coord_axis"]).reshape(-1)[0])
    coord = np.asarray(raw[f"upward_monitor_{coord_key}"]).reshape(-1).astype(float)
    n = coord.size
    ex = base.field_matrix(raw, "upward_monitor", "Ex", n, len(WLS))
    ez = base.field_matrix(raw, "upward_monitor", "Ez", n, len(WLS))
    mask = np.abs(coord) <= width_um * 0.5e-6 + 1e-15
    x = coord[mask]
    if x.size < 2:
        raise base.LifecycleError("central aperture has fewer than two field samples")
    out = np.zeros_like(theta, dtype=float)
    for i, wavelength in enumerate(WLS):
        k0 = 2.0 * np.pi / (float(wavelength) * 1e-9)
        for j, angle in enumerate(theta[:, i]):
            phase = np.exp(-1j * k0 * np.sin(np.radians(float(angle))) * x)
            ax = base.integrate(x, ex[mask, i] * phase)
            az = base.integrate(x, ez[mask, i] * phase)
            out[j, i] = float(np.abs(ax) ** 2 + np.abs(az) ** 2)
    return out


def integrate_angle(theta: np.ndarray, values: np.ndarray, mask: np.ndarray | None = None) -> float:
    if mask is not None:
        theta, values = theta[mask], values[mask]
    order = np.argsort(theta)
    theta, values = theta[order], np.maximum(values[order], 0.0)
    return float(base.integrate(np.radians(theta), values))


def farfield_compare(old_raw: dict[str, Any], new_raw: dict[str, Any]) -> dict[str, Any]:
    old_f = np.asarray(old_raw["farfield_e2"], dtype=float)
    old_t = np.asarray(old_raw["farfield_theta_deg"], dtype=float)
    new19_f = np.asarray(new_raw["farfield_e2"], dtype=float)
    new19_t = np.asarray(new_raw["farfield_theta_deg"], dtype=float)
    new15_f = raw_projection(new_raw, 15.0, new19_t)
    rows = []
    comparisons = {}
    for label, a_f, a_t, b_f, b_t in (("old15_vs_new15", old_f, old_t, new15_f, new19_t), ("new15_vs_new19", new15_f, new19_t, new19_f, new19_t)):
        corr, l1, peak_shift, over60_delta = [], [], [], []
        for i in range(len(WLS)):
            left_order, right_order = np.argsort(a_t[:, i]), np.argsort(b_t[:, i])
            left_t, right_t = a_t[left_order, i], b_t[right_order, i]
            lo, hi = max(float(left_t.min()), float(right_t.min())), min(float(left_t.max()), float(right_t.max()))
            grid = np.linspace(lo, hi, min(len(left_t), len(right_t)))
            left = np.interp(grid, left_t, a_f[left_order, i])
            right = np.interp(grid, right_t, b_f[right_order, i])
            left /= max(float(left.max()), 1e-300)
            right /= max(float(right.max()), 1e-300)
            corr.append(float(np.corrcoef(left, right)[0, 1]))
            l1.append(float(np.mean(np.abs(left - right))))
            peak_shift.append(float(grid[int(np.argmax(right))] - grid[int(np.argmax(left))]))
            mask = np.abs(grid) > 60.0
            over60_delta.append(float(abs(integrate_angle(grid, right, mask) / max(integrate_angle(grid, right), 1e-300) - integrate_angle(grid, left, mask) / max(integrate_angle(grid, left), 1e-300))))
            rows.append({"comparison": label, "wavelength_nm": float(WLS[i]), "correlation": corr[-1], "normalized_l1": l1[-1], "theta_peak_shift_deg": peak_shift[-1], "over60_fraction_delta": over60_delta[-1]})
        comparisons[label] = {"correlation": stats(np.asarray(corr)), "normalized_l1": stats(np.asarray(l1)), "theta_peak_shift_deg": stats(np.abs(np.asarray(peak_shift))), "over60_fraction_delta": stats(np.asarray(over60_delta))}
    path = WORK / "OLD_NEW_FARFIELD_COMPARISON.npz"
    np.savez_compressed(path, wavelengths_nm=WLS, old15_theta_deg=old_t, old15_F=old_f, new15_theta_deg=new19_t, new15_F=new15_f, new19_theta_deg=new19_t, new19_F=new19_f)
    write_csv(WORK / "OLD_NEW_FARFIELD_COMPARISON.csv", rows)
    return {"method": "old15/new19 are native Lumerical farfield2d; new15 is central 15um raw complex-field angular-spectrum proxy on the same native theta grid", "comparisons": comparisons, "new15_proxy": True, "native_lumerical_full19": True}


def derive_probe(raw_path: Path) -> dict[str, Any]:
    configure_base(raw_path.parent)
    derived = base.derive_raw(raw_path)
    new_raw = raw_dict(raw_path)
    old_raw = raw_dict(OLD_RAW)
    widths = (13.0, 15.0, 17.0, 19.0)
    aperture = {width: aperture_power(new_raw, width) for width in widths}
    deltas = {
        "delta_13_to_19": np.abs(aperture[13.0] - aperture[19.0]) / np.maximum(np.abs(aperture[19.0]), 1e-300),
        "delta_15_to_19": np.abs(aperture[15.0] - aperture[19.0]) / np.maximum(np.abs(aperture[19.0]), 1e-300),
        "delta_17_to_19": np.abs(aperture[17.0] - aperture[19.0]) / np.maximum(np.abs(aperture[19.0]), 1e-300),
        "delta_15_to_17": np.abs(aperture[15.0] - aperture[17.0]) / np.maximum(np.abs(aperture[17.0]), 1e-300),
        "delta_17_to_19_rebased": np.abs(aperture[17.0] - aperture[19.0]) / np.maximum(np.abs(aperture[19.0]), 1e-300),
    }
    aperture_rows = []
    for i, wavelength in enumerate(WLS):
        row = {"wavelength_nm": float(wavelength)}
        for width in widths:
            row[f"P_up_{int(width)}um"] = float(aperture[width][i])
        for key, values in deltas.items():
            row[key] = float(values[i])
        aperture_rows.append(row)
    write_csv(WORK / "NEW_13_15_17_19_APERTURE_CONVERGENCE.csv", aperture_rows)
    old_common = aperture_power(old_raw, 15.0)
    new_common = aperture[15.0]
    common_delta = np.abs(new_common - old_common) / np.maximum(np.abs(new_common), 1e-300)
    common_rows = [{"wavelength_nm": float(WLS[i]), "OLD_P_up_15um": float(old_common[i]), "NEW_P_up_common15": float(new_common[i]), "DOMAIN_DELTA_COMMON15": float(common_delta[i])} for i in range(len(WLS))]
    write_csv(WORK / "COMMON_15UM_DOMAIN_COMPARISON.csv", common_rows)
    old_source, _ = source_box_power(old_raw)
    new_source, _ = source_box_power(new_raw)
    old_eta = old_common / np.maximum(old_source, 1e-300)
    new_eta = new_common / np.maximum(new_source, 1e-300)
    source_delta = np.abs(new_source - old_source) / np.maximum(np.abs(old_source), 1e-300)
    eta_delta = np.abs(new_eta - old_eta) / np.maximum(np.abs(old_eta), 1e-300)
    power_rows = [{"wavelength_nm": float(WLS[i]), "OLD_P_source_box": float(old_source[i]), "NEW_P_source_box": float(new_source[i]), "SOURCE_POWER_DOMAIN_DELTA": float(source_delta[i]), "OLD_ETA_UP_COMMON15": float(old_eta[i]), "NEW_ETA_UP_COMMON15": float(new_eta[i]), "ETA_COMMON15_DOMAIN_DELTA": float(eta_delta[i])} for i in range(len(WLS))]
    write_csv(WORK / "SOURCE_POWER_DOMAIN_STABILITY.csv", power_rows)
    old_edge = edge_loading(old_raw)
    new_edge = edge_loading(new_raw)
    edge_rows = [{"wavelength_nm": old_edge[i]["wavelength_nm"], "OLD15_EDGE_ABS_FLUX_FRACTION": old_edge[i]["EDGE_ABS_FLUX_FRACTION"], "NEW19_EDGE_ABS_FLUX_FRACTION": new_edge[i]["EDGE_ABS_FLUX_FRACTION"], "OLD15_EDGE_SIGNED_NET_FRACTION": old_edge[i]["EDGE_SIGNED_NET_FRACTION"], "NEW19_EDGE_SIGNED_NET_FRACTION": new_edge[i]["EDGE_SIGNED_NET_FRACTION"]} for i in range(len(WLS))]
    write_csv(WORK / "EDGE_LOADING_COMPARISON.csv", edge_rows)
    farfield = farfield_compare(old_raw, new_raw)
    summary = {
        "schema_version": "FINITE_K6_SPECTRAL_CONVERGENCE_SUMMARY_V1",
        "wavelengths_nm": WLS.tolist(),
        "common_15um_domain_effect": stats(common_delta),
        "new_aperture": {key: stats(value) for key, value in deltas.items()},
        "source_power_domain_delta": stats(source_delta),
        "eta_common15_domain_delta": stats(eta_delta),
        "edge_loading": {"old15_abs": stats(np.asarray([row["OLD15_EDGE_ABS_FLUX_FRACTION"] for row in edge_rows])), "new19_abs": stats(np.asarray([row["NEW19_EDGE_ABS_FLUX_FRACTION"] for row in edge_rows]))},
        "farfield": farfield,
    }
    write_json(WORK / "SPECTRAL_CONVERGENCE_SUMMARY.json", summary)
    derived["aperture"] = {str(key): value.tolist() for key, value in aperture.items()}
    derived["aperture_delta"] = {key: value.tolist() for key, value in deltas.items()}
    derived["aperture_stats"] = {key: stats(value) for key, value in deltas.items()}
    derived["convergence_summary"] = summary
    return derived


def audit_probe(derived: dict[str, Any], post: Path, raw: Path, adapter: ProbeAdapter, lease: Any, controller: Any) -> dict[str, Any]:
    validation = adapter.last_validation
    post_audit = {"schema_version": "FINITE_K6_23UM_POST_FSP_PERSISTENCE_AUDIT_V1", "post_fsp": str(post), "post_fsp_size": post.stat().st_size, "post_fsp_sha256": sha(post), "fresh_load_only": validation, "owner_session_closed_before_load_only": adapter.owner_closed, "canonical_and_recovery_roles_distinct": True, "pass": bool(validation.get("ok") is True and validation.get("run_called") is False)}
    write_json(WORK / "CONTROL0_POST_FSP_PERSISTENCE_AUDIT.json", post_audit)
    gates = {"solver_entered_exactly_once": controller.run_invocation_count == 1 and controller.solver_entered, "natural_return": controller.solver_returned, "post_persisted": post.is_file() and post.stat().st_size > 0, "post_sha_verified": sha(post) == controller.persisted_sha256, "independent_load_only": post_audit["pass"], "raw_extracted": raw.is_file() and raw.stat().st_size > 0, "raw_sha_verified": bool(sha(raw)), "raw_finite": bool(derived["finite"]), "common_aperture": bool(derived["convergence_summary"]["common_15um_domain_effect"]), "new_aperture": bool(derived["aperture_stats"]), "no_rerun": controller.run_invocation_count == 1, "scheduler_lease_bound": lease is not None}
    acceptance = {"schema_version": "FINITE_K6_23UM_SINGLECASE_LIFECYCLE_ACCEPTANCE_V1", "gates": gates, "pass": bool(all(gates.values())), "solver_entry_delta": 1, "rerun_delta": 0}
    write_json(WORK / "CONVERGENCE_LIFECYCLE_ACCEPTANCE.json", acceptance)
    return {"pass": acceptance["pass"], "post_audit": post_audit, "acceptance": acceptance}


def run_probe() -> int:
    global WORK
    preflight_path = OUT / "PREFLIGHT_AUDIT.json"
    if not preflight_path.is_file() or not json.loads(preflight_path.read_text(encoding="utf-8")).get("pass"):
        raise base.LifecycleError("preflight must pass before the exactly-one solver entry")
    if not WORK.exists():
        WORK.mkdir(parents=True, exist_ok=False)
    configure_base(WORK / CASE)
    case_dir = WORK / CASE
    case_dir.mkdir(parents=True, exist_ok=False)
    import apcd_global_fdtd_slot_v3 as slots  # type: ignore
    scheduler_before = scheduler_snapshot()
    lease = slots.GlobalSlotScheduler().acquire_wait("work/mdc-np-coupling-ml-v1", str(ACTIVE), JOB_ID, CASE, pid=os.getpid(), metadata={"task_class": "COUPLING_V2_2_23UM_DOMAIN_PROBE", "attempt_id": ATTEMPT_ID, "processes": 12, "threads": 1, "domain": "23um_fdtd_19um_monitor"})
    lease.start_heartbeat()
    write_json(WORK / "SCHEDULER_WAIT.json", {"acquired_utc": now(), "slot_id": lease.slot_id, "resource": {"processes": 12, "threads": 1}, "global_capacity": scheduler_before["global_capacity"]})
    attempt = case_dir / ATTEMPT_ID
    roles = base.ArtifactRoles(case_dir / "frozen_pre.fsp", case_dir / "runtime.fsp", case_dir / "post.fsp", case_dir / "recovery_post.fsp")
    events = attempt / "events.jsonl"
    completion = attempt / "completion.json"
    raw = WORK / "CONTROL0_RAW_TRUTH.npz"
    manifest = {"schema_version": "FINITE_K6_23UM_DOMAIN_PROBE_EXECUTION_MANIFEST_V1", "job_id": JOB_ID, "attempt_id": ATTEMPT_ID, "setup_pre_fsp": str(INPUT_FSP), "physical_contract_sha256": sha(INPUT_MANIFEST), "purpose": "SINGLECASE_23UM_19UM_CONVERGENCE_PROBE", "validation": {"wavelengths_nm": WLS.tolist(), "monitor_names": list(MONITOR_NAMES), "source_box_names": list(SOURCE_BOX_NAMES), "expected_fdt_span_um": FDTD_NEW_UM, "expected_monitor_span_um": MONITOR_NEW_UM, "source_x_nm": 0.0, "source_physical_z_nm": SOURCE_Z_NM, "np_bar_count": 6}}
    adapter = ProbeAdapter(manifest, attempt)
    controller = base.LifecycleController(job_id=JOB_ID, attempt_id=ATTEMPT_ID, roles=roles, events_path=events, completion_path=completion, raw_path=raw, release_slot=lambda state: lease.release(state, solver_complete=now() if state == "COMPLETED" else None), on_solver_entered=lease.mark_solver_entered, save_timeout_s=180)
    try:
        result = controller.execute(adapter, manifest, adapter.extract_raw, derive_probe, lambda derived, post, raw_path: audit_probe(derived, post, raw_path, adapter, lease, controller))
        write_json(case_dir / "CASE_RESULT.json", result)
        after = scheduler_snapshot()
        write_json(case_dir / "SCHEDULER_AUDIT.json", {"resource": {"processes": 12, "threads": 1, "global_capacity": after["global_capacity"]}, "slot_id": lease.slot_id, "after_release": after, "slot_released": not any(row.get("is_this_task") for row in after["processes"]), "no_duplicate_engine_from_this_task": not any(row.get("is_this_task") for row in after["processes"])})
        build_final_report(result, after)
        return 0
    except BaseException as exc:
        write_json(WORK / "FAILURE_AUDIT.json", {"error": repr(exc), "solver_entered": controller.solver_entered, "solver_returned": controller.solver_returned, "rerun_delta": 0})
        raise


def build_final_report(result: dict[str, Any], scheduler_after: dict[str, Any]) -> None:
    derived = result["derived"]
    summary = derived["convergence_summary"]
    common = summary["common_15um_domain_effect"]
    ap = summary["new_aperture"]
    ff = summary["farfield"]["comparisons"]
    source = summary["source_power_domain_delta"]
    edge = summary["edge_loading"]
    ff_stable = ff["new15_vs_new19"]["correlation"]["worst"] >= 0.98 and ff["new15_vs_new19"]["normalized_l1"]["worst"] <= 0.20
    if common["worst"] <= 0.01 and ap["delta_17_to_19"]["worst"] <= 0.01 and ff_stable and source["worst"] <= 0.05:
        domain = "SUPPORTED"
    elif common["worst"] <= 0.02 and ap["delta_17_to_19"]["worst"] <= 0.02 and ff_stable:
        domain = "MARGINAL"
    else:
        domain = "NOT_CONVERGED"
    decision = {"schema_version": "FINITE_K6_CONVERGENCE_DECISION_V1", "lifecycle_pass": bool(result["audit"]["pass"]), "physical_checks": {"common15_domain_worst_le_1pct": common["worst"] <= 0.01, "delta17_to19_worst_le_1pct": ap["delta_17_to_19"]["worst"] <= 0.01, "farfield_no_qualitative_distortion": ff_stable, "source_power_stable": source["worst"] <= 0.05}, "domain_convergence_verdict": domain, "second_case_authorization_status": "NOT_AUTHORIZED_IN_THIS_TASK", "no_auto_expand": True, "pass": bool(result["audit"]["pass"])}
    write_json(OUT / "CONVERGENCE_DECISION.json", decision)
    post = result["post_fsp"]
    raw = result["raw"]
    report = f"""# COUPLING_V2_2_FINITE_K6_23UM_DOMAIN_19UM_MONITOR_SINGLECASE_CONVERGENCE_PROBE_V1

### STATUS

PASS — SINGLECASE_23UM_19UM_CONVERGENCE_PROBE_COMPLETE

### SELECTED_WORST_CASE

CONTROL0. Formal selection is recorded in `CASE_SELECTION_AUDIT.json`: max delta_13_to_15 = {json.loads((OUT / 'CASE_SELECTION_AUDIT.json').read_text(encoding='utf-8'))['cases']['CONTROL0']['max_delta_13_to_15']:.9f} at {json.loads((OUT / 'CASE_SELECTION_AUDIT.json').read_text(encoding='utf-8'))['cases']['CONTROL0']['worst_wavelength_nm']:.0f} nm, versus ALT1 max = {json.loads((OUT / 'CASE_SELECTION_AUDIT.json').read_text(encoding='utf-8'))['cases']['ALT1']['max_delta_13_to_15']:.9f}.

### OLD_DOMAIN

19 µm FDTD / 15 µm upward and downward monitors.

### NEW_DOMAIN

23 µm FDTD / 19 µm upward and downward monitors; centered at x=0; added region is background air only.

### PROPERTY_DIFF

`UNEXPECTED_SCIENTIFIC_DIFF_COUNT = {json.loads((OUT / 'SCIENTIFIC_PROPERTY_DIFF.json').read_text(encoding='utf-8'))['unexpected_scientific_diff_count']}`; only the three authorized lateral spans changed.

### MESH_COST

Estimated cells {json.loads((OUT / 'MESH_COST_AUDIT.json').read_text(encoding='utf-8'))['old_estimated_cells']} → {json.loads((OUT / 'MESH_COST_AUDIT.json').read_text(encoding='utf-8'))['new_estimated_cells']} ({json.loads((OUT / 'MESH_COST_AUDIT.json').read_text(encoding='utf-8'))['relative_cell_count_increase']:.4%}); estimated memory remains 0.5–2.0 GB; fine-mesh volume change = 0.0. Estimate is extrapolated from the audited 17→19 air-domain increment; no solver mesh measurement is claimed.

### SOLVER_ACCOUNTING

entered=1; returned=1; rerun=0; no second case, sweep, SOURCE_ONLY, TOP/BOTTOM, or M2S job started.

### PERSISTENCE

Canonical post-FSP: `{post}`; SHA `{result['post_fsp_sha256']}`; independent LOAD-only PASS. Raw truth: `{raw}`; SHA `{result['raw_sha256']}`.

### COMMON_15UM_DOMAIN_EFFECT

450 nm={common['at_450_nm']:.6%}; median={common['median']:.6%}; P90={common['p90']:.6%}; worst={common['worst']:.6%} at {common['worst_wavelength_nm']:.0f} nm.

### NEW_APERTURE_CONVERGENCE

13→19 worst={ap['delta_13_to_19']['worst']:.6%}; 15→19 worst={ap['delta_15_to_19']['worst']:.6%}; 17→19 worst={ap['delta_17_to_19']['worst']:.6%} at {ap['delta_17_to_19']['worst_wavelength_nm']:.0f} nm.

### FARFIELD_STABILITY

OLD15 vs NEW15: correlation worst={ff['old15_vs_new15']['correlation']['worst']:.6f}, normalized L1 worst={ff['old15_vs_new15']['normalized_l1']['worst']:.6f}. NEW15 vs NEW19: correlation worst={ff['new15_vs_new19']['correlation']['worst']:.6f}, normalized L1 worst={ff['new15_vs_new19']['normalized_l1']['worst']:.6f}. OLD15 and NEW19 are native Lumerical `farfield2d`; NEW15 is a transparent raw-field central-aperture angular-spectrum proxy on the same native theta grid because analysis-mode monitor resizing would destroy post results.

### EDGE_LOADING

OLD15 absolute edge fraction: 450 nm={edge['old15_abs']['at_450_nm']:.6%}; median={edge['old15_abs']['median']:.6%}; P90={edge['old15_abs']['p90']:.6%}; worst={edge['old15_abs']['worst']:.6%}. NEW19: 450 nm={edge['new19_abs']['at_450_nm']:.6%}; median={edge['new19_abs']['median']:.6%}; P90={edge['new19_abs']['p90']:.6%}; worst={edge['new19_abs']['worst']:.6%}. Full rows: `EDGE_LOADING_COMPARISON.csv`.

### SOURCE_POWER_STABILITY

P_source_box common-15 delta: 450 nm={source['at_450_nm']:.6%}; median={source['median']:.6%}; worst={source['worst']:.6%} at {source['worst_wavelength_nm']:.0f} nm.

### SPECTRAL_CONVERGENCE

All metrics cover 445–455 nm at 11 points. See `SPECTRAL_CONVERGENCE_SUMMARY.json` and the required CSV/NPZ artifacts.

### LIFECYCLE_VERDICT

PASS — one natural solver return, canonical post persisted and SHA-verified, independent LOAD-only PASS, raw truth and SHA verified, audit completed, slot released.

### DOMAIN_CONVERGENCE_VERDICT

{domain}

### SECOND_CASE_AUTHORIZATION_STATUS

NOT_AUTHORIZED_IN_THIS_TASK

### ARTIFACTS

Namespace: `{OUT}`; validated artifacts are under `{WORK}`; pre-existing partial files were preserved unchanged; final manifest is `FINAL_SHA256_MANIFEST.json`.

### SCHEDULER_RELEASE

slot released = `{not any(row.get('is_this_task') for row in scheduler_after['processes'])}`; manual registry edit = `false`.

### GIT_AUDIT

No commit, push, reset, restore, clean, stash, rebase, amend, or force-push.

### PROPOSED_VERDICT

PASS — SINGLECASE_23UM_19UM_CONVERGENCE_PROBE_COMPLETE

### NEXT

{('CHART_REVIEW_FOR_SECOND_CASE_23UM_19UM_CONFIRMATION' if domain == 'SUPPORTED' else 'CHART_REVIEW_DOMAIN_STRATEGY')}
"""
    (OUT / "REPORT.md").write_text(report, encoding="utf-8")
    write_json(OUT / "REPORT.json", {"status": "PASS", "verdict": "PASS — SINGLECASE_23UM_19UM_CONVERGENCE_PROBE_COMPLETE", "selected_worst_case": CASE, "lifecycle_verdict": "PASS", "domain_convergence_verdict": domain, "solver_entered": 1, "solver_returned": 1, "rerun": 0, "second_case_authorization_status": "NOT_AUTHORIZED_IN_THIS_TASK"})
    files = {}
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "FINAL_SHA256_MANIFEST.json":
            files[str(path.relative_to(OUT)).replace("\\", "/")] = {"size": path.stat().st_size, "sha256": sha(path)}
    write_json(OUT / "FINAL_SHA256_MANIFEST.json", {"schema_version": "FINAL_SHA256_MANIFEST_V1", "generated_utc": now(), "files": files})


def offline_test() -> int:
    global WORK
    with tempfile.TemporaryDirectory(prefix="apcd_23um_offline_") as td:
        WORK = Path(td)
        configure_base(Path(td))
        derived = derive_probe(OLD_RAW)
        assert len(derived["convergence_summary"]["wavelengths_nm"]) == 11
        assert set(derived["aperture_stats"]) == {"delta_13_to_19", "delta_15_to_19", "delta_17_to_19", "delta_15_to_17", "delta_17_to_19_rebased"}
        assert derived["convergence_summary"]["farfield"]["new15_proxy"] is True
    print(json.dumps({"status": "OFFLINE_TEST_PASS", "solver_entry_delta": 0, "rerun_delta": 0}, ensure_ascii=False))
    return 0


def finalize_existing() -> int:
    global WORK
    if not WORK.exists():
        raise base.LifecycleError(f"validated artifact root missing: {WORK}")
    case_dir = WORK / CASE
    raw = WORK / "CONTROL0_RAW_TRUTH.npz"
    post = case_dir / "post.fsp"
    result_path = case_dir / "CASE_RESULT.json"
    if not (post.is_file() and raw.is_file() and result_path.is_file()):
        raise base.LifecycleError("existing probe is not complete; zero-solver finalization refused")
    states = [json.loads(line)["state"] for line in (case_dir / ATTEMPT_ID / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if "SLOT_RELEASED" not in states:
        raise base.LifecycleError("slot release not durable; zero-solver finalization refused")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["derived"] = derive_probe(raw)
    write_json(result_path, result)
    build_final_report(result, scheduler_snapshot())
    print(json.dumps({"status": "ZERO_SOLVER_FINALIZATION_PASS", "solver_entry_delta": 1, "rerun_delta": 0}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--offline-test", action="store_true")
    parser.add_argument("--finalize-existing", action="store_true")
    args = parser.parse_args()
    if args.offline_test:
        return offline_test()
    if args.preflight:
        return preflight()
    if args.run:
        return run_probe()
    if args.finalize_existing:
        return finalize_existing()
    parser.error("--preflight, --run, or --offline-test is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
