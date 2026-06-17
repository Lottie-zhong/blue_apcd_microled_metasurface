from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

NM = 1e-9
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b2_finite_patch_xplus"
CANDIDATE_DIRNAME = "D195_T90"
CANDIDATE_OUT = OUT_DIR / CANDIDATE_DIRNAME
SAVED_FSP_DIR = CANDIDATE_OUT / "_saved_fsp"
BASELINE_AVG_CSV = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "xline_minimal_robustness" / "xline_minimal_position_averages.csv"

WAVELENGTH_NM = 450.0
MATERIAL_INDEX = 2.6
GAN_INDEX = 2.56
SIM_TIME_FS = 100.0
FIELD_MONITOR = "top_field_monitor_zprop"
POWER_MONITOR = "top_power_monitor_zprop"
X_SOURCE = "route_b2_x_dipole_zprop"
Y_SOURCE = "route_b2_y_dipole_zprop"
GRID_N = 101
CONES_DEG = [5.0, 10.0, 20.0, 30.0]

PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
Q_NM = min(PERIOD_X_NM, PERIOD_Y_NM) / 4.0
ARRAY_NX = 7
ARRAY_NY = 3
IX_VALUES = list(range(-3, 4))
IY_VALUES = list(range(-1, 2))
X_CENTERS_NM = [ix * PERIOD_X_NM for ix in IX_VALUES]
Y_CENTERS_NM = [iy * PERIOD_Y_NM for iy in IY_VALUES]

HEIGHT_NM = 525.0
D_NM = 195.0
THETA_DEG = 90.0
PSI_DEG = 97.5
J1_ROTATION_DEG = 90.0 - PSI_DEG
J2_ROTATION_DEG = 90.0 - (PSI_DEG - 45.0)
SOURCE_Z_NM = -200.0
GAN_X_SPAN_NM = 3000.0
GAN_Y_SPAN_NM = 1200.0
GAN_TOP_Z_NM = 0.0
GAN_ACTUAL_BOTTOM_Z_NM = -1100.0
FDTD_X_SPAN_NM = 20000.0
FDTD_Y_SPAN_NM = 20000.0
FDTD_Z_MIN_NM = -900.0
FDTD_Z_MAX_NM = 1800.0
MONITOR_Z_NM = 1000.0
MONITOR_X_SPAN_NM = 22000.0
MONITOR_Y_SPAN_NM = 22000.0

# J1/J2 only: no legacy A/B terminology in generated reports.
J_ROLES = [
    {
        "role": "J1",
        "length_nm": 230.0,
        "width_nm": 100.0,
        "height_nm": HEIGHT_NM,
        "rotation_deg": J1_ROTATION_DEG,
        "center_x_nm": 0.5 * D_NM * math.cos(math.radians(THETA_DEG)),
        "center_y_nm": 0.5 * D_NM * math.sin(math.radians(THETA_DEG)),
    },
    {
        "role": "J2",
        "length_nm": 180.0,
        "width_nm": 90.0,
        "height_nm": HEIGHT_NM,
        "rotation_deg": J2_ROTATION_DEG,
        "center_x_nm": -0.5 * D_NM * math.cos(math.radians(THETA_DEG)),
        "center_y_nm": -0.5 * D_NM * math.sin(math.radians(THETA_DEG)),
    },
]

