# COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1

**STATUS：PASS，受控4-fit实验完整完成。科学裁决：LOCAL_SCALE_PHASE_NO_CLEAR_GAIN。** A/B/C均仍为 DEVELOPMENT_H1_FAIL。

## Authority及实际执行

DESKTOP-NNE313K/dell；worktree `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`；branch `work/mdc-np-coupling-ml-v1`；起点 HEAD `cc53c98d4027b68756ff979ccfc9fd5954c70e2d`。解释器 `N:\anaconda_envs\RCP_LCP\python.exe`。根目录无AGENTS/CONTINUATION，采用用户提供的项目规则及上一科学审计的scoped continuation。现场版本、完整输入SHA、156G开发身份、四折模型、原始预测及正式H1/H2均核验。

实际新增4个CPU phase-head fits，每fold一次，无重试、核尺度/seed搜索或查询时拟合。幅值、P_scale、Cartesian baseline、MLP、NP/MDC拟合均0；FDTD/replay/confirmation response access均0。fit前原子记录invocation，完成后保存checkpoint、原始cos/sin、rho、预测、训练预测及SHA。旧65G/268-fit/NP88/幅相8-fit与确认预测保持不变。

## 唯一冻结数学合同

有序6D输入使用原B每fold训练geometry mean/std；距离为该标准化空间欧氏距离（不同于描述性130 nm尺度）。定义训练距离 `r_i²=min_(j≠i)||x_i−x_j||²`，`ell²=median_i r_i²`，`gamma=1/(2ell²)`。核为 `K(x,y)=exp(−gamma||x−y||²)`，alpha=1，float64。

四fold gamma分别0.2453374415、0.2407898859、0.2388632168、0.2436999799，精确等于上一提案的输入侧dry-run。它是**每fold一个固定尺度的stationary RBF**，不是逐查询局部fit，也不是非平稳核。推理使用全部124个训练几何的固定kernel；不依据查询HF响应选择邻域或参数。

少于2个有限独立训练几何、重复几何/零最近距离或非法尺度明确BLOCKED；不加epsilon或裁剪。边界使用同一核，不排序、镜像、cyclic扩增或响应校正。核矩阵严格对称，最小特征值1.66e-6…3.81e-6，正则化条件数17.97…18.75；原始K条件数约4.47e6…1.07e7，但alpha=1后求解稳定。阈值及PSD数值规则在首个fit前冻结，残差逐fold保存。

完整588D phase targets：21×7×2×[cos,sin]，沿用原B interleaved顺序、弱训练模态fraction<1e-4/零幅值时[1,0]、训练coordinate means/globalRMS。没有PCA或删阶。单位圆投影、64eps近零fallback及复数重建保持原规则；未采用上一圆盘诊断、oracle phase alignment或额外归一化。

## 零fit预检查与绑定

156G数据及所有原始inventories核验；每fold train124、heldout32/31/30/31，合计124唯一heldout。A/B原H1报告逐元素复算一致。对应训练/验证几何不交叉，21波长整组；尺度、targets、means/RMS及fallback只来自对应训练组。

零fit数学检查通过；**6项pytest回归通过（7.83s）**，合成estimator fits=0。覆盖核对称/PSD、已知邻域尺度、查询不改变训练尺度、非法近邻拒绝、单位圆fallback、完整复数及H2重建、仅train函数有一个fit调用点。全部通过后才执行正式4 fits。

C与B的294D幅值head预测、21D P_scale均**逐元素一致**。复数abs的最大浮点差为3.33e-16，H2 routing最大差3.89e-16、absolute-order最大差1.67e-16、total差0，均在预冻结1e-12容差内。相位改变引起这些舍入差，不是幅值或归一化改动。模型save/reload预测逐元素一致。

## 三组完整指标

|指标：median / q95|A Cartesian|B 原幅相|C 邻域尺度相位|
|---|---:|---:|---:|
|state_relative_rmse|0.872970 / 1.086444|1.039131 / 1.318987|1.039380 / 1.311795|
|amplitude_relative_rmse|0.672675 / 0.797020|0.430317 / 0.601391|0.430317 / 0.601391|
|routing_eta_rmse|0.182086 / 0.297147|0.122364 / 0.207292|0.122364 / 0.207292|
|absolute_order_source_normalized_rmse|0.064621 / 0.115201|0.048482 / 0.085943|0.048482 / 0.085943|
|thresholded_absolute_order_relative_median|0.801501 / 0.937560|0.647095 / 1.192286|0.647095 / 1.192286|
|p_scale_relative_rmse|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|
|total_power_relative_rmse|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|
|absolute_phase_rmse|1.220526 / 1.768362|1.281598 / 1.862608|1.298240 / 1.874707|
|relative_phase_rmse|1.721010 / 1.961726|1.750114 / 1.963318|1.745737 / 1.969461|
|nonzero_state_rmse|0.973604 / 1.129514|1.162706 / 1.677441|1.173682 / 1.675778|
|norm_ratio|0.507299 / 0.733121|0.875557 / 0.921973|0.875557 / 0.921973|

