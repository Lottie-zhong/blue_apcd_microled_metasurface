# LP 5D phase-reachability pre-solver reconciliation v2

- Outcome: `LP_5D_PHASE_REACHABILITY_PROBE_SOLVER_READY`
- Solver calls: `0`
- Bounds SHA256: `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`
- R1 quarantine hash present in clean-v3: `False`

## 054 exact-identity reconciliation

- `LPML_R2_BOUNDARY_AND_HIGH_GRADIENT_054`: `LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE`, exact hash `2e07d48ba61d315bc1f13ae407cd25ba2d8b825a7de07c1f830c9bfb8b04d069`.
- `LPML_R3_054`: `LEGAL_DIFFERENT_GEOMETRY_FALSE_POSITIVE`, exact hash `f3400f5c0285fce78abb249f8e7350bebf821ca3b902a13d63093145d61844ae`.
- R1 exact hash rows in clean-v3: 0; R2/R3 suffix rows retained as legal different geometries.

## Corrected clean-v3 admission

- clean-v3 exact geometry count: 377; corrected admitted reachability geometries including Stage-I dedupe: 409.
- Previous v1 admission is superseded by `SUPERSEDED_BY_EXACT_HASH_REACHABILITY_ADMISSION_V2`.

## Corrected physics phase envelope

- phase: 62.053626948833056 - 106.89783294848239 deg, span 44.84420599964933 deg, largest uncovered arc 315.1557940003507 deg. Label: OBSERVED_PHYSICS_PHASE_ENVELOPE_V2.
- Projector-conditioned classification: `PHASE_PROJECTOR_TRADEOFF`.

## Frozen authoritative 5D design bounds

- `D_nm`: 196.0 - 204.0 nm, inclusive; source `outputs\lp_ml_dataset_v1\plans\lp_ml_dataset_v1_5d_design_space_contract_v1.json` SHA256 `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`.
- `J1_side_nm`: 108 - 112 nm, inclusive; source `outputs\lp_ml_dataset_v1\plans\lp_ml_dataset_v1_5d_design_space_contract_v1.json` SHA256 `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`.
- `J2_length_nm`: 106 - 110 nm, inclusive; source `outputs\lp_ml_dataset_v1\plans\lp_ml_dataset_v1_5d_design_space_contract_v1.json` SHA256 `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`.
- `J2_width_nm`: 98 - 102 nm, inclusive; source `outputs\lp_ml_dataset_v1\plans\lp_ml_dataset_v1_5d_design_space_contract_v1.json` SHA256 `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`.
- `Psi_deg`: -1.2 - 1.2 deg, inclusive; source `outputs\lp_ml_dataset_v1\plans\lp_ml_dataset_v1_5d_design_space_contract_v1.json` SHA256 `ad47b66aa5b3bea41e7048a9998016e29150771a9a74633e66bbc98d7b25c2da`.
- Quantization: integer dimensions, half-grid centers, no sub-grid. Direct/periodic gap >=60 nm.

## Probe legality and composition

- 24/24 legal planned points; role counts: {'5D_BOUNDARY_SPARSE_REGION': 4, 'DISAGREEMENT_PHYSICS_CONTROL': 4, 'HIGH_PHASE_EXTREME': 6, 'LOW_PHASE_EXTREME': 6, 'PHASE_PROJECTOR_TRADEOFF': 4}; 48 x/y subruns at 450 nm; no runnable solver package.

## Readiness

The next solver authorization may be considered independently, but this task executed no solver. Historical hard gate and protected evidence are unchanged.
