from __future__ import annotations

import csv
import json
import math
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

NM = 1e-9
UM = 1e-6
ROOT = Path(r"D:\project\worktrees\blue_apcd_rcled_mdc")
sys.path.insert(0, str(ROOT / "src"))

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

OUT = ROOT / "outputs" / "r1c4_rcled_c2_cav230_source_y_robustness"
SAVED = OUT / "_saved_fsp"
LOGS = OUT / "logs"
STAGE_NAME = "R1C4_RCLED_C2_cav230_source_y_robustness"

N_GAN = 2.56
N_TIO2 = 2.60
N_SIO2 = 1.46
TOP_SIO2_NM = 100.0
TOP_TIO2_NM = 52.0
TOP_PAIR_COUNT = 6
BOTTOM_PAIR_COUNT = 0
CAVITY_SPAN_NM = 230.0
TERMINATION = "TiO2_50nm"
TERMINATION_THICKNESS_NM = 50.0
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
SOURCE_Y_OFFSETS_NM = [-40.0, -20.0, 0.0, 20.0, 40.0]
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


def offset_id(offset_nm: float) -> str:
    if offset_nm == 0:
        return "y0"
    return ("yp" if offset_nm > 0 else "ym") + str(int(abs(offset_nm)))


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


def build_case(fdtd: Any, source_y_offset_nm: float, wl_nm: float) -> dict[str, Any]:
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

    fdtd.addstructuregroup()
    fdtd.set("name", "RCLED_bottom_reflector_group")
    fdtd.groupscope("::model::RCLED_bottom_reflector_group")
    add_rect(fdtd, f"intentional_bottom_termination_{TERMINATION}", "TiO2_n2p6_custom", DBR_X_SPAN_UM, -TERMINATION_THICKNESS_NM, 0.0)
    fdtd.groupscope("::model")

    gan_min = 0.0
    gan_max = CAVITY_SPAN_NM
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
    fdtd.groupscope("::model")

    source_y_nm = (gan_min + gan_max) * 0.5 + source_y_offset_nm
    if not (gan_min < source_y_nm < gan_max):
        raise ValueError(f"source_y_nm outside GaN cavity: {source_y_nm}")
    fdtd.adddipole()
    fdtd.set("name", SOURCE)
    fdtd.set("x", 0)
    fdtd.set("y", source_y_nm * NM)
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
        "candidate_id": "R1C2_C2_cav230",
        "source_y_offset_nm": source_y_offset_nm,
        "source_y_nm": source_y_nm,
        "wavelength_nm": wl_nm,
        "fdtd_x_span_um": FDTD_X_SPAN_UM,
        "gan_device_x_span_um": DEVICE_X_SPAN_UM,
        "top_dbr_mdc_span_um": DBR_X_SPAN_UM,
        "bottom_pair_count": BOTTOM_PAIR_COUNT,
        "monitor_x_span_um": MONITOR_X_SPAN_UM,
        "monitor_y_um": MONITOR_Y_UM,
        "monitor_y_to_pml_um": FDTD_Y_MAX_UM - MONITOR_Y_UM,
        "monitor_inside_pml": False,
        "cavity_span_nm": CAVITY_SPAN_NM,
        "termination": TERMINATION,
        "termination_thickness_nm": TERMINATION_THICKNESS_NM,
        "top_group_exists": bool(fdtd.getnamednumber("RCLED_top_DBR_group")),
        "bottom_group_exists": bool(fdtd.getnamednumber("RCLED_bottom_reflector_group")),
        "gan_cavity_group_exists": bool(fdtd.getnamednumber("RCLED_GaN_cavity_group")),
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
    rings = {"ring_power_abs_0_10": frac(0, 10), "ring_power_abs_10_20": frac(10, 20), "ring_power_abs_20_30": frac(20, 30), "ring_power_abs_30_45": frac(30, 45)}
    zones = {"abs_0_5": frac(0, 5), "abs_5_10": frac(5, 10), "abs_10_20": frac(10, 20), "abs_20_30": frac(20, 30), "abs_30_45": frac(30, 45)}
    return {**etas, **rings, "FWHM_deg": fwhm, "peak_angle_deg": peak_angle, "peak_abs_angle_deg": abs(peak_angle), "P_total": total, "outside20": 1 - etas["eta20"], "dominant_zone": max(zones, key=zones.get), "near_normal_peak": abs(peak_angle) <= 10, "left_right_asymmetry": asym}


def run_case(lumapi: Any, runtime: Any, offset_nm: float, wl_nm: float) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    case_id = f"R1C4_{offset_id(offset_nm)}_{int(wl_nm)}nm"
    fsp = SAVED / f"{case_id}.fsp"
    log = LOGS / f"{case_id}.log"
    start = time.perf_counter()
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        if complete(fsp):
            fdtd.load(str(fsp))
            audit = {"case_id": case_id, "source_y_offset_nm": offset_nm, "wavelength_nm": wl_nm, "reused_existing_complete_fsp": True}
            status = "reused"
        else:
            audit = build_case(fdtd, offset_nm, wl_nm)
            setup = OUT / f"{case_id}_setup.fsp"
            fdtd.save(str(setup))
            fdtd.load(str(setup))
            fdtd.run()
            fdtd.save(str(fsp))
            status = "ok"
        metrics = angle_metrics(fdtd)
        row = {"candidate_id": "R1C2_C2_cav230", "source_y_offset_nm": offset_nm, "wavelength_nm": wl_nm, "dipole_orientation": "physical_x_theta90_phi0", "status": status, "runtime_s": time.perf_counter() - start, "result_fsp": str(fsp), **metrics}
        log.write_text(json.dumps(row, indent=2), encoding="utf-8")
        return row, audit, {"case_id": case_id, "status": status, "runtime_s": row["runtime_s"], "fsp_bytes": fsp.stat().st_size}
    finally:
        fdtd.close()


