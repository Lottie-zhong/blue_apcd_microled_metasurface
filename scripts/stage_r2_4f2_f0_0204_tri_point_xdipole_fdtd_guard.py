#!/usr/bin/env python3
"""R2-4F2 tri-point x-dipole FDTD guard for F0_0204 only.

Allowed Lumerical action: solve exactly three x-dipole 453 nm cases at x=-0.7,0,+0.7 um.
Forbidden: y dipole, z_outofplane, broadband, 5/9-point sweeps, other candidates.
"""
from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
OUT = ROOT / "outputs" / "r2_4f2_f0_0204_tri_point_xdipole_fdtd_guard"
SOLVE_DIR = OUT / "runtime_solve_fsp"
LUMAPI_DIR = Path(r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")

STAGE = "R2-4F2 F0_0204 tri-point x-dipole 453 nm FDTD guard"
CANDIDATE_ID = "F0_0204"
FAMILY_ID = "high_top_DBR_RCLED"
WAVELENGTH_NM = 453.0
X_POSITIONS_UM = [-0.7, 0.0, 0.7]
EXPECTED_CASE_IDS = [
    "F0_0204_xm0p7_xdipole_453",
    "F0_0204_x0p0_xdipole_453",
    "F0_0204_xp0p7_xdipole_453",
]

TOP_PAIR_COUNT = 9
BOTTOM_PAIR_COUNT = 10
CAVITY_NM = 230.0
TOP_TERMINATION_NM = 0.0
BOTTOM_TERMINATION_NM = 0.0
MDC_M = "n/a"
MDC_SIO2_NM = "n/a"
MDC_TIO2_NM = "n/a"
TIO2_QW_NM = 453.0 / (4.0 * 2.60)
SIO2_QW_NM = 453.0 / (4.0 * 1.46)

N_GAN = 2.56
N_TIO2 = 2.60
N_SIO2 = 1.46
UM = 1e-6
NM = 1e-9
FDTD_X_SPAN_UM = 20.0
DEVICE_X_SPAN_UM = 3.0
DBR_X_SPAN_UM = 8.0
MONITOR_X_SPAN_UM = 16.0
AIR_ABOVE_TOP_UM = 0.8
AIR_BELOW_BOTTOM_UM = 0.8
MONITOR_CLEARANCE_UM = 0.35
SIM_TIME_FS = 250.0
MONITOR = "top_farfield_monitor"

MATERIALS = {
    "GaN_450nm_n2p56_custom": (N_GAN, [0.45, 0.70, 1.0, 0.45]),
    "TiO2_n2p6_custom": (N_TIO2, [1.0, 0.0, 0.0, 0.45]),
    "SiO2_n1p46_custom": (N_SIO2, [1.0, 0.85, 0.0, 0.45]),
}
MAT_MAP = {"TiO2": "TiO2_n2p6_custom", "SiO2": "SiO2_n1p46_custom", "SiO2_termination": "SiO2_n1p46_custom"}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def import_lumapi() -> Any:
    sys.path.insert(0, str(LUMAPI_DIR))
    import lumapi  # type: ignore[import-not-found]
    return lumapi


def ensure_material(fdtd: Any, name: str, n: float, color: list[float]) -> None:
    existing = {line.strip() for line in str(fdtd.getmaterial()).splitlines() if line.strip()}
    if name in existing:
        return
    mid = fdtd.addmaterial("(n,k) Material")
    fdtd.setmaterial(mid, "name", name)
    fdtd.setmaterial(name, "Refractive Index", n)
    fdtd.setmaterial(name, "Imaginary Refractive Index", 0)
    fdtd.setmaterial(name, "Mesh order", 3)
    try:
        fdtd.setmaterial(name, "color", np.array(color))
    except Exception:
        pass


def add_rect(fdtd: Any, name: str, mat: str, x_span_um: float, y_min_nm: float, y_max_nm: float) -> None:
    if y_max_nm <= y_min_nm:
        raise ValueError(f"non-positive layer thickness for {name}: {y_min_nm}..{y_max_nm} nm")
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("material", mat)
    fdtd.set("x", 0)
    fdtd.set("x span", x_span_um * UM)
    fdtd.set("y min", y_min_nm * NM)
    fdtd.set("y max", y_max_nm * NM)


def make_layers() -> dict[str, list[dict[str, object]]]:
    top: list[dict[str, object]] = []
    idx = 0
    for _ in range(TOP_PAIR_COUNT):
        top.append({"layer_index": idx, "material": "TiO2", "thickness_nm": round(TIO2_QW_NM, 6)}); idx += 1
        top.append({"layer_index": idx, "material": "SiO2", "thickness_nm": round(SIO2_QW_NM, 6)}); idx += 1
    if TOP_TERMINATION_NM > 0:
        top.append({"layer_index": idx, "material": "SiO2_termination", "thickness_nm": TOP_TERMINATION_NM})

    bottom: list[dict[str, object]] = []
    if BOTTOM_TERMINATION_NM > 0:
        bottom.append({"layer_index": 0, "material": "SiO2_termination", "thickness_nm": BOTTOM_TERMINATION_NM})
    idx = len(bottom)
    for _ in range(BOTTOM_PAIR_COUNT):
        bottom.append({"layer_index": idx, "material": "TiO2", "thickness_nm": round(TIO2_QW_NM, 6)}); idx += 1
        bottom.append({"layer_index": idx, "material": "SiO2", "thickness_nm": round(SIO2_QW_NM, 6)}); idx += 1
    return {"top": top, "bottom": bottom}


def case_suffix(x_um: float) -> str:
    if abs(x_um) < 1e-12:
        return "x0p0"
    return f"x{x_um:+.1f}".replace("+", "p").replace("-", "m").replace(".", "p")


def build_case(fdtd: Any, x_um: float, stacks: dict[str, list[dict[str, object]]]) -> dict[str, object]:
    fdtd.switchtolayout()
    fdtd.deleteall()
    for name, (n, color) in MATERIALS.items():
        ensure_material(fdtd, name, n, color)

    top_total_nm = sum(float(r["thickness_nm"]) for r in stacks["top"])
    bottom_total_nm = sum(float(r["thickness_nm"]) for r in stacks["bottom"])
    top_max_nm = CAVITY_NM + top_total_nm
    bottom_min_nm = -bottom_total_nm
    y_min_um = bottom_min_nm / 1000.0 - AIR_BELOW_BOTTOM_UM
    y_max_um = top_max_nm / 1000.0 + AIR_ABOVE_TOP_UM
    monitor_y_um = min(y_max_um - 0.35, top_max_nm / 1000.0 + MONITOR_CLEARANCE_UM)
    source_y_nm = CAVITY_NM / 2.0

    fdtd.addfdtd()
    fdtd.set("dimension", "2D")
    fdtd.set("x span", FDTD_X_SPAN_UM * UM)
    fdtd.set("y min", y_min_um * UM)
    fdtd.set("y max", y_max_um * UM)
    fdtd.set("x min bc", "PML")
    fdtd.set("x max bc", "PML")
    fdtd.set("y min bc", "PML")
    fdtd.set("y max bc", "PML")
    fdtd.set("mesh accuracy", 3)
    fdtd.set("simulation time", SIM_TIME_FS * 1e-15)

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_bottom_reflector_group")
    fdtd.groupscope("::model::RCLED_bottom_reflector_group")
    y = 0.0
    for r in stacks["bottom"]:
        th = float(r["thickness_nm"])
        y_next = y - th
        add_rect(fdtd, f"bottom_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y_next, y)
        y = y_next
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_GaN_cavity_group")
    fdtd.groupscope("::model::RCLED_GaN_cavity_group")
    add_rect(fdtd, "GaN_cavity_device_aperture", "GaN_450nm_n2p56_custom", DEVICE_X_SPAN_UM, 0.0, CAVITY_NM)
    fdtd.groupscope("::model")

    fdtd.addstructuregroup(); fdtd.set("name", "RCLED_top_DBR_group")
    fdtd.groupscope("::model::RCLED_top_DBR_group")
    y = CAVITY_NM
    for r in stacks["top"]:
        th = float(r["thickness_nm"])
        add_rect(fdtd, f"top_{int(r['layer_index']):02d}_{r['material']}_{th:g}nm", MAT_MAP[str(r["material"])], DBR_X_SPAN_UM, y, y + th)
        y += th
    fdtd.groupscope("::model")

    suffix = case_suffix(x_um)
    case_id = f"F0_0204_{suffix}_xdipole_453"
    if case_id not in EXPECTED_CASE_IDS:
        raise RuntimeError(f"unexpected case generated: {case_id}")
    source_name = f"src_{suffix}_x"
    fdtd.adddipole()
    fdtd.set("name", source_name)
    fdtd.set("x", x_um * UM)
    fdtd.set("y", source_y_nm * NM)
    fdtd.set("theta", 90.0)
    fdtd.set("phi", 0.0)
    fdtd.set("wavelength start", WAVELENGTH_NM * NM)
    fdtd.set("wavelength stop", WAVELENGTH_NM * NM)

    fdtd.addpower()
    fdtd.set("name", MONITOR)
    fdtd.set("monitor type", "Linear X")
    fdtd.set("x", 0)
    fdtd.set("x span", MONITOR_X_SPAN_UM * UM)
    fdtd.set("y", monitor_y_um * UM)

    theta = float(fdtd.getnamed(source_name, "theta"))
    phi = float(fdtd.getnamed(source_name, "phi"))
    setup_ok = abs(theta - 90.0) < 1e-9 and abs(phi) < 1e-9 and abs(x_um) <= DEVICE_X_SPAN_UM / 2.0 and 0 < source_y_nm < CAVITY_NM
    fsp_path = SOLVE_DIR / f"{case_id}.fsp"
    fdtd.save(str(fsp_path))
    return {
        "case_id": case_id,
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "source_x_um": x_um,
        "source_y_nm": source_y_nm,
        "dipole_orientation": "x",
        "theta_readback_deg": theta,
        "phi_readback_deg": phi,
        "wavelength_nm": WAVELENGTH_NM,
        "top_pair_count": TOP_PAIR_COUNT,
        "bottom_pair_count": BOTTOM_PAIR_COUNT,
        "mdc_m": MDC_M,
        "mdc_sio2_nm": MDC_SIO2_NM,
        "mdc_tio2_nm": MDC_TIO2_NM,
        "cavity_nm": CAVITY_NM,
        "top_termination_nm": TOP_TERMINATION_NM,
        "bottom_termination_nm": BOTTOM_TERMINATION_NM,
        "top_layer_count": len(stacks["top"]),
        "bottom_layer_count": len(stacks["bottom"]),
        "monitor_y_um": monitor_y_um,
        "monitor_y_above_top_structure_um": monitor_y_um - top_max_nm / 1000.0,
        "monitor_y_to_top_pml_um": y_max_um - monitor_y_um,
        "source_inside_cavity": setup_ok,
        "result_fsp": str(fsp_path),
        "setup_status": "ok" if setup_ok else "setup_failed",
    }


def trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.trapz(y, x))


def sanitize(angles: object, intensity: object) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(angles, dtype=float).reshape(-1)
    i = np.asarray(intensity, dtype=float).reshape(-1)
    n = min(len(a), len(i))
    a, i = a[:n], i[:n]
    mask = np.isfinite(a) & np.isfinite(i)
    a, i = a[mask], np.maximum(i[mask], 0.0)
    order = np.argsort(a)
    return a[order], i[order]


def band_power(angles: np.ndarray, intensity: np.ndarray, lo: float, hi: float) -> float:
    mask = (np.abs(angles) >= lo) & (np.abs(angles) <= hi)
    if mask.sum() < 2:
        return 0.0
    return trapz(intensity[mask], angles[mask])


def cone_power(angles: np.ndarray, intensity: np.ndarray, cone: float) -> float:
    mask = np.abs(angles) <= cone
    if mask.sum() < 2:
        return 0.0
    return trapz(intensity[mask], angles[mask])


def fwhm_deg(angles: np.ndarray, intensity: np.ndarray) -> float:
    if len(angles) < 3 or np.max(intensity) <= 0:
        return math.nan
    half = 0.5 * float(np.max(intensity))
    above = intensity >= half
    idx = np.where(above)[0]
    if len(idx) == 0:
        return math.nan
    return float(angles[idx[-1]] - angles[idx[0]])


def extract_angle(fdtd: Any) -> tuple[np.ndarray, np.ndarray, str]:
    ff = fdtd.farfield2d(MONITOR, 1)
    ang = fdtd.farfieldangle(MONITOR, 1)
    return (*sanitize(ang, ff), "farfield2d_farfieldangle")


def metric_row(angles: np.ndarray, intensity: np.ndarray, runtime_s: float, mode: str) -> dict[str, object]:
    total = band_power(angles, intensity, 0, 90)
    normal = cone_power(angles, intensity, 10)
    off20_60 = band_power(angles, intensity, 20, 60)
    off30_40 = band_power(angles, intensity, 30, 40)
    off45_55 = band_power(angles, intensity, 45, 55)
    off40_60 = band_power(angles, intensity, 40, 60)
    k = int(np.argmax(intensity)) if len(intensity) else 0
    peak = float(angles[k]) if len(angles) else math.nan
    return {
        "status": "ok",
        "runtime_s": round(runtime_s, 3),
        "extraction_mode": mode,
        "signed_peak_angle_deg": peak,
        "peak_abs_angle_deg": abs(peak) if not math.isnan(peak) else math.nan,
        "angular_fwhm_deg": fwhm_deg(angles, intensity),
        "eta_5deg": cone_power(angles, intensity, 5) / total if total > 0 else math.nan,
        "eta_10deg": normal / total if total > 0 else math.nan,
        "eta_20deg": cone_power(angles, intensity, 20) / total if total > 0 else math.nan,
        "eta_30deg": cone_power(angles, intensity, 30) / total if total > 0 else math.nan,
        "normal_offaxis_ratio": normal / off20_60 if off20_60 > 0 else math.inf,
        "offaxis_20_60_fraction": off20_60 / total if total > 0 else math.nan,
        "offaxis_30_40_fraction": off30_40 / total if total > 0 else math.nan,
        "offaxis_45_55_fraction": off45_55 / total if total > 0 else math.nan,
        "offaxis_40_60_fraction": off40_60 / total if total > 0 else math.nan,
        "normal_10_fraction": normal / total if total > 0 else math.nan,
        "thirty_forty_lobe_flag": bool(30 <= abs(peak) <= 40 and off30_40 > normal),
        "fortyfive_fiftyfive_lobe_flag": bool(45 <= abs(peak) <= 55 and off45_55 > normal),
        "broad_forty_sixty_lobe_flag": bool(off40_60 > normal),
    }


def combine_average(cuts: dict[float, tuple[np.ndarray, np.ndarray]]) -> tuple[np.ndarray, np.ndarray]:
    if not cuts:
        return np.array([]), np.array([])
    base = next(iter(cuts.values()))[0]
    acc = np.zeros_like(base, dtype=float)
    for angles, intensity in cuts.values():
        acc += np.interp(base, angles, intensity)
    return base, acc / len(cuts)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SOLVE_DIR.mkdir(parents=True, exist_ok=True)
    stacks = make_layers()
    case_manifest = []
    for x in X_POSITIONS_UM:
        case_manifest.append({"case_id": f"F0_0204_{case_suffix(x)}_xdipole_453", "source_x_um": x, "candidate_id": CANDIDATE_ID, "dipole_orientation": "x", "wavelength_nm": WAVELENGTH_NM})
    if [r["case_id"] for r in case_manifest] != EXPECTED_CASE_IDS:
        raise RuntimeError("case manifest does not match expected E2 tri-point set")
    write_csv(OUT / "r2_4f2_case_manifest.csv", case_manifest)

    rows: list[dict[str, object]] = []
    cuts: dict[float, tuple[np.ndarray, np.ndarray]] = {}
    setup_failed = False
    try:
        lumapi = import_lumapi()
        fdtd = lumapi.FDTD(hide=True)
        try:
            for x in X_POSITIONS_UM:
                row = build_case(fdtd, x, stacks)
                if row["setup_status"] != "ok":
                    setup_failed = True
                    row.update({"status": "setup_failed", "error_message": "source or orientation setup audit failed"})
                    rows.append(row)
                    continue
                t0 = time.time()
                fdtd.run()
                runtime_s = time.time() - t0
                angles, intensity, mode = extract_angle(fdtd)
                row.update(metric_row(angles, intensity, runtime_s, mode))
                row["thirty_forty_lobe_flag"] = bool(row["thirty_forty_lobe_flag"])
                row["fortyfive_fiftyfive_lobe_flag"] = bool(row["fortyfive_fiftyfive_lobe_flag"])
                row["broad_forty_sixty_lobe_flag"] = bool(row["broad_forty_sixty_lobe_flag"])
                fdtd.save(str(row["result_fsp"]))
                rows.append(row)
                cuts[x] = (angles, intensity)
        finally:
            fdtd.close()
    except Exception as exc:
        setup_failed = True
        rows.append({"case_id": "setup_or_runtime_failure", "candidate_id": CANDIDATE_ID, "status": "setup_failed", "error_message": repr(exc)})

    write_csv(OUT / "r2_4f2_case_results.csv", rows)

    ok_rows = [r for r in rows if r.get("status") == "ok"]
    avg_rows: list[dict[str, object]] = []
    verdict_reasons: list[str] = []
    verdict = "fail"
    if len(ok_rows) == 3 and len(cuts) == 3:
        avg_a, avg_i = combine_average(cuts)
        avg = metric_row(avg_a, avg_i, sum(float(r.get("runtime_s", 0)) for r in ok_rows), "tri_point_intensity_mean")
        peaks = np.array([float(r["peak_abs_angle_deg"]) for r in ok_rows], dtype=float)
        neg = next(r for r in ok_rows if abs(float(r["source_x_um"]) + 0.7) < 1e-9)
        pos = next(r for r in ok_rows if abs(float(r["source_x_um"]) - 0.7) < 1e-9)
        center = next(r for r in ok_rows if abs(float(r["source_x_um"])) < 1e-9)
        bilateral_peak_avg = 0.5 * (float(neg["peak_abs_angle_deg"]) + float(pos["peak_abs_angle_deg"]))
        bilateral_asym = abs(float(neg["peak_abs_angle_deg"]) - float(pos["peak_abs_angle_deg"]))
        mismatch = abs(float(center["peak_abs_angle_deg"]) - bilateral_peak_avg)
        avg_row = {
            "candidate_id": CANDIDATE_ID,
            "case_count": 3,
            "tri_point_avg_peak_abs_angle_deg": avg["peak_abs_angle_deg"],
            "tri_point_avg_signed_peak_angle_deg": avg["signed_peak_angle_deg"],
            "tri_point_avg_fwhm_deg": avg["angular_fwhm_deg"],
            "tri_point_avg_normal_offaxis_ratio": avg["normal_offaxis_ratio"],
            "tri_point_avg_offaxis_30_40_fraction": avg["offaxis_30_40_fraction"],
            "tri_point_avg_offaxis_45_55_fraction": avg["offaxis_45_55_fraction"],
            "tri_point_avg_offaxis_40_60_fraction": avg["offaxis_40_60_fraction"],
            "tri_point_avg_eta_5deg": avg["eta_5deg"],
            "tri_point_avg_eta_10deg": avg["eta_10deg"],
            "tri_point_avg_eta_20deg": avg["eta_20deg"],
            "tri_point_avg_eta_30deg": avg["eta_30deg"],
            "source_position_peak_abs_min_deg": float(np.min(peaks)),
            "source_position_peak_abs_max_deg": float(np.max(peaks)),
            "source_position_peak_abs_std_deg": float(np.std(peaks)),
            "bilateral_asymmetry_metric": bilateral_asym,
            "center_vs_bilateral_mismatch_metric": mismatch,
        }
        hard_fail = False
        if float(avg_row["tri_point_avg_peak_abs_angle_deg"]) > 8:
            hard_fail = True; verdict_reasons.append("tri_point_avg_peak_abs_angle_gt_8deg")
        if float(avg_row["tri_point_avg_fwhm_deg"]) > 20:
            hard_fail = True; verdict_reasons.append("tri_point_avg_fwhm_gt_20deg")
        if float(avg_row["tri_point_avg_normal_offaxis_ratio"]) <= 1.0:
            hard_fail = True; verdict_reasons.append("tri_point_avg_normal_offaxis_ratio_le_1")
        for r in ok_rows:
            if bool(r.get("thirty_forty_lobe_flag")):
                hard_fail = True; verdict_reasons.append(f"{r['case_id']}_30_40_lobe_dominant")
            if bool(r.get("fortyfive_fiftyfive_lobe_flag")):
                hard_fail = True; verdict_reasons.append(f"{r['case_id']}_45_55_lobe_dominant")
            if bool(r.get("broad_forty_sixty_lobe_flag")):
                hard_fail = True; verdict_reasons.append(f"{r['case_id']}_40_60_lobe_dominant")
        if float(avg_row["source_position_peak_abs_std_deg"]) > 5:
            verdict_reasons.append("soft_warning_source_position_peak_abs_std_gt_5deg")
        if float(avg_row["bilateral_asymmetry_metric"]) > 5:
            verdict_reasons.append("soft_warning_large_bilateral_asymmetry")
        verdict = "pass" if not hard_fail else "fail"
        avg_row["pass_fail_verdict"] = verdict
        avg_row["verdict_reasons"] = ";".join(verdict_reasons) if verdict_reasons else "none"
        avg_rows.append(avg_row)
        angle_rows = []
        for x, (a, i) in cuts.items():
            for aa, ii in zip(a, i):
                angle_rows.append({"trace": "case", "source_x_um": x, "angle_deg": float(aa), "intensity_proxy": float(ii)})
        for aa, ii in zip(avg_a, avg_i):
            angle_rows.append({"trace": "tri_point_average", "source_x_um": "mean", "angle_deg": float(aa), "intensity_proxy": float(ii)})
        write_csv(OUT / "r2_4f2_angle_cut_data.csv", angle_rows)
    else:
        verdict = "setup_failed" if setup_failed else "fail"
        verdict_reasons.append(f"completed_ok_cases_{len(ok_rows)}_of_3")
        avg_rows.append({"candidate_id": CANDIDATE_ID, "case_count": len(ok_rows), "pass_fail_verdict": verdict, "verdict_reasons": ";".join(verdict_reasons)})
    write_csv(OUT / "r2_4f2_tri_point_incoherent_average.csv", avg_rows)

    manifest = {
        "stage": STAGE,
        "candidate_id": CANDIDATE_ID,
        "expected_case_count": 3,
        "completed_ok_case_count": len(ok_rows),
        "case_ids": EXPECTED_CASE_IDS,
        "x_positions_um": X_POSITIONS_UM,
        "dipole_orientation": "x only, theta=90 phi=0",
        "wavelength_nm": WAVELENGTH_NM,
        "no_F0_0781": True,
        "no_D5_BASE_13461": True,
        "no_E1_0236": True,
        "no_y_dipole": True,
        "no_z_outofplane": True,
        "no_broadband": True,
        "no_5_or_9_point": True,
        "verdict": verdict,
        "runtime_solve_fsp_dir": str(SOLVE_DIR),
    }
    write_json(OUT / "r2_4f2_manifest.json", manifest)

    summary = [
        "# R2-4F2 F0_0204 Tri-Point X-Dipole FDTD Guard",
        "",
        f"Completed ok cases: {len(ok_rows)} / 3.",
        f"Verdict: **{verdict}**.",
        "",
        "Scope was restricted to F0_0204, x-dipole only, 453 nm only, x = [-0.7, 0, +0.7] um.",
        "No y dipole, z-out-of-plane, broadband, 5-point, 9-point, other candidate, or D5 rerun was performed.",
    ]
    if avg_rows:
        summary.append("")
        summary.append(f"Average/verdict reasons: {avg_rows[0].get('verdict_reasons','missing')}")
    write_text(OUT / "r2_4f2_summary.md", "\n".join(summary))

    diag = ["# R2-4F2 Source Position Stability Diagnosis", "", f"Verdict: {verdict}.", ""]
    if avg_rows:
        ar = avg_rows[0]
        for k in ["source_position_peak_abs_min_deg", "source_position_peak_abs_max_deg", "source_position_peak_abs_std_deg", "bilateral_asymmetry_metric", "center_vs_bilateral_mismatch_metric"]:
            diag.append(f"- {k}: {ar.get(k, 'missing')}")
    write_text(OUT / "r2_4f2_source_position_stability_diagnosis.md", "\n".join(diag))

    verdict_md = ["# R2-4F2 Pass/Fail Verdict", "", f"Verdict: **{verdict}**.", "", "Rules applied:", "- hard fail if any case status != ok", "- hard fail if tri-point average peak_abs_angle > 8 deg", "- hard fail if tri-point average normal/offaxis <= 1", "- hard fail if any source revives a dominant 30-40, 45-55, or broad 40-60 deg lobe", "", f"Reasons: {avg_rows[0].get('verdict_reasons','missing') if avg_rows else 'missing'}"]
    write_text(OUT / "r2_4f2_pass_fail_verdict.md", "\n".join(verdict_md))

    if verdict == "pass":
        next_step = "F0_0204 passes tri-point guard. Next allowed step is a 5-point x-line x-dipole 453 nm plan only; do not execute it in F1."
    else:
        next_step = "F0_0204 fails or did not complete tri-point guard. Stop F0_0204; F0 shortlist tri-point FDTD guards have all failed. Do not continue to 5-point, 9-point, y/z dipole, or broadband FDTD."
    write_text(OUT / "r2_4f2_next_step_plan.md", "# R2-4F2 Next Step Plan\n\n" + next_step)

    print(json.dumps({"output": str(OUT), "ok_cases": len(ok_rows), "verdict": verdict, "reasons": verdict_reasons}, indent=2))
    return 0 if len(ok_rows) == 3 or verdict == "setup_failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
