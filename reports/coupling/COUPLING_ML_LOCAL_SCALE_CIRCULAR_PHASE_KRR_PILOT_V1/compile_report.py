"""Compile persisted phase-pilot evidence without fitting or changing predictions."""
from pathlib import Path
import sys,json,datetime,hashlib,csv,platform
import numpy as np,scipy,sklearn
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');OUT=ROOT/'reports/coupling/COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1'
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def write(n,d):(OUT/n).write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def text(n,s):(OUT/n).write_bytes(s.encode())
p=read('THREE_WAY_PAIRED_COMPARISON.json');h=read('H1_H2_EVALUATION.json');phase=read('PHASE_HEAD_RESULTS.json');density=read('NEIGHBORHOOD_DENSITY_DIAGNOSTIC.json');modal=read('NONZERO_ORDER_PHASE_ANALYSIS.json');ledger=read('FIT_LEDGER.json');spec=read('LOCAL_SCALE_PHASE_FROZEN_SPEC.json');verdict=read('FINAL_SCIENTIFIC_VERDICT.json');folds=read('FOUR_FOLD_FIT_MANIFEST.json')['folds']
assert sum(q['fit_invocations'] for q in ledger['fits'].values())==4
metrics=['state_relative_rmse','amplitude_relative_rmse','routing_eta_rmse','absolute_order_source_normalized_rmse','thresholded_absolute_order_relative_median','p_scale_relative_rmse','total_power_relative_rmse','absolute_phase_rmse','relative_phase_rmse','nonzero_state_rmse','norm_ratio']
table=['|指标：median / q95|A Cartesian|B 原幅相|C 邻域尺度相位|','|---|---:|---:|---:|']
for k in metrics:table.append('|'+k+'|'+ '|'.join(f"{p[k][a]['median']:.6f} / {p[k][a]['q95']:.6f}" for a in ['A','B','C'])+'|')
fp=p['state_relative_rmse']['paired']['C_minus_B'];ap=p['absolute_phase_rmse']['paired']['C_minus_B'];ca=p['state_relative_rmse']['paired']['C_minus_A']
foldtable=['|Fold|state C−B median|state改善/恶化|相位 C−B median/rad|相位改善/恶化|state C−A median|','|---|---:|---:|---:|---:|---:|']
for f in folds:
 k=str(f['fold']);s=fp['folds'][k];a=ap['folds'][k];foldtable.append(f"|{k}|{s['delta']['median']:.6f}|{s['wins']}/{s['losses']}|{a['delta']['median']:.6f}|{a['wins']}/{a['losses']}|{ca['folds'][k]['delta']['median']:.6f}|")
modtable=['|TM阶|B相位 median/q95|C相位 median/q95|B state median/q95|C state median/q95|','|---|---:|---:|---:|---:|']
for b,c in zip(modal['B'],modal['C']):modtable.append(f"|{b['m']}|"+'|'.join(f"{q[t]['median']:.6f}/{q[t]['q95']:.6f}" for q,t in [(b,'strong_TM_phase_RMSE'),(c,'strong_TM_phase_RMSE'),(b,'order_state_RMSE'),(c,'order_state_RMSE')])+'|')
dentable=['|分层|n|state C−B median|相位 C−B median|state C−A median|','|---|---:|---:|---:|---:|']
for n,q in density['groups'].items():
 if q['n']:dentable.append(f"|{n}|{q['n']}|{q['state_C_minus_B']['median']:.6f}|{q['phase_C_minus_B']['median']:.6f}|{q['state_C_minus_A']['median']:.6f}|")
