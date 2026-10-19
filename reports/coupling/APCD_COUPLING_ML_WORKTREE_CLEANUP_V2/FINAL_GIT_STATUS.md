# Final Git Status (V2)

这是 V2 最终文件归档之前的状态快照；本报告组由后续精确 allowlist commit 加入。报告组提交后预期状态计数保持相同（5 tracked modified、871 untracked、0 staged、15,748 ignored），其自身文件转为 tracked。

- Branch: `work/mdc-np-coupling-ml-v1`
- Snapshot HEAD: `c65602fcd2db035bda1b2db0b9b26e88ee0200ae`
- Upstream: `refs/remotes/origin/work/mdc-np-coupling-ml-v1`
- Snapshot ahead/behind: `10/0`
- Staged: 0
- Tracked modified: 5
- Untracked: 871
- Ignored (`git status --ignored`): 15748
- Status clean: **NO**（保护身份冲突与其他支线资产原样保留）

Tracked modifications deliberately retained:

- `reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json`
- `reports/coupling/COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md`
- `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/BATCH_PREPARATION_STATUS_V1.json`
- `reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json`
- `reports/coupling/COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1/CONTINUATION.md`

当前可见 untracked 项按 V1 分类见 `V2_CLASSIFICATION_SUMMARY.csv`。有 680 项位于 K6 remaining127 身份冲突目录，另有 171 项归属其他 Coupling 子线、以及共享/runtime/source-ownership 项。科学输出目录下 1,740 个原位资产由精确目录规则忽略；忽略状态不代表文件被移动或删除。

Final report commit 后执行 normal push；最终 branch/upstream 同步情况在对话 closeout 中复核。
