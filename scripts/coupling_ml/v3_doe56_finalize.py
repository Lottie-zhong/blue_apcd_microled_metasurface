"""V3 design review and source-pin verification; zero scientific execution."""
from pathlib import Path
import json, hashlib, datetime, ast
import numpy as np
ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
OUT=ROOT/'reports/coupling/APCD_COUPLING_ML_V3_DOE56_OVERNIGHT_PRODUCTION_DESIGN_V1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,v):
 (OUT/name).write_bytes((json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode() if not isinstance(v,str) else v.encode())
def main():
 manifest=read(OUT/'V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json');c=manifest['cases'];b=read(OUT/'V3_56CASE_GPU_BUDGET.json')
 for r in c:
  f=b['mesh_runtime_factor_assumed_not_measured'] if r['mesh_nm']==4 else 1.
  r['estimated_case_end_to_end_seconds']=b['median_case_end_to_end_s']*f
  r['conservative_case_seconds']=b['q95_case_end_to_end_s']*f+300
  r['estimated_native_fsp_h5_bytes']=int(b['native_fsp_h5_median_bytes']*((5/4)**3 if r['mesh_nm']==4 else 1))
  r['estimate_is_not_measured_for_new_case']=True
 put('V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json',manifest)
 req=read(OUT/'V3_GPU_V2_IMMUTABLE_REQUEST_DESIGN.json');req['queue_sha256']=sha(OUT/'V3_DOE56_FROZEN_GEOMETRY_MANIFEST.json');put('V3_GPU_V2_IMMUTABLE_REQUEST_DESIGN.json',req)
 inv=read(ROOT/'reports/coupling/APCD_COUPLING_ML_156G_DATASET_CLOSURE_AND_TRAINING_PROTOCOL_REVIEW_V1/DEVELOPMENT_156G_DATASET_INVENTORY.json'); old=np.array([r['ordered_D_nm'] for r in inv['cases']]);new=np.array([r['ordered_D_nm'] for r in c if not r['numerical_diagnostic']]);dist=np.sqrt(np.sum(((new[:,None,:]-old[None,:,:])/130)**2,axis=2)).min(axis=1)
 byrole={}
 for role in sorted({r['role'] for r in c}):
  group=np.array([r['ordered_D_nm'] for r in c if r['role']==role]);byrole[role]={'count':len(group),'coordinate_min_nm':group.min(axis=0).tolist(),'coordinate_max_nm':group.max(axis=0).tolist(),'strata':{s:sum(r['role']==role and r['stratum']==s for r in c) for s in ['DEEP_INTERIOR','NEAR_BOUNDARY','EXACT_BOUNDARY']}}
 put('GEOMETRY_COVERAGE_AND_ROLE_AUDIT.json',{'roles':byrole,'new52_vs_old156_nn_distance':{'median':float(np.median(dist)),'q95':float(np.quantile(dist,.95)),'min':float(min(dist)),'max':float(max(dist))},'minimum_all56_periodic_gap_nm':min(min(r['min_periodic_x_gap_nm'],r['min_periodic_y_gap_nm']) for r in c),'geometry_only_selection':True,'manufacturing_pass_claim':False,'independence':'52new geometries; diagnostic4 intentional oldanchor repeats'})
 pins=read(OUT/'SOURCE_AUTHORITY_PINS.json')
 external={
  r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts\apcd_native_materials.py':'12a1b183380137b50d0d381e6c93c1877ae5ed552d8b3807deb8a06fb297b07a',
  r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\configs\mdc_defect_450_material_policy.json':'73d1ab830795dd7bcd5ed7fa49f2f84653a151151a823a82969e2ab5ee8f98ee',
  r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\outputs\material_reference\mdc_blue_oujizi_m\material_ref_native_sampled_mdc_native_m1.csv':'16cf9219c577ad264c10d0e9933a40e9b9f1a43775878ae52806cecc47a4f4b6',
  r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\scripts\mdc_tmm_complex_2port_prior_v1.py':'a7d618b697a71ed59bf8b56d9d5239b570f0cb03f9f650497fa49ce37a5a6a00',
  r'D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2\reports\MDC_TMM_COMPLEX_2PORT_PRIOR_V1.json':'b8e856fed0c7859b6ce3d1aa7d40549f40720b0c317b6f3dbf362e62c7e37a38',
  r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_complex_two_port_reference_plane_contract_v1\contract_manifest.json':'a51a36dd1e9aa6f67fab3d43d132b38280a45705ae60ded3820b9f7d3e4ca45b'}
 for p,s in external.items():
  assert sha(p)==s,'PHYSICS_SOURCE_SHA_CHANGED:'+p
  if p not in {q['path'] for q in pins}:pins.append({'path':p,'sha256':s})
 put('SOURCE_AUTHORITY_PINS.json',pins)
 # All pinned source artifacts read/hash only. No import of Runner/model training APIs.
 for p in pins: assert sha(p['path'])==p['sha256']
 checks=read(OUT/'SYNTHETIC_AND_DESIGN_CHECKS.json')
 extra_names={'compiler_no_fit_solver_api_AST','all_source_pins_actual_SHA_match','remaining_window_boundary_admission_only','frozen_H1_H2_confirmation_prediction_SHA_unchanged'}
 checks['tests']=[r for r in checks['tests'] if r['test'] not in extra_names]
 prev=read(ROOT/'reports/coupling/COUPLING_ML_GEOMETRY_NEAREST_NEIGHBOR_PHASE_TRANSFER_AUDIT_V1/NEAREST_NEIGHBOR_PHASE_SPEC.json')['protected_files']
 for p in prev:assert sha(p['path'])==p['sha256'],'FROZEN_PREVIOUS_ARTIFACT_CHANGED:'+p['path']
 formal=ROOT/'reports/coupling/APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1'
 frozen=[p for p in prev if 'SEALED_GEOMETRY_ONLY_PREDICTIONS' in p['path']]
 assert len(frozen)==2,'CONFIRMATION_INPUT_PREDICTION_PIN_NOT_FOUND'
 # These are only model predictions for28 input geometries, never confirmation truth.
 put('FROZEN_ARTIFACT_PROTECTION_AUDIT.json',{'previous_protected_files':len(prev),'all_sha_match':True,'confirmation_input_predictions':frozen,'confirmation_responses_accessed':0,'original32_roles_unchanged':True,'protected_artifacts':prev})
 checks['tests'].append({'test':'frozen_H1_H2_confirmation_prediction_SHA_unchanged','result':'PASS'})
 src=ROOT/'scripts/coupling_ml/v3_doe56_design.py'; tree=ast.parse(src.read_text(encoding='utf-8'))
 forbidden={'fit','run','run_one','start_controller_task','resume_controller_task','FDTD'}
 calls=[n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id if isinstance(n.func,ast.Name) else '' for n in ast.walk(tree) if isinstance(n,ast.Call)]
 assert not(forbidden&set(calls))
 checks['tests'].append({'test':'compiler_no_fit_solver_api_AST','result':'PASS'})
 checks['tests'].append({'test':'all_source_pins_actual_SHA_match','result':'PASS'})
 # Window calculation cannot terminate an active case; admission decision only.
 deadline=10*3600;buffer=1800;normal=max(b['q95_case_end_to_end_s'],b['median_case_end_to_end_s'])+300
 admit=lambda now,bound:now+bound+buffer<=deadline
 assert admit(8*3600,normal) and not admit(deadline-normal-buffer+1,normal)
 checks['tests'].append({'test':'remaining_window_boundary_admission_only','result':'PASS'})
 checks['count']=len(checks['tests']);put('SYNTHETIC_AND_DESIGN_CHECKS.json',checks)
 anchors={r['anchor_case_id']:r['ordered_D_nm'] for r in c if r['role']=='DIAGNOSTIC_REPEAT'}
 anchorlines='\n'.join(f'- **{k}**：{v} nm。' for k,v in anchors.items())
 put('FINAL_REPORT.md',f'''# V3 DOE56 科学设计冻结\n\n状态：**DESIGN_READY / PRODUCTION_ADMISSION_PARTIAL**。本轮solver entry、训练fit、P_scale fit、replay、confirmation响应访问、新FSP、LOAD均为0。DOE32在未发布/未执行前由本次DOE56替代；未改变既有点集或任何历史结果。\n\n## 点集与科学价值\n\n|角色|案例数|训练准入|用途|\n|---|---:|---|---|\n|同合同独立重复|2|否|两个anchor各一次，衡量跨run重复性|\n|4nm网格诊断|2|否|两个anchor各一次，区别网格敏感性与真实几何变化|\n|局部开发|24|是，验收后|每anchor完整六维±5nm配对，比较跨anchor规律|\n|全域开发|20|是，验收后|10深内部/6近边界/4精确边界，覆盖+1/+3/-2/-3几何干涉描述符|\n|新增封存评估|8|否|4局部组合+4全域，模型与预测冻结后才允许正式开启|\n\n{anchorlines}\n\nAnchor A选取满足全部轴向/组合点合法且不重复的truth-valid非S31、非局部样本中最接近设计域中心者；B在同一条件下选距A最远者。不按HF响应、模型误差或效率选anchor。全域点使用独立固定种子的Sobol离散候选、几何Fourier描述符分层和maximin去重；Fourier描述符不是NP散射系数，物理相关性仍待验证。\n\n56个唯一case/attempt身份，对应54个不同几何：4个诊断案有意重复两个旧anchor。其余52个几何全部新且跨角色去重，其中44个开发、8个封存；不能称56个独立几何样本。全部满足100–230nm、5nm有序几何网格及周期间隙规则；制造authority仍缺失，不宣称制造通过。若44个开发全部有效，未来canonical开发池为200G。原32个confirmation继续封存。\n\n## 唯一优先物理相位方案\n\n共享逐阶/谱向圆周相位head：**23→32→32→2，1890参数**。输入为有序D、波长、有符号阶次、TE/TM、空气kz、Native-M1 spacer传播因子、固定MDC正常入射双向复数r/t和几何Fourier矩。输入可由未知几何及已知合同计算，无HF oracle。完整预测294个unit-complex相位，复用冻结幅值及独立P_scale，重建原609D并保留H1/H2。\n\n已核实NP柱顶1712nm、输出参考1722nm，空气carrier为10nm传播。单纯固定carrier相位旋转对全秩KRR数学等价，不能声称它本身提升学习；本方案真正待检验的是共享阶次/波长结构与相干损失。Normal MDC TMM不是非零阶返回的斜入射散射矩阵；NP88不是复数相位。当前不具备合法complex LF residual。此优先方案无需先重训NP/MDC。未来最小4个匹配phase-head开发fits，正式最终fit与优化预算需下一次训练授权，当前0fits。\n\n已观察：1-NN全部124 held-out state median1.132484；全域113点实际为1.148178，局部11点0.306594，不能混用统计口径。全域距离–相位Spearman0.024468；因此暂停通用邻域KRR搜索有依据。跨anchor局部规律、物理特征改善相位和±5nm可分辨性均是尚未验证的假设。\n\n## 夜间时间与存储\n\n86个真实完成案例的端到端中位数**{b['median_case_end_to_end_s']/60:.2f}分钟**，q95 **{b['q95_case_end_to_end_s']/60:.2f}分钟**；56案均按canonical估计 **{b['uniform56_median_hours']:.2f}小时**。两个4nm案例暂按2.5倍耗时估计后为 **{b['mesh_adjusted_median_hours']:.2f}小时**；q95逐案估计加30分钟报告缓冲约 **{b['q95_case_with_mesh_factor_plus30min_hours']:.2f}小时**。网格倍率并未测量；许可证/恢复故障开销无法保证上限。预留12–14小时合理但不能承诺结束时间。\n\nUTC+08默认20:00启动、次日10:00前目标交付；18:00或更早准备完成即可开始。每次入场前必须按保守剩余耗时和30分钟报告缓冲检查窗口；不足则停止新增入场，未入场留到后续窗口。绝不为赶时间杀死正在运行的solver或降低验收标准。\n\n最低native FSP/H5预算约**{b['minimum_durable_native_GiB']:.2f}GiB**，计入raw E/H约**{b['native_plus_raw_EH_GiB']:.2f}GiB**；建议预留**60GiB**工作空间用于pre/staged FSP、临时文件、后处理和失败证据。此为预算，未占用或预留磁盘。\n\n## 生产准入审查\n\n当前56案**尚不能直接执行**。需要Chat正式entry预算批准，以及GPU owner新case登记、任务隔离canonical FSP与fresh LOAD证明、完整SHA/immutable request/release绑定。当前V2消费者硬编码canonical合同，4nm诊断与封存/诊断角色必须经正式owner接口验证；禁止伪用旧合同SHA或自动进入开发入口。\n\n现有release支持到期拒绝，但尚无按剩余窗口预测下一案完成时间的动态gate。必须在现有V2内由owner闭合此门槛及10:00部分/超时状态报告能力；本任务不另建调度系统、不修改Runner。固定阶段N1诊断4→D1局部24→D2全域20→B1封存8，有限release及自动阶段衔接需正式绑定。诊断出现科学合同冲突立即HOLD后续入场；普通post-entry失败保留entry、replay=0，按正式收据恢复/结案，不自动重跑。\n\n实际已交付Scheduler快照为Disabled、PT0S、IgnoreNew、InteractiveToken；需要DELL登录，不能据此宣称注销/重启后可运行。再次launch前必须现场确认，不沿用历史RUNNING快照。已验证86案长时生产可复用，但不足以替代本次mesh/role/window准入。\n\n第二天开发数据可用于科学分析；封存8案只能返回身份、完整性状态及SHA，不能随晨报打开响应。4诊断排除训练，old32CF与已冻结28份输入预测保持原样。\n\n## 检查、交付与停止\n\n{checks['count']}项设计/数学/访问边界检查PASS，包括完整六维配对、保护集去重、角色、预算、carrier逆变换、H2功率保持公式及窗口边界；合成检查不证明真实物理准确。子agent v3_phase_design完成只读物理源码审计，主agent统一完成DOE、预算、窗口合同、整合和Git。\n\n完整案例/几何/来源FSP SHA、各来源authority及产物SHA见manifest、SOURCE_AUTHORITY_PINS、SHA_INVENTORY。所有新FSP为NOT_CREATED，来源solved FSP仅作参考模板证据。**下一步：Chat一次性科学预算裁决；批准后GPU owner闭合准入依赖，再按夜间窗口执行。当前停止，不自动启动HF或训练。**\n''')
 print(json.dumps({'checks':checks['count'],'anchors':anchors,'budget':b,'coverage':byrole},ensure_ascii=False))
if __name__=='__main__':main()
