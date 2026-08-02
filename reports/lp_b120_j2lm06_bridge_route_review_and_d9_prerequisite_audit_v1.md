# LP phase-projector bridge route review and D9 prerequisite audit v1

Status: PASS (offline-only analysis; no solver calls).

## Corrected authoritative graph state

The earlier 11/13/19-component and singleton conclusion is superseded. The defect was a stale phase=0 edge field after Batch1 accepted phase values were refreshed; only graph predicates changed. The authoritative graph has 7/9/15 components at thresholds 1.00/0.75/0.50, all four Batch1 nodes have local edges, and realized cross-component gain is 0. The phase and projector anchors remain disconnected. No current decision artifact marks the four nodes as true singletons.

## D9 bridge-prerequisite finding

The D9 contract explicitly freezes a piecewise dual-anchor method, a conditional Batch2 gate, route-decision-only status, and zero solver authorization. It does not explicitly define global anchor-to-anchor actual-node connectivity as a hard prerequisite. Therefore connectivity is **AMBIGUOUS_IN_CONTRACT**: it is a conservative diagnostic under the current evidence review, not a silently relaxable requirement. Phase-local continuation with an independent projector guard would require an explicit contract clause saying global connectivity is not claimed and is not required.

## Physical meaning

At threshold 1.00, the phase component has 20 nodes (phase 80.986-83.175?, Tyy 0.0933-0.1168) and the projector-anchor component has 10 nodes (phase 82.469-84.595?, Tyy 0.0741-0.0872). The nearest cross-component edges are one lattice step but fail mixed Jones/phase/Tyy/leakage/sigma predicates; this is consistent with an insufficiently sampled or curved manifold and a projector-response barrier, not proof of a globally separate manifold.

## Control-basis finding

D5 phase derivatives are approximately J1_side 0.07300 rad/nm, J2_length 0.02329 rad/nm, and J2_width 0.00881 rad/nm. D6 reports improved five-variable controllability and a large Psi orthogonal fraction, while D8 W/D/Psi models are local and not valid for further extrapolation. Fixing J2_length therefore removed a meaningful phase-control direction. R2 is the minimum new basis test; R3 remains an identifiability audit, not an execution authorization.

## Overall recommendation

**EXPAND_CONTROL_BASIS_BEFORE_MORE_BRIDGE_SOLVER**. A new 4-6 geometry, 8-12 x/y subrun, 450-nm prospective J2_length-inclusive local map is the minimum next experiment estimate. It must use a new contract, complete weighted-G0 Jones, independent projector guard, and no cross-slice graph edges. No candidates are frozen here.

Historical hard gate remains: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.
