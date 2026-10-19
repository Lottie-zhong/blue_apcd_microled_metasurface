# APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1

## 状态
PARTIAL / HOLD：仅已记录的真实Entry被消耗；A1未获科学PASS时A2不执行。

## 执行和科学验收
| 案例 | Entry | Truth | Labels | 状态相对L2最大 | Routing最大差 | P_scale最大相对差 | 相位RMSE最大 |
|---|---:|---|---|---:|---:|---:|---:|
| A1 | 1 | PASS | PASS | 0.014194 | 0.00227734 | 0.02434 | 0.0137662 |
| A2 | 0 | NOT_RUN | NOT_RUN | 未运行 | 未运行 | 未运行 | 未运行 |

原DIAG2预算使用 1/2，剩余 1。原A1/A2/attempt_001/External Execution ID全部保留，正式submit Job未重建。Runner源码5778eefb未改、未部署，严格调用已登记单Job批次run；Entry在backend前原子提交，独立SQL与单一科学账本对账，任何失败均不退款、不自动重跑。

A1: 科学验收 HOLD_NUMERICAL_REVIEW；停止 FULL_6PS_MAXIMUM；native FSP `D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\data\outputs\runner_v31\batch_1\job_1\output.fsp`；native H5 `D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\data\outputs\runner_v31\batch_1\job_1\input\input_output.h5`；truth H5 `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1\A1_science\truth_complete.h5`。
A2 未启动：A1尚未科学验收PASS，严格执行条件授权；原Job保留，不换ID、不恢复或新增预算。

A1_CLI_STDOUT/STDERR、各Job runner.log/input_p0.log、OWNED_PROCESS_IDENTITIES、LIVE_RECONCILIATION及RUNNER_FINAL_READONLY_AUDIT记录真实GPU与PID+create_time、停止及输出证据。只有自身API只读会话被关闭，其他CPU FDTD/EDT未停止或修改。

## 原冻结标准
沿用5nm/6ps、auto-shutoff1e-6、21lambda、参考面1722nm、TE/TM、Floquet分解、C_hat、P_scale、609D/H1/H2。使用冻结postprocess、H1.state_data/pscale_eh、H2及coupling_609d_v1数值检查，不改原importer源文件；V31原始科学身份和SHA由权威绑定账本核验。新旧容器合同的六字段投影复用既有resolver函数，不生成替代物理合同。Native输出只读freshLOAD、E/H/H5完整有限、SHA、功率映射及参考面检查见各science目录；必要时仅建立不改字节的Native basename读视图。

时间对照沿用V3_NUMERICAL_VALIDATION_PLAN：相对状态L2<=0.02、Routing和绝对阶功率差<=0.005、P_scale相对差<=0.01、有效模态能量加权相位RMSE<=0.05rad，模态功率mask1e-4，无oracle相位对齐。完整21波长表、609D差异及原始复数场幅度对照见TIME_CONVERGENCE_COMPARISON.json和WAVELENGTH_3PS_6PS_COMPARISON.csv。能量闭合沿用原R+T+A方法，A=1-R-T，不能将其代数闭合当作独立体吸收证明。

停止状态1=完整最大物理时间、2=自动停止、3=发散，依据[Ansys FDTD状态定义](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)。完整6ps停止不等于达到1e-6；逐案原生日志与status另列，不以Runner COMPLETED代替labels-valid。

## A–E 裁决
A. 历史3ps是否足以支持ML标签：不能按冻结总功率1%要求认证为足够。A1的P_scale最大相对变化2.434%，其余四项通过；原合法156G保留，但这一个反例已阻止对全部3ps标签作无条件时间精度背书。
B. 6ps改善：时域残余下降，但A1以status1到最大6ps停止，没有自动停止完成证明；P_scale变化2.434%仍超过冻结界限，因此不能宣称6ps自身已严格收敛。A2未运行，不能给出第二anchor结果。
C. 4/5nm仍须独立研究：是。本次仅改变最大物理时长，不能解决已知网格敏感度，未新增4nm求解。
D. 后续统一FDTD合同：保留Native材料、几何、源、monitor、参考面、609D和1e-6不变；6ps为本次诊断合同，尚不能替代全域网格/时间认证。新AL生产合同在剩余数值问题关闭前不冻结、不启动。
E. 历史156G与新数据：609D表示兼容；不支持无版本标签直接合并。保留3ps/6ps及诊断角色、数值质量标识，DIAG2不自动转为训练开发集；本次零新模型fits。

Truth/Labels PASS仅代表原生结果及冻结提取有效，不等于时间精度门禁PASS。A1科学推进为HOLD_NUMERICAL_REVIEW，因此未调用A2。标量H5压缩兼容错误已离线修复，部分truth.h5保留，truth_complete.h5与既有E/H和标签逐项一致，见OFFLINE_H5_EXPORT_REPAIR及POST_EXPORT_TARGETED_VALIDATION；没有重提取原生场或重跑Solver。补充MODAL_AMPLITUDE_PHASE_3PS_6PS、ALL_ORDER_ROUTING_3PS_6PS、LABEL_609D_COMPONENT_COMPARISON.csv及RAW_EH_PHASE_3PS_6PS.json保存完整对照。

## 边界和Git
DOE56=HOLD；AL16=NOT_AUTHORIZED；sealed response access=0；replay=0；new ML fits=0。历史FSP/H5和既有11+8证据保持，未重训或重整156G。
branch=work/mdc-np-coupling-ml-v1；HEAD=2cc687020e90ec4397e6cd4ed31efed59aaaf386；ahead/behind=0	0；dirty，原4项staged保留；未提交/推送。

## A1 重点数值及关闭记录

| 波长 | P_scale 3ps | P_scale 6ps | 相对变化 | eta(+1) 3ps→6ps |
|---|---:|---:|---:|---|
| 446nm | 0.2800307875 | 0.2732148314 | 2.4340% | 0.4085475635→0.4091817621 |
| 450nm | 0.6982029820 | 0.6976702123 | 0.07631% | 0.3656054566→0.3656036759 |

最后日志采样：3ps的99.0003%处AutoShutoff=6.7674e-05；6ps的99%处=4.4505e-06，约下降15.206倍。它们是日志采样值，不冒充精确终点残余；原生status1证明本次最大6ps停止，未获auto-stop完成证明。状态相对L2最大1.4194%、Routing最大绝对差0.00227734、绝对阶功率最大差0.00261137、有效模态相位RMSE最大0.0137662rad均通过冻结门槛，唯P_scale的2.4340%超过1%。

A2原Job2保持PENDING，无CLI调用、无Entry，剩余原预算1条，未重分配给A1。A1一次真实求解耗时约18分41秒（Entry至CLI返回），本次原预算不会退款。原permittivity潜在发散警告保留在日志中；正常status1及有限E/H不构成实际发散证据，未调整dt/PML。

独立科学账本entered/truth-valid/labels-valid=1/1/1；时间数值推进仍HOLD，详见SCIENCE_LEDGER_SUBSET_RECONCILIATION.json。H5导出修复后的7项定向一致性检查通过，未重跑模型或原生场提取。
