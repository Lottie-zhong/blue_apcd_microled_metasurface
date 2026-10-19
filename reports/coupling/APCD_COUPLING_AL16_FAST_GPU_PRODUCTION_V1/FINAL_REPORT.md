# APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1 — FINAL_REPORT

## 最终状态

**PASS — 首轮真实FAST生产与轻量代理更新完成。代理排序能力仍PARTIAL，未准入正式逆向优化。**

|字段|结果|
|---|---|
|AL16_REAL_SOLVER_ENTRIES|16 / 授权上限16|
|AL16_LABELS_VALID|16|
|AL16_LABELS_INVALID|0|
|AL16_REPLAY_COUNT|0|
|FAST_DATASET_TOTAL|172 = 原156 + 新16唯一几何|
|数据等级|ML_TRAINING_GRADE / FAST_DATASET|
|严格数值收敛|NOT_CERTIFIED；原A1严格HOLD不变|
|DIAG2|1/2，A2 HOLD|
|DOE56|HOLD|
|第二轮授权|0，未创建新科学Case/Job/Entry|

用户正式授权仅本包固定16案，每案最多1次。实际按G001→科学验收→G009→科学验收→其余14案逐案验收串行执行；canonical Entry顺序、科学接受时间与预算独立核对通过。无替换、额外几何、自动Replay或失败补跑。16个原ExternalExecutionID与源FSP SHA完整保留，使用冻结V3.1，未修改/部署Runner。

## 1. 实际时间与生产效率

- canonical Runner started_at→completed_at 累计 **2.566173 GPUh**，每有效几何9.6232min；包含native LOAD/run/save，不冒充纯GPU kernel计时。
- entry→科学验收服务时间合计 **3.122423h**，每有效几何11.7091min。
- 首entry至末案科学验收墙钟 **3.240238h**，含案间注册/门禁间隔。
- 北京时间 2026-10-17 23:09:44 至 2026-10-18 02:24:08。实际有效产出率16/16；这不是下一批成功率保证。

历史预计端到端3.11–3.13h与本轮3.1224h服务合计接近；调度等待、案间门禁与模型CPU成本分别记录。所有16案原生status=1到最大3ps，不是auto-shutoff收敛证据；采用训练级资格，不将“完成/标签有效”改写为严格收敛。

## 2. 原生数据、科学验收和资源安全

固定5nm内层mesh/最大3ps、auto-shutoff1e-6、440–460nm每1nm、3D正入射X/P_XLIKE、固定975nm MDC/237nm spacer/500nm有序六TiO2圆柱；保持原生材料、两冻结源对象、monitor、reference1722nm、Floquet/TE-TM/C_hat/P_scale/609D/H1/H2。理想几何仿真准入已获用户批准，实际制造资格仍UNRESOLVED。

每案均有真实RTX3080日志、唯一REAL entry、已保存输出FSP、原生H5和有限复E/H、独立science truth.h5、609D NPZ、21点native/H2 eta(+1)、P_scale、H2 P(+1)、停止日志、SHA/provenance及SCIENCE_RECEIPT。Native freshLOAD提取后关闭自己会话，未对已求解FSP switchtolayout/save。完整路径逐案见NATIVE_ARTIFACT_INDEX.json / CASE_RESULTS.csv；SHA复用Runner和receipt，未全量重哈希旧数据。

所有功率/标签有限，P_scale为正，七阶routing与原冻结numeric/profile检查通过，原生monitor总通量与EH积分一致。全新批次P_scale范围0.05115702…0.82257302，monitor/EH相对差最大1.16e-14。原R/T/A proxy范围与残差见ENERGY_ROUTING_NORMALIZATION_AUDIT；A=1−R−T的代数闭合不是独立体吸收验证，不把legacy Tproxy混同P_scale。所有case记录包括风险标记，未调松旧门槛。

