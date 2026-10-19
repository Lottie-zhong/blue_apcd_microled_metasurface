# APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1

**DIAG2_V3_1_MIGRATION_HOLD** — ZERO-SOLVER.

## 1. 原预算能否承接 V3.1

科学语义可无歧义承接：沿用原 batch K6V3_TIME_DIAG2_V1_BATCH_001、dataset APCD_COUPLING_V3_TIME_DIAG2_V1、原A1/A2、各attempt_001、各最多1entry、总上限2，历史0/2。用户本轮已原则同意，无需重复申请新增“两条预算”。当前任务授权真实执行仍为0；正式执行迁移尚未闭环。BUDGET_MIGRATION_REVIEW_RECORD.json 是不可执行审查记录，不是ScienceAdmission或生产账本。

## 2. 六项门禁

|门禁|结果|关键证据|
|---|---|---|
|1. Original budget/science identity|PASS|User principle carryover approved; original A1/A2 attempt_001,1entry/case,total2;newbudget0; exact original batch/dataset retained. Not execution authority.|
|2. V2.1/V3.1 entry reconciliation and immutable job mapping|PARTIAL|81 discovered DBs read-only;0DIAG2 matches/errors; historical0/2 retained; no live V3.1 job/attempt binding or single-owner budget handover transaction has been activated. No production ledger created.|
|3. physics_contract_sha|PASS|51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36|
|4. Original FSP and6ps input semantics|PASS|16source/setup pins match; frozen load-readback proof retained; only3ps→6ps maximum physical time,auto-shutoff1e-6 unchanged. No scheduler/physical-time conflation.|
|5. Native E/H→H5→609D|PARTIAL|Fresh read-only re-extraction of historical G001/G004 nativeFSP/H5, fullcomplexE/H,raw/state/truthH5, frozenimporter609D and label parity PASS.6ps resolver6tests PASS. V3.1 postsolve outputFSP/nativeH5 pair capture, immutable authorized sidecar and DIAG2 time telemetry integration are not yet proven; no6ps truth exists.|
|6. V3.1 resources/No Replay/reported defects|BLOCKED|Installed runner unchanged; prior isolated wrongSHA and crossbatchduplicate acceptance remain relevant. Local mutex cannot prove externalownership; freshWDDM snapshot0%/1805MiB withN/A consumers. CLIrun failed>0 returns0. ScienceID mapping and nativepair durability require failclosed bridge; RunnerCOMPLETED notlabelsvalid.|

不得把旧attempt重新命名为Runner生成的attempt；后者只能作为原科学身份下的执行标签。V2.1没有DIAG2生产登记的证据，不需要删除历史记录；V3.1任意cwd可建独立数据库，因此81库零匹配不替代未来唯一登记的科学job映射和单一预算所有权。

## 3. 尚未闭合的科学合同及原生提取

已闭合：5nm/6ps输入合同身份、原source/setup、auto-shutoff1e-6、21波长、TE/TM、m=-3…3、1722nm参考面及既有609D/H1/H2。physics_contract_sha=51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36。16项当前source/setup检查匹配冻结值，未替换expectedSHA。

未闭合：真实6ps时间收敛、4/5nm数值可信度；未来AL制造/精度合同；V3.1真实输出FSP与nativeH5持久配对、原科学身份sidecar和DIAG2停止时间/阈值证据接线。6ps是FDTD物理最大时间，与调度墙钟时间不同。

本轮从合法历史G001/G004原生FSP/H5新做只读LOAD→完整复E/H→原冻结后处理→raw/state/truthH5→原importer→609D。原case/attempt保留，新生成文件仅在任务隔离目录；不重新科学入场、不入新训练集、不改生产账本。下面是与冻结标签的最大绝对差：

|历史case|C_hat|P_scale|eta|absolute_order|
|---|---:|---:|---:|---:|
|K6GDP2_DEV_G001|0|0|0|0|
|K6GDP2_DEV_G004|0|0|0|0|

原生session只允许绑定FSP的LOAD和只读命令，run/save/layout禁用，结束关闭本次session。首次LOAD-only因模块搜索路径缺少项目已有incident-power helper而失败，已仅在任务加载路径中补齐原实现，保留失败证据；未改公式、冻结源或哈希。原生历史提取PASS不等于V3.1/6ps真值PASS。DIAG2_6PS_TRUTH_VALIDATION=NOT_RUN。6ps resolver定向6/6PASS，迁移guard14/14PASS；未全量回归。

## 4. Runner真实阻塞

