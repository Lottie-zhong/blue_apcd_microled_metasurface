# COUPLING_ML_K6_V2_GPU_PRODUCTION_FIRST_START_AND_CONTINUOUS_RUN_V1

状态：**BLOCKED，G027 尚未进入 solver**  
快照：2026-10-09 07:49 UTC，DESKTOP-NNE313K / desktop-nne313k\dell

## 结果

2026-10-09 07:40:41 UTC 对 successor request bbb7f19186776ceff07f93a17fded92b 调用了一次正式 start-controller-task。API 返回 START_REQUESTED，并生成 request 专属 start_claim.json。随后 Runner 查询返回 CONTROLLER_EXITED_NEEDS_RECONCILIATION、status=null；Task Scheduler 为 Ready、LastTaskResult=2。控制器未进入 case dispatch。

官方零 solver stop reconciliation 与独立零 solver startup dry-run 均 fail-closed，错误相同：QUEUE_STOP:CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT。未生成 controller status 或 reconciliation receipt。Scheduler 未保留 controller stdout/stderr；因此错误文本由正式对账入口与完整 dry-run直接证明，Scheduler 退出码与其相符，但不声称该错误来自被保存的 Scheduler 输出。

## 根因

Runner绑定 manifest 位于：
D:\apcd_runtime\gpu_production_runner_v1\requests\scheduled_queue_controller_v1\bbb7f19186776ceff07f93a17fded92b\controller_manifest.json

manifest SHA-256：
bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f

其 status_path 指向 G026 reconciliation 报告目录：
D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_G026_RECONCILE_AND_DURABLE_GPU_PRODUCTION_RESUME_V1\CONTROLLER_STATUS_K6V2SERIAL20261009T062450Z_0201c4b5.json

被绑定的 Coupling serial_queue.py 在第391–395行，将 status_path resolve 后限制在固定 REPORT 根目录 COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1 下。manifest status_path 位于另一个报告目录，因此校验在队列初始化和 G027 preflight 之前拒绝。

当前绑定下无法就地修复：改 manifest 会改变 manifest SHA/request binding；改 serial_queue.py 会改变 Runner Scheduler action 所绑定的代码 SHA。移动、别名或绕过此路径校验会规避正式validator。用户提供的本任务明确禁止重建request或重复rebind，因此没有修改代码、manifest、binding、Scheduler、账本或Runner，也没有重复 start/resume。

## 现场状态

- Runner worktree：D:\project\worktrees\blue_apcd_gpu_production_runner_v1；HEAD a8a09213d14883349921e5432daacd72f2ee7bb4；clean；upstream 0/0。
- Coupling worktree：D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1；branch work/mdc-np-coupling-ml-v1；HEAD a0747605c3e5fefe4e111aa5d16e3a148328ed37；upstream ahead 1 / behind 0。此前已有大量其他任务的 staged、unstaged、untracked 状态，均未清理、暂存或纳入提交。
- request 范围 G027–G116，共90个合法未入场开发案；单槽、每案至多一次entry、automatic replay=0、truth-before-next。
- 账本仍为128授权、38 entered、34 truth-valid、34 labels-valid、90 unentered；下一案 G027，之后G028、G029。current_case=null；G027无账本记录。当前 ledger SHA-256 为 ff9f9e92904eccf76744e60c32fa143dc2a36cf900788c3c3d6be635ed5177a2。
- 本任务新增 solver entry=0、training fit=0、P_scale fit=0、confirmation response access=0、replay=0；没有新truth或标签。
- Scheduler 实际读回：PT0S、IgnoreNew、用户 DELL、InteractiveToken、Ready、LastTaskResult=2。InteractiveToken不保证用户注销或主机重启后仍运行。
- G027尚无当前Runner record/run目录或preflight。现有source manifest SHA为95615c39f5df30a5f0703f7a6b9cf45547332e38448fca58aea90c8fc04efe2a；源与staged FSP SHA均为b5c6b41d28e55984d9cebd1f15814f698b408350b2cbeac02336b200bc72271e；contract SHA为32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5。旧LOAD proof仍须在实际case准备时按现有流程刷新；控制器没有到达该步骤。
- G026历史终态保持FAILED_POSTENTRY_NO_TRUTH，entry=1、replay=0、truth缺失、physical engine entry=UNKNOWN；未重放失败案。
- 最近只读license快照显示license服务与代理可达，但不能推翻G026既有启动失败，也不证明GPU engine已成功启动。没有G027 engine entry、求解时长、truth持久化、验证或标签导入证据。

## 证据

- Start stdout：START_CONTROLLER_STDOUT_20261009T074037Z.txt，SHA-256 12e0f9a4e1005eb39318e2401f6e3e4346153bef37eb69e8d47f841badfdc28a；result JSON SHA 05d2970a07ef41ccc7a0594e0294ba5e46ca5a66a6533bb22d5432c1e78621ee；stderr为空。
- start_claim.json SHA-256 061dd7e0bbcf13bd6364b6b816b691c9fe98a060d6b1364a346213b6b95ec249。
- 正式对账stderr：BOOTSTRAP_RECONCILIATION_STDERR_20261009T074243Z.txt，SHA-256 b3bdaff721fcb8aab93439ecddbfed5865cd7326400cc11a499c01f3d901bc95；stdout为空；result JSON SHA 6cb95739f1330c75aa7caddcbc4622cf86de1b50f028b8da940aed0f8b3b0015。
- Startup dry-run stderr：SUCCESSOR_DRY_RUN_STDERR_20261009T074401Z.txt，SHA-256 同为 b3bdaff721fcb8aab93439ecddbfed5865cd7326400cc11a499c01f3d901bc95；stdout为空；result JSON SHA c8849705377f1e17cb2cc8c3913d4090aa6f267b1437e7bb8fe6a38d04d4c47c。
- 现场完整状态：FINAL_LIVE_STATUS_20261009T074900Z.json。
- 所有任务产物及正式输入的SHA见SHA256_INVENTORY.json。

未提交或推送任何文件；没有暂存其他工作区状态。