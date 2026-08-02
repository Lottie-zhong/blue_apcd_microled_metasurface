# APCD LP prospective actual-node bridge-gap plan v1

## Status
`PROSPECTIVE_ACTUAL_NODE_BRIDGE_PLAN_READY`; `NOT_SOLVER_AUTHORIZED`. This is a prospective diagnostic plan only, not D9 and not physics.

## Environment
- host: `DESKTOP-NNE313K`; worktree: `D:\project\worktrees\blue_apcd_lp_stage11_4`
- branch: `work/lp-stage11-4`; HEAD: `cafeb6bd6469f14c45aa810bd654b599bfebb8bc`; upstream: `origin/work/lp-stage11-4`; ahead/behind: `['0', '0']`
- solver/lumapi/FDTD calls: `0`; active matching processes: `1`
- protected report hashes unchanged from recorded baseline: `True`

## Actual formal graph
- actual nodes: `24` (phase/projector anchors + bounded6 + 18 prospective cross-branch nodes); edges: `74` (L1=1 or preregistered deterministic nearest-neighbor only).
- threshold component counts: `1.00 -> 3`, `0.75 -> 5`, `0.50 -> 9`.
- phase anchor component IDs: `0/0/0`; projector anchor component IDs: `1/1/3`.
- nearest 1.00x phase/projector frontier pair: `[1, 1.0, 'PDCB_BRIDGE_13', 'PDCB_BRIDGE_18']`; at 0.75x the same pair remains nearest, while 0.50x uses `[3, 2.23606797749979, 'POSTD8_BOUNDED_DIAG_05', 'PDCB_BRIDGE_17']`. Formal graph remains disconnected; no virtual/interpolated node was added.
- minimum vertex/edge cut in the already-disconnected graph is `0/0`; bottleneck frontier failures and metrics are enumerated in the cut-set JSON.

## Barrier diagnosis
`MIXED_JONES_PROJECTOR_BRIDGE_BARRIER`. The endpoint geometry is legal and projector margins are evaluated, but frozen Jones/projector continuity guards fail across the nearest frontier gap. The proposed nodes are predictions only and will test whether missing actual sampling splits that gap.

## Frozen candidates
Exactly 8 unique planned-only nodes are frozen: `PDBG_PHASE_EXIT_01`, `PDBG_PHASE_EXIT_02`, `PDBG_PROJECTOR_EXIT_03`, `PDBG_PROJECTOR_EXIT_04`, `PDBG_CUT_SPLITTER_05`, `PDBG_CUT_SPLITTER_06`, `PDBG_ALT_PATH_07`, `PDBG_BASIS_TEST_08`. Role coverage is 2/2/2/1/1; all geometry/manufacturing/hash gates pass.

| ID | role | coordinate | adjacent actual frontier | predicted projector risk | information gain |
|---|---|---|---|---:|---:|
| PDBG_PHASE_EXIT_01 | BRIDGE_GAP_PHASE_EXIT_01 | [-1, 2, -2] | PDCB_PHASE_LOCAL_01|PDCB_PHASE_LOCAL_04 | 0.330135 | 0.295285 |
| PDBG_PHASE_EXIT_02 | BRIDGE_GAP_PHASE_EXIT_02 | [-1, 3, -1] | PDCB_PHASE_LOCAL_01|PDCB_PHASE_LOCAL_03 | 0.330135 | 0.305936 |
| PDBG_PROJECTOR_EXIT_03 | BRIDGE_GAP_PROJECTOR_EXIT_03 | [3, 0, 1] | PDCB_PROJECTOR_LOCAL_07|POSTD8_BOUNDED_PROJECTOR_03 | 0.291823 | 0.458904 |
| PDBG_PROJECTOR_EXIT_04 | BRIDGE_GAP_PROJECTOR_EXIT_04 | [3, 0, 2] | PDCB_PROJECTOR_LOCAL_12 | 0.278277 | 0.269452 |
| PDBG_CUT_SPLITTER_05 | BRIDGE_GAP_CUT_SPLITTER_05 | [1, 0, 2] | PDCB_BRIDGE_15|PDCB_PROJECTOR_LOCAL_12 | 0.307158 | 0.463413 |
| PDBG_CUT_SPLITTER_06 | BRIDGE_GAP_CUT_SPLITTER_06 | [1, 2, 2] | PDCB_BRIDGE_14|PDCB_BRIDGE_15|PDCB_PROJECTOR_LOCAL_08 | 0.312252 | 0.508964 |
| PDBG_ALT_PATH_07 | BRIDGE_GAP_ALTERNATIVE_PATH_07 | [2, 2, -1] | PDCB_BRIDGE_18|PDCB_PHASE_LOCAL_02 | 0.315231 | 0.572949 |
| PDBG_BASIS_TEST_08 | BRIDGE_GAP_ACTIVE_BASIS_DISCRIMINATOR_08 | [3, 2, 0] | PDCB_BRIDGE_18|PDCB_PROJECTOR_LOCAL_10|PDCB_PROJECTOR_LOCAL_11 | 0.294018 | 0.508964 |

## Batch freeze
- Batch 1: exactly 4 geometries / 8 x-y subruns: `PDBG_PHASE_EXIT_01, PDBG_PROJECTOR_EXIT_03, PDBG_CUT_SPLITTER_05, PDBG_ALT_PATH_07`.
- Batch 2: maximum 4 geometries / 8 x-y subruns, only after the Batch 1 physical gate.
- Future ceiling: 8 geometries / 16 x-y subruns / 450 nm only.

## Caveats and constraints
`PROSPECTIVE_DIAGNOSTIC_PLAN_ONLY`, `NOT_D9`, `NO_SOLVER_AUTHORIZATION`, `NO_PHYSICS_LABEL`, `HISTORICAL_FULL_JONES_GATE_REMAINS_BLOCKED`, `CURRENT_FORMAL_GRAPH_NOT_CONNECTED`, `CANDIDATE_GRAPH_EDGES_ARE_PREDICTED_NOT_PHYSICS`. No execution package, physics staging, D9 file, solver input, new physics row, canonical merge or training was created. Historical gate remains `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.

## Outputs
The 12 required graph, cut-set, barrier, candidate, plan, contract, checksum and report paths are listed in the checksum manifest.
