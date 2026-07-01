# Stage11-4A16 H650 B300 Escape-Hatch Plan

Planning only. No FDTD, coverage, H600 rerun, H700, K=6, dipole, DBR/RCLED, or H500 rescue was run.

## Context

H600 B300 is stopped for now: A10/A12/A15 selectivity candidates landed near 0/60, while A11 landed near 300 with collapsed projection/matrix behavior.
A15 best had ratio 11.589234, Tx 0.979696, matrix 0.293775, phase_error 105.037257, nearest 0/60.

## Decision

H650 B300 escape hatch is distinct from H600 failures because it changes fixed height instead of forcing H600 families that repeatedly landed near 0/60 or collapsed projection near 300.

## Planned Groups

| group | cases | purpose | distinctness |
|---|---:|---|---|
| S11_4A16_G1_H650_B300_DIRECT_ESCAPE | 12 | test whether H650 shifts selected-channel phase away from the H600 0/60 attractor while preserving LP projection | new fixed height; excludes H600 B60-donor forcing and does not reuse H600 true-B300 blind search groups |
| S11_4A16_G2_H650_B300_MINI_REPAIR | 6 | small repair set only if G1 has near-300 phase or near-miss projection evidence | H650 matrix/phase repair, not H600 rerun; stops if G1 shows the same 0/60 attractor |

Total future cases: 18. This does not exceed the A16 cap.

## Boundary

Do not run coverage, H600 B300 reruns, H700, or K=6 before evaluating H650 B300 G1.
