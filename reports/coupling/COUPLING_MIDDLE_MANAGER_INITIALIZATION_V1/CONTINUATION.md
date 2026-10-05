# 主控续接：事件驱动模式

恢复时先读 MANAGEMENT_RECORD_V1.json 和 UPPER_HANDOFF_V1.md，再读执行方自己维护的任务 continuation、账本和正式产物。此管理目录是索引，不创建科学或执行authority。

## 当前管理规则

本规则由 COUPLING_MIDDLE_MANAGER_EVENT_DRIVEN_CORRECTION_V1 修订，时间 2026-10-04 17:47:17 UTC；取代任何要求主控每10分钟轮询或收集heartbeat的旧规定。主控不定期查询线程、进程、日志或输出目录，不因普通等待发送状态询问，不新增计时器或监控服务。普通运行进度由执行方写入自身账本与continuation。

GPU负责Runner平台、GPU资源、单槽串行执行和truth持久化；耦合ML负责truth接入、标签校验和已授权后处理。GPU到ML的正式case handoff直接继续，主控不逐案转发或收集普通case消息。

主控只在下列事件接收回传：首案durable truth并通过ML接入验收（这是GPU继续余下127案的交接闸门）；128案完成并给出计数、产物和哈希；合同范围内无法解决的阻塞；科学协议冲突、预算问题或需要上层决策的事项。首案PASS后GPU按现有授权自动继续，不逐案等待主控批准。收到事件后主控核验交付证据，合同内工程修正可直接分派；科学路线、额外预算、确认集或正式训练决定返回用户。

## 当前活动任务

任务ID：COUPLING_K6_V2_128_DEVELOPMENT_CASES_GENERATION_V1。

范围仅限冻结V2的128个新增开发case：12个局部轴向点和116个全域点。预算最多128次solver entry、每案attempt_001最多一次、post-entry自动重放为0；32个确认case solver预算为0，真实training fits为0。执行使用GPU Production Runner V1单槽串行，不恢复旧Shared V3三槽调度。不得改变点集、monitor、H1/H2或模型方案；不追加EXT02求解。局部网格/PML和制造authority缺口仍为已知限制。

执行方已接单：GPU会话01a0ed0c-691b-7043-9c32-0454eef069e1正在原任务中推进；耦合ML会话01a10024-ea88-7561-bde3-852a10a08966等待GPU正式handoff的首份开发truth。GPU最近一次回传为当前route preflight PASS、entry=0，下一步是fresh launch revalidation；这是主控最后已知的状态快照，主控之后不自行查询。GPU和ML各已收到一次本管理规则修正，ML确认并更新了自己的continuation，GPU修正消息发至正在运行的既有线程，待其安全消息边界确认。此修正不重启或中断任务。

预算authority快照：Runner commit 2b6c4d7c06c10caf3337909ea908e55b8b1965c8；budget SHA256 e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c；authority SHA256 a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35。EXT02已完成的单案例跨高度比较来自commit 23dd330c0da4a1de4fef3a685a4f4a165fa3dede：报告SHA256 b1ae6ad04d5b50ca9daae07edd7411ea6fc8e4509403729654d636512c7b9c0a，数值JSON SHA256 c0a37527498857522347bfcb39307fab21779f412cb124771b59ad9982669a9f。其支持单案例跨高度一致性，不代表全域标签、绝对收敛或跨run重复性。

十分钟heartbeat自动化 v2-128-truth 已暂停；没有新增监控器、定时器或轮询脚本。恢复本任务时等待执行方按上述事件回传，不在普通等待中查询。


## 2026-10-05 — 首案标签归一化冲突，等待上层决定

首案 K6LDA1_DEV_D1_M05 / attempt_001（DEVELOPMENT_LOCAL_AXIS，run K6V2_D1M05_20261004T175055Z_449c4f94）已完成 Runner 执行：DONE、fresh LOAD、SCIENTIFIC_VALID、truth-before-DONE 屏障通过，run-one 返回码0。Runner 原始 truth 持久化并通过其自身验证，但 Coupling 冻结 importer 因 source_fraction = P_scale × eta 检查拒绝接入。首案隔离，原始 truth 未改写。

