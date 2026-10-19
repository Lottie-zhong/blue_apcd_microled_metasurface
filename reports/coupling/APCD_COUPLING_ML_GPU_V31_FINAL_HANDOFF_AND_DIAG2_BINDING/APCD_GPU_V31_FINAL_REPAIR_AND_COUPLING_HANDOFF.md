# APCD GPU V3.1 共享服务器发布与 Coupling-ML 接管

任务 APCD_GPU_V31_SHARED_SERVER_RESOURCE_POLICY_CORRECTION，2026-10-17。本文件取代此前要求服务器全局独占、按 FDTD/EDT 进程数 HOLD 的结论。其他人的 CPU FDTD、EDT/GUI 可以共存；不终止、修改或调查无关科研任务。不要求外部程序实现 APCD 锁。

## 发布身份与证据

- 主机 DESKTOP-NNE313K；工作树 `D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1`。
- 分支 `codex/apcd-gpu-v2-serial-production-v1`，基线 HEAD `4aae0c690c6d4e4438140c0d5d27ad7b8c4e43b1`。
- 版本 `3.1.1-shared-server`；源码 `minimal_runner_candidate/minimal_batch_runner_v3_1_1.py`；精确哈希见同目录 `RELEASE_MANIFEST_V3.1.1_SHARED.json`。
- 正式入口 `D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py`。
- 安装 Git SHA、文件哈希和时间以正式目录 `deployment_manifest.json` 为准。
- 本轮证据目录：工作树 `platform_v2\reports\APCD_GPU_V31_SHARED_SERVER_V1`。
- 发布完成以 `INSTALLATION_RECEIPT.json` 的 PASS 和 `FINAL_AUDIT.json` 的安装/Git 核对为准；没有记录不得仅凭本文宣称完成。

原安装 SHA256 `9d380e62f265cb7ca3d4398a9831dd8358362223d09fc5476a436b4f2582be33`。此前候选 SHA `30cb1cfe84d2fdff45bc66903ddaa00c5f32abae8c2c5a20c65250daf0b91917`。本轮复用其身份、事务、固定锁及恢复实现，修正共享资源策略、真实入口限制和 Manifest 保存，新源码使用新哈希。

## 共享资源与 APCD 串行边界

1. APCD 受支持的真实 GPU 入口统一为正式安装程序，数据库固定为其 `data\runner_v31.db`，文件锁固定为其 `gpu_runner_v31_shared.lock`，锁 byte 0。真实执行拒绝开发副本、自定义数据库及锁；Fake 必须使用隔离库，禁止写入正式库。
2. 旧 V2.1/V1 Scheduler 保持 Disabled。旧手工脚本、旧版本和另建生产库不是授权入口；保留旧文件供审计，不使用旧入口消费同一科学预算。只读查旧 Ledger 不等于原子预算互斥；采用单一受支持入口与旧入口停用的简单管理方案。
3. 取得锁后、原子记录入场前，重新采两次 NVIDIA GPU UUID/显存/进程及 Windows GPU 引擎证据。WDDM 的 C+G 列表含图形程序，EDT/GUI 名称本身不 HOLD。已有 Compute/CUDA 上下文即使瞬间 0% 仍 HOLD；实际 GPU 求解/计算进程、GPU 繁忙、监控/归属未知或资源不足也 HOLD。
4. 同时比较 CPU 余量、空闲 RAM、输出盘空间与任务需求，读取 `lmutil lmstat` 的 License feature 余量。未知仅 HOLD 新真实 GPU 入场；开发、submit/status 和隔离 Fake 可继续。
5. 软件锁只约束 APCD 参与进程，不能阻止别人随后启动 GPU 工作或 checkout License。实际竞争需协商共享时间安排，APCD 等待而不抢占。不开发全局 Controller。

策略为正式目录 `shared_resource_policy.json`。该主机实际 Lumerical/lmutil 位于 `N:\Program Files\ANSYS Inc\v251`，已确认路径并仅导入 lumapi 检查依赖，不创建真实 FDTD 会话。

## 通用 Manifest

```json
{
  "batch_name": "OWNER_BATCH_001",
  "jobs": [{
    "input_fsp": "case.fsp",
    "source_fsp_sha256": "<真实64位SHA256>",
    "external_execution_id": "owner:case/attempt-001",
    "external_job_id": "owner:case",
    "attempt_id": "attempt_001",
    "case_id": "owner-case",
    "physical_contract_sha256": "<真实64位物理合同SHA256>",
    "resource_requirements": {
      "gpu_free_mib": 4096,
      "ram_free_mib": 8192,
      "disk_free_gib": 20,
      "cpu_threads": 4,
      "license_features": {"lumerical_gui": 1, "lumerical_solve": 5, "anshpc": 64}
    }
  }]
}
```

资源数值仅为平台容量检查示例，**不是 DIAG2 需求、预算或通用 License 计算结果**。Science Owner 须依据正式 FSP、CPU 配置、GPU SM 数量及 License 模式填写准确需求并包含余量。缺项、无效数值或 License 不可确认时真实入场 HOLD。

身份为通用 1–200 字符 ASCII，允许字母数字与 `_.:/@+-`，不硬编码科学支线。source_fsp_sha256 仅校验完整性；不同合法执行身份可引用同一 FSP。external_execution_id 是一次不可重复的科学执行，external_job_id 是业务关联，internal_job_id 是 SQLite 行号。换 Batch/attempt 标签/源文件不能复用同一 execution identity。

