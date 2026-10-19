# Coupling K6 V2 恢复与训练环境核对

日期：2026-10-07 UTC  
状态：G023 账本对账完成；生产队列未启动；训练环境已核实。

## 环境与诊断训练

正式远端为 `DESKTOP-NNE313K`，用户 `desktop-nne313k\dell`。成功完成诊断 KRR/MLP fits 的解释器为 `N:\anaconda_envs\RCP_LCP\python.exe`（环境 `RCP_LCP`，Python 3.10.20）。PyTorch `2.5.1+cu121`，CUDA runtime `12.1`，可见设备 `NVIDIA GeForce RTX 3080`；本次 KRR/MLP 实际在 CPU 上运行。NumPy `2.2.5`、SciPy `1.15.3`、scikit-learn `1.7.1` 均成功导入。未安装依赖、升级 PyTorch 或修改 CUDA。

已有工程诊断账本记录 1 次 KRR 和 1 次 MLP 拟合，合计 2 次，均已完成；本次恢复没有追加训练。旧 Real32 记录的 Python 版本为 3.10.20，但未保存其绝对解释器路径，因此不能证明旧路径与本次路径完全相同；本次两次成功 fits 的环境路径由环境 inventory 明确记录。

## G023 与 D6_P05 对账

G023 (`K6GDP2_DEV_G023`, `attempt_001`, `K6V2_G023_20261006T144241Z_0a0cb192`) 已按 Runner closeout 凭据记录为 `FAILED_POSTENTRY_NO_TRUTH`：已消耗 1 次 entry，Runner invocation 1，自动 replay 0，无有效 truth，隔离。没有创建标签或新 attempt。

D6_P05 旧 run (`K6V2_D6P05_20261006T063951Z_c6f073e5`) 保持 `FAILED_PREENTRY_NO_ENTRY`：entry 0、invocation 0、replay 0。其后合法完成的独立 fresh run 和有效标签均保留；本次没有重跑。

G023 reconciliation 先验证原 ledger SHA `79da35c8c1fa129527c0828b954dfbcb1b9541e2fc236223c02bd47266bf05f9`，并复核 Runner registry、status、manifest、closeout claim/disposition/journal/receipt、归档锁标记和 P05 recovery。claim 同时核验 canonical body hash `7e8797b71fef3dc4a420ea56e946a3c49400e09608a9442cdd1e33a8aa64c65f` 与 claim 文件 SHA `97156447b1894558bb631cf0e3e8f28c877acd2fa5fdc07d7547c24edb5d9e83`。账本由 SHA `79da35c8…` 更新为 `10f71003aec4cdd50fcdd7b0e0bae636072c0277c736aff70dfe67803b858955`；reconciliation receipt SHA 为 `31cb24d18431028873e80b362bdfd4d37bbd1dc1e84b7cb9d1c106169f2b7bf2`。第二次调用幂等通过，账本与 receipt SHA 不变。

对账前后计数一致：entered 35、truth-valid 33、labels-valid 33、remaining 93、replay 0、training fits 0、P_scale fits 0、confirmation-response access 0。G023 从 current pointer 清除；Batch status 也清除指针并标记 `QUEUE_RECOVERY_RECONCILED_STOPPED`。下一未入场候选是 G024。

## 控制器代码与验证

Coupling 的 `serial_queue.py` 增加固定 G023 零分派 reconciliation、Runner 哈希绑定 controller manifest 参数校验、每次最多一个 case 的 allowlist 限制，以及只在 current case/ledger/Runner slot 均清空时生成安全 stop receipt。裸 `--execute` 现在拒绝运行。没有安装或启动 Task Scheduler 控制器，也没有启动生产队列。

远端 RCP_LCP 下 `py_compile` 通过，G023/controller focused tests 与既有 recovery tests 共 24 项通过。Runner Scheduler API 当前未提交 worktree 的 `task_scheduler_v1.py` 也通过编译及其专项 17 项测试；Runner worktree 仍有未提交改动，正式 handoff/owner acceptance 尚未闭合。

本次 solver entry、训练 fits、P_scale fits、自动 replay 均为 0。用户当前请求只授权定位并续接诊断训练，没有新增 HF/生产队列启动授权，因此队列停在已对账边界。