C state中位数几乎不变且略差，q95小幅改善；绝对相位median和q95均恶化。非零阶state median恶化、q95略改善。C相对Cartesian state仅14/124改善，110/124恶化，四fold paired median均更差。因此不能认为相干学习瓶颈已解决。

## 配对几何与fold

|Fold|state C−B median|state改善/恶化|相位 C−B median/rad|相位改善/恶化|state C−A median|
|---|---:|---:|---:|---:|---:|
|1|-0.000278|16/16|0.005157|15/17|0.161144|
|2|-0.004604|21/10|-0.013661|23/8|0.182615|
|3|0.002147|14/16|0.005384|14/16|0.151422|
|4|-0.000570|16/15|0.003081|15/16|0.181281|

C相对B：state 67/57改善/恶化，paired median=-0.001340；绝对相位67/57，paired median=-0.004736。**paired median小负数不等于两组总体median改善**，二者统计定义不同，不能只挑有利口径。相位仅fold2的paired median改善，其余三fold恶化。

逐geometry完整三组指标、两个主要delta及worst10均保存；不将geometry×21λ作为独立样本或声称统计显著。最大state相对B退化G013：1.01503→1.07013（+0.05510）；G076：0.88916→0.94345（+0.05428），其相位0.86842→1.05928（+0.19087 rad）。全局worst state仍G009，B1.48636→C1.47379，略降但仍显著差于A1.15656。完整mode tails未因少数改善被隐藏。

## rho、相位SSE及逐阶结果

强模态rho median/q95：B0.359144/0.824084→C0.364344/0.847648；rho<0.5占比69.27%→68.96%，<0.1为5.46%→5.31%。收缩仅轻微减弱。rho增大没有带来方向精度提高，仍不是校准置信度。

幅值SSE均596.35762；phase SSE2596.13773→2601.88617，相位占比81.3200%→81.3536%。完整state norm ratio仍约0.87556，恢复范数不能替代方向准确。弱TE仍完整保留，但其SSE约1e-9级占比，不驱动科学结论。相位采用固定truth模平方权重和1e-4显著mask，并保存阈值敏感性；该坐标权重不等同于H2的kz加权物理功率。

|TM阶|B相位 median/q95|C相位 median/q95|B state median/q95|C state median/q95|
|---|---:|---:|---:|---:|
|-3|1.567746/2.453014|1.513322/2.445830|1.282963/2.255860|1.291818/2.257112|
|-2|1.393971/2.634029|1.438090/2.536458|1.275626/2.483271|1.243811/2.521987|
|-1|1.013574/2.630800|0.966482/2.602200|1.055411/2.674015|1.050630/2.705776|
|0|0.457341/2.037062|0.441851/1.901643|0.584045/2.197658|0.571547/2.185737|
|1|1.239354/2.473998|1.228369/2.483492|1.096359/2.468508|1.123887/2.482286|
|2|1.351335/2.554442|1.347283/2.532603|1.272997/2.417611|1.206580/2.466717|
|3|1.534690/2.521313|1.566911/2.554782|1.350181/2.260886|1.336742/2.258407|

-3相位median/q95改善，但其state median/q95略恶化。+3相位median/q95恶化，state略改善。-2相位median恶化、q95改善，其state median改善、q95恶化。没有一致的高阶收益。+1 state median/q95从1.09636/2.46851恶化为1.12389/2.48229。方向/强模态错误仍可导致较大order-relative state tails，不能从rho上升或某阶median改善宣称有效。

## 邻域和边界分层

冻结距离分箱：CLOSE≤1、MEDIUM(1,2]、SPARSE>2，依据训练标准化空间。未按结果移动阈值。

|分层|n|state C−B median|相位 C−B median|state C−A median|
|---|---:|---:|---:|---:|
|CLOSE|11|-0.006185|-0.008340|-0.080490|
|MEDIUM|113|-0.000772|-0.002817|0.182331|
|DEEP_INTERIOR|24|-0.008983|-0.015093|0.163967|
|EXACT_BOUNDARY|45|0.001732|-0.002110|0.161734|
|NEAR_BOUNDARY_NONEXACT|55|-0.001190|0.001281|0.173096|
|LOCAL_AXIS|11|-0.006185|-0.008340|-0.080490|
|SPARSE|0|N/A|N/A|N/A|

