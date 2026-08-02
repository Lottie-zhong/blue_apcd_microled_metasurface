# APCD LP Batch 1 actual-node bridge execution and graph gate v1

## EXECUTION

- Batch 1 only: 4 geometries / 8 x-y subruns / 450 nm.
- Candidates: PDBG_PHASE_EXIT_01, PDBG_PROJECTOR_EXIT_03, PDBG_CUT_SPLITTER_05, PDBG_ALT_PATH_07
- Solver accounting: planned=8, raw=8, successful=8, accepted=8, failed=0, missing=0, duplicate=0, unauthorized=0.
- Two pre-solver compatibility stops were repaired without solver entry; the first candidate x/y checkpoints were reloaded and not rerun.
- All accepted rows are formal weighted-G0, prospective cross-branch diagnostic physics; no historical claim.

## GRAPH_GATE

- Existing graph 34 nodes / 84 edges; post-Batch-1 graph 38 nodes / 92 edges.
- Threshold 1.00: 11 components; 0.75: 13 components; 0.50: 19 components.
- All four new actual nodes remain singleton components at all three thresholds.
- Phase/projector anchors remain disconnected; nearest frontier remains PDCB_BRIDGE_13 ??PDCB_BRIDGE_18.
- No formal connectivity gain; no Batch 2 or D9 was authorized or generated.

## OUTCOME

- `BATCH1_DIAGNOSTIC_NO_FORMAL_CONNECTIVITY_GAIN`
- Batch-1 phase floor is reported as a diagnostic only and does not promote a D9 candidate.

## OUTPUTS

- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_candidate_metrics_v1.csv`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_complete_jones_audit_v1.json`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_solver_accounting_v1.json`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_graph_gate_v1.json`
- `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_prospective_actual_node_bridge_batch1_formal_graph_components_v1.json`
