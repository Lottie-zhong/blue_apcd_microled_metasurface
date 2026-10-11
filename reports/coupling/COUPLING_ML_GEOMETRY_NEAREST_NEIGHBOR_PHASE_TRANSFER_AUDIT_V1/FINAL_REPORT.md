# COUPLING_ML_GEOMETRY_NEAREST_NEIGHBOR_PHASE_TRANSFER_AUDIT_V1

**STATUS：PASS，零fit诊断完成。科学裁决：NN_PHASE_GLOBAL_NO_CLEAR_GAIN_LOCAL_SIGNAL_ONLY。四组完整H1均FAIL。**

## Authority、冻结合同与执行

主机DESKTOP-NNE313K/dell；worktree `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`；branch work/mdc-np-coupling-ml-v1；起点HEAD a1a28c3b212661e8964fdde8057dd86291a295a5。解释器N:\anaconda_envs\RCP_LCP\python.exe。采用用户AGENTS及上一scoped continuation；worktree根目录无AGENTS/CONTINUATION。正式156G inventory、四折124G refit、原A/B/C模型/预测、H1/H2及原始inventories完整SHA核验。

CPU training/P_scale/FDTD/replay/confirmation access均0；合成estimator fits=0。只读恢复已训练幅值模型predict，未调用fit/scaler fit。原268-fit/NP88/幅相8-fit/邻域4-fit、truth及confirmation预测不修改。

唯一D：ordered D1..D6，以(D−100)/130归一化；每fold只在原124训练身份中取欧氏1-NN。先以整nm计算平方距离，精确平局按case ID字典序。无k/权重搜索，无HF oracle或公共相位对齐。294模态按原21λ×7m×TE/TM、1722nm reference逐坐标迁移。邻居training模平方份额>=1e-4且非零时取unit phase，否则unit1；仅训练标签确定，不用heldout幅值决定fallback。

冻结B/C的294D幅值head逐元素复用；21D P_scale逐元素一致；D=amplitude×transferred_unit_phase。没有额外归一化、clipping、排序或删模态。数值abs误差最大2.220e-16，H2与B/C routing差最大4.441e-16，absolute-order最大1.943e-16，total差0；满足预登记1e-12容差。

## Split与泄漏审计

156G=旧32+11局部轴向+113全域。124个唯一heldout=11局部+113全域；旧32一直在四fold训练中，不是本轮heldout。每fold124训练，heldout32/31/30/31。原n124嵌套子集不是所有outer训练池点：fold2未使用G077、fold3未使用G036/G076、fold4未使用G054；这些身份不加入NN候选。所有训练/heldout交叉为0，21λ不拆组；四折身份原样。历史K6V1_EXT02为合法旧32开发点，独立双面诊断EXT02排除。

3个查询出现距离平局，已确定性处理；弱/零training坐标18230/36456=50.0055%，主要是弱TE；对应冻结预测幅值平方份额7.421379e-05，训练邻居坐标能量平均份额5.298782e-08。该能量权重不等同kz加权H2功率。每案邻居、fold、完整training provenance和SHA入口均保存。

## 四组指标：几何median / q95

|指标|A Cartesian|B 原幅相|C 邻域尺度|D 1-NN相位|
|---|---:|---:|---:|---:|
|state_relative_rmse|0.872970 / 1.086444|1.039131 / 1.318987|1.039380 / 1.311795|1.132484 / 1.360227|
|absolute_phase_rmse|1.220526 / 1.768362|1.281598 / 1.862608|1.298240 / 1.874707|1.413415 / 1.899371|
|relative_phase_rmse|1.721010 / 1.961726|1.750114 / 1.963318|1.745737 / 1.969461|1.809288 / 1.996195|
|nonzero_state_rmse|0.973604 / 1.129514|1.162706 / 1.677441|1.173682 / 1.675778|1.227281 / 1.673067|
|amplitude_relative_rmse|0.672675 / 0.797020|0.430317 / 0.601391|0.430317 / 0.601391|0.430317 / 0.601391|
|norm_ratio|0.507299 / 0.733121|0.875557 / 0.921973|0.875557 / 0.921973|0.875557 / 0.921973|
|routing_eta_rmse|0.182086 / 0.297147|0.122364 / 0.207292|0.122364 / 0.207292|0.122364 / 0.207292|
|absolute_order_source_normalized_rmse|0.064621 / 0.115201|0.048482 / 0.085943|0.048482 / 0.085943|0.048482 / 0.085943|
|thresholded_absolute_order_relative_median|0.801501 / 0.937560|0.647095 / 1.192286|0.647095 / 1.192286|0.647095 / 1.192286|
|p_scale_relative_rmse|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|
|total_power_relative_rmse|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|0.248064 / 0.757838|

