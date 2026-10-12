# APCD_COUPLING_5NM_TIME_CONVERGENCE_DIAG2_V1

## 状态

**BLOCKED_PREENTRY**  
ENGINEERING_ADMISSION=**BLOCKED**；SCIENTIFIC_DATA=**PARTIAL**；TIME_CONVERGENCE=**UNRESOLVED**；5NM_CANONICAL_STATUS=**RETAIN_PROVISIONALLY**；V3_NUMERICAL_ADVANCEMENT=**HOLD**。

本次两次新 solver entry 均为 0，replay=0。没有新 6 ps setup/FSP、fresh LOAD proof、native H5、609D 标签或停止轨迹；因此本报告不把缺失结果描述为实验 FAIL，也不推断 3 ps 时间截断是否改变了状态。

## 依据与边界

- 现场：`DESKTOP-NNE313K` / `desktop-nne313k\dell`；Coupling worktree `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`，branch `work/mdc-np-coupling-ml-v1`，检查时 HEAD `fee0451c1a5c9924c66599cd5845d5d290fd7878`，upstream ahead/behind `0	0`。
- V3 DOE56 冻结清单 SHA-256：`f0231e22b169f82f9239d7e89c3455f877ea85d493c422274f664c9dd91ba667`。本任务两 anchor 与旧值一致：A1/G001=`[120,160,165,175,160,195] nm`；A2/G004=`[210,115,175,115,180,125] nm`。
- 现场 V3 ledger SHA-256：`9e277f111f3ba6e7399d74e730f05a1f0a69388be8e40506135b28d8ffc84367`；counts=`4 entered / 4 truth-valid / 4 labels-valid / 52 unentered / replay 0`。训练/P_scale/confirmation-response access 均为 0。此次没有写入该 ledger。
- 原数值取证报告 SHA-256：`82055e7186315beea86b82bc48e14fa5bd15ca4cc29a8c6f456ed26b28e12f17`；其结论仍是 5 nm 同合同 repeat 原生场逐位一致，但四个旧 3 ps run 均运行到时间上限而未达到 `1e-6` 自动停止；既有 4 nm 比较仍 FAIL。重复性不等于时间收敛。

## 两个 3 ps 源 setup

两份已注册 source setup 与原 5 nm 合同绑定，且其 manifest 和 FRESH_SETUP_LOAD_PROOF 哈希现场匹配。旧证明实际读回 `simulation_time_s=3e-12`、`auto_shutoff_min=1e-6`、mesh=5 nm；它们不是本任务的新 6 ps setup，也不能代替新 case 的 fresh LOAD。

| 预定 anchor | 有序 D1…D6 (nm) | 原 3 ps source `pre.fsp` SHA-256 | source manifest SHA-256 | fresh LOAD proof SHA-256 | 物理合同 SHA-256 |
|---|---|---|---|---|---|
| A1 / G001 | 120,160,165,175,160,195 | `0e6e522141ddbd0f9a4323cdc470293fd485af9493257a4ccd166383f6a62bb2` | `686f589cc47236d1b0dd7d27fb8d9ec100d557b883d4cdb3872361d3935d94ec` | `528d8b156a18cea2db65a094678a3df14003fd70f939998590b96f17250caa95` | `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` |
| A2 / G004 | 210,115,175,115,180,125 | `540ec80315bcec60619afb85f60dc894d46e40bffd87d5f8c6fb38b48a2651d1` | `5af1ae7310625054db586870751d59729ca02d261b3795c4f8a6ec9f17096a79` | `715c2c77208ef2de2af34bd0da72aae68878a1f8a1d99b5ddbc2bef57c751ac5` | `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5` |

### 允许的 3 ps → 6 ps 差异

| 属性 | 已核验原 setup | 本任务拟定值 | 本轮实际状态 |
|---|---:|---:|---|
| FDTD maximum simulation time | 3 ps | 6 ps | 没有生成/LOAD 新 setup |
| auto-shutoff threshold | `1e-6` | `1e-6` | 没有新读回证明 |
| 核心 mesh | 5 nm | 5 nm | 未变更 |
| source、材料、MDC/spacer、边界、monitor、参考面、21 λ、Floquet/TE/TM | 原合同 SHA `32e60a…` | 保持原值 | 没有新配置 diff artifact |

由于 6 ps contract 和 source FSP 未生成，不存在可报告的 6 ps contract/FSP SHA；不能以旧 3 ps SHA 冒充新配置，也未尝试直接编辑已有 FSP。

## 正式 GPU admission 阻塞

安装版本为 GPU V2/V3 `03c0125c4a6b1e9f239a694d9052cbeb3229242a`。安装 engineering acceptance 为 PASS、182 项 regression PASS/1 skipped，但其 scope 是旧注册身份/已有 reference；标记 `GPU_ENGINE_LICENSE_NOT_TESTED=true`，不是新 6 ps 入场许可。

