# LP ML inverse Stage-I phase-convention and identifiability audit v1

## Decision

`LP_ML_INVERSE_STAGE1_PHASE_AUDIT_HARD_GATE`

The prior Stage-I `LP_ML_INVERSE_STAGE1_FIVED_SPACE_INSUFFICIENT_EVIDENCE` conclusion is superseded and not confirmed. No solver, retraining, new geometry, broadband, K6, geometry-054 rerun, or raw-physics rewrite occurred.

## Evidence/hash reconciliation

- Host: `DESKTOP-NNE313K`; branch: `work/lp-stage11-4`; HEAD: `9f0e5eb006478786cb5782bd5d55e22b4066fd6d`; ahead/behind: `0/0`.
- Stage-I immutable physics: 35 complete rows, bins `6/6/5/6/6/6`; raw Jones staging and immutable manifest are hash-recorded.
- Round-3 clean-v3: 377 geometries / 3393 rows; Stage-I and clean-v3 artifacts remain present.
- Round-2 clean-v2 lineage remains valid; quarantined `LPML_R1_GLOBAL_SOBOL_054` contributes zero rows and zero matching exact-hash rows.
- The normalization artifact is `outputs/lp_ml_dataset_v1/clean_v2/normalization_clean_v2.json` with recomputed SHA256 `13c7855b48d8c34e674ea67cb343df9414306cf43a943efdec6bba001f864167`. Manifest, checksum, and training records all match this exact 64-character hash. The alternate historical text value is classified `REPORT_TRANSCRIPTION_ONLY`; the artifact itself is unchanged.
- Protected report hashes are unchanged.

## Circular-phase contract

The frozen metric requires

`c(J) = <P_APCD,J>_F / ||P_APCD||_F^2`, with `<P,J>_F = sum(conj(P_ij)*J_ij)`,

`phi = arg(c)`, and shortest circular residual

`abs(angle(exp(i*(phi-phi_target))))` in `[0,180]` degrees.

The >180-degree B4/B5 ranges were produced by reporting raw signed differences without circular wrapping: `POSTPROCESS_UNWRAPPED_PHASE_BUG_IN_RANGE_REPORT`.

## P_APCD / Jones convention

The source hash matches `b120_j2lm06_projector_guard_metric_definition_contract_v1.json`, but that frozen contract contains no numerical P_APCD matrix and marks the projection-error formula unresolved. The 2x2 Jones order is verified as `[[txx,txy],[tyx,tyy]]`; x input is `[txx,tyx]` and y input is `[txy,tyy]`.

A provisional `diag(1,0)` reference was used only for bounded diagnostic calculations. It is not the formal P_APCD reference and cannot establish formal common-phase identifiability.

## Phase consistency and conditioning

All 35 raw Jones candidates were independently recomputed under the provisional reference; circular errors are bounded in `[0,180]`. Analytic `sum(conj(P)*J)` and numerical complex-scalar minimization agree to zero measured difference in the audit samples. The conditioning table records 0.5%, 1%, 2%, and 5% Jones perturbation responses; these are diagnostic only because the numerical formal P_APCD is absent.

## Corrected tuple closure

The corrected enumeration evaluates all 38,880 raw combinations from the 35 raw Jones rows. Residuals use circular arithmetic and are bounded; the previous tuple artifact is retained as `SUPERSEDED_BY_PHASE_CONVENTION_AUDIT`. Because the formal P_APCD matrix is unavailable, this closure cannot be promoted to a formal phase-library conclusion.

## 377-real-physics coverage

The 450-nm clean-v3 map contains 377 unique geometries with provisional phase range `62.0536–106.8978` degrees. B0–B5 nearest-control results are recorded in the known-physics-controls table. This provisional map does not prove 5D insufficiency.

## Final gate

`formal_P_APCD_numeric_source_available=false` and `five_d_insufficiency_confirmed=false`. The correct current result is a formal-reference hard gate, not a 5D-insufficiency physics conclusion. Solver calls for this audit: `0`.