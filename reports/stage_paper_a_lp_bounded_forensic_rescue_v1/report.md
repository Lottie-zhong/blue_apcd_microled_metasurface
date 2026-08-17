# Paper A LP bounded forensic rescue v1

## Status

`PAPER_A_LP_FORENSIC_RESCUE_BATCH1_READY`

This is a zero-solver historical evidence decision. It does not promote a current LP champion and does not reopen the frozen Paper A scope.

## Evidence boundary

- Authoritative cohort: 52 Native-M1 current/native-compatible geometries and 468 complete full-Jones rows.
- Historical coverage: 450.0–454.0 nm at 0.5 nm (9 points), from real FDTD H1C1A/B/C evidence.
- Current failed controls retained but excluded from the rescue shortlist: 009, 015, 010.
- Phase, K6, six-phase reachability, beam steering, grouped-D/J1 history, and ML predictions were not used for qualification or ranking.
- The existing 435–465 nm intrinsic failure and MDC source-weighted Gate A-prime failure remain frozen.

## Candidate counts

| quantity | count |
|---|---:|
| current/native-compatible geometries | 52 |
| complete full-Jones rows | 468 |
| non-control candidates | 49 |
| non-control historical physical-screen passes | 7 |
| physical Pareto front | 4 |
| primary rescue batch | 2 |
| reserve rescue batch | 2 |

The bounded physical screen is mean useful power >= 0.40, mean DoLP >= 0.80, and mean x-fidelity >= 0.90 on the historical 9-point grid. It is not Gate A-prime and is not source-weighted.

## Future-only shortlist

| batch | candidate | historical mean useful | worst useful | mean DoLP | worst DoLP | mean x-fidelity | worst x-fidelity | rationale |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PRIMARY | GLOBAL_018 | 0.4908 | 0.4813 | 0.8273 | 0.6184 | 0.9130 | 0.8079 | throughput-stability/rank basin |
| PRIMARY | H1C1B_V2_012 | 0.4222 | 0.1387 | 0.8990 | 0.7112 | 0.9494 | 0.8556 | purity/fidelity basin; throughput risk |
| RESERVE | GLOBAL_006 | 0.4495 | 0.2760 | 0.8377 | 0.7244 | 0.9184 | 0.8615 | 009-adjacent non-identical balance |
| RESERVE | H1C1C_R06 | 0.4912 | 0.4827 | 0.8267 | 0.6066 | 0.9128 | 0.8020 | H1C1C throughput-stability branch |

## Interpretation and stop-loss

The two primary candidates were selected because they represent distinct physical tradeoffs, not because of phase coverage or historical labels. A future Batch-1 would be at most 4 FDTD jobs (2 geometries × x/y), but it is not authorized by this zero-solver stage. No source-weighted MDC-main-region sign-flip claim is available for these historical candidates because their evidence does not cover approximately 438–458 nm.

The current status remains `FROZEN_NOT_PROMOTED`. If a future bounded confirmation does not produce two viable candidates, retain the frozen route and use `PAPER_A_LP_FORENSIC_RESCUE_NO_WORTHWHILE_CANDIDATES`.
