from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/stage_h1d1_detour_feasibility"
RUNTIME = ROOT / "outputs/lp_detour_h1d1"
CASE_ROOT = RUNTIME / "cases"
H1D0_PATH = ROOT / "reports/stage_h1d0_phase_mechanism_decision/h1d0_detour_geometry_feasibility.json"
STRICT_BANK_PATH = ROOT / "reports/stage_h1c1b1_sixbin_closure/h1c1b1_strict_bank_v1.json"
MANIFEST_PATH = REPORT / "h1d1_k6_detour_manifest.json"
ACCOUNTING_PATH = REPORT / "h1d1_solver_accounting.json"
LEGALITY_PATH = REPORT / "h1d1_geometry_legality.json"
GRID = [450.0 + 0.5 * i for i in range(9)]
H_GLOBAL_NM = 550.0
PY_NM = 432.0
MATERIAL = "APCD_TIO2_NATIVE_M1"
TARGET_BRANCH = "work/lp-global-h-manifold-v1"
SLOT_REGISTRY = Path(r"D:\project\apcd_global_fdtd_slot_registry_v1.json")
POLARIZATIONS = ("x", "y")
PARENT_UID = "H1C1B_V2_009"
PARENT_HASH = "955c293def3063f64969c25743e14ce122e7ed0364b12be0b9f75cdb350cb800"
MAX_SUBRUNS = 2
PROCESSES = 4
THREADS = 1
BUILDER_VERSION = "h1d1_pure_detour_k6_native_material_builder_v1"
EXTRACTION_VERSION = "h1d1_gratingvector_frequency_index_v1"
ALPHA_PSI_DEG = 112.5
ALPHA_CHI_DEG = 22.5


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode()


