# AL16_FAST_PRODUCTION_READINESS

## 最终状态

**AL16_FAST_PRODUCTION_READY**。

理想几何仿真准入16/16 PASS（用户本轮显式批准）；实际制造资格UNRESOLVED。FSP16/16保存并重新LOAD通过；替换0；原16与8192池保持一致。ML_TRAINING_GRADE，非FINAL_VALIDATION_GRADE；旧严格收敛HOLD保持，6ps不被预设为收敛。

## 可提交用户批准的范围

建议单独批准最多16个新AL Solver Entry，每案1次，失败也消费、不自动补跑或换身份；当前NOT_AUTHORIZED。批准应指向本包AL16_FAST_PRODUCTION_MANIFEST.json及SHA_INVENTORY中的固定16个case/输入。独立预算提案AL16_FAST_R01_BUDGET_PROPOSAL_V1当前授权0，不是DIAG2预算迁移。

第一阶段G001（空间覆盖/直径极值）和G009（模型分歧、较大间隙区域）逐案运行并完成完整科学验收。它们不是已知高性能候选或数值收敛锚点。两案无系统性异常后，在同一已批准总预算内连续串行继续其余14案，无需逐案再请示。所有后续case仍truth-before-next；个案失败保存证据，无solver replay；若发现资源、身份、归一化或后处理系统性问题暂停余案。

## 正式接口与执行清单（仅授权后使用）

Runner保持已部署3.1.1-shared-server和原SHA5778eefb…cb7不变。正式Python C:\Users\DELL\anaconda3\python.exe；Runner完整路径见SHA_INVENTORY。

1. 核实人类正式求解授权、16次上限、制造范围仅理想几何；把该授权关联到新的AL科学预算投影（不签发自授权，不改DIAG2 Ledger）。刷新已知科学/几何registry、生产jobs/entries，原case/execution无重复、输入SHA不变。
2. 检查真实RTX3080 GPU、参与式共享互斥及owner/fencing、真实资源与外部GPU冲突；CPU FDTD/EDT进程本身不是HOLD理由。WDDM显存N/A不当作空闲证据，未知资源failclosed。资源证据必须启动时实时获取，不以准备态历史快照背书。
3. 每案使用runner_manifests/<case>.json：`python <runner> submit <exact batch_name> --manifest <exact percase manifest>`；submit仅在明确授权后。获取status并将internal_job_id绑定到科学case/execution/预算。
4. 对同一case执行`python <runner> run <exact batch_name>`一次，然后`status`；REAL entry-before-launch由正式Runner记录，独立对账，即使失败也计入消耗。不能按“没有成功结果”退款。不要对总science wrapper执行run，单案batch避免Runner内部连续跳过科学验收。
5. 完成独立科学验收：GPU真实入场与日志/停止原因、输入输出身份与原生FSP/H5完整性。用科学Python执行`al16_extract_native_v1.py --case <exact case_id>`，该组件仅LOAD/提取，不调用run/save或改旧Ledger。科学输出目录已逐案固定，默认拒绝覆盖；后处理失败从同一原生证据离线恢复，不重跑solver。
6. 检查LABEL_EXTRACTION_AND_ACCEPTANCE.json全部要求，形成科学receipt后独立对账新AL投影，只有labels-valid入版本化FAST训练库。先完成G001/G009，再按manifest execution_order继续，预算最多16。

AL16_FAST_PRODUCTION_MANIFEST.json为科学总包，正式Runner输入是16个单案runner_manifests；它们使用已安装submit/run/status的真实字段，无私有猜测参数。**Runner不会强制science_entry_authorized字段，因此该false字段本身不是防误运行安全锁；本轮没有生产submit，未来Coupling必须先检查人类授权与科学预算。**

## 数据验收与研究目的

保留native FSP、原生H5、必要EH复场、truth.h5、609D、21点η(+1)/P_scale/H2 P(+1)、日志、SHA/provenance。额外保存native与H2两套η/阶功率并注明定义，不混淆旧标签小差异；不改C_hat/P_scale/TE-TM/Floquet/deembedding/H1/H2。原严格误差旗标继续保存，但不把训练级标签描述为严格收敛真值；异常有限值/归一化/身份不能因“训练级”放行。

目的为覆盖扩展、稀疏组合、FAST稳定性和后续学习曲线；本轮不找最优K6，不重训。156G不覆盖，role/grade/contract可追溯；old32 train-only、geometry-grouped、训练折预处理，sealed confirmation继续冻结。全链路有效receipt后才可正式训练入库，实际重训在后续获准数据生产闭环进行。

## 时间与有效产出

历史5nm3ps solver9.40–9.48min/case，端到端11.66–11.73min/case；16次规划solver2.51–2.53 GPUh、端到端3.11–3.13 GPUh。V31首两案实测校准，队列、失败、导出/验收开销另记；保守排程可预留最多8h（30min/attempt估计），这不是物理时长或实测成本。

最多新增16个唯一labels-valid几何，若全有效156→172。无实测新批次失败率，不能保证16有效；仅作情景：有效率90%/80%期望14.4/12.8个，不是观察值。失败不自动申请替换entry；累计有效几何数不计同几何锚点重复。每有效几何成本=总服务GPUh/有效唯一几何数。

## 保持边界

DIAG2=1/2，A2=HOLD，DOE56=HOLD，AL16=NOT_AUTHORIZED；本轮NEW_FDTD=0、NEW_SOLVER_ENTRY=0、REPLAY=0、NEW_ML_FITS=0、SEALED_RESPONSE_ACCESS=0。没有Runner修改、生产SQLite写入或旧Science Ledger修改。

本包现在可以进入用户正式求解授权；理想几何准入不需再次误称实际制造PASS。授权前停止。
