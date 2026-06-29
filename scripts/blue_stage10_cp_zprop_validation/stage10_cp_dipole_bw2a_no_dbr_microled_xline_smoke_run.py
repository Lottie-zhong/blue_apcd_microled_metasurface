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
PREP_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_smoke_prepare"
MANIFEST = PREP_DIR / "stage10_cp_dipole_bw2a_smoke_case_manifest.csv"
OUT_DIR = ROOT / "outputs" / "stage10_cp_dipole_bw2a_no_dbr_microled_xline_smoke_run"
SAVED_DIR = OUT_DIR / "_runtime_fsp_artifacts_not_for_git"
SETUP_DIR = SAVED_DIR / "setup"
RESULT_DIR = SAVED_DIR / "results"
GRID_N = 101
CONES = [5.0, 10.0, 20.0]
SIM_TIME_FS = 100.0

CANDIDATES: dict[str, dict[str, Any]] = {
    "BW2_J1J2_D194_T90_PSI99_H525": {
        "role": "primary robust CP candidate; all-band BW2 repair",
        "d_nm": 194.0,
        "theta_deg": 90.0,
        "psi_deg": 99.0,
        "J1_rotation_deg": -9.0,
        "J2_rotation_deg": 36.0,
        "J1_y_nm": 97.0,
        "J2_y_nm": -97.0,
    },
    "BW2_J1J2_D194_T90_PSI97_H525": {
        "role": "baseline B4INT notch reference",
        "d_nm": 194.0,
        "theta_deg": 90.0,
        "psi_deg": 97.0,
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


def read_manifest() -> list[dict[str, Any]]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"missing prepared manifest: {MANIFEST}")
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4:
        raise RuntimeError(f"Refusing to run: expected exactly 4 manifest rows, got {len(rows)}")
    allowed = set(CANDIDATES)
    for row in rows:
        if row["candidate_id"] not in allowed:
            raise RuntimeError(f"Unexpected candidate in manifest: {row['candidate_id']}")
        if float(row["wavelength_nm"]) != 453.0:
            raise RuntimeError(f"Unexpected wavelength: {row['wavelength_nm']}")
        if row["source_position_label"] != "center" or float(row["source_x_nm"]) != 0.0 or float(row["source_y_nm"]) != 0.0:
            raise RuntimeError(f"Unexpected source position: {row}")
        if row["dipole_axis"] not in {"x", "y"}:
            raise RuntimeError(f"Unexpected dipole axis: {row['dipole_axis']}")
    return rows


def patch_candidate(candidate_id: str) -> None:
    c = CANDIDATES[candidate_id]
    b2.WAVELENGTH_NM = 453.0
    b2.J_ROLES = [
        {
            "role": "J1",
            "length_nm": 230.0,
            "width_nm": 100.0,
            "height_nm": 525.0,
            "rotation_deg": c["J1_rotation_deg"],
            "center_x_nm": 0.0,
            "center_y_nm": c["J1_y_nm"],
        },
        {
            "role": "J2",
            "length_nm": 180.0,
            "width_nm": 90.0,
            "height_nm": 525.0,
            "rotation_deg": c["J2_rotation_deg"],
            "center_x_nm": 0.0,
            "center_y_nm": c["J2_y_nm"],
        },
    ]


def make_case(row: dict[str, Any]) -> dict[str, Any]:
    dip = row["dipole_axis"]
    candidate_id = row["candidate_id"]
    return {
        "case_id": row["expected_case_id"],
        "candidate_id": candidate_id,
        "position_id": row["source_position_label"],
        "orientation": dip,
        "x_nm": float(row["source_x_nm"]),
        "y_nm": float(row["source_y_nm"]),
        "z_nm": b2.SOURCE_Z_NM,
        "enabled_source": b2.X_SOURCE if dip == "x" else b2.Y_SOURCE,
        "disabled_source": b2.Y_SOURCE if dip == "x" else b2.X_SOURCE,
        "theta_deg": 90.0,
        "phi_deg": 0.0 if dip == "x" else 90.0,
        "wavelength_nm": float(row["wavelength_nm"]),
    }


def build_setups(lumapi: Any, runtime: Any, candidate_ids: list[str]) -> dict[str, Path]:
    setup_paths: dict[str, Path] = {}
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    for candidate_id in candidate_ids:
        patch_candidate(candidate_id)
        setup = SETUP_DIR / f"{candidate_id}_setup_prepared_not_run.fsp"
        fdtd = None
        try:
            fdtd = lumapi.FDTD(hide=runtime.hide_gui)
            warnings, inventory = b2.build_setup(fdtd, SIM_TIME_FS)
            fdtd.save(str(setup.resolve()))
            write_csv(OUT_DIR / f"{candidate_id}_patch_inventory.csv", inventory)
            setup_paths[candidate_id] = setup
            if warnings:
                (OUT_DIR / f"{candidate_id}_setup_warnings.txt").write_text("\n".join(warnings), encoding="utf-8")
        finally:
            if fdtd is not None:
                try:
                    fdtd.close()
                except Exception:
                    pass
    return setup_paths


def run_one(lumapi: Any, runtime: Any, setup_path: Path, case: dict[str, Any]) -> dict[str, Any]:
    candidate_dir = RESULT_DIR / case["candidate_id"]
    candidate_dir.mkdir(parents=True, exist_ok=True)
    old_saved = b2.SAVED_FSP_DIR
    b2.SAVED_FSP_DIR = candidate_dir
    try:
        row = b2.run_case(lumapi, runtime, setup_path, case, SIM_TIME_FS, False, False)
    finally:
        b2.SAVED_FSP_DIR = old_saved
    row["candidate_id"] = case["candidate_id"]
    row["wavelength_nm"] = case["wavelength_nm"]
    return row


def extract_case(lumapi: Any, runtime: Any, case: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fsp = RESULT_DIR / case["candidate_id"] / f"{case['case_id']}.fsp"
    base = {
        "candidate_id": case["candidate_id"],
        "wavelength_nm": case["wavelength_nm"],
        "source_position_label": case["position_id"],
        "source_x_nm": case["x_nm"],
        "source_y_nm": case["y_nm"],
        "dipole_axis": case["orientation"],
        "result_csv": str(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_case_results.csv"),
    }
    if not fsp.exists():
        return [{**base, "cone_half_angle_deg": cone, "status": "missing_fsp"} for cone in CONES], {"case_id": case["case_id"], "status": "missing_fsp"}
    fdtd = None
    try:
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        fdtd.load(str(fsp.resolve()))
        ex, ey, ux, uy, info = b2.extract_fields(fdtd, GRID_N)
        er = (ex - 1j * ey) / math.sqrt(2.0)
        el = (ex + 1j * ey) / math.sqrt(2.0)
        # peak angle proxy from total CP intensity on the far-field grid.
        ux_arr = np.asarray(ux, dtype=float).squeeze()
        uy_arr = np.asarray(uy, dtype=float).squeeze()
        if ux_arr.ndim == 1 and uy_arr.ndim == 1:
            xx, yy = np.meshgrid(ux_arr, uy_arr, indexing="ij")
        else:
            xx, yy = np.broadcast_arrays(ux_arr, uy_arr)
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
            rows.append({
                **base,
                "cone_half_angle_deg": cone,
                "R_power": r_power,
                "L_power": l_power,
                "L_fraction": l_power / total if total else float("nan"),
                "DoCP_RminusL": (r_power - l_power) / total if total else float("nan"),
                "total_cone_power": total,
                "peak_abs_theta_deg": peak_abs_theta_deg,
                "status": "ok",
            })
        return rows, {"case_id": case["case_id"], "status": "ok", "array_info": info, "fsp": str(fsp)}
    except Exception as exc:
        return [{**base, "cone_half_angle_deg": cone, "status": f"extract_failed:{type(exc).__name__}:{exc}"} for cone in CONES], {"case_id": case["case_id"], "status": "extract_failed", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if fdtd is not None:
            try:
                fdtd.close()
            except Exception:
                pass


def incoherent_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ok = [r for r in case_rows if r.get("status") == "ok"]
    out: list[dict[str, Any]] = []
    for candidate_id in sorted({r["candidate_id"] for r in ok}):
        for cone in CONES:
            subset = [r for r in ok if r["candidate_id"] == candidate_id and float(r["cone_half_angle_deg"]) == cone]
            if len(subset) != 2 or {r["dipole_axis"] for r in subset} != {"x", "y"}:
                out.append({"candidate_id": candidate_id, "wavelength_nm": 453.0, "source_position_label": "center", "cone_half_angle_deg": cone, "status": "missing_pair"})
                continue
            r_sum = sum(float(r["R_power"]) for r in subset)
            l_sum = sum(float(r["L_power"]) for r in subset)
            total = r_sum + l_sum
            out.append({
                "candidate_id": candidate_id,
                "wavelength_nm": 453.0,
                "source_position_label": "center",
                "cone_half_angle_deg": cone,
                "R_power_incoh": r_sum,
                "L_power_incoh": l_sum,
                "L_fraction_incoh": l_sum / total if total else float("nan"),
                "DoCP_RminusL_incoh": (r_sum - l_sum) / total if total else float("nan"),
                "total_cone_power_incoh": total,
                "status": "ok",
            })
    return out


def write_report(case_rows: list[dict[str, Any]], avg_rows: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> None:
    def line(candidate: str, axis: str, cone: float = 20.0) -> str:
        row = next((r for r in case_rows if r.get("candidate_id") == candidate and r.get("dipole_axis") == axis and float(r.get("cone_half_angle_deg", -1)) == cone), None)
        if not row:
            return "missing"
        return f"L_fraction={float(row['L_fraction']):.6g}, DoCP={float(row['DoCP_RminusL']):.6g}, P={float(row['total_cone_power']):.6g}"
    def avg(candidate: str, cone: float = 20.0) -> str:
        row = next((r for r in avg_rows if r.get("candidate_id") == candidate and float(r.get("cone_half_angle_deg", -1)) == cone), None)
        if not row:
            return "missing"
        return f"L_fraction={float(row['L_fraction_incoh']):.6g}, DoCP={float(row['DoCP_RminusL_incoh']):.6g}, P={float(row['total_cone_power_incoh']):.6g}"
    psi99 = "BW2_J1J2_D194_T90_PSI99_H525"
    psi97 = "BW2_J1J2_D194_T90_PSI97_H525"
    p99 = next((r for r in avg_rows if r.get("candidate_id") == psi99 and float(r.get("cone_half_angle_deg", -1)) == 20.0), None)
    p97 = next((r for r in avg_rows if r.get("candidate_id") == psi97 and float(r.get("cone_half_angle_deg", -1)) == 20.0), None)
    power_ratio = ""
    not_worse = "not evaluated"
    if p99 and p97 and p99.get("status") == p97.get("status") == "ok":
        power_ratio_float = float(p99["total_cone_power_incoh"]) / float(p97["total_cone_power_incoh"])
        power_ratio = f"{power_ratio_float:.6g}"
        not_worse = "yes" if power_ratio_float >= 0.6 else "no"
    text = f"""# Stage10 CP BW2A no-DBR MicroLED center dipole smoke run

## English
- FDTD smoke run scope: exactly 4 cases from the prepared manifest.
- No +/-q, no 450 nm, no 36-case run, no DBR, no RCLED, no MQW stack change, no top DBR, no bottom mirror, no spacer scan.
- CP extraction uses complex farfieldvector3d Ex/Ey and +z convention R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- L_out dominance means DoCP_RminusL < 0 and L_fraction > 0.5.

### 20 deg cone comparison
- PSI99 center x: {line(psi99, 'x')}
- PSI99 center y: {line(psi99, 'y')}
- PSI99 x/y incoherent average: {avg(psi99)}
- PSI97 center x: {line(psi97, 'x')}
- PSI97 center y: {line(psi97, 'y')}
- PSI97 x/y incoherent average: {avg(psi97)}
- PSI99 remains L_out dominant: {'yes' if p99 and float(p99.get('DoCP_RminusL_incoh', 1)) < 0 and float(p99.get('L_fraction_incoh', 0)) > 0.5 else 'no'}
- PSI99 not significantly worse than PSI97 by 0.6x total-cone-power guard: {not_worse}; PSI99/PSI97 power ratio = {power_ratio}

## 中文
- FDTD smoke 范围：严格只运行 manifest 中 4 个 case。
- 没有 +/-q、没有 450 nm、没有 36-case run、没有 DBR、RCLED、MQW stack change、顶 DBR、底镜或 spacer scan。
- CP 提取使用 complex farfieldvector3d Ex/Ey 和 +z 约定 R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)。
- L_out 占优表示 DoCP_RminusL < 0 且 L_fraction > 0.5。
- 20 deg cone 下 PSI99 x/y 非相干平均：{avg(psi99)}。
- 20 deg cone 下 PSI97 x/y 非相干平均：{avg(psi97)}。
- PSI99 是否保持 L_out 占优：{'yes' if p99 and float(p99.get('DoCP_RminusL_incoh', 1)) < 0 and float(p99.get('L_fraction_incoh', 0)) > 0.5 else 'no'}。
- PSI99 是否没有显著差于 PSI97：{not_worse}；总 cone power 比值 = {power_ratio}。
"""
    (OUT_DIR / "stage10_cp_dipole_bw2a_smoke_run_report.md").write_text(text, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SETUP_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = read_manifest()
    cases = [make_case(r) for r in manifest]
    if len(cases) != 4:
        raise RuntimeError("Refusing to run anything other than exactly 4 cases")
    runtime = SimpleNamespace(lumapi_python_api_dir=r"N:\\Program Files\\ANSYS Inc\\v251\\Lumerical\\api\\python", hide_gui=True)
    lumapi = import_lumapi(runtime)
    setup_paths = build_setups(lumapi, runtime, sorted({c["candidate_id"] for c in cases}))
    run_rows: list[dict[str, Any]] = []
    case_rows: list[dict[str, Any]] = []
    extract_debug: list[dict[str, Any]] = []
    for case in cases:
        patch_candidate(case["candidate_id"])
        run_rows.append(run_one(lumapi, runtime, setup_paths[case["candidate_id"]], case))
        rows, debug = extract_case(lumapi, runtime, case)
        case_rows.extend(rows)
        extract_debug.append(debug)
    avg_rows = incoherent_rows(case_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_case_results.csv", case_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_incoherent_summary.csv", avg_rows)
    write_csv(OUT_DIR / "stage10_cp_dipole_bw2a_smoke_run_table.csv", run_rows)
    summary = {
        "stage": "Stage10-CP-DIPOLE-BW2A-SMOKE",
        "fdtd_cases_requested": 4,
        "fdtd_cases_completed_or_reused": sum(1 for r in run_rows if r.get("fdtd_status") in {"ok", "reused"}),
        "failed_cases": [r for r in run_rows if r.get("fdtd_status") not in {"ok", "reused"}],
        "extraction_ok_rows": sum(1 for r in case_rows if r.get("status") == "ok"),
        "cone_half_angles_deg": CONES,
        "grid_n": GRID_N,
        "runtime_artifact_dir": str(SAVED_DIR),
        "no_dbr": True,
        "no_rcled": True,
        "no_mqw": True,
        "no_q_positions": True,
        "no_450nm": True,
        "extract_debug": extract_debug,
    }
    (OUT_DIR / "stage10_cp_dipole_bw2a_smoke_run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_report(case_rows, avg_rows, run_rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
