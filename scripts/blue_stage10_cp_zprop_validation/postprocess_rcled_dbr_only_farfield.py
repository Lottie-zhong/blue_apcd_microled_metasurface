from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from metasurface.config import load_runtime_config
from metasurface.lumapi_runner import import_lumapi


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "stage_rcled_dbr_only_farfield_postprocess"
MONITOR = "top_field_monitor_zprop"
ANGLES = (5.0, 10.0, 20.0, 30.0)
CASES = {
    "dbr_only_x": ROOT / "outputs" / "stage10_cp_dbr_1_gan_dbr_only" / "_saved_fsp" / "GAN_DBR_ONLY_CENTER_X_T100FS.fsp",
    "dbr_only_y": ROOT / "outputs" / "stage10_cp_dbr_1_gan_dbr_only" / "_saved_fsp" / "GAN_DBR_ONLY_CENTER_Y_T100FS.fsp",
    "no_dbr_x": ROOT / "outputs" / "stage10_cp_dbr_0_planar_sanity" / "_saved_fsp" / "DBR0_NO_DBR_REFERENCE_CENTER_X_T100FS.fsp",
    "no_dbr_y": ROOT / "outputs" / "stage10_cp_dbr_0_planar_sanity" / "_saved_fsp" / "DBR0_NO_DBR_REFERENCE_CENTER_Y_T100FS.fsp",
}


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def get_farfield(lumapi: Any, runtime: Any, path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if not path.exists() or path.stat().st_size < 1_000_000:
        raise FileNotFoundError(f"completed FSP missing: {path}")
    fdtd = lumapi.FDTD(hide=runtime.hide_gui)
    try:
        fdtd.load(str(path.resolve()))
        if not int(float(fdtd.getnamednumber(MONITOR))):
            raise RuntimeError(f"monitor missing: {MONITOR}")
        monitor_type = str(fdtd.getnamed(MONITOR, "monitor type"))
        monitor_z_nm = float(fdtd.getnamed(MONITOR, "z")) / 1e-9
        e2 = np.asarray(fdtd.farfield3d(MONITOR, 1), dtype=float).squeeze()
        ux = np.asarray(fdtd.farfieldux(MONITOR, 1), dtype=float).squeeze()
        uy = np.asarray(fdtd.farfielduy(MONITOR, 1), dtype=float).squeeze()
    finally:
        fdtd.close()
    while e2.ndim > 2:
        e2 = e2.sum(axis=-1).squeeze()
    if e2.shape == (uy.size, ux.size):
        e2 = e2.T
    if e2.shape != (ux.size, uy.size):
        raise RuntimeError(f"farfield shape mismatch: E2={e2.shape}, ux={ux.shape}, uy={uy.shape}")
    return ux, uy, e2, {"monitor_type": monitor_type, "monitor_z_nm": monitor_z_nm, "farfield_shape": list(e2.shape)}


def metrics(label: str, ux: np.ndarray, uy: np.ndarray, e2: np.ndarray) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    xx, yy = np.meshgrid(ux, uy, indexing="ij")
    rsq = xx * xx + yy * yy
    light = rsq <= 1.0
    cosn = np.sqrt(np.clip(1.0 - rsq, 0.0, None))
    cosn = np.maximum(cosn, 1e-6)
    theta = np.degrees(np.arcsin(np.sqrt(np.clip(rsq, 0.0, 1.0))))
    dux = float(abs(ux[1] - ux[0]))
    duy = float(abs(uy[1] - uy[0]))
    integrand = np.where(light, e2 / cosn, 0.0)
    p_total = float(integrand.sum() * dux * duy)
    row: dict[str, Any] = {"case_id": label, "data_mode": "farfield3d", "prop_axis": 3, "monitor_name": MONITOR, "P_total_solid_angle_proxy": p_total}
    for angle in ANGLES:
        p = float((integrand * ((theta <= angle) & light)).sum() * dux * duy)
        row[f"eta_{int(angle)}deg"] = p / p_total

    ix0 = int(np.argmin(np.abs(ux)))
    iy0 = int(np.argmin(np.abs(uy)))
    xcut = np.asarray(e2[:, iy0], dtype=float)
    ycut = np.asarray(e2[ix0, :], dtype=float)
    tx = np.degrees(np.arcsin(np.clip(ux, -1.0, 1.0)))
    ty = np.degrees(np.arcsin(np.clip(uy, -1.0, 1.0)))
    xnorm = xcut / xcut.max()
    ynorm = ycut / ycut.max()

    def cut_stats(t: np.ndarray, v: np.ndarray) -> tuple[float, float]:
        peak = float(t[int(np.argmax(v))])
        idx = np.flatnonzero(v >= 0.5)
        fwhm = float(t[idx[-1]] - t[idx[0]]) if idx.size else float("nan")
        return peak, fwhm

    row["x_cut_peak_deg"], row["x_cut_fwhm_deg"] = cut_stats(tx, xnorm)
    row["y_cut_peak_deg"], row["y_cut_fwhm_deg"] = cut_stats(ty, ynorm)
    return row, {"theta_x": tx, "xcut": xnorm, "theta_y": ty, "ycut": ynorm}


def save_plots(prefix: str, ux: np.ndarray, uy: np.ndarray, e2: np.ndarray, cuts: dict[str, np.ndarray]) -> list[str]:
    paths: list[str] = []
    norm = e2 / e2.max()
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.pcolormesh(ux, uy, norm.T, shading="auto", cmap="inferno")
    ax.set(xlabel="u_x", ylabel="u_y", title="Normalized far field |E|^2, normal +z", aspect="equal")
    fig.colorbar(im, ax=ax, label="Normalized intensity")
    fig.tight_layout()
    path = OUT / f"{prefix}_farfield_u_plane.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    paths.append(str(path))
    for axis in ("x", "y"):
        fig, ax = plt.subplots(figsize=(6.2, 4.2))
        ax.plot(cuts[f"theta_{axis}"], cuts[f"{axis}cut"], lw=1.6)
        ax.set(xlim=(-80, 80), ylim=(0, 1.05), xlabel=f"Angle from +z in {axis}-cut (deg)", ylabel="Normalized intensity", title=f"Far-field angular pattern: {axis}-cut")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        path = OUT / f"{prefix}_{axis}cut.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)
        paths.append(str(path))
    return paths


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config("configs/runtime.yaml")
    lumapi = import_lumapi(runtime)
    raw: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    debug: dict[str, Any] = {"no_fdtd_solve": True, "monitor": MONITOR, "prop_axis": 3, "cases": {}}
    rows: list[dict[str, Any]] = []
    pngs: list[str] = []
    for label, path in CASES.items():
        ux, uy, e2, info = get_farfield(lumapi, runtime, path)
        row, cuts = metrics(label, ux, uy, e2)
        row["fsp_path"] = str(path)
        rows.append(row)
        raw[label] = (ux, uy, e2)
        debug["cases"][label] = {"fsp_path": str(path), "fsp_size_bytes": path.stat().st_size, **info}
        if label.startswith("dbr_only"):
            pngs += save_plots(f"rcled_{label}", ux, uy, e2, cuts)

    combined_rows: list[dict[str, Any]] = []
    for stack in ("dbr_only", "no_dbr"):
        ux, uy, ex = raw[f"{stack}_x"]
        ux2, uy2, ey = raw[f"{stack}_y"]
        if not (np.allclose(ux, ux2) and np.allclose(uy, uy2)):
            raise RuntimeError(f"x/y grids differ for {stack}")
        summed = ex + ey
        row, cuts = metrics(f"{stack}_xy_incoherent", ux, uy, summed)
        combined_rows.append(row)
        pngs += save_plots(f"rcled_{stack}_xy_incoherent", ux, uy, summed, cuts)

    dbr = next(row for row in combined_rows if row["case_id"] == "dbr_only_xy_incoherent")
    ref = next(row for row in combined_rows if row["case_id"] == "no_dbr_xy_incoherent")
    comparison = {
        "comparison": "DBR-only versus no-DBR planar GaN reference",
        "eta_5deg_ratio": dbr["eta_5deg"] / ref["eta_5deg"],
        "eta_10deg_ratio": dbr["eta_10deg"] / ref["eta_10deg"],
        "eta_20deg_ratio": dbr["eta_20deg"] / ref["eta_20deg"],
        "eta_30deg_ratio": dbr["eta_30deg"] / ref["eta_30deg"],
        "x_fwhm_change_deg": dbr["x_cut_fwhm_deg"] - ref["x_cut_fwhm_deg"],
        "y_fwhm_change_deg": dbr["y_cut_fwhm_deg"] - ref["y_cut_fwhm_deg"],
        "narrowed_x": bool(dbr["x_cut_fwhm_deg"] < ref["x_cut_fwhm_deg"]),
        "narrowed_y": bool(dbr["y_cut_fwhm_deg"] < ref["y_cut_fwhm_deg"]),
    }
    write_csv(OUT / "farfield_case_metrics.csv", rows)
    write_csv(OUT / "farfield_incoherent_metrics.csv", combined_rows)
    write_csv(OUT / "farfield_dbr_vs_no_dbr.csv", [comparison])
    debug["exported_pngs"] = pngs
    debug["comparison"] = comparison
    (OUT / "farfield_postprocess_debug.json").write_text(json.dumps(debug, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"case_metrics": rows, "incoherent_metrics": combined_rows, "comparison": comparison, "pngs": pngs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
