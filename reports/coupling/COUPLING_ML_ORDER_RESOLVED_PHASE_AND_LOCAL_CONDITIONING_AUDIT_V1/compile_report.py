"""Compile final report from persisted diagnostics, without any fit."""
from pathlib import Path
import json,datetime,hashlib
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
OUT=ROOT/'reports/coupling/COUPLING_ML_ORDER_RESOLVED_PHASE_AND_LOCAL_CONDITIONING_AUDIT_V1'
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def write(n,s):(OUT/n).write_bytes(s.encode('utf-8'))
d=read('RAW_VS_UNIT_CIRCLE_ZERO_FIT_DIAGNOSTIC.json');m=d['metrics'];v=read('SCIENTIFIC_VERDICT.json');p=read('PRIORITIZED_MINIMUM_MODEL_SPEC.json');o=read('ORDER_RESOLVED_PHASE_STRUCTURE.json')
table=['|指标：median / q95|Cartesian KRR|正式单位圆幅相 KRR|单位圆盘零fit诊断|','|---|---:|---:|---:|']
for key in ['state_relative_rmse','amplitude_relative_rmse','routing_eta_rmse','absolute_order_source_normalized_rmse','total_power_relative_rmse','absolute_phase_rmse','relative_phase_rmse','norm_ratio']:
 table.append('|'+key+'|'+ '|'.join(f"{m[key][a]['median']:.6f} / {m[key][a]['q95']:.6f}" for a in ['Cartesian','Unit','Disk'])+'|')
