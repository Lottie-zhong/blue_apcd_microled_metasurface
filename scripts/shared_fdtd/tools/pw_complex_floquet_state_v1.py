"""Canonical PW complex Floquet state projection and comparison.

This module is solver-independent. It consumes saved complex monitor fields or
an FDTD load-only adapter and maps every plane to one deterministic modal
coordinate system.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

C0 = 299792458.0
ETA0 = 376.730313668
PERIOD_X_M = 1740e-9
PERIOD_Y_M = 290e-9
WAVELENGTHS_NM = np.arange(440.0, 461.0, 1.0)
FIELD_NAMES = ("Ex", "Ey", "Ez", "Hx", "Hy", "Hz")
PLANES = ("IN", "PRENP", "POSTNP")
DIRECTIONS = ("+z", "-z")
POLARIZATIONS = ("TE", "TM")
DEFAULT_ORDERS = tuple((m, n) for m in range(-4, 5) for n in range(-4, 5))
_REFERENCE_NM = {"IN": -50.0, "PRENP": 1202.0, "POSTNP": 1722.0}


def _finite_complex(value: np.ndarray) -> bool:
    return bool(np.all(np.isfinite(value.real)) and np.all(np.isfinite(value.imag)))


def _trap_weights(coordinate: np.ndarray) -> np.ndarray:
    coordinate = np.asarray(coordinate, dtype=float).reshape(-1)
    if coordinate.size < 2 or not np.all(np.isfinite(coordinate)):
        raise ValueError("coordinate_grid_invalid")
    delta = np.diff(coordinate)
    if np.any(delta <= 0.0):
        raise ValueError("coordinate_grid_must_be_strictly_increasing")
    weights = np.empty_like(coordinate)
    weights[0] = delta[0] / 2.0
    weights[-1] = delta[-1] / 2.0
    if coordinate.size > 2:
        weights[1:-1] = (delta[:-1] + delta[1:]) / 2.0
    return weights


def _passive_sqrt(value: complex) -> complex:
    result = complex(np.sqrt(complex(value)))
    tolerance = 1e-14 * max(1.0, abs(result))
    if result.real < -tolerance or (abs(result.real) <= tolerance and result.imag < 0.0):
        result = -result
    return result


def _mode(
    m: int,
    n: int,
    wavelength_nm: float,
    refractive_index: complex,
    direction: int,
    polarization: str,
    period_x_m: float = PERIOD_X_M,
    period_y_m: float = PERIOD_Y_M,
) -> dict[str, Any]:
    if direction not in (-1, 1):
        raise ValueError("direction")
    if polarization not in POLARIZATIONS:
        raise ValueError("polarization")
    n_medium = complex(refractive_index)
    if abs(n_medium) <= 1e-30:
        raise ValueError("local_medium_index_zero")
    k0 = 2.0 * math.pi / (float(wavelength_nm) * 1e-9)
    kx = 2.0 * math.pi * int(m) / float(period_x_m)
    ky = 2.0 * math.pi * int(n) / float(period_y_m)
    kz = _passive_sqrt((n_medium * k0) ** 2 - kx**2 - ky**2)
    kt = math.hypot(kx, ky)
    if kt <= 1e-30:
        s_hat = np.array([0.0, 1.0, 0.0], dtype=complex)
    else:
        s_hat = np.array([-ky / kt, kx / kt, 0.0], dtype=complex)
    k_hat = np.array([kx, ky, direction * kz], dtype=complex) / (n_medium * k0)
    p_hat = np.cross(s_hat, k_hat)
    bilinear_norm = np.dot(p_hat, p_hat)
    if abs(bilinear_norm) > 1e-24 and abs(bilinear_norm - 1.0) > 1e-10:
        p_hat = p_hat / np.sqrt(bilinear_norm)
    e_hat = s_hat if polarization == "TE" else p_hat
    h_hat = (n_medium / ETA0) * np.cross(k_hat, e_hat)
    power_z = 0.5 * float(np.real(np.cross(e_hat, np.conj(h_hat))[2]))
    propagating = bool(abs(kz.real) > 1e-12 * max(1.0, abs(kz)))
    return {
        "m": int(m),
        "n": int(n),
        "direction": int(direction),
        "polarization": polarization,
        "kx_rad_m": float(kx),
        "ky_rad_m": float(ky),
        "kz_rad_m": complex(kz),
        "k_hat": k_hat,
        "e_hat": e_hat,
        "h_hat": h_hat,
        "power_z_per_abs_e2": power_z,
        "propagating": propagating,
    }


def canonicalize_plane_raw(raw: Mapping[str, Any]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    x = np.asarray(raw["x"], dtype=float).reshape(-1)
    y = np.asarray(raw["y"], dtype=float).reshape(-1)
    frequency = np.asarray(raw["f"], dtype=float).reshape(-1)
    if x.size < 2 or y.size < 2 or frequency.size < 1:
        raise ValueError("plane_coordinates_or_frequency_invalid")
    fields: dict[str, np.ndarray] = {}
    expected = (x.size, y.size, frequency.size)
    for name in FIELD_NAMES:
        value = np.asarray(raw[name])
        if value.shape == (x.size, y.size, 1, frequency.size):
            value = value[:, :, 0, :]
        elif value.shape != expected:
            raise ValueError(f"{name}_shape_invalid:{value.shape}:expected={expected}")
        value = np.asarray(value, dtype=complex)
        if not np.iscomplexobj(value) or not _finite_complex(value):
            raise ValueError(f"{name}_must_be_finite_complex")
        fields[name] = value
    z_value = np.asarray(raw.get("z", 0.0), dtype=float).reshape(-1)
    if z_value.size != 1 or not np.isfinite(z_value[0]):
        raise ValueError("plane_z_invalid")
    if not np.all(np.isfinite(frequency)) or np.any(frequency <= 0.0):
        raise ValueError("frequency_invalid")
    return fields, {
        "x_m": x,
        "y_m": y,
        "frequency_hz": frequency,
        "z_sample_m": float(z_value[0]),
        "field_shape": list(expected),
    }


def read_fdtd_plane(fd: Any, monitor: str) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "x": np.asarray(fd.getdata(monitor, "x")),
        "y": np.asarray(fd.getdata(monitor, "y")),
        "z": np.asarray(fd.getdata(monitor, "z")),
        "f": np.asarray(fd.getdata(monitor, "f")),
    }
    for name in FIELD_NAMES:
        raw[name] = np.asarray(fd.getdata(monitor, name))
    return raw


def read_fdtd_index(fd: Any, material: str, frequency_hz: Sequence[float]) -> np.ndarray:
    frequency = np.asarray(frequency_hz, dtype=float).reshape(-1)
    fmin, fmax = float(np.min(frequency)), float(np.max(frequency))
    return np.asarray(
        [complex(fd.getfdtdindex(material, float(value), fmin, fmax)) for value in frequency],
        dtype=complex,
    )


def canonical_state_from_fdtd(
    fd: Any,
    pw_contract: Mapping[str, Any],
    z_references_nm: Mapping[str, float] | None = None,
    orders: Sequence[tuple[int, int]] = DEFAULT_ORDERS,
) -> dict[str, Any]:
    """Read six-component fields/indexes from an already loaded FDTD object."""
    monitors = pw_contract["monitors"]
    materials = pw_contract["materials"]
    monitor_by_plane = {"IN": monitors["input"], "PRENP": monitors["pre"], "POSTNP": monitors["output"]}
    material_by_plane = {
        "IN": materials["substrate"],
        "PRENP": materials.get("mdc_sio2", materials.get("pre_medium", "Air")),
        "POSTNP": materials.get("superstrate", "Air"),
    }
    planes = {plane: read_fdtd_plane(fd, monitor) for plane, monitor in monitor_by_plane.items()}
    local_indices = {}
    for plane, raw in planes.items():
        material = str(material_by_plane[plane])
        frequency = np.asarray(raw["f"], dtype=float).reshape(-1)
        local_indices[plane] = np.ones(frequency.size, dtype=complex) if material.lower() == "air" else read_fdtd_index(fd, material, frequency)
    return canonical_state_from_raw(planes, local_indices, z_references_nm=z_references_nm, orders=orders)

def _plane_projection(
    raw: Mapping[str, Any],
    refractive_index: Sequence[complex],
    orders: Sequence[tuple[int, int]] = DEFAULT_ORDERS,
    z_reference_nm: float | None = None,
    period_x_m: float = PERIOD_X_M,
    period_y_m: float = PERIOD_Y_M,
) -> dict[str, Any]:
    fields, axes = canonicalize_plane_raw(raw)
    frequency = axes["frequency_hz"]
    nf = frequency.size
    n_values = np.asarray(refractive_index, dtype=complex).reshape(-1)
    if n_values.size != nf:
        raise ValueError("local_index_frequency_length_mismatch")
    wavelengths = C0 / frequency * 1e9
    wavelength_order = np.argsort(wavelengths)
    fields = {name: value[:, :, wavelength_order] for name, value in fields.items()}
    frequency = frequency[wavelength_order]
    n_values = n_values[wavelength_order]
    wavelengths = wavelengths[wavelength_order]
    x, y = axes["x_m"], axes["y_m"]
    wx, wy = _trap_weights(x), _trap_weights(y)
    x_grid, y_grid = np.meshgrid(x, y, indexing="ij")
    orders = tuple((int(m), int(n)) for m, n in orders)
    coefficients = np.zeros((nf, len(orders), 2, 2), dtype=complex)
    mode_kz = np.zeros((nf, len(orders)), dtype=complex)
    mode_power = np.zeros((nf, len(orders), 2, 2), dtype=float)
    propagating = np.zeros((nf, len(orders)), dtype=bool)
    condition = np.zeros((nf, len(orders)), dtype=float)
    z_reference = float(axes["z_sample_m"] if z_reference_nm is None else z_reference_nm * 1e-9)
    for fi, wavelength in enumerate(wavelengths):
        for oi, (m, n) in enumerate(orders):
            basis_modes = [
                _mode(m, n, float(wavelength), n_values[fi], direction, polarization)
                for direction in (1, -1)
                for polarization in POLARIZATIONS
            ]
            matrix = np.stack(
                [np.concatenate([mode["e_hat"], mode["h_hat"]]) for mode in basis_modes],
                axis=1,
            )
            condition[fi, oi] = float(np.linalg.cond(matrix))
            mode_kz[fi, oi] = basis_modes[0]["kz_rad_m"]
            propagating[fi, oi] = all(mode["propagating"] for mode in basis_modes)
            for ci, mode in enumerate(basis_modes):
                mode_power[fi, oi, ci // 2, ci % 2] = mode["power_z_per_abs_e2"]
            phase = np.exp(-1j * (2.0 * math.pi * m * x_grid / period_x_m + 2.0 * math.pi * n * y_grid / period_y_m))
            sampled = np.empty(6, dtype=complex)
            for component_index, name in enumerate(FIELD_NAMES):
                sampled[component_index] = np.sum(wx[:, None] * wy[None, :] * fields[name][:, :, fi] * phase) / (period_x_m * period_y_m)
            modal, _, rank, _ = np.linalg.lstsq(matrix, sampled, rcond=None)
            if rank < 4:
                raise ValueError(f"modal_basis_rank_deficient:{m},{n}:{rank}")
            dz = z_reference - float(axes["z_sample_m"])
            for ci, mode in enumerate(basis_modes):
                direction = mode["direction"]
                factor = np.exp((1j if direction == 1 else -1j) * mode["kz_rad_m"] * dz)
                coefficients[fi, oi, ci // 2, ci % 2] = modal[ci] * factor
    return {
        "coefficients": coefficients,
        "wavelengths_nm": wavelengths,
        "orders": np.asarray(orders, dtype=int),
        "mode_kz_rad_m": mode_kz,
        "mode_power_z_per_abs_e2": mode_power,
        "propagating_mask": propagating,
        "basis_condition": condition,
        "z_sample_m": float(axes["z_sample_m"]),
        "z_reference_m": z_reference,
        "frequency_order": wavelength_order,
        "axis_contract": {
            "raw": ["x", "y", "z", "f"],
            "canonical_fields": ["x", "y", "f"],
            "projection": "actual_coordinate_trapezoidal_NUDFT",
            "endpoint_rule": "trapezoidal_weights_on_inclusive_monitor_coordinates",
        },
    }


def _normalize_plane_coefficients(
    projections: Mapping[str, Mapping[str, Any]],
    plane_order: Sequence[str],
) -> tuple[np.ndarray, dict[str, Any]]:
    reference = projections["IN"]
    orders = [tuple(row) for row in np.asarray(reference["orders"], dtype=int)]
    try:
        incident_order = orders.index((0, 0))
    except ValueError as exc:
        raise ValueError("incident_order_missing") from exc
    incident = np.asarray(reference["coefficients"])[:, incident_order, 0, 1]
    power_per_amplitude = np.asarray(reference["mode_power_z_per_abs_e2"])[:, incident_order, 0, 1]
    total_power = power_per_amplitude * np.abs(incident) ** 2
    if np.any(~np.isfinite(total_power)) or np.any(total_power <= 1e-30):
        raise ValueError("incident_power_nonpositive")
    scale = 1.0 / np.sqrt(total_power)
    gauge = np.conj(incident) / np.maximum(np.abs(incident), 1e-300)
    coefficients = np.stack(
        [np.asarray(projections[plane]["coefficients"]) * (scale * gauge)[:, None, None, None] for plane in plane_order],
        axis=0,
    )
    return coefficients, {
        "normalization": "incident_+z_(0,0)_TM_power_at_IN_REF",
        "incident_power_per_area": total_power.tolist(),
        "incident_power_per_abs_e2": power_per_amplitude.tolist(),
        "gauge": "single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM; reused at all planes/channels",
        "gauge_phase_rad": np.angle(gauge).tolist(),
        "relative_phase_preserved": True,
        "zero_denominator_count": 0,
    }


def canonical_state_from_raw(
    planes: Mapping[str, Mapping[str, Any]],
    local_indices: Mapping[str, Sequence[complex]],
    z_references_nm: Mapping[str, float] | None = None,
    orders: Sequence[tuple[int, int]] = DEFAULT_ORDERS,
) -> dict[str, Any]:
    plane_order = tuple(planes)
    if plane_order != PLANES:
        raise ValueError(f"plane_order_must_be_{PLANES}")
    z_references_nm = dict(z_references_nm or _REFERENCE_NM)
    projections: dict[str, dict[str, Any]] = {}
    for plane in plane_order:
        raw = planes[plane]
        fields, axes = canonicalize_plane_raw(raw)
        projections[plane] = _plane_projection(
            raw,
            local_indices[plane],
            orders=orders,
            z_reference_nm=float(z_references_nm[plane]),
        )
    wavelengths = np.asarray(projections["IN"]["wavelengths_nm"], dtype=float)
    for plane in plane_order[1:]:
        if not np.allclose(wavelengths, projections[plane]["wavelengths_nm"], rtol=0.0, atol=1e-9):
            raise ValueError("plane_wavelength_grid_mismatch")
    coefficients, normalization = _normalize_plane_coefficients(projections, plane_order)
    state = {
        "schema_version": "PW_COMPLEX_FLOQUET_STATE_V1",
        "coefficients": coefficients,
        "wavelengths_nm": wavelengths,
        "orders": np.asarray(orders, dtype=int),
        "planes": list(plane_order),
        "directions": list(DIRECTIONS),
        "polarizations": list(POLARIZATIONS),
        "propagating_mask": np.stack([projections[plane]["propagating_mask"] for plane in plane_order], axis=0),
        "mode_kz_rad_m": np.stack([projections[plane]["mode_kz_rad_m"] for plane in plane_order], axis=0),
        "basis_condition": np.stack([projections[plane]["basis_condition"] for plane in plane_order], axis=0),
        "normalization": normalization,
        "plane_metadata": {
            plane: {
                "z_sample_m": projections[plane]["z_sample_m"],
                "z_reference_m": projections[plane]["z_reference_m"],
                "projection": projections[plane]["axis_contract"],
                "local_index": [complex(value) for value in np.asarray(local_indices[plane]).reshape(-1)],
            }
            for plane in plane_order
        },
    }
    return state


def state_metadata(state: Mapping[str, Any], npz_path: str | None = None) -> dict[str, Any]:
    coefficients = np.asarray(state["coefficients"])
    metadata = {
        "schema_version": state["schema_version"],
        "state_role": "ML_LABEL_AND_FIDELITY_COMPARATOR_PRIMARY",
        "planes": list(state["planes"]),
        "plane_identifiers": list(state["planes"]),
        "wavelengths_nm": np.asarray(state["wavelengths_nm"], dtype=float).tolist(),
        "orders_mn": np.asarray(state["orders"], dtype=int).tolist(),
        "directions": list(state["directions"]),
        "polarizations": list(state["polarizations"]),
        "complex_encoding": "paired_float64_arrays_coefficients_real_coefficients_imag",
        "coefficients_shape": list(coefficients.shape),
        "axis_order": ["plane", "wavelength", "order", "direction", "polarization"],
        "normalization": state["normalization"],
        "relative_phase_preserved": True,
        "mode_basis": "local_medium_periodic_Floquet_TE_TM_with_passive_kz_branch",
        "evanescent_policy": "retain_complex_coefficients_and_metadata; no_propagating_power_assignment",
        "order_envelope": "m,n=-4..+4; propagating_mask_is_local_medium_and_wavelength_specific",
        "npz_path": npz_path,
    }
    return metadata


def save_state_npz(path: str | Path, state: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        coefficients_real=np.asarray(state["coefficients"]).real,
        coefficients_imag=np.asarray(state["coefficients"]).imag,
        wavelengths_nm=np.asarray(state["wavelengths_nm"], dtype=float),
        orders=np.asarray(state["orders"], dtype=int),
        propagating_mask=np.asarray(state["propagating_mask"], dtype=bool),
        mode_kz_real=np.asarray(state["mode_kz_rad_m"]).real,
        mode_kz_imag=np.asarray(state["mode_kz_rad_m"]).imag,
        basis_condition=np.asarray(state["basis_condition"], dtype=float),
    )
    return {"path": str(path), "size_bytes": path.stat().st_size}


def _channel_labels(orders: np.ndarray) -> list[dict[str, Any]]:
    return [
        {"order_m": int(m), "order_n": int(n), "direction": direction, "polarization": polarization}
        for m, n in orders
        for direction in DIRECTIONS
        for polarization in POLARIZATIONS
    ]


def compare_states(reference: Mapping[str, Any], candidate: Mapping[str, Any], planes: Sequence[str] = ("PRENP", "POSTNP")) -> dict[str, Any]:
    ref = np.asarray(reference["coefficients"], dtype=complex)
    got = np.asarray(candidate["coefficients"], dtype=complex)
    if ref.shape != got.shape:
        raise ValueError(f"state_shape_mismatch:{ref.shape}!={got.shape}")
    if list(reference["planes"]) != list(candidate["planes"]):
        raise ValueError("state_plane_order_mismatch")
    if not np.array_equal(np.asarray(reference["orders"]), np.asarray(candidate["orders"])):
        raise ValueError("state_order_mismatch")
    plane_index = {plane: index for index, plane in enumerate(reference["planes"])}
    if not np.allclose(np.asarray(reference["wavelengths_nm"], dtype=float), np.asarray(candidate["wavelengths_nm"], dtype=float), rtol=0.0, atol=1e-9):
        raise ValueError("state_wavelength_grid_mismatch")
    if list(reference["directions"]) != list(candidate["directions"]) or list(reference["polarizations"]) != list(candidate["polarizations"]):
        raise ValueError("state_channel_order_mismatch")
    labels = _channel_labels(np.asarray(reference["orders"]))
    report: dict[str, Any] = {
        "metric": "E_C(lambda,plane)=||C_candidate-C_reference||_2/||C_reference||_2",
        "no_raw_grid_pointwise_comparison": True,
        "phase_alignment": "none_after_input_reference_gauge",
        "planes": {},
        "aggregate": {"max": 0.0, "median": None, "worst": None},
    }
    all_errors: list[tuple[float, str, int, int]] = []
    for plane in planes:
        pi = plane_index[plane]
        rows = []
        for fi, wavelength in enumerate(np.asarray(reference["wavelengths_nm"], dtype=float)):
            r = ref[pi, fi].reshape(-1)
            c = got[pi, fi].reshape(-1)
            difference = c - r
            denominator = float(np.linalg.norm(r))
            numerator = float(np.linalg.norm(difference))
            error = None if denominator <= 1e-30 else numerator / denominator
            ref_abs = np.abs(r)
            channel_error = np.full(r.shape, np.nan, dtype=float)
            valid = ref_abs > 1e-30
            channel_error[valid] = np.abs(difference[valid]) / ref_abs[valid]
            if np.any(valid):
                worst_index = int(np.nanargmax(channel_error))
                worst_channel = {**labels[worst_index], "relative_error": float(channel_error[worst_index])}
            else:
                worst_index, worst_channel = 0, None
            phase_valid = valid & (np.abs(c) > 1e-30)
            phase_delta = np.angle(c[phase_valid] * np.conj(r[phase_valid]))
            phase_weight = ref_abs[phase_valid] ** 2
            phase_rms = None if not np.any(phase_valid) else float(np.sqrt(np.sum(phase_weight * phase_delta**2) / np.sum(phase_weight)))
            amplitude_rms = float(np.linalg.norm(np.abs(c) - ref_abs) / max(np.linalg.norm(ref_abs), 1e-30))
            row = {
                "wavelength_nm": float(wavelength),
                "E_C": None if error is None else float(error),
                "reference_norm": denominator,
                "absolute_norm": numerator,
                "zero_denominator": bool(denominator <= 1e-30),
                "zero_channel_denominator_count": int(np.count_nonzero(~valid)),
                "amplitude_rms_relative": amplitude_rms,
                "phase_rms_rad_weighted": phase_rms,
                "worst_channel": worst_channel,
            }
            rows.append(row)
            if error is not None:
                all_errors.append((float(error), plane, fi, worst_index))
        finite = [row["E_C"] for row in rows if row["E_C"] is not None]
        worst = max((row for row in rows if row["E_C"] is not None), key=lambda row: row["E_C"], default=None)
        report["planes"][plane] = {
            "per_wavelength": rows,
            "max": None if not finite else float(max(finite)),
            "median": None if not finite else float(np.median(finite)),
            "worst_wavelength_nm": None if worst is None else worst["wavelength_nm"],
        }
    if all_errors:
        value, plane, fi, ci = max(all_errors, key=lambda row: row[0])
        report["aggregate"] = {
            "max": float(value),
            "median": float(np.median([row[0] for row in all_errors])),
            "worst": {"plane": plane, "wavelength_nm": float(reference["wavelengths_nm"][fi]), "channel": labels[ci]},
        }
    return report


def _synthetic_raw(
    nx: int,
    ny: int,
    z_m: float,
    refractive_index: complex,
    amplitudes: Mapping[tuple[int, int, int, str], complex],
    wavelengths_nm: Sequence[float] = (450.0,),
) -> dict[str, Any]:
    x = np.linspace(-PERIOD_X_M / 2.0, PERIOD_X_M / 2.0, nx)
    y = np.linspace(-PERIOD_Y_M / 2.0, PERIOD_Y_M / 2.0, ny)
    wavelengths = np.asarray(wavelengths_nm, dtype=float)
    frequency = C0 / (wavelengths * 1e-9)
    fields = {name: np.zeros((nx, ny, 1, len(wavelengths)), dtype=complex) for name in FIELD_NAMES}
    x_grid, y_grid = np.meshgrid(x, y, indexing="ij")
    for fi, wavelength in enumerate(wavelengths):
        for (m, n, direction, polarization), amplitude in amplitudes.items():
            mode = _mode(m, n, float(wavelength), refractive_index, direction, polarization)
            phase = np.exp(
                1j
                * (
                    mode["kx_rad_m"] * x_grid
                    + mode["ky_rad_m"] * y_grid
                    + direction * mode["kz_rad_m"] * z_m
                )
            )
            for index, name in enumerate(("Ex", "Ey", "Ez")):
                fields[name][:, :, 0, fi] += complex(amplitude) * mode["e_hat"][index] * phase
            for index, name in enumerate(("Hx", "Hy", "Hz")):
                fields[name][:, :, 0, fi] += complex(amplitude) * mode["h_hat"][index] * phase
    return {"x": x[:, None], "y": y[:, None], "z": np.asarray(z_m), "f": frequency[:, None], **fields}


def synthetic_regression_tests() -> dict[str, Any]:
    tests: dict[str, Any] = {}
    n_medium = 1.7 + 0.002j
    amplitudes = {
        (0, 0, 1, "TM"): 1.0 + 0.2j,
        (1, 0, 1, "TE"): -0.2 + 0.4j,
        (-1, 0, -1, "TM"): 0.3 - 0.1j,
    }
    base = _synthetic_raw(129, 33, 0.0, n_medium, amplitudes)
    coarse = {key: value.copy() if isinstance(value, np.ndarray) else value for key, value in base.items()}
    coarse["x"], coarse["y"] = base["x"][::4], base["y"][::2]
    for name in FIELD_NAMES:
        coarse[name] = base[name][::4, ::2, :, :]
    high = _plane_projection(base, [n_medium], z_reference_nm=0.0)
    low = _plane_projection(coarse, [n_medium], z_reference_nm=0.0)
    sampling_error = float(np.max(np.abs(high["coefficients"] - low["coefficients"])))
    tests["same_data_different_spatial_sampling"] = {"pass": sampling_error < 2e-10, "max_abs_error": sampling_error}
    if not tests["same_data_different_spatial_sampling"]["pass"]:
        raise AssertionError("same_data_different_spatial_sampling")

    known = _plane_projection(_synthetic_raw(129, 33, 0.0, n_medium, {(1, 0, 1, "TM"): 0.8 - 0.3j}), [n_medium], z_reference_nm=0.0)
    order_index = list(map(tuple, known["orders"])).index((1, 0))
    known_error = abs(known["coefficients"][0, order_index, 0, 1] - (0.8 - 0.3j))
    tests["known_single_floquet_mode"] = {"pass": bool(known_error < 2e-10), "max_abs_error": float(known_error)}
    if not tests["known_single_floquet_mode"]["pass"]:
        raise AssertionError("known_single_floquet_mode")

    multi = _plane_projection(base, [n_medium], z_reference_nm=0.0)
    multi_errors = []
    for key, amplitude in amplitudes.items():
        oi = list(map(tuple, multi["orders"])).index(key[:2])
        di = 0 if key[2] == 1 else 1
        pi = 0 if key[3] == "TE" else 1
        multi_errors.append(abs(multi["coefficients"][0, oi, di, pi] - amplitude))
    tests["multimode_superposition"] = {"pass": bool(max(multi_errors) < 2e-10), "max_abs_error": float(max(multi_errors))}
    if not tests["multimode_superposition"]["pass"]:
        raise AssertionError("multimode_superposition")

    shifted = _synthetic_raw(129, 33, 37e-9, n_medium, amplitudes)
    shifted_projection = _plane_projection(shifted, [n_medium], z_reference_nm=0.0)
    reference_projection = _plane_projection(base, [n_medium], z_reference_nm=0.0)
    deembed_error = float(np.max(np.abs(shifted_projection["coefficients"] - reference_projection["coefficients"])))
    tests["reference_plane_deembedding"] = {"pass": deembed_error < 2e-10, "max_abs_error": deembed_error}
    if not tests["reference_plane_deembedding"]["pass"]:
        raise AssertionError("reference_plane_deembedding")

    air = _plane_projection(_synthetic_raw(129, 33, 0.0, 1.0 + 0j, {(1, 0, 1, "TE"): 0.7 + 0.1j}), [1.0 + 0j], z_reference_nm=0.0)
    gaN = _plane_projection(_synthetic_raw(129, 33, 0.0, 2.2 + 0.001j, {(0, 1, 1, "TE"): 0.7 + 0.1j}), [2.2 + 0.001j], z_reference_nm=0.0)
    tests["local_medium_basis"] = {"pass": bool(abs(air["coefficients"][0, list(map(tuple, air["orders"])).index((1, 0)), 0, 0] - (0.7 + 0.1j)) < 2e-10 and abs(gaN["coefficients"][0, list(map(tuple, gaN["orders"])).index((0, 1)), 0, 0] - (0.7 + 0.1j)) < 2e-10)}
    if not tests["local_medium_basis"]["pass"]:
        raise AssertionError("local_medium_basis")

    reverse = {key: value[..., ::-1] if key in FIELD_NAMES else value for key, value in base.items()}
    reverse["f"] = base["f"][::-1]
    reverse_projection = _plane_projection(reverse, [n_medium] * base["f"].reshape(-1).size, z_reference_nm=0.0)
    wavelength_pass = bool(np.allclose(reverse_projection["wavelengths_nm"], np.sort(C0 / base["f"].reshape(-1) * 1e9)))
    tests["wavelength_order"] = {"pass": wavelength_pass, "wavelengths_nm": reverse_projection["wavelengths_nm"].tolist()}
    if not wavelength_pass:
        raise AssertionError("wavelength_order")

    planes = {}
    local_indices = {}
    for plane, z_nm in zip(PLANES, (-100.0, 1150.0, 1800.0)):
        planes[plane] = _synthetic_raw(65, 17, z_nm * 1e-9, n_medium, amplitudes)
        local_indices[plane] = [n_medium]
    canonical = canonical_state_from_raw(planes, local_indices)
    gauged_planes = {}
    for plane, raw in planes.items():
        gauged_planes[plane] = {key: value * np.exp(1j * 0.731) if key in FIELD_NAMES else value for key, value in raw.items()}
    gauged = canonical_state_from_raw(gauged_planes, local_indices)
    gauge_report = compare_states(canonical, gauged)
    gauge_error = float(gauge_report["aggregate"]["max"])
    tests["global_representation_phase"] = {"pass": gauge_error < 2e-10, "max_error": gauge_error}
    if not tests["global_representation_phase"]["pass"]:
        raise AssertionError("global_representation_phase")

    relative_planes = {plane: {key: value.copy() if isinstance(value, np.ndarray) else value for key, value in raw.items()} for plane, raw in gauged_planes.items()}
    relative_planes["PRENP"]["Ex"][:, :, 0, :] *= np.exp(1j * 0.31)
    relative_state = canonical_state_from_raw(relative_planes, local_indices)
    relative_report = compare_states(canonical, relative_state)
    relative_error = float(relative_report["aggregate"]["max"])
    tests["relative_phase_perturbation"] = {"pass": relative_error > 1e-4, "max_error": relative_error}
    if not tests["relative_phase_perturbation"]["pass"]:
        raise AssertionError("relative_phase_perturbation")

    plus = _plane_projection(_synthetic_raw(129, 33, 0.0, n_medium, {(1, 0, 1, "TE"): 1.0}), [n_medium], z_reference_nm=0.0)
    plus_index = list(map(tuple, plus["orders"])).index((1, 0))
    order_pass = abs(plus["coefficients"][0, plus_index, 0, 0] - 1.0) < 2e-10
    tests["order_indexing_positive_x"] = {"pass": bool(order_pass), "order": [1, 0], "direction": "+x"}
    if not order_pass:
        raise AssertionError("order_indexing_positive_x")

    phase_candidate = {key: value.copy() if isinstance(value, np.ndarray) else value for key, value in canonical.items()}
    phase_candidate["coefficients"] = np.asarray(canonical["coefficients"]).copy()
    phase_candidate["coefficients"][1, 0, plus_index, 0, 0] *= np.exp(1j * 0.5)
    phase_report = compare_states(canonical, phase_candidate)
    phase_error = float(phase_report["aggregate"]["max"])
    tests["no_power_only_collapse"] = {"pass": phase_error > 1e-4, "max_error": phase_error}
    if not tests["no_power_only_collapse"]["pass"]:
        raise AssertionError("no_power_only_collapse")
    return {"schema_version": "PW_COMPLEX_FLOQUET_STATE_ZERO_SOLVER_TESTS_V1", "status": "PASS", "tests": tests}
