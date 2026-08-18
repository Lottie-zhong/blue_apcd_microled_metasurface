# Paper A LP physics-guided second rescue

Verdict: **PAPER_A_LP_SECOND_RESCUE_NO_PHYSICALLY_BETTER_SEED**

## Evidence boundary

The analysis uses 52 current-Native-compatible historical full-Jones geometries and 468 rows on 450-454 nm at 0.5 nm spacing. The five already FDTD-failed structures are excluded from any new shortlist and retained only as negative controls. No FDTD, RCWA, ML, or geometry generation was run.

## Answers

1. The prior ranking was primarily throughput/purity/anchor-oriented and did not explicitly rank distance from the target-channel flip boundary. This second rescue adds M_x margin, derivatives, orientation, and singular-vector stability.
2. Failed-control envelope: max min(M_x)=0.766657, min max|dM/dlambda|=0.162643/nm, min orientation ripple=0.242011 deg, min singular-vector drift=0.000009. Strict envelope dominance found: 0 candidate(s).
3. Future shortlist: none.
4. The selection logic requires positive historical M_x margin, low spectral slope/curvature, low psi drift, and stable dominant output singular vector; no phase/K6 metric is used.
5. Future FDTD budget: 0.

## Failure boundary

Historical evidence cannot prove 438-458 nm future broadband truth. Any future claim still requires Native-M1 430-470 nm source/monitor coverage, 435-465 nm extraction, MDC ZL-1 alternative weighting, coherency-first DoLP, and no main-spectrum channel flip.
