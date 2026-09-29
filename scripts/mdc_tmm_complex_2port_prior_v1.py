"""Frozen complex two-port prior for the fixed MDC coupling stack.

This module is deliberately limited to the current plane-wave MDC stack.  It
does not read DOE96 dipole profiles and it does not invoke FDTD.  The returned
amplitudes are E-field-basis complex scattering amplitudes at the two physical
MDC reference planes; the extra SiO2 spacer is intentionally excluded.
"""
from __future__ import annotations

import cmath
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from apcd_native_materials import get_complex_index, material_metadata
from mdc_tmm_complex_incident_power_v1 import normal_stack_power, oblique_stack_rt


MODEL_ID = "MDC_TMM_COMPLEX_2PORT_PRIOR_V1"
AUDITED_BASE_COMMIT = "8d1380355ae2c5548d7f0c66a783b413982c8a7c"
LEFT_PORT_MATERIAL = "APCD_GAN_NATIVE_M1"
RIGHT_PORT_MATERIAL = "APCD_SIO2_NATIVE_M1"
SPACER_MATERIAL = "APCD_SIO2_NATIVE_M1"
MDC_STRUCTURE_ID = "P1_ZL1_ALTERNATIVE_G3_A3"
MDC_STACK_FROM_LEFT: tuple[tuple[str, float], ...] = (
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 79.0),
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 79.0),
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 316.0),
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 79.0),
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 79.0),
    ("APCD_TIO2_NATIVE_M1", 44.0),
    ("APCD_SIO2_NATIVE_M1", 79.0),
)
MDC_THICKNESS_NM = 975.0
EXTRA_SPACER_NM = 237.0
WAVELENGTHS_NM = tuple(float(value) for value in range(440, 461))
ANGLE_DEG = 0.0
POLARIZATIONS = ("TE", "TM")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_repo_root(), text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _complex_record(value: complex) -> dict[str, float]:
    value = complex(value)
    return {
        "Re": float(value.real),
        "Im": float(value.imag),
        "magnitude": float(abs(value)),
        "phase_rad": float(cmath.phase(value)),
    }


def _normal_response(
    n_in: complex,
    n_out: complex,
    layers: list[tuple[complex, float]],
    wavelength_nm: float,
) -> dict[str, Any]:
    # The frozen normal-incidence E/H implementation is polarization-degenerate.
    return normal_stack_power(n_in, n_out, layers, wavelength_nm)


def _response_for_direction(wavelength_nm: float, direction: str) -> dict[str, Any]:
    n_left = get_complex_index(LEFT_PORT_MATERIAL, wavelength_nm)
    n_right = get_complex_index(RIGHT_PORT_MATERIAL, wavelength_nm)
    layers = [
        (get_complex_index(material, wavelength_nm), thickness)
        for material, thickness in MDC_STACK_FROM_LEFT
    ]
    if direction == "L_to_R":
        response = _normal_response(n_left, n_right, layers, wavelength_nm)
    elif direction == "R_to_L":
        response = _normal_response(n_right, n_left, list(reversed(layers)), wavelength_nm)
    else:
        raise ValueError(f"unknown direction: {direction}")
    return {"response": response, "n_left": n_left, "n_right": n_right}


