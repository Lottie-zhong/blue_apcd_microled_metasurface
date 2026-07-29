"""Lumerical adapter for the immutable APCD native sampled material library."""
from __future__ import annotations

from typing import Any

import numpy as np

from metasurface.apcd_material_library import get_native_samples

LUMERICAL_NAMES = {
    "APCD_TIO2_NATIVE_M1": "APCD_TIO2_NATIVE_M1",
    "APCD_SIO2_NATIVE_M1": "APCD_SIO2_NATIVE_M1",
}


def get_lumerical_material_name(material_reference_id: str) -> str:
    try:
        return LUMERICAL_NAMES[material_reference_id]
    except KeyError as exc:
        raise KeyError(f"unsupported APCD native material: {material_reference_id}") from exc


def _material_names(fdtd: Any) -> set[str]:
    raw = fdtd.getmaterial()
    if hasattr(raw, "tolist"):
        raw = raw.tolist()
    if isinstance(raw, str):
        return {item.strip() for item in raw.splitlines() if item.strip()}
    return {str(item).strip() for item in raw}


def _sampled_matrix(material_reference_id: str) -> np.ndarray:
    samples = get_native_samples(material_reference_id)
    return np.asarray([
        [complex(float(sample["frequency_hz"]), 0.0), complex(float(sample["epsilon_real"]), float(sample["epsilon_imag"]))]
        for sample in samples
    ], dtype=np.complex128)


def ensure_material(fdtd: Any, material_reference_id: str) -> str:
    """Create one Lumerical sampled material or return its explicit native name.

    There is deliberately no constant-index fallback. Any Lumerical API failure is
    propagated to the caller for a negative audit.
    """
    name = get_lumerical_material_name(material_reference_id)
    if name in _material_names(fdtd):
        return name
    temporary_name = fdtd.addmaterial("Sampled 3D data")
    temporary_name = str(temporary_name) if temporary_name else "Sampled 3D data"
    fdtd.setmaterial(temporary_name, "name", name)
    fdtd.setmaterial(name, "sampled data", _sampled_matrix(material_reference_id))
    return name


def ensure_apcd_native_materials(fdtd: Any) -> dict[str, str]:
    return {material_id: ensure_material(fdtd, material_id) for material_id in LUMERICAL_NAMES}
