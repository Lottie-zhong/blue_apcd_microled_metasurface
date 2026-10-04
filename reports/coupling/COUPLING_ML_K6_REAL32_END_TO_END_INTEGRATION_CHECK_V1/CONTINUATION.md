# CONTINUATION: COUPLING_ML_K6_REAL32_END_TO_END_INTEGRATION_CHECK_V1

Updated: 2026-10-04

## Resume entry

Read this file first, then REPORT_V1.md, INTEGRATION_RESULT_V1.json, FIT_LEDGER_V1.json, and SHA256_INVENTORY_V1.json. Reconfirm remote hostname/user, worktree, branch, HEAD, upstream divergence, and workspace state before further operations.

## Project and connection

- Canonical project root: D:\project\blue_apcd_microled_metasurface
- Formal worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1
- Host/user: DESKTOP-NNE313K / desktop-nne313k\dell
- NetBird SSH: dell@100.81.105.58; reuse the existing Windows key and host alias.
- Branch at task start: work/mdc-np-coupling-ml-v1; task-start HEAD: 40c3004e9c6a02436999b9de1be0276f8f29f6fa.
- Preserve unrelated dirty/untracked workspace files; stage only this task's exact allowlist.

## Git checkpoint before this task commit

- The task began at 40c3004e9c6a02436999b9de1be0276f8f29f6fa. During the task, HEAD advanced to 99d79d46079a925551bf12b34bd377a4e2e924ad through the unrelated Record K6 V2 owner enrollment setup readiness commit. Its files were reviewed as non-overlapping; no reset was performed.
- At the pre-commit audit, branch work/mdc-np-coupling-ml-v1 was 0/0 against upstream. Preserve all unrelated untracked files; only the explicit task allowlist is eligible for commit.

## Authority and frozen boundary

- Pipeline implementation continuation SHA-256: 8d5f507a29405f51926bec9a69532b34db43511fb05dfde51d250ec139ca421f.
- Pipeline report SHA-256: 5274a510985cee9c30598e3b23f604390201ec3723040fe86b63c4b30bd825cb.
- Old32 truth NPZ SHA-256: fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28.
- Original H1 authority SHA-256: 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd.
- Frozen H2 decoder SHA-256: b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15.
- Current read-only GPU Runner handoff SHA-256: 1b0545e69e5e4cc10cb887c1e0a5613c7ab892435f6ca9beb6ca39e4ab6608da; this task invokes no Runner.
- Split SHA-256: 9f2ed2aefcc9e49a3362356fd0aa5d336a9caaa6bbb315ffe334bb3d1397946e.
- Diagnostic config SHA-256: 6563a0f272f398fc84322889d2e3e10fd163711c7245313eb2776512f0ddd40d.
- Current amended pre-fit protocol SHA-256: 927aeeb35c8e204accead069b4f4f63058d52c55881aeccc2c4fd593e3681437.

The fixed seed-3208 old32 split is 24 train / 8 validation and engineering-only. It does not replace formal V2 folds. The frozen candidates are median-grid KRR (gamma=1/3, alpha=0.01) and Cartesian MLP (seed=0, weight decay=1e-4, early stop 50/min_delta=1e-5). No search or response-based config choice occurred.

## Completed state and counts

- Real logical fits complete: one KRR and one MLP, total two.
- MLP best checkpoint update 87; stopped after 137 optimizer updates.
- Solver entries 0; new FSPs 0; confirmation response values opened 0; standalone P_scale fits 0; formal V2 fits completed 0.
- SHA-checked reload parity passed: max absolute C_hat delta 0 and P_scale delta 0 at rtol=1e-12, atol=1e-12.
- Frozen H2 and original conjunctive H1 ran on all eight diagnostic geometries. All applicable numeric gates were false; one-seed stability is not applicable. This is engineering evidence only.
- Synthetic aggregation fixture covers complex C_hat mean and physical-domain arithmetic P_scale mean; test-only activity is counted in TEST_RESULTS_V1.json.
- Unrelated existing untracked worktree state was preserved.

## Artifacts and recovery

Artifacts are under reports/coupling/COUPLING_ML_K6_REAL32_END_TO_END_INTEGRATION_CHECK_V1/. Per-fit bundles are in fit_artifacts/RBF_KRR and fit_artifacts/CARTESIAN_MLP. The ledger is COMPLETE: do not refit either candidate. Verify artifact SHA values using SHA256_INVENTORY_V1.json before reuse.

Amendments V1-V4 and the preserved base protocol retain the exact pre-fit changes and implementation corrections. An old32-only load hit a loader return-name error before any fit; the ledger preserves the failure with zero fit starts. No scientific split, model config, or budget changed.

## Next action

This integration task is complete. Wait for newly admitted development truth and completed EXT02 two-plane scientific validation. Do not start formal V2 training, local affine fits, solver jobs, Runner jobs, or confirmation evaluation from this continuation.
