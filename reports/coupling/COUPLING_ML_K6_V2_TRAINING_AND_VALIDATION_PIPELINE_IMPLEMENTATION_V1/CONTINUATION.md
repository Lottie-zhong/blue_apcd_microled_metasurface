# CONTINUATION — COUPLING_ML_K6_V2_TRAINING_AND_VALIDATION_PIPELINE_IMPLEMENTATION_V1

更新：2026-10-04

恢复前先阅读本文件、同目录 `REPORT_V1.md`、`SHA256_INVENTORY_V1.json` 和 dry-run 任务清单。

## 项目/连接/工作树

- Canonical root: `D:\project\blue_apcd_microled_metasurface`
- Host/user: `DESKTOP-NNE313K` / `dell`
- NetBird SSH fallback: `dell@100.81.105.58`，密钥路径在本机 Codex SSH 配置中；LAN 可达时优先 `dell@192.168.1.107`。
- Formal task worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch: `work/mdc-np-coupling-ml-v1`
- Base HEAD at implementation start: `98c469ae3fd440227a82a4cfbcabe8636d281f12`
- Runner worktree is read-only and must not be edited.

## Authority / science

This is code preparation for the frozen K6 V2 Cartesian KRR/MLP protocol. Read REPORT and SHA inventory for all exact authority hashes. Ordered D1…D6, 21 wavelengths, seven TE/TM complex orders, C_hat 588 Cartesian values, separate positive 21-value P_scale, pinned H2 and original conjunctive H1 are fixed. MLP has 21,377 trainable parameters. P_scale seed aggregation is physical arithmetic mean after each seed is inverse-log-normalized and exponentiated; this was explicitly selected by the user.

## Boundaries

The implementation does not authorize new HF, solver entry, GPU Runner, reserve, inverse search, or production training. Confirmation responses must stay sealed. Production schedule is 281 fits (268 global plus 13 local) within the 284 ceiling; it is a dry-run only. No model selection from confirmation data. No confirmation data were read in this task.

## Implemented modules

See `scripts/coupling_ml/k6_v2_pipeline/README.md`. Data role registry/ingestion, geometry folds/preprocessing, models/scheduler/checkpoint/resume, H1/H2 wrapper, development learning-curve evaluation, local affine evaluator, raw two-air-plane evaluator, one-shot confirmation freeze/reveal/evaluation are in that package. Tests are under `tests/coupling_ml/k6_v2_pipeline`.

## Current status / execution counts

- Solver entries: 0.
- New FSP / production fits / P_scale-only fits: 0.
- Confirmation reveal/evaluation: 0.
- Only old32 development truth was read; 128 new response files and actual confirmation responses are absent.
- EXT02 double-air-plane truth/result remains a launch/label-validation dependency.
- Manufacturing compliance is not verified.
- Captured checks and exact synthetic test-only fit counts are in REPORT_V1.md.
- Final explicit current six-module pipeline test suite passed 34/34 in 19.54 s. Ingestion + confirmation targeted suite passed 13/13; earlier training suite passed 8/8, physics/local-affine passed 10/10, and pre-confirmation package suite passed 32/32.
- An earlier task-owned package-wide test subprocess had no captured output after about 15 minutes and was stopped. Its partial synthetic test-only operations are unobservable and are excluded from the captured totals; no solver or production fit was launched. No test process from that attempt remains active.
- Preserve all unrelated dirty/untracked workspace state. Stage only the exact paths listed in the task implementation report.

## Resume entry

1. Reconfirm hostname/user, branch, HEAD, upstream divergence, and worktree status.
2. Read this continuation and report before operating.
3. Verify each real development case against the frozen registry and provenance; fail closed until the full 160 development set is available.
4. Compare freshly built task-plan SHA/count with the frozen dry-run manifest.
5. Do not call training scheduler until the user separately authorizes scientific training.
6. Confirmation remains sealed until both candidate prediction bundles, model/preprocess/evaluator hashes, and artifact byte hashes are frozen and user-authorized reveal is formally recorded.
7. Do not run solver or Runner under this implementation task.
