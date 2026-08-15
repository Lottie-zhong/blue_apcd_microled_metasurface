# H1F-0 LP local-dimer route closure

## Status

`PASS` — zero-solver offline closure.

## Scoped conclusion

`CURRENT_H550_LOCAL_DIMER_GRAMMAR_PHASE_LEVERAGE_INSUFFICIENT`

Scope: shared H_global=550 nm, tested rectangular two-pillar dimer lateral/J1/J2/D/Psi grammar, J2 orientation-displacement decoupling, 450.0–454.0 nm at 0.5 nm, nine wavelengths, formal 9/9 projector-compatible strict trajectories. This is not a claim about all heights, shapes, dimers, metamolecules, or full supercells.

## Quantitative closure

- Strict bank: 7 historical + 5 H1E3C children = **12**.
- Selected strict phase coverage: **32.207338°**; largest circular gap **327.792662°**.
- H1E3C six-bin best: worst error **164.772059°**, RMS **99.959384°**; phase ordering crosses within the band.
- Broadband selectivity is demonstrated by strict 9/9 projector-compatible trajectories; six-phase reachability is not.
- Strict-bank geometry evidence supports `GEOMETRIC_DIVERSITY_WITH_OPTICAL_PHASE_CLUSTERING`.
- `GLOBAL_H_REVISIT_VALUE = MEDIUM`; H550 has the best sampled projector-compatible span (**30.096722°** in H1B0), but sparse H sampling does not prove a new region.

## Route decision

`COUPLING_AWARE_FULL_K6_FIRST`

Direct K6 order-resolved optimization attacks the H1D-demonstrated coupling/order bottleneck while retaining the tested strict broadband dimer bank. The isolated six-bin library remains a strategy/initialization method, not a Maxwell requirement.

## Proposed-only next stage

`LP_K6_COUPLING_AWARE_LEVEL0_DESIGN` — no execution. Use K6-A/B/C constrained seeds, with at most 4 x-pol prescreens and y-pol completion for up to 2 survivors; final acceptance requires x+y. Proposed maximum is 6 FDTD cases, solver-entered now is 0.

## Governance

The versioned local-dimer evidence count is **578** (506 prior + 72 H1E3C); the canonical registry is preserved unchanged and `ml_admitted=false`. No ML training and no K6 labels were fabricated.

## Scheduler

Current live accounting: FDTD=1, RCWA=0, UNKNOWN=0; LP remains admissible because global FDTD occupancy is below 2 and LP active occupancy is 0.

See the companion JSON reports in this directory for source paths and deterministic fields.
