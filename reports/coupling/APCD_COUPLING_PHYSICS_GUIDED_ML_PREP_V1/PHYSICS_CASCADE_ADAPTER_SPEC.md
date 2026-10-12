# Physics cascade adapter specification

## Status

The accompanying adapter implements a synthetic array and numerical exercise only. The composition formula below remains provisional until the Physics Codex freezes port direction, phase, normalization, and internal-mode conventions. No physical S-matrix was loaded by the adapter.

## Provisional transmission relation

For components M and N separated by a propagation operator P, the candidate relation is:

T_total = T_N P solve(I - R_M P R_N P, T_M)

Equivalently, the right-side feedback solve represents repeated internal round trips. The implementation uses a linear solve rather than explicitly forming an inverse. The multiplication order and whether a transpose or adjoint is required depend on the provider's declared port convention and are not resolved by this synthetic test.

## Array contract

- Each component matrix is complex, finite, non-empty, and has trailing output-by-input axes.
- P is square over the internal modal basis.
- R_M and R_N are square over that same internal basis.
- T_M must accept the internal input axis; T_N must accept the internal output axis.
- Leading batch and wavelength axes may broadcast under NumPy broadcasting rules.
- The output is the composed transmission coefficient matrix; the condition number is returned for every broadcast batch element.
- The default numerical condition limit in the prototype is 1e12. This is an implementation guard, not an accepted physical tolerance.

The function is cascade_transmission_synthetic in physics_provider_adapter.py. It checks complex dtype, finite values, matrix dimensions and broadcast compatibility. It rejects non-finite condition estimates, a configured limit at or below 1, a condition number above the configured limit, and a singular solve.

## What the synthetic test establishes

The offline tests verify a known scalar-multiple-of-identity result, batch/wavelength broadcasting, and rejection of an ill-conditioned feedback system. These tests establish code-path and numerical behavior for synthetic matrices only.

## Physical requirements still open

Before using this as a physical adapter, the provider contract must specify:

1. Port orientation and the direction represented by every T and R.
2. Modal normalization, reference planes, phase gauge, and whether modes are power-normalized.
3. The same ordered internal modal basis on every connected interface.
4. Treatment of evanescent modes and truncation convergence.
5. Whether P includes propagation phase and attenuation, including the coordinate sign.
6. Whether reciprocity or symmetry applies and whether it is safe to reduce stored terms.
7. Composition tests against an independent trusted calculation and energy accounting.

Until those are frozen, do not use this function for predictions, training labels, solver admission, or claims about APCD physics.
