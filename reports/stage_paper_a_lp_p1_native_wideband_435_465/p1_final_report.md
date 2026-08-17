# Paper A LP-P1 Zero-Solver Final Closeout

## Status

PAPER_A_GATE_A_FAIL_LP_BROADBAND_INSUFFICIENT

This closeout uses current Native-M1 physics only. No additional solver was run.

## Frozen contract

- Intrinsic LP broadband evaluation window: **435-465 nm**
- Formal extraction: **1 nm, 31 points**
- Emitter/design anchor: **450 nm**
- Source/monitor span: **430-470 nm**
- Real solver evidence: **6/6 x/y cases completed**
- Phase and K6 criteria: **not used in qualification**
- Ranking principle: broadband worst-case viability and stability first
- New solver entries in closeout: **0**

## Gate A comparison

| Candidate | Useful LP mean | Useful LP worst | Useful ripple | Useful CV | DoLP mean | DoLP worst | DoLP ripple | x-fidelity mean | x-fidelity worst | Leakage mean | Leakage worst | Gate A |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H1C1B_V2_009 | 0.371015 | 0.022843 | 0.489351 | 0.352217 | 0.455323 | 0.050969 | 0.887155 | 0.689202 | 0.238698 | 0.183422 | 0.411183 | FAIL |
| H1C1B_V2_015 | 0.443151 | 0.022649 | 0.486164 | 0.223151 | 0.302422 | 0.010357 | 0.989519 | 0.639723 | 0.454777 | 0.268082 | 0.478208 | FAIL |
| H1C1B_V2_010 | 0.386308 | 0.027842 | 0.496383 | 0.336958 | 0.457830 | 0.034411 | 0.931767 | 0.686562 | 0.098545 | 0.195757 | 0.432349 | FAIL |

## 450 nm anchor

| Candidate | Useful LP | DoLP | x-fidelity | Leakage | Rank contrast | Rank-one error |
|---|---:|---:|---:|---:|---:|---:|
| H1C1B_V2_009 | 0.463917 | 0.572549 | 0.786177 | 0.126175 | 1.923909 | 0.519775 |
| H1C1B_V2_015 | 0.483174 | 0.790991 | 0.895481 | 0.056395 | 2.928088 | 0.341520 |
| H1C1B_V2_010 | 0.469208 | 0.839350 | 0.901438 | 0.051303 | 3.991213 | 0.250550 |

## Ranking decision

All three candidates fail the fixed Gate A thresholds, including the broadband worst-case requirements. Therefore no P1_CURRENT_NATIVE_PRIMARY or P1_CURRENT_NATIVE_RUNNER_UP is frozen. The closeout preserves candidate tradeoffs without introducing a composite score:

- 009: strongest worst-case DoLP, DoLP flatness, x-fidelity mean, and leakage profile.
- 015: strongest useful-power mean/flatness and x-fidelity worst, but weakest DoLP.
- 010: strongest 450 nm DoLP/x-fidelity and useful-power worst, but still fails broadband viability.

No automatic geometry search or new LP design space is authorized.

## Evidence and scope

- Full spectra: lp_435_465_full_spectra.csv (93 rows = 3 candidates x 31 points)
- Metrics: p1_broadband_metrics.csv
- Candidate comparison/ranking: p1_candidate_ranking.csv
- Final decision: p1_final_champion.json
- Original postprocess: p1_postprocess.json
- Solver accounting: solver_accounting.json
- Terminal evidence: monitor/terminal_success.json

No CP, RCWA, angular sweep, integrated solver, or additional LP physics was run in this closeout.
