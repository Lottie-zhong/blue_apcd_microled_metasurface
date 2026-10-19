# DIAG2 V3.1 预算迁移与 AL 交接

任务：APCD_COUPLING_DIAG2_V3_1_BUDGET_MIGRATION_AND_AL_HANDOFF_V1

**DIAG2_V3_1_MIGRATION_HOLD**。本轮真实 entry / FDTD / ML fits / replay / sealed 响应访问均为0。

## 1. 原预算承接

科学预算语义明确：沿用原A1/A2、原batch、各attempt_001、各最多1entry，总上限2，历史0/2。用户已原则同意承接，无需再申请新增“两条预算”。当前仅生成不可执行的迁移审查记录；没有激活Admission、生产账本或V3.1任务。

|六项门禁|结果|
|---|---|
|原预算及科学身份|PASS|
|V2.1/V3.1 Entry对账及不可变job/attempt迁移绑定|PARTIAL|
|physics_contract_sha|PASS|
|原FSP与6ps输入合同|PASS|
|原生E/H→H5→609D及V3.1接线|PARTIAL|
|资源、No Replay及Runner缺陷|BLOCKED|

81个发现数据库只读检查无DIAG2匹配或读取错误；V2.1正式账本仍94条历史任务。但这不替代未来唯一科学job注册、原预算单一所有权及执行标签映射。Runner生成的attempt只能是原科学attempt下的执行标签，不能替换原身份。

## 2. 科学合同

16项source/setup SHA全部匹配。冻结合同SHA：51212d0c69f2112add3ee4008eb51a8aa94e380c39624d93d31e5f75e7be0e36。仅最大物理时间3→6ps；5nm、auto-shutoff1e-6及结构/材料/源/监视器/21波长/609D/参考面不变。调度墙钟时间不等于FDTD物理时间。

未闭合：真实6ps时间收敛与4/5nm数值可信度，以及未来AL制造/精度合同。DIAG2_6PS_TRUTH_VALIDATION=NOT_RUN。

## 3. 原生提取

本轮新完成合法历史G001/G004只读LOAD重提取：原生FSP/H5→完整复E/H→冻结后处理→raw/state/truth H5→原importer→609D。两例C_hat、P_scale、eta、absolute_order与冻结标签最大差均为**0**。保留原身份，隔离输出，session已关闭；未调用run/save/layout，未重新科学入场。

既有helper模块搜索路径问题已在任务加载路径内修复，公式及冻结源码不变。迁移guard **14/14 PASS**；既有6ps resolver **6/6 PASS**；未全量回归。V3.1实际求解后FSP/native H5配对、原身份sidecar及DIAG2停止证据接线仍未证明，不能据历史parity签发6ps有效真值。

## 4. Runner阻塞

安装仍为原审计版本。复用最小复现证据，不重跑FakeBackend：错误input SHA被接受、跨batch同输入可再次注册、NoReplay仅按job_id、run出现failed仍exit0。科学身份/预算防重由Coupling补齐，不能把COMPLETED视为labels-valid。

新快照为0%利用率/1805MiB；WDDM多个消费者显存N/A，含EDT。不能证明外部资源独占与owner/fencing，继续HOLD。仅向维护线程投递Runner缺陷证据；无修复回传，且此前线程因应用invalid message ID失败。没有修改Runner、安装态、Scheduler或生产SQLite。科学合同/FSP/Manifest/原生提取/609D/AL仍由Coupling负责。

## 5. AL交接

保留156G、old32 train-only、new124 grouped CV及所有既有模型比较，本轮重训0。8192池与16案CSV对应行一致，D1…D6顺序保留；与当前核验263个受保护几何无冲突，含历史/已入场/失败、DOE56、DIAG2及sealed几何元数据。未读取sealed响应。来源CSV/NPZ/生成脚本已记录文件SHA。

16案是有效研究提案，**尚不可生产准入**：制造Authority仍UNRESOLVED，物理不重叠不能替代制造批准；完整活跃队列排重仍须唯一科学job注册。保留8覆盖/4分歧/4分层随机；当前η/P+排序不可靠，不以预测最高效率单独选样。

## 6. 首轮新增数据建议

先用原2案关闭DIAG2，再冻结未来精度和制造合同。若有系统性数值偏差，保留旧156G原fidelity，不无标记混合3ps/6ps标签。之后另行申请首批**16个AL新entry**，1/case，失败消耗预算且不得自动重跑；最多新增16个labels-valid几何（156→最多172）。当前AL新增授权0，DIAG2诊断数据不自动入ML。

6ps尚无实测；按历史5nm/3ps约9.4min线性规划约19min solver/案，16案暂留8GPU小时计划余量，不含排队，不是耗时保证；无费率，不报货币成本。

## 7. 下次真实执行门禁

六门全部PASS：原预算唯一承接与跨版本对账；不可变科学身份↔Runner job/attempt映射；原合同/source/setup；外部资源owner/fencing与输入完整性；原生FSP/H5配对、只读609D和停止时间/阈值证据；A1科学验收后才推进A2。entered失败只做truth-only恢复，不重放。本轮即使随后门禁闭合也不启动，等待后续明确启动任务。

DIAG2仍0/2；DOE56仍4entered/52HOLD。Git：work/mdc-np-coupling-ml-v1；HEAD 2cc687020e90ec4397e6cd4ed31efed59aaaf386；ahead/behind0/0；953项dirty，原4项staged保留；未提交或推送。

完整技术证据见APPENDIX_TECHNICAL_REPORT.md、SIX_GATE_VERDICT.json、HISTORICAL_NATIVE_REEXTRACTION.json、AL16_HANDOFF_AUDIT.json、SHA_INVENTORY.json、FINAL_AUDIT.json及CONTINUATION.md。
