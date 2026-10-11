# V3 DOE56 owner接口最小续接包

科学预算已批准56次，不需要重新申请。冻结CouplingHEAD `21263d6d69a886e178262efe41993b44a80dc7d2`；registration package与budget authority完整SHA在本目录。当前installed `a09655cd577d7618d3080d35b7a5b2a4a5fc52c5`，126个安装代码SHA全部匹配。工作树RunnerHEAD a8a092…不是安装版本。

## 真实拒绝接口

1. `platform_v2/apcd_gpu_v2/serial.py:SerialRequest` line79–88：case_id只匹配K6GDP2/K6LDA1，role仅GLOBAL/LOCAL_AXIS，physical_contract仅canonical。56个冻结V3身份全部在model_validate前置校验被拒绝，见ACTUAL_INSTALLED_API_REJECTION_EVIDENCE。不得重命名DOE56来迁就旧规则。
2. `SerialConfig.paths` line65–68：只允许旧V2 canonical ledger/runtime；`CouplingBudget.validate` line156：旧账本128已全部消耗且remaining为空。新56预算必须独立scope并共享唯一全局slot/fencing，不得把56追加到旧128清单或改旧失败终态。
3. `validate_admission` line338：hardcodedCONTRACT检查；NativeTruthValidator、coupling.validate_labels以及Coupling importer需在正式诊断/封存路径绑定独立合同和角色。严禁把4nm当canonical5nm或封存当开发。需真实隔离读拒绝测试，不能只改目录名。
4. `controller` line519和`run_serial_case` line453：需要正式next-case deadline/cost gate，在prepare_entry之前实施，耗时依据最新有效日志及mesh倍率，UTC+08次日10:00，保留缓冲，不kill已运行solver。现有release到期检查不足。
5. 既有exit finisher需正式10:00部分/超时晨报能力，只公开sealed身份/状态/SHA；不要另建控制平台。数值4案工程阈值按原冻结协议，FAIL/未知停止开发，正常自动阶段衔接。

## owner交付要求

正式版本化代码+定向回归，独立诊断合同，sealed custody/ACL和开发入口拒绝证据，56逐案源manifest/canonicalpreFSP/freshLOAD/SHA，immutable request/config/queue/admission/budget，有限ALLOW及科学phase gate，实际Scheduler/PT0S/IgnoreNew/InteractiveToken/readback及empty slot，窗口/晨报测试，明确正式启动接口。先零solver完整dry-run，再遵守本次已批准预算启动。

本包不造ALLOW、不写Owner名单、不修改GPUworktree/安装/Task/slot/legacyledger；没有preFSP/load/enrollment冒充PASS。上述gap是owner受控接口支持和科学准入缺口，不是许可证故障或SSH故障。四gate关闭后Coupling无需再次申请同一预算，可按正式接口立即续接。
