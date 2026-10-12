"""Offline Coupling ML adapters for versioned complex physics providers.

This module contains schema guards and a synthetic algebra adapter only. It does
not load electromagnetic data, call an FDTD/RCWA solver, or claim that the
provisional cascade equation is the physical APCD contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import numpy as np


class ProviderStatus(str, Enum):
    VALIDATED_COMPLEX = "VALIDATED_COMPLEX"
    PARTIAL_COMPLEX = "PARTIAL_COMPLEX"
    POWER_ONLY = "POWER_ONLY"
    UNVERIFIED = "UNVERIFIED"
    UNAVAILABLE = "UNAVAILABLE"


class ProviderUnavailableError(ValueError):
    """Raised when no provider result exists; callers must not substitute zero."""


class IllConditionedCascadeError(ValueError):
    """Raised when the synthetic feedback solve is singular or ill-conditioned."""


@dataclass(frozen=True)
class ModeKey:
    """One ordered scattering-matrix port mode; dimension is provider-defined."""

    port_id: str
    order_m: int
    order_n: int
    polarization: str
    propagation_direction: str
    mode_kind: str


@dataclass(frozen=True)
class CascadeResult:
    coefficients: np.ndarray
    condition_number: np.ndarray


def require_full_complex_state(
    coefficients: np.ndarray | None,
    status: ProviderStatus | str,
    propagating_mask: np.ndarray | None,
    expected_shape: tuple[int, int, int] = (21, 7, 2),
) -> np.ndarray:
    """Accept only a complete validated complex state for the frozen H1 basis."""
    try:
        status = ProviderStatus(status)
    except ValueError as exc:
        raise ValueError("provider_status_unknown") from exc

    if status is ProviderStatus.UNAVAILABLE or coefficients is None:
        raise ProviderUnavailableError("physics_provider_unavailable")
    if status is not ProviderStatus.VALIDATED_COMPLEX:
        raise ValueError("provider_status_not_full_validated_complex")

    values = np.asarray(coefficients)
    if values.shape != expected_shape:
        raise ValueError("complex_state_shape_mismatch")
    if not np.iscomplexobj(values):
        raise TypeError("complex_state_must_have_complex_dtype")
    if not (np.isfinite(values.real).all() and np.isfinite(values.imag).all()):
        raise ValueError("complex_state_nonfinite")

    if propagating_mask is None:
        raise ValueError("propagating_mask_missing")
    mask = np.asarray(propagating_mask)
    if mask.dtype != np.bool_:
        raise TypeError("propagating_mask_must_be_boolean")
    if mask.shape != expected_shape:
        raise ValueError("propagating_mask_shape_mismatch")
    if not bool(mask.all()):
        raise ValueError("full_h1_state_requires_all_frozen_propagating_channels")
    return values.astype(np.complex128, copy=False)


def validate_p_scale(values: np.ndarray, expected_shape: tuple[int, ...] = (21,)) -> np.ndarray:
    """Validate the separate positive physical P_scale vector."""
    scale = np.asarray(values)
    if np.iscomplexobj(scale):
        raise TypeError("p_scale_must_be_real")
    if scale.shape != expected_shape:
        raise ValueError("p_scale_shape_mismatch")
    if not np.isfinite(scale).all() or not (scale > 0.0).all():
        raise ValueError("p_scale_must_be_finite_positive")
    return scale.astype(np.float64, copy=False)


def validate_mode_axis(modes: Sequence[ModeKey]) -> tuple[ModeKey, ...]:
    """Validate an explicit ordered mode axis without assuming a fixed S-matrix size."""
    axis = tuple(modes)
    if not axis:
        raise ValueError("mode_axis_empty")
    if any(not isinstance(mode, ModeKey) for mode in axis):
        raise TypeError("mode_axis_entry_type")
    for mode in axis:
        if not mode.port_id.strip():
            raise ValueError("mode_port_id_empty")
        if (
            isinstance(mode.order_m, (bool, np.bool_))
            or not isinstance(mode.order_m, (int, np.integer))
            or isinstance(mode.order_n, (bool, np.bool_))
            or not isinstance(mode.order_n, (int, np.integer))
        ):
            raise ValueError("mode_order_integer")
        if mode.polarization not in ("TE", "TM"):
            raise ValueError("mode_polarization")
        if mode.propagation_direction not in ("+z", "-z"):
            raise ValueError("mode_propagation_direction")
        if mode.mode_kind not in ("propagating", "evanescent"):
            raise ValueError("mode_propagation_kind")
    identity = tuple(
        (m.port_id, m.order_m, m.order_n, m.polarization, m.propagation_direction, m.mode_kind) for m in axis
    )
    if len(set(identity)) != len(identity):
        raise ValueError("mode_axis_duplicate")
    return axis


def validate_scattering_matrix(
    matrix: np.ndarray,
    input_modes: Sequence[ModeKey],
    output_modes: Sequence[ModeKey],
) -> np.ndarray:
    """Check complex dtype and explicit output-by-input mode-axis dimensions."""
    ins = validate_mode_axis(input_modes)
    outs = validate_mode_axis(output_modes)
    value = np.asarray(matrix)
    if not np.iscomplexobj(value):
        raise TypeError("scattering_matrix_must_have_complex_dtype")
    if value.ndim < 2 or value.shape[-2:] != (len(outs), len(ins)):
        raise ValueError("scattering_matrix_axis_shape_mismatch")
    if not (np.isfinite(value.real).all() and np.isfinite(value.imag).all()):
        raise ValueError("scattering_matrix_nonfinite")
    return value.astype(np.complex128, copy=False)


def _complex_matrix(name: str, value: np.ndarray) -> np.ndarray:
    matrix = np.asarray(value)
    if not np.iscomplexobj(matrix):
        raise TypeError(name + "_must_have_complex_dtype")
    if matrix.ndim < 2 or matrix.shape[-2] == 0 or matrix.shape[-1] == 0:
        raise ValueError(name + "_must_be_nonempty_matrix")
    if not (np.isfinite(matrix.real).all() and np.isfinite(matrix.imag).all()):
        raise ValueError(name + "_nonfinite")
    return matrix


def cascade_transmission_synthetic(
    t_n: np.ndarray,
    propagation: np.ndarray,
    r_m: np.ndarray,
    r_n: np.ndarray,
    t_m: np.ndarray,
    condition_limit: float = 1.0e12,
) -> CascadeResult:
    """Evaluate the provisional formula with a linear solve on synthetic matrices.

    Implements T_N P solve(I - R_M P R_N P, T_M). This verifies array and
    numerical handling only; port direction, phase, and component conventions
    remain subject to the Physics Codex contract.
    """
    tn = _complex_matrix("t_n", t_n)
    prop = _complex_matrix("propagation", propagation)
    rm = _complex_matrix("r_m", r_m)
    rn = _complex_matrix("r_n", r_n)
    tm = _complex_matrix("t_m", t_m)

    n = prop.shape[-1]
    if prop.shape[-2] != n:
        raise ValueError("propagation_must_be_square")
    for name, matrix in (("r_m", rm), ("r_n", rn)):
        if matrix.shape[-2:] != (n, n):
            raise ValueError(name + "_shape_mismatch")
    if tm.shape[-2] != n:
        raise ValueError("t_m_internal_axis_mismatch")
    if tn.shape[-1] != n:
        raise ValueError("t_n_internal_axis_mismatch")

    try:
        batch_shape = np.broadcast_shapes(
            tn.shape[:-2], prop.shape[:-2], rm.shape[:-2], rn.shape[:-2], tm.shape[:-2]
        )
    except ValueError as exc:
        raise ValueError("cascade_batch_shape_mismatch") from exc

    dtype = np.result_type(tn.dtype, prop.dtype, rm.dtype, rn.dtype, tm.dtype)
    tn, prop, rm, rn, tm = (
        np.broadcast_to(x.astype(dtype, copy=False), batch_shape + x.shape[-2:])
        for x in (tn, prop, rm, rn, tm)
    )
    identity = np.eye(n, dtype=dtype)
    feedback_system = identity - rm @ prop @ rn @ prop

    try:
        condition = np.asarray(np.linalg.cond(feedback_system), dtype=float)
    except np.linalg.LinAlgError as exc:
        raise IllConditionedCascadeError("feedback_condition_estimation_failed") from exc
    if (
        not np.isfinite(condition).all()
        or not np.isfinite(condition_limit)
        or condition_limit <= 1.0
        or np.any(condition > condition_limit)
    ):
        raise IllConditionedCascadeError("feedback_system_condition_limit")

    try:
        solved = np.linalg.solve(feedback_system, tm)
    except np.linalg.LinAlgError as exc:
        raise IllConditionedCascadeError("feedback_system_singular") from exc
    result = tn @ prop @ solved
    if not (np.isfinite(result.real).all() and np.isfinite(result.imag).all()):
        raise ValueError("cascade_result_nonfinite")
    return CascadeResult(coefficients=result, condition_number=condition)
