# Legacy ingress fence decision

FENCE_PREPARED_AWAITING_APPROVAL。起始 HEAD e4a6ce74ffabe01b10c2b425187546501b360a3f 已核验。正式 fence 未执行，V2 保持关闭，不具备 cutover 资格。

## 决策依据

1. ControlDB.set_hold(scope="COUPLING_ML") 并非 Coupling 专属入场控制：db.py:112–127 无条件设置全局 admission_control.new_entry_hold=1 并递增全局 generation。四个真实源码绑定的隔离测试均证明 Traditional 同时得到 NEW_ENTRY_HOLD。不能把 scope 字段的名称当作执行边界。
2. Allocator.set_branch_limit("coupling_ml", enabled=False) 只对 Shared V3 allocator 生效，且 allocator.py:702–711 递增全局 generation。隔离检查证明其使 Traditional RESERVED lease 的 final owner/generation 验证失效；V1 adapter.read_global_entry_control:76–149 仍 PASS。guard PASS 只证明分支控制缺口，没有执行完整 Runner，也没有证明某次科学入场成功。
3. V1 native static/controlled CLI 均经 adapter.run_cli:1255–1354 使用全局 guard；文件系统 Runner 不消费 branch_enabled。生产 root 虽要求 pre_entry_guard，Scheduler 禁用仍不封住该 CLI。因此只禁用两个 task 不能证明全部旧入场被拒绝。Shared host/canary demand-start 路径是独立范围，不能连同 Traditional 自动禁用。
4. Legacy PW_K6_PRODUCTION_NEW_ENTRY_HOLD.json 为 hold=true/generation=23，但实际 DB 为 hold=0/generation=27；其内容已陈旧，不得视为正式 admission 证据。Shared zero_solver_latest.json 存在 PermissionError；未提升权限、改变 ACL 或绕过读取限制。没有写任何 Shared 控制文件。

## 当前状态与 owner

两次快照 UTC 03:53:50.307394 / 03:58:22.947805，相隔 272.640411 秒。7 个历史 Python/API 父子组及 18936→40664 均通过当前 CIM/psutil PID/create_time/PPID 和旧身份交叉验证。15 个 UNKNOWN 被整理为 8 个组，40664 为额外关联 SSH 子进程；未将 UNKNOWN 数量归零作为证明。

未观察到当前 V1 Controller/Worker 命令、FDTD engine、Shared 活动 slots/resource/GPU lease、生产 root active_run/runner/worker lock。Controller STOPPED_RECONCILED，registry 54 条均 terminal（46 DONE、5 FAILED_POSTENTRY、3 FAILED_PREENTRY）。所有关联成员写入增量为 0，12 个历史目录文件的元数据未变。归档/released 锁仅作历史证据；未删除，未按旧 PID 终止进程。

可证明的是“这些对象不属于当前登记的 V1 active science-owner 集合”，并有 NP/surrogate/SSH 来源证据。完整 native handle/IPC 及 stdin 正文不足，绝对排除未登记 owner 或未来旧 ingress 关系尚未签发；保留残余风险，不把缺失业务目的本身当作 V1 owner。

## 正式 readback

global new_entry_hold=0，control_generation=27，health=PASS，temporary cap=null。Coupling enabled=1/cap=2；Traditional enabled=0/cap=1 是原始状态，非本轮修改。三 global slots FREE；GPU cap 原样保留。V1 Controller 与 Worker 均 Enabled=true、Ready、AllowDemandStart=true。两个 task 无触发器，但手动 demand start 仍开放。

最终 readback 再确认两 task 原始 XML 完全相同、正式控制和账本不变、全部 16 个关联进程相同身份仍存在。预算 38 entered / 34 valid / 90 unentered；G027 entry=0。G025 FSP/H5 原始 SHA 已复核不变。G025 LOAD、609 维 importer、G027 systemcheck 仅复用已验收报告，无新原生会话或科学 solver。

## 准备、验证与限制

16/16 正式 API 隔离检查通过；V2 89/89 离线回归通过。已备份一致性 SQLite 副本、原始 Scheduler XML、running task、Git、账本及 SHA。两份 disabled XML 在 Windows Task Scheduler NewTask 的内存定义中验证通过，Action、Principal、Trigger 和除 Enabled/AllowDemandStart 外的有效 Settings 保持一致，注册次数为 0。

离线普通问题已修复：Python 3.10 的 CIM 七位小数时间解析；fixture 首个 WAL reader 造成的 guard 瞬时文件变化；XML BSTR encoding/schema/default normalization。COM 实际 XML 字段是 AllowStartOnDemand，属性是 AllowDemandStart。失败摘要与修复见 engineering_fixes.json，首次 shadow 失败原始 JSON 留存于 runtime；未修改 V1 解决这些检查问题。生产拒绝、既有任务在正式 fence 后继续运行、Traditional 完全不受影响尚未现场证明。

## 隔离事务与下一步

见 fence_transaction.json：先 qualified Coupling-only 正式 hold → generation readback → 只关闭两 V1 task 的新实例及 demand start → 所有已知 admission 路径拒绝 → 已有任务/Traditional 不变 → owner/ledger/SHA 检查 → formal rollback。

事务停在第 1 步的共享控制边界。必须先由 Shared lifecycle 权限范围解决“专属 hold + native CLI 覆盖 + Traditional generation 不受损”的资格问题，再审查本事务并获得 APPROVE_V1_INGRESS_FENCE_ONLY。该授权本身不扩大 Shared 权限、不允许全局 hold，也不允许启动 V2/G027。不能为了绕过这个门槛继续给 V1 叠加补丁。

工程代码变更为 0；本轮仅新增审计报告、隔离检查源码及可审核 XML。Git 收尾 HEAD/status 在 runtime/final_git_receipt.json 单独记录，避免自引用 SHA。
