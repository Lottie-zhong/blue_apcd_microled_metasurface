"""Evidence-grounded reports for the approved complex-state method; no fits or solver."""
from pathlib import Path
import json,csv,numpy as np,datetime,subprocess,sqlite3
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';AL=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');rd=lambda n:json.loads((D/n).read_text(encoding='utf-8-sig'))
def table(head,rows):return '| '+' | '.join(head)+' |\n| '+' | '.join(['---']*len(head))+' |\n'+'\n'.join('| '+' | '.join(str(x) for x in r)+' |' for r in rows)
def num(v,n=5):return 'NA' if v is None else f'{v:.{n}f}'
def write(n,s):(D/n).write_text(s,encoding='utf-8')
def main():
 m=rd('METRICS_FIXED124.json');lo=rd('LOCAL_PREDICTION_METRICS.json');oc=rd('ORACLE_ERROR_ATTRIBUTION.json');se=rd('SEED_AGGREGATION_DIAGNOSTICS.json');it=rd('DOUBLE_PILLAR_COMPLEX_INTERACTION.json');audit=rd('SCIENCE_CONTRACT_AUDIT.json');parity=rd('INDEPENDENT_COMPLEX_STATE_PARITY.json');training=rd('TRAINING_COMPLETE.json');gate=rd('FROZEN_H1_GATES_SUMMARY.json');constant=rd('OUTPUT_DOMAIN_CONSTANT_BASELINE.json');assert parity['cases']==222 and parity['max_abs_complex_delta']<1e-10
 channels=list(csv.DictReader((D/'PER_CHANNEL_ERRORS.csv').open(encoding='utf-8')));spectral=list(csv.DictReader((D/'PER_WAVELENGTH_ERRORS.csv').open(encoding='utf-8')));pairs=list(csv.DictReader((D/'ALL23_PAIR_SUMMARY.csv').open(encoding='utf-8')));keys=list(m);ea=m['A_ExtraTrees'];eb=m['B_ExtraTrees']
 tstate=table(['结构/模型','Re RMSE','Im RMSE','复数NRMSE','模长RMSE','绝对相位MAE/deg','相对相位MAE/deg'],[[k,num(v['real_RMSE']),num(v['imag_RMSE']),num(v['state_relative_RMSE']),num(v['magnitude_RMSE']),num(v['phase']['MAE_deg'],2),num(v['relative_phase_MAE_deg'],2)] for k,v in m.items()])
 tpower=table(['结构/模型','P_scale MAE','H2 eta(+1) MAE','H2 P(+1) MAE','450nm折均rho','Top20%召回'],[[k,num(v['P_scale_MAE']),num(v['eta_plus1_MAE']),num(v['Pplus_MAE']),num(v['rho450_meanfold'],4),num(v['top20_recall'],4)] for k,v in m.items()])
 tl=table(['结构/模型','局部ΔC NRMSE','同家族绝对C NRMSE','ΔC skill vs 0','Δ模长NRMSE','Δ相对相位MAE/deg'],[[k,num(v['delta_complex_relative_RMSE']),num(v['absolute_state_relative_RMSE_same_family']),num(v['delta_complex_skill_vs_zero']),num(v['delta_magnitude_relative_RMSE']),num(v['relative_phase_delta_MAE_deg'],2)] for k,v in lo.items()])
 tor=table(['结构/模型','正常P+ MAE','真实模态＋预测P_scale','预测模态＋真实P_scale','预测加权范数均值（真值1）'],[[k,num(m[k]['Pplus_MAE']),num(v['truth_state_pred_Pscale_Pplus_MAE']),num(v['pred_state_truth_Pscale_Pplus_MAE']),num(v['pred_weighted_norm_mean'])] for k,v in oc.items()])
 tc=[]
 for row in channels:
  if row['model']=='B_ExtraTrees' and row['polarization']=='TM':tc.append([row['order'],num(float(row['real_RMSE'])),num(float(row['imag_RMSE'])),num(float(row['complex_RMSE'])),num(float(row['magnitude_RMSE'])),num(float(row['phase_MAE_deg']),2),num(float(row['eta_order_MAE']))])
 tch=table(['阶m（TM）','Re RMSE','Im RMSE','复数RMSE','模长RMSE','相位MAE/deg','该阶TE+TM总eta MAE'],tc)
 weak=sum(float(v['total_complex_SSE_fraction']) for v in channels if v['model']=='B_ExtraTrees' and v['polarization']=='TE');hard=sorted([v for v in channels if v['model']=='B_ExtraTrees'],key=lambda v:float(v['complex_RMSE']),reverse=True)[:3];hardphase=sorted([v for v in channels if v['model']=='B_ExtraTrees' and v['phase_MAE_deg']],key=lambda v:float(v['phase_MAE_deg']),reverse=True)[:2];worstwave=max([v for v in spectral if v['model']=='B_ExtraTrees'],key=lambda v:float(v['complex_RMSE']));worstpower=max([v for v in spectral if v['model']=='B_ExtraTrees'],key=lambda v:float(v['Pplus_MAE']))
 state_gain=100*(1-eb['state_relative_RMSE']/ea['state_relative_RMSE']);power_gain=100*(1-eb['Pplus_MAE']/ea['Pplus_MAE']);const_gain=100*(1-eb['Pplus_MAE']/constant['Pplus_MAE']);domain_mean_rows=table(['参照定义','P+ MAE','说明'],[['冻结609D Complex Mean → H2',num(m['A_Mean']['Pplus_MAE']),'正式复数态基线，A/B一致'],['输出功率域常数Mean',num(constant['Pplus_MAE']),'只作训练折常数评价参照，不是Geometry→eta模型'],['B ExtraTrees → H2',num(eb['Pplus_MAE']),'正式609D真值与冻结解码器']])
 folds=rd('FOLDS.json');fs=table(['折','训练几何数','B训练λ行数','持出几何数（含新数据次级队列）'],[[f['fold'],len(f['train_ids']),21*len(f['train_ids']),len(f['heldout_ids'])] for f in folds]);fits=rd('FIT_LEDGER.json');cost=table(['结构','折/种子任务数','fit+predict+checkpoint累计秒'],[[a,sum(v['id'].startswith(a+'_') for v in fits),num(sum(v['seconds'] for v in fits if v['id'].startswith(a+'_')),3)] for a in ['A','B']])
 report=f'''# APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1

## 状态与方法权威

任务完成：PASS（离线诊断完成，不代表模型通过冻结H1）。正式主线保持 **Geometry → C_hat复数Floquet态 + P_scale → Frozen H2 → eta/阶功率**。结构A=6D→整体609D，结构B=6D+λ→29D后按原布局重组609D；这里“结构B”不是被禁止的Geometry→A+参考平面路线。

数据222G；NEW_FDTD=0；NEXT_BATCH_AUTHORIZED=0；DIAG2=1/2；A2 HOLD；DOE56 HOLD。未修改GPU Runner、609D/H1/H2、源FSP/H5或旧科学账本；未访问sealed confirmation。

## 1. 哪些分量最难学习？

{tstate}

主要困难是具有可观信号的TM模态复数响应、阶间相对相位和相对幅度分配，不是几乎为零的TE相位。B-ET绝对复数RMSE最高的通道为 {', '.join('m='+v['order']+' TM ('+num(float(v['complex_RMSE']))+')' for v in hard)}；相位误差最高为 {', '.join('m='+v['order']+' TM ('+num(float(v['phase_MAE_deg']),2)+'deg)' for v in hardphase)}。Re/Im总体误差接近，没有单一实部或虚部独占全部问题。B-ET全谱复数误差最大波长为{worstwave['wavelength_nm']}nm，而P+绝对误差最大为{worstpower['wavelength_nm']}nm，二者不能混为同一难点。

TE复数RMSE约1e-5量级，合计复数SSE占比 {weak:.3g}。其相位在预注册幅度掩码下全部NA，不能把小TE绝对误差当作“相位已学会”，也不能据此宣称偏振选择性。只含X/P_XLIKE入射，不重建完整Jones矩阵。

以B-ET为例：复数NRMSE {eb['state_relative_RMSE']:.5f}，绝对相位{eb['phase']['MAE_deg']:.2f}deg，相对相位{eb['relative_phase_MAE_deg']:.2f}deg。相位掩码只用于避免对近零振幅求无物理意义角度；复数Re/Im误差仍保留全部14通道。0.001/0.01/0.05幅度门槛敏感性见原JSON，B-ET相位MAE约32.70deg基本不变。

## 2. 整体609D还是逐波长29D更有效？

{tpower}

没有全面支配者。相同ET配置下，B的复数NRMSE比A低{state_gain:.2f}%，P+谱MAE低{power_gain:.2f}%；但A绝对相位和P_scale误差更小，450nm排序更强。相对相位误差几乎相同。KRR的A/B差别也很小，且B的P_scale误差增加；KRR模长误差小于ET，不意味着阶间routing或复相位更准确。

因此B-ET可作为“复数与光谱功率误差”方向的候选，A-ET保留为相位/P_scale/450nm排序对照。当前固定模型/参数实验不足以宣布29D具有普遍优势，更不能因输出维度变小就解释为新增独立数据。B只学习相同21个已知λ，不证明未见波长外推能力。

正式复数Mean与额外的输出域常数Mean必须区分：

{domain_mean_rows}

输出域常数Mean仅用训练折求平均，无几何回归、无fit调用、无609D状态，不作为正式前向代理。加入此参照是避免把相干平均后解码较差的Complex Mean当作唯一弱基线。B-ET P+ MAE仅比这个较强常数参照低{const_gain:.2f}%，故不能宣称绝对功率精度已充分解决。

A/B ET的Top20%召回均{eb['top20_recall']:.4f}。A各折rho={ea['rho450_by_fold']}；B各折rho={eb['rho450_by_fold']}。已出现有用的中等排序信号，不能沿用旧42D模型“接近随机”的结论；但全空间可靠性/严格H1仍未成立。旧42D实验训练目标与聚合规则不同；若作历史参照，必须注明是同评价集合下的不同目标实验，不是222G扩容学习曲线或独立新验证。本任务未重训或恢复直接eta代理。

## 3. 局部复数响应能否提供额外信息？

{tl}

23条局部真值边、2组完整四角实验全部使用，逐λ逐14通道共6762条复数响应差分记录。G059的10条边具备共同家族外预测；S31的13条边只报告真值，未伪造OOF。只有1个独立局部测试家族，210个边×λ或2940个边×λ×通道不是独立家族样本数。

B-ET局部ΔC相对RMSE={lo['B_ExtraTrees']['delta_complex_relative_RMSE']:.4f}，对零差分基线MSE改善{100*lo['B_ExtraTrees']['delta_complex_skill_vs_zero']:.2f}%；但同家族绝对C相对RMSE={lo['B_ExtraTrees']['absolute_state_relative_RMSE_same_family']:.4f}更低，未证明局部比绝对响应更易学习。局部相对相位差分MAE {lo['B_ExtraTrees']['relative_phase_delta_MAE_deg']:.2f}deg还差于零变化基线 {lo['B_Mean']['relative_phase_delta_MAE_deg']:.2f}deg。G059四角复数交互预测NRMSE约{it[0]['predictions']['B_ExtraTrees']['relative_RMSE']:.4f}，约等于或略差于零交互，不能声称已学会双柱协同。

局部数据包含真实几何敏感性，但“有物理信号”与“采样带来可重复泛化增益”是两件事。固定第3折将整个G059家族和S31家族从训练中清除，该局部测试折没有可训练的完整局部边；不具备识别新增局部训练数据因果收益的设计。不能在保持原验证合同的同时偷用S31验证臂来训练一个局部模型。详见LOCAL_COMPLEX_DIAGNOSTIC.md。

## 4. 为什么目标阶功率仍难准确预测？

{tor}

已验证的关键：冻结H2采用 `modal_m=sum_pol weight*abs(C_hat)^2`，再除以所有7阶的总模态功率，最后乘P_scale。独立通道相位替换后eta变化≤约3.4e-16。H2保证非负和归一化阶分配只是结构性质，不代表routing准确或独立能量守恒认证。相位误差本身不直接进入这个固定正交模态功率求和；不得把53deg相对相位误差直接当成P+误差的唯一原因。

对B-ET，给真实P_scale后P+ MAE仍{oc['B_ExtraTrees']['pred_state_truth_Pscale_Pplus_MAE']:.5f}；给真实模态幅度/状态后降至{oc['B_ExtraTrees']['truth_state_pred_Pscale_Pplus_MAE']:.5f}。主要瓶颈在当前学得的阶间幅度分配/routing。预测C_hat加权范数均值约{oc['B_ExtraTrees']['pred_weighted_norm_mean']:.3f}（真值1），显示显著幅度收缩；但统一标量范数投影不会改变H2的归一化routing，不能只靠补范数修复功率。

3种子相干平均的范数收缩比仍约{se['B_ExtraTrees']['complex_seed_mean_norm_contraction_mean']:.4f}，不足以单独解释约0.47的预测范数。样本/树平均、复杂相位分散及几何稀疏导致条件均值收缩，是相容解释而非已分离的唯一因果机制。oracle按每λ对齐全局相位后状态NRMSE仍{oc['B_ExtraTrees']['oracle_global_phase_aligned_state_relative_RMSE']:.4f}，也不是一个统一相位偏移就能修复。所有oracle只作拟合后诊断，没有用于正式评分、训练或改写真值。

相位/身份检查未发现pipeline冲突，但FAST 5nm/3ps复数相位的数值不确定性尚无222G逐案独立估计。历史A1 P_scale 2.434%不能充当相位误差条。不能把所有残差解释为数值噪声，也不能宣称phase已严格收敛。

## 5. 下一批50G如何补充？

建议28G六维联合覆盖、10G有物理权重的复模态模型分歧、6G分层随机、6G跨独立锚点局部四角补全。优先增加不同锚点而不是围绕单一锚点堆叠扰动；不假设邻柱弱耦合，不按模型最高效率单独选样。复数分歧应关注具有可观功率的TM及相对幅度/phase轨迹，不用近零TE随机相位主导采样。模型分歧尚未校准，必须与几何覆盖共同约束。

仅提出科学配额与设计原则，不创建新Case、FSP、Execution ID、Manifest、预算或Admission。继续原有有序D1…D6及FAST物理合同、21λ和冻结H2。阶段评估仍用相同124几何与完整家族清除；未来阈值或超参数研究须训练折内进行。不能把旧42D曲线当作609D学习曲线。详见NEXT_50G_RECOMMENDATION.md。

## 科学合同与执行证据

222G=156+16+50，身份和有序几何均与合法inventory/生产收据绑定。统一POSTNP+z、m=-3…3、TE/TM、440–460nm、1722nm冻结参考。相位规范为IN_REF入射+z(0,0)TM每λ单一全局参考，所有plane/channel共用。绝对相位不作拟合后对齐；相对相位采用每折训练集主导通道，排除自参考的恒零相位，不据验证误差选择参考。

独立读保存模态系数，按既有H1切片/归一化重建C_hat，与222G缓存最大复差 {parity['max_abs_complex_delta']}；无需重新哈希或读取FSP/H5。609D拆成29D再组回完全一致；H2与历史P+标签最大差 {audit['H2_vs_saved_power_max_abs']:.3g}；H2与原生eta最大差{audit['H2_eta_vs_native_max_abs']:.6g}，二者分别保留，主要解码指标对比H2真值，原始H1门禁仍用其原生eta/功率定义。

40个折/种子任务包含32次sklearn拟合与8个Mean计算；累计{training['fit_seconds']:.3f}s包含拟合、全222预测及checkpoint写入，不是纯fit kernel计时。无超参数搜索、无训练警告。实际运行CPU2线程上限，未调用GPU Runner。所有6个模型组合的原冻结H1适用主门槛均未全达到；ET种子稳定性PASS，不能将稳定误当精度PASS。H1/H2/参考面/归一化阈值均未改动。

数据、配置、预测与各阶误差：COMPLEX_DATASET_222G.npz、PREREGISTRATION.json、FOLDS.json、FIT_LEDGER.json、PREDICTIONS_A/B.npz、PER_CHANNEL_ERRORS.csv、PER_WAVELENGTH_ERRORS.csv、PER_GEOMETRY_ERRORS.csv、各local/interaction文件与FROZEN_H1_DIAGNOSTIC.json。六类图包含所有模型/14通道、全21λ及124点排序；交互图聚焦+1TM，全部14通道真值另存。图表与QA不掩盖幅度收缩或局部学习失败。
'''
 write('FINAL_REPORT.md',report)
 comparison=f'''# 609D / 单λ29D 对照合同与全结果

正式路线始终为复数Floquet态＋P_scale经冻结H2解码。结构B仅条件化同一609D标签，绝非Geometry→A+或全3D E/H学习。

609D布局：21×7×2×2=588个按λ、阶、TE/TM、Re/Im排序的Cartesian分量，之后21个log(P_scale)。B每λ为28Cartesian+1logP；先显式拆装，不能直接把609维reshape为21×29。所有14通道均参与训练，未丢弃近零TE。

{fs}

主报告只对原124持出几何评分；新增样本和old32未混成同一个评价集合。局部家族purge与上轮完全一致。B中的每λ行继承父几何/家族的折，绝不按λ行随机切分。有效独立几何数没有变成222×21。预处理仅训练折StandardScaler输入；目标保留冻结Cartesian+logP，没有用验证数据白化、相位对齐或单独调整小通道权重。

KRR固定alpha=.1、gamma=1/输入维数；ET固定128树、leaf3、seeds17/29/43。没有验证集选参。相同名义leaf3在A表示3个几何，在B可表示3个λ行，二者不保证同等几何层模型容量；这是固定轻量配置比较，不是严格容量匹配的架构因果实验。A/B Mean都是各λ训练Cartesian均值+训练logP均值，输出相同；ET按冻结H1先逐种子逆log，再对物理P_scale求算术均值，同时复数C_hat求算术均值。没有改为decode后再平均的正式规则。

{tstate}

{tpower}

P_scale误差、state q50/q95、每折rho/Top召回、phase覆盖与阈值敏感性详见METRICS_FIXED124。相位误差是[-pi,pi]包裹角差，用真值abs(C_hat)^2加权（不是另定义H2功率权）；相对相位排除自参考通道。主幅度门槛为每case/λ最大模长的0.001，另报0.01/0.05；这些是诊断掩码，不是新科学准入门槛。复数误差保留未掩码全通道；未知/暗相位NA而非0。ET主相位掩码18228个可观测TM单元全部有预测覆盖。

## 各阶细分（B-ET）

{tch}

该阶eta是TE+TM总和，不是重复两次统计的偏振功率。TE相位NA、实虚/模长误差完整保留在14通道CSV。最难绝对复误差与最难相位误差不是同一阶，不能只报告+1或只挑最差点。

## 原门禁、复杂度与选择

{table(['组合','state','routing','absolute order','total power','seed stability'],[[k,gate[k]['gates']['state'],gate[k]['gates']['routing'],gate[k]['gates']['absolute_order'],gate[k]['gates']['total_power'],gate[k]['seed_stability_status']] for k in keys])}

{cost}

B输入行数增加21倍但输出降为29，并不等价于新增物理观测。耗时包含预测/压缩checkpoint，不宣称模型训练纯耗时或跨硬件性能。当前固定配置不存在一方同时主导复数、phase与P_scale全部目标的证据；B-ET略优谱功率/复数误差，A-ET更优绝对相位/P_scale/450nm排序。均未达到原H1全门槛。保持轻量，不据此开发更大网络或新ML平台。

## Mean的定义必须明确

{domain_mean_rows}

输出域常数Mean是训练标签的算术均值，只评价，不映射Geometry、不充当正式状态代理。没有把它当新路线训练或用它代替H2。B-ET在P+ MAE上只比该参照改善{const_gain:.2f}%；把与Complex Mean的约28.6%改善作为唯一“精度收益”会夸大实用功率改进。
'''
 write('MODEL_COMPARISON.md',comparison)
 localreport=f'''# 局部复数响应诊断

23条已完成局部边，2组真值完整四角实验。NEW_FDTD=0。所有label是完整集成MDC+K6的真实3D结果，不使用孤立柱叠加，不假设弱耦合。

ΔC=C_high−C_low；ΔMagnitude=abs(C_high)−abs(C_low)，二者不是同一量。所有边低→高直径+5nm，未排序D1…D6。相对相位先对同λ训练主导通道取比，再比较两端并包裹到[-pi,pi]；近零通道只留原始相位记录，不作主要物理解读。ALL23_LOCAL_COMPLEX_RESPONSE.csv包含23×21×14=6762行，ALL23_PAIR_SUMMARY完整列举每条边身份、信号大小和有效预测资格。

23边ΔC RMS范围 {min(float(v['complex_delta_RMS']) for v in pairs):.6f}…{max(float(v['complex_delta_RMS']) for v in pairs):.6f}；Δ模长RMS范围 {min(float(v['magnitude_delta_RMS']) for v in pairs):.6f}…{max(float(v['magnitude_delta_RMS']) for v in pairs):.6f}。这是观测信号，不是模型误差或数值不确定性。

## 预测：仅G059家族10条边

{tl}

相对RMSE=norm(预测差分−真实差分)/norm(真实差分)，零差分基线=1；skill=1−SSE/SSE_zero。用同一家族绝对态相对误差对照，避免因差分信号小就宣称更好。ET虽有约7.5–8.9%局部差分MSE skill，但差分相对误差比绝对态更高；局部相位变化预测差于零变化常数。当前没有证据说局部复数响应更易学习。

S31原old32锚点train-only，其13条边的臂分散于原验证折；严格家族防泄漏使其不能成为共同家族外预测测试。G059第3折中的全部新局部几何都持出，S31家族也被purge；不能把局部响应预测改善归因于对该局部家族新增标签的训练。本任务没有另造一个泄漏S31验证臂的直接Δ模型。

## 四角非加性

I_C=C_ij−C_i−C_j+C_0；I_mag=abs(C_ij)−abs(C_i)−abs(C_j)+abs(C_0)。相对相位四角项用`arg(R_ij*R_0*conj(R_i)*conj(R_j))`，不直接线性相减带分支的角度。

{table(['组','锚点','I_C RMS','max abs I_C','I_mag RMS','独立预测资格'],[[v['group_id'],v['anchor'],num(v['complex_interaction_RMS']),num(v['complex_interaction_max']),num(v['magnitude_interaction_RMS']),v['prediction_eligible']] for v in it])}

{table(['G059预测组合','I_C相对RMSE（零I=1）','I_mag RMSE','相对相位四角MAE/deg'],[[k,num(v['relative_RMSE']),num(v['magnitude_interaction_RMSE']),num(v['relative_phase_plaquette_MAE_deg'],2)] for k,v in it[0]['predictions'].items()])}

ET没有显著优于零交互；B-ET约1.004，甚至略差。S31只报告真值，没有伪独立模型误差。归一化C_hat的非加性包含归一化本身的非线性、多个散射路径、MDC反馈及潜在FAST偏差，不能直接等同于某个唯一近场耦合机制，也不能用它证明邻柱弱耦合。

## 数值与统计限制

当前222G没有逐几何复数phase噪声方差或高精度配对覆盖；旧P_scale时间敏感性不能变成角度误差界。不能证明这些局部I高于所有FAST复数误差，也不能把误差完全归因于FAST。2个物理锚点、1个合格局部预测测试家族，不能用21λ或14通道虚增独立样本数。下轮优先跨独立锚点并保留可训练局部家族，而非增加单锚点邻域密度。

LOCAL_COMPLEX_EASIER_THAN_ABSOLUTE = NOT_DEMONSTRATED
LOCAL_SAMPLING_REPRODUCIBLE_BENEFIT = NOT_ESTABLISHED
DOUBLE_PILLAR_INTERACTION_LEARNED = NOT_DEMONSTRATED
'''
 write('LOCAL_COMPLEX_DIAGNOSTIC.md',localreport)
 write('NEXT_50G_RECOMMENDATION.md',f'''# 下一批50G：复数物理状态导向建议（未授权）

正式路线A不变：Geometry→C_hat+P_scale→冻结H2；结构A609D和结构B29D都是该路线内的表述。NEXT_BATCH_AUTHORIZED=0；本文件不生成Case、FSP、Execution ID、Manifest、预算或Admission。

## 已验证优先级

1. **具有功率的TM模态及阶间相对幅度。** B-ET相对相位仍约53deg；给真实P_scale后P+误差仍0.03092，给真实幅度后降至0.00745。不能只继续改善公共P_scale光谱，也不能把全局C_hat范数投影当作routing修复。
2. **复数分布的覆盖而非低预测效率排名。** 六维几何联合覆盖、±阶TM模式强弱组合、λ方向谱形与相位轨迹共同记录。近零TE随机相位不主导选样，但609D通道不删除、不改标签。
3. **数据少与估计器平均收缩分开。** 预测范数约0.47，而3种子平均收缩仅约0.6%。零求解先看每几何/每阶残差、目标尺度、训练几何密度和样本条件均值；“由树/样本平均造成”是相容解释，未分离所有因果因素。
4. **局部以独立锚点为单位。** 10条G059边不是10个独立实验家族，四角预测接近零基线；不提高局部比例，不假设弱耦合。

## 建议配额（总50，不是新预算）

- **28G全局联合覆盖**：从已有8192池的合法未计算区域补六维联合稀疏点，兼顾D2/D3与其余四维，保留周期D6-D1组合覆盖。
- **10G复数模式分歧**：A/B ET与KRR在可观测TM幅度、阶间分配及一致相位参考下的分歧。用训练/验证残差分析约束分歧解释；它不是已校准置信区间。避免只选相位近零幅度的高噪声点，也不按最高预测P+单独选样。
- **6G分层随机探索**：对联合直径区间分层，作为选择偏差参照。
- **6G局部补充**：两个互相远离的合法已完成新锚点，各3点补成四角；优先D2-D3与D6-D1。家族整组持出，保留其他独立家族训练，解决当前“局部测试折无局部训练边”的可辨识性不足。无法满足时返回覆盖配额，不硬凑局部。

保持原有有序D1…D6 100–230nm、5nm步长、237nm spacer、冻结MDC、5nm/3ps FAST、21λ与原生材料/monitor/reference。实际制造UNRESOLVED。不得用DIAG2剩余额度或DOE56，若未来研究复数phase数值不确定性，须单独设计并获得明确求解授权，不自动挪用A2。

## 先做零求解再定最终50个几何

复核不改变609D语义的输入/损失尺度、物理功率权重及归一化约束候选；所有预处理和可学习变换仅训练折拟合。B保留λ条件化的小模型，A作对照；目前不需更大网络、整个3D场或Geometry→A+新路线。任何下轮模型对照先固定参数，不用sealed confirmation选型。

以后16/32/50个新增有效几何阶段报告：全复数/实虚/模长/包裹相位与相对相位、P_scale、原H1、H2 eta/P+、固定124几何rho/Top召回、训练计算成本及真实标签成本。保持Complex Mean和功率域常数Mean两种不同参照的名称，后者只评价，不替代正式609D模型。旧42D数据量学习曲线不能冒充609D学习曲线。

DIAG2=1/2；A2 HOLD；DOE56 HOLD；NEW_FDTD=0；NEXT_BATCH_AUTHORIZED=0。
''')
 if (D/'VISUAL_QA_VERIFIED.json').exists():
  qa=rd('VISUAL_QA_VERIFIED.json');assert qa['all_six_figures_visually_reviewed'] and qa['pdf_font_audit_pass'];write('FIGURE_QA_REPORT.md',f'''# 图表验收

FIGURE_QA = PASS。Python matplotlib，6组可编辑SVG/PDF与600dpi PNG；全部进行面板及整图目视检查。{qa['pdf_summary']}。{qa['source_summary']}。TIFF仅为通用静态规则提示，本次未指定期刊投稿栅格要求，PDF/SVG/PNG足够本报告交付。

主A/B条图的误差线为固定4折范围，非CI；光谱为固定124几何的逐λ确定性OOF误差，不画伪独立λ置信区间；局部仅1家族，不伪造家族间误差条。功率域Mean虚线仅画pooled参照值，其折分布在原JSON中保存，不宣称该参照没有不确定性。21λ和14通道不是独立几何重复。

全部6模型、14模态通道、21λ和124几何均有源数据。仅光谱图省略与A完全相同的B-Mean重复曲线；交互图预先聚焦目标+1TM，全部14通道仍在NPZ/CSV。相位暗通道明确NA，不改为0。通道T=TE、M=TM，功率/效率沿用冻结归一化无量纲标度，phase为deg，波长为nm。

条图Complex Mean经H2解码；横向虚线为输出域常数Mean，仅评价参照、无Geometry映射或609D状态，不作为正式路线。未用其替代复数模型，也没有利用更弱基线夸大功率收益。

{chr(10).join('- '+v for v in qa['notes'])}

相位0.001/0.01/0.05掩码敏感性与覆盖率完整保存；绝对C误差仍保留所有通道。没有平滑、重采样、隐藏弱表现、删几何或用oracle对齐后分数代替正式误差。二维热图只表达误差，不是原始空间场学习结果。全复数差分6762行及两组I保留原始科学身份和版本。
''')
 print('REPORTS_WRITTEN_COMPLEX609',4+int((D/'VISUAL_QA_VERIFIED.json').exists()))
if __name__=='__main__':main()
