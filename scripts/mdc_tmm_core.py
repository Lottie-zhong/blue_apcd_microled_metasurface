from __future__ import annotations

import cmath
import math
from typing import Iterable

import numpy as np

import apcd_native_materials as materials

N_AIR = 1.0 + 0j
N_GAN = 2.41 + 0j  # Existing MDC GaN model; deliberately unchanged.


def _cos_from_sin(value: complex) -> complex:
    result = cmath.sqrt(1 - value * value)
    return -result if result.real < 0 or (abs(result.real) < 1e-14 and result.imag < 0) else result


def _admittance(index: complex, cosine: complex, polarization: str) -> complex:
    if polarization == "TE":
        return index * cosine
    if polarization == "TM":
        return cosine / index
    raise ValueError("polarization must be TE or TM")


def tmm_complex(n_in: complex, n_out: complex, layers: Iterable[tuple[complex, float]], wavelength_nm: float, theta_in_deg: float, polarization: str) -> dict[str, float]:
    sin_in = math.sin(math.radians(theta_in_deg))
    cos_in = _cos_from_sin(sin_in)
    q_in = _admittance(n_in, cos_in, polarization)
    matrix = np.eye(2, dtype=complex)
    for index, thickness_nm in layers:
        sine = n_in * sin_in / index
        cosine = _cos_from_sin(sine)
        q = _admittance(index, cosine, polarization)
        delta = 2 * math.pi * index * thickness_nm * cosine / wavelength_nm
        layer = np.array([[cmath.cos(delta), 1j * cmath.sin(delta) / q], [1j * q * cmath.sin(delta), cmath.cos(delta)]])
        matrix = matrix @ layer
    cos_out = _cos_from_sin(n_in * sin_in / n_out)
    q_out = _admittance(n_out, cos_out, polarization)
    a, b, c, d = matrix.ravel()
    denominator = q_in * a + q_in * q_out * b + c + q_out * d
    reflection = (q_in * a + q_in * q_out * b - c - q_out * d) / denominator
    transmission = 2 * q_in / denominator
    r = abs(reflection) ** 2
    t = float(np.real(q_out / q_in) * abs(transmission) ** 2)
    if not np.isfinite(r) or not np.isfinite(t) or r < -1e-9 or t < -1e-9 or r + t > 1.000001:
        raise ValueError("non-physical or non-finite TMM power result")
    return {"R": float(r), "T": t, "R_plus_T": float(r + t)}


def material_layers(wavelength_nm: float, material_model: str, design_layers: list[tuple[str, float]]) -> list[tuple[complex, float]]:
    if material_model == "native_m1":
        lookup = {"H": "APCD_TIO2_NATIVE_M1", "L": "APCD_SIO2_NATIVE_M1"}
        return [(materials.get_complex_index(lookup[key], wavelength_nm), thickness) for key, thickness in design_layers]
    if material_model == "legacy_constant_index":
        lookup = {"H": 2.25 + 0j, "L": 1.47 + 0j}
        return [(lookup[key], thickness) for key, thickness in design_layers]
    raise ValueError("material_model must be native_m1 or explicit legacy_constant_index")


def emission_tmm(design_layers: list[tuple[str, float]], wavelength_nm: float, theta_air_deg: float, polarization: str, material_model: str = "native_m1") -> dict[str, float]:
    theta_gan = math.degrees(math.asin(float(N_AIR.real / N_GAN.real) * math.sin(math.radians(theta_air_deg))))
    layers = list(reversed(material_layers(wavelength_nm, material_model, design_layers)))
    return tmm_complex(N_GAN, N_AIR, layers, wavelength_nm, theta_gan, polarization)
