from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

C_M_PER_S = 299_792_458.0
REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "configs" / "mdc_defect_450_material_policy.json"
ALIASES = {"tio22": "APCD_TIO2_NATIVE_M1", "sio222": "APCD_SIO2_NATIVE_M1"}
REQUIRED_COLUMNS = {"frequency_hz", "wavelength_nm", "epsilon_real", "epsilon_imag", "n_real", "k_imag", "material_name"}


def load_mdc_material_policy() -> dict[str, Any]:
    with POLICY_PATH.open(encoding="utf-8-sig") as handle:
        policy = json.load(handle)
    if policy.get("policy_id") != "MDC_NATIVE_M1" or policy["interpolation"].get("extrapolation") != "forbidden":
        raise ValueError("invalid MDC Native-M1 material policy")
    return policy


def resolve_material_id(material_id: str) -> str:
    canonical = ALIASES.get(material_id, material_id)
    if canonical not in load_mdc_material_policy()["materials"]:
        raise KeyError(f"unknown material id: {material_id}")
    return canonical


@lru_cache(maxsize=1)
def _native_table() -> dict[str, dict[str, np.ndarray]]:
    policy = load_mdc_material_policy()
    path = REPO_ROOT / policy["reference"]["native_sampled_csv"]
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not REQUIRED_COLUMNS.issubset(rows[0]):
        raise ValueError("native sampled CSV schema is invalid")
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(resolve_material_id(row["material_name"]), []).append(row)
    table: dict[str, dict[str, np.ndarray]] = {}
    for material_id, group in groups.items():
        group.sort(key=lambda row: float(row["frequency_hz"]))
        frequency = np.asarray([float(row["frequency_hz"]) for row in group])
        wavelength = np.asarray([float(row["wavelength_nm"]) for row in group])
        epsilon = np.asarray([complex(float(row["epsilon_real"]), float(row["epsilon_imag"])) for row in group])
        expected_samples = int(policy["materials"][material_id].get("sample_count", 101))
        if len(group) != expected_samples or not np.all(np.isfinite(frequency)) or not np.all(np.isfinite(wavelength)):
            raise ValueError(f"invalid native samples for {material_id}")
        if not np.all(np.diff(frequency) > 0) or len(np.unique(frequency)) != expected_samples:
            raise ValueError(f"frequency axis is invalid for {material_id}")
        if not np.all(np.isfinite(epsilon.real)) or not np.all(np.isfinite(epsilon.imag)):
            raise ValueError(f"epsilon is invalid for {material_id}")
        table[material_id] = {"frequency_hz": frequency, "wavelength_nm": wavelength, "epsilon": epsilon}
    if set(table) != set(policy["materials"]):
        raise ValueError("native material set does not match policy")
    return table


def load_native_sampled_epsilon(material_id: str | None = None):
    table = _native_table()
    if material_id is None:
        return {key: {name: value.copy() for name, value in data.items()} for key, data in table.items()}
    data = table[resolve_material_id(material_id)]
    return {name: value.copy() for name, value in data.items()}


def _interpolate_epsilon(material_id: str, wavelength_nm):
    data = _native_table()[resolve_material_id(material_id)]
    values = np.asarray(wavelength_nm, dtype=float)
    scalar = values.ndim == 0
    if not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("wavelength must be finite and positive")
    frequency = C_M_PER_S / values * 1e9
    axis = data["frequency_hz"]
    if np.any(frequency < axis[0]) or np.any(frequency > axis[-1]):
        raise ValueError("wavelength is outside the native sampled range")
    flat = frequency.reshape(-1)
    epsilon = np.interp(flat, axis, data["epsilon"].real) + 1j * np.interp(flat, axis, data["epsilon"].imag)
    return epsilon.reshape(values.shape), scalar


def get_complex_epsilon(material_id: str, wavelength_nm):
    epsilon, scalar = _interpolate_epsilon(material_id, wavelength_nm)
    return complex(epsilon.reshape(())) if scalar else epsilon


def physical_principal_sqrt_epsilon(epsilon):
    values = np.asarray(epsilon, dtype=complex)
    result = np.sqrt(values)
    if np.any(result.real < -1e-12) or np.any(result.imag < -1e-12):
        raise ValueError("epsilon cannot produce a passive physical principal index")
    return complex(result.reshape(())) if result.ndim == 0 else result


