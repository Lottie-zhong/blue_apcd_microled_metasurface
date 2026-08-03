# J2LM06 absolute projector guard calibration and D9 contract audit v1

## Scope
Offline-only audit. No solver/FDTD/lumapi calls, no new geometry, no Batch B/old Batch 2, and Batch A was held out before calibration.

## Metric contract
- Frozen Jones convention: J=[[txx,txy],[tyx,tyy]].
- Tij=|tij|^2; combined leakage is Tyy+Txy+Tyx; sigma ratio is SVD sigma2/sigma1.
- Projection error is not frozen across sources: projection_error and matrix_projection_error lack one traceable target-Jones formula.
- Manufacturing is a geometry gate, not an optical guard.
- Existing graph deltas are Layer-3 local continuation thresholds only.

## Cohorts
Calibration core contains 5 positives (4 POST_D8 curvature formal positives + 1 D0 projector control) and 11 D0 negatives (wrong-axis/high-rank). 6 bounded pre-Batch-A rows are supporting positives only. Batch A calibration leakage is 0.

## Observed separation
- Txx: positive max=1.0098177, negative min=0.939153142904, separated=False (provisional only)
- Tyy: positive max=0.112334825379, negative min=0.940741886609, separated=True (provisional only)
- combined_leakage: positive max=0.112334825886, negative min=0.940741886609, separated=True (provisional only)
- cross_power: positive max=1.55630728108e-05, negative min=4.59690520244e-18, separated=False (provisional only)
- sigma2_over_sigma1: positive max=0.340589482057, negative min=0.971890755246, separated=True (provisional only)
- projection_metric: positive max=0.340589482057, negative min=0.974625223448, separated=True (provisional only)

## Identifiability
Outcome: PROJECTOR_GUARD_CONTRACT_NOT_IDENTIFIABLE.
Observed separation is not a frozen absolute guard: no independent negative stage, no pre-registered operating point, and unresolved projection-error semantics. Existing empirical guard explicitly says threshold_invented=false.

## Layered guard
- Layer 1 absolute: evidence gap; no PASS/FAIL emission.
- Layer 2 cross-metric: not identifiable.
- Layer 3 local continuation: frozen relative thresholds from the formal graph only.
- Projector lineage remains projector_preserved_from_backbone.

## Batch A holdout
Four J2_length nodes were evaluated after the immutable audit and remain PROJECTOR_GUARD_REMAINS_INDETERMINATE; none influenced calibration.

## Phase anchor and D9
Phase anchor decision: RETAIN_EXISTING_PHASE_ANCHOR.
D9 contract status: CONTRACT_EVIDENCE_GAP, solver_authorized=false, candidate_count=0.

## Preservation
Historical hard gate HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE is preserved. Canonical and protected reports are not modified.
