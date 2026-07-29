"""Stable, relative 2D line-dipole air-channel TMM for the MDC stack.

This module intentionally reports a reciprocity-derived *relative* air-side
channel power.  It is not a Sommerfeld-integrated total power, extraction
efficiency, LDOS, or Purcell calculation.
"""
from __future__ import annotations

import cmath
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
import apcd_native_materials as native  # noqa: E402

AIR_EPSILON = 1.0 + 0.0j
ALTERNATIVE_HASH = "c38694d6f162c04322ae8a87def91622d4fd4f272e4ec286e85acc978f74d888"
ALTERNATIVE_LAYERS = (("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 79.0),
                      ("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 79.0),
                      ("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 316.0),
                      ("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 79.0),
                      ("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 79.0),
                      ("APCD_TIO2_NATIVE_M1", 44.0), ("APCD_SIO2_NATIVE_M1", 79.0))


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    geometry_hash: str
    layers: tuple[tuple[str, float], ...]


BARE_GAN_AIR = Candidate("BARE_GAN_AIR", "bare_gan_air_no_stack_v1", ())
P1_ZL1_ALTERNATIVE_G3_A3 = Candidate("P1_ZL1_ALTERNATIVE_G3_A3", ALTERNATIVE_HASH, ALTERNATIVE_LAYERS)


def passive_ky(epsilon: complex, k0: float, kx: complex) -> complex:
    """Outgoing/passive branch: Im(ky)>=0, then Re(ky)>=0 at grazing."""
    ky = cmath.sqrt(epsilon * k0 * k0 - kx * kx)
    if ky.imag < -1e-12 or (abs(ky.imag) <= 1e-12 and ky.real < 0):
        ky = -ky
    return ky


def admittance(epsilon: complex, ky: complex, k0: float, polarization: str) -> complex:
    if polarization == "TE":
        return ky / k0
    if polarization == "TM":
        return epsilon * k0 / ky
    raise ValueError("polarization must be TE or TM")


def interface_smatrix(q_left: complex, q_right: complex) -> tuple[complex, complex, complex, complex]:
    """(r_left, t_left_right, t_right_left, r_right) for power amplitudes."""
    den = q_left + q_right
    return ((q_left - q_right) / den, 2 * q_left / den,
            2 * q_right / den, (q_right - q_left) / den)


def compose_smatrix(a, b):
    """Redheffer star product for scalar two-port scattering matrices."""
    r_a, t_a, tp_a, rp_a = a
    r_b, t_b, tp_b, rp_b = b
    den = 1 - rp_a * r_b
    return (r_a + tp_a * r_b * t_a / den,
            t_b * t_a / den,
            tp_a * tp_b / den,
            rp_b + t_b * rp_a * tp_b / den)


def propagation_smatrix(ky: complex, thickness_nm: float):
    phase = cmath.exp(1j * ky * thickness_nm)
    return (0j, phase, phase, 0j)


def _epsilon(material_id: str, wavelength_nm: float) -> complex:
    return AIR_EPSILON if material_id == "AIR" else native.get_complex_epsilon(material_id, wavelength_nm)


def rt_smatrix(n_in_epsilon: complex, n_out_epsilon: complex, layers: Iterable[tuple[str, float]],
               wavelength_nm: float, air_angle_deg: float, polarization: str) -> dict[str, complex | float]:
    """Stable scattering-matrix r/t with real conserved air-side kx."""
    k0 = 2 * math.pi / wavelength_nm
    kx = k0 * math.sin(math.radians(air_angle_deg))
    epsilons = [n_in_epsilon] + [_epsilon(name, wavelength_nm) for name, _ in layers] + [n_out_epsilon]
    kys = [passive_ky(eps, k0, kx) for eps in epsilons]
    qs = [admittance(eps, ky, k0, polarization) for eps, ky in zip(epsilons, kys)]
    s = interface_smatrix(qs[0], qs[1])
    for index, (_, thickness) in enumerate(layers):
        s = compose_smatrix(s, propagation_smatrix(kys[index + 1], thickness))
        s = compose_smatrix(s, interface_smatrix(qs[index + 1], qs[index + 2]))
    r, t, _, _ = s
    flux_ratio = float(np.real(qs[-1]) / np.real(qs[0]))
    R, T = abs(r) ** 2, max(0.0, flux_ratio * abs(t) ** 2)
    if not all(np.isfinite((R, T))) or R < -1e-10 or T < -1e-10:
        raise FloatingPointError("non-finite passive S-matrix result")
    return {"r": r, "t": t, "R": float(R), "T": float(T), "ky_source": kys[0], "ky_air": kys[-1]}


def dipole_channel(candidate: Candidate, wavelength_nm: float, air_angle_deg: float,
                   source_depth_nm: float, orientation: str) -> dict[str, float | complex]:
    """Relative reciprocal air-channel emission for one in-plane 2D dipole.

    The source phase is retained for the depth-continuity audit; with no lower
    reflector in this layered half-space its magnitude cancels in relative
    channel power, which is physically expected for this limited model.
    """
    pol = "TM" if orientation == "x" else "TE" if orientation == "z" else None
    if pol is None:
        raise ValueError("orientation must be x or z")
    eps_gan = native.get_complex_epsilon("APCD_GAN_NATIVE_M1", wavelength_nm)
    rt = rt_smatrix(eps_gan, AIR_EPSILON, candidate.layers, wavelength_nm, air_angle_deg, pol)
    k0 = 2 * math.pi / wavelength_nm
    kx = k0 * math.sin(math.radians(air_angle_deg))
    # In-plane line-dipole coupling weights under the stated x-y invariant 2D convention.
    source_weight = abs(rt["ky_source"] / (k0 * cmath.sqrt(eps_gan))) ** 2 if orientation == "x" else 1.0
    source_phase = cmath.exp(1j * rt["ky_source"] * source_depth_nm)
    relative = float(max(0.0, source_weight * rt["T"]))
    return {"I_air_relative": relative, "source_phase": source_phase, "r": rt["r"], "t": rt["t"],
            "T_plane_wave": rt["T"], "ky_source": rt["ky_source"], "kx": kx}


def fwhm(grid: np.ndarray, values: np.ndarray) -> float:
    if len(grid) < 2 or np.max(values) <= 0:
        return float("nan")
    half = np.max(values) * .5
    indices = np.flatnonzero(values >= half)
    return float(grid[indices[-1]] - grid[indices[0]]) if len(indices) else float("nan")


def cone_fraction(angles: np.ndarray, values: np.ndarray, cone_deg: float) -> float:
    total = np.trapezoid(values, np.deg2rad(angles))
    mask = np.abs(angles) <= cone_deg
    return float(np.trapezoid(values[mask], np.deg2rad(angles[mask])) / total) if total > 0 else float("nan")
