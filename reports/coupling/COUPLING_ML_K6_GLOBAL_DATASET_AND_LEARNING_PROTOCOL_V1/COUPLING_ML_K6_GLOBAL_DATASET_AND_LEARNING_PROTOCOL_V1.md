# COUPLING_ML_K6_GLOBAL_DATASET_AND_LEARNING_PROTOCOL_V1

**状态：READY_FOR_CHAT_SCIENTIFIC_REVIEW / PROPOSAL_ONLY。没有 HF 或训练授权。**

## AUTHORITY / GIT

远端为 DESKTOP-NNE313K / desktop-nne313k\dell。worktree 为 D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1，branch work/mdc-np-coupling-ml-v1，输入 HEAD cd0531632b1d9ba4fac3bed15457820f2f7c3882，upstream 0/0。参考 HEAD 03f4a5b737a99bb0ec5b6a0d38b64a5d51ad1a3f 是其祖先；后续提交 4274851（EXT02 pre-entry audit）与 cd05316（local DOE）。未 reset。

已核查 physical contract SHA 32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5、32G authority SHA 0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e、domain authority SHA 93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f、H1 SHA 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd、expansion manifest SHA 4cf521c18576c34407c158a20f748fe560910909728bed5cdadf53ec9fbe2e7f、exclusion registry SHA 78f48a4400d5ab469a2054a8ad849d5cae16cb4bee042e2b542529a78973bb80。

任务开始有 164 项既有 untracked 状态、没有 tracked 修改。未清理、未覆盖、未纳入本任务提交。

## DATASET COUNTS / COVERAGE

32G 只有32个独立 ordered geometry group、672个 geometry×wavelength行、4704个order行，21个波长。每个 D1…D6 覆盖100–230 nm，5 nm格点；但这是恢复出的候选范围，不是开放的生产设计域。归一化距离为 sqrt(sum((delta D/130)^2))；最近邻 min/median/mean/max = 0.7892/0.82266/0.83497/0.93660。半径1.0内邻居数 median/mean/min/max=4/4.125/1/14。496个成对比较中，geometry distance 与 C_hat 对称相对L2变化的 Pearson/Spearman 为 -0.253/-0.245；与 routing RMS 为 -0.0875/-0.102；与 mean absolute log(P_scale ratio) 为 -0.129/-0.120。距离0.5–1.0、1.0–1.5、>=1.5三段的中位数 (C_hat,routing,P_scale) 分别为 (1.247,0.1499,0.2403)、(1.145,0.1470,0.2184)、(1.082,0.1399,0.2098)；没有距离<0.5的样本对。所有成对比较均相互依赖且通常多个直径同时改变，不能解释成单坐标导数或因果关系，也不能证明映射光滑或不可学习。

冻结的新点集共160个逻辑 geometry proposal：
- 开发128 = 冻结的12个 S31 轴向点 +116个全域点。
- 确认32 = 冻结的4个 S31 组合点 +28个全域点。
- 原32G只作开发，不计入新增预算，永不作为独立确认集。

全域算法：6维 scrambled Sobol 量化到有序27^6格点，seed=20261004，32768次抽样，D=100+5*floor(27u)，接着相对固定参考集顺序 maximin，距离尺度130 nm。排除与原32G、local16、reserve6、protected25及冻结的源候选池48点重复的向量；相同距离用Sobol流中最早的唯一行决胜。144个全域点中，索引5、10、…、140分配给28个全域确认点，其余116个是开发点。选择没有使用响应、模型误差、routing或P_scale。
Deterministic rerun under N:\anaconda_envs\RCP_LCP (SciPy 1.15.3) preserved candidate CSV SHA-256 f09d238177054e71741670ae263411949731ff78108ac9fd00801a277fdd8c31 and fold-manifest SHA-256 5e36a0628222de1b565505dc5c05ecd29b21f966cab422ad99a300b049c0e098; the coverage audit was refreshed with its generation timestamp.

全部坐标范围覆盖100至230 nm；每个坐标使用27个离散值中的24–27个。160点中112点触及至少一个精确边界面，151点距某边界面不超过10 nm。全部新点最近邻中位数0.5493；仅看144个全域点，min/median=0.5217/0.5534。全体最小值0.0544来自有意密集的local轴向/组合点，不代表全域点稠密。28个全域确认点到全域开发点的最近距离 median/min=0.5540/0.5260；4个local组合点到local轴向点为0.0860。