def evaluate_row(wavelength_nm: float, angle_deg: float = ANGLE_DEG) -> dict[str, Any]:
    if angle_deg != 0.0:
        raise ValueError("V1 grid is normal incidence only; no oblique extrapolation is allowed")
    left = _response_for_direction(wavelength_nm, "L_to_R")["response"]
    right = _response_for_direction(wavelength_nm, "R_to_L")["response"]
    n_left = get_complex_index(LEFT_PORT_MATERIAL, wavelength_nm)
    n_right = get_complex_index(RIGHT_PORT_MATERIAL, wavelength_nm)
    reciprocity = n_right * left["t"] - n_left * right["t"]
    return {
        "wavelength_nm": float(wavelength_nm),
        "angle_deg": 0.0,
        "polarization": "P_XLIKE_NORMAL_DEGENERATE_TE_TM",
        "r_L_Re": _complex_record(left["r"])["Re"],
        "r_L_Im": _complex_record(left["r"])["Im"],
        "t_LR_Re": _complex_record(left["t"])["Re"],
        "t_LR_Im": _complex_record(left["t"])["Im"],
        "r_R_Re": _complex_record(right["r"])["Re"],
        "r_R_Im": _complex_record(right["r"])["Im"],
        "t_RL_Re": _complex_record(right["t"])["Re"],
        "t_RL_Im": _complex_record(right["t"])["Im"],
        "R_L": float(left["R"]),
        "T_LR": float(left["T"]),
        "R_R": float(right["R"]),
        "T_RL": float(right["T"]),
        "r_L_magnitude": _complex_record(left["r"])["magnitude"],
        "r_L_phase_rad": _complex_record(left["r"])["phase_rad"],
        "t_LR_magnitude": _complex_record(left["t"])["magnitude"],
        "t_LR_phase_rad": _complex_record(left["t"])["phase_rad"],
        "r_R_magnitude": _complex_record(right["r"])["magnitude"],
        "r_R_phase_rad": _complex_record(right["r"])["phase_rad"],
        "t_RL_magnitude": _complex_record(right["t"])["magnitude"],
        "t_RL_phase_rad": _complex_record(right["t"])["phase_rad"],
        "power_entering_L": float(left["power_entering"]),
        "power_entering_R": float(right["power_entering"]),
        "A_stack_L": float(left["A_stack"]),
        "A_stack_R": float(right["A_stack"]),
        "R_plus_T_L": float(left["R"] + left["T"]),
        "R_plus_T_R": float(right["R"] + right["T"]),
        "power_closure_L": float(left["power_entering"] - left["T"] - left["A_stack"]),
        "power_closure_R": float(right["power_entering"] - right["T"] - right["A_stack"]),
        "reciprocity_residual_Re": float(reciprocity.real),
        "reciprocity_residual_Im": float(reciprocity.imag),
    }


def verify_normal_incidence_degeneracy() -> dict[str, Any]:
    checks = []
    for wavelength_nm in WAVELENGTHS_NM:
        n_left = get_complex_index(LEFT_PORT_MATERIAL, wavelength_nm)
        n_right = get_complex_index(RIGHT_PORT_MATERIAL, wavelength_nm)
        layers = [(get_complex_index(material, wavelength_nm), thickness) for material, thickness in MDC_STACK_FROM_LEFT]
        # Exercise both frozen polarization labels through the existing oblique
        # entry point.  At kx=0 it deliberately delegates to the same E/H
        # normal-incidence basis, which is the physical TE/TM degeneracy here.
        te = oblique_stack_rt(n_left, n_right, layers, wavelength_nm, 0.0, "TE")
        tm = oblique_stack_rt(n_left, n_right, layers, wavelength_nm, 0.0, "TM")
        checks.append(max(abs(te[key] - tm[key]) for key in ("r", "t", "R", "T")))
    maximum = float(max(checks))
    return {"exact_at_normal_incidence": bool(maximum == 0.0), "max_abs_difference": maximum}


