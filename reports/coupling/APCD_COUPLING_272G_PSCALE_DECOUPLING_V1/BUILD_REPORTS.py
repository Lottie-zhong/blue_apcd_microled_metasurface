from pathlib import Path
import json,csv,numpy as np
D=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_272G_PSCALE_DECOUPLING_V1');R=D.parents[2];B=D.parent/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'));read=lambda p:list(csv.DictReader((D/p).open(encoding='utf-8')))
models={r['model']:r for r in rd(D/'MODEL_SUMMARY.json')};oracle={r['model']:r for r in rd(D/'ORACLE_SUMMARY.json')};boot=rd(D/'PAIRED_FAMILY_STABILITY.json')['comparisons'];pboot=rd(D/'PSCALE_PAIRED_STABILITY.json');h1=rd(D/'FROZEN_H1_DIAGNOSTIC.json');pd={r['model']:r for r in read('PSCALE_POOLED_DIAGNOSTIC.csv')};ps={r['model']:r for r in rd(D/'PSCALE_SUMMARY_FOLD_WEIGHTED.json')};seed=rd(D/'SEED_STABILITY_SUMMARY.json');z=np.load(B/'COMPLEX_DATASET.npz');ix={s:i for i,s in enumerate(z['case_ids'])};nn=np.load(D/'NN3_Joint_OOF.npz');va=np.array([ix[s] for s in nn['case_ids']]);ptrue=z['P_scale'][va]
def table(names,columns,source=models):
 text='|模型|'+'|'.join(label for key,label in columns)+'|\n|---|'+'|'.join('---:' for _ in columns)+'|\n'
 for name in names:
  a=source[name];text+='|'+name+'|'+'|'.join(f'{a[key]:.6f}' if a.get(key) is not None else 'N/A' for key,label in columns)+'|\n'
 return text
names=['Leaf1_Joint','ET3_Joint','NN2_Joint','NN3_Joint','NN3_PSNet','NN3_ET3','NN3_Leaf1','NN3_Ridge','NN3_PMean']
columns=[('complex_NRMSE','复数NRMSE'),('TM_magnitude_MAE','TM幅度MAE'),('routing_MAE','Routing MAE'),('relative_phase_deg','相对相位°'),('P_scale_MAE','P_scale MAE'),('Pplus_MAE','P(+1) MAE'),('rho450','450nmρ'),('Top20_recall','Top20召回')]
metrics=table(names,columns)
# Exact pooled error algebra; fold-averaged correlation is deliberately not substituted.
cancel=[]
for name in ['NN2','NN3','Leaf1','ET3','NN3_PSNet','NN3_ET3']:
 a=[np.load(D/f'ORACLE_{name}_fold{f}.npz') for f in range(1,5)];ec=np.concatenate([v['error_C'] for v in a]);ep=np.concatenate([v['error_P'] for v in a]);inter=np.concatenate([v['interaction'] for v in a]);ed=np.concatenate([v['both']-v['true'] for v in a]);cancel.append({'model':name,'C_only_MAE':float(abs(ec).mean()),'P_only_MAE':float(abs(ep).mean()),'interaction_MAE':float(abs(inter).mean()),'both_MAE':float(abs(ed).mean()),'opposite_sign_fraction':float(np.mean(ec*ep<0)),'signed_error_correlation_pooled':float(np.corrcoef(ec.ravel(),ep.ravel())[0,1]),'component_abs_cancellation_fraction':float(1-abs(ed).mean()/(abs(ec).mean()+abs(ep).mean()+abs(inter).mean())),'MSE_C':float(np.mean(ec**2)),'MSE_P':float(np.mean(ep**2)),'MSE_interaction':float(np.mean(inter**2)),'MSE_cross_terms':float(np.mean(2*ec*ep+2*ec*inter+2*ep*inter)),'MSE_total':float(np.mean(ed**2)),'identity_max_error':float(abs(ed-ec-ep-inter).max())})