旧 `sha256`、`external_job_id`/`job_id` 别名兼容；缺 SHA 时计算真实 SHA，双 hash 别名须一致。相对输入按 Manifest 目录解析。旧 Manifest 无外部身份可 Fake 回归；真实执行须有 execution identity、case_id、物理合同 hash 和资源需求。

## submit / run / status

远端 PowerShell：

```powershell
$py = 'C:\Users\DELL\anaconda3\python.exe'
$runner = 'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\minimal_batch_runner_v3.1_final.py'
& $py $runner submit OWNER_BATCH_001 --manifest 'D:\owner\manifest.json'
& $py $runner status OWNER_BATCH_001
# 仅 Science Owner 的身份、原预算承接和科学门禁全部通过后才可运行：
& $py $runner run OWNER_BATCH_001
```

上面的 Owner 路径须替换为真实输入。已存在、可复现的零 Solver fixture 由安装 receipt 提供：

```powershell
$receipt = Get-Content 'D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\platform_v2\reports\APCD_GPU_V31_SHARED_SERVER_V1\INSTALLATION_RECEIPT.json' -Raw | ConvertFrom-Json
$fixture = $receipt.fixture
& $py $runner submit PLATFORM_SHARED_FAKE --manifest "$fixture\manifest.json" --db "$fixture\repro.db" --output-dir "$fixture\repro_outputs"
& $py $runner run PLATFORM_SHARED_FAKE --fake-solver --db "$fixture\repro.db" --output-dir "$fixture\repro_outputs"
& $py $runner status PLATFORM_SHARED_FAKE --db "$fixture\repro.db"
```

原验收库为 fixture 下 isolated.db；重复 submit 被拒绝属预期。CLI 成功返回 0，非法输入/失败返回 1，资源 HOLD 或未闭环 RUNNING 返回 2。status 包含身份、Attempt、路径、hash 与错误；COMPLETED 不代表科学有效，须区分 FAKE/REAL、solver_entered。

## 原子准入、No Replay 与历史保护

同一正式库中跨 Batch 身份注册和 solver_entries 唯一索引受 SQLite 事务保护。BEGIN IMMEDIATE 内检查 PENDING、已有 Attempt 与身份，在 backend 调用前原子提交 case_id、attempt_id、entered timestamp、solver_entered、pre-FSP hash、physical-contract hash。此记录是保守预算预留；即使 API 创建、load/run/save 失败也不自动重放。

断线、异常、FAILED、遗留 RUNNING 或 partial/输出缺失时，先检查原进程、日志及 FSP。禁止删 entry、重置状态或换 ID 假装新预算。预算与科学恢复由 Science Owner 判断。

历史 Ledger `D:\apcd_runtime\gpu_platform_v2_serial_production_v1\ledger.sqlite3`，94 tasks，SHA256 `8c52bb709b7f595dd500b474c9023175889ae34551630fbce8a281dc67dc6e99`；前后 size/hash/mtime/count 见 LEDGER_BEFORE 与 FINAL_AUDIT。未覆盖 Ledger、导入科学任务或清理历史资产。历史执行身份及 DIAG2 两条预算的绑定仍由 Science Owner 验证。

## Native FSP / 日志 / Manifest 合同

每 Job 默认 `<output-dir>\batch_<internal batch id>\job_<internal job id>\`，保存 manifest.json、input.fsp、runner.log、resource_snapshot.json 和 output.partial.fsp / output.fsp。Fake 复制合成字节，不能当原生 FSP。

真实 backend：load(staged input) → run('FDTD','GPU') → save(output.partial.fsp) → close，不调用 switchtolayout。输出非空并核验 SHA 后原子 rename，最后写 COMPLETED。失败保留 partial 与日志；不清理 Lumerical 在工作目录产生的 engine 日志。

本轮 Native FSP **API 调用及持久化合同**用隔离 Mock 验证：入场先于 backend、GPU 参数、load/run/save/close 顺序、输出 hash、日志与 Manifest。没有生成/验收新的真实求解输出，没有宣称 H5/609D 科学 PASS。新增真实 FDTD=0；DIAG2 本轮 0/2；DOE56 原 HOLD 不变。

官方依据：[run 接口](https://optics.ansys.com/hc/en-us/articles/360034931333-run-Script-command)、[GPU License 规则](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)。

## 部署、回滚与冻结

源码、辅助模块、策略、两份测试、发布 manifest 与本文通过精确 allowlist 提交；不纳入既有 dirty/untracked 科研资产。原入口和 deployment_manifest 可核验备份位于本轮报告 `predeployment_backup`。先安装辅助模块/策略，再原子替换入口；安装验收只用隔离库和合成文件，不启动 Scheduler。

回滚须在维护授权下确认无 APCD GPU 入场后，恢复备份并核验 SHA；旧版能力较弱，回滚后真实 GPU 保持 HOLD，不恢复旧 Scheduler，不删新库/Attempt/输出。

当安装 receipt PASS、Git push 和 FINAL_AUDIT 核实后，发布结论为 APCD_GPU_V31_SHARED_SERVER_PRODUCTION_PASS，冻结 Runner 并交接 Coupling-ML，停止日常平台开发；仅真实平台缺陷或新维护任务重新开启。

Coupling-ML 独立负责 DIAG2 身份、两条预算合法承接、正式 FSP/Manifest/资源需求、GPU 提交、H5/609D、主动学习、训练和逆向设计。**平台 PASS 不解除科学 HOLD。** 本轮不提交 DIAG2、不启动 DOE56、不访问 sealed 科学数据，不向其他 chat 发出执行指令。
