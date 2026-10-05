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