另用独立seed 20261005的32768点Sobol格点作近似联合覆盖检查：到原32G的最近距离q95为0.7277；加入新增开发点后q95为0.5073；加入全部点后q95为0.4757。这是可复现抽样近似，不是对27^6的穷举覆盖证明。

D1…D6物理顺序保持不变，不做cyclic/permutation扩增。精确local点在候选CSV和原始local manifest中。S31 anchor=[220,195,210,150,140,210] nm，边界余量10 nm，周期相邻净间隙75 nm。

## GEOMETRY / MANUFACTURING

固定合同：ordered K6、固定 MDC P1_ZL1_ALTERNATIVE_G3_A3、237 nm spacer、500 nm柱高、290 nm pitch、1740×290 nm周期、GaN到air、+z正入射X偏振、440–460 nm每1 nm、Native-M1材料、z PML。输出是完整复数Cartesian C_hat、独立正值P_scale、冻结H2和原conjunctive H1。

160个proposal均唯一、在范围及5nm格点内。周期净距按 gap_i=290-(D_i+D_(i+1))/2 计算并包含D6→D1，最小为60 nm；半胞元横向几何余量按145-max(D)/2计算，最小30 nm。这些是几何/数值包络检查；本任务没有为144个全域点构造FSP或运行mesh LOAD/readback，因此不声称其完成setup preflight。独立制造限制authority仍缺失，不宣称制造合格。

恢复的几何authority写明扩展仅限冻结48点源池（其中32 eligible）。144个新全域向量刻意避开该池。因此所有新身份/向量均未登记到owner-controlled source authority；未来任何HF前都必须由authority owner批准精确扩展并逐case登记。候选ID仅是提案，不是Runner准入ID。

## MODEL / VALIDATION PROTOCOL

只冻结两个全域候选：
A. 对六个训练标准化ordered直径输入的多输出RBF KRR。
B. Cartesian PyTorch MLP：共享6→32→32 GELU trunk，分开的线性C_hat及log-P_scale head，588个Re/Im状态通道和21个P_scale通道，参数数21,377。

每个geometry作为一个样本，目标包含完整21波长谱 C_hat[21,7,2] complex 与 P_scale[21]，共609个real target。禁止把波长、节点或patch行当独立样本；禁止NP/OOD输入、PCA、polar、hybrid或residual。所有输入、输出归一化仅拟合当前训练组。P_scale使用log预测并按该训练组log均值/标准差反变换后取exp。现有672个P_scale真值全为正，min=0.0539231、max=0.831680、零值0；不加epsilon、不clip、不用oracle。未来遇到非正标签或非有限/溢出输出，按失败报告。

冻结loss为标准化Cartesian state MSE + 标准化log-P_scale MSE，两个项等权。A的9种组合：RBF gamma {1/6,1/3,2/3} × ridge alpha {1e-4,1e-2,1}。B固定width32、AdamW lr=1e-3、weight decay {1e-5,1e-4,1e-3}、seeds {0,1,2}、最多1000个full-geometry update、inner validation patience50/min_delta 1e-5。不扩架构/rank/loss/seed搜索。KRR为确定性算法；seed-stability gate不适用且不能宣称通过。

开发估计采用新增128开发几何的4-fold grouped outer split，每折留32个完整几何组（3 local axis +29 global），原32G始终只作训练。每折内部3-fold geometry-grouped调参。所有21波长随geometry组划分。nested learning curve总样本数32/64/96/128，每个规模都含全部既有32G，另加0/32/64/96个嵌套新开发点。最后在全部160个开发组上训练final models。未来fit上限284：outer inner 108 KRR+108 MLP，learning-curve refit 16 KRR+48 MLP，final development 1 KRR+3 MLP；每个MLP最多1000 epochs。本任务实际0 fits。

确认响应生成或打开前，冻结并hash模型、超参数、train-only预处理、loss、适用域、评估器及32个确认点预测文件。然后仅评估4个local组合和28个全域点一次，不按结果挑模型/设置。若确认响应以后改作开发集，须记录转换并另建封存确认集。

评价完整复数state、P_scale、H2 routing、source-normalized绝对阶功率、传播总功率、相位诊断和原H1所有项。显著相位诊断mask仅供评价：每个波长真值 |C_hat|^2 / 所有传播坐标 |C_hat|^2 总和 >=1e-4。H1阈值维持原值且conjunctive：state相对RMSE median/q95<=0.5/0.8；routing eta<=0.05/0.1且Pearson>=0.95；source-normalized absolute-order RMSE<=0.05/0.1；thresholded relative absolute-order<=0.3/0.75、significance=0.0009885656815447454；total-power relative<=0.15/0.3且Pearson>=0.95；seed-state median std<=0.03。在这些cohort上达到数值门槛也不代表production admission。确认响应尚不存在。

