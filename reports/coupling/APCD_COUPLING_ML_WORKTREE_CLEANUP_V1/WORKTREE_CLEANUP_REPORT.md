# APCD Coupling-ML Worktree Cleanup Audit

## 结论

**PARTIAL**。已建立可恢复外置快照并归档8个可确认的临时文件。工作树仍保留其他研究任务的科学资产、账本、代码和历史staged状态；不安全把这些文件批量提交、忽略或移走，因此未达到 clean。

## 范围与快照

- 正式 worktree：`D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch / HEAD at start：`work/mdc-np-coupling-ml-v1` / `2cc687020e90ec4397e6cd4ed31efed59aaaf386`
- Upstream ahead/behind at start：`0	0`
- Snapshot：`D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z`
- 快照记录：tracked文件的HEAD/index/工作树版本及Git补丁；6,944个未跟踪文件逐文件SHA256；12,935个ignored文件的路径、大小和类别。大型ignored数据未复制或重新哈希。
- 快照哈希：20.135 GB未跟踪文件，0个哈希失败；ignore资产共92.415 GB，按路径元数据引用。

## 数量与体积

| 状态 | 整理前 | 归档后/报告提交前 | 说明 |
|---|---:|---:|---|
| Tracked改动路径 | 10 | 10 | 保留，不覆盖 |
| Staged路径 | 4 | 4 | index保持原样；有一个`MM`文件还包含未暂存后续内容 |
| Untracked文件 | 6,944 / 20.135 GB (20,134,774,020 bytes) | 6,936 / 20.134 GB (20,134,097,881 bytes) | 8个临时文件移至外置归档 |
| Ignored文件 | 12,935 / 92.415 GB (92,415,199,269 bytes) | 不变 | 科学数据、模型、运行时状态和缓存保留 |

### 归档文件

- `.TEMP_SERIAL_QUEUE_STAGED_0251112F.py` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.TEMP_SERIAL_QUEUE_STAGED_0251112F.py`，133114 B，SHA256 `0251112fa75a151e09704feb283bef9a03ce508314cf71c43547a6bc8d893a42`
- `.TEMP_TEST_G023_RECOVERY.py` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.TEMP_TEST_G023_RECOVERY.py`，6491 B，SHA256 `c8212c85782fc4b1b8a6c2d95fe93ac18a473ec2da78683cc659376d3bdd85e8`
- `.serial_queue.pre_claim_hash_fix_1fdea4df.bak` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.serial_queue.pre_claim_hash_fix_1fdea4df.bak`，141025 B，SHA256 `1fdea4df839fad577687a5ff11267a2180c4d287ebe1a7c0987d8db5db755e2b`
- `.serial_queue.pre_controller_stop_fix_3499b933.bak` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.serial_queue.pre_controller_stop_fix_3499b933.bak`，141058 B，SHA256 `3499b93302857cf3e93cdf4b3832e042e0680574a2e2692ffc739eb40947ce05`
- `.serial_queue.pre_current_case_fix_05e80ae3.bak` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.serial_queue.pre_current_case_fix_05e80ae3.bak`，141124 B，SHA256 `05e80ae30a63c47e30867e1677649cfb1c04f4b694326f62d51028a73eba58a8`
- `.serial_queue.pre_g023_87ca4598.bak` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\.serial_queue.pre_g023_87ca4598.bak`，99843 B，SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966`
- `TEMP_TEST_G023_RECOVERY.py` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\TEMP_TEST_G023_RECOVERY.py`，13423 B，SHA256 `866be9b79aab9d8a501ada3e183a197ad5d40032f495fd6493b4c2d30ddf46ba`
- `$null` → `D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z\archive_candidates\$null`，61 B，SHA256 `d22ac9558e7c8dc8d9413dfe60f1ce0c8091cbc5152c78948c0139dc5085509d`

## 重点审查与冲突

### 4个原staged路径

这些是2026-10-05的K6 V2 `REMAINING127`启动复核材料，记录当时`BLOCKED_PREENTRY`，source/route SHA不匹配。其原始index字节、工作树版本和HEAD基线均在快照中保存。当前未提交队列账本已显示128个entry、124个labels-valid，故该启动报告只能作为历史时间点材料；**保持原staged状态，不作为当前authority提交**。

- `MM` `reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/SHA256_INVENTORY_V1.json`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_AUDIT_V1.json`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_BLOCKER_20261005.md`

### 10个tracked dirty路径

- ` M` `reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json`
- `MM` `reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md`
- ` M` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/BATCH_PREPARATION_STATUS_V1.json`
- ` M` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/SHA256_INVENTORY_V1.json`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_AUDIT_V1.json`
- `AM` `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/STARTUP_BLOCKER_20261005.md`
- ` M` `reports/coupling/COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1/CONTINUATION.md`
- ` M` `scripts/coupling_ml/k6_v2_pipeline/serial_queue.py`
- ` M` `scripts/coupling_ml/k6_v2_pipeline/training.py`

其中 `V3_EXECUTION_LEDGER_V1.json` 当前工作树记录4个entered/labels-valid项、52项未入场；`QUEUE_EXECUTION_LEDGER_V1.json` 当前工作树记录128个entry、124个labels-valid。二者属于受保护科学账本，保持不变。

