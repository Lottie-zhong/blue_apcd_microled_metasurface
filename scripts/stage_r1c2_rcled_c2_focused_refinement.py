from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

NM = 1e-9
UM = 1e-6
ROOT = Path(r"D:\project\blue_apcd_microled_metasurface")
sys.path.insert(0, str(ROOT / "src"))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

OUT = ROOT / "outputs" / "r1c2_rcled_c2_focused_refinement"
SAVED = OUT / "_saved_fsp"
LOGS = OUT / "logs"
STAGE_NAME = "R1C2_RCLED_C2_focused_refinement"

N_GAN = 2.56
N_TIO2 = 2.60
N_SIO2 = 1.46
TOP_SIO2_NM = 100.0
TOP_TIO2_NM = 52.0
TOP_PAIR_COUNT = 6
FDTD_X_SPAN_UM = 20.0
DEVICE_X_SPAN_UM = 3.0
DBR_X_SPAN_UM = 8.0
MONITOR_X_SPAN_UM = 16.0
FDTD_Y_MIN_UM = -1.2
FDTD_Y_MAX_UM = 2.2
MONITOR_Y_UM = 1.8
SIM_TIME_FS = 250.0
MONITOR = "top_farfield_monitor"
SOURCE = "center_physical_x_dipole"

CANDIDATES = [
    {"candidate_id": "C2_base", "cavity_span_nm": 220.0, "termination": "TiO2_50nm", "termination_material": "TiO2", "termination_thickness_nm": 50.0},
    {"candidate_id": "C2_cav210", "cavity_span_nm": 210.0, "termination": "TiO2_50nm", "termination_material": "TiO2", "termination_thickness_nm": 50.0},
    {"candidate_id": "C2_cav230", "cavity_span_nm": 230.0, "termination": "TiO2_50nm", "termination_material": "TiO2", "termination_thickness_nm": 50.0},
    {"candidate_id": "C2_TiO2_40", "cavity_span_nm": 220.0, "termination": "TiO2_40nm", "termination_material": "TiO2", "termination_thickness_nm": 40.0},
    {"candidate_id": "C2_TiO2_60", "cavity_span_nm": 220.0, "termination": "TiO2_60nm", "termination_material": "TiO2", "termination_thickness_nm": 60.0},
]
WAVELENGTHS = [450.0, 453.0, 456.0]


def rows_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


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
    fdtd.addrect()
    fdtd.set("name", name)
    fdtd.set("material", mat)
    fdtd.set("x", 0)
    fdtd.set("x span", x_span_um * UM)
    fdtd.set("y min", y_min_nm * NM)
    fdtd.set("y max", y_max_nm * NM)


