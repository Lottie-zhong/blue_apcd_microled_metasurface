from __future__ import annotations

import argparse
import csv
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi

NM = 1e-9
ROOT = Path(r"D:\project\blue_apcd_microled_metasurface")
SOURCE_3D = ROOT / "outputs" / "stage_rcled_mdc_blue_oujizi_dbr_only" / "rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp"
OUT = ROOT / "outputs" / "stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum"
FIG = OUT / "figures"
LOGS = OUT / "logs"
FSP = OUT / "rcled_mdc_blue_oujizi_2d_plane_wave_spectrum.fsp"
SCRIPT_PATH = ROOT / "scripts" / "blue_stage10_cp_zprop_validation" / "stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum.py"

DBR_LAYERS = []
z = 0.0
idx = 0
for pair in range(8):
    DBR_LAYERS.append((idx, f"DBR_{pair:02d}_sio222", "sio222", z, z + 100.0)); z += 100.0; idx += 1
    DBR_LAYERS.append((idx, f"DBR_{pair:02d}_tio22", "tio22", z, z + 52.0)); z += 52.0; idx += 1
DBR_LAYERS.append((idx, "DBR_08_sio222_terminal", "sio222", z, z + 100.0))
DBR_TOP_NM = z + 100.0
WAVELENGTHS_NM = np.arange(438.0, 468.0 + 0.001, 0.5)
FREQ_POINTS = len(WAVELENGTHS_NM)


def rows_to_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader(); writer.writerows(rows)


def material_names(fdtd: Any) -> set[str]:
    return {line.strip() for line in str(fdtd.getmaterial()).splitlines() if line.strip()}


def load_materials(lumapi: Any, runtime: Any) -> dict[str, Any]:
    if not SOURCE_3D.exists():
        raise FileNotFoundError(SOURCE_3D)
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        fdtd.load(str(SOURCE_3D))
        mats = {}
        for name in ("tio22", "sio222"):
            mats[name] = {
                "sampled_3d_data": fdtd.getmaterial(name, "sampled 3d data"),
                "mesh_order": float(fdtd.getmaterial(name, "Mesh order")),
                "color": fdtd.getmaterial(name, "color"),
            }
    finally:
        fdtd.close()
    return mats


def ensure_sampled(fdtd: Any, name: str, info: dict[str, Any]) -> None:
    if name in material_names(fdtd):
        return
    mid = fdtd.addmaterial("Sampled 3D data")
    fdtd.setmaterial(mid, "name", name)
    fdtd.setmaterial(name, "sampled 3d data", info["sampled_3d_data"])
    fdtd.setmaterial(name, "Mesh order", info["mesh_order"])
    fdtd.setmaterial(name, "color", info["color"])


def ensure_gan(fdtd: Any) -> None:
    name = "GaN_450nm_n2p56_custom"
    if name in material_names(fdtd):
        return
    mid = fdtd.addmaterial("(n,k) Material")
    fdtd.setmaterial(mid, "name", name)
    fdtd.setmaterial(name, "Refractive Index", 2.56)
    fdtd.setmaterial(name, "Imaginary Refractive Index", 0)
    fdtd.setmaterial(name, "Mesh order", 3)
    try:
        fdtd.setmaterial(name, "color", np.array([1.0, 0.35, 0.70, 0.45]))
    except Exception:
        pass


def layer_table() -> list[dict[str, Any]]:
    rows = [{"order_index": -1, "object_name": "GaN_continuous_region", "material": "GaN_450nm_n2p56_custom", "z_min_nm": -1200.0, "z_max_nm": 0.0, "thickness_nm": 1200.0, "role": "source_side_medium"}]
    for idx, name, mat, z0, z1 in DBR_LAYERS:
        rows.append({"order_index": idx, "object_name": name, "material": mat, "z_min_nm": z0, "z_max_nm": z1, "thickness_nm": z1 - z0, "role": "MDC_blue_oujizi_DBR"})
    rows.append({"order_index": 999, "object_name": "air_output_region", "material": "air", "z_min_nm": DBR_TOP_NM, "z_max_nm": 2400.0, "thickness_nm": 2400.0 - DBR_TOP_NM, "role": "output_side_medium"})
    return rows


def set_first_existing(fdtd: Any, props: list[tuple[str, Any]]) -> None:
    for prop, value in props:
        try:
            fdtd.set(prop, value)
        except Exception:
            continue


