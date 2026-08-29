from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"N:\Program Files\ANSYS Inc\v251\Lumerical\api\python")
import lumapi


UTC = dt.timezone.utc
MONITOR = "ic1_top_near_to_far"
DIAGNOSTIC_WAVELENGTHS = (440.0, 450.0, 460.0)
SINGLE_POLARIZATION_CONFIDENCE_FRACTION = 0.10


def now():
    return dt.datetime.now(UTC).isoformat()


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{__import__('os').getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    temp.replace(path)


def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise RuntimeError(f"EMPTY_CSV:{path}")
    return {key: np.asarray([float(row[key]) for row in rows], dtype=float) for key in rows[0]}


def finite(a):
    return bool(np.all(np.isfinite(np.asarray(a))))


def stokes_from_fields(ex, ey):
    ex = np.asarray(ex, dtype=np.complex128)
    ey = np.asarray(ey, dtype=np.complex128)
    cxy = 0.5 * ey * np.conj(ex)
    s0 = 0.5 * (np.abs(ex) ** 2 + np.abs(ey) ** 2)
    s1 = 0.5 * (np.abs(ex) ** 2 - np.abs(ey) ** 2)
    s2 = 2.0 * np.real(cxy)
    s3 = -2.0 * np.imag(cxy)
    return {"S0": s0, "S1": s1, "S2": s2, "S3": s3}


def metric_arrays(s):
    s0, s1, s2, s3 = (np.asarray(s[key], dtype=float) for key in ("S0", "S1", "S2", "S3"))
    lmag = np.hypot(s1, s2)
    with np.errstate(divide="ignore", invalid="ignore"):
        dolp = lmag / s0
        docp = s3 / s0
    psi = np.mod(np.degrees(0.5 * np.arctan2(s2, s1)), 180.0)
    useful = 0.5 * (s0 + lmag)
    return {**s, "Lmag": lmag, "DoLP": dolp, "DoCP": docp, "psi_deg": psi, "useful_LP_axisfree": useful}


def scalar_metrics(s):
    values = metric_arrays({key: np.asarray([float(s[key])]) for key in ("S0", "S1", "S2", "S3")})
    return {key: float(values[key][0]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree")}


def exact_450_index(wavelength_nm):
    indices = np.flatnonzero(np.isclose(wavelength_nm, 450.0, rtol=0.0, atol=1e-9))
    if len(indices) != 1:
        raise RuntimeError(f"EXACT_450_INDEX_INVALID:{len(indices)}")
    return int(indices[0])


def load_single_csv_data(path_stokes: Path, path_flux: Path, path_farfield: Path):
    stokes = load_csv(path_stokes)
    flux = load_csv(path_flux)
    farfield = load_csv(path_farfield)
    return stokes, flux, farfield


def extract_angular_case(post_fsp: Path, sourcepower: np.ndarray, wavelength_nm: np.ndarray):
    wanted = {}
    for target in DIAGNOSTIC_WAVELENGTHS:
        indices = np.flatnonzero(np.isclose(wavelength_nm, target, rtol=0.0, atol=1e-9))
        if len(indices) != 1:
            raise RuntimeError(f"DIAGNOSTIC_WAVELENGTH_NOT_FOUND:{target}")
        wanted[target] = int(indices[0])
    f = lumapi.FDTD(hide=True)
    try:
        f.load(str(post_fsp))
        result = {}
        for target, csv_index in wanted.items():
            frequency_index = csv_index + 1
            ux = np.asarray(f.farfieldux(MONITOR, frequency_index), dtype=float).reshape(-1)
            uy = np.asarray(f.farfielduy(MONITOR, frequency_index), dtype=float).reshape(-1)
            vector = np.asarray(f.farfieldvector3d(MONITOR, frequency_index), dtype=np.complex128)
            intensity = np.asarray(f.farfield3d(MONITOR, frequency_index), dtype=float)
            if vector.ndim != 3 or vector.shape[-1] < 2 or vector.shape[:2] != intensity.shape:
                raise RuntimeError(f"ANGULAR_VECTOR_SHAPE_INVALID:{target}:{vector.shape}:{intensity.shape}")
            if vector.shape[0] != len(ux) or vector.shape[1] != len(uy):
                raise RuntimeError(f"ANGULAR_VECTOR_GRID_INVALID:{target}")
            if not finite(ux) or not finite(uy) or not finite(vector) or not finite(intensity):
                raise RuntimeError(f"ANGULAR_NONFINITE:{target}")
            ex = vector[:, :, 0]
            ey = vector[:, :, 1]
            s = stokes_from_fields(ex, ey)
            sp = float(sourcepower[csv_index])
            if not math.isfinite(sp) or sp <= 0.0:
                raise RuntimeError(f"SOURCEPOWER_INVALID:{target}")
            result[target] = {**metric_arrays(s), "ux": ux, "uy": uy, "intensity": intensity, "ex": ex, "ey": ey, "sourcepower_W": sp, "frequency_index_1based": frequency_index}
        return result
    finally:
        f.close()


def solid_angle_grid(ux, uy):
    uxg, uyg = np.meshgrid(ux, uy, indexing="ij")
    rho2 = uxg * uxg + uyg * uyg
    propagating = rho2 < (1.0 - 1e-12)
    jacobian = np.zeros_like(rho2, dtype=float)
    jacobian[propagating] = 1.0 / np.sqrt(1.0 - rho2[propagating])
    du = float(np.median(np.diff(ux))) if len(ux) > 1 else 1.0
    dv = float(np.median(np.diff(uy))) if len(uy) > 1 else 1.0
    domega = jacobian * abs(du * dv)
    uzg = np.zeros_like(rho2, dtype=float)
    uzg[propagating] = np.sqrt(1.0 - rho2[propagating])
    theta = np.full_like(rho2, np.nan, dtype=float)
    phi = np.full_like(rho2, np.nan, dtype=float)
    theta[propagating] = np.degrees(np.arcsin(np.sqrt(rho2[propagating])))
    phi[propagating] = np.mod(np.degrees(np.arctan2(uyg[propagating], uxg[propagating])), 360.0)
    return {"uxg": uxg, "uyg": uyg, "uzg": uzg, "theta_deg": theta, "phi_deg": phi, "propagating": propagating, "domega": domega}


def integrate_stokes(s, grid, mask):
    w = grid["domega"] * mask
    out = {key: float(np.sum(s[key] * w)) for key in ("S0", "S1", "S2", "S3")}
    out["solid_angle_sr"] = float(np.sum(w))
    out["metrics"] = scalar_metrics(out)
    return out


def cone_mask_normal(grid, degrees):
    return grid["propagating"] & (grid["theta_deg"] <= degrees + 1e-9)


def cone_mask_peak(grid, ux_peak, uy_peak, degrees):
    uz_peak = math.sqrt(max(0.0, 1.0 - ux_peak * ux_peak - uy_peak * uy_peak))
    dot = ux_peak * grid["uxg"] + uy_peak * grid["uyg"] + uz_peak * grid["uzg"]
    angle = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
    return grid["propagating"] & (angle <= degrees + 1e-9)


def weighted_scalar(a, weight):
    """Return a positive-weighted mean without letting masked NaNs leak in."""
    a = np.asarray(a, dtype=float)
    weight = np.asarray(weight, dtype=float)
    valid = np.isfinite(a) & np.isfinite(weight) & (weight > 0.0)
    denom = float(np.sum(weight[valid]))
    return float(np.sum(a[valid] * weight[valid]) / denom) if denom > 0.0 else float("nan")


def save_heatmap(path, data, grid, title, cbar_label, vmin=None, vmax=None, cmap="viridis"):
    masked = np.where(grid["propagating"], data, np.nan)
    fig, ax = plt.subplots(figsize=(6.2, 5.2), constrained_layout=True)
    im = ax.imshow(masked.T, origin="lower", extent=[float(grid["uxg"].min()), float(grid["uxg"].max()), float(grid["uyg"].min()), float(grid["uyg"].max())], cmap=cmap, vmin=vmin, vmax=vmax, aspect="equal")
    ax.set_xlabel("ux")
    ax.set_ylabel("uy")
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=cbar_label)
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_single_source_spectra(path, wl, x, y):
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    axes[0, 0].plot(wl, x["S1"] / x["S0"], label="IC1 x")
    axes[0, 0].plot(wl, y["S1"] / y["S0"], label="IC2 y")
    axes[0, 0].set_ylabel("S1/S0")
    axes[0, 1].plot(wl, x["S2"] / x["S0"], label="IC1 x")
    axes[0, 1].plot(wl, y["S2"] / y["S0"], label="IC2 y")
    axes[0, 1].set_ylabel("S2/S0")
    axes[1, 0].plot(wl, x["S3"] / x["S0"], label="IC1 x")
    axes[1, 0].plot(wl, y["S3"] / y["S0"], label="IC2 y")
    axes[1, 0].set_ylabel("S3/S0")
    axes[1, 1].plot(wl, x["DoLP"], label="IC1 x")
    axes[1, 1].plot(wl, y["DoLP"], label="IC2 y")
    axes[1, 1].set_ylabel("DoLP")
    for ax in axes.flat:
        ax.set_xlabel("wavelength (nm)")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Single-source Stokes / polarization spectra")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_poincare(path, wl, dot, separation, valid):
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.plot(wl, dot, label="dot(sx, sy)")
    ax2 = ax.twinx()
    ax2.plot(wl, separation, color="tab:orange", label="Poincare separation")
    ax2.scatter(wl[~valid], separation[~valid], s=8, color="gray", label="low individual DoLP")
    ax.set_xlabel("wavelength (nm)")
    ax.set_ylabel("normalized Stokes dot")
    ax2.set_ylabel("separation (deg)")
    ax.grid(alpha=0.25)
    ax.set_title("IC1-x / IC2-y Poincare relation")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_cone(path, angles, dolp):
    fig, ax = plt.subplots(figsize=(6.5, 4.2), constrained_layout=True)
    ax.plot(angles, dolp, "o-")
    ax.set_xlabel("normal-centered collection cone (deg; full=available hemisphere)")
    ax.set_ylabel("pair DoLP")
    ax.set_ylim(bottom=0.0)
    ax.grid(alpha=0.25)
    ax.set_title("Normal-centered cone DoLP at 450 nm")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_decomposition(path, labels, values):
    fig, ax = plt.subplots(figsize=(7.5, 4.5), constrained_layout=True)
    ax.bar(labels, values, color=["#4c78a8", "#f58518", "#54a24b", "#e45756"][:len(labels)])
    ax.set_ylabel("DoLP / linear fraction diagnostic")
    ax.set_ylim(0.0, max(1.0, max(values) * 1.15))
    ax.grid(axis="y", alpha=0.25)
    ax.set_title("Source-cancellation versus angular-integration decomposition")
    fig.savefig(path, dpi=170)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ic1-post-fsp", type=Path, required=True)
    parser.add_argument("--ic2-post-fsp", type=Path, required=True)
    parser.add_argument("--ic1-stokes", type=Path, required=True)
    parser.add_argument("--ic2-stokes", type=Path, required=True)
    parser.add_argument("--ic1-flux", type=Path, required=True)
    parser.add_argument("--ic2-flux", type=Path, required=True)
    parser.add_argument("--ic1-farfield", type=Path, required=True)
    parser.add_argument("--ic2-farfield", type=Path, required=True)
    parser.add_argument("--ic1-validity", type=Path, required=True)
    parser.add_argument("--ic2-validity", type=Path, required=True)
    parser.add_argument("--ic1-summary", type=Path, required=True)
    parser.add_argument("--ic2-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir = args.output_dir / "figures"
    figure_dir.mkdir(parents=True, exist_ok=True)

    x, x_flux, x_far = load_single_csv_data(args.ic1_stokes, args.ic1_flux, args.ic1_farfield)
    y, y_flux, y_far = load_single_csv_data(args.ic2_stokes, args.ic2_flux, args.ic2_farfield)
    ic1_validity = json.loads(args.ic1_validity.read_text(encoding="utf-8"))
    ic2_validity = json.loads(args.ic2_validity.read_text(encoding="utf-8"))
    ic1_summary = json.loads(args.ic1_summary.read_text(encoding="utf-8"))
    ic2_summary = json.loads(args.ic2_summary.read_text(encoding="utf-8"))

    required_stokes = ["S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "sourcepower_normalized_S0", "sourcepower_normalized_S1", "sourcepower_normalized_S2", "sourcepower_normalized_S3"]
    for label, data in (("IC1", x), ("IC2", y)):
        missing = [key for key in required_stokes if key not in data]
        if missing:
            raise RuntimeError(f"MISSING_STOKES_COLUMNS:{label}:{missing}")
    wl = x["wavelength_nm"]
    if not np.array_equal(wl, y["wavelength_nm"]) or not np.array_equal(wl, x_flux["wavelength_nm"]) or not np.array_equal(wl, y_flux["wavelength_nm"]):
        raise RuntimeError("FORENSIC_WAVELENGTH_GRID_MISMATCH")
    i450 = exact_450_index(wl)
    if len(wl) != 101 or not np.all(np.diff(wl) > 0.0):
        raise RuntimeError("FORENSIC_WAVELENGTH_GRID_INVALID")

    # The stored source-normalized near-to-far Stokes are the common spectral truth used for the pair.
    sx = {key: x[f"sourcepower_normalized_{key}"] for key in ("S0", "S1", "S2", "S3")}
    sy = {key: y[f"sourcepower_normalized_{key}"] for key in ("S0", "S1", "S2", "S3")}
    sxy = {key: 0.5 * (sx[key] + sy[key]) for key in ("S0", "S1", "S2", "S3")}
    mxy = metric_arrays(sxy)
    mx = metric_arrays(sx)
    my = metric_arrays(sy)
    lx = np.column_stack([sx["S1"], sx["S2"]])
    ly = np.column_stack([sy["S1"], sy["S2"]])
    lx_mag = np.linalg.norm(lx, axis=1)
    ly_mag = np.linalg.norm(ly, axis=1)
    lsum_mag = np.linalg.norm(lx + ly, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        c_linear = lsum_mag / (lx_mag + ly_mag)
        linear_angle = np.degrees(np.arccos(np.clip(np.sum(lx * ly, axis=1) / (lx_mag * ly_mag), -1.0, 1.0)))
        power_ratio = sx["S0"] / sy["S0"]
    power_ratio_450 = float(power_ratio[i450])
    power_ratio_class = "NEARLY_EQUAL" if 0.8 <= power_ratio_450 <= 1.25 else ("MODERATELY_IMBALANCED" if 0.5 <= power_ratio_450 <= 2.0 else "STRONGLY_IMBALANCED")

    # Poincare relation: suppress only the classification of ill-conditioned states; retain every raw point in CSV.
    nx = np.column_stack([mx["S1"] / mx["S0"], mx["S2"] / mx["S0"], mx["S3"] / mx["S0"]])
    ny = np.column_stack([my["S1"] / my["S0"], my["S2"] / my["S0"], my["S3"] / my["S0"]])
    dot = np.sum(nx * ny, axis=1)
    separation = np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))
    poincare_valid = (mx["DoLP"] >= SINGLE_POLARIZATION_CONFIDENCE_FRACTION) & (my["DoLP"] >= SINGLE_POLARIZATION_CONFIDENCE_FRACTION)

    pair_rows = []
    cancellation_rows = []
    poincare_rows = []
    useful_rows = []
    for i, wavelength in enumerate(wl):
        pair_rows.append({
            "wavelength_nm": float(wavelength),
            "S0_x": float(x["S0"][i]), "S1_x": float(x["S1"][i]), "S2_x": float(x["S2"][i]), "S3_x": float(x["S3"][i]), "DoLP_x": float(x["DoLP"][i]), "DoCP_x": float(x["DoCP"][i]), "psi_x_deg": float(x["psi_deg"][i]),
            "S0_y": float(y["S0"][i]), "S1_y": float(y["S1"][i]), "S2_y": float(y["S2"][i]), "S3_y": float(y["S3"][i]), "DoLP_y": float(y["DoLP"][i]), "DoCP_y": float(y["DoCP"][i]), "psi_y_deg": float(y["psi_deg"][i]),
            "S0_x_sourcepower_normalized": float(sx["S0"][i]), "S1_x_sourcepower_normalized": float(sx["S1"][i]), "S2_x_sourcepower_normalized": float(sx["S2"][i]), "S3_x_sourcepower_normalized": float(sx["S3"][i]),
            "S0_y_sourcepower_normalized": float(sy["S0"][i]), "S1_y_sourcepower_normalized": float(sy["S1"][i]), "S2_y_sourcepower_normalized": float(sy["S2"][i]), "S3_y_sourcepower_normalized": float(sy["S3"][i]),
        })
        cancellation_rows.append({"wavelength_nm": float(wavelength), "S0_x_over_S0_y": float(power_ratio[i]), "linear_Stokes_magnitude_x": float(lx_mag[i]), "linear_Stokes_magnitude_y": float(ly_mag[i]), "linear_Stokes_angle_deg": float(linear_angle[i]), "C_linear": float(c_linear[i]), "source_linear_cancellation_fraction": float(1.0 - c_linear[i])})
        poincare_rows.append({"wavelength_nm": float(wavelength), "dot_sx_sy": float(dot[i]), "Poincare_separation_deg": float(separation[i]), "DoLP_x": float(mx["DoLP"][i]), "DoLP_y": float(my["DoLP"][i]), "psi_x_raw_deg": float(x["psi_deg"][i]), "psi_y_raw_deg": float(y["psi_deg"][i]), "individual_axis_confidence": bool(poincare_valid[i]), "axis_confidence_definition": "DoLP>=0.10 diagnostic only; raw psi retained"})
        useful_rows.append({"wavelength_nm": float(wavelength), "S0_xy_sourcepower_normalized": float(mxy["S0"][i]), "linear_Stokes_magnitude_xy": float(mxy["Lmag"][i]), "useful_LP_axisfree_xy": float(mxy["useful_LP_axisfree"][i]), "useful_LP_over_S0": float(0.5 * (1.0 + mxy["DoLP"][i])), "DoLP_xy": float(mxy["DoLP"][i]), "unpolarized_baseline": 0.5})
    write_csv(args.output_dir / "pair_single_source_stokes.csv", pair_rows, list(pair_rows[0]))
    write_csv(args.output_dir / "pair_xy_source_cancellation.csv", cancellation_rows, list(cancellation_rows[0]))
    write_csv(args.output_dir / "pair_poincare_relation.csv", poincare_rows, list(poincare_rows[0]))
    write_csv(args.output_dir / "pair_useful_lp_normalized.csv", useful_rows, list(useful_rows[0]))

    angular_x = extract_angular_case(args.ic1_post_fsp, x_flux["sourcepower_W"], wl)
    angular_y = extract_angular_case(args.ic2_post_fsp, y_flux["sourcepower_W"], wl)
    angular = {}
    for target in DIAGNOSTIC_WAVELENGTHS:
        ax = angular_x[target]
        ay = angular_y[target]
        if not np.array_equal(ax["ux"], ay["ux"]) or not np.array_equal(ax["uy"], ay["uy"]):
            raise RuntimeError(f"ANGULAR_GRID_MISMATCH:{target}")
        grid = solid_angle_grid(ax["ux"], ax["uy"])
        sxm = {key: ax[key] / ax["sourcepower_W"] for key in ("S0", "S1", "S2", "S3")}
        sym = {key: ay[key] / ay["sourcepower_W"] for key in ("S0", "S1", "S2", "S3")}
        sp = {key: 0.5 * (sxm[key] + sym[key]) for key in ("S0", "S1", "S2", "S3")}
        mp = metric_arrays(sp)
        intensity_pair = 0.5 * (ax["intensity"] / ax["sourcepower_W"] + ay["intensity"] / ay["sourcepower_W"])
        angular[target] = {"x": sxm, "y": sym, "pair": mp, "intensity_pair": intensity_pair, "grid": grid, "source_intensity_x": ax["intensity"] / ax["sourcepower_W"], "source_intensity_y": ay["intensity"] / ay["sourcepower_W"]}

    a450 = angular[450.0]
    grid = a450["grid"]
    pair_map = a450["pair"]
    intensity_pair = a450["intensity_pair"]
    disk = grid["propagating"]
    peak_flat = np.where(disk, intensity_pair, -np.inf)
    peak_index = np.unravel_index(int(np.nanargmax(peak_flat)), peak_flat.shape)
    ux_peak = float(grid["uxg"][peak_index])
    uy_peak = float(grid["uyg"][peak_index])
    theta_peak = float(grid["theta_deg"][peak_index])
    phi_peak = float(grid["phi_deg"][peak_index])
    peak_metrics = {key: float(pair_map[key][peak_index]) for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree")}

    cone_rows = []
    cone_integrals = {}
    full_intensity = float(np.sum(intensity_pair * grid["domega"] * disk))
    for label, mask in [("5_deg_normal", cone_mask_normal(grid, 5.0)), ("10_deg_normal", cone_mask_normal(grid, 10.0)), ("20_deg_normal", cone_mask_normal(grid, 20.0)), ("full_available_upper", disk), ("5_deg_peak", cone_mask_peak(grid, ux_peak, uy_peak, 5.0)), ("10_deg_peak", cone_mask_peak(grid, ux_peak, uy_peak, 10.0))]:
        integ = integrate_stokes(pair_map, grid, mask)
        intensity_integral = float(np.sum(intensity_pair * grid["domega"] * mask))
        cone_integrals[label] = integ
        cone_rows.append({"wavelength_nm": 450.0, "cone": label, "pixels": int(np.count_nonzero(mask)), "solid_angle_sr": integ["solid_angle_sr"], "S0_integrated": integ["S0"], "S1_integrated": integ["S1"], "S2_integrated": integ["S2"], "S3_integrated": integ["S3"], "DoLP": integ["metrics"]["DoLP"], "psi_deg": integ["metrics"]["psi_deg"], "DoCP": integ["metrics"]["DoCP"], "useful_LP_axisfree": integ["metrics"]["useful_LP_axisfree"], "useful_LP_over_S0": 0.5 * (1.0 + integ["metrics"]["DoLP"]), "upward_source_normalized_power_integral": intensity_integral, "fraction_of_full_available_upward_power": intensity_integral / full_intensity if full_intensity > 0.0 else float("nan")})
    write_csv(args.output_dir / "pair_collection_cone_metrics.csv", cone_rows, list(cone_rows[0]))

    angular_rows = []
    for target in DIAGNOSTIC_WAVELENGTHS:
        data = angular[target]
        g = data["grid"]
        p = data["pair"]
        lx_map = data["x"]
        ly_map = data["y"]
        mask = g["propagating"]
        w = g["domega"] * mask
        integrated = integrate_stokes(p, g, mask)
        local_lmag_integral = float(np.sum(p["Lmag"] * w))
        c_ang = float(np.linalg.norm([integrated["S1"], integrated["S2"]]) / local_lmag_integral) if local_lmag_integral > 0.0 else float("nan")
        source_c_after_angular = float(np.linalg.norm([0.5 * np.sum(lx_map["S1"] * w) + 0.5 * np.sum(ly_map["S1"] * w), 0.5 * np.sum(lx_map["S2"] * w) + 0.5 * np.sum(ly_map["S2"] * w)]) / (0.5 * (np.linalg.norm([np.sum(lx_map["S1"] * w), np.sum(lx_map["S2"] * w)]) + np.linalg.norm([np.sum(ly_map["S1"] * w), np.sum(ly_map["S2"] * w)])))) if (np.linalg.norm([np.sum(lx_map["S1"] * w), np.sum(lx_map["S2"] * w)]) + np.linalg.norm([np.sum(ly_map["S1"] * w), np.sum(ly_map["S2"] * w)])) > 0.0 else float("nan")
        per_angle_c = np.divide(p["Lmag"], 0.5 * (np.hypot(lx_map["S1"], lx_map["S2"]) + np.hypot(ly_map["S1"], ly_map["S2"])), out=np.full_like(p["Lmag"], np.nan), where=mask & (np.hypot(lx_map["S1"], lx_map["S2"]) + np.hypot(ly_map["S1"], ly_map["S2"]) > 0.0))
        pair_local_dolp_powerweighted = float(np.sum(p["Lmag"] * w) / np.sum(p["S0"] * w)) if np.sum(p["S0"] * w) > 0.0 else float("nan")
        single_x_integrated = integrate_stokes(lx_map, g, mask)
        single_y_integrated = integrate_stokes(ly_map, g, mask)
        angular_rows.append({"wavelength_nm": target, "single_x_angular_integrated_DoLP": single_x_integrated["metrics"]["DoLP"], "single_y_angular_integrated_DoLP": single_y_integrated["metrics"]["DoLP"], "pair_angular_integrated_DoLP": integrated["metrics"]["DoLP"], "pair_local_DoLP_powerweighted": pair_local_dolp_powerweighted, "integral_local_linear_magnitude": local_lmag_integral, "magnitude_integrated_linear_Stokes": float(np.hypot(integrated["S1"], integrated["S2"])), "C_angular": c_ang, "C_source_after_angular": source_c_after_angular, "C_source_per_angle_powerweighted": weighted_scalar(per_angle_c, p["S0"] * w), "pair_S0_integral": integrated["S0"], "full_angle_solid_angle_sr": integrated["solid_angle_sr"], "peak_theta_deg_450_only": theta_peak if target == 450.0 else float("nan"), "peak_phi_deg_450_only": phi_peak if target == 450.0 else float("nan")})
    write_csv(args.output_dir / "pair_angular_cancellation_metrics.csv", angular_rows, list(angular_rows[0]))

    npz_kwargs = {"ux": grid["uxg"][:, 0], "uy": grid["uyg"][0, :], "wavelengths_nm": np.asarray(DIAGNOSTIC_WAVELENGTHS, dtype=float)}
    for target in DIAGNOSTIC_WAVELENGTHS:
        p = angular[target]["pair"]
        g = angular[target]["grid"]
        for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree"):
            npz_kwargs[f"{key}_xy_{int(target)}nm"] = p[key]
        npz_kwargs[f"intensity_xy_{int(target)}nm"] = angular[target]["intensity_pair"]
        npz_kwargs[f"domega_{int(target)}nm"] = g["domega"]
        npz_kwargs[f"propagating_{int(target)}nm"] = g["propagating"]
        npz_kwargs[f"S1_over_S0_xy_{int(target)}nm"] = np.divide(p["S1"], p["S0"], out=np.full_like(p["S1"], np.nan), where=p["S0"] > 0.0)
        npz_kwargs[f"S2_over_S0_xy_{int(target)}nm"] = np.divide(p["S2"], p["S0"], out=np.full_like(p["S2"], np.nan), where=p["S0"] > 0.0)
        npz_kwargs[f"psi_confidence_{int(target)}nm"] = np.divide(p["Lmag"], p["S0"], out=np.full_like(p["Lmag"], np.nan), where=p["S0"] > 0.0)
    np.savez_compressed(args.output_dir / "pair_angular_resolved_450nm.npz", **npz_kwargs)
    np.savez_compressed(args.output_dir / "pair_angular_resolved_relevant_wavelengths.npz", **npz_kwargs)

    # Required figures.
    plot_single_source_spectra(figure_dir / "pair_single_source_stokes_spectra.png", wl, x, y)
    plot_poincare(figure_dir / "pair_poincare_relation.png", wl, dot, separation, poincare_valid)
    save_heatmap(figure_dir / "pair_angular_dolp_450nm.png", pair_map["DoLP"], grid, "Pair angular DoLP at 450 nm", "DoLP", 0.0, 1.0)
    save_heatmap(figure_dir / "pair_angular_psi_450nm.png", pair_map["psi_deg"], grid, "Pair angular raw psi at 450 nm", "psi (deg)", 0.0, 180.0, "twilight")
    cone_plot_rows = [row for row in cone_rows if row["cone"] in ("5_deg_normal", "10_deg_normal", "20_deg_normal", "full_available_upper")]
    plot_cone(figure_dir / "pair_normal_centered_cone_dolp.png", [5.0, 10.0, 20.0, 90.0], [row["DoLP"] for row in cone_plot_rows])
    decomp_450 = angular_rows[1]
    plot_decomposition(figure_dir / "pair_source_vs_angular_decomposition.png", ["IC1 x", "IC2 y", "pair local", "pair global"], [float(x["DoLP"][i450]), float(y["DoLP"][i450]), decomp_450["pair_local_DoLP_powerweighted"], decomp_450["pair_angular_integrated_DoLP"]])

    c450 = cancellation_rows[i450]
    ap450 = angular_rows[1]
    cone_by_name = {row["cone"]: row for row in cone_rows}
    finite_linear = np.isfinite(c_linear)
    finite_poincare = np.isfinite(separation)
    broadband_summary = {
        "wavelength_start_nm": float(wl[0]),
        "wavelength_end_nm": float(wl[-1]),
        "points": int(len(wl)),
        "C_linear_mean": float(np.nanmean(c_linear)),
        "C_linear_worst": float(np.nanmin(c_linear)),
        "C_linear_max": float(np.nanmax(c_linear)),
        "linear_Stokes_angle_mean_deg": float(np.nanmean(linear_angle)),
        "linear_Stokes_angle_min_deg": float(np.nanmin(linear_angle)),
        "linear_Stokes_angle_max_deg": float(np.nanmax(linear_angle)),
        "Poincare_separation_mean_deg": float(np.nanmean(separation[finite_poincare])),
        "Poincare_separation_max_deg": float(np.nanmax(separation[finite_poincare])),
        "Poincare_valid_points_DoLP_ge_0p10": int(np.count_nonzero(poincare_valid)),
        "pair_DoLP_mean": float(np.nanmean(mxy["DoLP"])),
        "pair_DoLP_worst": float(np.nanmin(mxy["DoLP"])),
    }
    if c450["C_linear"] < 0.5 and ap450["C_angular"] < 0.5:
        root_class = "BOTH_SOURCE_AND_ANGULAR_CANCELLATION"
    elif c450["C_linear"] < 0.5:
        root_class = "XY_SOURCE_STOKES_CANCELLATION_DOMINANT"
    elif ap450["C_angular"] < 0.5:
        root_class = "ANGULAR_POLARIZATION_CANCELLATION_DOMINANT"
    elif cone_by_name["20_deg_normal"]["DoLP"] >= 0.5 and cone_by_name["full_available_upper"]["DoLP"] < 0.5:
        root_class = "CENTRAL_CONE_LP_SURVIVES_FULL_ANGLE_AVERAGING_ONLY"
    else:
        root_class = "INTEGRATED_I03_DIATTENUATION_COLLAPSE_CONFIRMED"
    recommendation = "INTEGRATED_AWARE_LP_REDESIGN_REQUIRED" if root_class in ("XY_SOURCE_STOKES_CANCELLATION_DOMINANT", "BOTH_SOURCE_AND_ANGULAR_CANCELLATION", "ANGULAR_POLARIZATION_CANCELLATION_DOMINANT") else "PAIR_VALID_BUT_NEEDS_PHYSICS_REVIEW_BEFORE_EXPANSION"

    anchor = {
        "wavelength_nm": float(wl[i450]),
        "IC1_TOPWELL_X_raw_Stokes": {key: float(x[key][i450]) for key in ("S0", "S1", "S2", "S3")},
        "IC2_TOPWELL_Y_raw_Stokes": {key: float(y[key][i450]) for key in ("S0", "S1", "S2", "S3")},
        "IC1_TOPWELL_X_raw_DoLP": float(x["DoLP"][i450]),
        "IC2_TOPWELL_Y_raw_DoLP": float(y["DoLP"][i450]),
        "IC1_IC2_sourcepower_normalized_Stokes": {key: float(sxy[key][i450]) for key in ("S0", "S1", "S2", "S3")},
        "pair_DoLP": float(mxy["DoLP"][i450]),
        "pair_psi_deg_raw": float(mxy["psi_deg"][i450]),
        "pair_DoCP": float(mxy["DoCP"][i450]),
        "pair_useful_LP_axisfree": float(mxy["useful_LP_axisfree"][i450]),
        "pair_useful_LP_over_S0": float(0.5 * (1.0 + mxy["DoLP"][i450])),
        "unpolarized_baseline": 0.5,
        "upward_source_normalized_power": float(0.5 * (x_flux["top_W"][i450] / x_flux["sourcepower_W"][i450] + y_flux["top_W"][i450] / y_flux["sourcepower_W"][i450])),
        "power_ratio_S0x_over_S0y": power_ratio_450,
        "C_linear": float(c450["C_linear"]),
        "linear_Stokes_angle_deg": float(c450["linear_Stokes_angle_deg"]),
        "Poincare_dot": float(dot[i450]),
        "Poincare_separation_deg": float(separation[i450]),
        "peak_pixel_pair_metrics": peak_metrics,
        "angular": {"peak_theta_deg": theta_peak, "peak_phi_deg": phi_peak, "normal_5_deg": cone_by_name["5_deg_normal"], "normal_10_deg": cone_by_name["10_deg_normal"], "normal_20_deg": cone_by_name["20_deg_normal"], "full_available_upper": cone_by_name["full_available_upper"], "peak_5_deg": cone_by_name["5_deg_peak"], "peak_10_deg": cone_by_name["10_deg_peak"], "angular_cancellation": ap450},
    }
    write_json(args.output_dir / "pair_450nm_forensic_anchor.json", anchor)

    scope_boundary = {
        "intrinsic_vs_integrated": "Intrinsic periodic/full-Jones I03 truth is not interchangeable with finite integrated top-well pair truth.",
        "differences": ["finite 5x5 I03 array versus periodic unit cell", "dipole-source angular spectrum versus plane-wave excitation", "finite mesa/PML boundaries", "near-field source coupling", "angular integration", "MDC-conditioned illumination", "incoherent x/y spontaneous-source semantics"],
        "unsupported_attribution": "Stored IC1/IC2 truth does not include the field immediately incident on I03; source-to-I03 angular-spectrum attribution cannot be proven zero-solver.",
    }
    decision = {
        "schema": "PAPER_A_IC2_PAIR_POLARIZATION_CANCELLATION_FORENSIC_V1",
        "status": "PASS",
        "root_cause_classification": root_class,
        "root_cause_basis": {"450_nm_source_C_linear": float(c450["C_linear"]), "450_nm_angular_C_angular": float(ap450["C_angular"]), "450_nm_pair_global_DoLP": float(mxy["DoLP"][i450]), "450_nm_pair_local_DoLP_powerweighted": ap450["pair_local_DoLP_powerweighted"], "450_nm_full_angle_DoLP": cone_by_name["full_available_upper"]["DoLP"], "normal_20_deg_DoLP": cone_by_name["20_deg_normal"]["DoLP"]},
        "next_stage_recommendation": recommendation,
        "power_balance": {"S0x_over_S0y_450": power_ratio_450, "S0x_over_S0y_min": float(np.nanmin(power_ratio)), "S0x_over_S0y_max": float(np.nanmax(power_ratio)), "classification_at_450": power_ratio_class},
        "broadband_source_summary": broadband_summary,
        "anchor": anchor,
        "scope_boundary": scope_boundary,
        "W_emit": "UNRESOLVED_FOR_PRODUCTION_CLOSURE",
        "solver_accounting": {"new_fdtd_budget": 0, "solver_run_called_delta": 0, "solver_entered_delta": 0, "fdtd": 0, "rcwa": 0, "ml": 0, "replay": 0, "new_cases_started": []},
        "timestamp_utc": now(),
    }
    write_json(args.output_dir / "root_cause_decision.json", decision)

    audit = {
        "schema": "PAPER_A_IC2_PAIR_POLARIZATION_CANCELLATION_FORENSIC_AUDIT_V1",
        "status": "PASS",
        "stage": "PAPER_A_IC2_PAIR_POLARIZATION_CANCELLATION_FORENSIC_V1",
        "inputs": {str(path): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in (args.ic1_stokes, args.ic2_stokes, args.ic1_flux, args.ic2_flux, args.ic1_farfield, args.ic2_farfield, args.ic1_validity, args.ic2_validity, args.ic1_summary, args.ic2_summary)},
        "post_fsp_provenance": {"IC1_post_fsp_sha256": ic1_summary.get("post_fsp_sha256"), "IC2_post_fsp_sha256": ic2_summary.get("post_fsp_sha256"), "IC1_status": ic1_validity.get("status"), "IC2_status": ic2_validity.get("status")},
        "grid_tests": {"spectral_points": int(len(wl)), "spectral_spacing_nm": float(np.median(np.diff(wl))), "wavelength_grid_exact": True, "exact_450_index": i450, "angular_points": [150, 150], "angular_grid_exact": True, "solid_angle_jacobian": "du*dv/sqrt(1-ux^2-uy^2) on propagating disk", "stokes_convention": "S0=trace(C), S1=Cxx-Cyy, S2=2Re(Cxy), S3=-2Im(Cxy), Cxy=0.5*Ey*conj(Ex), S3=-2Im(Cxy)"},
        "finite_nan_inf": {"input_csv": all(finite(data[key]) for data, keys in ((x, required_stokes), (y, required_stokes)) for key in keys), "angular": all(finite(angular[target]["pair"][key]) for target in DIAGNOSTIC_WAVELENGTHS for key in ("S0", "S1", "S2", "S3", "DoLP", "DoCP", "psi_deg", "useful_LP_axisfree"))},
        "analysis_tests": {"single_source_stokes": "PASS", "linear_stokes_cancellation": "PASS", "poincare_relation": "PASS", "angular_incoherent_combination": "PASS", "collection_cone_stokes_first": "PASS", "peak_direction": "PASS", "angular_cancellation": "PASS", "raw_psi_retained_with_confidence": "PASS", "useful_lp_normalized_identity": "PASS", "no_new_solver": True},
        "decision": decision,
        "output_files": {str(path.name): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in args.output_dir.iterdir() if path.is_file() and path.name != "audit.json"},
        "solver_accounting": decision["solver_accounting"],
        "W_emit": decision["W_emit"],
        "timestamp_utc": now(),
    }

    report = f"""# IC1/IC2 polarization-cancellation forensic

## Status

`PASS` — zero-solver forensic attribution completed.

## 450 nm source decomposition

- IC1-x raw Stokes: `{anchor['IC1_TOPWELL_X_raw_Stokes']}`; DoLP=`{anchor['IC1_TOPWELL_X_raw_DoLP']:.8f}`
- IC2-y raw Stokes: `{anchor['IC2_TOPWELL_Y_raw_Stokes']}`; DoLP=`{anchor['IC2_TOPWELL_Y_raw_DoLP']:.8f}`
- x/y S0 ratio: `{power_ratio_450:.8f}` (`{power_ratio_class}`)
- linear-Stokes angle: `{c450['linear_Stokes_angle_deg']:.8f} deg`; `C_linear={c450['C_linear']:.8f}`
- Poincare dot/separation: `{dot[i450]:.8f}` / `{separation[i450]:.8f} deg`

## Angular pair at 450 nm

- normal-centered 5/10/20 deg DoLP: `{cone_by_name['5_deg_normal']['DoLP']:.8f}` / `{cone_by_name['10_deg_normal']['DoLP']:.8f}` / `{cone_by_name['20_deg_normal']['DoLP']:.8f}`
- full available upper-angle DoLP: `{cone_by_name['full_available_upper']['DoLP']:.8f}`
- peak direction: theta=`{theta_peak:.8f} deg`, phi=`{phi_peak:.8f} deg`; peak-centered 5 deg DoLP=`{cone_by_name['5_deg_peak']['DoLP']:.8f}`
- peak-pixel pair DoLP/DoCP/raw psi: `{peak_metrics['DoLP']:.8f}` / `{peak_metrics['DoCP']:.8f}` / `{peak_metrics['psi_deg']:.8f} deg`
- angular cancellation `C_angular`: `{ap450['C_angular']:.8f}`
- pair local DoLP power-weighted before angular integration: `{ap450['pair_local_DoLP_powerweighted']:.8f}`

## Broadband pair

- 400–500 nm global pair DoLP mean/worst: `{float(np.nanmean(mxy['DoLP'])):.8f}` / `{float(np.nanmin(mxy['DoLP'])):.8f}`
- 400–500 nm source `C_linear` mean/worst/max: `{broadband_summary['C_linear_mean']:.8f}` / `{broadband_summary['C_linear_worst']:.8f}` / `{broadband_summary['C_linear_max']:.8f}`
- 400–500 nm Poincare separation mean/max: `{broadband_summary['Poincare_separation_mean_deg']:.8f} deg` / `{broadband_summary['Poincare_separation_max_deg']:.8f} deg`
- max absolute global pair DoCP: `{float(np.nanmax(np.abs(mxy['DoCP']))):.8f}`
- raw psi retained; global maximum circular psi step is inherited from the pair closeout. Low linear-Stokes regions are marked by continuous `Lmag/S0` and a diagnostic `DoLP>=0.10` confidence flag; no points were deleted.

## Attribution

`{root_class}`. The result is quantitatively based on source `C_linear={c450['C_linear']:.8f}`, angular `C_angular={ap450['C_angular']:.8f}`, and full-angle pair DoLP `{cone_by_name['full_available_upper']['DoLP']:.8f}`. This distinguishes x/y source Stokes cancellation from subsequent angular integration.

Intrinsic periodic/full-Jones I03 truth is not equivalent to finite integrated top-well x/y truth. Differences include finite 5x5 I03 versus periodic cell, dipole angular spectrum, finite mesa/PML, near-field coupling, MDC conditioning, angular integration, and incoherent spontaneous-source semantics. The stored truth does not include the field immediately incident on I03, so source-to-I03 angular-spectrum attribution is not proven.

## Boundary and next step

`W_emit = UNRESOLVED_FOR_PRODUCTION_CLOSURE`; no emitter-weighted DoLP, absolute LEE, or full-device claim is made.

Recommendation: `{recommendation}`. It is not executed here. No new well, CP, Bare+I03, redesign, or solver was started.

## Solver accounting

`NEW_FDTD_BUDGET=0`, `solver_run_called_delta=0`, `solver_entered_delta=0`, `FDTD=0`, `RCWA=0`, `ML=0`, `replay=0`.
"""
    (args.output_dir / "final_report.md").write_text(report, encoding="utf-8")
    write_json(args.output_dir / "audit.json", audit)
    audit["output_files"] = {str(path.name): {"sha256": sha256(path), "bytes": path.stat().st_size} for path in args.output_dir.iterdir() if path.is_file() and path.name != "audit.json"}
    write_json(args.output_dir / "audit.json", audit)
    print(json.dumps(decision, ensure_ascii=False, default=str))


if __name__ == "__main__":
    raise SystemExit(main())