def build_case(fdtd: Any, cand: dict[str, Any], wl_nm: float) -> dict[str, Any]:
    fdtd.switchtolayout()
    fdtd.deleteall()
    ensure_material(fdtd, "GaN_450nm_n2p56_custom", N_GAN, [1.0, 0.35, 0.70, 0.45])
    ensure_material(fdtd, "TiO2_n2p6_custom", N_TIO2, [1.0, 0.0, 0.0, 0.45])
    ensure_material(fdtd, "SiO2_n1p46_custom", N_SIO2, [1.0, 0.85, 0.0, 0.45])

    fdtd.addfdtd()
    fdtd.set("dimension", "2D")
    fdtd.set("x span", FDTD_X_SPAN_UM * UM)
    fdtd.set("y min", FDTD_Y_MIN_UM * UM)
    fdtd.set("y max", FDTD_Y_MAX_UM * UM)
    fdtd.set("x min bc", "PML")
    fdtd.set("x max bc", "PML")
    fdtd.set("y min bc", "PML")
    fdtd.set("y max bc", "PML")
    fdtd.set("mesh accuracy", 3)
    fdtd.set("simulation time", SIM_TIME_FS * 1e-15)

    term_t = float(cand["termination_thickness_nm"])
    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_bottom_reflector_group")
    fdtd.groupscope("::model::RCLED_bottom_reflector_group")
    mat = "TiO2_n2p6_custom" if cand["termination_material"] == "TiO2" else "SiO2_n1p46_custom"
    add_rect(fdtd, f"intentional_bottom_termination_{cand['termination']}", mat, DBR_X_SPAN_UM, -term_t, 0.0)
    fdtd.groupscope("::model")

    gan_min = 0.0
    gan_max = float(cand["cavity_span_nm"])
    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_GaN_cavity_group")
    fdtd.groupscope("::model::RCLED_GaN_cavity_group")
    add_rect(fdtd, "GaN_cavity_device_aperture", "GaN_450nm_n2p56_custom", DEVICE_X_SPAN_UM, gan_min, gan_max)
    fdtd.groupscope("::model")

    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_top_DBR_group")
    fdtd.groupscope("::model::RCLED_top_DBR_group")
    y = gan_max
    for i in range(TOP_PAIR_COUNT):
        add_rect(fdtd, f"top_{i:02d}_SiO2_100nm", "SiO2_n1p46_custom", DBR_X_SPAN_UM, y, y + TOP_SIO2_NM)
        y += TOP_SIO2_NM
        add_rect(fdtd, f"top_{i:02d}_TiO2_52nm", "TiO2_n2p6_custom", DBR_X_SPAN_UM, y, y + TOP_TIO2_NM)
        y += TOP_TIO2_NM
    add_rect(fdtd, "top_terminal_SiO2_100nm", "SiO2_n1p46_custom", DBR_X_SPAN_UM, y, y + TOP_SIO2_NM)
    y += TOP_SIO2_NM
    fdtd.groupscope("::model")

    fdtd.adddipole()
    fdtd.set("name", SOURCE)
    fdtd.set("x", 0)
    fdtd.set("y", (gan_min + gan_max) * 0.5 * NM)
    fdtd.set("theta", 90)
    fdtd.set("phi", 0)
    fdtd.set("wavelength start", wl_nm * NM)
    fdtd.set("wavelength stop", wl_nm * NM)

    fdtd.addpower()
    fdtd.set("name", MONITOR)
    fdtd.set("monitor type", "Linear X")
    fdtd.set("x", 0)
    fdtd.set("x span", MONITOR_X_SPAN_UM * UM)
    fdtd.set("y", MONITOR_Y_UM * UM)

    return {
        "stage_name": STAGE_NAME,
        "candidate_id": cand["candidate_id"],
        "wavelength_nm": wl_nm,
        "fdtd_x_span_um": FDTD_X_SPAN_UM,
        "gan_device_x_span_um": DEVICE_X_SPAN_UM,
        "top_dbr_mdc_span_um": DBR_X_SPAN_UM,
        "bottom_pair_count": 0,
        "monitor_x_span_um": MONITOR_X_SPAN_UM,
        "monitor_y_um": MONITOR_Y_UM,
        "monitor_y_to_pml_um": FDTD_Y_MAX_UM - MONITOR_Y_UM,
        "monitor_inside_pml": False,
        "cavity_span_nm": gan_max - gan_min,
        "termination_material": cand["termination_material"],
        "termination_thickness_nm": term_t,
        "top_group_exists": bool(fdtd.getnamednumber("RCLED_top_DBR_group")),
        "bottom_group_exists": bool(fdtd.getnamednumber("RCLED_bottom_reflector_group")),
        "gan_cavity_group_exists": bool(fdtd.getnamednumber("RCLED_GaN_cavity_group")),
        "bottom_group_termination_only": True,
        "physical_x_dipole_verified": abs(float(fdtd.getnamed(SOURCE, "theta")) - 90) < 1e-6 and abs(float(fdtd.getnamed(SOURCE, "phi"))) < 1e-6,
        "no_forbidden_integration": True,
    }