每次入场前保存两个资源采样、GPU身份/显存/compute-context、RAM/CPU/disk、许可证和旧Scheduler隔离证据；正式Runner在锁内再次检查。参与式互斥未被解释为能约束所有手工启动程序；CPU FDTD/EDT/GUI本身不是阻塞条件。没有kill其他用户进程。共享资源未知时failclosed，本轮16案实际检查均无HOLD理由。OWNED_PROCESS_IDENTITIES保留controller/CLI/engine PID+create_time证据。原DIAG2 Ledger最终逐字段相同，未消费A2，旧生产数据不覆盖。

首次后台控制进程随SSH结束而未启动，现场证明进程不存在、无Job/Entry后改用保持SSH前台父进程；该事件没有求解入场，不是Solver Replay。此后生产控制器一次连续完成16案。canonical SQLite Entry是原子入场权威；科学JSON是其独立投影，在长run期间可能暂时滞后，预算消费始终以canonical Entry计算，最终16对16完全对账。

## 3. 合库资格及字段定义

同原156的冻结六字段physics SHA32e60a…dea5、21lambda、7order、TE/TM、reference1722nm及H1/H2一致；5nm3ps配置由原已审计历史合同和新16实际readback继承。原156不重新提取/训练比较，使用已验证科学inventory与已有缓存；新16逐案receipt/labels SHA和Entry绑定核验。仅labels-valid新样本进入版本化FAST数据视图，未修改旧156、旧Ledger或sealed确认集；DOE56/DIAG2诊断响应未加入。

正式新增训练视图在ML_UPDATE/FAST_DATASET_MANIFEST.json与FAST_DATASET_172G.npz。记录来源、case/attempt/entry、数值等级、角色和严格精度风险。缓存是172个训练目标视图，不冒充172案新的原生求解；609D完整资产保留各自原路径。native eta与H2解码eta的小差异保留并标注，训练42D目标仍沿用21native eta+21logP_scale，预测P+=eta_hat*exp(logP_hat)对照原H2 P+；未改变H2来匹配模型。

## 4. 模型更新：固定验证身份的前后对比

复用原make()：KRR alpha0.1/gamma1/6；ExtraTrees128trees/leaf3；小MLP6→32→32→42/tanh/Adam1000epoch；ET/MLP种子17/29/43，Mean简单基线。没有GPR再比较或新架构。共40拟合（四折32+最终8），CPU拟合合计17.6804s；15个MLP固定预算warning保留，不声称优化器已收敛。

原old32始终train-only，原new124四折heldout IDs不变；新16按固定Case顺序四折各留4个，训练预处理仅训练折拟合。同一几何从不跨train/validation；旧124前后可比，新16小样本单独报告。每折OOF先保存再做model reload，未重演历史OOF丢失。无超参数调优、无sealed响应或重新分割。

|模型|P+谱MAE before→after|eta谱MAE before→after|P_scale谱MAE before→after|450nm P+ mean-fold Spearman before→after|
|---|---|---|---|---|
|Mean|0.0311368→0.0309869|0.0987434→0.0983052|0.0539882→0.0539949|未定义→未定义|
|KRR|0.0363550→0.0366192|0.1137204→0.1135335|0.0633556→0.0643317|-0.06830→-0.11986|
|ExtraTrees|0.0315207→0.0313934|0.0997928→0.0997448|0.0490010→0.0493067|-0.04649→-0.04455|
|MLP|0.0389650→0.0389522|0.1233656→0.1234780|0.0661326→0.0671094|-0.06648→-0.16752|

ExtraTrees P+略改善但仍不优于Mean，P_scale仍有部分预测信号，eta/P+未知K6排序仍不可靠；新增16没有带来可信的设计精度跃升。KRR/MLP排序没有改善，不选择性只报有利指标。完整450nm、谱MAE/RMSE、fold/pooled Spearman、invalid prediction fraction及seed信息见MODEL_METRICS_AFTER与FOLD_METRICS。Mean的跨fold pooled rho可受折间常数偏移影响，正式比较采用同定义mean-fold rho，常量预测未定义。