def rank(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    center_power = {r["wavelength_nm"]: float(r["P_total"]) for r in rows if float(r["source_y_offset_nm"]) == 0.0}
    out = []
    for off in SOURCE_Y_OFFSETS_NM:
        subset = [r for r in rows if float(r["source_y_offset_nm"]) == off]
        if len(subset) != len(WAVELENGTHS):
            continue
        passes = all(float(r["peak_abs_angle_deg"]) <= 15 and r["dominant_zone"] in {"abs_0_5", "abs_5_10", "abs_10_20"} for r in subset)
        power_ok = all(float(r["P_total"]) >= 0.5 * center_power.get(r["wavelength_nm"], float(r["P_total"])) for r in subset)
        avg_eta20 = sum(float(r["eta20"]) for r in subset) / len(subset)
        out.append({"source_y_offset_nm": off, "robustness_pass": passes, "power_not_collapsed_vs_center": power_ok, "avg_eta20": avg_eta20, "min_eta20": min(float(r["eta20"]) for r in subset), "max_peak_abs_angle_deg": max(float(r["peak_abs_angle_deg"]) for r in subset), "worst_dominant_zone": max((r["dominant_zone"] for r in subset), key=lambda z: ["abs_0_5", "abs_5_10", "abs_10_20", "abs_20_30", "abs_30_45"].index(z))})
    out.sort(key=lambda r: (not r["robustness_pass"], not r["power_not_collapsed_vs_center"], -float(r["avg_eta20"])))
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def write_summary(rows: list[dict[str, Any]], ranking: list[dict[str, Any]]) -> None:
    best = ranking[0]
    center = next(r for r in ranking if float(r["source_y_offset_nm"]) == 0.0)
    worst = max(ranking, key=lambda r: (not r["robustness_pass"], r["max_peak_abs_angle_deg"]))
    all_pass = all(r["robustness_pass"] for r in ranking)
    ready = all_pass and bool(best["power_not_collapsed_vs_center"])
    lines = ["# R1C4 RCLED C2 cav230 source-y robustness", "", "2D FDTD source-y robustness for frozen R1C2_C2_cav230. No forbidden integration, no bottom DBR, no cavity/termination sweep.", "", f"Center source remains best: `{center['rank'] == 1}`.", f"Source-y robustness passes all offsets: `{all_pass}`.", f"Worst source_y_offset_nm: `{worst['source_y_offset_nm']}`.", f"Best robust source_y_offset_nm: `{best['source_y_offset_nm']}`.", f"Ready for later coupling: `{ready}`.", "Integration with downstream metasurfaces has not been run.", "", "| source_y_offset_nm | wl | eta10 | eta20 | eta30 | peak_abs | zone | near | P_total |", "|---:|---:|---:|---:|---:|---:|---|---|---:|"]
    for r in rows:
        lines.append(f"| {float(r['source_y_offset_nm']):.0f} | {float(r['wavelength_nm']):.0f} | {float(r['eta10']):.4f} | {float(r['eta20']):.4f} | {float(r['eta30']):.4f} | {float(r['peak_abs_angle_deg']):.2f} | {r['dominant_zone']} | {r['near_normal_peak']} | {float(r['P_total']):.6g} |")
    (OUT / "r1c4_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    SAVED.mkdir(exist_ok=True)
    LOGS.mkdir(exist_ok=True)
    runtime_path = ROOT / "configs/runtime.yaml"
    if runtime_path.exists():
        runtime = load_runtime_config(runtime_path)
        lumapi = import_lumapi(runtime)
    else:
        sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
        import lumapi  # type: ignore[import-not-found]
        runtime = SimpleNamespace(hide_gui=True)
    rows: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    debug: list[dict[str, Any]] = []
    for off in SOURCE_Y_OFFSETS_NM:
        for wl in WAVELENGTHS:
            row, audit, dbg = run_case(lumapi, runtime, off, wl)
            rows.append(row); audits.append(audit); debug.append(dbg)
            print(f"source_y={off:+.0f}nm {wl:.0f}nm {row['status']} eta20={row['eta20']:.4g} peak={row['peak_abs_angle_deg']:.2f}", flush=True)
    ranking = rank(rows)
    rows_to_csv(OUT / "r1c4_source_y_results.csv", rows)
    (OUT / "r1c4_source_y_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    rows_to_csv(OUT / "r1c4_geometry_audit.csv", audits)
    rows_to_csv(OUT / "r1c4_ranking.csv", ranking)
    (OUT / "r1c4_debug.json").write_text(json.dumps(debug, indent=2), encoding="utf-8")
    write_summary(rows, ranking)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
