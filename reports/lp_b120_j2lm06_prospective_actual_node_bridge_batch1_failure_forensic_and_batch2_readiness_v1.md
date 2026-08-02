# APCD LP Batch 1 singleton forensic and Batch 2 readiness review v1

## Scope
- Offline only; solver calls in this review: 0.
- Frozen 8-node plan and formal thresholds unchanged; no Batch 2 staging/package/physics artifact created.

## Batch 1 forensic
- 4/4 nodes have exact geometry hashes, complete x/y weighted-G0 Jones provenance and accepted checkpoints.
- Every incident coordinate-comparable edge is decomposed at 1.00x, 0.75x and 0.50x in the machine-readable CSV.
- The original all-singleton result was a stale-edge-metric artifact. After recomputing Batch-1 edges from accepted phase values, all four nodes connect locally to pre-existing components at 1.00x; realized cross-anchor component gain remains 0.

### PDBG_PHASE_EXIT_01
- nearest coordinate node: PDCB_PHASE_LOCAL_01 (L2=1); nearest Jones node: PDCB_PHASE_LOCAL_01 (Frobenius=0.00179333).
- dominant barrier: NONE; secondary: none; classification: CONNECTED_WITHIN_EXISTING_COMPONENT.

### PDBG_PROJECTOR_EXIT_03
- nearest coordinate node: PDCB_PROJECTOR_LOCAL_07 (L2=1); nearest Jones node: PDCB_PROJECTOR_LOCAL_07 (Frobenius=0.00408597).
- dominant barrier: sigma_ratio; secondary: Tyy, leakage, jones_frobenius; classification: MIXED_BARRIER_WITH_LOCAL_CONNECTION.

### PDBG_CUT_SPLITTER_05
- nearest coordinate node: PDCB_BRIDGE_15 (L2=1); nearest Jones node: PDCB_BRIDGE_15 (Frobenius=0.00361879).
- dominant barrier: sigma_ratio; secondary: leakage, Tyy, jones_frobenius; classification: MIXED_BARRIER_WITH_LOCAL_CONNECTION.

### PDBG_ALT_PATH_07
- nearest coordinate node: PDCB_BRIDGE_18 (L2=1); nearest Jones node: PDCB_BRIDGE_18 (Frobenius=0.00269677).
- dominant barrier: sigma_ratio; secondary: Tyy, leakage; classification: MIXED_BARRIER_WITH_LOCAL_CONNECTION.

## Prediction versus realization
- Predicted cross-component merging potential for Batch-1: 3; realized cross-component merge: 0.
- Prediction and prospective physics labels remain separate. Predicted projection error/Jones-step fields have no actual counterpart in Batch-1 candidate metrics and are reported as unavailable, not fabricated.
- Plan-level conclusion: COMPONENT_GAIN_ESTIMATOR_LOCALLY_UNRELIABLE_AT_TESTED_BRIDGE_ROUTES; local same-component insertion is supported, cross-anchor bridge prediction is not.

## Batch 2 readiness
- PDBG_PHASE_EXIT_02: BATCH2_NODE_LIKELY_SINGLETON (phase exit); solver=0, frozen geometry preserved.
- PDBG_PROJECTOR_EXIT_04: BATCH2_NODE_LIKELY_SINGLETON (projector exit); solver=0, frozen geometry preserved.
- PDBG_CUT_SPLITTER_06: BATCH2_NODE_LIKELY_SINGLETON (cut split); solver=0, frozen geometry preserved.
- PDBG_BASIS_TEST_08: BATCH2_NODE_INDETERMINATE (active-basis rotation); solver=0, frozen geometry preserved.

## Overall recommendation
- `DO_NOT_AUTHORIZE_BATCH2_UNCHANGED`.
- Rationale: all four Batch-1 bridge predictions overestimated realized connectivity; remaining phase/projector/cut-split nodes repeat failed routes, while the basis-test node lacks edge-level predicted Jones support for a conservative authorization.

## Integrity
- Historical hard gate remains `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.
- Protected reports and Batch-1 solver entry count are audited separately; no D9 artifacts.