def evaluate_prior() -> dict[str, Any]:
    rows = [evaluate_row(wavelength_nm) for wavelength_nm in WAVELENGTHS_NM]
    degeneracy = verify_normal_incidence_degeneracy()
    max_power_closure = max(
        max(abs(row["power_closure_L"]), abs(row["power_closure_R"])) for row in rows
    )
    max_reciprocity = max(
        abs(complex(row["reciprocity_residual_Re"], row["reciprocity_residual_Im"]))
        for row in rows
    )
    return {
        "model_id": MODEL_ID,
        "schema_version": "MDC_TMM_COMPLEX_2PORT_PRIOR_V1",
        "status": "FROZEN",
        "source_authority": {
            "audited_base_commit": AUDITED_BASE_COMMIT,
            "generated_from_commit": _git_commit(),
            "mdc_structure_id": MDC_STRUCTURE_ID,
            "coupling_interface_contract": "APCD_MDC_NP_ONE_WAY_POWER_INTERFACE_V1",
            "coupling_interface_contract_path": "contracts/coupling/interface_stack_v1.json",
            "coupling_interface_contract_sha256": "1bb8bb792fc0e36c8073679b0afa25e48855127756fdcd426663554d21c5b9f6",
            "coupling_coordinate_contract_sha256": "b8bf2b956b68dcfc8aae9532936c3ac4e24eed74b6cf44a909da258be10a4257",
        },
        "port_media": {
            "left": {"role": "incident_side", "material": LEFT_PORT_MATERIAL},
            "right": {"role": "coupling_spacer_side", "material": RIGHT_PORT_MATERIAL},
            "right_medium_is_air": False,
            "extra_spacer": {"material": SPACER_MATERIAL, "thickness_nm": EXTRA_SPACER_NM},
        },
        "tmm_conventions": {
            "material_policy": "MDC_NATIVE_M1",
            "dispersion": "linear_complex_epsilon_on_frequency_axis; extrapolation_forbidden",
            "lambda_convention": "wavelength_nm_in_vacuum",
            "angle_convention": "air-side/conserved-kx convention; V1 normal incidence theta=0",
            "polarization": "TE/TM E-field basis; P_XLIKE at normal incidence",
            "normal_incidence_te_tm_degeneracy": degeneracy,
            "field_amplitude_basis": "electric-field amplitude, not power-normalized amplitude",
            "power_normalization": "R=|r|^2; T=|t|^2*Re(n_out)/Re(n_in)",
            "time_convention": "exp(-i omega t)",
            "forward_propagation": "exp(+i k_z z), passive Im(n)>=0",
            "matrix_sign": "frozen existing physical branch sign=-i",
        },
        "reference_planes": {
            "left_reference_plane": "GaN/MDC first-layer interface, z=0 nm",
            "right_reference_plane": "MDC top / extra-spacer entrance, z=975 nm",
            "included_mdc_thickness_nm": MDC_THICKNESS_NM,
            "excluded_spacer_thickness_nm": EXTRA_SPACER_NM,
            "phase_origin": "left reference plane",
            "spacer_phase_rule": "append exp(+i*kz_spacer*d) exactly once in compositor",
        },
        "stack": {
            "layers_from_left": [{"material": material, "thickness_nm": thickness} for material, thickness in MDC_STACK_FROM_LEFT],
            "total_thickness_nm": MDC_THICKNESS_NM,
            "top_termination": "APCD_SIO2_NATIVE_M1:79nm",
        },
        "grid": {
            "wavelength_nm": {"start": 440.0, "stop": 460.0, "step": 1.0, "count": len(WAVELENGTHS_NM)},
            "angle_deg": [0.0],
            "polarization": ["P_XLIKE_NORMAL_DEGENERATE_TE_TM"],
        },
        "rows": rows,
        "power_consistency": {
            "max_abs_power_closure": float(max_power_closure),
            "max_abs_reciprocity_residual": float(max_reciprocity),
            "R_plus_T_interpretation": "diagnostic only for absorbing port media; use power_entering and A_stack for physical balance",
            "lossy_port_policy": "do not force R+T=1 when Native-M1 port has nonzero Im(n)",
        },
        "semantic_boundaries": {
            "TMM_vs_DOE96_DIPOLAR_PROFILE": "NOT_DIRECTLY_COMPARABLE",
            "v3_c_role": "MDC_V3_C_DIPOLE_PROFILE_ROLE / DIPOLE_PROFILE_AUXILIARY_ONLY",
            "dipole_fields_are_plane_wave_transfer": False,
        },
        "current_fixed_mdc_role": {
            "identical_across_k6_geometries": True,
            "condition": "fixed MDC and fixed wavelength/source condition",
            "allowed": ["spectral amplitude conditioning", "phase conditioning", "cavity/reference response", "composition with spacer and NP", "future residual-model baseline"],
            "not_allowed": ["K6 geometry discrimination", "absolute power claim", "LEE", "Level-1 coupling truth"],
        },
        "future_component_compositor_interface": {
            "inputs": ["MDC two-port S(λ,kx,pol)", "spacer propagation exp(+i*kz*d)", "NP complex scattering state"],
            "output": "C_component",
            "composition_policy": "support full two-port multiple-reflection composition; do not assume a single-pass product",
            "spacer_thickness_nm": EXTRA_SPACER_NM,
        },
        "artifact_provenance": {
            "source_code": "scripts/mdc_tmm_complex_2port_prior_v1.py",
            "existing_tmm_dependency": "scripts/mdc_tmm_complex_incident_power_v1.py",
            "native_material_metadata": {
                LEFT_PORT_MATERIAL: material_metadata(LEFT_PORT_MATERIAL),
                RIGHT_PORT_MATERIAL: material_metadata(RIGHT_PORT_MATERIAL),
                "APCD_TIO2_NATIVE_M1": material_metadata("APCD_TIO2_NATIVE_M1"),
            },
        },
    }


def write_prior(path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evaluate_prior(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    write_prior(_repo_root() / "reports" / f"{MODEL_ID}.json")