orders=['|TM阶次|正式相位 RMSE/rad|state SSE 占比|真实谱向绝对相位增量 RMS/rad|m=0 相对相位增量 RMS/rad|','|---|---:|---:|---:|---:|']
for q in o['TM_orders']:orders.append(f"|{q['m']}|{q['unit_phase_error_RMSE_rad']:.6f}|{q['unit_state_SSE_fraction']:.2%}|{q['absolute_spectral_step_RMSE_rad']:.6f}|{q['relative_spectral_step_RMSE_rad']:.6f}|")
write('FINAL_REPORT.md',f'''# COUPLING_ML_ORDER_RESOLVED_PHASE_AND_LOCAL_CONDITIONING_AUDIT_V1

状态：**PASS，零fit审计完成**。原正式模型仍为 **DEVELOPMENT_H1_FAIL**；没有独立确认或生产准入。

## Authority、恢复与执行边界

主机 DESKTOP-NNE313K，用户 dell。Coupling worktree：`{ROOT}`；branch：`work/mdc-np-coupling-ml-v1`；起点 HEAD：`2f798d8d9393cfba346829b1ced50558d1f270e2`。现场 HEAD 与交接一致。解释器：`N:\\anaconda_envs\\RCP_LCP\\python.exe`，没有环境改动。

worktree 根目录没有 AGENTS.md 或 CONTINUATION.md；采用用户提供的项目规则与上一幅相pilot正式 scoped continuation。读取并核验正式156G数据、268-fit、NP88、复数模态审计及幅相8-fit inventories，完整输入 SHA 位于 DIAGNOSTIC_PROTOCOL。此次先冻结唯一规则，再执行实际诊断。原始模型、truth、标签、H1/H2、28份确认输入预测和历史结果均保留。

本轮计数：FDTD=0，replay=0，CPU training fits=0，P_scale fits=0，confirmation response access=0。仅调用已保存模型的 predict。没有新的 scaler/PCA/模型拟合，没有读取确认响应。

## 幅值head复用审计

294维幅值完整保留：21波长×7阶×TE/TM。四个checkpoint恢复出的 C_hat、原始相位向量长度和 P_scale 与保存预测逐元素一致。输出非负，没有负sqrt预测、相位fallback、模态丢弃、测试标签重缩放或额外归一化。

独立复算：幅值121/124几何改善，routing 106/124改善，absolute-order 101/124改善。各阶及TE/TM幅值误差、能量占比均在 AMPLITUDE_HEAD_REUSE_AUDIT。保留该head作为**开发阶段结构化幅值基准**，不将其单独认定为完整609D代理。

P_scale 为原独立物理域预测，四fold均逐元素一致。原H2：routing从加权模态能量计算，absolute-order=eta×P_scale，total=P_scale，因此总功率与P_scale误差相同；TE/TM之间没有相位交叉项。

## 唯一单位圆盘对照

标签：**RETROSPECTIVE_ZERO_FIT_DIAGNOSTIC**。

正式单位圆重建保留原规则；唯一新诊断为 `v/max(1,abs(v))`。零向量保持零；全零波长会被原H2拒绝，不补值或伪造功率。实际数据没有全零波长。幅值head和P_scale冻结，但圆盘重建的**有效幅值**变为 `A×min(rho,1)`，因此不保证routing或order power保留。没有缩放指数、阈值搜索、oracle alignment或事后调参。

{chr(10).join(table)}

圆盘state相对单位圆改善112/124案，但相对Cartesian仅42/124案。总复数SSE下降27.8946%；phase SSE从2596.14降至869.58，amplitude SSE从596.36升至1432.38。相位方向差最大仅2.00e-16 rad，固定truth权重的绝对/相对相位指标完全相同。

这表明强制恢复长度会放大错误方向的复数损失；圆盘降低损失依靠幅值收缩，**没有改善相位预测**。其routing、absolute-order及幅值收益丢失，范数比降至0.437。4个原始向量rho>1被固定规则投影，对应冻结预测幅值平方占比0.0472%。

原Cartesian与正式单位圆模型的H1报告被精确复现。原单位圆仅absolute-order gate达到；其他primary gates失败。圆盘所有primary gates失败。单seed确定性KRR的seed stability为N/A，不写成PASS。圆盘结果不替换任何原正式预测或authority。

## 相位向量长度rho

显著mask沿用每波长真值模平方占比≥1e-4，仅用于诊断。强模态rho median/q95=0.359144/0.824084；弱模态median=1，多数来自弱TE的固定圆周监督，不能解释为高置信度。

rho<0.1的显著坐标幅值加权相位RMSE=1.77797 rad；0.75≤rho<1为0.48130 rad。按几何汇总，rho与绝对相位误差Pearson=-0.67307、Spearman=-0.51896；与state误差Pearson=-0.69284、Spearman=-0.51666。各阶、波长、固定rho区间及阈值1e-6…1e-2敏感性完整保存。

**OBSERVED：rho有描述性的方向集中程度信息。UNRESOLVED：它是否能校准预测不确定度。** KRR inverse-scaled输出并非受约束的概率/凸组合，rho可能超过1。相关波长、坐标不是独立样本；相关性不构成因果证据，也没有得到可用于生产的置信阈值。

## 逐阶相位结构

{chr(10).join(orders)}

TM主导；TE坐标模平方占比9.20e-10，不能让弱TE相位驱动选择，但完整输出仍保留TE。本文相位诊断的能量权重指坐标模平方或幅值乘积，不等同于带kz权重的H2物理功率占比；routing/absolute-order指标始终使用原H2。+3相位最难，-3及-2也较差；六个非零阶合计贡献约88.25% state SSE，不能将问题归结于一个阶次。+1相位RMSE=1.42894 rad，目标阶仍困难。

绝对相位与m=0相对相位的谱向平滑性因阶次而异；m=0相对相位恒零只是定义结果。所有21个TM阶对均已报告。一个特别的描述性结构是-3/+3相对相位跨几何coherence median=0.81791；其余多数阶对较低。这不是新模型的性能证据，未据此增加候选。

phase wrapping通过principal unit-complex增量区分；弱幅值越阈值次数及wrap次数按阶保存。原物理参考面1722 nm、阶次及TE/TM基底符号不变。单一P_XLIKE入射的两个输出分量不能冒充完整Jones operator。

## 相对相位参考可行性

固定m=0 TM参考：156G的所有波长中零/弱计数均为0，最低坐标能量占比0.000320869；raw round-trip最大误差6.28e-16。固定身份在未知几何推理合法，但其绝对/common phase仍须实际预测。未来参考幅值足够强没有保证。精确零幅值采用unit1并完整保留相对坐标，可数学重建；近零的学习条件性仍需未来协议处理。

HF主导模态参考：433次谱向身份切换；使用已预测幅值选参考时与HF真实主导身份仅41.28%一致。未知几何不能读取HF argmax，不推荐真值选参考的方案进入预测。各阶TM参考仍需预测七个绝对order phases，不能只输出TE/TM相对相位。谱向相位差分需保留首波长14个绝对相位和后续增量；包含零幅值的round-trip最大1.48e-15，但未证明累计预测误差更小。

**相对相位并不普遍更平滑。** 全12090几何对绝对/相对相位距离median=1.57819/1.48603 rad；最近66对（归一化距离≤0.1）为0.30973/0.52072；S31的11轴向点为0.20730/0.33993。既有预测m=0 common phase pooled RMSE=0.68671、m=0-relative RMSE=1.39512 rad；两者权重不同，不是可相加的SSE归因比例。没有执行任何oracle相位对齐。

## 几何局部条件化

全部156个身份和12090几何对保留；有序D以130 nm归一化，nearest按几何距离确定，tie按case ID，未按响应选择。

实际fold的最近训练几何距离与相位预测误差Pearson=0.71659/Spearman=0.37837；邻居真值相位差与误差Pearson=0.71457/Spearman=0.54108。局部S31变化较小，D1轴向变化较大；11个有效轴向点及各阶统计全部保存。深内部、近边界、精确边界分别报告。

**SUPPORTED_HYPOTHESIS：邻域覆盖与相位方向预测有关，值得有限测试。** 全域113点没有归一化距离≤0.25的几何对，不能据此宣称响应物理不连续，也不能宣布局部模型已泛化。极近邻统计主要来自同一S31簇，几何对共享样本且相关。D6_M05缺失，六维±5 nm检查不完整。受控跨run重复性误差缺失；EXT02同run跨高度一致性不能替代重复性或绝对收敛，±5 nm响应是否可分辨仍未验证。

## 一个优先后续实验：仅提案，不执行

选择**训练邻域尺度条件化的相位KRR**：复用四个全秩幅值head及同一独立P_scale，仅重新训练588D绝对圆周相位head。保留原n124 train IDs、heldout 32/31/30/31、6D scaler、弱幅值监督、head尺度、alpha=1、float64、单位圆重建及fallback。只改变一个因素：

`gamma = 1 / (2 × median_i min_(j≠i) ||x_i-x_j||²)`

x仅来自当前fold训练输入，经原geometry scaler变换。零/非有限距离明确拒绝，不加epsilon。输入侧dry-run的四个gamma约0.245337、0.240790、0.238863、0.243700；原值1/6。不做k/gamma/alpha搜索，不读取heldout响应调尺度。它仍是stationary RBF，使用训练邻域定义长度尺度，**不是已经实现的局部Maxwell模型或逐样本标签插值**。

最小=最大**4个新增CPU phase fits**；baseline、amplitude、P_scale refit均0。只有一个候选；不追加common-relative、rho缩放或更大MLP。与保存的Cartesian和原幅相KRR严格配对，最终仍输出588D Cartesian C_hat+21D正P_scale，经原H2及全部H1。

研究收益需同时报告state median/q95、幅值/routing收益保留、逐fold/geometry及tails；不以新综合分数替代H1。比较JSON的norm_ratio“wins”字段仅表示数值下降，不能按误差改善解释；范数应接近1而非越小越好。失败只能说明此邻域尺度规则不足，不能证明局部物理不可学习。156G足以开展该有限开发实验，不需要为它先新增HF；但覆盖及重复性证据不足，无法提前保证成功。

开发数据已反复参与方法选择，下一试验仍属探索；不把相同heldout视作独立确认。32个confirmation继续封存，28份原输入预测及SHA未改动。新独立确认及重复性验证须另获授权。

## A–K裁决

A 保留幅值head。B 单位圆强制恢复长度放大错误方向损失；圆盘降SSE但损失功率收益。C rho具有关联信息，未校准。D +3、-3/-2困难，六非零阶共同主导。E 相对相位不普遍更平滑。F 固定m=0 TM合法可逆，在已观测数据强但未知几何无保证；HF主导身份不可oracle读取。G 局部条件化值得4-fit开发检验，尚未证明泛化。H 仅优先训练邻域尺度相位KRR。I 提议4 fits，实际0。J 该试验无需新增HF；±5 nm分辨性仍需独立重复性证据。K H1 FAIL及确认封存状态不变。

## 测试、产物与交付

12项数学检查PASS：零/极小幅值、wrap、固定/切换参考、谱向增量重建、圆盘有界与方向不变、SSE恒等式、H2相位不变性、幅值改变routing、独立total及AST零fit调用。初始fixture含全零波长，原H2正确拒绝；将拒绝测试与正能量H2测试分开，原preflight协议保留于 DIAGNOSTIC_PROTOCOL_ORIGINAL_PREFLIGHT，实施修复记录在当前协议中。科学规则未改动。

SHA_INVENTORY覆盖代码、报告、原始相位恢复NPZ、独立圆盘诊断NPZ及逐几何对CSV。原先921项无关dirty/runtime状态保留，foreign staged SHA再次一致。只提交本任务文本/代码/CSV；二进制保留服务器并完整哈希。最终Git与push记录在 DELIVERY_RECEIPT。完成后停止，交Chat科学裁决。
''')
write('CONTINUATION.md',f'''# {OUT.name} — COMPLETE
恢复先读 FINAL_REPORT.md、DIAGNOSTIC_PROTOCOL.json及ORIGINAL_PREFLIGHT、SCIENTIFIC_VERDICT.json、SHA_INVENTORY.json、DELIVERY_RECEIPT.json。
主机DESKTOP-NNE313K/dell；worktree {ROOT}；branch work/mdc-np-coupling-ml-v1；解释器 N:\\anaconda_envs\\RCP_LCP\\python.exe；起点HEAD2f798d8d9393cfba346829b1ced50558d1f270e2。
156G开发数据、124G匹配OOF；本轮0CPU/P_scale/FDTD/replay/确认响应。原268-fit、NP88、幅相8-fit及28确认输入预测不变。原模型仍H1FAIL。
唯一圆盘诊断state0.88956 vs正式Unit1.03913，但routing0.19330 vs0.12236，幅值0.71293 vs0.43032；方向完全不变。幅值head保留为开发基准；rho有关联但未校准。固定m0相对相位不普遍更平滑；局部S31更平稳，D6minus与重复性证据缺失。
下一提案仅4个phase KRR fits，训练NN定义gamma，复用幅值/P_scale；本任务未授权执行。等待Chat裁决，不自动训练、HF或改参考面。恢复报告使用保存JSON/RAW_PHASE_RECOVERY.npz，不重新prepare/refreeze，不试多个圆盘规则。无关dirty/staged保留，GPU平台未修改。
''')
files=[]
for f in sorted(OUT.rglob('*')):
 if f.is_file() and '__pycache__' not in f.parts and f.name not in ['SHA_INVENTORY.json','DELIVERY_RECEIPT.json']:
  files.append({'path':str(f),'relative_path':f.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
write('SHA_INVENTORY.json',json.dumps({'task':OUT.name,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'exclusions':['self','deliveryreceipt','__pycache__'],'execution_counts':v['execution_counts']},ensure_ascii=False,indent=2)+'\n')
print('REPORT_SHA',hashlib.sha256((OUT/'FINAL_REPORT.md').read_bytes()).hexdigest(),'INVENTORY_SHA',hashlib.sha256((OUT/'SHA_INVENTORY.json').read_bytes()).hexdigest())
