# APCD LP prospective actual-node bridge-gap plan v1

## Status
`PROSPECTIVE_ACTUAL_NODE_BRIDGE_PLAN_READY`; `NOT_SOLVER_AUTHORIZED`. This is a prospective diagnostic plan only, not D9 and not physics.

## Environment and evidence boundary
- formal worktree branch: `work/lp-stage11-4`; task baseline HEAD: `cafeb6bd6469f14c45aa810bd654b599bfebb8bc`.
- solver/lumapi/FDTD calls: `0`; no bridge-gap execution package or physics staging exists.
- protected reports unchanged: `True`; historical gate remains `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.
- no D9 candidate/geometry/package, spectrum, tolerance, K6/K7, canonical merge or training was created.

## Actual formal graph
- node policy: complete accepted/recovered formal weighted-G0 nodes only, fixed J1_side=110 nm and J2_length=106 nm with derivable `[uW,uD,uPsi]`; model-only, incomplete, virtual, prospective-unsimulated and inactive-variable nodes excluded.
- actual nodes: `34`; edges: `84` (all L1=1 plus pre-registered deterministic nearest-neighbor edges; no temporary bridge edge).
- included completion: six same-route D8 formal nodes including the complete historical phase-floor node `D8_TRV_PLAN_28f33b5793175bc4` (80.9856886303 deg), plus four completed curvature mirror formal nodes. Two D8 rows with J2_length=107 nm were excluded as inactive-variable non-comparable.
- threshold components: 1.00 -> 7 (sizes [18, 9, 3, 1, 1, 1, 1]), 0.75 -> 9 (sizes [18, 6, 3, 2, 1, 1, 1, 1, 1]), 0.50 -> 15 (sizes [9, 3, 3, 3, 3, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1]).
- phase-anchor component IDs: 0/0/0; projector-anchor IDs: 1/1/3.
- nearest 1.00x and 0.75x frontier pair: `PDCB_BRIDGE_13` ??`PDCB_BRIDGE_18`, L1=1. At 0.50x nearest pair is `D8_TRV_PLAN_d6f4911593b64495` ??`POSTD8_BOUNDED_PROJECTOR_03`, L1=3, Euclidean=2.236068. Graph remains disconnected; min vertex/edge cut is 0/0 because the formal graph is already disconnected.

## Bottleneck and barrier
- 1.00x frontier metrics: Jones Frobenius 0.028745863617; phase 0.331877339353 deg; Tyy 0.011527881364; leakage 0.011523081767; sigma-ratio jump 0.020442397528; endpoint projector margin 0.035539955755; manufacturing margin 33.250035 nm.
- barrier diagnosis: `MIXED_JONES_PROJECTOR_BRIDGE_BARRIER`. Geometry is legal and endpoint margin is positive, while frozen continuity/projector metric checks fail at the frontier; proposed nodes remain diagnostic predictions only.

## Frozen candidates
Exactly eight unique planned-only nodes remain frozen, with roles 2 phase exits / 2 projector exits / 2 cut splitters / 1 alternative / 1 active-basis discriminator. All geometry, manufacturing, exact/canonical/symmetry uniqueness gates pass.

| ID | coordinate | role |
|---|---|---|
| PDBG_PHASE_EXIT_01 | [-1, 2, -2] | BRIDGE_GAP_PHASE_EXIT_01 |
| PDBG_PHASE_EXIT_02 | [-1, 3, -1] | BRIDGE_GAP_PHASE_EXIT_02 |
| PDBG_PROJECTOR_EXIT_03 | [3, 0, 1] | BRIDGE_GAP_PROJECTOR_EXIT_03 |
| PDBG_PROJECTOR_EXIT_04 | [3, 0, 2] | BRIDGE_GAP_PROJECTOR_EXIT_04 |
| PDBG_CUT_SPLITTER_05 | [1, 0, 2] | BRIDGE_GAP_CUT_SPLITTER_05 |
| PDBG_CUT_SPLITTER_06 | [1, 2, 2] | BRIDGE_GAP_CUT_SPLITTER_06 |
| PDBG_ALT_PATH_07 | [2, 2, -1] | BRIDGE_GAP_ALTERNATIVE_PATH_07 |
| PDBG_BASIS_TEST_08 | [3, 2, 0] | BRIDGE_GAP_ACTIVE_BASIS_DISCRIMINATOR_08 |

## Batch freeze
- Batch 1: `PDBG_PHASE_EXIT_01`, `PDBG_PROJECTOR_EXIT_03`, `PDBG_CUT_SPLITTER_05`, `PDBG_ALT_PATH_07` = exactly 4 geometries / 8 x-y subruns.
- Batch 2: `PDBG_PHASE_EXIT_02`, `PDBG_PROJECTOR_EXIT_04`, `PDBG_CUT_SPLITTER_06`, `PDBG_BASIS_TEST_08` = maximum 4 geometries / 8 x-y subruns, only after the Batch 1 physical gate.
- Future ceiling: 8 geometries / 16 x-y subruns / 450 nm only; status remains `NOT_SOLVER_AUTHORIZED`.

## Caveats
`PROSPECTIVE_DIAGNOSTIC_PLAN_ONLY`, `NOT_D9`, `NO_SOLVER_AUTHORIZATION`, `NO_PHYSICS_LABEL`, `HISTORICAL_FULL_JONES_GATE_REMAINS_BLOCKED`, `CURRENT_FORMAL_GRAPH_NOT_CONNECTED`, `CANDIDATE_GRAPH_EDGES_ARE_PREDICTED_NOT_PHYSICS`.

## Outputs
The checksum manifest binds the graph, cut-set, barrier, candidate pool/gate, plan, contracts, report and test. No solver was run.
