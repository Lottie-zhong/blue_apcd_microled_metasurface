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
sys.path.insert(0, str(ROOT / 'src'))
from metasurface.lumapi_runner import import_lumapi
import stage10_cp_route_b2_finite_patch_xplus_test as b2

OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_center_spectral_run"
SMOKE_453 = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_smoke_run" / "stage10_cp_dipole_bw2a_smoke_incoherent_summary.csv"
SAVED_DIR = OUT_DIR / "_runtime_fsp_artifacts_not_for_git"
SETUP_DIR = SAVED_DIR / "setup"
RESULT_DIR = SAVED_DIR / "results"
GRID_N = 101
CONES = [5.0, 10.0, 20.0]
WAVELENGTHS = [447.0, 448.0, 450.0, 454.0]
SIM_TIME_FS = 100.0

CANDIDATES: dict[str, dict[str, Any]] = {
    "BW2_J1J2_D194_T90_PSI99_H525": {
        "role": "primary robust CP candidate; all-band BW2 repair",
        "J1_rotation_deg": -9.0,
        "J2_rotation_deg": 36.0,
        "J1_y_nm": 97.0,
        "J2_y_nm": -97.0,
    },
    "BW2_J1J2_D194_T90_PSI97_H525": {
        "role": "baseline B4INT notch reference",
        "J1_rotation_deg": -7.0,
        "J2_rotation_deg": 38.0,
        "J1_y_nm": 97.0,
        "J2_y_nm": -97.0,
    },
}


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


def patch_candidate(candidate_id: str, wavelength_nm: float) -> None:
    c = CANDIDATES[candidate_id]
    b2.WAVELENGTH_NM = wavelength_nm
    b2.J_ROLES = [
        {"role": "J1", "length_nm": 230.0, "width_nm": 100.0, "height_nm": 525.0, "rotation_deg": c["J1_rotation_deg"], "center_x_nm": 0.0, "center_y_nm": c["J1_y_nm"]},
        {"role": "J2", "length_nm": 180.0, "width_nm": 90.0, "height_nm": 525.0, "rotation_deg": c["J2_rotation_deg"], "center_x_nm": 0.0, "center_y_nm": c["J2_y_nm"]},
    ]


def planned_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wavelength_nm in WAVELENGTHS:
        for candidate_id in CANDIDATES:
            for dip in ["x", "y"]:
                rows.append({
                    "case_id": f"BW2A_SPEC_{candidate_id}_{int(wavelength_nm)}NM_CENTER_{dip.upper()}DIP",
                    "candidate_id": candidate_id,
                    "wavelength_nm": wavelength_nm,
                    "source_position_label": "center",
                    "position_id": "center",
                    "x_nm": 0.0,
                    "y_nm": 0.0,
                    "z_nm": b2.SOURCE_Z_NM,
                    "orientation": dip,
                    "enabled_source": b2.X_SOURCE if dip == "x" else b2.Y_SOURCE,
                    "disabled_source": b2.Y_SOURCE if dip == "x" else b2.X_SOURCE,
                    "theta_deg": 90.0,
                    "phi_deg": 0.0 if dip == "x" else 90.0,
                })
    if len(rows) != 16:
        raise RuntimeError(f"Refusing to run: expected exactly 16 cases, got {len(rows)}")
    return rows


