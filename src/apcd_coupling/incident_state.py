"""Generic single-frequency incident-state and polarization contract helpers."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

C0_M_PER_S = 299_792_458.0
REAL_KX_TOLERANCE_REL = 1e-9
TRANSVERSALITY_TOLERANCE = 1e-12


@dataclass(frozen=True)
class IncidentState:
    wavelength_nm: float
    ux: float
    uy: float
    polarization_branch: str
    theta_air_in_deg: float
    angle_convention_id: str = "air_side_far_field_conserved_real_kx_v1"

    def __post_init__(self) -> None:
        if self.wavelength_nm <= 0 or not math.isfinite(self.wavelength_nm):
            raise ValueError("wavelength_nm must be finite and positive")
        if not all(math.isfinite(float(v)) for v in (self.ux, self.uy, self.theta_air_in_deg)):
            raise ValueError("incident state values must be finite")
        if self.polarization_branch not in {"P_XLIKE", "S_YLIKE"}:
            raise ValueError("polarization_branch must be P_XLIKE or S_YLIKE")
        if abs(float(self.uy)) > REAL_KX_TOLERANCE_REL:
            raise ValueError("this contract requires ky/k0=0")

    @classmethod
    def from_air_angle(cls, theta_air_deg: float, polarization_branch: str) -> "IncidentState":
        theta = float(theta_air_deg)
        return cls(
            wavelength_nm=450.0,
            ux=math.sin(math.radians(theta)),
            uy=0.0,
            polarization_branch=polarization_branch,
            theta_air_in_deg=theta,
        )

    @property
    def k0_real(self) -> float:
        return 2.0 * math.pi / (self.wavelength_nm * 1e-9)

    @property
    def real_kx(self) -> float:
        return self.k0_real * float(self.ux)

    @property
    def polarization_angle_deg(self) -> float:
        return 0.0 if self.polarization_branch == "P_XLIKE" else 90.0

    @property
    def linear_polarization(self) -> str:
        return "x" if self.polarization_branch == "P_XLIKE" else "y"

    @property
    def state_id(self) -> str:
        return f"{self.polarization_branch}_{self.theta_air_in_deg:+g}".replace("+", "P").replace("-", "M").replace(".0", "")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "k0_real": self.k0_real,
                "real_kx": self.real_kx,
                "polarization_angle_deg": self.polarization_angle_deg,
                "linear_polarization": self.linear_polarization,
                "state_id": self.state_id,
            }
        )
        return data

    def sha256(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def air_angle_states() -> list[IncidentState]:
    states: list[IncidentState] = []
    for theta in (-10.0, -5.0, 0.0, 5.0, 10.0):
        for branch in ("P_XLIKE", "S_YLIKE"):
            states.append(IncidentState.from_air_angle(theta, branch))
    return states


def passive_forward_kz(n_complex: complex, state: IncidentState) -> complex:
    kz = complex((n_complex * n_complex - state.ux * state.ux) ** 0.5 * state.k0_real)
    if kz.real < 0.0:
        kz = -kz
    if abs(kz.real) < 1e-15 and kz.imag < 0.0:
        kz = -kz
    return kz


def polarization_vector(n_complex: complex, state: IncidentState) -> tuple[complex, complex, complex]:
    if state.polarization_branch == "S_YLIKE":
        return (0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j)
    kz = passive_forward_kz(n_complex, state)
    kx = state.real_kx
    norm = (abs(kz) ** 2 + abs(kx) ** 2) ** 0.5
    return (kz / norm, 0.0 + 0.0j, -kx / norm)


def transversality_residual(n_complex: complex, state: IncidentState) -> float:
    kz = passive_forward_kz(n_complex, state)
    k = (state.real_kx, 0.0, kz)
    e = polarization_vector(n_complex, state)
    dot = k[0] * e[0] + k[1] * e[1] + k[2] * e[2]
    denom = sum(abs(value) ** 2 for value in k) ** 0.5 * sum(abs(value) ** 2 for value in e) ** 0.5
    return float(abs(dot) / denom) if denom else 0.0