预算对账：冻结包160案，128开发案中仅此案1次 entry，余下127案0 entry；其余32个非开发/确认案0 entry；真实training fits=0，post-entry replay=0。GPU和Coupling已收到主控保持隔离/只读诊断的指令。当前不得启动余下案件，也不得改Runner公式、生成替代权威标签或覆盖原始truth。

独立复算依据：
- Runner scripts/shared_fdtd/tools/pw_scientific_launcher.py:437-457,502-514 中，grating() 的各阶分数被乘以 t_fdtd = ptrans/pin；其中 post_plus 来自输出面 Ex/Hy 空间平均，表示零阶模态代理量。Ansys官方 grating 文档说明各阶值相对总透射功率归一化、阶和为1；转为sourcepower分数时应乘 transmission(monitor)。这与当前零阶代理不同，且不能把不同入射功率分母直接视为等价。
- Coupling冻结 scripts/coupling_ml/k6_v2_pipeline/ingest.py:201-208 用POSTNP完整E/H梯形Poynting积分、单元面积及IN_REF入射功率密度定义 P_scale，并要求 source_fraction = P_scale × eta，容差 rtol=1e-3, atol=1e-9。
- 对21个波长按冻结公式复算，eta逐波长和偏差最大2.22e-16；P_scale范围0.0664912–0.562037。440 nm时Runner source fraction总和0.0158773，冻结 P_scale=0.0769179。最大绝对不一致0.169494，最大相对不一致0.991849（449 nm，order x=-1）。冻结检查失败。

原始产物位置：D:/apcd_runtime/gpu_production_runner_v1/runs/K6LDA1_DEV_D1_M05/attempt_001/K6V2_D1M05_20261004T175055Z_449c4f94。验证通过的Runner truth H5 SHA256 a51d5179...e7db1da64；run FSP f2258b74...8be4fb2b9；run_output H5 8aa4ca58...af298dcd。不可变输入：raw complex fields NPZ 987756dd...53d8caac；orders JSON eee74666...571bff158；raw metadata JSON 245d37f2...fd624afa。完整SHA与入场账本见 MANAGEMENT_RECORD_V1.json。

需要上层裁定：是否授权对这一个已完成case做版本化、零solver的补充派生记录，严格使用既有冻结等式 source_fraction=P_scale×eta 并保留原始truth/拒绝记录；以及是否允许按同一冻结定义修正Runner生产映射后，在首案重新通过Coupling验收时续跑其余127案。此建议不改变物理标签定义、阈值、点集或预算。Ansys依据：https://optics.ansys.com/hc/en-us/articles/360034927213-grating-Script-command。

## 2026-10-05 — COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1 已授权接续

上层裁定授权对首案做零solver功率归一化独立核验、版本化补充标签及Runner生产映射修复；满足物理核验、补充标签、生产映射回归和实时启动前authority/预算/owner/fence检查后，GPU可直接串行续跑剩余127个开发case。