CASES = [
    {
        "case_id": "RB2_D195_T90_X_PLUS_QP_X_T100FS",
        "position_id": "x_plus_qp",
        "orientation": "x",
        "x_nm": Q_NM,
        "y_nm": 0.0,
        "z_nm": SOURCE_Z_NM,
        "enabled_source": X_SOURCE,
        "disabled_source": Y_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0,
    },
    {
        "case_id": "RB2_D195_T90_X_PLUS_QP_Y_T100FS",
        "position_id": "x_plus_qp",
        "orientation": "y",
        "x_nm": Q_NM,
        "y_nm": 0.0,
        "z_nm": SOURCE_Z_NM,
        "enabled_source": Y_SOURCE,
        "disabled_source": X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 90.0,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage10 CP Route B2 D195/T90 finite-patch x_plus_qp rescue test only.")
    parser.add_argument("--runtime", default="configs/runtime.yaml")
    parser.add_argument("--output-dir", default=str(OUT_DIR))
    parser.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
    parser.add_argument("--grid-n", type=int, default=GRID_N)
    parser.add_argument("--cone-deg", type=float, nargs="*", default=CONES_DEG)
    parser.add_argument("--show-gui", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def ensure_dirs() -> None:
    CANDIDATE_OUT.mkdir(parents=True, exist_ok=True)
    SAVED_FSP_DIR.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def safe_set(fdtd: object, prop: str, value: Any, warnings: list[str]) -> None:
    try:
        fdtd.set(prop, value)
    except Exception as exc:
        warnings.append(f"set skipped {prop}={value!r}: {type(exc).__name__}: {exc}")


def try_create_gan_material(fdtd: object, warnings: list[str]) -> str:
    name = "GaN_450nm_n2p56_custom"
    try:
        fdtd.addrect(); fdtd.set("name", "tmp_gan_material_probe"); fdtd.set("material", name); fdtd.delete()
        return name
    except Exception:
        try:
            fdtd.delete()
        except Exception:
            pass
    try:
        fdtd.eval('mat = addmaterial("(n,k) Material"); setmaterial(mat, "name", "GaN_450nm_n2p56_custom"); setmaterial("GaN_450nm_n2p56_custom", "Refractive Index", 2.56); setmaterial("GaN_450nm_n2p56_custom", "Imaginary Refractive Index", 0); setmaterial("GaN_450nm_n2p56_custom", "Mesh order", 3); setmaterial("GaN_450nm_n2p56_custom", "color", [1,0.35,0.75,1]);')
        return name
    except Exception as exc:
        warnings.append(f"Could not create/assign {name}; fallback to object-defined n=2.56: {type(exc).__name__}: {exc}")
        return ""


def add_gan(fdtd: object, warnings: list[str]) -> None:
    mat = try_create_gan_material(fdtd, warnings)
    fdtd.addrect()
    fdtd.set("name", "GaN_continuous_block_zprop_extends_into_bottom_PML")
    fdtd.set("x", 0)
    fdtd.set("y", 0)
    fdtd.set("x span", GAN_X_SPAN_NM * NM)
    fdtd.set("y span", GAN_Y_SPAN_NM * NM)
    fdtd.set("z min", GAN_ACTUAL_BOTTOM_Z_NM * NM)
    fdtd.set("z max", GAN_TOP_Z_NM * NM)
    if mat:
        fdtd.set("material", mat)
    else:
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", GAN_INDEX)


def add_uniform_patch(fdtd: object) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    parent = "CP_route_b2_D195_T90_uniform_patch_7x3_group"
    fdtd.addstructuregroup()
    fdtd.set("name", parent)
    fdtd.groupscope(f"::model::{parent}")
    for ix, x0 in zip(IX_VALUES, X_CENTERS_NM):
        for iy, y0 in zip(IY_VALUES, Y_CENTERS_NM):
            group = f"DIMER_ix{ix}_iy{iy}_J1J2_D195_T90"
            fdtd.addstructuregroup()
            fdtd.set("name", group)
            fdtd.groupscope(f"::model::{parent}::{group}")
            for role in J_ROLES:
                x_nm = x0 + float(role["center_x_nm"])
                y_nm = y0 + float(role["center_y_nm"])
                fdtd.addrect()
                fdtd.set("name", f"{role['role']}_pillar")
                fdtd.set("x", x_nm * NM)
                fdtd.set("y", y_nm * NM)
                fdtd.set("x span", float(role["length_nm"]) * NM)
                fdtd.set("y span", float(role["width_nm"]) * NM)
                fdtd.set("z min", 0)
                fdtd.set("z max", float(role["height_nm"]) * NM)
                fdtd.set("first axis", "z")
                fdtd.set("rotation 1", float(role["rotation_deg"]))
                fdtd.set("material", "<Object defined dielectric>")
                fdtd.set("index", MATERIAL_INDEX)
                inventory.append({
                    "object_name": f"{parent}/{group}/{role['role']}_pillar",
                    "dimer_ix": ix,
                    "dimer_iy": iy,
                    "role": role["role"],
                    "x_center_nm": f"{x_nm:.6f}",
                    "y_center_nm": f"{y_nm:.6f}",
                    "z_min_nm": "0.0",
                    "z_max_nm": f"{float(role['height_nm']):.1f}",
                    "rotation_axis": "z",
                    "rotation_deg": f"{float(role['rotation_deg']):.6g}",
                })
            fdtd.groupscope(f"::model::{parent}")
    fdtd.groupscope("::model")
    return inventory


def add_dipoles(fdtd: object, warnings: list[str]) -> None:
    for name, theta, phi in [(X_SOURCE, 90.0, 0.0), (Y_SOURCE, 90.0, 90.0)]:
        fdtd.adddipole()
        fdtd.set("name", name)
        fdtd.set("x", Q_NM * NM)
        fdtd.set("y", 0)
        fdtd.set("z", SOURCE_Z_NM * NM)
        fdtd.set("wavelength start", WAVELENGTH_NM * NM)
        fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
        safe_set(fdtd, "theta", theta, warnings)
        safe_set(fdtd, "phi", phi, warnings)
        fdtd.set("enabled", 0)


def add_monitors(fdtd: object) -> None:
    for add, name in [(fdtd.addprofile, FIELD_MONITOR), (fdtd.addpower, POWER_MONITOR)]:
        add()
        fdtd.set("name", name)
        fdtd.set("monitor type", "2D Z-normal")
        fdtd.set("x span", MONITOR_X_SPAN_NM * NM)
        fdtd.set("y span", MONITOR_Y_SPAN_NM * NM)
        fdtd.set("z", MONITOR_Z_NM * NM)


def build_setup(fdtd: object, sim_time_fs: float) -> tuple[list[str], list[dict[str, Any]]]:
    warnings: list[str] = []
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", FDTD_X_SPAN_NM * NM)
    fdtd.set("y span", FDTD_Y_SPAN_NM * NM)
    fdtd.set("z min", FDTD_Z_MIN_NM * NM)
    fdtd.set("z max", FDTD_Z_MAX_NM * NM)
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        fdtd.set(prop, "PML")
    fdtd.set("mesh accuracy", 3)
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_gan(fdtd, warnings)
    inventory = add_uniform_patch(fdtd)
    add_dipoles(fdtd, warnings)
    add_monitors(fdtd)
    return warnings, inventory


def configure_case(fdtd: object, case: dict[str, Any], sim_time_fs: float) -> None:
    fdtd.select("FDTD")
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    for source, enabled in [(case["enabled_source"], 1), (case["disabled_source"], 0)]:
        fdtd.select(source)
        fdtd.set("enabled", enabled)
        fdtd.set("x", float(case["x_nm"]) * NM)
        fdtd.set("y", float(case["y_nm"]) * NM)
        fdtd.set("z", float(case["z_nm"]) * NM)
    fdtd.select(case["enabled_source"])
    fdtd.set("theta", case["theta_deg"])
    fdtd.set("phi", case["phi_deg"])


def preflight(fdtd: object, case: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for name in ["FDTD", X_SOURCE, Y_SOURCE, FIELD_MONITOR, POWER_MONITOR]:
        try:
            fdtd.select(name)
        except Exception as exc:
            errors.append(f"missing object {name}: {type(exc).__name__}: {exc}")
    for prop in ["x min bc", "x max bc", "y min bc", "y max bc", "z min bc", "z max bc"]:
        try:
            val = fdtd.getnamed("FDTD", prop)
            if str(val).strip().upper() != "PML":
                errors.append(f"{prop}={val}, expected PML")
        except Exception as exc:
            errors.append(f"could not read {prop}: {type(exc).__name__}: {exc}")
    for source_name, expected in [(case["enabled_source"], 1), (case["disabled_source"], 0)]:
        try:
            enabled = int(float(fdtd.getnamed(source_name, "enabled")))
            if enabled != expected:
                errors.append(f"{source_name} enabled={enabled}, expected {expected}")
        except Exception as exc:
            errors.append(f"could not read enabled for {source_name}: {type(exc).__name__}: {exc}")
    return not errors, errors


def fsp_complete(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "missing_fsp"
    size = path.stat().st_size
    if size < 10_000_000:
        return False, f"incomplete_setup_size_fsp:{size}"
    return True, f"existing_completed_size_fsp:{size}"


def run_case(lumapi: Any, runtime: Any, setup_fsp: Path, case: dict[str, Any], sim_time_fs: float, show_gui: bool, force: bool) -> dict[str, Any]:
    fsp = SAVED_FSP_DIR / f"{case['case_id']}.fsp"
    if fsp.exists() and not force:
        ok, reason = fsp_complete(fsp)
        if ok:
            return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "reused", "result_fsp": str(fsp), "notes": reason + "; saved FSP already exists; not rerun"}
        try:
            fsp.unlink()
        except Exception:
            pass
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(setup_fsp.resolve()))
        configure_case(fdtd, case, sim_time_fs)
        ok, errors = preflight(fdtd, case)
        if not ok:
            return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "preflight_failed", "result_fsp": str(fsp), "notes": " | ".join(errors)}
        fdtd.save(str(fsp.resolve()))
        fdtd.run()
        fdtd.save(str(fsp.resolve()))
        return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "ok", "result_fsp": str(fsp), "notes": "setup/save/load/run/save lifecycle complete"}
    except Exception as exc:
        return {"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "failed", "result_fsp": str(fsp), "notes": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def mask_for(ux: np.ndarray, uy: np.ndarray, shape: tuple[int, ...], cone: float) -> np.ndarray:
    ux = np.asarray(ux, dtype=float).squeeze()
    uy = np.asarray(uy, dtype=float).squeeze()
    lim = math.sin(math.radians(cone))
    if ux.ndim == 1 and uy.ndim == 1:
        xx, yy = np.meshgrid(ux, uy, indexing="ij")
    else:
        xx, yy = np.broadcast_arrays(ux, uy)
    mask = (xx**2 + yy**2) <= lim**2
    try:
        return np.broadcast_to(mask, shape)
    except Exception:
        return mask.T if mask.T.shape == shape else np.ones(shape, dtype=bool)


def extract_fields(fdtd: object, grid_n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    vec = fdtd.farfieldvector3d(FIELD_MONITOR, 1, grid_n, grid_n)
    arr = np.asarray(vec)
    if arr.shape[-1] >= 3:
        ex, ey = arr[..., 0], arr[..., 1]
    elif arr.shape[0] >= 3:
        ex, ey = arr[0, ...], arr[1, ...]
    else:
        raise ValueError(f"bad farfieldvector3d shape {arr.shape}")
    ux = np.asarray(fdtd.farfieldux(FIELD_MONITOR, 1, grid_n, grid_n), dtype=float).squeeze()
    uy = np.asarray(fdtd.farfielduy(FIELD_MONITOR, 1, grid_n, grid_n), dtype=float).squeeze()
    info = {"farfieldvector3d_shape": list(arr.shape), "farfieldvector3d_complex": bool(np.iscomplexobj(arr)), "ux_shape": list(np.asarray(ux).shape), "uy_shape": list(np.asarray(uy).shape)}
    return np.asarray(ex, dtype=np.complex128).squeeze(), np.asarray(ey, dtype=np.complex128).squeeze(), ux, uy, info


def extract_case(lumapi: Any, runtime: Any, case: dict[str, Any], grid_n: int, cones: list[float], show_gui: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fsp = SAVED_FSP_DIR / f"{case['case_id']}.fsp"
    base = {"case_id": case["case_id"], "candidate_id": "RB1_J1J2_D195_T90_PSI97p5_H525", "position_id": case["position_id"], "orientation": case["orientation"], "x_nm": case["x_nm"], "y_nm": case["y_nm"], "z_nm": case["z_nm"], "grid_n": grid_n, "result_fsp": str(fsp)}
    if not fsp.exists():
        return [{**base, "cone_deg": c, "extraction_status": "missing_fsp", "notes": "FSP not found"} for c in cones], {"case_id": case["case_id"], "status": "missing_fsp"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, ux, uy, info = extract_fields(fdtd, grid_n)
        er = (ex - 1j * ey) / math.sqrt(2.0)
        el = (ex + 1j * ey) / math.sqrt(2.0)
        rows: list[dict[str, Any]] = []
        for cone in cones:
            mask = mask_for(ux, uy, er.shape, cone).astype(bool)
            ir = float(np.sum(np.abs(er[mask]) ** 2))
            il = float(np.sum(np.abs(el[mask]) ** 2))
            total = ir + il
            rows.append({
                **base,
                "cone_deg": cone,
                "IR_cone": ir,
                "IL_cone": il,
                "DoCP_RminusL": (ir - il) / total if total else float("nan"),
                "DoCP_LminusR": (il - ir) / total if total else float("nan"),
                "L_fraction": il / total if total else float("nan"),
                "R_fraction": ir / total if total else float("nan"),
                "total_cone_power": total,
                "extraction_status": "ok",
                "monitor_names": f"{FIELD_MONITOR};{POWER_MONITOR}",
                "E_components_used": "farfieldvector3d Ex/Ey for calibrated +z CP basis",
                "notes": "Route B2 finite-patch x_plus_qp only; incoherent averaging done at position level",
            })
        return rows, {"case_id": case["case_id"], "status": "ok", "array_info": info}
    except Exception as exc:
        return [{**base, "cone_deg": c, "extraction_status": "failed", "notes": f"{type(exc).__name__}: {exc}"} for c in cones], {"case_id": case["case_id"], "status": "failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd:
            try:
                fdtd.close()
            except Exception:
                pass


def average_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [r for r in case_rows if r.get("extraction_status") == "ok"]
    out: list[dict[str, Any]] = []
    for cone in sorted({float(r["cone_deg"]) for r in ok}):
        pair = [r for r in ok if float(r["cone_deg"]) == cone]
        if len({r["orientation"] for r in pair}) != 2:
            continue
        ir = sum(float(r["IR_cone"]) for r in pair)
        il = sum(float(r["IL_cone"]) for r in pair)
        total = ir + il
        out.append({
            "candidate_id": "RB1_J1J2_D195_T90_PSI97p5_H525",
            "position_id": "x_plus_qp",
            "cone_deg": cone,
            "included_cases": ";".join(r["case_id"] for r in pair),
            "IR_total": ir,
            "IL_total": il,
            "P_total": total,
            "DoCP_RminusL": (ir - il) / total if total else float("nan"),
            "DoCP_LminusR": (il - ir) / total if total else float("nan"),
            "L_fraction": il / total if total else float("nan"),
            "R_fraction": ir / total if total else float("nan"),
            "notes": "Incoherent x/y dipole power sum only; no coherent field addition.",
        })
    return out


def read_baseline() -> dict[float, dict[str, Any]]:
    out: dict[float, dict[str, Any]] = {}
    if not BASELINE_AVG_CSV.exists():
        return out
    with BASELINE_AVG_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("position_id") == "x_plus_qp":
                out[float(row["cone_deg"])] = row
    return out


def comparison_rows(avg_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = read_baseline()
    rows: list[dict[str, Any]] = []
    for row in avg_rows:
        cone = float(row["cone_deg"])
        b = baseline.get(cone, {})
        base_docp = float(b.get("DoCP_total_RminusL", "nan")) if b else float("nan")
        base_lfrac = float(b.get("L_fraction_total", "nan")) if b else float("nan")
        base_power = float(b.get("P_total", "nan")) if b else float("nan")
        route_docp = float(row["DoCP_RminusL"])
        route_lfrac = float(row["L_fraction"])
        route_power = float(row["P_total"])
        rows.append({
            "cone_deg": cone,
            "baseline_DoCP_RminusL": base_docp,
            "route_b2_DoCP_RminusL": route_docp,
            "delta_DoCP_RminusL": route_docp - base_docp if math.isfinite(base_docp) else "",
            "baseline_L_fraction": base_lfrac,
            "route_b2_L_fraction": route_lfrac,
            "delta_L_fraction": route_lfrac - base_lfrac if math.isfinite(base_lfrac) else "",
            "baseline_total_cone_power": base_power,
            "route_b2_total_cone_power": route_power,
            "power_ratio_route_over_baseline": route_power / base_power if math.isfinite(base_power) and base_power else "",
            "promising_by_threshold": "yes" if route_docp < -0.2 and route_lfrac > 0.60 else "no",
            "notes": "Baseline is frozen dimer x_plus_qp average; Route B2 uses D195/T90 candidate.",
        })
    return rows


def write_summary(case_rows: list[dict[str, Any]], avg_rows: list[dict[str, Any]], comp_rows: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    def fmt_case(orientation: str, cone: float) -> str:
        row = next((r for r in case_rows if r.get("orientation") == orientation and float(r.get("cone_deg", -1)) == cone and r.get("extraction_status") == "ok"), None)
        if not row:
            return "not available"
        return f"DoCP={float(row['DoCP_RminusL']):.6g}, L_fraction={float(row['L_fraction']):.6g}, P={float(row['total_cone_power']):.6g}"
    def fmt_avg(cone: float) -> str:
        row = next((r for r in avg_rows if float(r.get("cone_deg", -1)) == cone), None)
        if not row:
            return "not available"
        return f"DoCP={float(row['DoCP_RminusL']):.6g}, L_fraction={float(row['L_fraction']):.6g}, P={float(row['P_total']):.6g}"
    comp20 = next((r for r in comp_rows if abs(float(r["cone_deg"]) - 20.0) < 1e-9), None)
    rescued = bool(comp20 and comp20["promising_by_threshold"] == "yes")
    power_ratio = comp20.get("power_ratio_route_over_baseline", "") if comp20 else ""
    lines = ["# Stage10 CP Route B2 D195/T90 finite-patch x_plus_qp rescue test\n\n"]
    lines.append("## English\n\n")
    lines.append("- Route: B2. Candidate tested: RB1_J1J2_D195_T90_PSI97p5_H525 only.\n")
    lines.append("- Finite-patch cases run/reused: x_plus_qp_x and x_plus_qp_y only. No center, no x_minus_qp, no broad sweep, no y-offset, no DBR/RCLED, no K=6, no steering.\n")
    lines.append("- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.\n")
    lines.append("- Powers are farfieldvector3d cone metrics. x/y dipole averaging is incoherent power addition only.\n\n")
    lines.append("### Single-case results\n\n")
    for cone in [5.0, 10.0, 20.0]:
        lines.append(f"- +/-{cone:g} deg: x-orientation {fmt_case('x', cone)}; y-orientation {fmt_case('y', cone)}.\n")
    lines.append("\n### x_plus_qp x/y incoherent average\n\n")
    for cone in [5.0, 10.0, 20.0]:
        lines.append(f"- +/-{cone:g} deg: {fmt_avg(cone)}.\n")
    lines.append("\n### Baseline comparison\n\n")
    if comp20:
        lines.append(f"- +/-20 deg baseline: DoCP={float(comp20['baseline_DoCP_RminusL']):.6g}, L_fraction={float(comp20['baseline_L_fraction']):.6g}, P={float(comp20['baseline_total_cone_power']):.6g}.\n")
        lines.append(f"- +/-20 deg Route B2: DoCP={float(comp20['route_b2_DoCP_RminusL']):.6g}, L_fraction={float(comp20['route_b2_L_fraction']):.6g}, P={float(comp20['route_b2_total_cone_power']):.6g}.\n")
        lines.append(f"- Total cone power ratio Route/Baseline at +/-20 deg: {power_ratio}.\n")
    lines.append(f"- Rescue verdict at +/-20 deg: {'rescued / promising' if rescued else 'not rescued by the requested thresholds'}.\n")
    lines.append("- If rescued: next step is D195/T90 center_x/y and x_minus_qp_x/y. If failed: test backup D182p5_T85 x_plus_qp_x/y.\n")
    lines.append("\n## 中文\n\n")
    lines.append("- 路线：B2。只测试候选 RB1_J1J2_D195_T90_PSI97p5_H525。\n")
    lines.append("- 有限阵列 case：只运行/复用 x_plus_qp_x 和 x_plus_qp_y。没有 center，没有 x_minus_qp，没有大扫，没有 y-offset，没有 DBR/RCLED，没有 K=6，没有 steering。\n")
    lines.append("- CP 约定：R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)；DoCP_RminusL 为负表示 L 输出占优。\n")
    lines.append("- 这里的功率是 farfieldvector3d cone 指标；x/y 偶极平均只做强度非相干相加。\n\n")
    lines.append("### 单 case 结果\n\n")
    for cone in [5.0, 10.0, 20.0]:
        lines.append(f"- +/-{cone:g} deg：x 取向 {fmt_case('x', cone)}；y 取向 {fmt_case('y', cone)}。\n")
    lines.append("\n### x_plus_qp 的 x/y 非相干平均\n\n")
    for cone in [5.0, 10.0, 20.0]:
        lines.append(f"- +/-{cone:g} deg：{fmt_avg(cone)}。\n")
    lines.append("\n### baseline 对比\n\n")
    if comp20:
        lines.append(f"- +/-20 deg baseline：DoCP={float(comp20['baseline_DoCP_RminusL']):.6g}, L_fraction={float(comp20['baseline_L_fraction']):.6g}, P={float(comp20['baseline_total_cone_power']):.6g}。\n")
        lines.append(f"- +/-20 deg Route B2：DoCP={float(comp20['route_b2_DoCP_RminusL']):.6g}, L_fraction={float(comp20['route_b2_L_fraction']):.6g}, P={float(comp20['route_b2_total_cone_power']):.6g}。\n")
        lines.append(f"- +/-20 deg 总 cone power 比值 Route/Baseline：{power_ratio}。\n")
    lines.append(f"- +/-20 deg 救援判断：{'救回 / promising' if rescued else '未达到本轮阈值'}。\n")
    lines.append("- 如果救回，下一步测试 D195/T90 的 center_x/y 和 x_minus_qp_x/y；如果失败，下一步测试备选 D182p5_T85 的 x_plus_qp_x/y。\n")
    (OUT_DIR / "route_b2_xplus_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    ensure_dirs()
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    setup_fsp = CANDIDATE_OUT / "route_b2_D195_T90_xplus_setup.fsp"
    warnings: list[str] = []
    inventory: list[dict[str, Any]] = []
    setup_status = "ok"
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not args.show_gui) and runtime.hide_gui)
        warnings, inventory = build_setup(fdtd, args.simulation_time_fs)
        fdtd.save(str(setup_fsp.resolve()))
    except Exception as exc:
        setup_status = f"failed: {type(exc).__name__}: {exc}"
    finally:
        if fdtd:
            try:
                fdtd.close()
            except Exception:
                pass
    run_rows: list[dict[str, Any]] = []
    if setup_status == "ok" and not args.dry_run:
        for case in CASES:
            run_rows.append(run_case(lumapi, runtime, setup_fsp, case, args.simulation_time_fs, args.show_gui, args.force))
    else:
        for case in CASES:
            run_rows.append({"case_id": case["case_id"], "position_id": case["position_id"], "orientation": case["orientation"], "fdtd_status": "not_run" if args.dry_run else setup_status, "result_fsp": str(SAVED_FSP_DIR / f"{case['case_id']}.fsp"), "notes": "dry run" if args.dry_run else setup_status})
    case_rows: list[dict[str, Any]] = []
    extract_debug: list[dict[str, Any]] = []
    if not args.dry_run:
        for case in CASES:
            rows, dbg = extract_case(lumapi, runtime, case, args.grid_n, args.cone_deg, args.show_gui)
            case_rows.extend(rows)
            extract_debug.append(dbg)
    avg_rows = average_rows(case_rows)
    comp_rows = comparison_rows(avg_rows)
    write_csv(OUT_DIR / "route_b2_xplus_case_metrics.csv", case_rows)
    write_csv(OUT_DIR / "route_b2_xplus_average_metrics.csv", avg_rows)
    write_csv(OUT_DIR / "route_b2_xplus_baseline_comparison.csv", comp_rows)
    debug = {
        "route": "B2",
        "candidate_id": "RB1_J1J2_D195_T90_PSI97p5_H525",
        "only_cases_requested": [c["case_id"] for c in CASES],
        "no_center": True,
        "no_x_minus_qp": True,
        "no_broad_sweep": True,
        "setup_status": setup_status,
        "setup_fsp": str(setup_fsp),
        "setup_warnings": warnings,
        "run_rows": run_rows,
        "extract_debug": extract_debug,
        "patch_inventory_count": len(inventory),
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
    }
    (OUT_DIR / "route_b2_xplus_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_summary(case_rows, avg_rows, comp_rows, run_rows)
    failed_runs = [r for r in run_rows if r["fdtd_status"] not in {"ok", "reused", "not_run"}]
    failed_extract = [d for d in extract_debug if d.get("status") != "ok"]
    print(json.dumps({"setup_status": setup_status, "run_rows": run_rows, "average_rows": avg_rows, "comparison_rows": comp_rows}, indent=2))
    return 1 if setup_status != "ok" or failed_runs or failed_extract else 0


if __name__ == "__main__":
    raise SystemExit(main())