`serial_queue.py` 的差异为约+653/-13行，`training.py` 约+35/-1行；存在对应的未跟踪controller修复报告和测试文件，但其continuation记录的是修复“进行中”，未闭合最终交接。没有验证其所有者和与当前账本的最终关系，因此不提交、不回滚、不覆盖。没有改动GPU Runner。

### 未跟踪与ignored文件分类

以下分类由路径、扩展名、大小和既有状态推定；不代表逐文件内容审阅。逐项记录见 `FILE_CLASSIFICATION_MANIFEST.csv`。

- `UNRESOLVED_OR_OTHER_SOURCE`：6871 files，0.277 GB (276,627,501 bytes)
- `NATIVE_SCIENTIFIC_DATA`：3223 files，87.404 GB (87,404,178,462 bytes)
- `FORMAL_REPORT_METRICS_OR_PROVENANCE_CANDIDATE`：2918 files，0.080 GB (79,996,168 bytes)
- `SCIENCE_IDENTITY_OR_PROVENANCE`：2229 files，0.039 GB (39,339,264 bytes)
- `MODEL_OR_DERIVED_SCIENTIFIC_ARTIFACT`：1847 files，8.299 GB (8,298,635,434 bytes)
- `OTHER_COUPLING_SUBLINE_ASSET`：1659 files，16.138 GB (16,137,695,856 bytes)
- `RUNTIME_OR_EXECUTION_STATE`：357 files，0.043 GB (43,196,560 bytes)
- `REGENERABLE_CACHE`：355 files，0.005 GB (5,062,787 bytes)
- `FORMAL_CODE_OR_ANALYSIS_SCRIPT`：218 files，0.003 GB (2,728,426 bytes)
- `OTHER_SHARED_INFRA_ASSET`：192 files，0.262 GB (261,828,574 bytes)
- `TEMPORARY_ARCHIVED`：8 files，0.001 GB (676,139 bytes)
- `HISTORICAL_REPORT_OR_AUDIT_EVIDENCE`：5 files，0.000 GB (31,995 bytes)
- `PROTECTED_QUEUE_OR_SCIENCE_LEDGER`：2 files，0.009 GB (9,351,621 bytes)
- `FORMAL_CODE_CHANGE_REVIEW_REQUIRED`：2 files，0.000 GB (339,945 bytes)
- `PROJECT_INSTRUCTIONS`：1 files，0.000 GB (4,118 bytes)
- `TEMPORARY_CANDIDATE`：1 files，0.000 GB (4,000 bytes)
- `PROTECTED_SCIENCE_LEDGER`：1 files，0.000 GB (452,190 bytes)

未跟踪文件最多的目录分布（前20项）：

- `reports\coupling\APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1`：1497 files
- `reports\coupling\APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1`：1405 files
- `reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1`：982 files
- `reports\coupling\APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1`：614 files
- `reports\coupling\APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION`：399 files
- `reports\coupling\APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1`：249 files
- `reports\coupling\APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2`：181 files
- `reports\coupling\APCD_COUPLING_272G_PSCALE_DECOUPLING_V1`：177 files
- `reports\coupling\APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1`：163 files
- `reports\coupling\APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1`：150 files
- `reports\coupling\APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1`：113 files
- `reports\coupling\APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1`：72 files
- `reports\coupling\APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1`：54 files
- `reports\coupling\APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1`：52 files
- `reports\coupling\APCD_COUPLING_AL50_V2_FINAL_SCIENTIFIC_CLOSEOUT`：51 files
- `reports\coupling\APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1`：50 files
- `reports\coupling\APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1`：46 files
- `reports\coupling\COUPLING_ML_CONTROLLER_STATUS_PATH_CONTRACT_REPAIR_AND_PRODUCTION_RECOVERY_V1`：43 files
- `reports\coupling\APCD_COUPLING_DIAG2_V31_FINAL_EXECUTION_GATE_CLOSEOUT_V1`：42 files
- `reports\coupling\COUPLING_K6_V2_G025_RECOVERED_TRUTH_INGEST_AND_G026_RESUME_V1`：35 files

Ignored资产按清单保留。现有`.gitignore`规则已覆盖`.fsp`、`.h5`、`__pycache__`、`.pytest_cache`等；本轮未添加新的宽泛规则，避免隐藏尚待归属的科学数据、报告或代码。

## Commit与验证

没有提交预存staged文件、受保护账本或来源未闭合的代码差异。本轮只归档上述8个临时文件；没有执行FDTD，也没有修改任何FSP/H5/609D、Science Ledger或GPU Runner。清理报告本身按精确allowlist单独提交；不推送。

本提交只包含四个清理交付文件，不含代码或科学原始数据，因此没有关联离线测试。工作树最终状态预计仍为dirty：4个原staged路径、10个tracked改动路径、约6,936个其他未跟踪文件（不含将提交的4个报告）。

## 交付文件

- `WORKTREE_CLEANUP_REPORT.md`
- `FILE_CLASSIFICATION_MANIFEST.csv`
- `BACKUP_AND_SHA256_MANIFEST.csv`
- `GIT_COMMIT_SUMMARY.md`