## LOCAL DIAGNOSTIC

local模型是固定仿射映射，输入[1,(D1-anchor1)/5,…,(D6-anchor6)/5]，输出完整Cartesian C_hat和独立log-P_scale。未来执行12个leave-one-axial-geometry-out fits，每折以S31及另外11个轴向几何训练，再做S31+12的最终fit。每折重新拟合全部预处理/敏感度；留出几何及其21波长不能进入有限差分/Jacobian、归一化、预处理或拟合。冻结local模型及预测后才打开4个local组合响应。

轴向差分只是局部响应线索，不证明多坐标交互项可忽略。当前没有经验证的跨run重复性误差；EXT02双高度验证是跨高度一致性，不可替代重复性。没有测得数值误差/重复性前，不宣称±5 nm响应可分辨。

## RUNNER / MONITOR DEPENDENCIES

Runner worktree HEAD is 2a6f515a1d28002bca3c4e30094dbf66e463fb17 and upstream is 0/0. At final read-only audit, tracked files adapter.py and runner.py had uncommitted modifications; their diffs appear to add a controlled-admission route, preflight-setup command and monitor-readback hooks. These edits were not committed or accepted as formal authority, and this task did not modify the Runner worktree. Three existing untracked prototype files were also preserved. The committed production authority remains READY, one serial slot/no replay, and the original 12 IDs only.

EXT02 two-air-plane validation remains BLOCKED_PREENTRY under committed Runner authority because no formally admitted EXT02/monitor-overlay route is recorded. The uncommitted worktree draft does not change this status and was not used as authority. This is not a numerical monitor failure; no independent second NP-above air field was saved, so near-field cross-height validity remains unverified. Production POSTNP monitor and contract were not changed.

先前local DOE的16个task-private FSP仍存在；本次只读复核其FSP hash及LOAD-only证据hash，16/16匹配，总计8,322,928 bytes。它们不是Runner canonical input。本任务新建FSP 0个，也未生成global点的setup或Runner manifest。

## TIME / STORAGE ESTIMATE

从D:\apcd_runtime\gpu_production_runner_v1\runs直接核查11个真实DONE case tree。created_unix到done_unix中位668.129秒/例、均值673.759、范围653.241–698.565。每case保留目录median 369,078,434 bytes、mean 369,137,523、range 368,813,524–369,874,724。目录包含FSP、native/truth H5、raw NPZ及postprocess/log metadata。S35仍单独保留FAILED_POSTENTRY；不纳入DONE样本估计，恢复证据不代表replay或失败率。

当前正式单槽串行下，128开发点预计median 23.76小时，随后32确认点5.94小时，总计29.69小时；均值总计29.94小时；按观测min/max线性估算总计29.03–31.05小时。按实测median输出包估计，开发约44.00 GiB、确认约11.00 GiB、合计约55.00 GiB。未计临时工作区开销、额外双面monitor overlay或可能的失败恢复副本；不假设并行。以上只是外推，不是速度保证或执行许可。

冻结协议保留了此前local任务的粗略单case bundle估值369,628,975 bytes。RESOURCE_ESTIMATE_V1.json依据当前Runner目录的11个DONE样本把此估值更新为369,078,434 bytes；只修正时间/存储估算，没有修改抽样、模型、split、loss、metric或response-access规则。

## EXECUTION COUNTS / LIMITATIONS

本任务solver entries 0、FDTD/GPU Runner invocations 0、training fits 0、P_scale fits 0、新FSP 0、reserve launch 0。候选生成器只读取有序几何元数据，并写几何候选、fold表和覆盖审计，不读truth数组或响应值。确认响应与模型结果都不存在，因此本轮没有回答“增加覆盖能否持续改善泛化”，只冻结了可执行的数据与验证设计。

未闭环限制：owner source-authority扩展、独立monitor验证、制造约束authority。几何可行和零solver检查不等于物理准确或制造通过。

## NEXT — DO NOT EXECUTE

等待Chat科学评审此160点提案及launch dependencies。本任务不授权HF、FSP构造、训练或P_scale拟合。
