# Continuation — COUPLING_ML_K6_V2_GPU_PRODUCTION_FIRST_START_AND_CONTINUOUS_RUN_V1

上下文恢复时先读此文件。以下阻塞解除前，不得再次调用 start/resume、修改 Scheduler/runtime manifest，或使G027进入solver。

## 当前状态（2026-10-09 07:49 UTC）

- 远端已核验：DESKTOP-NNE313K / desktop-nne313k\dell。
- Coupling：D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1，branch work/mdc-np-coupling-ml-v1，HEAD a0747605c3e5fefe4e111aa5d16e3a148328ed37，upstream ahead 1 / behind 0；保留所有既有dirty/staged/untracked状态。
- Runner：D:\project\worktrees\blue_apcd_gpu_production_runner_v1，branch codex/apcd-gpu-production-runner-v1，HEAD a8a09213d14883349921e5432daacd72f2ee7bb4，clean/upstream 0/0。
- Successor request bbb7f19186776ceff07f93a17fded92b；manifest SHA bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f；binding SHA 155b81aeab5227aa99ac55bf5a9778f0c2e3fd2e79a31c1d17c9b2474dd65193。
- 仅调用过一次正式 start-controller-task。API返回START_REQUESTED；新查询为CONTROLLER_EXITED_NEEDS_RECONCILIATION、status=null；Scheduler Ready / LastTaskResult=2。未产生status或正式对账receipt。
- 正式stop reconciliation和零solver startup dry-run均返回QUEUE_STOP:CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT。
- 根因：manifest status_path 在COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1目录；已绑定的serial_queue.py第391–395行要求status_path位于COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1 REPORT根目录下。代码/manifest均与此request及Scheduler action绑定。禁止就地改动或绕过验证。
- 当前任务禁止重建request/rebind，因此生产阻塞于G027入场前。最小下一决策：是否授权通过正式Runner流程创建一个后继request/rebind，保留G027–G116范围和已消耗entry预算不变。得到授权后按正式绑定流程修正status路径，重新做完整零solver startup/reconciliation检查，再对新request只start一次；不可重试当前request。
- 当前计数：128授权、38 entered、34 truth-valid、34 labels-valid、90 unentered；training=0、P_scale=0、confirmation response access=0、automatic replay=0。下一案G027。本任务未新增solver entry/truth/label。
- Scheduler：PT0S、IgnoreNew、DELL、InteractiveToken；状态Ready、LastTaskResult=2。PT0S不证明logout/reboot后仍存活。
- 无代码或Runtime更改，无commit/push。证据在本任务目录的FINAL_REPORT.md、CURRENT_STATUS.md、SHA256_INVENTORY.json。

## 获得范围授权后的续接清单

1. 阅读FINAL_REPORT.md与SHA256_INVENTORY.json，再现场核对两个worktree HEAD、binding、request、ledger、slot、owner和active solver状态。
2. 仅在得到明确授权后走正式Runner retire/rebind/request流程；保留G026结案与预算消费，后继范围仍仅G027–G116、单槽、replay=0、truth-before-next、确认集封存。
3. 确保manifest status路径符合Coupling固定REPORT根目录要求，且脚本/manifest/binding/task action SHA一致。
4. 完成完整零solver启动与对账检查后，才对新request正式start一次。确认真实GPU engine entry后方可报告生产恢复。
5. G027必须具备完整E/H truth、正式验证和冻结importer PASS后才能计有效标签并推进。

## 证据入口

- 本任务报告目录：D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_K6_V2_GPU_PRODUCTION_FIRST_START_AND_CONTINUOUS_RUN_V1
- 账本：D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\QUEUE_EXECUTION_LEDGER_V1.json
- Runner request目录：D:\apcd_runtime\gpu_production_runner_v1\requests\scheduled_queue_controller_v1\bbb7f19186776ceff07f93a17fded92b
- Runner handoff：D:\project\worktrees\blue_apcd_gpu_production_runner_v1\docs\APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md