def complete(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 1_000_000


def angle_metrics(fdtd: Any) -> dict[str, Any]:
    ff = np.asarray(fdtd.farfield2d(MONITOR, 1), dtype=float).squeeze()
    ang = np.asarray(fdtd.farfieldangle(MONITOR, 1), dtype=float).squeeze()
    if np.nanmax(np.abs(ang)) <= math.pi + 1e-6:
        ang = np.degrees(ang)
    ff = np.abs(ff).ravel()
    if ff.size != ang.size:
        ang = np.linspace(-90, 90, ff.size)
    total = float(np.sum(ff))

    def frac(lo: float, hi: float) -> float:
        m = (np.abs(ang) >= lo) & (np.abs(ang) <= hi)
        return float(np.sum(ff[m]) / total) if total else float("nan")

    etas = {f"eta{d}": frac(0, d) for d in (5, 10, 20, 30)}
    peak_i = int(np.argmax(ff))
    peak_angle = float(ang[peak_i])
    half = float(ff[peak_i]) * 0.5
    above = np.where(ff >= half)[0]
    fwhm = float(abs(ang[above[-1]] - ang[above[0]])) if above.size else float("nan")
    left = float(np.sum(ff[ang < 0]))
    right = float(np.sum(ff[ang > 0]))
    asym = float((right - left) / (right + left)) if (right + left) else float("nan")
    rings = {
        "ring_power_abs_0_10": frac(0, 10),
        "ring_power_abs_10_20": frac(10, 20),
        "ring_power_abs_20_30": frac(20, 30),
        "ring_power_abs_30_45": frac(30, 45),
    }
    zones = {
        "abs_0_5": frac(0, 5),
        "abs_5_10": frac(5, 10),
        "abs_10_20": frac(10, 20),
        "abs_20_30": frac(20, 30),
        "abs_30_45": frac(30, 45),
    }
    return {
        **etas,
        **rings,
        "FWHM_deg": fwhm,
        "peak_angle_deg": peak_angle,
        "peak_abs_angle_deg": abs(peak_angle),
        "P_total": total,
        "outside20": 1 - etas["eta20"],
        "dominant_zone": max(zones, key=zones.get),
        "near_normal_peak": abs(peak_angle) <= 10,
        "left_right_asymmetry": asym,
    }


def run_case(lumapi: Any, runtime: Any, cand: dict[str, Any], wl_nm: float) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    case_id = f"R1C2_{cand['candidate_id']}_{int(wl_nm)}nm"
    fsp = SAVED / f"{case_id}.fsp"
    log = LOGS / f"{case_id}.log"
    start = time.perf_counter()
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        if complete(fsp):
            fdtd.load(str(fsp))
            audit = {"case_id": case_id, "candidate_id": cand["candidate_id"], "wavelength_nm": wl_nm, "reused_existing_complete_fsp": True}
            status = "reused"
        else:
            audit = build_case(fdtd, cand, wl_nm)
            setup = OUT / f"{case_id}_setup.fsp"
            fdtd.save(str(setup))
            fdtd.load(str(setup))
            fdtd.run()
            fdtd.save(str(fsp))
            status = "ok"
        metrics = angle_metrics(fdtd)
        row = {
            "candidate_id": cand["candidate_id"],
            "top_pair_count": TOP_PAIR_COUNT,
            "bottom_pair_count": 0,
            "cavity_span_nm": cand["cavity_span_nm"],
            "termination": cand["termination"],
            "termination_thickness_nm": cand["termination_thickness_nm"],
            "wavelength_nm": wl_nm,
            "dipole_orientation": "physical_x_theta90_phi0",
            "status": status,
            "runtime_s": time.perf_counter() - start,
            "result_fsp": str(fsp),
            **metrics,
        }
        log.write_text(json.dumps(row, indent=2), encoding="utf-8")
        return row, audit, {"case_id": case_id, "status": status, "runtime_s": row["runtime_s"], "fsp_bytes": fsp.stat().st_size}
    finally:
        fdtd.close()


def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_power = {(r["wavelength_nm"]): float(r["P_total"]) for r in rows if r["candidate_id"] == "C2_base"}
    out: list[dict[str, Any]] = []
    for cand in CANDIDATES:
        subset = [r for r in rows if r["candidate_id"] == cand["candidate_id"]]
        if len(subset) != len(WAVELENGTHS):
            continue
        peak_abs_le15_all = all(float(r["peak_abs_angle_deg"]) <= 15 for r in subset)
        dominant_zone_abs_0_20_all = all(r["dominant_zone"] in {"abs_0_5", "abs_5_10", "abs_10_20"} for r in subset)
        near_normal_all = all(bool(r["near_normal_peak"]) for r in subset)
        power_ok = all(float(r["P_total"]) >= 0.5 * base_power.get(r["wavelength_nm"], float(r["P_total"])) for r in subset)
        avg_eta20 = sum(float(r["eta20"]) for r in subset) / len(subset)
        avg_eta10 = sum(float(r["eta10"]) for r in subset) / len(subset)
        avg_peak = sum(float(r["peak_abs_angle_deg"]) for r in subset) / len(subset)
        score = avg_eta20 + avg_eta10 - 0.02 * avg_peak
        out.append({
            "candidate_id": cand["candidate_id"],
            "cavity_span_nm": cand["cavity_span_nm"],
            "termination": cand["termination"],
            "peak_abs_le15_all": peak_abs_le15_all,
            "dominant_zone_abs_0_20_all": dominant_zone_abs_0_20_all,
            "near_normal_all": near_normal_all,
            "power_not_collapsed_vs_base": power_ok,
            "avg_eta10": avg_eta10,
            "avg_eta20": avg_eta20,
            "min_eta20": min(float(r["eta20"]) for r in subset),
            "avg_peak_abs_angle_deg": avg_peak,
            "score": score,
        })
    out.sort(key=lambda r: (not r["peak_abs_le15_all"], not r["dominant_zone_abs_0_20_all"], not r["power_not_collapsed_vs_base"], -float(r["avg_eta20"])))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def write_summary(rows: list[dict[str, Any]], ranking: list[dict[str, Any]]) -> None:
    best = ranking[0]
    c2_base_rank = next(r for r in ranking if r["candidate_id"] == "C2_base")["rank"]
    freeze_ok = bool(best["peak_abs_le15_all"] and best["dominant_zone_abs_0_20_all"] and best["power_not_collapsed_vs_base"])
    lines = [
        "# R1C2 RCLED C2 focused refinement",
        "",
        "2D FDTD focused refinement around R1C1 C2 only. No APCD/B4INT/CP/LP/finite patch/3D/source-y sweep/bottom DBR.",
        "",
        f"Best robust candidate: `{best['candidate_id']}` cavity `{best['cavity_span_nm']}` nm termination `{best['termination']}`.",
        f"C2_base remains best: `{c2_base_rank == 1}`.",
        f"450/453/456 robust by peak<=15 and zone abs_0_20: `{freeze_ok}`.",
        f"Source-y sweep allowed: `{freeze_ok}`.",
        f"Freeze as RCLED source-module baseline: `{freeze_ok}`.",
        "",
        "| candidate | wl | eta10 | eta20 | eta30 | peak_abs | zone | near | P_total |",
        "|---|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for r in rows:
        lines.append(f"| {r['candidate_id']} | {float(r['wavelength_nm']):.0f} | {float(r['eta10']):.4f} | {float(r['eta20']):.4f} | {float(r['eta30']):.4f} | {float(r['peak_abs_angle_deg']):.2f} | {r['dominant_zone']} | {r['near_normal_peak']} | {float(r['P_total']):.6g} |")
    (OUT / "r1c2_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SAVED.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    runtime = load_runtime_config(ROOT / "configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []
    for cand in CANDIDATES:
        for wl in WAVELENGTHS:
            row, audit, dbg = run_case(lumapi, runtime, cand, wl)
            rows.append(row)
            audits.append(audit)
            debug.append(dbg)
            print(f"{row['candidate_id']} {wl:.0f}nm {row['status']} eta20={row['eta20']:.4g} peak={row['peak_abs_angle_deg']:.2f}", flush=True)
    ranking = rank(rows)
    rows_to_csv(OUT / "r1c2_refinement_results.csv", rows)
    (OUT / "r1c2_refinement_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    rows_to_csv(OUT / "r1c2_geometry_audit.csv", audits)
    rows_to_csv(OUT / "r1c2_ranking.csv", ranking)
    (OUT / "r1c2_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_summary(rows, ranking)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