State相对RMSE=||Cpred−Ctrue||F/||Ctrue||F，全部21λ/7m/TE/TM；非零指标只排m=0。phase是principal circular差，固定truth模平方加权、每λ份额>=1e-4，仅用于评价，另保存阈值敏感性。无oracle alignment。范数比接近1才好，paired raw decrease字段不能当该项改善。

## 配对几何与四fold

|对照|state改善/恶化|state D−baseline median|相位改善/恶化|相位 D−baseline median|
|---|---:|---:|---:|---:|
|D vs A|15/109|0.242313|44/80|0.168436|
|D vs B|43/81|0.071332|46/78|0.118328|
|D vs C|39/85|0.059932|47/77|0.107597|

|Fold|n|state D−A median|D−B|D−C|phase D−B|
|---|---:|---:|---:|---:|---:|
|1|32|0.252674|0.076256|0.097902|0.122086|
|2|31|0.232389|0.012571|0.015862|0.006003|
|3|30|0.270443|0.068101|0.051978|0.162015|
|4|31|0.234250|0.082807|0.063341|0.117115|

D四fold state paired median相对A/B/C均恶化；相位相对B四fold均恶化。逐案CSV及JSON保存全部124案、delta与worst10。不将波长/模态当独立样本，不声称显著性。

## 阶次TM显著相位与state

|m|B phase median/q95|C phase median/q95|D phase median/q95|D state median/q95|
|---|---:|---:|---:|---:|
|-3|1.567746 / 2.453014|1.513322 / 2.445830|1.559508 / 2.768699|1.305900 / 2.358374|
|-2|1.393971 / 2.634029|1.438090 / 2.536458|1.570553 / 2.813321|1.339216 / 2.635204|
|-1|1.013574 / 2.630800|0.966482 / 2.602200|1.379637 / 2.667734|1.203757 / 2.887332|
|0|0.457341 / 2.037062|0.441851 / 1.901643|0.668996 / 2.122103|0.707212 / 2.245239|
|1|1.239354 / 2.473998|1.228369 / 2.483492|1.272926 / 2.644437|1.212791 / 2.451531|
|2|1.351335 / 2.554442|1.347283 / 2.532603|1.521870 / 2.766437|1.302927 / 2.626799|
|3|1.534690 / 2.521313|1.566911 / 2.554782|1.621479 / 2.611360|1.379215 / 2.229766|

m=0通常更容易，+1/-2/±3方向误差仍较大；按模态精确数字见上表。少数阶median/q95混合变化不等于完整state通过；所谓“非局部性”这里只是稀疏几何空间的预测困难，没有证据证明物理耦合机制非局部。TE完整保留但能量极弱，不驱动模型选择。每波长诊断另保存，全部坐标预测在D_OOF_PREDICTIONS。

## 几何距离与局部覆盖

|分层|n|距离median/q95|D state median/q95|D phase median/q95|
|---|---:|---:|---:|---:|
|<=0.1|11|0.038462 / 0.038462|0.306594 / 0.518565|0.214179 / 0.507340|
|(0.1,0.25]|0|N/A / N/A|N/A / N/A|N/A / N/A|
|(0.25,0.5]|52|0.489535 / 0.497033|1.134145 / 1.342214|1.426415 / 1.938139|
|>0.5|61|0.520298 / 0.593356|1.153642 / 1.366911|1.490282 / 1.887760|
|LOCAL_AXIS|11|0.038462 / 0.038462|0.306594 / 0.518565|0.214179 / 0.507340|
|GLOBAL|113|0.504418 / 0.563076|1.148178 / 1.363613|1.450569 / 1.908503|
|DEEP_INTERIOR|24|0.494790 / 0.546030|1.153004 / 1.365502|1.422817 / 1.825844|
|NEAR_BOUNDARY_NONEXACT|55|0.514580 / 0.593356|1.085113 / 1.341907|1.331653 / 1.891767|
|EXACT_BOUNDARY|45|0.492548 / 0.545005|1.145141 / 1.360907|1.504976 / 1.946550|