**任务合同**
- 目标：明确并闭合首案 K6LDA1_DEV_D1_M05 / attempt_001 的功率分母与映射问题；保护原始truth/拒绝记录；仅在全部门槛通过后恢复余下开发案。
- 输入authority：本次用户上层裁定、冻结V2物理合同、首案归档FSP/H5/raw及Runner/Coupling代码，旧32G与EXT02正式产物。
- 范围：GPU只对归档FSP做LOAD-only读取，修复被证实的零阶/总透射映射错误并做真实fixture与非零衍射阶回归；Coupling独立计算E/H面积功率、模态功率、IN_REF及分母转换，生成显式opt-in版本化标签，并只审计实际受影响的32G/EXT02派生字段。
- 预算：本阶段新增solver=0；首案已用1次entry且绝不重跑；总上限128开发案、每案最多1次entry，余下最多127次；post-entry自动重放=0；确认32案=0；真实training fits=0；额外诊断solver=0。
- 执行方：GPU Codex（归档读取、Runner映射、回归、门槛后单槽串行续跑）；Coupling ML Codex（物理定义、独立核验、版本化补充标签、历史受影响字段审计）；主控统一收件核验和汇总。
- 验收：eta分子/分母/方向/阶次、P_scale、IN_REF入射功率、Runner source_fraction分母及sourcepower/POSTNP总通量/零阶模态/正向和净功率均有证据定义；各逐波长独立对照达到冻结阈值，不用P_scale × eta代数关系替代物理核验，不拟合换算；原始输入与拒绝记录不变；补充标签绑定全部SHA、代码版本、公式、分母、结果和被替代字段，消费者显式选择；生产回归含非零阶、分母差异和首案真实fixture；仅修复确实受影响的历史派生量；启动前authority门槛实时有效。
- 阻塞：关键物理量或冻结验收阈值缺失、独立物理核验失败、冻结定义/分母存在实质冲突、标签系统异常、当前owner/fence/authority失效，或需要新增预算。发生时暂停依赖问题的新entry并回传证据。
- 回传：GPU与Coupling ML分别回到主控会话 01a10791-e5f1-7150-ae43-700a1bb48305；完成、合同内无法解决的阻塞、需上层决定或首案续跑门槛事件时回传。主控统一向用户汇总。

**接单确认与当前状态**
GPU会话 01a0ed0c-691b-7043-9c32-0454eef069e1 和Coupling ML会话 01a10024-ea88-7561-bde3-852a10a08966 均已通过原生 send_message_to_thread 收到本任务消息；2026-10-05 wait_threads返回两线程active并含任务范围确认。GPU确认检查期间未启动FDTD、未改控制库或归档；Coupling确认只做独立物理核验、不会运行solver或训练。此为接单/开始确认，不是完成报告。

**等待事件**
GPU正在核实生产route实际backend映射及归档monitor LOAD-only提取器；Coupling正在核对冻结定义、归档E/H与模态/投影数据和物理阈值。主控不轮询进度。首案完整通过上述验收后，GPU按授权直接恢复余下127案；否则保持相关新entry暂停并回传具体差异。

## 2026-10-05 — 上层接受EXT02并冻结生产monitor

上层接受EXT02单案例跨高度一致性结果。当前生产配置保留近面实际z约1802 nm、距NP顶面约90 nm；剩余开发案沿用该配置，不移动monitor、不逐案新增第二面、不追加诊断solver。EXT02继续排除训练集。该结论不外推至任意几何或距离，也不代替当前任务的独立功率核验、首案版本化标签验收、Runner生产映射修复与回归、实时authority/预算/owner/fence/启动核验。

所有门槛通过后，按既有128案授权单槽串行续跑剩余127案，无需再次请示；每案最多一次entry、自动重放为0，确认32案和真实训练预算均为0。后续逐案保持原标签与物理验收；系统性异常时暂停受影响的新entry并回传证据。端点闭合、实际mesh及PML内边界读数缺失仍作为诊断限制，不扩展成monitor优化或收敛研究。

本裁定已通过原生跨任务消息各通知GPU与Coupling ML，任务ID保持 COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1；不触发solver或重做EXT02。

## 2026-10-05 — Stage execution ownership reorganization

Task `COUPLING_TWO_AGENT_STAGE_EXECUTION_REORGANIZATION_V1` supersedes earlier continuation wording that assigned long-stage K6 database queue ownership to GPU.

