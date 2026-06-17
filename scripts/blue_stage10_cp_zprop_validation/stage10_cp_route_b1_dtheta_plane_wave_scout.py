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
OUT_DIR = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "route_b1_dtheta_plane_wave_scout"
SAVED_FSP_DIR = OUT_DIR / "_saved_fsp"
BASELINE_METRICS = ROOT / "outputs" / "blue_stage10_cp_zprop_validation" / "planewave_control" / "cp_zprop_planewave_control_metrics.csv"

WAVELENGTH_NM = 450.0
PERIOD_X_NM = 431.907786
PERIOD_Y_NM = 432.0
HEIGHT_NM = 525.0
MATERIAL_INDEX = 2.6
SOURCE_Z_NM = -250.0
MONITOR_Z_NM = HEIGHT_NM + 350.0
Z_MIN_NM = -500.0
Z_MAX_NM = HEIGHT_NM + 700.0
SIM_TIME_FS = 300.0
FIELD_MONITOR = "field_monitor"
POWER_MONITOR = "T"
PSI_DEG = 97.5
Q_NM = min(PERIOD_X_NM, PERIOD_Y_NM) / 4.0
BASELINE_D_NM = 182.5
BASELINE_THETA_DEG = 70.0
THETA_LIST = [75.0, 80.0, 85.0, 90.0]
D_LIST = [170.0, 182.5, 195.0]

