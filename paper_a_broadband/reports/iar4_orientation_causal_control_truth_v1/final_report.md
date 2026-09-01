# IAR4-OC1 Orientation-Only Causal Control Truth

## Status

Two authorized current Native-M1 integrated FDTD cases were completed: IAR4-OC1 x/y. IAR4 is the pre-existing comparator; no IAR4 replay was performed.

## Frozen causal pair

Only `delta_theta` changes: IAR4 = 82.820909321 deg; IAR4-OC1 = 85.819861293 deg. L1/W1/L2/W2/D/H/Px/Py remain the exact contract values. Direct and periodic clearances are 62.390756888 nm and 74.390756888 nm.

## 450 nm anchor

Pair DoLP: IAR4 0.0535758376 -> OC1 0.0414350443 (delta -0.0121407933); C_source: 0.127127814 -> 0.0958328776; C_angular: 0.105196425 -> 0.100818153.
Source-normalized upward power: 0.00739307247 -> 0.00738383098; axis-free useful LP: 1.93828797 -> 1.91289391.

## Broadband contrast

The 400-500 nm, 101-point point-by-point comparison is in `iar4_vs_oc1_causal_contrast.csv`. Descriptive candidate interpretation: `ORIENTATION_PURITY_POWER_TRADEOFF`. This is not a new promotion threshold or composite score; final scientific authority remains with Chart.

Power assessment: `DESCRIPTIVE_POWER_DECREASE_REQUIRES_TRADEOFF_REVIEW`. Source and angular reinforcement are reported separately; W_emit and historical 28-nm Gaussian weighting were not used.

## Boundary

The result establishes only the strict IAR4↔IAR4-OC1 causal contrast. It does not alter the prior IAR4-like integrated-response interpretation, does not establish a Paper A promotion threshold, and does not authorize further geometry or solver work.

## Accounting

`authorized=2`, `entered=2`, `returned=2`, `accepted=2`, `replay=0`, `RCWA=0`, `ML=0`, `active FDTD=0`.

## Scoped causal-scope audit (zero-solver)
This zero-solver audit reads only the existing 101-point IAR4 and IAR4-OC1 truth.
The 445–455 nm scope is an unweighted diagnostic window, not production W_emit weighting.
W_emit and the historical 28-nm Gaussian remain unresolved and were not used.

Final scoped verdict: `ORIENTATION_CAUSAL_EFFECT_WAVELENGTH_DEPENDENT`.
The prior descriptive label `ORIENTATION_PURITY_POWER_TRADEOFF` is retained in provenance but downgraded to `FULL_BAND_DESCRIPTIVE_NONUNIFORMITY`; it is not a top-level causal verdict.
The preserved `terminal_failure.json` records an earlier analysis-only NameError; it is superseded by the later `terminal_success.json` and is not a physics failure or solver replay.

Delta convention: OC1 minus IAR4. Complete per-wavelength values and sign-flip intervals are in `causal_scope_spectral_deltas.csv` and `causal_scope_audit.json`.
No composite score, promotion threshold, solver, replay, RCWA, or ML was introduced.
