# J2_length-inclusive dual-anchor prospective local-map plan v1

Status: PLANNED_NOT_RUN; offline-only; solver calls=0.

## Anchor provenance

Phase anchor POSTD8_BOUNDED_PHASE_01 and projector anchor POSTD8_BOUNDED_DIAG_06 were read from formal candidate records. Both are H500, period 432 nm, Native-M1, complete weighted-G0 Jones records with independent geometry hashes. Local coordinate origins remain independent.

## J2_length evidence

D5 gives a J2_length phase derivative of about 0.0232856 rad/nm from a 1-nm central difference at the older LP_H500_D2_B120_J2LM06 reference (J2_length 109 nm). Current formal D7/D8 comparable nodes in this fixed J1/H500 slice all have J2_length 106 nm; no current-anchor non-106 formal node was found. This is a planning prior, not a current-anchor derivative. D8 secant residual envelope is phase max 3.5419 degrees and Jones Frobenius max 0.06179; metric-specific uncertainty is not fabricated.

## Frozen 4D contract

u4=[delta_J2_length, delta_J2_width, delta_D, delta_Psi]; J1_side is fixed and each anchor retains its own absolute origin. qL=1 nm is the smallest demonstrated legal J2_length step. Existing W/D/Psi quantization rules are reused without sub-grid substitution. Absolute geometry and fixed contract fields govern hashes and alias decisions.

## Batch A

Exactly four planned nodes: each anchor at J2_length = anchor +/-1 nm, with W/D/Psi and all other geometry fixed to that anchor. All have unique exact/canonical/symmetry hashes, no existing hash collision, integer/half-grid, no overlap, primitive validity, and direct/periodic gaps above 60 nm. Physics fields remain ABSENT_NOT_SIMULATED.

## Batch B

At most two conditional slots, not frozen and not authorized. They may be selected only after Batch A outcome A or B demonstrates a formal W/D/Psi compensation direction. Redundant or unidentifiable outcomes leave Batch B unexecuted.

## Future contract and gates

Future ceiling is 4 geometries/8 x-y subruns at 450 nm for Batch A and conditional 2 geometries/4 subruns for Batch B. Each geometry requires x/checkpoint/reload/acceptance then y/checkpoint/reload/acceptance and complete Jones. No D9, old Batch2, graph/projector guard changes, training, spectrum, staging, runnable package, or solver execution is authorized in this task.

Historical hard gate remains HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE.
