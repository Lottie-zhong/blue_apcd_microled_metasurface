from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from metasurface.lumapi_runner import import_lumapi
import stage10_cp_route_b2_finite_patch_xplus_test as b2
import stage10_cp_dipole_bw2a_prepare_no_dbr_microled_xline as prep

OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_psi99_position_run"
SMOKE_453 = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_smoke_run" / "stage10_cp_dipole_bw2a_smoke_incoherent_summary.csv"
SAVED_DIR = OUT_DIR / "_runtime_fsp_artifacts_not_for_git"
SETUP_DIR = SAVED_DIR / "setup"
RESULT_DIR = SAVED_DIR / "results"
GRID_N = 101
CONES = [5.0, 10.0, 20.0]
SIM_TIME_FS = 100.0
WAVELENGTH_NM = 453.0
Q_NM = float(prep.Q_NM)
CANDIDATE_ID = "BW2_J1J2_D194_T90_PSI99_H525"


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


def patch_candidate() -> None:
    b2.WAVELENGTH_NM = WAVELENGTH_NM
    b2.J_ROLES = [
        {"role": "J1", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": -9.0, "center_x_nm": 0.0, "center_y_nm": 97.0},
        {"role": "J2", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": 36.0, "center_x_nm": 0.0, "center_y_nm": -97.0},
    ]


def positions() -> list[dict[str, Any]]:
    return [
        {"source_position_label": "center", "x_nm": 0.0, "y_nm": 0.0},
        {"source_position_label": "x_plus_q", "x_nm": Q_NM, "y_nm": 0.0},
        {"source_position_label": "x_minus_q", "x_nm": -Q_NM, "y_nm": 0.0},
    ]


def planned_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pos in positions():
        for dip in ["x", "y"]:
            rows.append({
                "case_id": f"BW2A_POS_{CANDIDATE_ID}_{int(WAVELENGTH_NM)}NM_{pos['source_position_label'].upper()}_{dip.upper()}DIP",
                "candidate_id": CANDIDATE_ID,
                "wavelength_nm": WAVELENGTH_NM,
                "source_position_label": pos["source_position_label"],
                "position_id": pos["source_position_label"],
                "x_nm": pos["x_nm"],
                "y_nm": pos["y_nm"],
                "z_nm": b2.SOURCE_Z_NM,
                "q_nm": Q_NM,
                "orientation": dip,
                "enabled_source": b2.X_SOURCE if dip == "x" else b2.Y_SOURCE,
                "disabled_source": b2.Y_SOURCE if dip == "x" else b2.X_SOURCE,
                "theta_deg": 90.0,
                "phi_deg": 0.0 if dip == "x" else 90.0,
            })
    if len(rows) != 6:
        raise RuntimeError(f"Refusing to run: expected exactly 6 cases, got {len(rows)}")
    return rows


def build_setup(lumapi: Any, runtime: Any) -> Path:
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    patch_candidate()
    setup = SETUP_DIR / f"{CANDIDATE_ID}_{int(WAVELENGTH_NM)}NM_setup_prepared_not_run.fsp"
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        warnings, inventory = b2.build_setup(fdtd, SIM_TIME_FS)
        fdtd.save(str(setup.resolve()))
        write_csv(OUT_DIR / f"{CANDIDATE_ID}_{int(WAVELENGTH_NM)}NM_patch_inventory.csv", inventory)
        write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_source_inventory.csv", [{"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "q_nm": Q_NM, **p} for p in positions()])
        if warnings:
            (OUT_DIR / f"{CANDIDATE_ID}_{int(WAVELENGTH_NM)}NM_setup_warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
        return setup
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def run_one(lumapi: Any, runtime: Any, setup_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    case_dir = RESULT_DIR / case["source_position_label"]
    case_dir.mkdir(parents=True, exist_ok=True)
    old_saved = b2.SAVED_FSP_DIR
    b2.SAVED_FSP_DIR = case_dir
    try:
        row = b2.run_case(lumapi, runtime, setup_path, case, SIM_TIME_FS, False, False)
    finally:
        b2.SAVED_FSP_DIR = old_saved
    row.update({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "source_position_label": case["source_position_label"], "source_x_nm": case["x_nm"], "source_y_nm": case["y_nm"], "q_nm": Q_NM})
    return row


def extract_case(lumapi: Any, runtime: Any, case: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fsp = RESULT_DIR / case["source_position_label"] / f"{case['case_id']}.fsp"
    base = {"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "source_position_label": case["source_position_label"], "source_x_nm": case["x_nm"], "source_y_nm": case["y_nm"], "q_nm": Q_NM, "dipole_axis": case["orientation"], "result_csv": str(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_case_results.csv")}
    if not fsp.exists():
        return [{**base, "cone_half_angle_deg": cone, "status": "missing_fsp"} for cone in CONES], {"case_id": case["case_id"], "status": "missing_fsp"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, ux, uy, info = b2.extract_fields(fdtd, GRID_N)
        er = (ex - 1j * ey) / math.sqrt(2.0)
        el = (ex + 1j * ey) / math.sqrt(2.0)
        ux_arr = np.asarray(ux, dtype=float).squeeze()
        uy_arr = np.asarray(uy, dtype=float).squeeze()
        xx, yy = np.meshgrid(ux_arr, uy_arr, indexing="ij") if ux_arr.ndim == 1 and uy_arr.ndim == 1 else np.broadcast_arrays(ux_arr, uy_arr)
        total_grid = np.abs(er) ** 2 + np.abs(el) ** 2
        peak_idx = np.unravel_index(int(np.nanargmax(total_grid)), total_grid.shape)
        peak_u = math.sqrt(float(xx[peak_idx]) ** 2 + float(yy[peak_idx]) ** 2) if xx.shape == total_grid.shape else float("nan")
        peak_abs_theta_deg = math.degrees(math.asin(max(-1.0, min(1.0, peak_u)))) if math.isfinite(peak_u) else float("nan")
        rows: list[dict[str, Any]] = []
        for cone in CONES:
            mask = b2.mask_for(ux, uy, er.shape, cone).astype(bool)
            r_power = float(np.sum(np.abs(er[mask]) ** 2))
            l_power = float(np.sum(np.abs(el[mask]) ** 2))
            total = r_power + l_power
            rows.append({**base, "cone_half_angle_deg": cone, "R_power": r_power, "L_power": l_power, "L_fraction": l_power / total if total else float("nan"), "DoCP_RminusL": (r_power - l_power) / total if total else float("nan"), "total_cone_power": total, "peak_abs_theta_deg": peak_abs_theta_deg, "status": "ok"})
        return rows, {"case_id": case["case_id"], "status": "ok", "array_info": info, "fsp": str(fsp)}
    except Exception as exc:
        return [{**base, "cone_half_angle_deg": cone, "status": f"extract_failed:{type(exc).__name__}:{exc}"} for cone in CONES], {"case_id": case["case_id"], "status": "extract_failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def incoherent(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [r for r in case_rows if r.get("status") == "ok"]
    out: list[dict[str, Any]] = []
    for pos in ["center", "x_plus_q", "x_minus_q"]:
        for cone in CONES:
            subset = [r for r in ok if r["source_position_label"] == pos and float(r["cone_half_angle_deg"]) == cone]
            p = next((x for x in positions() if x["source_position_label"] == pos), {"x_nm": float("nan"), "y_nm": float("nan")})
            if len(subset) != 2 or {r["dipole_axis"] for r in subset} != {"x", "y"}:
                out.append({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "source_position_label": pos, "source_x_nm": p["x_nm"], "source_y_nm": p["y_nm"], "q_nm": Q_NM, "cone_half_angle_deg": cone, "status": "missing_pair"})
                continue
            r_sum = sum(float(r["R_power"]) for r in subset)
            l_sum = sum(float(r["L_power"]) for r in subset)
            total = r_sum + l_sum
            out.append({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "source_position_label": pos, "source_x_nm": p["x_nm"], "source_y_nm": p["y_nm"], "q_nm": Q_NM, "cone_half_angle_deg": cone, "R_power_incoh": r_sum, "L_power_incoh": l_sum, "L_fraction_incoh": l_sum / total if total else float("nan"), "DoCP_RminusL_incoh": (r_sum - l_sum) / total if total else float("nan"), "total_cone_power_incoh": total, "status": "ok"})
    return out


def read_existing_center() -> list[dict[str, Any]]:
    if not SMOKE_453.exists():
        return []
    rows: list[dict[str, Any]] = []
    with SMOKE_453.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("candidate_id") == CANDIDATE_ID and row.get("source_position_label") == "center":
                rows.append({**row, "data_source": "reused_existing_center_453_data"})
    return rows


def report(avg_rows: list[dict[str, Any]], existing_center: list[dict[str, Any]]) -> None:
    lines = ["# Stage10 CP BW2A PSI99 source-position run\n\n"]
    lines.append("- Scope: PSI99 only, 453 nm only, center/+q/-q x-line source positions, x/y dipoles.\n")
    lines.append("- No DBR/RCLED/MQW/top DBR/bottom mirror/spacer scan.\n")
    lines.append(f"- Resolved q_nm = {Q_NM:.6f}.\n")
    lines.append("- CP basis: +z transverse Ex/Ey, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). L_out dominance means DoCP_RminusL < 0.\n\n")
    for pos in ["center", "x_plus_q", "x_minus_q"]:
        lines.append(f"## {pos}\n")
        for r in sorted([x for x in avg_rows if x["source_position_label"] == pos], key=lambda x: float(x["cone_half_angle_deg"])):
            lines.append(f"- {float(r['cone_half_angle_deg']):g} deg: L_fraction={float(r['L_fraction_incoh']):.6f}, DoCP={float(r['DoCP_RminusL_incoh']):.6f}, P={float(r['total_cone_power_incoh']):.6g}.\n")
    rows20 = [r for r in avg_rows if float(r["cone_half_angle_deg"]) == 20.0]
    worst = min(rows20, key=lambda r: float(r["L_fraction_incoh"])) if rows20 else None
    lines.append("\n## Interpretation\n")
    if worst:
        lines.append(f"- Worst 20 deg source position: {worst['source_position_label']}, L_fraction={float(worst['L_fraction_incoh']):.6f}.\n")
    all_l = all(float(r["L_fraction_incoh"]) > 0.5 and float(r["DoCP_RminusL_incoh"]) < 0 for r in rows20)
    lines.append(f"- All 20 deg positions remain L_out dominant: {'yes' if all_l else 'no'}.\n")
    if existing_center:
        lines.append("- Existing 453 nm smoke center data was read for comparison and labeled reused_existing_center_453_data.\n")
    (OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_run_report.md").write_text("".join(lines), encoding="utf-8")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    cases = planned_cases()
    print(json.dumps({"candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "resolved_q_nm": Q_NM, "source_positions": positions(), "dipoles": ["x", "y"], "planned_case_count": len(cases)}, indent=2))
    runtime = SimpleNamespace(lumapi_python_api_dir=r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python", hide_gui=True)
    lumapi = import_lumapi(runtime)
    setup = build_setup(lumapi, runtime)
    run_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []
    for case in cases:
        patch_candidate()
        run_rows.append(run_one(lumapi, runtime, setup, case))
        rows, info = extract_case(lumapi, runtime, case)
        case_rows.extend(rows)
        debug.append(info)
    avg_rows = incoherent(case_rows)
    existing_center = read_existing_center()
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_case_results.csv", case_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_incoherent_summary.csv", avg_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_run_table.csv", run_rows)
    if existing_center:
        write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_existing_center_comparison.csv", existing_center)
    summary = {"stage": "Stage10-CP-DIPOLE-BW2A-PSI99-POSITION", "candidate_id": CANDIDATE_ID, "wavelength_nm": WAVELENGTH_NM, "resolved_q_nm": Q_NM, "new_fdtd_cases_requested": 6, "new_fdtd_cases_completed_or_reused": sum(1 for r in run_rows if r.get("fdtd_status") in {"ok", "reused"}), "failed_cases": [r for r in run_rows if r.get("fdtd_status") not in {"ok", "reused"}], "extraction_ok_rows": sum(1 for r in case_rows if r.get("status") == "ok"), "cones_deg": CONES, "runtime_artifact_dir": str(SAVED_DIR), "no_dbr": True, "no_rcled": True, "no_mqw": True, "only_psi99": True, "only_453_nm": True, "extract_debug": debug}
    (OUT_DIR / "stage10_cp_dipole_bw2a_psi99_position_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report(avg_rows, existing_center)
    print(json.dumps(summary, indent=2))
    return 1 if summary["failed_cases"] or summary["extraction_ok_rows"] != 18 else 0


if __name__ == "__main__":
    raise SystemExit(main())
