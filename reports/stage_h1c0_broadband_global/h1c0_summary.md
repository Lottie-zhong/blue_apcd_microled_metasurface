# H1C-0 Broadband Global Phase-Island Search Readiness

## Status

- Solver contract: `ZERO NEW FDTD / ZERO NEW RCWA / ZERO NEW PHYSICS SOLVER`.
- Frozen LP broadband grid: `450.0..454.0 nm`, step `0.5 nm`, count `9`.
- 450 nm is a reference label only, not broadband acceptance.

## Salvage closure

- Audited exact H550 geometries: `20` (H1A 6, H1B1 5, H1B2 5, H1B3 4).
- Full-Jones broadband recoverable: `0`.
- All 20 existing cases expose only one 450 nm row and pre-FSP artifacts; no postprocess-only broadband extraction was performed.
- Existing 450 nm projector semantics remain empirical H1A best-50%-within-slice, inherited threshold `0.1864961370084426`; broadband aggregate semantics are not frozen.

## Candidate bank and search

- Candidate bank retains all 20 exact hashes before any extremum filter; C remains a `GLOBAL_SIX_BIN_CANDIDATE_SEED`, not a broadband promotion.
- Proposed domain is a legality-filtered global 5D envelope, not a solver authorization.
- Proposed rectangle volume is `7.261x` the observed local H550 range envelope.
- Proposed scan: 48 coarse global points plus 24 adaptive phase-gap points; deterministic Sobol/LHS-equivalent coverage, not edge continuation.
- Recommended strategy: x reconnaissance followed by mandatory y completion; x-only never proves projector compatibility.
- Six-bin objective must fit free `phi0(lambda)` and minimize circular relative-spacing error across all nine wavelengths, jointly with projector and throughput robustness.

## Hard gates

- `solver_entered` delta: `0`.
- `solver_replay`: `false` for every audited case.
- Constituent reconnaissance remains diagnostic-only; no constituent FDTD was run.

## Evidence

- `h1c0_broadband_contract.json`
- `h1c0_h550_existing_salvage_audit.json`
- `h1c0_global_candidate_bank.json`
- `h1c0_global_domain_proposal.json`
- `h1c0_solver_strategy_comparison.json`
- `h1c0_proposed_global_scan.json`