- Coupling ML is the sole K6 V2 stage executor and owns the development queue, case ledger, truth intake, label checks and authorized post-processing. It directly invokes the existing single official GPU Production Runner V1 after the repair and startup gates pass.
- GPU Codex is an on-demand Runner/platform maintainer. It owns Runner/platform implementation and its official code changes, but does not manage the Coupling case queue. The already-assigned zero-solver power-normalization repair remains with GPU until it returns completion or a concrete blocker.
- The manager owns stage contracts, the separate manager worktree records, version selection evidence and stage-level acceptance. It does not poll routine progress or forward each case.
- Coupling ML accepted queue ownership and returned a one-time live ledger/lock audit. GPU acknowledged the on-demand platform-maintainer role on its existing thread and confirmed that the same zero-solver repair continues. This record adds no execution authority.
- The frozen case set remains 128 (12 local-axis plus 116 global), with one maximum entry per case and zero replay. One entry is already consumed by `K6LDA1_DEV_D1_M05 / attempt_001`; at most 127 remain. Confirmation32, real training fits and extra diagnostic solver entries remain zero.
- Keep the accepted near monitor at actual z approximately 1802 nm, about 90 nm above the NP top; do not move it, add per-case second planes, or run another diagnostic. EXT02 stays out of training. Endpoint closure, actual mesh and PML-inner-boundary gaps remain recorded limitations.
- Current blocker/gate: first-case independent power verification, versioned label acceptance, tested production mapping repair and live authority/budget/owner/fence/startup checks. Until all pass, the 127 later entries remain paused. After they pass, Coupling ML continues under the existing authorization without another per-case approval.
- Next return to the manager is GPU role acknowledgment, repair completion, or concrete blocker; after recovery, report at the explicit first-case gate, full-stage completion, or a blocker requiring action. No periodic status requests.

Version manifest: `reports/coupling/COUPLING_TWO_AGENT_STAGE_EXECUTION_REORGANIZATION_V1/STAGE_VERSION_MANIFEST_V1.json`.


## 2026-10-05 — 上层接受功率映射证据并授权恢复



上层已接受首案归档E/H独立功率映射核验、Coupling版本化补充标签接入以及Runner/Coupling相关回归。模态总和最大相对残差 2.8956697877272297e-4、逐阶最大相对残差 1.499059534294761e-3 仅作为已测量但无预注册判据的诊断限制；不标记物理闭合PASS、不套H1、不追认阈值，且不阻塞本轮数据生成。



采用Coupling HEAD `3c9c3b540c6b88d5c964245f37b5017397e68bea` 和Runner HEAD `02ad6b4b5f47b247f384fc132af329cc05612327`。正式预算overlay SHA `e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c`；route authority SHA `a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35`，其 `k6_v2_development_solver_budget.path/sha256` 已现场核对指向并匹配该overlay；production policy SHA `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45`。当前采用版本、冻结点集/合同/monitor/mesh哈希、首案与runtime ledger快照、执行owner和预算均记录于 `../COUPLING_TWO_AGENT_STAGE_EXECUTION_REORGANIZATION_V1/STAGE_VERSION_MANIFEST_V1.json`（SHA256 `95d498f175253e22fdfd87c5c704d64cd81ee4eaecdb65b8a8e42be5e8851779`）。此版本记录不代替Coupling ML的实时启动前核验。



权限保持128个冻结开发case总上限，首案既有entry=1，剩余最多127；attempt_001每案最多一次、post-entry自动重放=0、确认32案entry=0、真实training fits=0。第一案不重跑；monitor保持实际z约1802 nm；EXT02不进训练；queue21消费者继续隔离。每案保留直接E/H功率、sourcepower与IN_REF分母、总量和逐阶模态功率及残差定义/数值；无预注册门槛的模态残差不单独触发隔离或重跑。



已向现有Coupling ML会话 `01a10024-ea88-7561-bde3-852a10a08966`（host `local`）通过原生 `send_message_to_thread` 发送同一任务ID的恢复续接，要求其独立进行新鲜route/overlay、owner/fence、control/hold、ledger及下一案正式launch revalidation；全部通过后直接单槽串行恢复127案。此消息没有启动solver。下一次主控回传只期待实时启动核验通过且生产恢复、具体阻塞，或阶段完成；不收集普通进度。


