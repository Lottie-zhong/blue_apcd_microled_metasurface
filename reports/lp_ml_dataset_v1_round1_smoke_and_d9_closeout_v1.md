# LP_ML_DATASET_V1 Round-1 smoke and D9 closeout

## D9 closeout
- Decision: `CONTRACT_EVIDENCE_GAP`; D9 solver/candidate generation remains unauthorized.
- Absolute projector guard: `PROJECTOR_GUARD_CONTRACT_NOT_IDENTIFIABLE`; phase anchor retained.
- Historical hard gate preserved: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`.

## Contract and plan
- 256 planned candidates: {'GLOBAL_SOBOL': 128, 'PHASE_REGION': 64, 'PROJECTOR_REGION': 32, 'BOUNDARY_FAILURE': 32}.
- Smoke subset: 16 candidates: {'GLOBAL_SOBOL': 8, 'PHASE_REGION': 4, 'PROJECTOR_REGION': 2, 'BOUNDARY_FAILURE': 2}.
- Inputs are the five geometry variables plus sin/cos(Psi); fixed H=500 nm, period=432 nm, Native-M1, field_monitor z=1000 nm and weighted-G0 normalization.
- `projection_error_apcd_v1` is continuous, target-Jones scalar/phase-invariant, and not an absolute guard.

## Smoke execution
- Planned: 16 geometries / 32 x-y subruns / 450.0--454.0 nm at 0.5 nm.
- Entered: 1; accepted: 0; complete geometries: 0; spectral rows: 0.
- First subrun `LPML_R1_GLOBAL_SOBOL_001_x` entered the solver once. The monitor returned 5 transmission frequency samples while the contract requires 9. No retry was made and scheduling stopped.
- Outcome: `LP_ML_PIPELINE_SMOKE_PARTIAL_FIX_REQUIRED`.

## Integrity
- Protected reports unchanged by SHA256. No D9 geometry, model training, inverse design, K6, remaining 240 production points, or heavy artifact was generated.
- Failure evidence and entered accounting are retained under `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\staging\lp_ml_dataset_v1_round1_smoke_v1`.
