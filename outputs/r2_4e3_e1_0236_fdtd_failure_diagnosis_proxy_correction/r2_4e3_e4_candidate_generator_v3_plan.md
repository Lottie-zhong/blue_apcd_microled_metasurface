# R2-4E4 Candidate Generator V3 Plan

Recommended task name: **R2-4E4_Python_only_candidate_generator_v3_faroffaxis_guard**.

E4 must remain Python-only: no Lumerical, no lumapi, no FDTD, no FSP generation.

Mandatory E4 changes:
- no E1_0236 retry
- shortlist max 2 candidates
- candidate must pass both 30-40 deg and 45-55 deg off-axis penalties
- include 40-60 deg broad lobe penalty
- include normal-cone energy lower-bound proxy
- include broad-FWHM/multilobe risk guard
- include E1_0236-like risk flag and proxy-FDTD mismatch guard
- candidate must be marked requires_tri_point_FDTD before validation

FDTD is not allowed until after E4 review. If E4 produces a candidate, the first validation remains tri-point x-dipole 453 nm only.
