# NP K6 M8A Primary2 targeted HF acquisition closeout v1

## Scope and safety

This closeout uses only existing attempt_001 results and independent read-only extraction. No solver was called during extraction, adjudication, slot release, dataset assembly, or monitor terminalization. No attempt_002, replay, replacement, sealed-HF read, external-HF read, or M9 training was started.

## G02-S authoritative audit

- Case: `NP_K6_M8A_PRIMARY2_G02_S`; attempt: `attempt_001`; polarization: `s`.
- Resource contract: 4 MPI processes x 1 thread; readback passed.
- Engine/controller/post-save: `1/1/1`; run invocation count: `1`.
- Post-FSP: `outputs\np_k6_m8a_primary2_hf_acquisition_v1\runtime_runs\NP_K6_M8A_PRIMARY2_G02_S\attempt_001\NP_K6_M8A_PRIMARY2_G02_S_attempt_001_post.fsp`.
- Post-FSP SHA256: `af13851ac4fde21e8a05de2287ea522fa98c5e336a24c84ab6b2c1de199b0f4b`.
- Independent reload: PASS; `run_called=false`; `save_called=false`; exact wavelengths 445--455 nm: 11/11.
- V2 gates: closure max `0.0021812441913199587`; structure interval anomaly max `0.0022240545939568035`; order-sum mismatch max `2.220446049250313e-16`; direct normalization mismatch max `1.1102230246251565e-16`; all PASS.
- T range `0.8129929389508684..0.9189877944842835`; R range `0.08088393444717466..0.18918830524045152`.

The authoritative V3 slot release API released `GLOBAL_SLOT_1` after quality adjudication. The old supervisor was ended before release so it could not replay the already completed G02-S pending entry. The durable monitor then produced `terminal_success.json`; historical anomalies remain retained and `active_hard_gate=false`.

## Dataset closeout

- Primary2: 4 logical cases, exactly 44 rows.
- HF22 development view: 484 rows, 22 unique geometries, 44 geometry-polarization pairs, 11 exact wavelengths per pair.
- LF22 linkage: 484 rows. The 20 existing geometries retain the formal full tracked-order LF baseline. The two new Primary2 geometries are linked to the frozen candidate LF `eta(+1)` authority only; other LF outputs are intentionally blank and labeled `ETA_PLUS1_ONLY`.
- P/S remains explicit; no polarization averaging was performed.
- M9 is not started; checkpoint count is zero; bulk MDC-compatible training remains unauthorized.

Machine-readable evidence is under `outputs\np_k6_m8a_primary2_closeout_v1\`.

## Decision

`NP_K6_M8A_PRIMARY2_TARGETED_HF_ACQUISITION_COMPLETE_22G_M9_RETRAIN_READY`

This is a development/HF-pilot closeout, not a frozen surrogate or bulk-MDC release.