正式身份接口 `V3_REGISTERED_BATCH_V1` 当前状态 `FROZEN_REGISTERED_NOT_LAUNCH_AUTHORITY`，绑定 DOE56 manifest `f0231e22b169f82f9239d7e89c3455f877ea85d493c422274f664c9dd91ba667` 和恰好 56 个 ID。它只接受 `APCD_COUPLING_V3_DOE56`，`V3Request` 只列出既有诊断/开发/封存角色，合同 SHA 只接受既有 canonical/4 nm mesh 合同；注册校验要求 exact-56 身份和冻结角色数。两个新 time-diagnostic 身份不在表内。把它们塞入 DOE56 会改变冻结清单/计数；复用已有 ID 会污染旧 attempt；两者都不合法。

同一 installed template 绑定的 science acceptance (`SCIENTIFIC_ADMISSION_PASS`) 也只绑定上述 DOE56 registry/hash；实际 release 文件 `SCIENCE_RELEASE_DENY.json` 的 SHA-256 为 `8f8d17cbcc7ab7552d88446bcf36d552b4ea4e2a07b2add3988a4db13a11ea8f`，其中 `science_authorized=false`、`requests=[]`。当前 `PRODUCTION_STATE.json` 为 `HOLD`。因此本任务没有新 6 ps admission/release，也没有调用 preflight、start、resume 或 solver。

## 运行状态快照

截至 `2026-10-12T04:22:40.504892Z`（UTC；服务器 CST=`2026-10-12 12:22:40`）：`APCD_GPU_V2_SERIAL_CONTROLLER` 为 Scheduler `Ready`、Enabled；last task result=1；next trigger `2026-10-12 20:00 CST`。其 action 指向 DOE56 `PLAN_SCIENCE_PASS.json`（SHA-256 `cfd2456b367899ed46a46981089ee9b33c8417e55148d07b487543de17be660a`），并非本任务两案。当前没有 serial-controller 进程或 `fdtd-engine-msmpi.exe` 科学 solver；8 个较早创建的 `fdtd-solutions.exe -server -hide` API 进程保留原状，未触碰。现有 controller plan 的数值 gate fail-closed：冻结评估器不产生 `advance_to_development=true` 时会以 `FROZEN_NUMERICAL_GATE_HOLD` 拦住 DOE56 后续阶段；这不能代替新增两案的独立 release。

本任务执行计数：新 FDTD entry=0；新 solver invocation=0；replay=0；native LOAD=0；新 truth/labels=0；training/P_scale fits=0；sealed/confirmation response access=0。原 DOE56 ledger 保持 4/4/4/52、replay=0。

## 结果与判定

- 两个 6 ps 案的实际停止时间、停止原因、auto-shutoff 曲线、末端场、FSP/H5、609D 标签、GPU wall time：**均 N/A，因未入场**。
- 3 ps 基准可从旧正式取证复核：A1 FDTD wall 548.960819 s、end-to-end 703.763606 s；A2 FDTD wall 544.070146 s、end-to-end 699.353218 s。对应旧 5 nm repeat 是独立 entry，且 native H5/raw payload 与其历史 3 ps 对照逐位一致；这只支持该执行条件下 repeatability。
- 本任务没有合法的 3 ps vs 6 ps 配对输出，故 state、阶次振幅/相位、强 TM、routing、P_scale、absolute-order、total-power 差异均未计算。禁止将缺失结果解释为零差异或 gate PASS。
- 原 4 nm A1/A2 FAIL（state 0.1303/0.1925，routing 0.0450/0.1166，total-power 0.1605/0.3221）保持不变。

结论：`TIME_CONVERGENCE_UNRESOLVED`。5 nm 保留为当前 canonical 候选（`RETAIN_PROVISIONALLY`），但现有证据不证明 3 ps 时间稳定性；空间网格门也未通过。V3 剩余 DOE56 52 案继续 `HOLD`，本任务不改变生产数据或 authority。

## 下一步唯一前置

GPU V2/V3 Owner 需通过正式的独立身份注册、consumer 回归测试和受控 release，为两个 `TIME_CONVERGENCE_DIAGNOSTIC_ONLY` 新 attempt 建立与 DOE56 隔离的 case/contract/request/预算绑定，并明确唯一允许的 3 ps→6 ps 字段差异。Owner 正式交付可验证的 admission/release、case IDs、request 和版本 SHA 后，再从全新 pre-entry 核查开始；不复用 DOE56 entry 计数、不解除 52 案 HOLD。Scheduler 当前任务仍 Enabled，须由 owner 按正式状态协调；本任务未更改它。

## Git 与证据

- 报告、continuation 和本 SHA inventory 均为本任务新建文件；没有修改 Runner、Scheduler、release、账本、156G truth/labels、H1/H2 或 sealed data。
- 当前证据路径及完整 SHA 见同目录 `SHA_INVENTORY.json`。基线 V3 forensic 与 DOE56 authority 保持原样。