def build_model(lumapi: Any, runtime: Any, mats: dict[str, Any]) -> dict[str, Any]:
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        ensure_sampled(fdtd, "tio22", mats["tio22"])
        ensure_sampled(fdtd, "sio222", mats["sio222"])
        ensure_gan(fdtd)
        fdtd.addfdtd()
        fdtd.set("dimension", "2D")
        fdtd.set("x span", 2.0e-6); fdtd.set("y min", -1.0e-6); fdtd.set("y max", 2.4e-6)
        fdtd.set("x min bc", "Periodic"); fdtd.set("x max bc", "Periodic")
        fdtd.set("y min bc", "PML"); fdtd.set("y max bc", "PML")
        fdtd.set("mesh accuracy", 3); fdtd.set("simulation time", 200e-15)
        try: fdtd.setglobalmonitor("frequency points", FREQ_POINTS)
        except Exception: pass
        # layers
        fdtd.addrect(); fdtd.set("name", "GaN_continuous_region")
        fdtd.set("x", 0); fdtd.set("x span", 2.0e-6); fdtd.set("y min", -1.2e-6); fdtd.set("y max", 0); fdtd.set("material", "GaN_450nm_n2p56_custom")
        fdtd.addstructuregroup(); fdtd.set("name", "MDC_blue_oujizi_DBR_2D_group")
        fdtd.groupscope("::model::MDC_blue_oujizi_DBR_2D_group")
        for _, name, mat, z0, z1 in DBR_LAYERS:
            fdtd.addrect(); fdtd.set("name", name); fdtd.set("x", 0); fdtd.set("x span", 2.0e-6)
            fdtd.set("y min", z0 * NM); fdtd.set("y max", z1 * NM); fdtd.set("material", mat)
        fdtd.groupscope("::model")
        # monitors
        for name, zpos in (("T_up_monitor", 1.95e-6), ("R_down_monitor", -0.75e-6)):
            fdtd.addpower(); fdtd.set("name", name); fdtd.set("monitor type", "Linear X")
            fdtd.set("x", 0); fdtd.set("x span", 2.0e-6); fdtd.set("y", zpos)
            try: fdtd.set("override global monitor settings", 1); fdtd.set("frequency points", FREQ_POINTS)
            except Exception: pass
        # plane source
        fdtd.addplane(); fdtd.set("name", "normal_incidence_plane_wave")
        fdtd.set("injection axis", "y"); fdtd.set("direction", "Forward")
        fdtd.set("x", 0); fdtd.set("x span", 2.0e-6); fdtd.set("y", -0.45e-6)
        fdtd.set("wavelength start", 438 * NM); fdtd.set("wavelength stop", 468 * NM)
        fdtd.save(str(FSP))
    finally:
        fdtd.close()
    return {"fsp": str(FSP), "x_bc": "Periodic", "vertical_bc": "PML", "dimension": "2D", "sim_axis_mapping": "simulation y represents physical z", "mesh_accuracy": 3, "source_physical_z_nm": -450, "T_monitor_physical_z_nm": 1950, "R_monitor_physical_z_nm": -750}


def configure_pol(fdtd: Any, angle: float) -> None:
    fdtd.switchtolayout(); fdtd.select("normal_incidence_plane_wave")
    fdtd.set("polarization angle", angle)


def extract_spectrum(fdtd: Any, mode: str) -> list[dict[str, Any]]:
    # 2025 R1 exposes wavelength in the T result dataset, not as getdata(..., "lambda").
    t_res = fdtd.getresult("T_up_monitor", "T")
    r_res = fdtd.getresult("R_down_monitor", "T")
    lam = np.array(t_res["lambda"]).astype(float).ravel() / NM
    T = np.array(t_res["T"]).astype(float).ravel()
    Rraw = np.array(r_res["T"]).astype(float).ravel()
    # Downward monitor sign is negative for backward flux; use magnitude as reflection proxy.
    R = np.abs(Rraw)
    order = np.argsort(lam); lam = lam[order]; T = np.abs(T[order]); R = R[order]
    # Restrict to requested window and use whatever monitor points Lumerical returned.
    mask = (lam >= 437.9) & (lam <= 468.1)
    lam = lam[mask]; T = T[mask]; R = R[mask]
    tmax = float(np.max(T)) if len(T) else float("nan")
    rows = []
    for l, t, r in zip(lam, T, R):
        rows.append({"mode": mode, "wavelength_nm": float(l), "T_up": float(t), "R_down": float(r), "A_or_loss_proxy": float(1 - t - r), "T_norm": float(t / tmax) if tmax > 0 else float("nan")})
    return rows