def build_setups(lumapi: Any, runtime: Any, cases: list[dict[str, Any]]) -> dict[tuple[str, float], Path]:
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    setup_paths: dict[tuple[str, float], Path] = {}
    for key in sorted({(c["candidate_id"], float(c["wavelength_nm"])) for c in cases}):
        candidate_id, wavelength_nm = key
        patch_candidate(candidate_id, wavelength_nm)
        setup = SETUP_DIR / f"{candidate_id}_{int(wavelength_nm)}NM_setup_prepared_not_run.fsp"
        fdtd = None
        try:
            fdtd = lumapi.FDTD(hide=runtime.hide_gui)
            warnings, inventory = b2.build_setup(fdtd, SIM_TIME_FS)
            fdtd.save(str(setup.resolve()))
            write_csv(OUT_DIR / f"{candidate_id}_{int(wavelength_nm)}NM_patch_inventory.csv", inventory)
            if warnings:
                (OUT_DIR / f"{candidate_id}_{int(wavelength_nm)}NM_setup_warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
            setup_paths[key] = setup
        finally:
            if fdtd is not None:
                try: fdtd.close()
                except Exception: pass
    return setup_paths


def run_one(lumapi: Any, runtime: Any, setup_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    case_dir = RESULT_DIR / case["candidate_id"] / f"{int(case['wavelength_nm'])}nm"
    case_dir.mkdir(parents=True, exist_ok=True)
    old_saved = b2.SAVED_FSP_DIR
    b2.SAVED_FSP_DIR = case_dir
    try:
        row = b2.run_case(lumapi, runtime, setup_path, case, SIM_TIME_FS, False, False)
    finally:
        b2.SAVED_FSP_DIR = old_saved
    row.update({"candidate_id": case["candidate_id"], "wavelength_nm": case["wavelength_nm"]})
    return row


def extract_case(lumapi: Any, runtime: Any, case: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fsp = RESULT_DIR / case["candidate_id"] / f"{int(case['wavelength_nm'])}nm" / f"{case['case_id']}.fsp"
    base = {"candidate_id": case["candidate_id"], "wavelength_nm": case["wavelength_nm"], "source_position_label": "center",
                    "position_id": "center", "source_x_nm": 0.0, "source_y_nm": 0.0, "dipole_axis": case["orientation"], "result_csv": str(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_case_results.csv")}
    if not fsp.exists():
        return [{**base, "cone_half_angle_deg": cone, "status": "missing_fsp"} for cone in CONES], {"case_id": case["case_id"], "status": "missing_fsp"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, ux, uy, info = b2.extract_fields(fdtd, GRID_N)
        er = (ex - 1j * ey) / math.sqrt(2.0)
        el = (ex + 1j * ey) / math.sqrt(2.0)
        ux_arr = np.asarray(ux, dtype=float).squeeze(); uy_arr = np.asarray(uy, dtype=float).squeeze()
        xx, yy = np.meshgrid(ux_arr, uy_arr, indexing="ij") if ux_arr.ndim == 1 and uy_arr.ndim == 1 else np.broadcast_arrays(ux_arr, uy_arr)
        total_grid = np.abs(er) ** 2 + np.abs(el) ** 2
        peak_idx = np.unravel_index(int(np.nanargmax(total_grid)), total_grid.shape)
        peak_u = math.sqrt(float(xx[peak_idx]) ** 2 + float(yy[peak_idx]) ** 2) if xx.shape == total_grid.shape else float("nan")
        peak_abs_theta_deg = math.degrees(math.asin(max(-1.0, min(1.0, peak_u)))) if math.isfinite(peak_u) else float("nan")
        rows: list[dict[str, Any]] = []
        for cone in CONES:
            mask = b2.mask_for(ux, uy, er.shape, cone).astype(bool)
            r_power = float(np.sum(np.abs(er[mask]) ** 2)); l_power = float(np.sum(np.abs(el[mask]) ** 2)); total = r_power + l_power
            rows.append({**base, "cone_half_angle_deg": cone, "R_power": r_power, "L_power": l_power, "L_fraction": l_power / total if total else float("nan"), "DoCP_RminusL": (r_power - l_power) / total if total else float("nan"), "total_cone_power": total, "peak_abs_theta_deg": peak_abs_theta_deg, "status": "ok"})
        return rows, {"case_id": case["case_id"], "status": "ok", "array_info": info, "fsp": str(fsp)}
    except Exception as exc:
        return [{**base, "cone_half_angle_deg": cone, "status": f"extract_failed:{type(exc).__name__}:{exc}"} for cone in CONES], {"case_id": case["case_id"], "status": "extract_failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try: fdtd.close()
            except Exception: pass


def incoherent(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [r for r in case_rows if r.get("status") == "ok"]
    out: list[dict[str, Any]] = []
    for candidate_id in sorted({r["candidate_id"] for r in ok}):
        for wl in sorted({float(r["wavelength_nm"]) for r in ok if r["candidate_id"] == candidate_id}):
            for cone in CONES:
                subset = [r for r in ok if r["candidate_id"] == candidate_id and float(r["wavelength_nm"]) == wl and float(r["cone_half_angle_deg"]) == cone]
                if len(subset) != 2 or {r["dipole_axis"] for r in subset} != {"x", "y"}:
                    out.append({"candidate_id": candidate_id, "wavelength_nm": wl, "source_position_label": "center",
                    "position_id": "center", "cone_half_angle_deg": cone, "status": "missing_pair"}); continue
                r_sum = sum(float(r["R_power"]) for r in subset); l_sum = sum(float(r["L_power"]) for r in subset); total = r_sum + l_sum
                out.append({"candidate_id": candidate_id, "wavelength_nm": wl, "source_position_label": "center",
                    "position_id": "center", "cone_half_angle_deg": cone, "R_power_incoh": r_sum, "L_power_incoh": l_sum, "L_fraction_incoh": l_sum / total if total else float("nan"), "DoCP_RminusL_incoh": (r_sum - l_sum) / total if total else float("nan"), "total_cone_power_incoh": total, "status": "ok", "data_source": "new_spectral_run"})
    return out


def read_existing_453() -> list[dict[str, Any]]:
    if not SMOKE_453.exists(): return []
    rows: list[dict[str, Any]] = []
    with SMOKE_453.open(newline="", encoding="utf-8") as h:
        for r in csv.DictReader(h):
            rows.append({"candidate_id": r["candidate_id"], "wavelength_nm": float(r["wavelength_nm"]), "source_position_label": r["source_position_label"], "cone_half_angle_deg": float(r["cone_half_angle_deg"]), "R_power_incoh": float(r["R_power_incoh"]), "L_power_incoh": float(r["L_power_incoh"]), "L_fraction_incoh": float(r["L_fraction_incoh"]), "DoCP_RminusL_incoh": float(r["DoCP_RminusL_incoh"]), "total_cone_power_incoh": float(r["total_cone_power_incoh"]), "status": r["status"], "data_source": "reused_existing_453_data"})
    return rows


def report(avg_rows: list[dict[str, Any]], combined: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    lines = ["# Stage10 CP BW2A center spectral dipole run\n\n", "- Scope: center-only no-DBR ordinary MicroLED dipole wavelength scan.\n", "- New FDTD cases: 16 exactly. No +/-q, no 453 rerun, no 36-case run, no DBR/RCLED/MQW/mirrors/spacer.\n", "- CP basis: +z transverse Ex/Ey, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). L_out dominance means DoCP_RminusL < 0.\n\n"]
    for candidate_id in sorted({r["candidate_id"] for r in combined}):
        lines.append(f"## {candidate_id}\n")
        for cone in CONES:
            vals = [r for r in combined if r["candidate_id"] == candidate_id and float(r["cone_half_angle_deg"]) == cone]
            vals = sorted(vals, key=lambda r: float(r["wavelength_nm"]))
            lines.append(f"- {cone:g} deg L_fraction vs wavelength: " + ", ".join(f"{float(v['wavelength_nm']):g}nm={float(v['L_fraction_incoh']):.6f}" for v in vals) + "\n")
        vals20 = [r for r in combined if r["candidate_id"] == candidate_id and float(r["cone_half_angle_deg"]) == 20.0]
        worst = min(vals20, key=lambda r: float(r["L_fraction_incoh"])) if vals20 else None
        if worst:
            lines.append(f"- Worst 20 deg L_fraction: {float(worst['wavelength_nm']):g} nm, {float(worst['L_fraction_incoh']):.6f}, source={worst.get('data_source','')}.\n")
        ok = all(float(r["L_fraction_incoh"]) > 0.5 and float(r["DoCP_RminusL_incoh"]) < 0 for r in vals20)
        lines.append(f"- L_out dominant at all 20 deg scanned/reference wavelengths: {'yes' if ok else 'no'}.\n\n")
    psi99 = [r for r in combined if r["candidate_id"].endswith("PSI99_H525") and float(r["cone_half_angle_deg"]) == 20.0]
    psi97 = [r for r in combined if r["candidate_id"].endswith("PSI97_H525") and float(r["cone_half_angle_deg"]) == 20.0]
    lines.append("## Interpretation\n")
    lines.append("- 447-448 nm notch risk should be judged by PSI99 vs PSI97 20 deg L_fraction and total cone power in the combined CSV.\n")
    if psi99 and psi97:
        w99 = min(psi99, key=lambda r: float(r["L_fraction_incoh"])); w97 = min(psi97, key=lambda r: float(r["L_fraction_incoh"]))
        lines.append(f"- PSI99 worst 20 deg row: {float(w99['wavelength_nm']):g} nm L_fraction={float(w99['L_fraction_incoh']):.6f}.\n")
        lines.append(f"- PSI97 worst 20 deg row: {float(w97['wavelength_nm']):g} nm L_fraction={float(w97['L_fraction_incoh']):.6f}.\n")
    (OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_run_report.md").write_text("".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True); SETUP_DIR.mkdir(parents=True, exist_ok=True); RESULT_DIR.mkdir(parents=True, exist_ok=True)
    cases = planned_cases()
    print(json.dumps({"planned_case_count": len(cases), "wavelengths": WAVELENGTHS, "candidates": list(CANDIDATES), "dipoles": ["x", "y"]}, indent=2))
    runtime = SimpleNamespace(lumapi_python_api_dir=r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python", hide_gui=True)
    lumapi = import_lumapi(runtime)
    setups = build_setups(lumapi, runtime, cases)
    run_rows: list[dict[str, Any]] = []; case_rows: list[dict[str, Any]] = []; debug: list[dict[str, Any]] = []
    for case in cases:
        patch_candidate(case["candidate_id"], float(case["wavelength_nm"]))
        run_rows.append(run_one(lumapi, runtime, setups[(case["candidate_id"], float(case["wavelength_nm"]))], case))
        rows, info = extract_case(lumapi, runtime, case); case_rows.extend(rows); debug.append(info)
    avg_rows = incoherent(case_rows)
    combined = sorted(avg_rows + read_existing_453(), key=lambda r: (r["candidate_id"], float(r["cone_half_angle_deg"]), float(r["wavelength_nm"])))
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_case_results.csv", case_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_incoherent_summary.csv", avg_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_combined_summary.csv", combined)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_run_table.csv", run_rows)
    summary = {"stage": "Stage10-CP-DIPOLE-BW2A-CENTER-SPECTRAL", "new_fdtd_cases_requested": 16, "new_fdtd_cases_completed_or_reused": sum(1 for r in run_rows if r.get("fdtd_status") in {"ok", "reused"}), "failed_cases": [r for r in run_rows if r.get("fdtd_status") not in {"ok", "reused"}], "extraction_ok_rows": sum(1 for r in case_rows if r.get("status") == "ok"), "wavelengths_nm": WAVELENGTHS, "cones_deg": CONES, "runtime_artifact_dir": str(SAVED_DIR), "no_dbr": True, "no_rcled": True, "no_mqw": True, "no_q_positions": True, "reused_existing_453": SMOKE_453.exists(), "extract_debug": debug}
    (OUT_DIR / "stage10_cp_dipole_bw2a_center_spectral_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report(avg_rows, combined, run_rows)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()