CLOSE恰为11个S31局部轴向heldout点，state和相位有小幅改善；这一个局部簇不能代表全域。113个全域heldout均在MEDIUM；SPARSE为空，所以没有证据评价该预注册稀疏bin，亦不能据此称全域六维覆盖密集。

深内部小幅改善；精确边界state paired median恶化，近边界相位paired median恶化；最差退化按case保存。近邻距离与state/phase delta的Spearman为0.24300/0.21005，仅描述性关联。不能证明改善由近邻因果产生。D6_M05缺失，未补标签；±5 nm受控重复性误差未知，局部11点不是完整六维局部验证。

四fold训练state median从B的0.54248…0.56092降至C的0.46374…0.47200；训练相位median从0.48545…0.51977降至0.37084…0.38638。训练拟合确实改善，但heldout整体无清晰收益，不能将训练改善当成泛化进展。TRAIN_VS_HELDOUT_DIAGNOSTIC保留完整数值，未用于checkpoint或核参数选择。

## 冻结H1/H2

A全部primary gates失败；B/C只有absolute-order达到，state、routing、thresholded-relative、total/P_scale仍失败，seed stability=N/A（确定性单seedKRR）。

Routing Pearson A=0.47060067、B/C≈0.43925728；total Pearson三组均0.90458786。P_scale/total median/q95=0.248064/0.757838保持不变。routing与absolute-order收益保留是冻结幅值及decoder无相位交叉项的结果，不是新phase head改善了功率预测。

## 科学裁决及限制

**LOCAL_SCALE_PHASE_NO_CLEAR_GAIN**，按照fit前规则：未同时改善完整state与强模态相位median/q95；更未超过Cartesian。没有以q95少量下降、67个paired wins或rho变大升级为成功。

OBSERVED：当前唯一训练邻域尺度核未带来清晰总体收益；幅值和功率收益合法保留。SUPPORTED_HYPOTHESIS：局部簇/深内部可能更容易预测相位，但改动不足以解决全域方向问题。UNRESOLVED：其他真正局部或物理相位表示能否泛化；本实验只是stationary RBF长度尺度的一次受控变更，不能否定所有局部条件化。

不建议自动追加gamma/alpha/seed搜索。停止该pilot，交Chat重新评审相位模态结构和局部覆盖证据；已有有限局部收益可以保留，但不能作为追加fits的自动授权。原开发集已反复参与方案选择，本次仍是开发探索，不是独立确认或生产准入。

## 产物、隔离与续接

LOCAL_SCALE_PHASE_FROZEN_SPEC、ZERO_FIT_PREFLIGHT、FOUR_FOLD_FIT_MANIFEST、LOCAL_KERNEL_NUMERICAL_AUDIT、FIT_LEDGER、每fold provenance、MODEL_SHA_INVENTORY、原始phase/rho及C_OOF NPZ完整保存。THREE_WAY_PAIRED_COMPARISON与PAIRED_GEOMETRY_METRICS.csv覆盖全部124案；PHASE_HEAD_RESULTS、NONZERO_ORDER_PHASE_ANALYSIS、NEIGHBORHOOD_DENSITY_DIAGNOSTIC、H1_H2_EVALUATION和TRAIN_VS_HELDOUT_DIAGNOSTIC保留诊断细节。

32个confirmation响应仍封存；28份既有confirmation输入预测/模型SHA未改。0 FDTD/replay/P_scale/amplitude/baseline fits，4/4 phase fits。FINAL_ISOLATION_CHECK验证旧产物及确认输入预测哈希；未触及GPU V2。只提交本任务allowlist文本/代码/CSV，模型及NPZ保留远端完整SHA。外部dirty/staged保留，正常push，最终HEAD见DELIVERY_RECEIPT。恢复先读本CONTINUATION与账本，任何非COMPLETE的已调用fit不得盲目重训。

## 最终A–N

A PASS（执行完成），科学NO_CLEAR_GAIN。B4 fits。C训练最近邻平方距离median定义固定RBF gamma。D state A0.872970/1.086444、B1.039131/1.318987、C1.039380/1.311795。E强模态相位总体未改善。F非零阶state无一致改善。G rho轻升但phase SSE稍增。H routing/absolute-order收益保留。I无完整state增益超越Cartesian。J全部124几何/fold配对已保存，收益混合。K H1FAIL。L这一个尺度规则不支持继续自动扩fit，局部条件化更广泛可行性仍未定。M Git/report/SHA见DELIVERY_RECEIPT及SHA_INVENTORY。N confirmation封存及原28预测保持不变。