## 2026-10-05 — next-case route-bound proof revalidation

The upper decision has accepted the first-case archived E/H power-mapping verification, the versioned Coupling label intake and the Runner/Coupling regressions. The modal-total maximum relative residual `2.8956697877272297e-4` and per-order maximum relative residual `1.499059534294761e-3` remain measured diagnostics without a preregistered criterion; they are not physical-closure PASS, do not borrow H1, and do not block generation. Adopted versions and the route-bound formal budget overlay remain as recorded in the stage version manifest.

The next frozen case is `K6LDA1_DEV_D1_P05 / attempt_001`. Its existing `source_manifest.json`, `pre_entry_setup_load_proof.json`, `formal_preflight_envelope.json`, and `formal_preflight_result.json` are bound to old route SHA `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`, while the adopted current route SHA is `a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35`. The formal budget overlay remains SHA `e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c` and is route-bound. Existing proof artifact SHA256 values are recorded in `MANAGEMENT_RECORD_V1.json`.

Coupling ML reported this stale route binding and acknowledged the supported official LOAD-only regeneration path; at the latest return it was checking the official atomic/versioned entry before regenerating. No next-case solver entry has been triggered. Preserve the old proof files and hashes. Do not hand-edit hash fields or change setup-only geometry authority, budget overlay, contracts, or geometry. Keep the next entry paused until current-route LOAD-only proof regeneration and formal launch revalidation pass; then resume the already authorized remaining 127 cases. Confirmation32 entries, real training fits and post-entry replay remain zero.

Manager handling remains event-driven. The next report is current-route formal preflight PASS with production restored, a concrete blocker, or full stage completion.


## 2026-10-05 — serial batch continuation

The existing Coupling ML task accepted the serial-batch supplement on its current thread; no second phase was dispatched. It reused the adopted Runner/Coupling versions, route-bound budget overlay, setup FSPs, accepted mapping repair, and frozen importer.

The latest read-only K6 Runner registry contains exactly three K6 rows, all `DONE`: `K6LDA1_DEV_D1_M05`, `K6LDA1_DEV_D1_P05`, and `K6LDA1_DEV_D2_M05`. Coupling reported all three as one-entry cases with valid durable truth and labels PASS. At the recorded snapshot, 125 of the frozen 128 remain unentered; confirmation32, training, P_scale fits, and post-entry replay remain zero. One `GPU_RESOURCE_NAME_REQUIRED` pre-entry CLI failure for D1_P05 created no run directory and consumed no entry.

Batch artifact `BATCH_PREPARATION_STATUS_V1.json` (SHA256 `551c5ff6fca09d972fada009d4f02e91502a46ec9e9c6869cd4fe6ed3d58856a`) lists the 125 frozen unentered IDs and reports current-route LOAD/preflight PASS for global sequence indices 4–19 (16 cases), with zero solver invocations during preparation. The first unentered case `K6LDA1_DEV_D2_P05` at sequence 4 is PASS, with its current-route proof and official preflight hashes in the artifact. Its final launch-time lock/hold/GPU check must still be refreshed before run-one. The status JSON lacks an explicit `current_case`; an earlier Coupling chat status named sequence 10 / D6_P05, inconsistent with the later status file. Do not record an inferred current case as fact.

Coupling reports the formal runner exposes only the official single-case `adapter.py run-one`, not a native multi-case command; it planned a thin Coupling-owned serial controller. The manager instructed it to preserve the in-progress LOAD-only preparation, then start the authorized queue at the first frozen unentered case after its final live checks, rather than require all 125 case proofs before the first entry. Reuse passed proofs and refresh later cases just-in-time. Automatic queue execution had not started at the last verified snapshot.

Next manager return: actual automatic queue start with verified counts/current case, a concrete blocker, or stage completion. No periodic polling.
