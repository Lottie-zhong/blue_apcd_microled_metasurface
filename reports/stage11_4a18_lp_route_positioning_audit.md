# Stage11-4A18 LP Route-Positioning Audit

This is a route-positioning audit only. No FDTD, A16 G2, coverage, H600/H650 rerun, K=6, or heavy output was run.

## Core Decision

Stop LP-Hnew six-bin fixed-height attempt for now. Do not run coverage or K=6 from current LP-Hnew data.

## Evidence Table

| evidence | role | h | ratio | Tx | matrix | phase error | nearest bins | status | use |
|---|---|---:|---:|---:|---:|---:|---|---|---|
| A8_B60_DONOR | partial LP evidence: B60 strict donor | 600 | 11.278722 | 0.752180 | 0.297811 | 24.596581 | 60 | strict | keep_as_partial_evidence |
| A5_B240_LOOSE | partial LP evidence: B240 loose mechanism | 600 | 5.157216 | 0.835876 | 0.481903 | 25.892659 | 240 | loose | keep_as_partial_evidence |
| A15_H600_B300_FAIL | H600 B300 failure evidence | 600 | 11.589234 | 0.979696 | 0.293775 | 105.037257 | 0;60 | fail_phase | stop_manual_H600_B300_rescue |
| A17_H650_B300_FAIL | H650 B300 failure evidence | 650 | 0.986137 | 0.928105 | 1.007004 | 158.473359 | 120;60 | fail_ratio_matrix_phase | stop_LP_Hnew_sixbin_attempt |

## Route Options

A. Pause LP-Hnew six-bin and return priority to CP/RCLED mainline.
B. Keep LP results as partial phase-library/mechanism evidence for thesis or paper background.
C. Revisit LP later only with a new mechanism or ML/global search, not manual local B300 rescue.
D. Do not enter K=6 from current LP-Hnew data.

## Recommended Next

Return priority to CP/RCLED mainline; keep LP results as partial phase-library/mechanism evidence. Revisit LP only with a new mechanism or ML/global search, not manual local B300 rescue.