(D/'CANCELLATION_POOLED.json').write_text(json.dumps(cancel,indent=2));cd={r['model']:r for r in cancel}
gate_rows=[];limits=rd(D/'H1_FROZEN_THRESHOLDS.json')['chart_numeric_authority']
for model in ['NN3_Joint','NN3_Leaf1']:
 g=h1[model];m=g['aggregate']['metrics'];ag=g['aggregate']
 definitions=[('state','state_relative_rmse','state_relative_rmse',None),('routing','routing_eta_rmse','routing_eta_rmse','routing_pearson'),('absolute_order','absolute_order_source_normalized_rmse','absolute_order_source_normalized_rmse',None),('thresholded_absolute_order','thresholded_absolute_order_relative_median','thresholded_absolute_order_relative',None),('total_power','total_power_relative_rmse','total_power_relative','total_power_pearson')]
 for name,metric,lim,corr in definitions:gate_rows.append({'model':model,'gate':name,'median':m[metric]['median'],'median_max':limits[lim]['median_max'],'q95':m[metric]['q95'],'q95_max':limits[lim]['q95_max'],'pearson':ag[corr] if corr else None,'pearson_min':limits[lim].get('pearson_min'),'PASS':g['gates'][name]})
 gate_rows.append({'model':model,'gate':'seed_stability','median':g['seed_state_median_std'],'median_max':limits['seed_state_median_std_max'],'q95':None,'q95_max':None,'pearson':None,'pearson_min':None,'PASS':g['gates']['seed_stability']})
with (D/'H1_NUMERIC_GAPS.csv').open('w',newline='',encoding='utf-8') as f:wr=csv.DictWriter(f,fieldnames=list(gate_rows[0]));wr.writeheader();wr.writerows(gate_rows)
gate_table='|模型/门禁|median / 上限|q95 / 上限|Pearson / 下限|裁决|\n|---|---:|---:|---:|---|\n'
for r in gate_rows:
 fmt=lambda a:'N/A' if a is None else f'{a:.5f}'
 gate_table+=f'|{r["model"]}/{r["gate"]}|{fmt(r["median"])} / {fmt(r["median_max"])}|{fmt(r["q95"])} / {fmt(r["q95_max"])}|{fmt(r["pearson"])} / {fmt(r["pearson_min"])}|'+('PASS' if r['PASS'] else 'FAIL')+'|\n'
trendvar=float(np.var(ptrue.mean(0)));geomvar=float(np.var(ptrue,axis=0).mean());total=float(np.var(ptrue));assert abs(trendvar+geomvar-total)<1e-12
waves=read('PSCALE_WAVELENGTH_POOLED.csv');maxwave={name:max([r for r in waves if r['model']==name],key=lambda r:float(r['MAE'])) for name in ['Joint','PSNet','ET3','Leaf1']};logdiag={'total_variance':total,'common_wavelength_mean_variance_fraction':trendvar/total,'mean_within_wavelength_geometry_variance_fraction':geomvar/total,'definition':'exact balanced124x21 variance decomposition, descriptive only, not variance explained on unseen geometry','largest_MAE_wavelength':maxwave};(D/'PSCALE_VARIANCE_DECOMPOSITION.json').write_text(json.dumps(logdiag,indent=2))
method='''## 冻结评价合同与新增训练

合法FAST272G，主评价为原124个几何，四折32/31/30/31；训练折分别216/217/208/217。原old32为train-only，原局部家族connected components保留purge，所有21波长归属同一几何折。所有输入/输出StandardScaler仅拟合训练折，无验证标签作为模型输入。未访问sealed confirmation。

原29D网络为7→64→64→29、tanh、Adam、300epochs、batch256；原17/29两种子八个模型完整复用，本轮仅为每折补seed43。独立PNet为7→32→32→1，目标lnP，三个种子、300epochs；Ridge(alpha1)使用六维几何、中心化波长及其平方，回归lnP；Mean为各波长训练几何的物理P均值。另复用原ET leaf3与Leaf1三个种子P预测。共4个联合NN+12个PNet+4个Ridge轻量fit，无树模型重训、无CVAE训练、无超参搜索。

所有模型为Geometry+λ输入；28Cartesian+lnP组成29D，21λ通过显式Cartesian588+lnP21重组609D。复数态使用Cartesian种子均值，P使用每种子逆log后的物理算术均值。独立P组合共用同一NN3复数态，故复数NRMSE、相位、TM幅度、η完全相同；区别仅来自P。

复数NRMSE为124G pooled SSE/真值能量；MAE为124G×21λ平均；450nm Spearman与Top20为四折均值，Top20每折ceil(20%×n)且延续既有argsort tie口径。相对相位使用同一训练折参考通道、圆周角差和|C_true|²权重；真值振幅低于逐case/λ最大值0.001倍排除，相位近零保护不变。七阶-3…+3、TE/TM、POSTNP1722nm及统一incident phase gauge不变。X/P_XLIKE单入射不构成完整Jones/偏振选择性验证。

误差条为114个原connected局部家族/单例的配对cluster bootstrap，2000次；只描述固定OOF模型条件下的不确定性，不包含重训/选模不确定性。数据获取为自适应开发流程，不是独立外部test。所有候选均列报；根据本轮验证挑选的模型不得称未见数据无偏认证。
'''
oracletext='''# H2误差解耦 — Oracle诊断

A=TrueC+TrueP，B=PredC+TrueP，C=TrueC+PredP，D=PredC+PredP。全部调用原冻结H2，不手工替换解码器。A与存量H2标签逐项一致到数值精度；B/C仅Oracle，不作为正式代理结果。

目标阶精确分解：`ΔP(+1)=P_true·Δη(+1)+η_true(+1)·ΔP_scale+Δη(+1)·ΔP_scale`。三个分量依次对应B误差、C误差与乘积项。每点代数复核最大残差<1e-12。不存在将真实验证P或C喂给正式模型的步骤。

'''
for n in ['NN2','NN3','Leaf1','ET3','NN3_PSNet','NN3_ET3']:
 oracletext+=f'## {n}\n\n'+table([n+'_A_TRUE',n+'_B_C_ONLY',n+'_C_P_ONLY',n+'_D_BOTH'],[('Pplus_MAE','P(+1) MAE'),('rho450','450nmρ'),('Top20_recall','Top20'),('Pplus_centered_spectral_RMSE','折加权中心化光谱RMSE'),('Pplus_spectral_Pearson_mean','光谱Pearson均值')],oracle)+'\n'