S31的11案最近邻均为训练anchor K6V1_S31，raw距离5nm、归一化5/130。该簇state median由B0.33940/C0.33279降至D0.30659，相位B0.26299/C0.25659降至D0.21418，但state q95升至0.51857、phase q95升至0.50734。D1两方向phase比B更差；D1_P05 state比A更差。不是所有轴向都改善。D6_M05仍缺失，未补造；5nm变化相对独立重复性误差未知。

全113点最近距离median=0.504418（原始nm距离=×130），均无<=0.25近邻。全域内距离与phase Spearman=0.024468、state=0.089309；混合全124分别0.261256/0.310335。混合相关主要受局部簇/全域的不同尺度影响，不能声称全域“越近越准”已成立。局部11距离严格相同，相关性N/A；空bin N/A，不输出NaN或虚构统计。

## H1/H2与权力边界

A全部primary gates FAIL；B/C/D仅absolute-order gate达到，state、routing、thresholded-relative、total/P_scale仍FAIL；seed stability N/A，不记PASS。全部原Pearson/逐geometry/H1原阈值保存在H1_H2_DIAGNOSTIC。D功率收益与B/C一致是decoder没有phase交叉项和幅值冻结的结果，不是NN预测提升功率。总功率=P_scale，所以误差相同。

已多次查看的开发heldout不是独立确认；32confirmation响应仍封存，原28输入预测SHA不变，未读取其响应。单P_XLIKE入射两输出polarization不等同完整Jones/多端口scattering。

## 科学裁决：唯一推荐B，不执行

**OBSERVED**：1-NN全域state/phase更差，局部一个5nm簇中位数较好但tails未获一致改善；幅值/power保留，完整H1FAIL。

**SUPPORTED_HYPOTHESIS**：极小局部域有相位信息，但当前全域density不足以支持几何邻域迁移。优先B：暂停继续试通用几何邻域模型，研究同物理参考下order-resolved相干相位机制，先核对既有跨阶/谱向物理关系，再编译一个可证伪的最小phase实验。已有-3/+3相对相位coherence median=0.817908仅支持继续审查模态关系，不证明任何模型准确。幅值/P_scale head继续保留。

**UNRESOLVED**：不能区分稀疏采样与真实快速几何变化；不能证明全域物理不连续。固定m0 relative并不普遍更平滑，没有合法完整LF scattering baseline，不能伪造complex residual。物理引导路线尚不是冻结可执行模型，不自行新增fits。

不选择A的主要否定证据：113全域点无清晰相位优势，四foldstate都恶化，局部样本只有一个anchor、tails变差。亦不选择C为不可逆结论：局部信息和既有模态结构尚保留可检验物理线索，不能宣称完整state永远不可学。

本轮不需要新增HF来完成诊断，也不建议为再试NN自动补样。任何未来局部策略须另审覆盖密度和受控重复性；EXT02跨高度一致性不等于跨run重复性，不等于156G绝对收敛。NEXT仅为Chat科学评审，不执行模型或solver。

## 实现检查、修复和交付

8项零fit数学检查PASS：精确tie、train候选排列不影响结果、弱/零相位固定规则、wrapping、相位单独改变H2不变、重复ID拒绝、AST无fit。四fold所有NN均来自合法train，A/B/C原正式H1逐元素精确复现。完整588+21有限、P_scale正值，原数据入口强校验。

AM01修正误把固定n124refit要求覆盖完整156union的实现断言，保存初始代码/协议；AM02修复NumPy整数JSON序列化及常量距离相关性报告，保存修复前代码/协议。没有改科学规则、邻居、阈值或预测选择，没有新fit或重跑科学实验；错误类型、触发行及修复前代码/协议保留，最终哈希对应实际代码。

所有要求的JSON、逐案CSV、原始D组合NPZ、数学测试与协议在本任务目录；二进制仅服务器持久化不纳入Git。SHA_INVENTORY含完整源代码/报告/NPZ SHA；DELIVERY_RECEIPT记录最终commit/push。foreign staged/dirty保留，未触及GPU平台。恢复先读CONTINUATION、SPEC、FINAL_ISOLATION_CHECK和inventory。
