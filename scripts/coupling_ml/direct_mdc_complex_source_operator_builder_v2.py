"""Guarded complex-source angular-spectrum utilities for APCD Coupling ML.

This builder intentionally does not equate a finite-domain FFT with the
periodic Level-2A Bloch input basis. A separately audited Floquet/Bloch bridge
is required before any returned spectrum may be used in an operator integral.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


BUILDER_ID = "DIRECT_MDC_COMPLEX_SOURCE_OPERATOR_BUILDER_V2"
SCHEMA_VERSION = "direct_mdc_complex_source_operator_builder_v2"
FFT_CONVENTION = "A(kx,ky)=dx*dy*sum_xy F(x,y)*exp[-i(kx*x+ky*y)]"


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _uniform_spacing(values: np.ndarray, name: str) -> float:
    values = np.asarray(values, dtype=float).reshape(-1)
    if values.size < 2:
        raise ValueError(f"{name}_requires_at_least_two_points")
    delta = np.diff(values)
    if not np.all(delta > 0) or not np.allclose(delta, delta[0], rtol=1e-10, atol=1e-15):
        raise ValueError(f"{name}_must_be_strictly_increasing_uniform")
    return float(delta[0])


def fft2_complex_field(field_xy: np.ndarray, x_m: np.ndarray, y_m: np.ndarray) -> dict[str, np.ndarray]:
    """Return a continuous-transform-normalized discrete angular spectrum."""
    x_m = np.asarray(x_m, dtype=float).reshape(-1)
    y_m = np.asarray(y_m, dtype=float).reshape(-1)
    field_xy = np.asarray(field_xy, dtype=complex)
    if field_xy.shape != (x_m.size, y_m.size):
        raise ValueError(f"field_shape_{field_xy.shape}_not_{(x_m.size, y_m.size)}")
    dx = _uniform_spacing(x_m, "x")
    dy = _uniform_spacing(y_m, "y")
    kx = np.fft.fftshift(2 * np.pi * np.fft.fftfreq(x_m.size, d=dx))
    ky = np.fft.fftshift(2 * np.pi * np.fft.fftfreq(y_m.size, d=dy))
    raw = np.fft.fftshift(np.fft.fft2(field_xy)) * dx * dy
    phase_origin = np.exp(-1j * (kx[:, None] * x_m[0] + ky[None, :] * y_m[0]))
    return {"kx_rad_m": kx, "ky_rad_m": ky, "spectrum": raw * phase_origin}


def ps_basis(ux: float, uy: float, direction: int, refractive_index: float = 1.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return electric P, electric S, and unit-k for one propagating sector."""
    if direction not in (-1, 1):
        raise ValueError("direction_must_be_plus_or_minus_one")
    n = float(refractive_index)
    if n <= 0:
        raise ValueError("refractive_index_must_be_positive")
    tx, ty = float(ux) / n, float(uy) / n
    rho2 = tx * tx + ty * ty
    if rho2 >= 1.0 - 1e-12:
        raise ValueError("evanescent_or_grazing_sector_rejected")
    kz = direction * np.sqrt(1.0 - rho2)
    khat = np.array([tx, ty, kz], dtype=float)
    rho = np.sqrt(rho2)
    s_hat = np.array([0.0, 1.0, 0.0]) if rho < 1e-14 else np.array([-ty / rho, tx / rho, 0.0])
    p_hat = np.cross(s_hat, khat)
    p_hat /= np.linalg.norm(p_hat)
    return p_hat, s_hat, khat