oracletext+='''## 正式归因

原NN2：B=0.020078、C=0.008644、D=0.021560；Leaf1：B=0.027383、C=0.007428、D=0.028486。即使将P全部换成真值，NN的模态贡献仍明显更好；NN在P单独误差反而较大的情况下仍改善，不能将全部功率收益归因于η/P误差抵消。

NN3：B=0.019046、C=0.008403、D=0.020600；真实P时更好，预测P仍造成净损失。约51.08%点上B/C误差异号；三个分量绝对值之和与合成误差之间存在抵消。精确pooled统计见CANCELLATION_POOLED.json，包括MSE展开的交叉项。不得将“component_abs_cancellation_fraction”解读为34%的模型改善由作弊/抵消造成：该值是三项绝对和相对最终绝对误差的描述，树模型也存在抵消，非可加的因果收益份额。

独立PNet的P误差稍差，却使D略低于Joint，进一步提示联合误差相关性会影响最终MAE。该微小功率增益的家族CI跨0，Top20下降，因此不是稳定提升证据。分离为ET P确实稳定降低P自身误差，但最终功率改善仍小且CI跨0。H2的η只取决于复模态功率分配，P变化不应改变η；六个组合已独立重算验证。

谱形与几何排序逐折见ORACLE_FOLD_METRICS.csv；光谱RMSE为逐折中心化RMSE加权汇总，不冒充全局重新开方结果。Oracle真值A的ρ=1、Top20=1，功率MAE=0；其余仅诊断。使用相同几何集合，无单折推广全空间。
'''
(D/'H2_ORACLE_DECOUPLING_REPORT.md').write_text(oracletext,encoding='utf-8')
ptable='|P模型|P MAE|偏差|几何方差/真值|几何均值ρ|峰值MAE|中心化光谱RMSE|\n|---|---:|---:|---:|---:|---:|---:|\n'
for n,r in pd.items():ptable+='|'+n+'|'+'|'.join(f'{float(r[k]):.6f}' for k in ['P_MAE','P_bias','geometry_variance_ratio_pooled124','geometry_mean_Spearman','peak_MAE','spectral_centered_RMSE'])+'|\n'
ptext=f'''# P_scale独立诊断

{ptable}
上表几何方差为固定λ跨124G的方差比，光谱RMSE为全局pooled；Mean跨折有微小方差只来自折间训练均值不同，不能视为有效几何区分能力。折内Mean预测几何方差为0。

## 可复核的误差来源

1. 公共波长趋势占总P真值方差的{trendvar/total:.2%}，同λ几何变化占{geomvar/total:.2%}（平衡124×21分解）。捕捉公共趋势即可有较低MAE；波长Mean的P MAE0.053435近似ET0.053431，并不表示几何P已可学或已解决。
2. 联合NN3保留约31.09%真实同λ几何方差，几何均值排序ρ仅0.168。ET/Leaf1仅3.83%/6.70%，尽管P MAE更低；较低误差同时伴随强烈均值收缩。PNet恢复约63.65%方差，但MAE反而0.06210，表明恢复方差不等于恢复正确几何响应。
3. 全域联合NN偏差+0.00447掩盖区域性错误：训练折各λ q90以上真值区域偏差-0.11431、MAE0.11462；每几何真实峰值MAE0.09298。高P被低估，部分低P被高估，是有证据的压缩/失配。q90只由各自训练折定义；评价时按真值分层仅作诊断，不作为候选输入。
4. 联合NN的物理偏差精确为加权log误差项-0.00521与指数曲率项+0.00968之和=+0.00447。种子物理均值相对几何均值增加约0.00164。该非线性逆变换对偏高有贡献，但不是全部MAE原因；没有用验证偏差作校准/裁剪。
5. 单种子跨折等权训练P MAE均值：联合网络0.05359→验证0.06543；独立PNet0.03867→0.06524。独立网络降低训练误差却未降低验证误差，有泛化差距证据；不能简单归结为联合网络容量不足或lnP一个输出被28复数输出淹没。多任务损失竞争可作假设，尚无严格因果对照证据。
6. 最差波长及21点偏差/MAE/真值预测标准差/几何Spearman见PSCALE_WAVELENGTH_POOLED.csv和PSCALE_VARIANCE_DECOMPOSITION.json。逐几何峰值、六维有序直径、误差及身份见PSCALE_GEOMETRY_DIAGNOSTIC.csv。没有只挑一个波长报告。

独立PNet在ensemble预测中有1个P_scale>1点（最大1.02897），保留原始预测，不裁剪、不伪装物理有效；联合NN最大0.84455。该模型仅离线研究，无科学/生产资格。所有P为正，未修改H2合法输入检查。

## 稳定性

独立PNet相对Joint的P MAE差+0.002082，家族CI[-0.002801,+0.008081]；不支持稳定改善。Leaf1 P差-0.006895，CI[-0.009970,-0.004212]，P自身改善有一致证据。ET3也改善。Ridge更差。见PSCALE_PAIRED_STABILITY.json，分母不近零偷换、不做case剔除。

没有证据将本轮模型残差唯一归因为FAST数值误差。272G仍为ML_TRAINING_GRADE、严格收敛未闭合；A1已有数值风险保持，不能用本轮拟合把HOLD追认为PASS。
'''
(D/'PSCALE_DIAGNOSTIC_REPORT.md').write_text(ptext,encoding='utf-8')
seedtable='|Seed|基线|NN P MAE|基线 P MAE|NN ρ|基线ρ|NN胜出折数|\n|---|---|---:|---:|---:|---:|---:|\n'
for r in seed:seedtable+=f'|{r["seed"]}|{r["baseline"]}|{r["NN_Pplus_MAE"]:.6f}|{r["baseline_Pplus_MAE"]:.6f}|{r["NN_rho_foldmean"]:.5f}|{r["baseline_rho_foldmean"]:.5f}|{r["folds_NN_better_Pplus"]}/4|\n'
nextstage='''# H1与下一阶段科学决策

## 六项回答

1. **NN是否稳定优于ExtraTrees？** 在本次固定开发验证口径下，P(+1)、复数态、TM幅度、Routing与排序有一致改善：三个种子各4/4折功率MAE优于对应ET/Leaf1，共12/12。三种子ensemble功率MAE0.02060 vsLeaf1 0.02849；家族配对CI完全低于0。但P_scale自身更差，未达到全指标优势，也不是未知全空间独立认证。
2. **P_scale误差来源？** 已验证公共波长趋势占主导、几何响应压缩、高P区域低估、log→exp曲率偏差及训练/验证差距。共享多任务竞争、覆盖不足、输入表征是否为唯一主因尚未证实。独立PNet无稳定改善反驳“只要拆头就能解决”的强说法。
3. **功率改善是否部分依赖抵消？** 存在点级抵消与交互；但真P的模态Oracle仍显著更好，且真实P比预测P的最终误差更低，所以主要模态收益真实可见，不能简化成仅靠抵消。所有Oracle单列。
4. **分离P是否稳定获益？** ET/Leaf1使P MAE下降有稳定证据，整链路P+MAE仅再降约1.4–1.6%、家族CI跨0，Top20由0.738降为0.702；不作为正式全面升级。PNet微小功率收益同时P误差更坏、CI跨0，不推荐替代。保留联合NN3作为研究主对照，分离ET作为P误差受控对照；本轮无生产模型安装。
5. **H1还差什么？** 见下方原阈值数值，state、Routing、thresholded absolute order、total-power仍FAIL；absolute order与seed stability PASS。状态门槛为逐几何相对RMSE，不等同于pooled复数NRMSE；不能混口径宣布通过。
6. **下批50G如何采样？** 只建议、不建Job/Entry：24G六维稀疏联合覆盖，10G有功率TM/Routing局部误差与模型分歧（不按最高效率），10G P_scale公共谱形残差/高P极值附近的独立模型分歧与欠覆盖几何，6G分层随机。可在24G中组织约4–6个局部补全案例，优先已有锚点；不得越过总50或虚构现有真值。训练数据上的高P/残差用于理解风险，未计算候选只能用训练模型、覆盖距离与可验证分歧评分，不能用不可获得真值选样。先零求解检查P分歧是否对OOF真误差有信息，若无校准就将其配额回拨几何覆盖/随机。防止P均值收缩模型以低不确定性漏掉峰值区域。

下一优先动作是冻结几何/波长共同趋势与几何残差的轻量P基线，利用现有数据检验（不在本轮另起大型模型工程）；继续以609D+FrozenH2为主，禁止η或P(+1)直接回归取代主线。新50预算必须单独授权。

## 冻结H1数值缺口

'''+gate_table+'''
表格为原H1 authority逐geometry median/q95/Pearson及种子稳定性；没有放宽阈值。即使以后retrospective通过，生产资格仍需原prospective验证条件，不可用本开发OOF自动替代。

DIAG2=1/2,A2HOLD,DOE56HOLD；NEW_FDTD0,NEXT_BATCH_AUTHORIZED0；CVAE与逆向设计继续暂停。
'''
(D/'H1_GAP_AND_NEXT_STAGE.md').write_text(nextstage,encoding='utf-8')
report='''# APCD_COUPLING_272G_PSCALE_DECOUPLING_V1

## 正式裁决

**零求解研究任务完成PASS；前向代理H1继续HOLD。** 原两种子结果精确复现，补齐三种子后神经网络的模态与目标功率收益仍成立。P_scale误差是独立瓶颈；整链路存在抵消，不能仅按P(+1) MAE选P模型。分离树P显著改善P自身误差，但当前证据不足以证明整链路稳定升级。

'''+method+'''
## 完整同口径模型对照

'''+metrics+'''
表格中NN2是原17/29seed复核，NN3是补齐43后的新ensemble，明确不混作同一旧结果。Leaf1为前轮0.02849基线，ET3为正式旧leaf3对照。NN3所有分离组合保持同一28D复态，没有真实验证标签作为输入。

## 三种子稳定性

'''+seedtable+'''
每个种子均复用相同折，不能把12个相关折/种子当成12次独立外部实验。三种子NN相对Leaf1功率MAE差-0.007886，114家族bootstrap95%[-0.012027,-0.004432]，四折均改善；相对原ET3同样四折改善。Top20及相位、复数误差见MODEL_FOLD_METRICS.csv，未做best-seed筛选。

## H2解耦与P_scale关键证据

NN3仅模态预测Oracle功率MAE0.01905，只有P预测Oracle0.00840，完整0.02060。Leaf1对应0.02738/0.00743/0.02849，说明NN的收益在消除P误差后仍成立。

逐点误差可抵消：NN3约51.08%的模态/P误差异号；完整误差是两项加乘积，不应简单把B+C的MAE相加。CANCELLATION_POOLED.json保存精确分解、MSE交叉项；H2_ORACLE_DECOUPLING_REPORT.md完整列出A/B/C/D谱形与排序，B/C不是正式模型指标。

分离Leaf1 P把P MAE0.06002→0.05312；组合功率0.02060→0.02028、ρ0.7117→0.7192，但功率增益CI跨0、Top20 0.7381→0.7024。独立PNet把P MAE变为0.06210，不是稳定改善。原冻结H2及609D均不变。

## 冻结H1

'''+gate_table+'''
## 文件与图表

- MODEL_COMPARISON.csv、MODEL_FOLD_METRICS.csv：所有ensemble及seed同口径完整指标。
- H2_ORACLE_DECOUPLING_REPORT.md、ORACLE_COMPARISON.csv、ORACLE_FOLD_METRICS.csv、CANCELLATION_POOLED.json：Oracle和精确误差分解。
- PSCALE_DIAGNOSTIC_REPORT.md、PSCALE_POOLED_DIAGNOSTIC.csv、PSCALE_WAVELENGTH_POOLED.csv、PSCALE_GEOMETRY_DIAGNOSTIC.csv：波长、几何、峰值、方差、系统偏差。
- H1_GAP_AND_NEXT_STAGE.md、H1_NUMERIC_GAPS.csv：科学裁决和下一批建议。
- FIGURES/PSCALE_DECOUPLING_OVERVIEW、PSCALE_AND_POWER_SPECTRA：PDF/SVG/PNG及逐图来源和QA。谱例为联合P误差最低/中位/最高几何，不是选择有利案例。
- PREREGISTRATION、WORKER、FIT_LEDGER、全部训练checkpoint与OOF预测：可复现记录；大模型留远端，不混入Git。
- BOUNDARY_AUDIT、INDEPENDENT_RECONSTRUCTION_AUDIT、GIT_BEFORE/AFTER：边界和对账证据。原生FSP/H5/609D未改，Runner未改，sealed未访问。

## 边界与Git

FAST272，NEW_FDTD0，NEXT_BATCH_AUTHORIZED0；DIAG2=1/2,A2HOLD,DOE56HOLD；CVAE与逆向暂停。canonical117条Solver Entry不变，历史科学账本及原4项staged文件按原字节保留。

branch work/mdc-np-coupling-ml-v1，HEAD2cc687020e90ec4397e6cd4ed31efed59aaaf386，ahead/behind0/0，保留原dirty；未commit/push。完整报告位于正式Coupling worktree reports/coupling/APCD_COUPLING_272G_PSCALE_DECOUPLING_V1。
'''
(D/'PSCALE_DECOUPLING_REPORT.md').write_text(report,encoding='utf-8');(D/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
(D/'CURRENT_AUTHORITY.json').write_text(json.dumps({'task':'APCD_COUPLING_272G_PSCALE_DECOUPLING_V1','task_status':'PASS_OFFLINE_COMPLETE','H1':'HOLD','NN2_metrics_reproduced':True,'NN3_seeds':[17,29,43],'NN3_Pplus_MAE':models['NN3_Joint']['Pplus_MAE'],'NN3_rho450':models['NN3_Joint']['rho450'],'P_decoupling':'TREE_P_SELF_ERROR_IMPROVES_POWER_GAIN_NOT_STABLE','FAST':272,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','CVAE':'FROZEN'},indent=2))
(D/'CONTINUATION.md').write_text('''# Continuation — P_scale decoupling closed

Read FINAL_REPORT.md and CURRENT_AUTHORITY.json. Original NN2 metrics reproduced exactly. NN3 completed seed43 only; total new fits4Joint+12PSNet+4Ridge; old8NN and ET reused, no CVAE. Do not rerun completed fits/WORKER. Same124 primary geometry/familyguard. NN3 P+MAE0.020600,rho0.711677,Top20.738095. H1HOLD. Modal Oracle confirms actual improvement independent of P errors; point cancellation exists. Independent PNet does not improve P. Leaf1/ET P improves P MAE, but power gainCIcross0 andTop20worse: no blanket promotion. Read Pscale diagnostics, H1_NUMERIC_GAPS and next-stage recommendation. No production model install or nextbatch entry identities. FAST272,NEW_FDTD0,nextbudget0,DIAG21/2,A2HOLD,DOE56HOLD. Original117entries, scientific ledgers and4staged retained. Branchwork/mdc-np-coupling-ml-v1 HEAD2cc6870,0/0,dirtypreserved,no commit/push.
''',encoding='utf-8')
print('REPORTS_COMPLETE',logdiag['common_wavelength_mean_variance_fraction'])
