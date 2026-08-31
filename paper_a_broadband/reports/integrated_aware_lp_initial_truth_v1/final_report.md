# Integrated-aware LP initial truth

Status: **PASS**

This is an integrated-aware LP truth acquisition for IAR3 and IAR4. It does not select a champion or use a composite score.

## IAR3 pair
- 450 nm pair DoLP: `0.03066649`; broadband mean/worst: `0.04496786` / `0.00098714`.
- 450 nm useful axis-free LP: `1.88141877e+00`; upward source-normalized power: `7.35412848e-03`.
- Source C / angular C: `0.07344704` / `0.08075726`; mechanism: `BOTH_SOURCE_AND_ANGULAR_CANCELLATION`.

## IAR4 pair
- 450 nm pair DoLP: `0.05357584`; broadband mean/worst: `0.04414290` / `0.00336338`.
- 450 nm useful axis-free LP: `1.93828797e+00`; upward source-normalized power: `7.39307247e-03`.
- Source C / angular C: `0.12712781` / `0.10519643`; mechanism: `BOTH_SOURCE_AND_ANGULAR_CANCELLATION`.

## Baseline comparison
The fixed IC1+IC2 I03 baseline is used only for delta comparison; no baseline solver was rerun.
- Baseline 450 nm pair DoLP / C_source / C_angular: `0.037876844117608964` / `0.08854257161559786` / `0.08612761641165362`.

## Interpretation
- x/y sources were combined incoherently at Stokes/coherency level; electric fields were not added and DoLP/psi were not averaged.
- Angular metrics are wavelength-resolved over the full 400–500 nm descriptive grid; raw psi remains diagnostic and is ill-conditioned at low DoLP.
- `W_emit` remains unresolved; no emitter-weighted or absolute LEE claim is made.
- Mechanism classes are descriptive only. Final promotion remains a Chart scientific decision.

## Validity and accounting
- Same finite 3 um mesa, 5x5 array, MDC, source z, z datum, PML/domain/monitor and Native-M1 contract were used.
- 4 new FDTD entries: IAR3_x, IAR3_y, IAR4_x, IAR4_y; 12 MPI x 1 thread/job; no replay; RCWA=0; ML=0.

## Controller provenance history
- `terminal_failure.json` records an early pre-entry setup-only failure caused by a UTF-8 BOM parsing issue while reading `setup_readback.json`; its solver accounting is `entered=0`.
- This historical setup/format failure was superseded by `terminal_success.json`, is retained as provenance, and is not the final physics-truth state.