def get_complex_index(material_id: str, wavelength_nm):
    return physical_principal_sqrt_epsilon(get_complex_epsilon(material_id, wavelength_nm))


def get_native_epsilon_samples(material_id: str) -> dict[str, np.ndarray]:
    data = load_native_sampled_epsilon(material_id)
    return {key: data[key] for key in ("frequency_hz", "epsilon")}


def quarter_wave_thickness_nm(material_id: str, wavelength_nm: float = 450.0) -> float:
    index = get_complex_index(material_id, wavelength_nm)
    if index.real <= 0:
        raise ValueError("non-positive refractive index")
    return float(wavelength_nm / (4.0 * index.real))


def half_wave_thickness_nm(material_id: str, wavelength_nm: float = 450.0) -> float:
    return 2.0 * quarter_wave_thickness_nm(material_id, wavelength_nm)


def material_metadata(material_id: str) -> dict[str, Any]:
    policy = load_mdc_material_policy()
    canonical = resolve_material_id(material_id)
    data = _native_table()[canonical]
    return {"material_id": canonical, "policy_id": policy["policy_id"], "sample_count": len(data["frequency_hz"]), "wavelength_range_nm": [float(data["wavelength_nm"].min()), float(data["wavelength_nm"].max())], "interpolation_axis": "frequency_hz", "interpolation_method": "linear_complex_epsilon", "extrapolation": "forbidden", "source": policy["materials"][canonical], "loss_warning": "high_loss_warning_retained" if canonical == "APCD_GAN_NATIVE_M1" else None}


def load_material(material_id: str) -> dict[str, Any]:
    """Return canonical sampled complex material data; no constant-index fallback exists."""
    canonical = resolve_material_id(material_id)
    data = load_native_sampled_epsilon(canonical)
    return {"canonical_id": canonical, "frequency_hz": data["frequency_hz"], "epsilon_complex": data["epsilon"], "n_complex": physical_principal_sqrt_epsilon(data["epsilon"]), "valid_frequency_hz": [float(data["frequency_hz"].min()), float(data["frequency_hz"].max())], "valid_wavelength_nm": [float(data["wavelength_nm"].min()), float(data["wavelength_nm"].max())], "source_provenance": material_metadata(canonical)["source"], "loss_warning": material_metadata(canonical)["loss_warning"]}


def display_policy() -> dict[str, Any]:
    """Return visualization-only colors; never part of optical material data."""
    return load_mdc_material_policy().get("display_policy", {"version": 1, "units": "normalized_rgba_0_to_1", "materials": {}})


def _lumerical_color(canonical_id: str) -> list[float] | None:
    entry = display_policy().get("materials", {}).get(canonical_id)
    return None if entry is None else [float(x) for x in entry["rgba"]]


def register_lumerical_sampled_material(fdtd: Any, canonical_id: str, overwrite: bool = False, apply_display_style: bool = True) -> dict[str, Any]:
    """Register one canonical Native-M1 sampled material in a blank session.

    Optical sampled data and fitting settings are installed before the optional
    visualization color. SiO2 intentionally has no display color override.
    """
    canonical = resolve_material_id(canonical_id)
    material = load_material(canonical)
    if overwrite and canonical in list(fdtd.getmaterial()):
        fdtd.deletematerial(canonical)
    created = fdtd.addmaterial("Sampled data")
    fdtd.setmaterial(created, "name", canonical)
    payload = np.column_stack((material["frequency_hz"], material["epsilon_complex"]))
    fdtd.setmaterial(canonical, "sampled data", payload)
    color = _lumerical_color(canonical) if apply_display_style else None
    if color is not None:
        if len(color) != 4 or any(x < 0.0 or x > 1.0 for x in color):
            raise ValueError(f"invalid display RGBA for {canonical}")
        fdtd.setmaterial(canonical, "color", np.asarray(color, dtype=float).reshape((4, 1)))
    return {"canonical_id": canonical, "material_type": fdtd.getmaterial(canonical, "type"), "sampled_data_shape": list(np.asarray(fdtd.getmaterial(canonical, "sampled data")).shape), "display_color_applied": color is not None, "rgba": color}