Top候选在原124每折按450nmP+选ceil(20%n)，稳定Case ID打破ties。本轮平均Top20%召回：KRR 0.1488，ExtraTrees 0.2202，MLP 0.1488；相同k/n随机选择期望约0.2176，未形成可靠富集证据。历史pooledOOF丢失，旧Top召回不可重建，明确NOT_AVAILABLE，没有重训基线补造before。新16为主动选择的极小样本，不是独立随机全空间测试；其OOF单独列，不能以某个P_scale rho正值宣称P+排序可靠。

合库前消费者误把原pack_model_target容器(1,609)当(609,)；在0拟合时修正本轮形状检查，原标签不变。没有FDTD重复，之后40拟合一次完成；细节ML_UPDATE_REPAIR.json。

## 5. 几何覆盖和信息价值

唯一几何156→172（+10.26%），原8192池已有16新计算、尚余8176未计算。以同一剩余池计算，归一化最近数据点距离均值0.379409→0.370301（下降2.40%）；全池距离中位数0.382687→0.374877。
轴级覆盖仍[27,25,27,27,27,27]，D2=130/185nm仍未补到；本轮主要增加六维组合覆盖，而非新轴值。距离变小部分是新增点的机械结果，不证明泛化提高。数据生产稳定性和可追溯性已得到本批证据，学习增益微弱也是本轮信息价值，不能用算得更多替代学习曲线判断。

## 6. 下一轮建议（无新预算）

已用更新后的模型和172G覆盖重新计算原8192池优先级，保存POOL_PRIORITY_UPDATE.npz，输出NEXT_ROUND_16_PROPOSALS_NOT_AUTHORIZED.csv：8覆盖、4未校准分歧、4分层随机，均来自原池、避开已计算172，不新建科学Case或生产Job。当前首个coverage提案D2=130，下一包冻结时优先补D2=185及稀疏组合，并刷新全部受保护/排队元数据，完成逐案理想几何检查；不冒充当前草案已是可直接执行生产包。

建议下一轮仍是一个独立、最多16-entry的FAST探索批次，先审查以上覆盖缺口与分歧是否关联实际OOF误差，再冻结生产包并申请预算。本轮不批准/执行下一轮，不扩大数值收敛诊断、不开发复杂网络、不启动逆向优化。若持续几轮不能优于Mean，应先检查目标可学习性、数据覆盖/局部变化和物理偏差，再决定是否扩至250；500/1000不作为自动路线保证。训练级高精度锚点可后续按需单独小额裁决，未在本轮创建或挪用DIAG2预算。

## 7. 附件与恢复入口

- CASE_RESULTS.csv / NATIVE_ARTIFACT_INDEX.json：所有FSP、原生H5、科学H5、609D及SHA/Entry路径。
- INDEPENDENT_PRODUCTION_RECONCILIATION.json：Runner/科学账本独立对账；AL16_SCIENCE_LEDGER.json为本批投影。
- 各case_PREFLIGHT_RESOURCES.json、RUN_INVOCATION_ONCE、RUN_RETURN、SCIENCE_ACCEPTANCE、Solver日志原生路径和SOLVER_TIMING_SAFE_EXCERPTS.json；原始含许可证上下文日志不在聊天中展开。
- ENERGY_ROUTING_NORMALIZATION_AUDIT.json；ML_UPDATE数据manifest/OOF/40fitledger/modelmetrics/coverage及下一轮草案。
- SHA_INVENTORY.json、FINAL_GIT_AUDIT.json、CONTINUATION.md。大FSP/H5/EH与模型joblib保留远端，不混入Git或本地小报告交付。

本轮没有失败求解/无效标签；已解决的连接/消费者形状问题保留证据，不混同物理失败。最终停止在16次预算结束，下一轮零授权。
