"""Write evidence-based AL50 closeout reports; no solver and no model fits."""
from pathlib import Path
import json,csv,numpy as np,datetime
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';S=D/'STAGE_50';C=Q/'APCD_COUPLING_AL50_V2_FINAL_SCIENTIFIC_CLOSEOUT';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2'
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(v) for v in row)+' |' for row in rows)
def main():
 m=rd(C/'MATCHED_EVALUATION_METRICS.json');local=rd(S/'LOCAL_DIFFERENCE_ACCURACY.json');inter=rd(S/'INTERACTION_TRUTH_AND_PREDICTION.json');prod=rd(D/'INDEPENDENT_PRODUCTION_RECONCILIATION.json');diag=rd(C/'LABEL_AND_COVERAGE_DIAGNOSTICS.json');assoc=rd(C/'ERROR_ASSOCIATIONS_NOT_CAUSAL.json');pol=rd(C/'EVALUATION_FAMILY_AUDIT.json');pairs=list(csv.DictReader((C/'ALL23_PAIR_ANALYSIS.csv').open(encoding='utf-8')));z=np.load(S/'FAST_DATASET_222G.npz',allow_pickle=False);ids=list(z['case_ids']);folds=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');ns=[len(f['heldout_old_ids']) for f in folds];random_top=float(np.mean([np.ceil(.2*n)/n for n in ns]));assert len(pairs)==69
 mt=table(['模型','P(+1) MAE','eta(+1) MAE','P_scale MAE','450nm mean-fold rho','Top20%召回'],[[k,f"{v['P_plus1_H2']['MAE']:.8f}",f"{v['eta']['MAE']:.8f}",f"{v['P_scale']['MAE']:.8f}",'未定义' if v['rho450_meanfold'] is None else f"{v['rho450_meanfold']:.5f}",'未定义' if v['top20_recall'] is None else f"{v['top20_recall']:.5f}"] for k,v in m['222'].items()])
 lc=table(['模型','156G P+ MAE','172G P+ MAE','222G P+ MAE'],[[k]+[f"{m[n][k]['P_plus1_H2']['MAE']:.8f}" for n in ['156','172','222']] for k in m['222']])
 localrows=[]
 for k in ['Mean','KRR','ExtraTrees','MLP']:
  a=local['MATCHED_172_BASELINE'][k]['P_plus1_H2'];v=local['ALL_V2_AVAILABLE'][k]['P_plus1_H2'];localrows.append([k,f"{a['local_delta_MAE']:.7f}",f"{v['local_delta_MAE']:.7f}",f"{100*v['direction_accuracy_nonzero_truth']:.2f}%",v['edges'],v['independent_heldout_families']])
 lt=table(['模型','172差分MAE','222差分MAE','222方向准确率','边数','独立验证家族'],localrows)
 itrows=[]
 for g in inter:
  for t,v in g['targets'].items():
   itrows.append([g['group_id'],t,f"{v['peak_abs_I']:.7f}",v['peak_wavelength_nm'],f"{v['mean_abs_I']:.7f}"])
 it=table(['四角组','目标','max abs I','峰值波长/nm','mean abs I'],itrows)
 intpred=[]
 for t,v in inter[0]['targets'].items():
  for k,e in v['prediction_errors']['ALL_V2_AVAILABLE'].items():intpred.append([t,k,f"{e['interaction_prediction_MAE']:.8f}",f"{v['mean_abs_I']:.8f}"])
 ipt=table(['G059目标','模型','家族外交互预测MAE','零交互MAE'],intpred)
 localall=[]
 for k,v in local['ALL_V2_AVAILABLE'].items():
  for t,e in v.items():localall.append([k,t,f"{e['local_delta_MAE']:.8f}",f"{e['direction_accuracy_nonzero_truth']:.5f}",e['family_mean_spectral_rank_rho']])
 lat=table(['模型','目标','222G局部差分MAE','方向准确率','家族内逐λ平均rho'],localall)
 amplitudes=[]
 for t in ['P_plus1_H2','eta','P_scale']:
  a=[v for v in pairs if v['target']==t];amplitudes.append([t,f"{min(float(v['mean_abs_signal']) for v in a):.7f}",f"{max(float(v['mean_abs_signal']) for v in a):.7f}",f"{max(float(v['max_abs_signal']) for v in a):.7f}",sum(int(v['wavelengths_above_unmatched_A1_time_reference']) for v in a)])
 at=table(['目标','23边mean abs delta最小','最大','全边max abs delta','abs delta大于异几何A1参考的λ单元/483'],amplitudes)
 oracle=rd(C/'ORACLE_FACTOR_ERROR_DIAGNOSTIC.json');ot=table(['模型','原P+ MAE','真实eta×预测P_scale','预测eta×真实P_scale'],[[k,f"{v['full_Pplus_MAE']:.8f}",f"{v['oracle_eta_predicted_Pscale_MAE']:.8f}",f"{v['predicted_eta_oracle_Pscale_MAE']:.8f}"] for k,v in oracle.items() if isinstance(v,dict)])
 report=f'''# AL50 V2 最终科学收尾

## 正式裁决

- AL50_PRODUCTION = PASS
- AL50_LABELS = 50/50 VALID
- AL50_REPLAY = 0
- FAST开发集 = 222G
- MODEL_GENERALIZATION = NOT_RELIABLY_BETTER_THAN_MEAN
- LOCAL_LEARNING_BENEFIT = NOT_ESTABLISHED_REPRODUCIBLY
- DIAG2 = 1/2；A2 = HOLD；DOE56 = HOLD
- NEXT_BATCH_AUTHORIZED = 0；NEW_FDTD = 0

这里的生产与标签 PASS 不等于严格电磁收敛认证。数据等级 ML_TRAINING_GRADE；实际制造资格 UNRESOLVED。原严格1%数值门槛和历史HOLD未修改。

## 生产证据及费用

50条唯一正式V2 Case/External Execution ID对应50条canonical REAL Entry、50个有效科学收据。旧V1已移出案例未使用。原生FSP、H5、609D全部保留，逐案路径沿用 `{D.name}/NATIVE_ARTIFACT_INDEX.json` 与 CASE_RESULTS.csv。继承已完成逐案验收与对账，不重复读取大FSP或全量哈希。

求解调用累计 {prod['AL50_GPU_TIME_hours']:.4f} h，含原生加载/求解/保存，不是GPU kernel计时；入场到科学验收累计 {prod['AL50_TOTAL_SERVICE_TIME_hours']:.4f} h；首入场至末验收墙钟 {prod['AL50_WALL_hours']:.4f} h，包含已修复SSH输出故障的停顿。每有效几何求解调用 {prod['AL50_GPU_TIME_hours']*60/50:.3f} min，含验收服务 {prod['AL50_TOTAL_SERVICE_TIME_hours']*60/50:.3f} min。16/32/50有效样本的离线阶段均完成。原生证据与旧科学账本保持不变。

## 同口径模型复核

{mt}

124个既定验证几何、原4折与固定模型参数均保留；old32不作为验证样本。每折将触及验证家族的所有训练成员清除，预处理只拟合训练折。ET/MLP采用原17/29/43三个种子预测均值。MAE/RMSE按124×21个标签单元汇总；波长单元不当作独立实验重复。rho与Top召回按折算后平均；Mean恒定预测排序未定义，不用人为打破平局制造排序结果。随机Top召回的折尺寸期望为 {random_top:.5f}，仅作描述性参照，不是显著性检验。

ExtraTrees的P(+1) MAE较Mean高 {(m['222']['ExtraTrees']['P_plus1_H2']['MAE']/m['222']['Mean']['P_plus1_H2']['MAE']-1)*100:.2f}%；eta MAE也略高。P_scale略低（{m['222']['Mean']['P_scale']['MAE']-m['222']['ExtraTrees']['P_scale']['MAE']:.8f}），不能据此宣称三目标全面泛化优势。ET P+ RMSE {m['222']['ExtraTrees']['P_plus1_H2']['RMSE']:.8f} 略低于Mean {m['222']['Mean']['P_plus1_H2']['RMSE']:.8f}，这与MAE裁决并存。ET各折rho={m['222']['ExtraTrees']['rho450_by_fold']}，Top召回={m['222']['ExtraTrees']['top20_by_fold']}；表现不稳定，未知K6可靠排序尚未建立。KRR与小MLP也未可靠优于Mean。

## 学习曲线合同

{lc}

156G旧发表口径无完整家族清除，不能直接与当前222G连接。仅补做此前不存在的匹配156G参考（32次固定配置拟合）；已有172/222结果不重训。MATCHED_156_FOLDS.json与既有fold清单可复核成员。新的三点曲线均在相同124验证几何上按同一家族规则计算，不混入旧0.03152→0.03139曲线。图中区间为4折范围，不是置信区间，曲线只连接实际已有点。

既有阶段共99个MLP拟合达到1000迭代上限，同时出现batch size按训练规模裁剪警告；保留全部警告。最终收尾未调参或续训来改善数字。MLP未充分优化是具体工程/学习限制，不能直接证明换复杂网络就会解决。

## 零求解目标误差分解

{ot}

这是拟合完成后替换为验证真值的oracle诊断，不是可部署预测分数，也不参与训练或选模。ET在使用真实eta时P+ MAE降至0.00735；只使用真实P_scale时仍为0.03146。当前代理的eta预测环节比P_scale环节更值得优先诊断；乘积交叉项使这些误差不能简单相加，也不能将差值当作唯一因果贡献。它不证明电磁标签本身无误，更不证明某个新表征一定有效。

## 局部学习

{lt}

23条真值边、2组完整四角实验均可追溯。只有G059家族的10条边符合独立家族外预测；S31旧32锚点为train-only且其扰动分布在验证折，因此另外13条边只报告物理真值，不冒充共同家族外OOF。不能把210个波长×边标签单元当作210个独立验证家族。

G059所在第3折中 ALL_V2_AVAILABLE 与 GLOBAL_ONLY_ABLATION 的训练成员一致，四模型预测最大差≤8.9e-16。因而172→222局部差分改善不能归因于新增局部训练样本；主要对照同时加入了全局数据。等名义40条新增数据的混合/全局对照也混合了采样组成与各折训练量差异，KRR/MLP略有收益、ET变差；尚无跨独立家族可重复的局部采样收益。具体数值和可辨识性见 LOCAL_LEARNING_VERDICT。

## 图表与数据

六组最终图：同口径156/172/222曲线；Best/Median/Worst光谱；局部差分预测；D2-D3/D6-D1交互；450nm散点与rho；Mean对照。每组提供SVG/PDF与600dpiPNG，源CSV/JSON、确定性案例选择和QA记录同目录保存。所有值沿用冻结609D/H1/H2定义；P+为H2，eta为原生+1分量，P_scale为冻结归一化标度，不以W为单位。没有从X单入射结果推导完整Jones矩阵或偏振选择性结论。

## 下一步

优先完成零求解的误差归因与家族可辨识性设计；不建议目前启动代理逆向生产或提高局部采样比例。下一批约50G仅提出30覆盖+8分歧+6分层随机+6局部的研究建议，尚无新Case/Entry/预算授权。
'''
 (C/'AL50_V2_FINAL_CLOSEOUT_REPORT.md').write_text(report,encoding='utf-8')
 verdict=f'''# 局部学习最终裁决

LOCAL_LEARNING_BENEFIT = NOT_ESTABLISHED_REPRODUCIBLY

## 1. 全部23条边

冻结有序六维几何逐边检验：恰有一个直径变化+5nm，未排序D1…D6。23条边×21λ×3目标共1449行已在LOCAL_PREDICTION_SOURCE.csv保存，ALL23_PAIR_ANALYSIS.csv保存69条边/目标摘要；S31有13条真值边，G059有10条。低→高直径方向固定，包含负扰动→锚点，不混淆扰动符号。

{at}

信号幅度是观察量；不直接等于可预测性。对异几何A1 3→6ps参考的逐λ比较仅描述量级，不是本几何误差条、显著性或全空间误差上界。差分含两个FAST标签误差，四角交互含四个标签误差，相关性未知，不能当作相互抵消或构造独立噪声置信区间。

## 2. 预测与基线

{lt}

Mean零差分方向视为弃权/不匹配非零真值，0%不代表随机二分类基线应为0%。非零真值方向率对全部210单元计算，未施加自造的数值误差阈值；很小信号的符号可能不稳。局部rho与方向率只描述一个家族，不作独立λ重复显著性检验。

三目标完整预测指标：

{lat}

关键负结果：第3折加入局部样本前后（ALL vs GLOBAL_ONLY）预测相同，因G059全家族持出、S31家族也被清除。S31新I002在全部4折均被清除，不能贡献当前OOF学习收益；G059新增9条几何仅在其余3折训练。这保住防泄漏，但导致现有设计无法把“G059家族外局部预测改善”归因于该家族自身的新标签。

## 3. 两组四角实验

{it}

G059的交互预测与零交互基线：

{ipt}

I(λ)=Y(D+δi+δj)−Y(D+δi)−Y(D+δj)+Y(D)。D2-D3取G059锚点，D6-D1取S31；四角均有真实有效标签，设计完整与真值完整已明确区分。原冻结设计表仍留存TRUTH_PENDING历史状态，不回写；本次INTERACTION_TRUTH_AND_PREDICTION.json才是完成后科学证据。

G059的各模型交互误差与零交互（Mean）对照已在继承的21点表和图中显示。模型通常将交互幅度压低，不能仅因交互预测误差小就说学会耦合，应与零交互误差一起比较。S31只做真值，不给出伪独立预测分数。非加性不是某一种近场机制的唯一证据，也可能包含多重散射、MDC反馈、归一化与数值误差影响。

## 4. 科学不确定性与决策

A1固定5nm的3/6ps对比：P_scale最大相对2.434%@446nm，严格1%门槛历史HOLD保留；6ps本身未证明收敛。P+最大绝对差约0.00261137；eta约0.00227734；P_scale约0.00681596。这些是异几何已知敏感性，不是所有局部边的误差估计。旧4/5nm报告还显示更大差异，不能宣布网格风险已闭合。

物理局部信号真实可测，但可重复的代理学习收益尚未建立。等名义40新增样本对照模型结论不一致，各折实际训练量不同，不能声称局部方案因果优于原V1覆盖方案（被替换的10案没有真值）。不建议提高局部比例；如下一批获授权，少量跨独立锚点补充，优先支持leave-family-out检验，避免全部局部预算集中于一个锚点。
'''
 (C/'AL50_V2_LOCAL_LEARNING_VERDICT.md').write_text(verdict,encoding='utf-8')
 recommendation=f'''# 下一阶段建议（零求解优先）

NEXT_BATCH_AUTHORIZED = 0。以下仅科学建议；本次不生成生产Case、External Execution ID、FSP或入场记录。

## 已验证事实与待检验假设

|问题|现有事实|不能据此声称|零求解优先动作|
|---|---|---|---|
|六维覆盖|222独立几何覆盖27^6={diag['grid_domain_cardinality']}离散域；二维投影仅164–175/729格。单维齐全不代表联合齐全|稀疏是唯一误差原因|逐折训练近邻距离、联合occupancy、D2/D3稀疏组合与残差交叉表；使用现有8192池元数据，不看sealed响应|
|覆盖-残差关系|124验证几何的近邻距离与ET误差Spearman={assoc['train_nearest6D_normalized']:.4f}|简单最近距离能预测全部误差|按各折和局部密度分层检查，而非只看总体相关|
|窄峰/强非线性|21个1nm采样有光谱变化，二阶差分与残差rho={assoc['max_abs_second_difference']:.4f}|已证实亚nm窄共振导致失败|检查峰位、谱形、每λ误差、现有光谱PCA残差；不插值制造窄峰真值|
|输入表征|有序D1…D6是冻结结构的完整名义可变输入，未排序；当前直接直径表征拟合弱|一定遗漏某一物理自由度|离线检查不变结构元数据、归一化、周期邻接D6-D1距离；若做下一轮表征试验只增加几何派生特征，先定协议，不换大网络|
|数值标签|A1时间敏感性和旧网格敏感性未闭合；ML_TRAINING_GRADE不等于严格收敛|已测出222G逐案标签噪声|仅利用已存native/日志/已有锚点做分层风险；无同几何重复则不估计普遍噪声方差|
|P+动态范围|全222×21范围 {diag['Pplus_global_range']}；分位见LABEL_AND_COVERAGE_DIAGNOSTICS|小绝对MAE即高功率候选排序可靠|按真值功率分位、每λ、低信号绝对误差/参考量同时报；保持固定验证ID，不用当前验证结果反复选模|
|标签分解|native eta×P_scale对H2 P+的全数据MAE={diag['factorization_native_eta_times_Pscale_vs_H2_power_MAE']:.8g}，max={diag['factorization_max_abs']:.8g}|该近似必然无影响，或能解释约0.03全部误差|保留误差分解账本；尺度远小于当前模型MAE，尚无证据是主要来源|
|局部排序|仅1个合格家族外局部验证锚点；ALL/GLOBAL第3折预测相同|局部学习收益已经可重复|以锚点为统计单位，完整家族持出，纳入跨锚点训练对照，分别给差分幅度、方向、交互零基线|
|训练稳定性|99个既有MLP拟合未达到1000轮内优化收敛|更复杂网络一定更好|先审训练曲线/目标缩放/预测非法比例，使用原轻量模型；参数改动须预注册，禁止用本轮图表掩盖警告|

以上相关性为描述性分析，未做多重比较显著性检验，不用来认定因果。误差归因CSV逐案可审计。2个交互锚点不支持六维全空间机制或数值认证。

## 已完成的目标通道oracle诊断

{ot}

所有替换只发生在预测完成后的诊断中，未把验证真值用于训练；不可作为部署模型指标。ET真实eta×预测P_scale的MAE约0.00735，预测eta×真实P_scale约0.03146，相比原0.03258更指向当前eta学习环节。下一步先审查eta的几何依赖、目标尺度、折内残差与局部符号，不应只继续改善公共P_scale谱形。该诊断不区分表征、数据稀疏、优化或FAST标签偏差等根因。

## 下一批约50G的建议配额

- 30G：六维联合maximin覆盖，保留D2稀疏组合与D3=170nm邻域关注，同时平衡其他5维和二维投影。
- 8G：现有模型分歧区，但分歧未校准；与几何密度联合约束，不按预测最高效率单独选样。
- 6G：按联合直径区间分层随机探索，防止只追局部或单一稀疏维度。
- 6G：两个互相远离、合法已完成锚点，各补3点构成四角实验；优先各一组D2-D3和周期D6-D1。按完整家族留出，保证其他独立局部家族可训练；若无法实现训练/验证可辨识性，6G返回覆盖，不硬凑局部实验。

总计50G建议，局部比例12%，低于本轮20%，不提高比例。当前不选择最终几何、不生成不可逆身份、不登记预算；后续仍需全历史去重、理想几何合法性与独立求解授权。不得用DIAG2剩余额度或DOE56预算。

## 阶段验收

继续16/32/50有效样本的固定124几何OOF，与同口径Mean、KRR、ET、小MLP比较。优先P+ MAE/RMSE、eta/P_scale MAE、各折450nm rho、Top召回相对随机参照；独立家族外差分方向率、局部排序和交互误差必须对零差分/零交互基线。报告训练成本与每有效几何服务成本。模型未改善不自动扩预算，也不改变冻结电磁合同。探索性结论只用于下一轮预注册方案，不宣称独立最终确认。
'''
 (C/'AL50_NEXT_STAGE_RECOMMENDATION.md').write_text(recommendation,encoding='utf-8')
 # QA report completed only after actual visual review file is supplied.
 visual=C/'VISUAL_QA_VERIFIED.json'
 if visual.exists():
  qa=rd(visual);assert qa['all_six_figures_visually_reviewed'] and qa['pdf_font_audit_pass']
  text=f'''# AL50 V2 图表QA

FIGURE_QA = PASS。六类图逐张目视检查，源数据身份、坐标/单位、图例与冻结标签定义均核对。无修改不理想数据、无隐藏失败样本、无截断负预测。

|图|数据与口径|目视检查|
|---|---|---|
|LEARNING_156_172_222_MATCHED|同124验证ID、4折家族清除，补齐缺失156参考；4折范围非CI|轴、三点与Mean基线、rho缺失Mean点明确|
|SPECTRAL_BEST_MEDIAN_WORST|ET P+谱MAE对全部124稳定排序，取1/63/124位；21λ三目标，无挑选好例|真实/预测/Mean图例、科学ID及未贴合光谱均展示|
|LOCAL_DIFFERENCE_PREDICTIONS|10条G059家族外边×21λ，Mean零差分见数表；其余13边只报告真值|正负差分、y=x、模型低幅度预测可见；不是210个独立家族|
|TWO_INTERACTION_GROUPS|两组四角真值；G059模型家族外，S31只真值|D2-D3/D6-D1、λ轴、交互零线和模型低估均可见|
|RANKING_SCATTER_FIXED124|124点全保留，450nm H2 P+；标题是折均rho|恒定Mean、负预测、弱相关均保留；不误用pooled rho|
|MEAN_BASELINE_COMPARISON|同124×21误差，三目标，4折范围非CI|0基线、模型名称、差别量级和误差范围可见|

单位：P+为冻结H2归一化功率，eta原生+1效率、P_scale冻结归一化标度，均沿用既有无量纲标签；不标作瓦特。单X入射不宣称完整Jones或偏振选择性。600dpi PNG预览及可编辑SVG/PDF均保留。

数据选择记录SPECTRAL_CASE_SELECTION.json；原124固定ID集合、成员和purge结果见EVALUATION_FAMILY_AUDIT。23条局部边均进入1449行全量源表。波长不算独立重复；未做p值/显著性星标。无平滑、插值、剪裁、归一化美化或隐藏负预测。不同评估口径没有直接连接。

源级检查：{qa['source_validation_summary']}。PDF检查：{qa['pdf_audit_summary']}。静态检查不能替代目视验收；已完成各面板和整图检查。静态检查唯一提示为未提供TIFF；本轮交付可编辑SVG/PDF和600dpi PNG，未指定期刊投稿栅格格式，故保留该格式提示，不影响数据或目视验收。P_scale>0在源代码中显式检查。

逐图观察：
{chr(10).join('- '+v for v in qa['notes'])}

旧生产目录三张图不覆盖；本任务六类最终图在figures/中，旧图保留为历史版本。四份正式报告与所有源数据在本任务目录，原生FSP/H5/609D仍在原输出路径。
'''
  (C/'AL50_V2_FIGURE_QA_REPORT.md').write_text(text,encoding='utf-8')
 print('REPORTS_WRITTEN',3+int(visual.exists()));print('TOP20_RANDOM_EXPECTATION',random_top);print('AMPLITUDES',at);print('INTERACTIONS',it)
if __name__=='__main__':main()