dentable.append('|SPARSE|0|N/A|N/A|N/A|')
text('NUMERIC_COMPARISON.md','\n'.join(table)+'\n\n'+'\n'.join(foldtable)+'\n\n'+'\n'.join(modtable)+'\n\n'+'\n'.join(dentable)+'\n')
ids=[q['case_id'] for q in fp['per_geometry']];rows=[]
for i,cid in enumerate(ids):
 row={'case_id':cid,'fold':fp['per_geometry'][i]['fold']}
 for k in metrics:
  ab=p[k]['paired']['B_minus_A']['per_geometry'][i];bc=p[k]['paired']['C_minus_B']['per_geometry'][i];ac=p[k]['paired']['C_minus_A']['per_geometry'][i]
  assert ab['case_id']==bc['case_id']==ac['case_id']==cid
  row.update({k+'_A':ab['base'],k+'_B':bc['base'],k+'_C':bc['new'],k+'_C_minus_B':bc['delta'],k+'_C_minus_A':ac['delta']})
 rows.append(row)
with (OUT/'PAIRED_GEOMETRY_METRICS.csv').open('w',encoding='utf-8',newline='') as fh:
 writer=csv.DictWriter(fh,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
original=ROOT/'reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
trainingB=json.loads((original/'AMPLITUDE_HEAD_RESULTS.json').read_text(encoding='utf-8'))['training']
trainrows=[]
for b,c in zip(trainingB,phase['training']):trainrows.append({'fold':c['fold'],'B_state':b['train_state_relative_RMSE'],'C_state':c['state'],'B_phase':b['train_phase']['absolute_phase_RMSE'],'C_phase':c['phase']['absolute_phase_RMSE']})
write('TRAIN_VS_HELDOUT_DIAGNOSTIC.json',{'training':trainrows,'meaning':'diagnostic only, no checkpoint selection or additionalfit; same fitted phaseheads'})
artifacts=[]
for f in sorted((OUT/'models').rglob('*')):
 if f.is_file():artifacts.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
write('MODEL_SHA_INVENTORY.json',{'models_and_predictions':artifacts,'C_OOF':{'path':str(OUT/'C_OOF_PREDICTIONS.npz'),'sha256':hashlib.sha256((OUT/'C_OOF_PREDICTIONS.npz').read_bytes()).hexdigest()},'amplitude_source':'original model payload binding, zero amplitudefits','fit_ledger_sha256':hashlib.sha256((OUT/'FIT_LEDGER.json').read_bytes()).hexdigest()})
write('ENVIRONMENT_VERSIONS.json',{'host':'DESKTOP-NNE313K','python':platform.python_version(),'executable':sys.executable,'numpy':np.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,'environment_changes':0,'GPU_training':False})
text('FINAL_REPORT.md',f'''# COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1

**STATUS：PASS，受控4-fit实验完整完成。科学裁决：{verdict['verdict']}。** A/B/C均仍为 DEVELOPMENT_H1_FAIL。

## Authority及实际执行

DESKTOP-NNE313K/dell；worktree `{ROOT}`；branch `work/mdc-np-coupling-ml-v1`；起点 HEAD `cc53c98d4027b68756ff979ccfc9fd5954c70e2d`。解释器 `{sys.executable}`。根目录无AGENTS/CONTINUATION，采用用户提供的项目规则及上一科学审计的scoped continuation。现场版本、完整输入SHA、156G开发身份、四折模型、原始预测及正式H1/H2均核验。

实际新增4个CPU phase-head fits，每fold一次，无重试、核尺度/seed搜索或查询时拟合。幅值、P_scale、Cartesian baseline、MLP、NP/MDC拟合均0；FDTD/replay/confirmation response access均0。fit前原子记录invocation，完成后保存checkpoint、原始cos/sin、rho、预测、训练预测及SHA。旧65G/268-fit/NP88/幅相8-fit与确认预测保持不变。

## 唯一冻结数学合同

有序6D输入使用原B每fold训练geometry mean/std；距离为该标准化空间欧氏距离（不同于描述性130 nm尺度）。定义训练距离 `r_i²=min_(j≠i)||x_i−x_j||²`，`ell²=median_i r_i²`，`gamma=1/(2ell²)`。核为 `K(x,y)=exp(−gamma||x−y||²)`，alpha=1，float64。

四fold gamma分别0.2453374415、0.2407898859、0.2388632168、0.2436999799，精确等于上一提案的输入侧dry-run。它是**每fold一个固定尺度的stationary RBF**，不是逐查询局部fit，也不是非平稳核。推理使用全部124个训练几何的固定kernel；不依据查询HF响应选择邻域或参数。

少于2个有限独立训练几何、重复几何/零最近距离或非法尺度明确BLOCKED；不加epsilon或裁剪。边界使用同一核，不排序、镜像、cyclic扩增或响应校正。核矩阵严格对称，最小特征值1.66e-6…3.81e-6，正则化条件数17.97…18.75；原始K条件数约4.47e6…1.07e7，但alpha=1后求解稳定。阈值及PSD数值规则在首个fit前冻结，残差逐fold保存。

完整588D phase targets：21×7×2×[cos,sin]，沿用原B interleaved顺序、弱训练模态fraction<1e-4/零幅值时[1,0]、训练coordinate means/globalRMS。没有PCA或删阶。单位圆投影、64eps近零fallback及复数重建保持原规则；未采用上一圆盘诊断、oracle phase alignment或额外归一化。

## 零fit预检查与绑定

156G数据及所有原始inventories核验；每fold train124、heldout32/31/30/31，合计124唯一heldout。A/B原H1报告逐元素复算一致。对应训练/验证几何不交叉，21波长整组；尺度、targets、means/RMS及fallback只来自对应训练组。

零fit数学检查通过；**6项pytest回归通过（7.83s）**，合成estimator fits=0。覆盖核对称/PSD、已知邻域尺度、查询不改变训练尺度、非法近邻拒绝、单位圆fallback、完整复数及H2重建、仅train函数有一个fit调用点。全部通过后才执行正式4 fits。

C与B的294D幅值head预测、21D P_scale均**逐元素一致**。复数abs的最大浮点差为{h['reconstructed_abs_max_B_C']:.3g}，H2 routing最大差{h['H2_B_C_max_abs']['eta']:.3g}、absolute-order最大差{h['H2_B_C_max_abs']['absolute_order']:.3g}、total差0，均在预冻结1e-12容差内。相位改变引起这些舍入差，不是幅值或归一化改动。模型save/reload预测逐元素一致。

## 三组完整指标

{chr(10).join(table)}

C state中位数几乎不变且略差，q95小幅改善；绝对相位median和q95均恶化。非零阶state median恶化、q95略改善。C相对Cartesian state仅{ca['wins']}/124改善，{ca['losses']}/124恶化，四fold paired median均更差。因此不能认为相干学习瓶颈已解决。

## 配对几何与fold

{chr(10).join(foldtable)}

C相对B：state {fp['wins']}/{fp['losses']}改善/恶化，paired median={fp['delta']['median']:.6f}；绝对相位{ap['wins']}/{ap['losses']}，paired median={ap['delta']['median']:.6f}。**paired median小负数不等于两组总体median改善**，二者统计定义不同，不能只挑有利口径。相位仅fold2的paired median改善，其余三fold恶化。

逐geometry完整三组指标、两个主要delta及worst10均保存；不将geometry×21λ作为独立样本或声称统计显著。最大state相对B退化G013：1.01503→1.07013（+0.05510）；G076：0.88916→0.94345（+0.05428），其相位0.86842→1.05928（+0.19087 rad）。全局worst state仍G009，B1.48636→C1.47379，略降但仍显著差于A1.15656。完整mode tails未因少数改善被隐藏。

## rho、相位SSE及逐阶结果

强模态rho median/q95：B0.359144/0.824084→C0.364344/0.847648；rho<0.5占比69.27%→68.96%，<0.1为5.46%→5.31%。收缩仅轻微减弱。rho增大没有带来方向精度提高，仍不是校准置信度。

幅值SSE均596.35762；phase SSE2596.13773→2601.88617，相位占比81.3200%→81.3536%。完整state norm ratio仍约0.87556，恢复范数不能替代方向准确。弱TE仍完整保留，但其SSE约1e-9级占比，不驱动科学结论。相位采用固定truth模平方权重和1e-4显著mask，并保存阈值敏感性；该坐标权重不等同于H2的kz加权物理功率。

{chr(10).join(modtable)}

-3相位median/q95改善，但其state median/q95略恶化。+3相位median/q95恶化，state略改善。-2相位median恶化、q95改善，其state median改善、q95恶化。没有一致的高阶收益。+1 state median/q95从1.09636/2.46851恶化为1.12389/2.48229。方向/强模态错误仍可导致较大order-relative state tails，不能从rho上升或某阶median改善宣称有效。

## 邻域和边界分层

冻结距离分箱：CLOSE≤1、MEDIUM(1,2]、SPARSE>2，依据训练标准化空间。未按结果移动阈值。

{chr(10).join(dentable)}

CLOSE恰为11个S31局部轴向heldout点，state和相位有小幅改善；这一个局部簇不能代表全域。113个全域heldout均在MEDIUM；SPARSE为空，所以没有证据评价该预注册稀疏bin，亦不能据此称全域六维覆盖密集。

深内部小幅改善；精确边界state paired median恶化，近边界相位paired median恶化；最差退化按case保存。近邻距离与state/phase delta的Spearman为0.24300/0.21005，仅描述性关联。不能证明改善由近邻因果产生。D6_M05缺失，未补标签；±5 nm受控重复性误差未知，局部11点不是完整六维局部验证。

四fold训练state median从B的0.54248…0.56092降至C的0.46374…0.47200；训练相位median从0.48545…0.51977降至0.37084…0.38638。训练拟合确实改善，但heldout整体无清晰收益，不能将训练改善当成泛化进展。TRAIN_VS_HELDOUT_DIAGNOSTIC保留完整数值，未用于checkpoint或核参数选择。

## 冻结H1/H2

A全部primary gates失败；B/C只有absolute-order达到，state、routing、thresholded-relative、total/P_scale仍失败，seed stability=N/A（确定性单seedKRR）。

Routing Pearson A=0.47060067、B/C≈0.43925728；total Pearson三组均0.90458786。P_scale/total median/q95=0.248064/0.757838保持不变。routing与absolute-order收益保留是冻结幅值及decoder无相位交叉项的结果，不是新phase head改善了功率预测。

## 科学裁决及限制

**{verdict['verdict']}**，按照fit前规则：未同时改善完整state与强模态相位median/q95；更未超过Cartesian。没有以q95少量下降、67个paired wins或rho变大升级为成功。

OBSERVED：当前唯一训练邻域尺度核未带来清晰总体收益；幅值和功率收益合法保留。SUPPORTED_HYPOTHESIS：局部簇/深内部可能更容易预测相位，但改动不足以解决全域方向问题。UNRESOLVED：其他真正局部或物理相位表示能否泛化；本实验只是stationary RBF长度尺度的一次受控变更，不能否定所有局部条件化。

不建议自动追加gamma/alpha/seed搜索。停止该pilot，交Chat重新评审相位模态结构和局部覆盖证据；已有有限局部收益可以保留，但不能作为追加fits的自动授权。原开发集已反复参与方案选择，本次仍是开发探索，不是独立确认或生产准入。

## 产物、隔离与续接

LOCAL_SCALE_PHASE_FROZEN_SPEC、ZERO_FIT_PREFLIGHT、FOUR_FOLD_FIT_MANIFEST、LOCAL_KERNEL_NUMERICAL_AUDIT、FIT_LEDGER、每fold provenance、MODEL_SHA_INVENTORY、原始phase/rho及C_OOF NPZ完整保存。THREE_WAY_PAIRED_COMPARISON与PAIRED_GEOMETRY_METRICS.csv覆盖全部124案；PHASE_HEAD_RESULTS、NONZERO_ORDER_PHASE_ANALYSIS、NEIGHBORHOOD_DENSITY_DIAGNOSTIC、H1_H2_EVALUATION和TRAIN_VS_HELDOUT_DIAGNOSTIC保留诊断细节。

32个confirmation响应仍封存；28份既有confirmation输入预测/模型SHA未改。0 FDTD/replay/P_scale/amplitude/baseline fits，4/4 phase fits。FINAL_ISOLATION_CHECK验证旧产物及确认输入预测哈希；未触及GPU V2。只提交本任务allowlist文本/代码/CSV，模型及NPZ保留远端完整SHA。外部dirty/staged保留，正常push，最终HEAD见DELIVERY_RECEIPT。恢复先读本CONTINUATION与账本，任何非COMPLETE的已调用fit不得盲目重训。

## 最终A–N

A PASS（执行完成），科学NO_CLEAR_GAIN。B4 fits。C训练最近邻平方距离median定义固定RBF gamma。D state A0.872970/1.086444、B1.039131/1.318987、C1.039380/1.311795。E强模态相位总体未改善。F非零阶state无一致改善。G rho轻升但phase SSE稍增。H routing/absolute-order收益保留。I无完整state增益超越Cartesian。J全部124几何/fold配对已保存，收益混合。K H1FAIL。L这一个尺度规则不支持继续自动扩fit，局部条件化更广泛可行性仍未定。M Git/report/SHA见DELIVERY_RECEIPT及SHA_INVENTORY。N confirmation封存及原28预测保持不变。
''')
text('CONTINUATION.md',f'''# {OUT.name} COMPLETE
恢复先读FINAL_REPORT、LOCAL_SCALE_PHASE_FROZEN_SPEC、FIT_LEDGER、FINAL_ISOLATION_CHECK、SHA_INVENTORY及DELIVERY_RECEIPT。
主机DESKTOP-NNE313K/dell；worktree {ROOT}；branch work/mdc-np-coupling-ml-v1；Python {sys.executable}；sourceHEADcc53c98d4027b68756ff979ccfc9fd5954c70e2d。
4/4 phase fits完成，禁止重算；幅值/P_scale/baseline/MLP/FDTD/replay/confirmation=0。每fold固定训练NN gamma≈0.239..0.245，alpha1；非查询时fit。原幅值head与P_scale逐元素一致，A/B正式H1精确复现。
科学LOCAL_SCALE_PHASE_NO_CLEAR_GAIN；state B1.03913→C1.03938，CartesianA0.87297；phase B1.28160→C1.29824rad；rho稍升但相位SSE81.32%→81.35%。routing0.12236和absolute-order0.04848收益保留，H1仍FAIL。局部簇轻微改善不等于全域成功；D6minus及重复性证据仍缺失。
32确认响应封存、原28输入预测SHA不变。只从保存模型/预测继续报告；不追加scale/seed/fit或HF，等待Chat裁决。无关dirty/staged和GPU平台保留。
''')
text('.gitattributes','* -text\n*.json whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
files=[{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in sorted(OUT.rglob('*')) if f.is_file() and '__pycache__' not in f.parts and f.name not in ['SHA_INVENTORY.json','DELIVERY_RECEIPT.json']]
write('SHA_INVENTORY.json',{'task':OUT.name,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'self_excluded':True,'deliveryreceipt_excluded':True,'execution_counts':{'CPU_phase_fits':4,'amplitude_fits':0,'P_scale_fits':0,'baseline_fits':0,'FDTD':0,'replay':0,'confirmation_access':0}})
print('REPORT_SHA',hashlib.sha256((OUT/'FINAL_REPORT.md').read_bytes()).hexdigest());print('INVENTORY_SHA',hashlib.sha256((OUT/'SHA_INVENTORY.json').read_bytes()).hexdigest());print('TRAIN_VS_HELDOUT',json.dumps(trainrows))