def run_and_extract(lumapi: Any, runtime: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    run_rows: list[dict[str, Any]] = []
    # Two orthogonal plane-wave polarization angles at normal incidence.
    for mode, angle in (("pol0_angle0", 0.0), ("pol90_angle90", 90.0)):
        fdtd = lumapi.FDTD(hide=runtime.hide_gui)
        started = time.perf_counter()
        try:
            case_fsp = OUT / f"rcled_mdc_blue_oujizi_2d_plane_wave_spectrum_{mode}.fsp"
            if case_fsp.exists() and case_fsp.stat().st_size > 1_000_000:
                fdtd.load(str(case_fsp))
                status = "reused"
            else:
                fdtd.load(str(FSP)); configure_pol(fdtd, angle)
                fdtd.save(str(case_fsp)); fdtd.run(); fdtd.save(str(case_fsp))
                status = "ok"
            rows = extract_spectrum(fdtd, mode)
            all_rows.extend(rows)
            run_rows.append({"mode": mode, "polarization_angle_deg": angle, "status": status, "runtime_seconds": time.perf_counter() - started, "case_fsp": str(case_fsp), "case_fsp_bytes": case_fsp.stat().st_size})
        except Exception as exc:
            run_rows.append({"mode": mode, "polarization_angle_deg": angle, "status": "failed", "runtime_seconds": time.perf_counter() - started, "error": f"{type(exc).__name__}: {exc}"})
        finally:
            fdtd.close()
    return all_rows, run_rows


def interp_metric(rows: list[dict[str, Any]], wavelength: float) -> float:
    x = np.array([r["wavelength_nm"] for r in rows], dtype=float)
    y = np.array([r["T_norm"] for r in rows], dtype=float)
    return float(np.interp(wavelength, x, y))


def fwhm(rows: list[dict[str, Any]]) -> dict[str, Any]:
    x = np.array([r["wavelength_nm"] for r in rows], dtype=float)
    y = np.array([r["T_norm"] for r in rows], dtype=float)
    imax = int(np.argmax(y)); peak_x = float(x[imax]); peak_y = float(y[imax]); half = 0.5 * peak_y
    def crossing(left: bool) -> float | None:
        rng = range(imax, 0, -1) if left else range(imax, len(x) - 1)
        for i in rng:
            j = i - 1 if left else i + 1
            if (y[i] - half) * (y[j] - half) <= 0 and y[i] != y[j]:
                return float(x[i] + (half - y[i]) * (x[j] - x[i]) / (y[j] - y[i]))
        return None
    l = crossing(True); r = crossing(False)
    bounded = l is not None and r is not None
    return {"peak_wavelength_nm": peak_x, "peak_T_norm": peak_y, "left_halfmax_wavelength_nm": l, "right_halfmax_wavelength_nm": r, "FWHM_nm": (r - l) if bounded else None, "FWHM_bounded_in_scan": bounded, "FWHM_note": "bounded" if bounded else "FWHM not bounded in scan window; FWHM > 30 nm or peak/halfmax outside 438-468 nm"}


def summarize(spectrum: list[dict[str, Any]], run_rows: list[dict[str, Any]]) -> dict[str, Any]:
    modes = sorted({r["mode"] for r in spectrum})
    summaries = []
    for mode in modes:
        rows = [r for r in spectrum if r["mode"] == mode]
        out = {"mode": mode, **fwhm(rows)}
        out.update({"T_norm_447": interp_metric(rows, 447), "T_norm_450": interp_metric(rows, 450), "T_norm_453": interp_metric(rows, 453)})
        band = [r for r in rows if 447 <= r["wavelength_nm"] <= 453]
        out["avg_T_norm_447_453"] = float(np.mean([r["T_norm"] for r in band]))
        weights = np.array([math.exp(-4 * math.log(2) * ((r["wavelength_nm"] - 450.0) / 6.0) ** 2) for r in band])
        vals = np.array([r["T_norm"] for r in band])
        out["gaussian_fwhm6_weighted_T_norm_447_453"] = float(np.sum(weights * vals) / np.sum(weights))
        summaries.append(out)
    # compact TE/TM comparison proxy
    if len(summaries) == 2:
        summaries[0]["max_abs_Tnorm_difference_vs_other_mode"] = max(abs(a["T_norm"] - b["T_norm"]) for a, b in zip([r for r in spectrum if r["mode"] == modes[0]], [r for r in spectrum if r["mode"] == modes[1]]))
    result = {"source_3d_fsp": str(SOURCE_3D), "output_fsp": str(FSP), "wavelength_sampling_step_nm": 0.5, "run_rows": run_rows, "mode_summaries": summaries}
    (OUT / "mdc_blue_oujizi_2d_plane_wave_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def plot_outputs(spectrum: list[dict[str, Any]]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    FIG.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    modes = sorted({r["mode"] for r in spectrum})
    plt.figure(figsize=(7, 4))
    for mode in modes:
        rows = [r for r in spectrum if r["mode"] == mode]
        plt.plot([r["wavelength_nm"] for r in rows], [r["T_norm"] for r in rows], label=mode)
    plt.axvspan(447, 453, color="gray", alpha=0.15, label="447-453 nm")
    plt.xlabel("Wavelength (nm)"); plt.ylabel("T_norm"); plt.legend(); plt.tight_layout()
    p = FIG / "T_norm_vs_wavelength.png"; plt.savefig(p, dpi=180); plt.close(); paths.append(str(p))
    plt.figure(figsize=(7, 4))
    for mode in modes:
        rows = [r for r in spectrum if r["mode"] == mode]
        plt.plot([r["wavelength_nm"] for r in rows], [r["T_up"] for r in rows], label=f"T {mode}")
        plt.plot([r["wavelength_nm"] for r in rows], [r["R_down"] for r in rows], "--", label=f"R {mode}")
    plt.xlabel("Wavelength (nm)"); plt.ylabel("Power proxy"); plt.legend(fontsize=8); plt.tight_layout()
    p = FIG / "T_R_loss_proxy_vs_wavelength.png"; plt.savefig(p, dpi=180); plt.close(); paths.append(str(p))
    wl = np.arange(447, 453.001, 0.5)
    weights = np.exp(-4 * np.log(2) * ((wl - 450.0) / 6.0) ** 2)
    plt.figure(figsize=(7, 4)); plt.plot(wl, weights, marker="o"); plt.xlabel("Wavelength (nm)"); plt.ylabel("Gaussian FWHM=6 nm weight"); plt.tight_layout()
    p = FIG / "gaussian_fwhm6_weights_447_453.png"; plt.savefig(p, dpi=180); plt.close(); paths.append(str(p))
    if len(modes) == 2:
        rows0 = [r for r in spectrum if r["mode"] == modes[0]]; rows1 = [r for r in spectrum if r["mode"] == modes[1]]
        plt.figure(figsize=(7, 4)); plt.plot([r["wavelength_nm"] for r in rows0], [a["T_norm"] - b["T_norm"] for a, b in zip(rows0, rows1)])
        plt.xlabel("Wavelength (nm)"); plt.ylabel(f"T_norm {modes[0]} - {modes[1]}"); plt.tight_layout()
        p = FIG / "polarization_mode_comparison.png"; plt.savefig(p, dpi=180); plt.close(); paths.append(str(p))
    return paths


def write_reports(setup: dict[str, Any], spectrum: list[dict[str, Any]], summary: dict[str, Any], figs: list[str]) -> None:
    rows_to_csv(OUT / "vertical_stack_layers.csv", layer_table())
    rows_to_csv(OUT / "mdc_blue_oujizi_2d_plane_wave_spectrum.csv", spectrum)
    mode_rows = summary["mode_summaries"]
    first = mode_rows[0]
    md = [
        "# MDC_blue_oujizi 2D Plane-Wave Spectrum\n\n",
        f"- Source 3D FSP: `{SOURCE_3D}`\n",
        f"- 2D FSP: `{FSP}`\n",
        "- Scope: 2D x-z plane-wave only; no dipoles, no APCD/B4INT/metasurface, no finite patch.\n",
        "- Source: normal incidence from GaN/source side toward physical +z DBR/output side; Lumerical 2D uses simulation +y as physical +z.\n",
        "- Wavelength range: 438-468 nm; requested sampling step 0.5 nm.\n",
        "- Boundaries: x periodic, simulation y PML (physical z PML).\n",
        "- Monitors: `T_up_monitor` above DBR, `R_down_monitor` below/source side.\n",
        "- Mesh accuracy: 3.\n\n",
        "## Layer stack\n\n",
        "GaN source-side region, then `[sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm`, then air output side.\n\n",
        "## Spectral summary\n\n",
        "| mode | peak nm | FWHM nm | bounded | T447 | T450 | T453 | avg 447-453 | FWHM6 weighted |\n|---|---:|---:|---|---:|---:|---:|---:|---:|\n",
    ]
    for r in mode_rows:
        fwhm_text = "" if r["FWHM_nm"] is None else f"{r['FWHM_nm']:.3f}"
        md.append(f"| {r['mode']} | {r['peak_wavelength_nm']:.3f} | {fwhm_text} | {r['FWHM_bounded_in_scan']} | {r['T_norm_447']:.4f} | {r['T_norm_450']:.4f} | {r['T_norm_453']:.4f} | {r['avg_T_norm_447_453']:.4f} | {r['gaussian_fwhm6_weighted_T_norm_447_453']:.4f} |\n")
    near450 = abs(float(first["peak_wavelength_nm"]) - 450.0) <= 3.0
    high_window = min(float(first["T_norm_447"]), float(first["T_norm_450"]), float(first["T_norm_453"])) >= 0.7
    md += [
        "\n## Judgement\n\n",
        f"1. Spectral peak near 450 nm: {near450}.\n",
        f"2. FWHM: {first['FWHM_nm'] if first['FWHM_nm'] is not None else first['FWHM_note']}.\n",
        f"3. 447-453 nm remains in a high-response region: {high_window}.\n",
        f"4. A later RCLED/MicroLED FWHM about 6 nm spectrum is {'likely acceptable' if high_window else 'not clearly acceptable'} from this normal-incidence plane-wave proxy.\n",
        "5. Recommended next step: 2D dipole spectral-angle simulation, because this result is only a normal-incidence spectral proxy and cannot replace 2D/3D dipole angular emission validation.\n\n",
        "## Figures\n\n",
    ]
    for p in figs:
        md.append(f"- `{p}`\n")
    (OUT / "stage_rcled_mdc_blue_oujizi_2d_plane_wave_summary.md").write_text("".join(md), encoding="utf-8")
    (OUT / "setup_sanity.md").write_text("\n".join([
        "# Setup sanity",
        f"source_3d_fsp: {SOURCE_3D}",
        f"final_2d_fsp: {FSP}",
        "source_direction: physical +z from GaN/source side to DBR/output side; simulation +y in 2D",
        "source_wavelength_range_nm: 438-468",
        "wavelength_step_nm: 0.5 requested via 61 monitor points",
        "monitors: T_up_monitor, R_down_monitor",
        "boundaries: x periodic, simulation y PML (physical z PML)",
        "mesh_accuracy: 3",
        "polarization_modes: pol0_angle0, pol90_angle90",
        "confirmation: no APCD/B4INT/metasurface/dipole objects",
        "DBR: [sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm",
    ]) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-run", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True); LOGS.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    mats = load_materials(lumapi, runtime)
    setup = build_model(lumapi, runtime, mats)
    rows_to_csv(OUT / "vertical_stack_layers.csv", layer_table())
    manifest = {"script": str(SCRIPT_PATH), "source_3d_fsp": str(SOURCE_3D), "final_2d_fsp": str(FSP), "wavelength_start_nm": 438, "wavelength_stop_nm": 468, "wavelength_step_nm": 0.5, "modes": ["pol0_angle0", "pol90_angle90"], "setup": setup, "no_dipole": True, "no_metasurface": True}
    (OUT / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.dry_run:
        write_reports(setup, [], {"mode_summaries": [{"mode": "dry_run", "peak_wavelength_nm": 0, "FWHM_nm": None, "FWHM_bounded_in_scan": False, "FWHM_note": "dry run", "T_norm_447": 0, "T_norm_450": 0, "T_norm_453": 0, "avg_T_norm_447_453": 0, "gaussian_fwhm6_weighted_T_norm_447_453": 0}]}, [])
        print(json.dumps(manifest, indent=2)); return 0
    if args.skip_run:
        raise RuntimeError("skip-run extraction is not implemented for this first pass")
    spectrum, run_rows = run_and_extract(lumapi, runtime)
    rows_to_csv(OUT / "run_results.csv", run_rows)
    if any(r["status"] not in {"ok", "reused"} for r in run_rows):
        print(json.dumps(run_rows, indent=2)); return 1
    summary = summarize(spectrum, run_rows)
    figs = plot_outputs(spectrum)
    write_reports(setup, spectrum, summary, figs)
    (LOGS / "runner.log").write_text(json.dumps({"run_rows": run_rows, "figures": figs}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





