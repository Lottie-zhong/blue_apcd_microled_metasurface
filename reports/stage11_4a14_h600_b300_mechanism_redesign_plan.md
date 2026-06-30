# Stage11-4A14 H600 B300 Mechanism Redesign Plan

Planning only. No FDTD, coverage, H650, K=6, finite patch, dipole, DBR/RCLED, or H500 rescue was run.

## Why Previous B300 Searches Failed

- A10 G1: moderate selectivity, but selected phase landed near 0 rather than 300.
- A11 G2: selected phase landed near 300, but projection selectivity collapsed.
- A12 G3: no useful result; best case still failed ratio, matrix, and phase gates.
- A8 high-selectivity B300-labeled family is a B60 donor and is excluded from B300 forcing.

## Decision

A bounded distinct H600 B300 mechanism plan exists, but it is the last H600 true-B300 attempt before H650 escape-hatch planning.

## Planned Groups

| group | cases | purpose | distinctness |
|---|---:|---|---|
| S11_4A14_G1_B300_SELECTIVITY_WITH_300_PHASE_HYBRID | 12 | recover projection selectivity while keeping selected phase near 300 | combines A10 selectivity source and A11 phase source instead of rerunning either family |
| S11_4A14_G2_B300_MATRIX_REPAIR_NEAR_300 | 6 | keep near-300 phase while reducing blocked-y leakage | uses A11 only as a phase-local anchor and changes matrix-repair knobs |
| S11_4A14_G3_B300_NON_B60_ANCHOR_MICRO_ESCAPE | 6 | last bounded H600-only escape before H650 planning | excludes A8 B60 donor family and avoids A12 mini-escape geometries |

Total future cases: 24. This does not exceed the A14 cap.

## Boundary

Do not run H600 coverage, H650, or K=6 until true B300 has loose/strict evidence or H600 is formally stopped.
