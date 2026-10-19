# Unresolved Items (V2)

以下内容原样保留，避免为追求 clean 改写科学记录或跨支线数据。

## 1. DOE56 V3 science ledger / credential context

- Dirty tracked file：`reports/coupling/APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1/V3_EXECUTION_LEDGER_V1.json`
- 追加记录计数检查：56 authorized、4 entered/truth/labels、52 remaining、replay 0、confirmation access 0；旧 record 未删除/改写。
- 新增的 Runner process command 字段含外部 license credential context；未提交、未清洗/重写 ledger。两个 untracked protected ledger snapshots 同样含该上下文，已精确忽略保留。

## 2. K6 remaining127 identity/authority conflict

- Dirty tracked queue ledger：`reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1/QUEUE_EXECUTION_LEDGER_V1.json`
- 对账发现 ledger authorized IDs=125，但 entered IDs=128；正式 batch manifest 有128个唯一身份。entered IDs 在该 manifest 内，但授权集与执行数不一致，不能认证为安全 append-only 科学权威状态。
- `BATCH_PREPARATION_STATUS_V1.json`、4项原 staged 文件和同目录 680 个未跟踪历史队列证据都保留。精确 unstage 后 index 为0；没有提交该冲突目录或改写历史。
- 另有 `COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1/CONTINUATION.md` 与 K6GDP2 当前身份叙事冲突，保留 dirty。

## 3. 其他任务/子线归属

- `M2I_LEVEL2A_RUNTIME_V1/cases`：133 项（V1 分类为 OTHER_COUPLING_SUBLINE_ASSET），未提交/删除。
- `scripts/coupling_ml`：38 项（V1 归为其他子线脚本），未执行、未提交。
- `reports/shared_v3`、`scripts/shared_fdtd`、`scripts/postentry-race-p6816tot`、两份 `entered_exception_isolation_results.csv`、一个根级 `AGENTS.md` 和其他9项不明 source/runtime 项均原样保留。

## 4. 跨任务恢复状态

- `reports/coupling/COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1/CONTINUATION.md` 仍处于等待 Runner owner 修复的历史恢复说明。本轮未启动 controller/runner，也未执行 solver。
- 其他 K6 history files 未纳入本次提交，以免混淆旧 attempt、授权集与当前批次身份。

## 关闭条件

需要由科学 Owner 确认 K6 授权/entry 映射，DOE56 credential-bearing ledger 需要用安全方式隔离凭据而不丢权威记录，并由资产负责人确认 M2I/shared/instruction 文件归属。当前为 **PARTIAL**，不应把 Git 状态写成 clean。
