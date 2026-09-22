# PW_COMPLEX_FLOQUET_STATE_COMPARATOR_V1

Frozen zero-solver authority for the plane-wave periodic complex state. The
machine-readable contract is next to this file. The implementation is
`scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py`.

## Mathematical definition

For each wavelength, plane, and order `(m,n)`, the raw complex fields are
projected with an actual-coordinate trapezoidal NUDFT. The projected six-vector
is fitted to the local-medium Maxwell basis

`[E_TE+, E_TM+, E_TE-, E_TM- ; H_TE+, H_TM+, H_TE-, H_TM-]`.

The basis uses `kx=2*pi*m/Lx`, `ky=2*pi*n/Ly`, passive complex `kz`,
deterministic TE/TM vectors, and `H=(n/eta0) k_hat x E`. Each direction is
de-embedded from the sampled plane to the frozen reference plane with the V2
complex-kz convention. The coefficient tensor is

`C_PW[plane, wavelength, order, direction, polarization]`.

The incident `(0,0), +z, TM` coefficient at `IN_REF` supplies unit-power
normalization and one global phase gauge per wavelength. The same gauge is
used at all planes; no per-order or candidate/reference phase fitting is
allowed.

The comparator reports

`E_C = ||C_candidate - C_reference||_2 / ||C_reference||_2`

for every wavelength and requested plane, plus amplitude RMS, weighted phase
RMS, worst channel, aggregate maximum, and aggregate median. A zero reference
norm is reported rather than silently divided away.

## Frozen state schema

The primary state is three planes (`IN`, `PRENP`, `POSTNP`), 21 wavelengths
(440¨C460 nm, 1 nm spacing), 81 deterministic orders (`m,n=-4..+4`), two
directions, and TE/TM. Stored complex coefficients are paired float64 real and
imaginary arrays. The current shape is `[3,21,81,2,2]`.

The state also stores order metadata, local-medium `kz`, propagating mask,
basis condition, reference/sample plane metadata, normalization, and gauge.
Evanescent coefficients remain complex state; they are never converted into
propagating power. `R/T/order power` is auxiliary and cannot replace `C_PW`.

## Reuse and non-reuse

The M2Q module contributes axis conventions and synthetic projection ideas but
is Air-only and uses a finite-source/zero-sentinel policy, so it is not the
canonical comparator. The old PW launcher lifecycle, load-only checks, and
R/T/order reports remain useful, but its Ex/Hy scalar mode amplitude is not the
primary state. R3/R4 reports are historical diagnostics and do not define the
coherent state.

All future PW truth extraction and saved-state comparison must call the new
module. The launcher postprocess path now writes a compressed state NPZ and
SHA-bearing metadata beside the existing raw/projection/order outputs.

## Validation boundary

`run_pw_complex_floquet_state_zero_solver_tests.py` covers:

A same field with different spatial sampling; B one known mode; C coherent
multimode superposition; D global representation phase; E relative phase
perturbation; F positive-x order indexing; G reference-plane de-embedding;
H local-medium basis; I wavelength ordering; J rejection of power-only phase
collapse.

The corrected FAST comparison is offline/load-only. It can clarify the complex
state metric, but it cannot overturn the already frozen FAST rejection based on
R and diffraction/order trajectory gates. No MEDIUM solver entry is implied by
this authority.
