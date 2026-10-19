"""Zero-solver Level-2B source-transfer projection contract."""
from __future__ import annotations
import math
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

BUILDER_ID = "LEVEL2B_SOURCE_TRANSFER_BUILDER_V2"
EXPECTED_WAVELENGTH_NM = tuple(float(x) for x in range(445, 456))
TARGET_UX = 0.37868939998860307
TARGET_UY = 0.0
REQUIRED_MONITORS = ("interface_field_monitor", "transmission_monitor", "reflection_monitor")
REFERENCE_PLANE_ID = "NP_BOTTOM_COMMON_REFERENCE_PLANE"

def _cross(a: Sequence[float], b: Sequence[float]) -> Tuple[float, float, float]:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

def _norm(a: Sequence[float]) -> float:
    return math.sqrt(sum(float(x)*float(x) for x in a))

def _unit(a: Sequence[float]) -> Tuple[float, float, float]:
    n = _norm(a)
    if n <= 0.0:
        raise ValueError("zero direction")
    return tuple(float(x)/n for x in a)  # type: ignore[return-value]

def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(x)*float(y) for x, y in zip(a, b))

def _conj(a: Sequence[complex]) -> Tuple[complex, complex, complex]:
    return tuple(complex(x).conjugate() for x in a)  # type: ignore[return-value]

def _directional_flux(e: Sequence[complex], h: Sequence[complex], direction: Sequence[float]) -> float:
    value = sum(complex(x) * float(y) for x, y in zip(_cross(e, _conj(h)), direction))
    return 0.5 * float(value.real)

def ps_basis(k_hat: Sequence[float]) -> Dict[str, Tuple[float, float, float]]:
    """Build the physical basis for a propagating k direction."""
    k = _unit(k_hat)
    rho = math.sqrt(k[0]*k[0] + k[1]*k[1])
    if rho <= 1.0e-12:
        s = (0.0, 1.0, 0.0)
        p = (1.0, 0.0, 0.0)
    else:
        s = _unit((-k[1], k[0], 0.0))
        p = _unit(_cross(s, k))
    return {"p": p, "s": s, "k": k}

def validate_exact_ux(ux_grid: Iterable[float], target_ux: float, tolerance: float = 1.0e-12) -> int:
    matches = [i for i, x in enumerate(float(v) for v in ux_grid) if abs(x-float(target_ux)) <= tolerance]
    if len(matches) != 1:
        raise ValueError("target ux is not represented exactly once; interpolation is forbidden")
    return matches[0]

def validate_wavelength_grid(wavelength_nm: Iterable[float], expected: Iterable[float] = EXPECTED_WAVELENGTH_NM) -> bool:
    if tuple(float(x) for x in wavelength_nm) != tuple(float(x) for x in expected):
        raise ValueError("wavelength grid mismatch")
    return True

def validate_monitor_contract(monitors: Mapping[str, Any], reference_plane_id: str = REFERENCE_PLANE_ID) -> bool:
    missing = [name for name in REQUIRED_MONITORS if name not in monitors]
    if missing:
        raise ValueError("missing required monitor(s): " + ",".join(missing))
    if str(monitors["interface_field_monitor"].get("reference_plane_id")) != reference_plane_id:
        raise ValueError("interface monitor is not on the common NP-bottom reference plane")
    return True

def decompose_directional_power(e_complex: Sequence[complex], h_complex: Sequence[complex],
                                k_hat: Sequence[float], impedance: float = 1.0) -> Dict[str, Any]:
    """Project complex E/H into P/S power and retain coherent cross terms."""
    if len(e_complex) != 3 or len(h_complex) != 3:
        raise ValueError("E/H must have three complex components")
    if impedance <= 0.0:
        raise ValueError("impedance must be positive")
    basis = ps_basis(k_hat)
    p, s, k = basis["p"], basis["s"], basis["k"]
    e = tuple(complex(x) for x in e_complex)
    h = tuple(complex(x) for x in h_complex)
    p_amp = sum(e[i]*p[i] for i in range(3))
    s_amp = sum(e[i]*s[i] for i in range(3))
    return {
        "direction": k,
        "p_amplitude": p_amp,
        "s_amplitude": s_amp,
        "p_power": 0.5*(abs(p_amp)**2)/float(impedance),
        "s_power": 0.5*(abs(s_amp)**2)/float(impedance),
        "p_s_cross_term": (p_amp*s_amp.conjugate()).real/float(impedance),
        "p_s_cross_term_retained": True,
        "directional_poynting_flux": _directional_flux(e, h, k),
        "propagating_only": True,
    }

def build_source_transfer_contract(source_metadata: Mapping[str, Any],
                                   interface_metadata: Mapping[str, Any],
                                   output_metadata: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "builder_id": BUILDER_ID,
        "source": dict(source_metadata),
        "interface": dict(interface_metadata),
        "output": dict(output_metadata),
        "normalization": {
            "input": "NP-bottom directional complex E/H channel power",
            "transmission": "same Bloch sector and all propagating orders iff Level2A T includes all",
            "reflection": "same sector downward reflected power / upward incident channel power",
            "emitter": "dipolepower preferred; sourcepower never substituted automatically",
        },
        "cross_terms": {"P_S_cross_term_retained": True, "cross_sector_terms_retained": True},
        "off_grid_policy": "reject; no interpolation",
    }

__all__ = ["BUILDER_ID", "EXPECTED_WAVELENGTH_NM", "TARGET_UX", "TARGET_UY",
           "REQUIRED_MONITORS", "REFERENCE_PLANE_ID", "ps_basis", "validate_exact_ux",
           "validate_wavelength_grid", "validate_monitor_contract", "decompose_directional_power",
           "build_source_transfer_contract"]
