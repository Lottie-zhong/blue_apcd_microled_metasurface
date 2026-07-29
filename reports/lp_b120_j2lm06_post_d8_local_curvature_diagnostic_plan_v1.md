# APCD LP POST-D8 Local Curvature Diagnostic Plan v1

## Status
`PLANNING_ONLY_NOT_AUTHORIZED`; offline only, solver calls = 0.

## Design comparison
Compared Design A antipodal tetrahedral complement, Design B half-step tetrahedral repeat, and Design C axis-focused active-basis design. Design A is selected because it creates four central pairs (+Δa, −Δa), retains an overdetermined full-rank three-variable gradient, and permits odd/even separation of phase, complex Jones, transmission, leakage, rank and projection response. Design B is one-sided and cannot identify even curvature. Design C is full-rank but not overdetermined or centrally symmetric.

## Anchor and probes
Anchor: `D8_TRV_PLAN_d6f4911593b64495`. Existing measured probes: 4. New diagnostic probes: 4. New IDs: POSTD8_CURV_MIRROR_WP_DP_PP, POSTD8_CURV_MIRROR_WP_DM_PM, POSTD8_CURV_MIRROR_WM_DP_PM, POSTD8_CURV_MIRROR_WM_DM_PP.

The new geometry is generated only from each existing probe's actual quantized displacement: `q_new = q_anchor - (q_existing - q_anchor)`. J1 side, J2 length, H=500 nm, period=432 nm, native material, reference plane, boundaries, mesh, monitor and weighted-G0 observable remain fixed. All probes are `PLANNED_NOT_RUN`, physics fields are `ABSENT_NOT_SIMULATED`, and prediction labels are `MODEL_PREDICTION_NOT_PHYSICS_LABEL`.

## Central symmetry
Maximum raw pair residual norm: `0.005208009`. Maximum normalized residual norm: `0.011179940`. All four centers are integer/half-nm grid; all direct and periodic gaps pass the 60-nm gate; exact, canonical-relative and symmetry hashes are internally unique and canonical duplicate-free.

## Future validation contract
Future budget is exactly 4 geometries / 8 x-y subruns / 450 nm, planning-only and not authorized. After execution, each pair must provide phase/Jones/projector odd/even terms, central gradients, directional second differences, covariance and leave-one-pair-out stability. No full Hessian may be claimed. No anchor rerun, existing-probe rerun, extra probe, D9, spectrum, tolerance or canonical merge is authorized.

## Outputs
Plan, contracts, checksum manifest and gate files are emitted under `outputs/lp_ml_dataset_v1/{analysis,plans}`. No execution package or physics staging was created.
