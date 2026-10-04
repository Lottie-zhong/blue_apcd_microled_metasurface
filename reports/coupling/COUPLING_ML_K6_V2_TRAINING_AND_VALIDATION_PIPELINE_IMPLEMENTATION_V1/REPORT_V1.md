# COUPLING_ML_K6_V2_TRAINING_AND_VALIDATION_PIPELINE_IMPLEMENTATION_V1

更新时间：2026-10-04
工作树：`D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
分支：`work/mdc-np-coupling-ml-v1`

## 状态

**READY（代码准备完成，真实执行依赖未满足）**。实现、冻结协议接线和合成代码检查已完成；本轮没有启动生产训练、solver 或确认评估。

## authority 与冻结接口

代码中的物理输入输出来自已核对的 K6 V2 authorities。SHA-256：

| Authority | SHA-256 |
|---|---|
| Integrated K6 physical contract | `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` |
| V2 dataset authority | `0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e` |
| Ordered geometry authority | `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f` |
| Original H1 authority | `8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd` |
| Frozen H2 decoder source | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| V2 base protocol | `4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a` |
| Amendment 01 | `124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a` |
| Frozen candidate point set | `596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4` |
| Outer geometry folds | `309556978921717151716f20bbb80faf38e9d94bbbf52e27e6ff0a61d44a15ee` |
| Inner geometry folds | `ab8d7d1cf1dc1909b03d15cc43fda7d9a036c50fd66039eed66c6e1495936441` |
| Learning-curve manifest | `2ad2282e6551520e32644e3335d167f2706dd6a3e250ac75d7358c47fb5706de` |
| Two-air-plane protocol | `fa2839ac5613df63d54508d79df9da98d5bc0243876ab9c1a5538ae75b9f92b8` |
| GPU Runner formal handoff | `b7884408f7273a161e39f082e5228cab41e91af68521b6ddbfa9fd56bed02761` |

The schemas preserve ordered six-diameter geometry, the 21-wavelength axis, seven order-local TE/TM complex coordinates, C_hat as 588 real Cartesian values per geometry, and positive P_scale as 21 values. Each geometry remains a single grouped sample.

## Implemented pipeline

- **Data access:** a role-bound registry enforces old32/new128 development, local4/global28 confirmation, and diagnostic roles. Verified truth loading checks IDs/attempts, geometry and contract, wavelength/order/polarization order, reference plane, normalization, provenance, hashes, finiteness, and P_scale positivity. Training APIs reject confirmation and diagnostic cases; they also reject raw-array production fits.
- **Folds and preprocessing:** geometry-level outer/inner splits and train-only geometry scaling. Scaler/fold APIs make the fit indices explicit.
- **Models:** RBF KRR and the frozen 6→32→32 Cartesian MLP. Outputs are 588 C_hat Cartesian channels plus 21 log(P_scale) channels; the MLP has 21,377 trainable parameters including P_scale. The log/exp path rejects non-finite, overflow, and invalid positive values instead of clipping or adding epsilon.
- **Training/recovery:** exact fit task validation, nested 32/64/128 learning curves, checkpoints, per-update resumable MLP state, input/config SHA, and a dry-run schedule. Final global execution is wired to all 160 development geometries. Local affine work is a separate 13-fit interface.
- **H1:** uses the pinned H2 reconstruction and all applicable original conjunctive gates. C_hat uses complex arithmetic seed mean. Following the user’s decision, every seed’s P_scale is individually inverse-log-normalized and exponentiated; the positive physical values are then averaged arithmetically for the aggregate H1 prediction. The evaluator reports gate attainment only and sets production admission false.
- **Confirmation:** both global candidates’ prediction files must be frozen and byte-hashed before a one-shot reveal token can be issued. An evaluation ledger consumes the single evaluation attempt. Reports retain all 4 local-combination, 27 core, 1 stress, and 28 overall global confirmation strata; no stratum is dropped to hide an H1 failure.
- **Local and two-plane diagnostics:** local 12-fold leave-one-axial-out plus final-fit API; raw two-plane evaluator refits the official Floquet basis against saved E/H and reports rank, residual, conditioning and parity before de-embedding to 1722 nm. It requires both independent raw field planes, official gauge phase, and frozen extractor identity. Evanescent terms remain diagnostic and are excluded from propagating far-field power gates.

## Frozen schedule

The generated task file is `DRY_RUN_FIT_PLAN_V1.json` (SHA recorded in inventory). It schedules **281 logical fits** against the V2 ceiling of 284:

| Group | KRR | MLP | Total |
|---|---:|---:|---:|
| Nested inner selection | 108 | 108 | 216 |
| Fixed-outer learning curves | 12 | 36 | 48 |
| Final global refits | 0 | 4 | 4 |
| Local affine diagnostic | — | — | 13 |
| **Total** |  |  | **281** |

The global scheduler is 268 fits; the local 13 are separate. No P_scale-only model is scheduled. Dry-run tasks are not executed fits.

## Checks and execution counts

Completed captured checks:
- Final explicit current six-module pipeline suite: **34 passed in 19.54 s** (ingestion, confirmation, training, two-plane/local-affine, H1, and learning-curve validation tests).
- Ingestion + confirmation after the final role/freeze-gate change: **13 passed**.
- Training-focused suite: **8 passed**; an earlier pipeline-folder run: **32 passed** before the confirmation module was added.
- Two-plane/local-affine focused suite: **10 passed**.
- Python compilation checks passed for the implemented modules.

Captured synthetic-only work: four completed training-suite invocations exercise 1 KRR fit and 2 small MLP fits each (10 MLP optimizer updates each), for **12 captured synthetic model fits and 40 captured optimizer updates**. Four physics/local-affine test invocations exercise 13 OLS local fits each, for **52 captured synthetic OLS fits**. These are software fixtures, not scientific training. Confirmation tests use fabricated arrays and do not load confirmation truth.

One earlier task-owned package-wide pytest subprocess remained active for about 15 minutes without returning its buffered output, so it was stopped. Its partial synthetic test work, if any, cannot be recovered and is excluded from the captured counts above. The final explicit six-module rerun passed after the whitespace-only cleanup; no real truth, confirmation response, solver, or production fit was involved.

**Actual execution in scope:** solver entries 0; production/global training fits 0; production local fits 0; standalone P_scale fits 0; confirmation reveals/evaluations 0; new FSPs 0.

## Open dependencies and limits

- Only the existing 32 development truths were read and validated. The 128 new development responses are not yet available in an enrolled/validated package.
- No confirmation response values were read or evaluated.
- Runner handoff permits the previously authorized EXT02 attempt only; its formal double-air-plane scientific result is absent. This does not establish failure, but the label-validation launch dependency remains open.
- Manufacturing authority is absent; this pipeline supports scientific numerical experiments only and does not assert manufacturing compliance.
- A passing synthetic test proves software behavior only. It does not establish truth extraction quality, physical accuracy, global generalization, H1 admission, or production readiness.

## Handoff

Read `CONTINUATION.md` before resuming. The safe next action is to wait for enrolled, provenance-verified development truth and the actual EXT02 two-plane evidence; then run data validation and the frozen dry-run review. Do not train or reveal the confirmation set before the separately specified freeze conditions and user execution authorization are satisfied.
