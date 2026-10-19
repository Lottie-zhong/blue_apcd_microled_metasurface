"""Frozen V3A A+ projection and deterministic wideband labels."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

ETA0 = 376.730313668
LAMBDA_X_NM = 1740.0
WAVELENGTHS_NM = np.arange(440.0, 461.0, 1.0)
FIELD_KEYS = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")


def trapz(value: np.ndarray, axis: np.ndarray) -> float:
    return float(np.trapezoid(value, axis) if hasattr(np, "trapezoid") else np.trapz(value, axis))


def line(raw: dict[str, Any], name: str) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    coord_key = str(np.asarray(raw[f"{name}_coord_axis"]).reshape(-1)[0])
    x = np.asarray(raw[f"{name}_{coord_key}"]).squeeze().reshape(-1).astype(float)
    nf = len(np.asarray(raw["wavelength_nm"]).reshape(-1))
    fields = {}
    for key in FIELD_KEYS:
        value = np.asarray(raw.get(f"{name}_{key}", np.array([])))
        fields[key] = value.reshape((x.size, nf), order="C").astype(complex) if value.size else np.zeros((x.size, nf), complex)
    return x, fields


def poynting_y(fields: dict[str, np.ndarray]) -> np.ndarray:
    # Preserve the project's established 2D line-flux convention.
    return 0.5 * np.real(fields["Ey"] * np.conj(fields["Hx"]) - fields["Ex"] * np.conj(fields["Hz"]))


def integrate_line(raw: dict[str, Any], name: str, outward: float = 1.0) -> np.ndarray:
    coord, fields = line(raw, name)
    return np.asarray([trapz(outward * poynting_y(fields)[:, i], coord) for i in range(fields["Ex"].shape[1])])


def fourier_x(x: np.ndarray, values: np.ndarray, kx: np.ndarray) -> np.ndarray:
    order = np.argsort(x)
    x = x[order]
    values = values[order]
    if x.size < 2 or np.any(np.diff(x) <= 0):
        raise ValueError("upward monitor x grid must be strictly increasing")
    # Lumerical's mesh-refined monitor is nonuniform.  Use trapezoidal
    # quadrature directly; the exponent is the frozen negative-sign Fourier
    # convention and x0 is the frozen coordinate origin.
    weights = np.empty(x.size, dtype=float)
    weights[0] = 0.5 * (x[1] - x[0])
    weights[-1] = 0.5 * (x[-1] - x[-2])
    weights[1:-1] = 0.5 * (x[2:] - x[:-2])
    phase = np.exp(-1j * np.asarray(kx, dtype=float)[:, None] * (x - 0.0)[None, :])
    return phase @ (values * weights[:, None])


def metric_from_profile(u: np.ndarray, profile: np.ndarray, wavelengths: np.ndarray) -> dict[str, np.ndarray]:
    order = np.argsort(u)
    u = u[order]
    profile = profile[order]
    theta = np.degrees(np.arcsin(np.clip(u, -1.0, 1.0)))
    out = {"F_seed_2": [], "F_seed_5": [], "F_seed_10": [], "asymmetry": [], "centroid_deg": [], "positive_fraction": [], "negative_fraction": [], "over60_fraction": []}
    for i, wavelength in enumerate(wavelengths):
        p = np.maximum(profile[:, i], 0.0)
        total = max(trapz(p, u), 1e-300)
        seed = np.degrees(np.arcsin(float(wavelength) / LAMBDA_X_NM))
        for window in (2, 5, 10):
            mask = np.abs(theta - seed) <= window
            out[f"F_seed_{window}"].append(trapz(p[mask], u[mask]) / total if mask.sum() > 1 else 0.0)
        pos = u >= 0
        neg = u < 0
        pp = trapz(p[pos], u[pos]) if pos.sum() > 1 else 0.0
        pn = trapz(p[neg], u[neg]) if neg.sum() > 1 else 0.0
        out["positive_fraction"].append(pp / total)
        out["negative_fraction"].append(pn / total)
        out["asymmetry"].append((pp - pn) / max(pp + pn, 1e-300))
        poynting = p * np.sqrt(np.maximum(0.0, 1.0 - u * u))
        out["centroid_deg"].append(trapz(theta * poynting, u) / max(trapz(poynting, u), 1e-300))
        out["over60_fraction"].append(trapz(p[np.abs(theta) > 60], u[np.abs(theta) > 60]) / total)
    return {key: np.asarray(value, dtype=float) for key, value in out.items()}


def native_profile(raw: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    theta = np.asarray(raw["farfield_theta_deg"], dtype=float)
    intensity = np.maximum(np.asarray(raw["farfield_e2"], dtype=float), 0.0)
    nf = intensity.shape[1]
    u = np.sin(np.radians(theta))
    result_u, result_p = [], []
    for i in range(nf):
        order = np.argsort(u[:, i])
        ui, pi = u[order, i], intensity[order, i]
        norm = max(trapz(pi, ui), 1e-300)
        result_u.append(ui)
        result_p.append(pi / norm)
    return np.column_stack(result_u), np.column_stack(result_p)


def compare_native(u: np.ndarray, profile: np.ndarray, raw: dict[str, Any], wavelengths: np.ndarray) -> dict[str, Any]:
    nu, np_=native_profile(raw)
    native_metrics = {key: [] for key in ("F_seed_2", "F_seed_5", "F_seed_10", "asymmetry", "centroid_deg", "positive_fraction", "negative_fraction", "over60_fraction")}
    for i, wavelength in enumerate(wavelengths):
        one = metric_from_profile(nu[:, i], np_[:, i:i + 1], np.asarray([wavelength]))
        for key, value in one.items():
            native_metrics[key].append(float(value[0]))
    native_metrics = {key: np.asarray(value) for key, value in native_metrics.items()}
    l1, corr = [], []
    for i in range(profile.shape[1]):
        ui = nu[:, i]
        pa = np.interp(ui, u, profile[:, i])
        pn = np_[..., i]
        l1.append(trapz(np.abs(pa - pn), ui))
        corr.append(float(np.corrcoef(pa, pn)[0, 1]) if np.std(pa) and np.std(pn) else 0.0)
    return {"profile_weighted_l1": np.asarray(l1), "profile_correlation": np.asarray(corr), "native_metrics": native_metrics}


def extract_labels(raw: dict[str, Any]) -> dict[str, Any]:
    wavelengths = np.asarray(raw["wavelength_nm"], dtype=float).reshape(-1)
    if wavelengths.size != 21 or not np.allclose(wavelengths, WAVELENGTHS_NM, atol=1e-5):
        raise ValueError("exact 440-460 nm / 21-point grid required")
    x, fields = line(raw, "upward_monitor")
    # Evaluate the frozen transform on a deterministic dense propagating grid;
    # this avoids making F_seed windows depend on the coarse FFT-node spacing.
    u_axis = np.linspace(-1.0, 1.0, 721)
    k0 = 2 * np.pi / (wavelengths * 1e-9)
    a_columns = []
    for i, k0_i in enumerate(k0):
        kx_i = u_axis * k0_i
        fx_ex = fourier_x(x, fields["Ex"][:, i:i + 1], kx_i)[:, 0]
        fx_hz = fourier_x(x, fields["Hz"][:, i:i + 1], kx_i)[:, 0]
        a_columns.append(fx_ex - ETA0 * np.sqrt(np.maximum(0.0, 1.0 - u_axis * u_axis)) * fx_hz)
    u = np.repeat(u_axis[:, None], wavelengths.size, axis=1)
    a_plus = np.column_stack(a_columns)
    zero_index = int(np.argmin(np.abs(u_axis)))
    gauges = np.angle(a_plus[zero_index, :])
    a_plus = a_plus * np.exp(-1j * gauges)[None, :]
    norms = np.asarray([max(trapz(np.abs(a_plus[:, i]) ** 2, u[:, i]), 1e-300) for i in range(wavelengths.size)])
    c_route = a_plus / np.sqrt(norms)[None, :]
    profile = np.abs(c_route) ** 2
    metrics = metric_from_profile(u_axis, profile, wavelengths)
    p_up_direct = integrate_line(raw, "upward_monitor", 1.0)
    source = sum(integrate_line(raw, name, sign) for name, sign in (("source_box_top", 1.0), ("source_box_bottom", -1.0), ("source_box_left", -1.0), ("source_box_right", 1.0)))
    compare = compare_native(u[:, 0], profile, raw, wavelengths)
    return {"wavelengths_nm": wavelengths, "u_x": u_axis, "u_x_by_wavelength": u, "theta_deg": np.degrees(np.arcsin(np.clip(u, -1, 1))), "A_plus": a_plus, "C_route": c_route, "profile": profile, "P_up": p_up_direct, "P_up_state": norms, "P_up_direct": p_up_direct, "source_box_power": source, "eta_up": p_up_direct / np.maximum(source, 1e-300), "metrics": metrics, "native_comparison": compare, "gauge_phase_rad": gauges, "finite": bool(all(np.isfinite(np.real(v)).all() and np.isfinite(np.imag(v)).all() for v in (a_plus, c_route)))}


def jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {key: jsonable(child) for key, child in value.items()}
    return value


def write_result(result: dict[str, Any], output_dir: Path, geometry_id: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_dir / "WIDEBAND_A_PLUS_LABELS.npz", **{key: value for key, value in result.items() if isinstance(value, np.ndarray)})
    rows = []
    for i, wavelength in enumerate(result["wavelengths_nm"]):
        rows.append({"geometry_id": geometry_id, "wavelength_nm": float(wavelength), "P_up": float(result["P_up"][i]), "eta_up": float(result["eta_up"][i]), "F_seed_2": float(result["metrics"]["F_seed_2"][i]), "F_seed_5": float(result["metrics"]["F_seed_5"][i]), "F_seed_10": float(result["metrics"]["F_seed_10"][i]), "asymmetry": float(result["metrics"]["asymmetry"][i]), "centroid_deg": float(result["metrics"]["centroid_deg"][i]), "positive_fraction": float(result["metrics"]["positive_fraction"][i]), "negative_fraction": float(result["metrics"]["negative_fraction"][i]), "over60_fraction": float(result["metrics"]["over60_fraction"][i]), "native_profile_weighted_l1": float(result["native_comparison"]["profile_weighted_l1"][i]), "native_profile_correlation": float(result["native_comparison"]["profile_correlation"][i])})
    with (output_dir / "WIDEBAND_LABELS.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary = {"geometry_id": geometry_id, "wavelength_count": 21, "u_count": int(result["u_x"].size), "finite": result["finite"], "profile_weighted_l1_median": float(np.median(result["native_comparison"]["profile_weighted_l1"])), "profile_weighted_l1_p95": float(np.quantile(result["native_comparison"]["profile_weighted_l1"], .95)), "P_up": {"median": float(np.median(result["P_up"])), "finite": bool(np.isfinite(result["P_up"]).all())}, "metrics": {key: {"median": float(np.median(value)), "p95": float(np.quantile(value, .95))} for key, value in result["metrics"].items()}, "P_down_status": "RAW_ONLY_NOT_ACTIVE_LABEL"}
    (output_dir / "WIDEBAND_LABEL_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
