# LP 5D formal-phase reachability evidence audit v1

- Outcome: `LP_5D_PHASE_REACHABILITY_PROBE_PLANNING_READY`
- Evidence level: `LEVEL_1_CURRENT_PHASE_SUPPORT_NARROW_DESIGN_SPACE_UNDEREXPLORED`
- Creation code commit: `6c32c8e7d6687cb2279e6cff815b9d0ea54be55e`
- Solver calls: `0`
- Formal phase: `arg(txx)` under `P_APCD=diag(1,0)`
- Matrix payload SHA256: `accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb7025821587348f0` (expected `accd073c7d27086debc80e21056dade6b534080bc6e5d4fbb7025821587348f0`)
- Contract file SHA256: `7f3ecb0468bb29a86f5bd5ff1da4cd833ee057acf9fb41fc6ad0346e630ff926` (expected `7f3ecb0468bb29a86f5bd5ff1da4cd833ee057acf9fb41fc6ad0346e630ff926`)

## Compatible historical physics

- `lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv`: `FORMAL_CONTRACT_EXACT_COMPATIBLE`, admitted 450nm complete/non-054 rows=375; excluded 054 at 450nm=2, all wavelengths=18.
- `candidate_wavelength_jones_v1.csv`: `FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE`, admitted 450nm complete/non-054 rows=35; excluded 054 at 450nm=0, all wavelengths=0.
- `candidate_wavelength_jones_v1_17.csv`: `HISTORICAL_REFERENCE_ONLY`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `candidate_wavelength_jones_v1_22.csv`: `FORMAL_CONTRACT_EXACT_COMPATIBLE`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `candidate_wavelength_jones_v1_21.csv`: `HISTORICAL_REFERENCE_ONLY`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `candidate_wavelength_jones_v1.csv`: `HISTORICAL_REFERENCE_ONLY`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `b120_j2lm06_original22_complete_jones_manifest_after_regeneration_v1.csv`: `HISTORICAL_REFERENCE_ONLY`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `b120_j2lm06_bounded6_full_jones_retrospective_candidate_residuals_v1.csv`: `HISTORICAL_REFERENCE_ONLY`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `b120_j2lm06_stage_d7_d8_joint_candidate_metrics_v1.csv`: `FORMAL_CONTRACT_NUMERICALLY_TRANSFORMABLE`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `stage11_12_13_lp_compatibility_inventory_v1.csv`: `INCOMPATIBLE_EXCLUDE`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- `lp_ml_round3_recalibrated_508_candidate_table_v1.csv`: `INCOMPATIBLE_EXCLUDE`, admitted 450nm complete/non-054 rows=0; excluded 054 at 450nm=0, all wavelengths=0.
- Historical hard gate preserved: `HARD_GATE_FROZEN_TXX_REPRODUCTION_FAILURE`; original22/bounded6 are not promoted to historical primary reachability physics.

## Observed real phase envelope

- Unique admitted geometry rows: 407; phase 62.053626948833056–106.89783294848239°; linear span 44.84420599964933°; largest uncovered circular arc 315.1557940003507°. Label is OBSERVED_PHYSICS_PHASE_ENVELOPE, not TRUE_5D_PHASE_LIMIT.

## Projector-conditioned phase envelope

- all: n=407, phase=62.053626948833056–106.89783294848239°, span=44.84420599964933°.
- best25: n=102, phase=82.6271887339913–106.89783294848239°, span=24.270644214491085°.
- best50: n=204, phase=79.05281393084377–106.89783294848239°, span=27.84501901763862°.
- throughput_ge_median: n=204, phase=62.053626948833056–106.16483788778189°, span=44.11121093894883°.
- Conditioning result: `PHASE_PROJECTOR_TRADEOFF`; no new absolute PASS threshold introduced.

## Geometry phase leverage and boundary coverage

{"J1_side_nm": 0.8637787108207389, "J2_length_nm": 0.5744760814190888, "J2_width_nm": 0.1796755121661784, "D_nm": -0.451142244285971, "Psi_deg": -0.38555251870454277}

- 5D rows with coordinates: 375; extrema are interpreted against observed support only. Frozen manufacturing bounds were not inferred from a single artifact.

## Six-bin surrogate extrapolation and dense diagnostic

- 508-row table stored no predicted complex txx fields: recomputed C0/C1/C5/planning-blend phase is unavailable; target phases are not substituted.
- Dense request: 200,000 points; status `DENSE_SCAN_NOT_EXECUTED_MODEL_UNAVAILABLE`; prediction-only label retained.

## Dedicated probe proposal

- `LP_5D_PHASE_REACHABILITY_PROBE_V1`: 24 planned geometries / 48 x/y subruns / 450nm only; offline plan, no runnable solver package, no D9.

## Decision

`LP_5D_PHASE_REACHABILITY_PROBE_PLANNING_READY` — current support is too narrow to prove a 5D limit; a dedicated reachability probe is planning-ready. Sampling limitation is plausible, not established.