J1 = {
    "role": "J1",
    "length_nm": 230.0,
    "width_nm": 100.0,
    "height_nm": HEIGHT_NM,
    "rotation_deg": 90.0 - PSI_DEG,
    "definition": "larger Jones-response pillar role; frozen mapping element-1 role",
}
J2 = {
    "role": "J2",
    "length_nm": 180.0,
    "width_nm": 90.0,
    "height_nm": HEIGHT_NM,
    "rotation_deg": 90.0 - (PSI_DEG - 45.0),
    "definition": "smaller Jones-response pillar role; frozen mapping element-2 role",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Stage10 CP Route B1 d/theta periodic plane-wave scout; no finite-patch dipole FDTD.")
    p.add_argument("--runtime", default="configs/runtime.yaml")
    p.add_argument("--output-dir", default=str(OUT_DIR))
    p.add_argument("--simulation-time-fs", type=float, default=SIM_TIME_FS)
    p.add_argument("--mesh-accuracy", type=int, default=3)
    p.add_argument("--show-gui", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def ensure_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "_saved_fsp").mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def fnum(value: float) -> str:
    return f"{value:.9g}"


def token(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return str(value).replace(".", "p")


def cstr(z: complex) -> str:
    return f"{z.real:.12g}{z.imag:+.12g}j"


def candidate_id(d_nm: float, theta_deg: float, psi_deg: float = PSI_DEG) -> str:
    return f"RB1_J1J2_D{token(d_nm)}_T{token(theta_deg)}_PSI{token(psi_deg)}_H525"


def centers(d_nm: float, theta_deg: float) -> dict[str, tuple[float, float]]:
    a = math.radians(theta_deg)
    dx = d_nm * math.cos(a)
    dy = d_nm * math.sin(a)
    return {"J1": (0.5 * dx, 0.5 * dy), "J2": (-0.5 * dx, -0.5 * dy)}


def dist(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def source_distance_summary(d_nm: float, theta_deg: float) -> dict[str, Any]:
    c = centers(d_nm, theta_deg)
    j1x, j1y = c["J1"]
    j2x, j2y = c["J2"]
    plus_j1 = dist(Q_NM, 0.0, j1x, j1y)
    plus_j2 = dist(Q_NM, 0.0, j2x, j2y)
    minus_j1 = dist(-Q_NM, 0.0, j1x, j1y)
    minus_j2 = dist(-Q_NM, 0.0, j2x, j2y)
    center_j1 = dist(0.0, 0.0, j1x, j1y)
    center_j2 = dist(0.0, 0.0, j2x, j2y)
    return {
        "J1_x_nm": j1x,
        "J1_y_nm": j1y,
        "J2_x_nm": j2x,
        "J2_y_nm": j2y,
        "delta_x_J2_minus_J1_nm": j2x - j1x,
        "delta_y_J2_minus_J1_nm": j2y - j1y,
        "x_bias_abs_nm": abs(j1x - j2x),
        "center_distance_to_J1_nm": center_j1,
        "center_distance_to_J2_nm": center_j2,
        "plus_distance_to_J1_nm": plus_j1,
        "plus_distance_to_J2_nm": plus_j2,
        "minus_distance_to_J1_nm": minus_j1,
        "minus_distance_to_J2_nm": minus_j2,
        "plus_nearer_role": "J1" if plus_j1 < plus_j2 else "J2" if plus_j2 < plus_j1 else "tie",
        "minus_nearer_role": "J1" if minus_j1 < minus_j2 else "J2" if minus_j2 < minus_j1 else "tie",
    }


def candidate_rows() -> list[dict[str, Any]]:
    rows = []
    for d in D_LIST:
        for theta in THETA_LIST:
            cid = candidate_id(d, theta)
            g = source_distance_summary(d, theta)
            rows.append({
                "candidate_id": cid,
                "role_terms": "J1/J2 only",
                "d_nm": fnum(d),
                "theta_deg": fnum(theta),
                "psi_deg": fnum(PSI_DEG),
                "height_nm": fnum(HEIGHT_NM),
                "period_x_nm": fnum(PERIOD_X_NM),
                "period_y_nm": fnum(PERIOD_Y_NM),
                "wavelength_nm": fnum(WAVELENGTH_NM),
                "material_index": fnum(MATERIAL_INDEX),
                "J1_size_nm": "230x100",
                "J2_size_nm": "180x90",
                "J1_rotation_deg": fnum(J1["rotation_deg"]),
                "J2_rotation_deg": fnum(J2["rotation_deg"]),
                "note": "Route B1 d/theta scout; no J1/J2 swap; no finite-patch dipole FDTD",
                **{k: fnum(v) if isinstance(v, float) else v for k, v in g.items()},
            })
    return rows


def add_pillars(fdtd: object, d_nm: float, theta_deg: float) -> None:
    c = centers(d_nm, theta_deg)
    for role in [J1, J2]:
        x_nm, y_nm = c[role["role"]]
        fdtd.addrect()
        fdtd.set("name", f"{role['role']}_pillar")
        fdtd.set("x", x_nm * NM)
        fdtd.set("y", y_nm * NM)
        fdtd.set("x span", role["length_nm"] * NM)
        fdtd.set("y span", role["width_nm"] * NM)
        fdtd.set("z min", 0)
        fdtd.set("z max", role["height_nm"] * NM)
        fdtd.set("first axis", "z")
        fdtd.set("rotation 1", role["rotation_deg"])
        fdtd.set("material", "<Object defined dielectric>")
        fdtd.set("index", MATERIAL_INDEX)


def build_model(fdtd: object, d_nm: float, theta_deg: float, linear_input: str, sim_time_fs: float, mesh_accuracy: int) -> None:
    fdtd.switchtolayout()
    fdtd.deleteall()
    fdtd.addfdtd()
    fdtd.set("dimension", "3D")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z min", Z_MIN_NM * NM)
    fdtd.set("z max", Z_MAX_NM * NM)
    fdtd.set("x min bc", "Periodic")
    fdtd.set("x max bc", "Periodic")
    fdtd.set("y min bc", "Periodic")
    fdtd.set("y max bc", "Periodic")
    fdtd.set("z min bc", "PML")
    fdtd.set("z max bc", "PML")
    fdtd.set("mesh accuracy", int(mesh_accuracy))
    fdtd.set("simulation time", sim_time_fs * 1e-15)
    add_pillars(fdtd, d_nm, theta_deg)
    fdtd.addplane()
    fdtd.set("name", "source")
    fdtd.set("injection axis", "z")
    fdtd.set("direction", "Forward")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", SOURCE_Z_NM * NM)
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)
    fdtd.set("polarization angle", 0.0 if linear_input == "x" else 90.0)
    fdtd.addpower()
    fdtd.set("name", POWER_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)
    fdtd.addprofile()
    fdtd.set("name", FIELD_MONITOR)
    fdtd.set("monitor type", "2D Z-normal")
    fdtd.set("x span", PERIOD_X_NM * NM)
    fdtd.set("y span", PERIOD_Y_NM * NM)
    fdtd.set("z", MONITOR_Z_NM * NM)


def fsp_complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 10_000_000


def run_one(lumapi: Any, runtime: Any, out_dir: Path, d_nm: float, theta_deg: float, linear_input: str, sim_time_fs: float, mesh_accuracy: int, show_gui: bool, dry_run: bool, force: bool) -> dict[str, Any]:
    cid = candidate_id(d_nm, theta_deg)
    fsp = out_dir / "_saved_fsp" / f"{cid}_{linear_input.upper()}IN.fsp"
    if fsp_complete(fsp) and not force:
        return {"candidate_id": cid, "d_nm": d_nm, "theta_deg": theta_deg, "linear_input": linear_input, "fdtd_status": "reused", "result_fsp": str(fsp), "note": "existing completed FSP reused"}
    if dry_run:
        return {"candidate_id": cid, "d_nm": d_nm, "theta_deg": theta_deg, "linear_input": linear_input, "fdtd_status": "not_run", "result_fsp": str(fsp), "note": "dry run"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        build_model(fdtd, d_nm, theta_deg, linear_input, sim_time_fs, mesh_accuracy)
        fdtd.save(str(fsp.resolve()))
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        fdtd.run()
        fdtd.save(str(fsp.resolve()))
        return {"candidate_id": cid, "d_nm": d_nm, "theta_deg": theta_deg, "linear_input": linear_input, "fdtd_status": "ok", "result_fsp": str(fsp), "note": "setup/save/load/run/save lifecycle complete"}
    except Exception as exc:
        return {"candidate_id": cid, "d_nm": d_nm, "theta_deg": theta_deg, "linear_input": linear_input, "fdtd_status": "failed", "result_fsp": str(fsp), "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def extract_mean_ex_ey(fdtd: object) -> tuple[complex, complex, dict[str, Any]]:
    result = fdtd.getresult(FIELD_MONITOR, "E")
    meta: dict[str, Any] = {"monitor": FIELD_MONITOR}
    if isinstance(result, dict):
        meta["keys"] = list(map(str, result.keys()))
        if "Ex" in result and "Ey" in result:
            ex = np.asarray(result["Ex"], dtype=np.complex128).squeeze()
            ey = np.asarray(result["Ey"], dtype=np.complex128).squeeze()
        elif "E" in result:
            arr = np.asarray(result["E"], dtype=np.complex128).squeeze()
            if arr.shape[-1] >= 2:
                ex, ey = arr[..., 0], arr[..., 1]
            elif arr.shape[0] >= 2:
                ex, ey = arr[0, ...], arr[1, ...]
            else:
                raise ValueError(f"Cannot infer Ex/Ey from E shape {arr.shape}")
        else:
            raise ValueError(f"E result has no Ex/Ey/E keys; keys={meta['keys']}")
    else:
        arr = np.asarray(result, dtype=np.complex128).squeeze()
        if arr.shape[-1] >= 2:
            ex, ey = arr[..., 0], arr[..., 1]
        elif arr.shape[0] >= 2:
            ex, ey = arr[0, ...], arr[1, ...]
        else:
            raise ValueError(f"Cannot infer Ex/Ey from result shape {arr.shape}")
    meta["Ex_shape"] = list(np.asarray(ex).shape)
    meta["Ey_shape"] = list(np.asarray(ey).shape)
    return complex(np.mean(ex)), complex(np.mean(ey)), meta


def extract_linear_fields(lumapi: Any, runtime: Any, fsp: Path, show_gui: bool) -> tuple[str, complex | None, complex | None, dict[str, Any]]:
    if not fsp.exists():
        return "missing", None, None, {"note": "missing FSP"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=(not show_gui) and runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, meta = extract_mean_ex_ey(fdtd)
        return "ok", ex, ey, meta
    except Exception as exc:
        return "failed", None, None, {"note": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def cp_matrix_from_linear(j: np.ndarray) -> np.ndarray:
    s = math.sqrt(2.0)
    a = np.array([[1 / s, -1j / s], [1 / s, 1j / s]], dtype=np.complex128)
    b = np.array([[1 / s, 1 / s], [1j / s, -1j / s]], dtype=np.complex128)
    return a @ j @ b


def build_metrics_for_candidate(lumapi: Any, runtime: Any, out_dir: Path, d_nm: float, theta_deg: float, show_gui: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    cid = candidate_id(d_nm, theta_deg)
    fsp_x = out_dir / "_saved_fsp" / f"{cid}_XIN.fsp"
    fsp_y = out_dir / "_saved_fsp" / f"{cid}_YIN.fsp"
    sx, exx, eyx, meta_x = extract_linear_fields(lumapi, runtime, fsp_x, show_gui)
    sy, exy, eyy, meta_y = extract_linear_fields(lumapi, runtime, fsp_y, show_gui)
    if sx != "ok" or sy != "ok" or exx is None or eyx is None or exy is None or eyy is None:
        return {
            "candidate_id": cid,
            "d_nm": fnum(d_nm),
            "theta_deg": fnum(theta_deg),
            "psi_deg": fnum(PSI_DEG),
            "status": "missing_or_failed",
            "DoCP_RminusL_for_Rin": "",
            "L_fraction_for_Rin": "",
            "IR_Rin": "",
            "IL_Rin": "",
            "IR_Lin": "",
            "IL_Lin": "",
            "target_to_Rin_opposite_ratio": "",
            "target_to_all_other_ratio": "",
            "pass_soft_thresholds": "no",
            "note": f"x={sx}; y={sy}",
        }, {"x": meta_x, "y": meta_y}
    j = np.array([[exx, exy], [eyx, eyy]], dtype=np.complex128)
    cp = cp_matrix_from_linear(j)
    ir_r = float(abs(cp[0, 0]) ** 2)
    il_r = float(abs(cp[1, 0]) ** 2)
    ir_l = float(abs(cp[0, 1]) ** 2)
    il_l = float(abs(cp[1, 1]) ** 2)
    total_r = ir_r + il_r
    docp_r = (ir_r - il_r) / total_r if total_r else float("nan")
    lfrac_r = il_r / total_r if total_r else float("nan")
    ratio_same = il_r / ir_r if ir_r else float("inf")
    all_other = ir_r + ir_l + il_l
    ratio_all = il_r / all_other if all_other else float("inf")
    passed = docp_r < -0.8 and il_r > 0.3 and ratio_same > 20.0
    return {
        "candidate_id": cid,
        "d_nm": fnum(d_nm),
        "theta_deg": fnum(theta_deg),
        "psi_deg": fnum(PSI_DEG),
        "status": "ok",
        "DoCP_RminusL_for_Rin": fnum(docp_r),
        "L_fraction_for_Rin": fnum(lfrac_r),
        "IR_Rin": fnum(ir_r),
        "IL_Rin": fnum(il_r),
        "IR_Lin": fnum(ir_l),
        "IL_Lin": fnum(il_l),
        "target_to_Rin_opposite_ratio": fnum(ratio_same),
        "target_to_all_other_ratio": fnum(ratio_all),
        "pass_soft_thresholds": "yes" if passed else "no",
        "note": "T_output,input CP matrix from x/y periodic plane-wave runs; target is R_in -> L_out",
    }, {"x": meta_x, "y": meta_y, "J_linear": [[cstr(v) for v in row] for row in j], "J_cp": [[cstr(v) for v in row] for row in cp]}


def read_baseline_reference() -> dict[str, Any] | None:
    if not BASELINE_METRICS.exists():
        return None
    with BASELINE_METRICS.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    rrow = next((r for r in rows if r.get("structure") == "frozen_dimer" and r.get("input_label") == "R"), None)
    lrow = next((r for r in rows if r.get("structure") == "frozen_dimer" and r.get("input_label") == "L"), None)
    if not rrow:
        return None
    return {
        "candidate_id": "BASELINE_D182p5_T70_PSI97p5_H525",
        "d_nm": fnum(BASELINE_D_NM),
        "theta_deg": fnum(BASELINE_THETA_DEG),
        "psi_deg": fnum(PSI_DEG),
        "status": "baseline_reference_from_existing_planewave_control",
        "DoCP_RminusL_for_Rin": rrow.get("DoCP_RminusL", ""),
        "L_fraction_for_Rin": str((1.0 - float(rrow.get("DoCP_RminusL", "nan"))) / 2.0) if rrow.get("DoCP_RminusL") else "",
        "IR_Rin": rrow.get("IR_out", ""),
        "IL_Rin": rrow.get("IL_out", ""),
        "IR_Lin": lrow.get("IR_out", "") if lrow else "",
        "IL_Lin": lrow.get("IL_out", "") if lrow else "",
        "target_to_Rin_opposite_ratio": rrow.get("conversion_ratio_dominant_to_opposite", ""),
        "target_to_all_other_ratio": "",
        "pass_soft_thresholds": "yes",
        "note": "baseline reference read from existing calibrated +z plane-wave control; not rerun in Route B1",
    }


def rank_candidates(metrics: list[dict[str, Any]], geom_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    geom = {r["candidate_id"]: r for r in geom_rows}
    baseline_xbias = abs(BASELINE_D_NM * math.cos(math.radians(BASELINE_THETA_DEG)))
    ranked: list[dict[str, Any]] = []
    for m in metrics:
        if m.get("status") != "ok":
            continue
        cid = m["candidate_id"]
        g = geom.get(cid)
        if not g:
            continue
        il = float(m["IL_Rin"])
        docp = float(m["DoCP_RminusL_for_Rin"])
        ratio = float(m["target_to_Rin_opposite_ratio"])
        xbias = float(g["x_bias_abs_nm"])
        cp_quality = il * max(0.0, -docp) * math.log10(max(ratio, 1.0) + 1.0)
        geometry_factor = 1.0 / (1.0 + xbias / max(baseline_xbias, 1e-9))
        score = cp_quality * geometry_factor
        ranked.append({
            "candidate_id": cid,
            "d_nm": m["d_nm"],
            "theta_deg": m["theta_deg"],
            "psi_deg": m["psi_deg"],
            "DoCP_RminusL_for_Rin": m["DoCP_RminusL_for_Rin"],
            "L_fraction_for_Rin": m["L_fraction_for_Rin"],
            "IL_Rin_target": m["IL_Rin"],
            "target_to_Rin_opposite_ratio": m["target_to_Rin_opposite_ratio"],
            "target_to_all_other_ratio": m["target_to_all_other_ratio"],
            "x_bias_abs_nm": g["x_bias_abs_nm"],
            "plus_nearer_role": g["plus_nearer_role"],
            "minus_nearer_role": g["minus_nearer_role"],
            "soft_pass": m["pass_soft_thresholds"],
            "combined_score": fnum(score),
            "recommendation_reason": "strong R_in->L_out and reduced x-bias" if xbias < baseline_xbias and m["pass_soft_thresholds"] == "yes" else "screening reference",
        })
    ranked.sort(key=lambda r: float(r["combined_score"]), reverse=True)
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return ranked


def write_summary(out_dir: Path, baseline: dict[str, Any] | None, ranked: list[dict[str, Any]], geom_rows: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    baseline_xbias = abs(BASELINE_D_NM * math.cos(math.radians(BASELINE_THETA_DEG)))
    ok_runs = [r for r in run_rows if r["fdtd_status"] in {"ok", "reused"}]
    top3 = ranked[:3]
    def row_line(r: dict[str, Any]) -> str:
        return f"| {r['rank']} | {r['candidate_id']} | {r['d_nm']} | {r['theta_deg']} | {r['DoCP_RminusL_for_Rin']} | {r['L_fraction_for_Rin']} | {r['IL_Rin_target']} | {r['target_to_Rin_opposite_ratio']} | {r['x_bias_abs_nm']} | {r['recommendation_reason']} |\n"
    lines = []
    lines.append("# Stage10 CP Route B1 d/theta periodic plane-wave scout\n\n")
    lines.append("## English\n\n")
    lines.append("- Route: B1, local d/theta scout around the frozen J1/J2 dimer.\n")
    lines.append("- Finite-patch dipole FDTD: not run. No x_plus_qp/x_minus_qp finite-patch cases were run.\n")
    lines.append("- Periodic plane-wave screening: x/y linear inputs were run or reused and converted to the calibrated +z CP basis, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).\n")
    lines.append(f"- Candidate count: 12 d/theta candidates; successful/reused periodic linear FDTD files: {len(ok_runs)} of 24.\n")
    lines.append("- Why d/theta first: increasing theta toward 90 deg reduces the x projection of J1/J2 separation, which should reduce +q/-q source preference for different Jones-response roles.\n")
    lines.append("- L_fraction relation: L_fraction=(1-DoCP_RminusL)/2. More negative DoCP_RminusL means stronger L-output dominance.\n")
    if baseline:
        lines.append(f"- Baseline plane-wave reference: DoCP_RminusL_for_Rin={baseline['DoCP_RminusL_for_Rin']}, L_fraction_for_Rin={baseline['L_fraction_for_Rin']}, IL_Rin={baseline['IL_Rin']}, target/opposite ratio={baseline['target_to_Rin_opposite_ratio']}.\n")
    lines.append(f"- Baseline geometry x_bias_abs_nm={baseline_xbias:.6f}.\n\n")
    lines.append("### Top candidates\n\n")
    lines.append("| rank | candidate_id | d | theta | DoCP_RminusL_for_Rin | L_fraction_for_Rin | target L output | target/opposite ratio | x_bias_abs_nm | reason |\n")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for r in top3:
        lines.append(row_line(r))
    near90 = [r for r in ranked if float(r["theta_deg"]) >= 85 and r["soft_pass"] == "yes"]
    lines.append(f"\n- Theta near 90 deg preserving plane-wave function: {'yes' if near90 else 'not under the soft thresholds in this scout'}.\n")
    if top3:
        lines.append(f"- Recommended Route B2 finite-patch test: {top3[0]['candidate_id']} with x_plus_qp_x and x_plus_qp_y only; optionally {top3[1]['candidate_id']} if one backup is desired. Do not run them in B1.\n")
    lines.append("\n## 中文\n\n")
    lines.append("- 路线：B1，围绕 frozen J1/J2 dimer 的局部 d/theta scout。\n")
    lines.append("- 有限阵列偶极 FDTD：没有运行。本任务没有运行新的 x_plus_qp/x_minus_qp 有限阵列偶极 case。\n")
    lines.append("- 周期平面波筛选：运行或复用 x/y 线偏振入射，再转换到校准后的 +z CP 基底 R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)。\n")
    lines.append(f"- 候选数量：12 个 d/theta 候选；成功/复用的周期线偏振 FDTD 文件：{len(ok_runs)} / 24。\n")
    lines.append("- 为什么先扫 d/theta：theta 靠近 90 deg 会减小 J1/J2 分离向量的 x 投影，预计降低 +q/-q 对不同 Jones 响应柱的偏置激发。\n")
    lines.append("- L_fraction 关系：L_fraction=(1-DoCP_RminusL)/2。DoCP_RminusL 越负，L 输出占优越强。\n")
    if baseline:
        lines.append(f"- baseline 平面波参考：DoCP_RminusL_for_Rin={baseline['DoCP_RminusL_for_Rin']}, L_fraction_for_Rin={baseline['L_fraction_for_Rin']}, IL_Rin={baseline['IL_Rin']}, target/opposite ratio={baseline['target_to_Rin_opposite_ratio']}。\n")
    lines.append(f"- baseline 几何 x_bias_abs_nm={baseline_xbias:.6f}。\n\n")
    lines.append("### Top 候选\n\n")
    lines.append("| rank | candidate_id | d | theta | DoCP_RminusL_for_Rin | L_fraction_for_Rin | target L output | target/opposite ratio | x_bias_abs_nm | reason |\n")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---:|---:|---|\n")
    for r in top3:
        lines.append(row_line(r))
    lines.append(f"\n- theta 接近 90 deg 是否保持平面波 CP 功能：{'是' if near90 else '本轮 soft threshold 下没有明确通过'}。\n")
    if top3:
        lines.append(f"- 推荐 Route B2 有限阵列测试：优先 {top3[0]['candidate_id']}，只跑 x_plus_qp_x 和 x_plus_qp_y；如需备选，再考虑 {top3[1]['candidate_id']}。B1 本轮不运行它们。\n")
    (out_dir / "route_b1_summary.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.output_dir)
    ensure_dirs(out_dir)
    cand_rows = candidate_rows()
    write_csv(out_dir / "route_b1_candidates.csv", cand_rows)
    geom_rows = []
    for c in cand_rows:
        geom_rows.append({k: c[k] for k in ["candidate_id", "d_nm", "theta_deg", "psi_deg", "J1_x_nm", "J1_y_nm", "J2_x_nm", "J2_y_nm", "delta_x_J2_minus_J1_nm", "delta_y_J2_minus_J1_nm", "x_bias_abs_nm", "center_distance_to_J1_nm", "center_distance_to_J2_nm", "plus_distance_to_J1_nm", "plus_distance_to_J2_nm", "minus_distance_to_J1_nm", "minus_distance_to_J2_nm", "plus_nearer_role", "minus_nearer_role"]})
    write_csv(out_dir / "route_b1_geometry_bias_metrics.csv", geom_rows)
    runtime = load_runtime_config(args.runtime)
    lumapi = import_lumapi(runtime)
    run_rows: list[dict[str, Any]] = []
    for d in D_LIST:
        for theta in THETA_LIST:
            for lin in ["x", "y"]:
                run_rows.append(run_one(lumapi, runtime, out_dir, d, theta, lin, args.simulation_time_fs, args.mesh_accuracy, args.show_gui, args.dry_run, args.force))
    metrics: list[dict[str, Any]] = []
    extract_debug: dict[str, Any] = {}
    if not args.dry_run:
        for d in D_LIST:
            for theta in THETA_LIST:
                m, dbg = build_metrics_for_candidate(lumapi, runtime, out_dir, d, theta, args.show_gui)
                metrics.append(m)
                extract_debug[m["candidate_id"]] = dbg
    else:
        for d in D_LIST:
            for theta in THETA_LIST:
                metrics.append({"candidate_id": candidate_id(d, theta), "d_nm": fnum(d), "theta_deg": fnum(theta), "psi_deg": fnum(PSI_DEG), "status": "not_run", "DoCP_RminusL_for_Rin": "", "L_fraction_for_Rin": "", "IR_Rin": "", "IL_Rin": "", "IR_Lin": "", "IL_Lin": "", "target_to_Rin_opposite_ratio": "", "target_to_all_other_ratio": "", "pass_soft_thresholds": "no", "note": "dry run"})
    baseline = read_baseline_reference()
    metrics_with_baseline = ([baseline] if baseline else []) + metrics
    write_csv(out_dir / "route_b1_plane_wave_metrics.csv", metrics_with_baseline)
    ranked = rank_candidates(metrics, geom_rows)
    write_csv(out_dir / "route_b1_ranked_candidates.csv", ranked)
    write_summary(out_dir, baseline, ranked, geom_rows, run_rows)
    debug = {
        "route": "B1",
        "no_finite_patch_dipole_fdtd": True,
        "periodic_planewave_linear_runs": len(run_rows),
        "run_rows": run_rows,
        "extract_debug": extract_debug,
        "baseline_reference_source": str(BASELINE_METRICS),
        "cp_convention": "R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)",
        "ranking_note": "combined score weights plane-wave target strength and smaller x_bias_abs_nm; use as scout guidance only",
    }
    (out_dir / "route_b1_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir), "candidate_count": len(cand_rows), "run_rows": len(run_rows), "ranked_top3": ranked[:3]}, indent=2))
    failed = [r for r in run_rows if r["fdtd_status"] not in {"ok", "reused", "not_run"}]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
