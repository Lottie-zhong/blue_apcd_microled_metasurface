# 串行批量仿真队列工作流 V1

更新时间：2026-10-06

## 用户所需的执行顺序

先把整批有序几何的 canonical setup/FSP、case manifest 与输入来源准备好，再把 case 按冻结预算顺序放入单槽队列。每案进入 Runner 前核对其当前 route LOAD proof 和正式 setup preflight；随后只调用正式 Runner V1 `adapter.py run-one <manifest>`。Runner 完成后，控制器等待 `DONE`、单次 solver entry、零自动 replay、truth 与验证文件持久化、锁释放，并成功导入 development label；只有全部成立才推进到下一案。

正式 Runner 目前没有多案 batch CLI，因此 `serial_queue.py` 是 Coupling 仓库内的队列控制层，不修改或替代 Runner。它负责顺序调度和完成屏障，实际仿真仍由每案唯一的官方 `run-one` 调用完成。所有 case setup 已预先在隔离目录准备；当前 route proof/preflight 不要求在第一案前对全部剩余 125 案重复刷新，而是在 case 到达队首时复核/刷新，避免将全部 preflight 完成作为首个 entry 的额外门槛。

## 现场状态与检查

- Coupling：`work/mdc-np-coupling-ml-v1`，HEAD `3c9c3b540c6b88d5c964245f37b5017397e68bea`。Runner：`codex/apcd-gpu-production-runner-v1`，HEAD `02ad6b4b5f47b247f384fc132af329cc05612327`。
- 冻结队列预算 128 案；已有 3 案 DONE 且标签有效；剩余 125 案。当前准备清单中 23 个 case 的 current-route setup preflight 为 PASS。
- 下一案 `K6LDA1_DEV_D2_P05`，序号 4，D2_P05；fresh LOAD proof、preflight result 均为 PASS，preflight SHA `3a8b5049c98537d94bae84033fb61ace46da75265a58129770a5d98a3f39b98d`。这些是 setup/preflight 证据，不等同 solver truth。
- `serial_queue.py` SHA-256 `65e85ff5a1bba8f9ff54bec2e28196aea1dfc38a9c336f9e81ce28e7aaa4c906`；本地编译无错误，远端 `py_compile` PASS；`--dry-run` PASS，报告 solver entries this call = 0，training/P_scale fits = 0，confirmation access = 0。dry-run 给出的 queue manifest SHA-256 `ecbb9b32105f5a26adf051d614bef68fcf793e0f089eae391510e6b86a138e32`。
- dry-run 时 Runner registry 有 3 条本项目 K6 记录，active-run 与 `.runner.lock` 均不存在。实际每案仍由 Runner 和队列控制器在入槽时重查 live hold、owner、slot 与 GPU gate。

## 恢复规则

每案在调用 `run-one` 前先落盘 `current_case` 与 run envelope；entry 后无论 SSH 是否中断都不自动 replay。恢复时先查 Runner registry、status、truth、validation 和锁；如果 entry 已发生但最终状态或 truth 有歧义，队列停止并保留证据。标签导入使用 case/attempt、authority 和文件 hash 校验；若只写出 NPZ 而进程中断，恢复会比对 NPZ 内容与已验证 truth 后再补写结果记录，不重新求解。

本工作流不读取确认/诊断响应，不训练，不拟合 P_scale，也不触碰 Runner、truth/H1/H2、合同、mesh 或生产 monitor。