安装SHA仍为9d380e62f265cb7ca3d4398a9831dd8358362223d09fc5476a436b4f2582be33，未发现修复安装。复用上一轮最小FakeBackend证据，不新增fakeentry：错误inputSHA被接受、同输入可跨batch再次注册、NoReplay仅按job_id、run CLI失败数大于0仍exit0。case/预算层属于Coupling职责，不能把通用Runner的job_id当作科学NoReplay。

资源快照：RTX3080利用率0%、显存1805MiB；WDDM多个图形/远控进程显存N/A，包括EDT上下文。0%和N/A均不是独占证据。本Runner文件锁没有覆盖外部GPU消费者；不终止或接管外部进程。当前独立owner/fencing未通过，因此保持HOLD。

平台维护只接收Runner资源、保存/输入完整性与CLI错误语义的最小证据；科学合同、FSP、Manifest、H5/609D和AL仍由Coupling-ML Codex负责。上一轮维护线程消息工具接收成功，但线程因应用invalid message ID报错，尚无修复回传，不能报告已修复。未修改任何Runner源码、安装态、Scheduler或生产SQLite。

## 5. AL资产与16案结论

156G合法开发集核验通过；old32 train-only，new124 geometry-grouped CV保持。原268-fit、479-fit和104-fit模型比较及KRR/GPR/MLP/ExtraTrees证据保留，本轮新fits=0。8192池与16案CSV对应行逐值一致；未排序或置换D1…D6。

16案唯一；与263个当前已核验受保护有序几何无冲突，包含历史/已入场/失败登记、DOE56全部保留几何、DIAG2和sealed几何元数据；未读sealed响应。最小提案间距离0.4551（D/130nm）。来源CSV、池NPZ、生成脚本已按既有SHA256文件规则记录，不新造canonical哈希。

结论：16案是有效、已知来源内无冲突的研究提案；不是有效生产准入。正式manufacturing authority仍明确UNRESOLVED，旧几何域只允许冻结池扩展，不能凭100–230nm/5nm网格和不重叠自动批准整个Cartesian空间。完整活跃队列排重也需唯一科学job注册。现有模型η/P+排序不可靠，保留8覆盖/4分歧/4分层随机探索，不以最高预测效率单独选样。

## 6. 第一轮数据与预算建议

优先完成原2案DIAG2数值诊断，比较3ps/6ps和停止阈值；结果若显示系统性标签问题，先冻结统一未来精度，保留旧156G的原fidelity，不直接扩充旧3ps集、不把不同精度无标记混合。DIAG2诊断数据不自动进入ML。

数值与制造合同闭合后，再独立申请16个AL新entry，1/case、失败消耗预算、entered禁止自动重跑；最多新增16个labels-valid几何（156→最多172），不是预先授权250/500/1000。只有truth-valid与labels-valid均通过的新几何可入版本化HF库。当前16案预算授权0。历史5nm/3ps约9.4min solver/案；6ps仅线性规划约19min，尚无实测，16案暂留8GPU小时计划余量，不含排队；无费率，不报货币成本。

## 7. 下次真实执行前的最终门禁

必须全部通过：原2身份及预算唯一承接；V2/V3历史对账与不可变job/attempt绑定；原SHA和source/setup复核；独立外部资源owner/fencing及输入完整性；V3.1输出原生FSP/H5完整配对、只读E/H/609D与停止时间/阈值证据；A1完成科学验收后才推进A2。任何entered失败只做truth-only恢复，不重新提交求解。所有六门PASS后仍遵守本轮绝对零求解，等待后续明确启动任务。

## Git与交付

正式分支work/mdc-np-coupling-ml-v1；HEAD2cc687020e90ec4397e6cd4ed31efed59aaaf386；ahead/behind0/0。未提交、未推送。保留原950项dirty状态和4项历史staged；任务仅增加自有guard/audit及报告文件，并追加AGENTS最新权威指针。FINAL_AUDIT.json记录最终状态。

关键文件：SIX_GATE_VERDICT.json、BUDGET_MIGRATION_REVIEW_RECORD.json、ENTRY_RECONCILIATION.json、CONTRACT_SOURCE_AUDIT.json、HISTORICAL_NATIVE_REEXTRACTION.json、AL16_HANDOFF_AUDIT.json、POSTSOLVE_BINDING_PLAN.json、RUNNER_DEFECT_EVIDENCE.json、NEXT_ROUND_BUDGET_RECOMMENDATION.json、SHA_INVENTORY.json、CONTINUATION.md。

本轮：0新增真实entry、0FDTD、0FMM/RCWA、0新ML fits、0replay、0sealed响应、0生产账本写入；DIAG2仍0/2、DOE56仍4entered/52HOLD。