def sha256_obj(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"])
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def current_branch() -> str:
    return subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()


def current_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def parent_record() -> dict[str, Any]:
    bank = read_json(STRICT_BANK_PATH)
    row = next(row for row in bank["geometries"] if row["geometry_uid"] == PARENT_UID)
    if row["exact_hash"] != PARENT_HASH:
        raise RuntimeError("HARD_GATE_PARENT_HASH_MISMATCH")
    return row


def build_alpha_beta_basis(psi_deg: float, chi_deg: float) -> dict[str, tuple[complex, complex]]:
    psi = math.radians(psi_deg)
    chi = math.radians(chi_deg)
    alpha = (math.cos(chi) * math.cos(psi) - 1j * math.sin(chi) * math.sin(psi),
             math.cos(chi) * math.sin(psi) + 1j * math.sin(chi) * math.cos(psi))
    beta = (-alpha[1].conjugate(), alpha[0].conjugate())
    return {"alpha": alpha, "beta": beta, "alpha_star": (alpha[0].conjugate(), alpha[1].conjugate()), "beta_star": (beta[0].conjugate(), beta[1].conjugate())}


def transform_xy(jones: list[list[complex]]) -> list[list[complex]]:
    basis = build_alpha_beta_basis(ALPHA_PSI_DEG, ALPHA_CHI_DEG)
    transformed = []
    for out_vec in (basis["alpha_star"], basis["beta_star"]):
        row = []
        for in_vec in (basis["alpha"], basis["beta"]):
            v = (jones[0][0] * in_vec[0] + jones[0][1] * in_vec[1], jones[1][0] * in_vec[0] + jones[1][1] * in_vec[1])
            row.append(out_vec[0].conjugate() * v[0] + out_vec[1].conjugate() * v[1])
        transformed.append(row)
    return transformed


def manifest_payload() -> dict[str, Any]:
    h1d0 = read_json(H1D0_PATH)
    parent = parent_record()
    pure = h1d0["pure_detour"]
    assignments = pure["assignments"]
    positions = pure["audit"]["absolute_positions_nm"]
    p_nm = float(h1d0["dimer_pitch_nm"])
    P_nm = float(h1d0["supercell_period_nm"])
    coords = parent["coordinates_5d"]
    psi = float(coords["Psi_deg"])
    cx = float(coords["D_nm"]) * math.cos(math.radians(psi)) / 2.0
    cy = float(coords["D_nm"]) * math.sin(math.radians(psi)) / 2.0
    if abs(cx - 95.5) > 1e-9 or abs(cy - 4.0) > 1e-9:
        raise RuntimeError("HARD_GATE_PARENT_CENTER_CONVENTION_MISMATCH")
    if abs(P_nm - 6.0 * p_nm) > 1e-9:
        raise RuntimeError("HARD_GATE_AUTHORITATIVE_PERIOD_INCONSISTENCY")
    copies = []
    for index, (assignment, x_nm) in enumerate(zip(assignments, positions)):
        copies.append({
            "copy_index": index,
            "intended_phase_deg": float(assignment["target_phase_deg"]),
            "detour_phase_deg": float(assignment["detour_phase_deg"]),
            "relative_offset_nm": float(assignment["relative_offset_nm"]),
            "x_nm": float(x_nm),
            "y_nm": 0.0,
            "parent_geometry_uid": PARENT_UID,
            "parent_exact_hash": PARENT_HASH,
            "geometry_hash": PARENT_HASH,
        })
    contract = {
        "stage": "H1D-1",
        "layout_uid": "LP_H1D1_PURE_DETOUR_K6_V2_009",
        "parent_geometry_uid": PARENT_UID,
        "parent_exact_hash": PARENT_HASH,
        "H_global_nm": H_GLOBAL_NM,
        "period_nm": {"local_x_nm": p_nm, "supercell_x_nm": P_nm, "y_nm": PY_NM},
        "material": MATERIAL,
        "target_order": {"m": 1, "n": 1, "direction": "+x", "translation_phase": "exp(-i*G_m*Delta_x)", "G_m_rad_per_nm": 2.0 * math.pi / P_nm},
        "wavelength_grid_nm": GRID,
        "builder_version": BUILDER_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "processes": PROCESSES,
        "threads": THREADS,
        "formal_subruns": [{"polarization": "x", "solver_runs_for_spectrum": 1}, {"polarization": "y", "solver_runs_for_spectrum": 1}],
        "no_control_layout": True,
        "ml_admitted": False,
    }
    payload = {
        "schema": "H1D1_K6_PURE_DETOUR_MANIFEST_V1",
        "status": "FROZEN_READY",
        "branch": current_branch(),
        "worktree": str(ROOT),
        "layout_uid": contract["layout_uid"],
        "parent": {"geometry_uid": PARENT_UID, "exact_hash": PARENT_HASH, "coordinates_5d": coords, "local_center_nm": {"x": cx, "y": cy}, "source_artifact": str(STRICT_BANK_PATH)},
        "copies": copies,
        "position_sorted_phase_order": [row["intended_phase_deg"] for row in sorted(copies, key=lambda row: row["x_nm"])],
        "p_nm": p_nm,
        "P_supercell_nm": P_nm,
        "m_target": 1,
        "detour_sign_convention": "exp(-i*G_m*Delta_x)",
        "H_global_nm": H_GLOBAL_NM,
        "wavelength_grid_nm": GRID,
        "legality_reference": pure["audit"],
        "contract": contract,
        "contract_sha256": sha256_obj(contract),
        "freeze_sha256": "",
    }
    payload["freeze_sha256"] = sha256_obj({key: value for key, value in payload.items() if key != "freeze_sha256"})
    return payload


def ensure_manifest() -> dict[str, Any]:
    payload = manifest_payload()
    if MANIFEST_PATH.exists():
        existing = read_json(MANIFEST_PATH)
        if existing.get("freeze_sha256") != payload["freeze_sha256"]:
            raise RuntimeError("HARD_GATE_FROZEN_MANIFEST_DRIFT")
        return existing
    write_json(MANIFEST_PATH, payload)
    return payload


def rotate_corners(cx: float, cy: float, length: float, width: float, angle_deg: float) -> list[tuple[float, float]]:
    angle = math.radians(angle_deg)
    ux, uy = math.cos(angle), math.sin(angle)
    vx, vy = -uy, ux
    return [(cx + sx * length * ux / 2 + sy * width * vx / 2, cy + sx * length * uy / 2 + sy * width * vy / 2) for sx, sy in ((-1, -1), (-1, 1), (1, 1), (1, -1))]


def segment_distance(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> float:
    def cross(u: tuple[float, float], v: tuple[float, float]) -> float:
        return u[0] * v[1] - u[1] * v[0]
    def orient(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return cross((q[0] - p[0], q[1] - p[1]), (r[0] - p[0], r[1] - p[1]))
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if ((o1 > 0 > o2) or (o2 > 0 > o1)) and ((o3 > 0 > o4) or (o4 > 0 > o3)):
        return 0.0
    def point_segment(p: tuple[float, float], x: tuple[float, float], y: tuple[float, float]) -> float:
        vx, vy = y[0] - x[0], y[1] - x[1]
        den = vx * vx + vy * vy
        t = max(0.0, min(1.0, ((p[0] - x[0]) * vx + (p[1] - x[1]) * vy) / den))
        return math.hypot(p[0] - x[0] - t * vx, p[1] - x[1] - t * vy)
    return min(point_segment(a, c, d), point_segment(b, c, d), point_segment(c, a, b), point_segment(d, a, b))


def polygon_distance(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    return min(segment_distance(a[i], a[(i + 1) % 4], b[j], b[(j + 1) % 4]) for i in range(4) for j in range(4))


def legality(manifest: dict[str, Any]) -> dict[str, Any]:
    parent = manifest["parent"]["coordinates_5d"]
    cx, cy = manifest["parent"]["local_center_nm"]["x"], manifest["parent"]["local_center_nm"]["y"]
    shapes: list[tuple[int, int, list[tuple[float, float]]]] = []
    for copy in manifest["copies"]:
        x, y = copy["x_nm"], copy["y_nm"]
        shapes.append((copy["copy_index"], 1, rotate_corners(x - cx, y - cy, float(parent["J1_side_nm"]), float(parent["J1_side_nm"]), 0.0)))
        shapes.append((copy["copy_index"], 2, rotate_corners(x + cx, y + cy, float(parent["J2_length_nm"]), float(parent["J2_width_nm"]), float(parent["Psi_deg"]))))
    min_gap = float("inf")
    min_pair = None
    boundary = float("inf")
    for copy_index, pillar, poly in shapes:
        for x, y in poly:
            boundary = min(boundary, x, manifest["P_supercell_nm"] - x, y + manifest["period_nm_y"] if "period_nm_y" in manifest else y + PY_NM, PY_NM - y)
    for i, (ci, pi, ai) in enumerate(shapes):
        for j, (cj, pj, bj) in enumerate(shapes):
            if j <= i:
                continue
            for nx in (-1, 0, 1):
                for ny in (-1, 0, 1):
                    if nx == 0 and ny == 0:
                        shifted = bj
                    else:
                        shifted = [(x + nx * manifest["P_supercell_nm"], y + ny * PY_NM) for x, y in bj]
                    gap = polygon_distance(ai, shifted)
                    if gap < min_gap:
                        min_gap, min_pair = gap, {"a": [ci, pi], "b": [cj, pj], "translation": [nx, ny]}
    ref = manifest["legality_reference"]
    return {
        "schema": "H1D1_GEOMETRY_LEGALITY_V1",
        "layout_uid": manifest["layout_uid"],
        "no_overlap": min_gap > 0.0,
        "minimum_clearance_computed_nm": min_gap,
        "minimum_clearance_reference_nm": ref["min_clearance_nm"],
        "minimum_clearance_required_nm": 20.0,
        "boundary_margin_computed_nm": boundary,
        "boundary_margin_reference_nm": ref["supercell_boundary_margin_nm"],
        "parent_local_center_nm": {"x": cx, "y": cy},
        "period_nm": {"x": manifest["P_supercell_nm"], "y": PY_NM},
        "H_global_nm": H_GLOBAL_NM,
        "material": MATERIAL,
        "integer_lateral_dimensions": all(float(parent[key]).is_integer() for key in ("J1_side_nm", "J2_length_nm", "J2_width_nm")),
        "half_grid_local_center": all(abs(2 * float(value) - round(2 * float(value))) < 1e-9 for value in (cx, cy)),
        "minimum_pair": min_pair,
        "pass": bool(min_gap >= 20.0 and boundary >= 0.0),
    }


def live_accounting() -> dict[str, Any]:
    slot = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1d1_slot_readonly")
    live = slot.live_job_snapshot()
    live["scheduler_invariant"] = {
        "process_count_is_not_job_count": True,
        "four_mpi_engines_equal_one_fdtd_case": True,
        "rcwa_excluded_from_fdtd_accounting": True,
        "validated_production_fdtd_concurrency": 2,
        "max_active_fdtd_per_branch": 1,
        "processes_per_fdtd_job": PROCESSES,
        "threads_per_fdtd_job": THREADS,
    }
    return live


def load_runtime():
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "scripts"))
    from metasurface.config import load_runtime_config
    from metasurface.lumapi_runner import import_lumapi
    config = load_runtime_config(str(ROOT / "configs/runtime.yaml"))
    return type("Runtime", (), {"lumapi": import_lumapi(config), "hide_gui": getattr(config, "hide_gui", True)})()


def initial_accounting(manifest: dict[str, Any]) -> dict[str, Any]:
    if ACCOUNTING_PATH.exists():
        return read_json(ACCOUNTING_PATH)
    payload = {
        "schema": "H1D1_SOLVER_ACCOUNTING_V1",
        "manifest_freeze_sha256": manifest["freeze_sha256"],
        "solver_budget_planned": MAX_SUBRUNS,
        "solver_subruns_entered": 0,
        "solver_subruns_accepted": 0,
        "max_global_fdtd_concurrency": 2,
        "max_active_fdtd_per_branch": 1,
        "processes_per_job": PROCESSES,
        "threads_per_job": THREADS,
        "cases": {pol: {"planned": True, "solver_entered": False, "status": "PLANNED"} for pol in POLARIZATIONS},
        "solver_entries": [],
        "status": "PLANNED",
    }
    write_json(ACCOUNTING_PATH, payload)
    return payload


def update_case_accounting(pol: str, **changes: Any) -> dict[str, Any]:
    accounting = read_json(ACCOUNTING_PATH)
    solver_entry = changes.pop("solver_entry", None)
    accounting["cases"].setdefault(pol, {}).update(changes)
    if solver_entry is not None and not any(row.get("case_id") == solver_entry.get("case_id") for row in accounting["solver_entries"]):
        accounting["solver_entries"].append(solver_entry)
    accounting["solver_subruns_entered"] = sum(bool(row.get("solver_entered")) for row in accounting["cases"].values())
    accounting["solver_subruns_accepted"] = sum(row.get("status") == "ACCEPTED" for row in accounting["cases"].values())
    accounting["status"] = "COMPLETE" if accounting["solver_subruns_accepted"] == MAX_SUBRUNS else "RUNNING" if accounting["solver_subruns_entered"] else "PLANNED"
    write_json(ACCOUNTING_PATH, accounting)
    return accounting


def build(fdtd: Any, manifest: dict[str, Any], pol: str) -> dict[str, Any]:
    from metasurface.lumerical_native_materials import ensure_apcd_native_materials, get_lumerical_material_name
    nm = 1e-9
    px, py, h = manifest["P_supercell_nm"] * nm, PY_NM * nm, H_GLOBAL_NM * nm
    fdtd.switchtolayout()
    fdtd.deleteall()
    ensure_apcd_native_materials(fdtd)
    material = get_lumerical_material_name(MATERIAL)
    fdtd.addfdtd()
    for key, value in (("dimension", "3D"), ("x", px / 2), ("y", py / 2), ("x span", px), ("y span", py), ("z min", -500 * nm), ("z max", 1200 * nm), ("x min bc", "Periodic"), ("x max bc", "Periodic"), ("y min bc", "Periodic"), ("y max bc", "Periodic"), ("z min bc", "PML"), ("z max bc", "PML"), ("mesh accuracy", 2), ("simulation time", 1000e-15), ("background material", "<Object defined dielectric>"), ("index", 1.0)):
        fdtd.set(key, value)
    fdtd.setglobalmonitor("frequency points", len(GRID))
    fdtd.setglobalmonitor("use wavelength spacing", True)
    fdtd.setglobalmonitor("use source limits", True)
    parent = manifest["parent"]["coordinates_5d"]
    cx, cy = manifest["parent"]["local_center_nm"]["x"] * nm, manifest["parent"]["local_center_nm"]["y"] * nm
    for copy in manifest["copies"]:
        x0, y0 = copy["x_nm"] * nm, copy["y_nm"] * nm
        for name, x, y, xspan, yspan, rotation in ((f"k6_{copy['copy_index']}_pillar_1", x0 - cx, y0 - cy, parent["J1_side_nm"] * nm, parent["J1_side_nm"] * nm, 0.0), (f"k6_{copy['copy_index']}_pillar_2", x0 + cx, y0 + cy, parent["J2_length_nm"] * nm, parent["J2_width_nm"] * nm, parent["Psi_deg"])):
            fdtd.addrect(); fdtd.set("name", name); fdtd.set("x", x); fdtd.set("y", y); fdtd.set("x span", xspan); fdtd.set("y span", yspan); fdtd.set("z min", 0.0); fdtd.set("z max", h); fdtd.set("first axis", "z"); fdtd.set("rotation 1", rotation); fdtd.set("material", material)
    fdtd.addplane(); fdtd.set("name", "source"); fdtd.set("injection axis", "z"); fdtd.set("direction", "Forward"); fdtd.set("x", px / 2); fdtd.set("y", py / 2); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", -250 * nm); fdtd.set("wavelength start", GRID[0] * nm); fdtd.set("wavelength stop", GRID[-1] * nm); fdtd.set("polarization angle", 0 if pol == "x" else 90)
    fdtd.addpower(); fdtd.set("name", "T"); fdtd.set("monitor type", "2D Z-normal"); fdtd.set("x", px / 2); fdtd.set("y", py / 2); fdtd.set("x span", px); fdtd.set("y span", py); fdtd.set("z", 1000 * nm); fdtd.set("override global monitor settings", True); fdtd.set("use wavelength spacing", True); fdtd.set("frequency points", len(GRID)); fdtd.set("use source limits", True)
    return {"material_name": material, "polarization": pol, "wavelength_grid_nm": GRID, "supercell_nm": [manifest["P_supercell_nm"], PY_NM], "monitor_z_nm": 1000.0, "pillar_count": 12, "H_global_nm": H_GLOBAL_NM}


def safe_value(fdtd: Any, name: str, prop: str) -> Any:
    try:
        return fdtd.getnamed(name, prop)
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def gate(fdtd: Any, manifest: dict[str, Any], pol: str) -> dict[str, Any]:
    from metasurface.lumerical_native_materials import get_lumerical_material_name
    material = get_lumerical_material_name(MATERIAL)
    checks = {"source_start_nm": float(safe_value(fdtd, "source", "wavelength start")) * 1e9, "source_stop_nm": float(safe_value(fdtd, "source", "wavelength stop")) * 1e9, "monitor_z_nm": float(safe_value(fdtd, "T", "z")) * 1e9, "frequency_points": float(safe_value(fdtd, "T", "frequency points")), "source_material_contract": material}
    expected = {"source_start_nm": GRID[0], "source_stop_nm": GRID[-1], "monitor_z_nm": 1000.0, "frequency_points": 9.0, "source_material_contract": material}
    passed = all(abs(checks[key] - value) < 1e-7 if isinstance(value, float) else checks[key] == value for key, value in expected.items()) and pol in POLARIZATIONS
    return {"pass": bool(passed), "checks": checks, "expected": expected, "polarization": pol, "one_broadband_run_returns_all_9_points": True}


def _complex(value: Any) -> complex:
    return complex(value)


def _gv_at(gv: Any, ni: int, mi: int) -> tuple[complex, complex, complex]:
    import numpy as np
    a = np.asarray(gv)
    while a.ndim > 3 and a.shape[2] == 1:
        a = np.squeeze(a, axis=2)
    while a.ndim > 3 and a.shape[0] == 1:
        a = np.squeeze(a, axis=0)
    value = a[ni, mi] if a.ndim >= 3 else a[ni]
    return (_complex(value[0]), _complex(value[1]), _complex(value[2]))


def extract_orders(fdtd: Any, pol: str) -> list[dict[str, Any]]:
    import numpy as np
    transmission = np.real(np.asarray(fdtd.transmission("T")).reshape(-1))
    if len(transmission) != len(GRID):
        raise RuntimeError(f"BROADBAND_TRANSMISSION_GRID_MISMATCH:{len(transmission)}")
    rows: list[dict[str, Any]] = []
    for frequency_index, wavelength in enumerate(GRID, start=1):
        n = np.asarray(fdtd.gratingn("T", frequency_index)).reshape(-1)
        m = np.asarray(fdtd.gratingm("T", frequency_index)).reshape(-1)
        ux = np.asarray(fdtd.gratingu1("T", frequency_index)).reshape(-1)
        uy = np.asarray(fdtd.gratingu2("T", frequency_index)).reshape(-1)
        g = np.asarray(fdtd.grating("T", frequency_index))
        gv = fdtd.gratingvector("T", frequency_index)
        order_rows = []
        for ni, n_value in enumerate(n):
            for mi, m_value in enumerate(m):
                fraction = float(np.real(g[ni, mi]))
                vector = _gv_at(gv, ni, mi)
                source_amp = math.sqrt(max(float(transmission[frequency_index - 1]), 0.0))
                vector_source = tuple(source_amp * value for value in vector)
                ux_value = float(ux[ni]) if ni < len(ux) else None
                uy_value = float(uy[mi]) if mi < len(uy) else None
                theta_value = None if ux_value is None or uy_value is None else math.degrees(math.asin(min(1.0, math.hypot(ux_value, uy_value))))
                order_rows.append({"wavelength_nm": wavelength, "polarization": pol, "frequency_index": frequency_index, "order_n": int(round(float(n_value))), "order_m": int(round(float(m_value))), "ux": ux_value, "uy": uy_value, "theta_deg": theta_value, "total_transmission": float(transmission[frequency_index - 1]), "order_fraction_transmitted": fraction, "order_efficiency_source_norm": fraction * float(transmission[frequency_index - 1]), "Ex_real": vector_source[0].real, "Ex_imag": vector_source[0].imag, "Ey_real": vector_source[1].real, "Ey_imag": vector_source[1].imag, "Ez_real": vector_source[2].real, "Ez_imag": vector_source[2].imag, "complex_source_normalized": True})
        rows.extend(order_rows)
    return rows


def case_identity(manifest: dict[str, Any], pol: str) -> dict[str, Any]:
    return {"case_uid": f"H1D1_K6_PURE_DETOUR_{pol.upper()}", "layout_uid": manifest["layout_uid"], "polarization": pol, "manifest_freeze_sha256": manifest["freeze_sha256"], "solver_runs_for_spectrum": 1, "wavelength_grid_nm": GRID}


def run_case(manifest: dict[str, Any], pol: str, scheduler: Any, runtime: Any) -> dict[str, Any]:
    identity = case_identity(manifest, pol)
    case_dir = CASE_ROOT / identity["case_uid"]
    case_dir.mkdir(parents=True, exist_ok=True)
    provenance = case_dir / "attempt_provenance.json"
    checkpoint = case_dir / "checkpoint.json"
    if checkpoint.exists():
        saved = read_json(checkpoint)
        if saved.get("case_identity_sha256") == sha256_obj(identity) and saved.get("status") == "ACCEPTED":
            return saved
    if provenance.exists() and read_json(provenance).get("solver_entered") is True:
        result = {"status": "QUARANTINED_ENTERED_NO_REPLAY", "case_uid": identity["case_uid"], "solver_entered": True}
        update_case_accounting(pol, solver_entered=True, status=result["status"], quarantined=True)
        return result
    attempt_id = f"{identity['case_uid']}_attempt_001"
    record: dict[str, Any] = {"schema": "H1D1_ATTEMPT_PROVENANCE_V1", "case_id": identity["case_uid"], "attempt_id": attempt_id, "case_identity": identity, "case_identity_sha256": sha256_obj(identity), "physical_contract_sha256": manifest["contract_sha256"], "solver_entered": False, "entered_solver": False, "processes": PROCESSES, "threads": THREADS, "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "wavelength_grid_nm": GRID, "solver_runs_for_spectrum": 1}
    write_json(provenance, record)
    f = None
    lease = None
    try:
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui)
        setup = build(f, manifest, pol)
        pre_fsp = case_dir / f"{attempt_id}_pre.fsp"
        f.save(str(pre_fsp)); record.update({"setup": setup, "pre_fsp_path": str(pre_fsp), "pre_fsp_sha256": sha256_file(pre_fsp), "status": "PREPARED"}); f.close(); f = None
        write_json(provenance, record)
        lease = scheduler.acquire_wait(branch=TARGET_BRANCH, worktree=str(ROOT), task_id="H1D1_PURE_DETOUR_K6", case_uid=identity["case_uid"], pid=os.getpid(), metadata={"task_class": "H1D1_FORMAL_BROADBAND_FDTD", "attempt_id": attempt_id, "polarization": pol, "H_global_nm": H_GLOBAL_NM}, timeout_s=21600.0, poll_s=15.0)
        record.update({"slot_acquired": True, "slot_id": lease.slot_id, "admission_snapshot": lease.record.get("admission_snapshot"), "status": "SLOT_ACQUIRED"}); lease.start_heartbeat(); write_json(provenance, record)
        f = runtime.lumapi.FDTD(hide=runtime.hide_gui); f.load(str(pre_fsp))
        configuration_gate = gate(f, manifest, pol); record.update({"configuration_gate": configuration_gate, "status": "PREFLIGHT_GATED"}); write_json(provenance, record)
        if not configuration_gate["pass"]:
            lease.release("QUARANTINED_PREFLIGHT_GATE"); lease = None; record.update({"status": "QUARANTINED_PREFLIGHT_GATE", "quarantined": True}); update_case_accounting(pol, status=record["status"], quarantined=True); return record
        entered_utc = dt.datetime.now(dt.timezone.utc).isoformat()
        lease.mark_solver_entered(entered_utc)
        entry = {"case_id": identity["case_uid"], "attempt_id": attempt_id, "solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "pre_fsp_sha256": record["pre_fsp_sha256"], "physical_contract_sha256": manifest["contract_sha256"], "case_identity_sha256": sha256_obj(identity), "slot_id": lease.slot_id, "processes": PROCESSES, "threads": THREADS, "polarization": pol}
        record.update({"solver_entered": True, "entered_solver": True, "entered_utc": entered_utc, "status": "ENTERED"}); write_json(provenance, record); update_case_accounting(pol, solver_entered=True, status="ENTERED", entered_utc=entered_utc, attempt_id=attempt_id, slot_id=lease.slot_id, solver_entry=entry)
        f.run()
        complete = dt.datetime.now(dt.timezone.utc).isoformat(); record["solver_complete"] = complete
        run_fsp = case_dir / f"{attempt_id}_run.fsp"
        try:
            f.save(str(run_fsp)); record.update({"run_fsp_path": str(run_fsp), "run_fsp_sha256": sha256_file(run_fsp)})
        except Exception as exc:
            record["run_fsp_save_error"] = f"{type(exc).__name__}: {exc}"
        lease.release("SOLVER_COMPLETED", complete); lease = None; record["slot_release_time"] = dt.datetime.now(dt.timezone.utc).isoformat()
        rows = extract_orders(f, pol)
        result = {"schema": "H1D1_CASE_CHECKPOINT_V1", "status": "ACCEPTED", "case_uid": identity["case_uid"], "case_identity": identity, "case_identity_sha256": sha256_obj(identity), "polarization": pol, "solver_entered": True, "solver_replay": False, "setup": setup, "configuration_gate": configuration_gate, "rows": rows, "provenance_path": str(provenance), "attempt_id": attempt_id}
        write_json(checkpoint, result); record.update({"status": "ACCEPTED", "checkpoint_path": str(checkpoint), "checkpoint_sha256": sha256_file(checkpoint)}); update_case_accounting(pol, status="ACCEPTED", accepted=True, checkpoint_path=str(checkpoint)); return result
    except Exception as exc:
        record.update({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc(), "retained_data_status": "entered_evidence_preserved_no_replay" if record.get("solver_entered") else "pre_entry_failure_evidence_preserved"}); update_case_accounting(pol, status="FAILED", quarantined=bool(record.get("solver_entered"))); return record
    finally:
        if lease is not None:
            try: lease.release("FAILED_ENTERED" if record.get("solver_entered") else "FAILED_PRE_ENTRY")
            except Exception: pass
        if f is not None:
            try: f.close()
            except Exception: pass
        write_json(provenance, record)


def order_rows_by_case(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    results = {}
    for pol in POLARIZATIONS:
        checkpoint = CASE_ROOT / case_identity(manifest, pol)["case_uid"] / "checkpoint.json"
        if checkpoint.exists():
            data = read_json(checkpoint)
            if data.get("status") == "ACCEPTED": results[pol] = data["rows"]
    return results


def postprocess(manifest: dict[str, Any]) -> dict[str, Any]:
    result = order_rows_by_case(manifest)
    for pol in POLARIZATIONS:
        rows = result.get(pol, [])
        write_csv(REPORT / f"h1d1_{pol}pol_order_spectrum.csv", rows)
    contrast = []
    for wavelength in GRID:
        xrows = [r for r in result.get("x", []) if r["wavelength_nm"] == wavelength]
        yrows = [r for r in result.get("y", []) if r["wavelength_nm"] == wavelength]
        def target(rows, n): return next((r for r in rows if r["order_n"] == n and r["order_m"] == 0), None)
        xr1, yr1 = target(xrows, 1), target(yrows, 1)
        def eta(row): return None if row is None else float(row["order_efficiency_source_norm"])
        ex, ey = eta(xr1), eta(yr1)
        ratio = None if ex is None or ey is None or ey <= 0 else ex / ey
        jxy = None
        jab = None
        if xr1 is not None and yr1 is not None:
            jxy = [[complex(xr1["Ex_real"], xr1["Ex_imag"]), complex(yr1["Ex_real"], yr1["Ex_imag"])], [complex(xr1["Ey_real"], xr1["Ey_imag"]), complex(yr1["Ey_real"], yr1["Ey_imag"])]]
            jab = transform_xy(jxy)
        target_ab = None if jab is None else jab[0][0]
        contrast.append({"wavelength_nm": wavelength, "eta_plus1_x": ex, "eta_plus1_y": ey, "x_over_y_ratio": ratio, "x_minus_y": None if ex is None or ey is None else ex - ey, "contrast_db": None if ratio is None else 10.0 * math.log10(ratio), "denominator_directionality_x": float(sum(r["order_efficiency_source_norm"] for r in xrows)) if xrows else None, "denominator_directionality_y": float(sum(r["order_efficiency_source_norm"] for r in yrows)) if yrows else None, "target_x_Ex_real": None if xr1 is None else xr1["Ex_real"], "target_x_Ex_imag": None if xr1 is None else xr1["Ex_imag"], "target_x_Ey_real": None if xr1 is None else xr1["Ey_real"], "target_x_Ey_imag": None if xr1 is None else xr1["Ey_imag"], "target_y_Ex_real": None if yr1 is None else yr1["Ex_real"], "target_y_Ex_imag": None if yr1 is None else yr1["Ex_imag"], "target_y_Ey_real": None if yr1 is None else yr1["Ey_real"], "target_y_Ey_imag": None if yr1 is None else yr1["Ey_imag"], "t_alpha_star_from_alpha_real": None if target_ab is None else target_ab.real, "t_alpha_star_from_alpha_imag": None if target_ab is None else target_ab.imag, "t_alpha_star_from_alpha_phase_rad": None if target_ab is None or abs(target_ab) == 0 else math.atan2(target_ab.imag, target_ab.real), "alpha_basis_psi_deg": ALPHA_PSI_DEG, "alpha_basis_chi_deg": ALPHA_CHI_DEG})
    write_csv(REPORT / "h1d1_order_contrast.csv", contrast)
    P = manifest["P_supercell_nm"]
    xs = [row["x_nm"] for row in manifest["copies"]]
    analytic = {"schema": "H1D1_ANALYTIC_ARRAY_FACTOR_V1", "positions_nm": xs, "sign_convention": manifest["detour_sign_convention"], "m_target": 1, "wavelength_independent_normalized_phase": True, "orders": {}}
    for m in (-1, 0, 1):
        amplitude = sum(complex(math.cos(-2 * math.pi * m * x / P), math.sin(-2 * math.pi * m * x / P)) for x in xs)
        analytic["orders"][str(m)] = {"array_factor_real": amplitude.real, "array_factor_imag": amplitude.imag, "array_factor_abs": abs(amplitude), "array_factor_power": abs(amplitude) ** 2, "normalized_power": abs(amplitude) ** 2 / 36.0}
    analytic["interpretation"] = "Identical local blocks at six equally spaced positions yield the exact discrete array-factor result; this is the analytic reference, not full-wave truth."
    write_json(REPORT / "h1d1_analytic_array_factor.json", analytic)
    fullwave = {"schema": "H1D1_FULLWAVE_VS_ANALYTIC_V1", "analytic_reference": str(REPORT / "h1d1_analytic_array_factor.json"), "available_polarizations": sorted(result), "comparison": "postprocess-only; no analytic substitution for FDTD", "target_order_rows": contrast}
    write_json(REPORT / "h1d1_fullwave_vs_analytic.json", fullwave)
    coupling = {"schema": "H1D1_PARENT_VS_K6_COUPLING_V1", "parent_reference": str(STRICT_BANK_PATH), "parent_uid": PARENT_UID, "parent_hash": PARENT_HASH, "parent_read_only": True, "k6_order_contrast": contrast, "causal_attribution": "not_available_without_no_detour_control", "coupling_assessment": "PENDING_FULLWAVE_EVIDENCE" if len(result) < 2 else "DESCRIPTIVE_ONLY_NO_FROZEN_THRESHOLD"}
    write_json(REPORT / "h1d1_parent_vs_k6_coupling.json", coupling)
    accounting = read_json(ACCOUNTING_PATH)
    if len(result) < 2:
        classification = "INCONCLUSIVE"
    else:
        target_x = [row["eta_plus1_x"] for row in contrast if row["eta_plus1_x"] is not None]
        target_y = [row["eta_plus1_y"] for row in contrast if row["eta_plus1_y"] is not None]
        zero_x = [next((r["order_efficiency_source_norm"] for r in result["x"] if r["wavelength_nm"] == row["wavelength_nm"] and r["order_n"] == 0 and r["order_m"] == 0), None) for row in contrast]
        minus_x = [next((r["order_efficiency_source_norm"] for r in result["x"] if r["wavelength_nm"] == row["wavelength_nm"] and r["order_n"] == -1 and r["order_m"] == 0), None) for row in contrast]
        target_dominant = bool(target_x and all(tx > max(zx or 0.0, mx or 0.0) for tx, zx, mx in zip(target_x, zero_x, minus_x)))
        x_over_y = bool(target_x and target_y and all(tx > ty for tx, ty in zip(target_x, target_y)))
        classification = "PURE_DETOUR_FULLWAVE_FEASIBILITY_SUPPORTED" if target_dominant and x_over_y else "PURE_DETOUR_FULLWAVE_FEASIBILITY_WEAK_OR_DISTORTED" if any(tx > ty for tx, ty in zip(target_x, target_y)) and target_dominant else "PURE_DETOUR_FULLWAVE_FEASIBILITY_NOT_SUPPORTED"
    final = {"schema": "H1D1_FINAL_V1", "status": classification if len(result) == 2 else "INCONCLUSIVE", "stage": "H1D-1", "branch": current_branch(), "head": current_head(), "layout_uid": manifest["layout_uid"], "parent_geometry_uid": PARENT_UID, "parent_exact_hash": PARENT_HASH, "six_positions_nm": xs, "intended_phase_deg": [row["intended_phase_deg"] for row in manifest["copies"]], "position_sorted_phase_order": manifest["position_sorted_phase_order"], "p_nm": manifest["p_nm"], "P_supercell_nm": P, "m_target": 1, "sign_convention": manifest["detour_sign_convention"], "planned_formal_cases": MAX_SUBRUNS, "entered_formal_cases": accounting["solver_subruns_entered"], "accepted_formal_cases": accounting["solver_subruns_accepted"], "x_pol_eta_plus1_0_minus1": [{"wavelength_nm": w, "eta_plus1": next((r["order_efficiency_source_norm"] for r in result.get("x", []) if r["wavelength_nm"] == w and r["order_n"] == 1 and r["order_m"] == 0), None), "eta_0": next((r["order_efficiency_source_norm"] for r in result.get("x", []) if r["wavelength_nm"] == w and r["order_n"] == 0 and r["order_m"] == 0), None), "eta_minus1": next((r["order_efficiency_source_norm"] for r in result.get("x", []) if r["wavelength_nm"] == w and r["order_n"] == -1 and r["order_m"] == 0), None)} for w in GRID], "y_pol_eta_plus1_0_minus1": [{"wavelength_nm": w, "eta_plus1": next((r["order_efficiency_source_norm"] for r in result.get("y", []) if r["wavelength_nm"] == w and r["order_n"] == 1 and r["order_m"] == 0), None), "eta_0": next((r["order_efficiency_source_norm"] for r in result.get("y", []) if r["wavelength_nm"] == w and r["order_n"] == 0 and r["order_m"] == 0), None), "eta_minus1": next((r["order_efficiency_source_norm"] for r in result.get("y", []) if r["wavelength_nm"] == w and r["order_n"] == -1 and r["order_m"] == 0), None)} for w in GRID], "target_order_contrast": contrast, "analytic_expectation": analytic["orders"], "control_layout_present": False, "causal_attribution_allowed": False, "ml_admitted": False, "hard_gates": []}
    write_json(REPORT / "h1d1_final.json", final)
    lines = ["# Stage H1D-1 LP Pure-Detour K6 Full-Wave Feasibility", "", f"- Status: `{final['status']}`", f"- Formal cases planned/entered/accepted: `{MAX_SUBRUNS}/{final['entered_formal_cases']}/{final['accepted_formal_cases']}`; one 9-point broadband solve per polarization.", f"- Parent: `{PARENT_UID}` / `{PARENT_HASH}`; one exact local dimer copied six times.", f"- p/P: `{manifest['p_nm']}` / `{manifest['P_supercell_nm']}` nm; target m=+1; sign `{manifest['detour_sign_convention']}`.", f"- x-sorted phase order: `{manifest['position_sorted_phase_order']}`.", "- No no-detour control was run; mechanism attribution is not claimed.", "- No new performance threshold was frozen; classification is descriptive and evidence-scoped.", "", "Artifacts: `h1d1_k6_detour_manifest.json`, `h1d1_geometry_legality.json`, `h1d1_solver_accounting.json`, `h1d1_xpol_order_spectrum.csv`, `h1d1_ypol_order_spectrum.csv`, `h1d1_order_contrast.csv`, `h1d1_analytic_array_factor.json`, `h1d1_fullwave_vs_analytic.json`, `h1d1_parent_vs_k6_coupling.json`, `h1d1_final.json`." ]
    (REPORT / "h1d1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return final


def preflight() -> dict[str, Any]:
    manifest = ensure_manifest()
    legal = legality(manifest)
    if not legal["pass"]:
        raise RuntimeError("HARD_GATE_K6_GEOMETRY_ILLEGAL")
    write_json(LEGALITY_PATH, legal)
    accounting = initial_accounting(manifest)
    snapshot = live_accounting()
    write_json(REPORT / "h1d1_solver_accounting.json", {**accounting, "preflight_live_solver_accounting": snapshot})
    return {"status": "READY", "manifest_freeze_sha256": manifest["freeze_sha256"], "legality": legal, "live_solver_accounting": snapshot, "solver_entered": False}


def execute() -> dict[str, Any]:
    manifest = ensure_manifest()
    legal = read_json(LEGALITY_PATH)
    if not legal.get("pass"):
        raise RuntimeError("HARD_GATE_PREFLIGHT_NOT_PASS")
    runtime_config = load_runtime()
    scheduler_mod = load_module(ROOT / "scripts/apcd_global_fdtd_slot_v1.py", "h1d1_slot")
    scheduler = scheduler_mod.GlobalSlotScheduler(SLOT_REGISTRY)
    for pol in POLARIZATIONS:
        result = run_case(manifest, pol, scheduler, runtime_config)
        print(json.dumps({"case": pol, "status": result.get("status"), "solver_entered": result.get("solver_entered", False)}), flush=True)
    return postprocess(manifest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "execute", "postprocess"))
    args = parser.parse_args()
    if args.mode == "preflight":
        print(json.dumps(preflight(), indent=2, default=str)); return 0
    manifest = ensure_manifest(); initial_accounting(manifest)
    if args.mode == "postprocess":
        print(json.dumps(postprocess(manifest), indent=2, default=str)); return 0
    print(json.dumps(execute(), indent=2, default=str)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
