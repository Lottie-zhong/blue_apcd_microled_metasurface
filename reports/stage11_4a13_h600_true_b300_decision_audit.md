# Stage11-4A13 H600 True-B300 Decision Audit

This is a decision audit only. No FDTD, coverage, H650, K=6, finite patch, dipole, DBR, RCLED, or H500 rescue was run.

## Decision

Stop H600 true-B300 blind search for now; do not run H600 coverage yet.

Keep the A8 B60 donor and A5 B240 loose case as useful partial LP-H600 library evidence. Do not run H600 coverage because true B300 remains unresolved.

## Evidence Summary

| evidence | role | candidate | ratio | Tx | matrix | phase error | status | use |
|---|---|---|---:|---:|---:|---:|---|---|
| A8_B60_DONOR | B60 donor | H600B300PULL_002_FROM_H500DIMER12D_004_B300_x_pair_swap_G80_O-40 | 11.278722 | 0.752180 | 0.297811 | 24.596581 | strict | keep_as_B60_donor |
| A5_B240_LOOSE | B240 partial library evidence | H600B240MECH_009_diag_pair_J1J2_G40 | 5.157216 | 0.835876 | 0.481903 | 25.892659 | loose | keep_as_B240_loose_evidence |
| A10_G1_B300_FAIL | true B300 G1 failed | A10_G1_best | 4.458043 | n/a | 0.475631 | 89.940554 | fail | do_not_continue_this_family |
| A11_G2_B300_FAIL | true B300 G2 failed | A11_G2_best | 1.010146 | n/a | 0.994965 | 26.072770 | fail | do_not_continue_this_family |
| A12_G3_B300_FAIL | true B300 G3 failed | H600TRUEB300G3_002_diag_pair_J1J2_G100 | 2.357350 | 0.947046 | 0.651573 | 88.009657 | fail | stop_H600_true_B300_blind_search |

## Route Recommendation

Stage11-4A13 recommends route A first: H600 B300 mechanism redesign planning only. Route B H650 B300 escape hatch is next if A cannot produce a bounded, physically distinct search plan.

Alternatives kept open: route B H650 B300 escape hatch, route C partial phase-library/mechanism positioning, or route D return to CP/RCLED mainline if paper timeline dominates.

## Boundary

No K=6 work is justified until a fixed-height LP library has a credible true-B300 route.
