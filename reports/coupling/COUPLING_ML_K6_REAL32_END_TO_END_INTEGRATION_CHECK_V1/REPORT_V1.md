# COUPLING_ML_K6_REAL32_END_TO_END_INTEGRATION_CHECK_V1

Status: PASS for engineering integration only. This is not the V2 formal learning curve, model selection, independent confirmation, or model admission.

## Frozen inputs and split

- Worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; branch: work/mdc-np-coupling-ml-v1.
- Old32 truth NPZ SHA-256: fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28. Dataset authority SHA-256: 0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e.
- Fixed seed-3208 PCG64 split: 24 train and 8 validation geometries. All 21 wavelengths stay grouped per geometry. These validation cases are reused historical old32 development data, not an independent confirmation set.
- Split SHA-256: 9f2ed2aefcc9e49a3362356fd0aa5d336a9caaa6bbb315ffe334bb3d1397946e. Diagnostic config SHA-256: 6563a0f272f398fc84322889d2e3e10fd163711c7245313eb2776512f0ddd40d.
- Targets: 588 ordered Cartesian C_hat real coordinates plus 21 log(P_scale) channels. P_scale is strictly positive and finite before log and after exp. Geometry and target normalizers were fit only on the 24 training geometries.

## Fixed fits

- KRR: median frozen grid values gamma=1/3 and ridge alpha=0.01; one logical fit.
- Cartesian MLP: 6->32 GELU->32 GELU, 21,377 parameters, seed=0, weight decay=1e-4, AdamW at 1e-3, frozen validation early stop (patience=50, min_delta=1e-5); one logical fit. Best checkpoint was update 87; stop occurred after 137 optimizer updates.
- Each candidate predicted complete C_hat and physical positive P_scale. No standalone P_scale fit or additional candidate was run. Both fits used CPU; no GPU Runner was invoked.

## Frozen H2 and original H1 diagnostic on the 8 reused old32 geometries

| Model | State relative RMSE median / q95 / worst | Routing RMSE median / q95 / worst | Routing Pearson | Absolute-order RMSE median / q95 / worst | Thresholded-relative median / q95 / worst | P_scale/total-power RMSE median / q95 / worst | Total-power Pearson |
|---|---|---|---:|---|---|---|---:|
| KRR | 0.8104 / 0.9592 / 1.0036 (S42) | 0.1650 / 0.2375 / 0.2665 (S42) | 0.8474 | 0.0510 / 0.0700 / 0.0787 (S42) | 0.7829 / 0.8721 / 0.9044 (EXT07) | 0.4455 / 0.6587 / 0.6953 (S42) | 0.9078 |
| MLP | 0.7495 / 0.8869 / 0.9196 (S42) | 0.1794 / 0.2864 / 0.3026 (S42) | 0.8342 | 0.0768 / 0.0998 / 0.1076 (S42) | 0.8828 / 0.9412 / 0.9501 (EXT11) | 0.2083 / 0.5045 / 0.6127 (S42) | 0.9175 |

All applicable original numeric H1 gates were evaluated and were false for both candidates on this diagnostic split. Seed stability is not applicable because each candidate has one fitted seed. This is not an admission decision and does not establish generalization beyond these reused old32 geometries.

## Save/reload and seed aggregation

Both fit objects and prediction files passed SHA-checked reload. Recomputed predictions matched saved predictions at rtol=1e-12 and atol=1e-12; maximum absolute differences were exactly 0 for C_hat and P_scale. The MLP progress checkpoint best state matched the saved model (best update 87, completed updates 137).

The H1 report now includes per-seed metrics, C_hat norms before and after complex seed mean, aggregate metrics, and positive-physical-domain P_scale summaries. With one real seed per model, the C_hat norm ratio after/before mean was 1.0. The synthetic three-seed fixture checked arithmetic physical P_scale aggregation and the C_hat aggregation diagnostic; no additional real seed fits were run.

## Execution and audit

- Real fits: 1 KRR + 1 MLP. Synthetic test-only fit API calls: 2 KRR + 10 MLP calls across captured training-test invocations; 20 MLP optimizer updates. These are test fixtures, not scientific fits.
- Solver entries: 0. New FSPs: 0. Confirmation response values opened: 0. Standalone P_scale fits: 0. Formal V2 fits completed: 0.
- Targeted captured suites: H1/training modules 10 passed; ingestion/confirmation modules 13 passed. Python compilation, final pre-fit hash checks, and full real32 integration also passed.
- Pre-fit implementation errors and corrections are retained in the hash amendments and test results. The split and scientific configs were frozen before response access. A loader return reference was corrected after an old32-only load but before any fit. Split, candidates, parameters, and fit budget did not change.
- Current read-only GPU Runner handoff SHA: 1b0545e69e5e4cc10cb887c1e0a5613c7ab892435f6ca9beb6ca39e4ab6608da. Earlier metadata with an older Runner fingerprint is preserved in the base and amendment records. This task made no Runner changes.

- Git audit: task-start HEAD 40c3004e9c6a02436999b9de1be0276f8f29f6fa advanced to 99d79d46079a925551bf12b34bd377a4e2e924ad via the reviewed, unrelated owner-enrollment readiness commit. At the pre-commit check the branch was work/mdc-np-coupling-ml-v1, upstream divergence 0/0; unrelated untracked state was retained.

## Artifacts

- Split/config/protocol and amendments V1-V4.
- Fit ledger, freeze records, integration result, test results, and continuation.
- Per-candidate model, preprocessing, trajectory, progress checkpoint where applicable, validation predictions, fit manifest, and frozen H1/H2 diagnostic metrics under fit_artifacts/RBF_KRR and fit_artifacts/CARTESIAN_MLP.
- Exact file hashes and sizes are recorded in SHA256_INVENTORY_V1.json. Read CONTINUATION.md before resuming.