def synthesize_modal_fields(
    amplitudes: dict[str, complex], ux: float, uy: float, refractive_index: float = 1.0, impedance_ohm: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """Synthesize E,H from +P,+S,-P,-S amplitudes for tests and audits."""
    electric = np.zeros(3, dtype=complex)
    magnetic = np.zeros(3, dtype=complex)
    for direction, prefix in ((1, "up"), (-1, "down")):
        p_hat, s_hat, khat = ps_basis(ux, uy, direction, refractive_index)
        for label, basis in (("P", p_hat), ("S", s_hat)):
            amplitude = complex(amplitudes.get(f"{prefix}_{label}", 0.0))
            electric += amplitude * basis
            magnetic += amplitude * np.cross(khat, basis) / impedance_ohm
    return electric, magnetic


def decompose_ps_directional(
    electric: np.ndarray,
    magnetic: np.ndarray,
    ux: float,
    uy: float,
    refractive_index: float = 1.0,
    impedance_ohm: float = 1.0,
) -> dict[str, complex]:
    """Separate coherent up/down P/S amplitudes using both E and H."""
    columns = []
    labels = []
    for direction, prefix in ((1, "up"), (-1, "down")):
        p_hat, s_hat, khat = ps_basis(ux, uy, direction, refractive_index)
        for label, basis in (("P", p_hat), ("S", s_hat)):
            columns.append(np.concatenate([basis, np.cross(khat, basis)]))
            labels.append(f"{prefix}_{label}")
    matrix = np.stack(columns, axis=1).astype(complex)
    vector = np.concatenate([np.asarray(electric, dtype=complex), impedance_ohm * np.asarray(magnetic, dtype=complex)])
    amplitudes, _, rank, _ = np.linalg.lstsq(matrix, vector, rcond=None)
    if rank != 4:
        raise RuntimeError(f"directional_ps_basis_rank_{rank}_not_4")
    return {label: complex(value) for label, value in zip(labels, amplitudes)}


def mirror_y_fields(electric: np.ndarray, magnetic: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply y->-y: E is polar and H is axial."""
    e_transform = np.diag([1.0, -1.0, 1.0])
    h_transform = np.diag([-1.0, 1.0, -1.0])
    return e_transform @ np.asarray(electric), h_transform @ np.asarray(magnetic)


def guarded_source_record(metadata: dict[str, Any]) -> dict[str, Any]:
    """Bind extracted finite-domain data to the non-equivalence gate."""
    return {
        "schema_version": SCHEMA_VERSION,
        "builder_id": BUILDER_ID,
        "fft_convention": FFT_CONVENTION,
        "source_representation": "C_FINITE_DOMAIN_COMPLEX_FIELD_BASIS",
        "direct_mdc_fft_kspace_equals_level2a_bloch_input_basis": False,
        "operator_input_compatible": False,
        "hard_gate": "SOURCE_BLOCH_DECOMPOSITION_REDESIGN_REQUIRED",
        "required_bridge": "phase-origin-bound continuous Floquet transform into periodic-supercell Bloch sectors",
        "metadata": metadata,
    }


def _assert_close(actual: complex, expected: complex, label: str, atol: float = 2e-12) -> None:
    if not np.allclose(actual, expected, rtol=0.0, atol=atol):
        raise AssertionError(f"{label}:{actual!r}!={expected!r}")


def synthetic_self_tests() -> dict[str, Any]:
    tests: dict[str, dict[str, Any]] = {}

    def modal_test(name: str, amplitudes: dict[str, complex], ux: float, uy: float) -> None:
        e, h = synthesize_modal_fields(amplitudes, ux, uy)
        recovered = decompose_ps_directional(e, h, ux, uy)
        for label in ("up_P", "up_S", "down_P", "down_S"):
            _assert_close(recovered[label], amplitudes.get(label, 0.0), f"{name}:{label}")
        tests[name] = {"pass": True, "ux": ux, "uy": uy}

    modal_test("pure_plus_z_P", {"up_P": 1.0 + 0.2j}, 0.0, 0.0)
    modal_test("pure_plus_z_S", {"up_S": -0.3 + 0.8j}, 0.0, 0.0)
    modal_test("coherent_P_S", {"up_P": 1.0 + 0.5j, "up_S": -0.4 + 0.7j}, 0.18, 0.0)
    modal_test("oblique_kx_ky", {"up_P": 0.8 - 0.1j, "up_S": 0.2 + 0.3j}, 0.25, -0.31)
    modal_test("up_down_superposition", {"up_P": 1.0, "up_S": 0.3j, "down_P": -0.2 + 0.1j, "down_S": 0.4}, 0.22, 0.17)

    ux, uy = 0.29, 0.21
    original = {"up_P": 0.7 + 0.2j, "up_S": -0.4 + 0.1j}
    e, h = synthesize_modal_fields(original, ux, uy)
    em, hm = mirror_y_fields(e, h)
    mirrored = decompose_ps_directional(em, hm, ux, -uy)
    _assert_close(mirrored["up_P"], original["up_P"], "uy_parity:P")
    _assert_close(mirrored["up_S"], -original["up_S"], "uy_parity:S")
    tests["uy_parity_transform"] = {"pass": True, "P_parity": "+", "S_parity": "-"}

    try:
        ps_basis(1.01, 0.0, 1)
        raise AssertionError("evanescent sector was not rejected")
    except ValueError as exc:
        if "evanescent" not in str(exc):
            raise
    tests["evanescent_rejection"] = {"pass": True}

    nx, ny, dx, dy = 32, 24, 0.4, 0.6
    x = (-nx / 2 + np.arange(nx)) * dx
    y = (-ny / 2 + np.arange(ny)) * dy
    kx0 = 2 * np.pi * 3 / (nx * dx)
    ky0 = 2 * np.pi * -2 / (ny * dy)
    field = np.exp(1j * (kx0 * x[:, None] + ky0 * y[None, :]))
    spectrum = fft2_complex_field(field, x, y)
    peak = np.unravel_index(np.argmax(np.abs(spectrum["spectrum"])), spectrum["spectrum"].shape)
    _assert_close(spectrum["kx_rad_m"][peak[0]], kx0, "fft:kx")
    _assert_close(spectrum["ky_rad_m"][peak[1]], ky0, "fft:ky")
    tests["fft_2d_phase_origin"] = {"pass": True}

    guard = guarded_source_record({"synthetic": True})
    if guard["operator_input_compatible"] or guard["direct_mdc_fft_kspace_equals_level2a_bloch_input_basis"]:
        raise AssertionError("non-equivalence guard failed")
    tests["bloch_non_equivalence_guard"] = {"pass": True}
    return {"schema_version": "M2O_SYNTHETIC_COMPLEX_SOURCE_TESTS_V1", "pass": all(x["pass"] for x in tests.values()), "tests": tests}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("only --self-test is enabled before the Floquet/Bloch bridge is authorized")
    result = synthetic_self_tests()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
