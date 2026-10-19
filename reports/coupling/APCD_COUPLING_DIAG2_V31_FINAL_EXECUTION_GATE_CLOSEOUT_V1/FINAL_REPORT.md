# APCD_COUPLING_DIAG2_V31_FINAL_EXECUTION_GATE_CLOSEOUT_V1

|剩余门禁|裁决|证据|
|---|---|---|
|SCIENCE_IDENTITY_JOB_BINDING|HOLD|隔离映射/共享原预算WAL/entry-before-launch/双向禁重放/崩溃对账11项PASS；单job执行子批次4项PASS。正式生产DB/Job/Entry绑定尚未激活，新旧入口共享排他仍缺独立证明。|
|NATIVE_FSP_H5_609D_PIPELINE|PASS|新Runner输出布局到冻结importer的7项定向联验PASS；使用合法G001历史原生字节控制，fresh LOAD复E/H、H5配对、609D与标签SHA通过。不是6ps物理真值。|
|INDEPENDENT_GPU_RESOURCE_GATE|HOLD|安装Runner仍原9d380e62…版本，无维护者实际修复/共享资源独立验收回传；旧Cross-process Mutex证据不能替代全局排他。|

**DIAG2_ENTRY=0/2；DOE56=HOLD；AL16=NOT_AUTHORIZED；NEW_FDTD=0；REPLAY=0。**

## 已关闭的本轮接口问题

1. 复用现成Diag2Budget及其原子WAL/writer lock，不重新实现预算平台。原Science ID（dataset/case/attempt）、2条总预算、每案1条、原physics/source SHA均保留。测试分别验证V3.1先消费后V2拒绝、V2先消费后V3.1拒绝；receipt已落盘而JSON未更新时仍禁止重放并保守对账。全部写入仅在标记identity_fixture的隔离目录，非生产科学入场。
2. V3.1 run会连续处理batch全部pending jobs。已准备两个各1job的执行子批次，仍属于原科学batch/原A1/A2，不是第三个科学身份或新额度。这样正式入口可在A1科学验收后才运行A2；候选manifest未提交生产。
3. 直接改名历史FSP会丢失外部E/H查找。已在Coupling侧增加基于声明原生名称的字节一致只读视图：原Runner命名FSP/H5先做配对/SHA/有限E/H检查，再LOAD该视图；run/save/layout均未调用。复用之前已PASS的科学提取状态和原历史身份，通过未修改的generic_profile完整导入609D并审核标签SHA；缺H5、错SHA、将历史身份冒充6ps案例均被拒绝。未重做原两例全科学重提取。

## 阻塞、责任与最小证据

- **SCIENCE_IDENTITY_JOB_BINDING**：Coupling负责正式映射激活与原预算唯一入口；当前FORMAL_IDENTITY_MAPPING_CANDIDATE.json中的生产DB/Job/Entry仍为空。D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py 的run_job（L187）直接调用_record_solver_entry（L148），没有科学预算回调。测试映射和既有deny marker不证明所有旧/新执行路径都被同一授权栅栏覆盖。正式激活还受AGENTS禁止生产SQLite写入及本轮零执行边界约束，不能把隔离测试写成已上线。
- **INDEPENDENT_GPU_RESOURCE_GATE**：平台维护者/独立共享资源验收负责。D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py::_acquire_gpu_lock（L86）只检查本文件锁；外部GPU消费者/旧执行器排他、owner/fencing与不影响他人求解未独立证明。原最小复现见上一轮FAKE_BACKEND_E2E.json，本轮仅核验安装未变，未重复已PASS的mutex测试。维护线程仍systemError（invalid message ID），无实际修复回传；不声称已接收修复。
- 完整定位、函数和证据路径见BLOCKERS.json及INDEPENDENT_RESOURCE_EVIDENCE.json。未修改Runner源码、生产数据库、Scheduler、原历史科学ledger或他人进程。

## 权威来源与保留资产

正式科学原件在DESKTOP-NNE313K的D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1；原生历史FSP/H5位于冻结inventory指定的D:\apcd_runtime路径，其权威来自已核验registry/provenance，不因目录不同失效。本机D:\project\blue plane wave meta-surface中的同名报告仅为交付副本，不能作为远端批准/ledger。SOURCE_PROVENANCE.json记录现场比对。GPU工作树报告只作为平台维护证据，不签发Coupling科学批准。

合法156G、old32 train-only/new124 CV、16项source/setup SHA、G001/G004零差异重提取、14迁移检查、6resolver检查、全部模型、8192池和16提案均保留，未重跑。AL16制造Authority仍缺失，保留待审核；本轮未申请16条预算。

所有后续真实执行必须先取得共享执行排他与资源独立证明，由Coupling将准备好的单job原身份映射接入正式入口；再依据后续明确启动任务执行原两案。两条原预算继续有效，不重复申请。

Git基线：work/mdc-np-coupling-ml-v1 @2cc687020e90ec4397e6cd4ed31efed59aaaf386，ahead/behind0/0。保留原4项staged与无关dirty；本任务新增文件未提交/推送。详见FINAL_GIT_AUDIT.json。

隔离测试数据库已封存为TEST_FIXTURE_DISABLED_NO_EXECUTION，PENDING=0；保留原模拟entry证据，防止误用CLI启动真实输入。生产SQLite未变。
