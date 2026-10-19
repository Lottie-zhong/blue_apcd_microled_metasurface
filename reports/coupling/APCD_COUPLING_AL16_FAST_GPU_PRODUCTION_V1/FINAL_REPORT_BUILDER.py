from pathlib import Path
import json,csv,sqlite3,subprocess,datetime,hashlib,base64,numpy as np
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';O=D/'ML_UPDATE';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3')
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
prod=read(D/'INDEPENDENT_PRODUCTION_RECONCILIATION.json');models=read(O/'MODEL_MAE_RANKING_BEFORE_AFTER.json');after=read(O/'MODEL_METRICS_AFTER.json');cov=read(O/'GEOMETRY_COVERAGE_CHANGE.json');train=read(O/'TRAINING_COMPLETE.json');energy=read(D/'ENERGY_ROUTING_NORMALIZATION_AUDIT.json');art=read(D/'NATIVE_ARTIFACT_INDEX.json');baseline=read(D/'GIT_BASELINE.json');ledger=read(D/'AL16_SCIENCE_LEDGER.json');assert prod['AL16_LABELS_VALID']==train['unique_total']-156==16
folds=read(O/'FOLDS.json');z=np.load(O/'FAST_DATASET_172G.npz',allow_pickle=False);assert len(z['case_ids'])==len(set(z['case_ids']))==len(set(map(tuple,z['D_nm'])))==172
for f in folds:
 assert not set(f['train_ids'])&set(f['heldout_old_ids']+f['heldout_new_ids'])
assert len({i for f in folds for i in f['heldout_old_ids']})==124 and len({i for f in folds for i in f['heldout_new_ids']})==16
fit=read(O/'FIT_LEDGER.json');assert len(fit)==40 and all(r['state']=='COMPLETE' for r in fit)
meanrecall={k:float(np.mean([f['top20_recall'] for f in v['fold_top20_450_recall'] if f['top20_recall'] is not None])) if k!='Mean' else None for k,v in after.items()};chance=float(np.mean([np.ceil(.2*len(f['heldout_old_ids']))/len(f['heldout_old_ids']) for f in folds]))
report='''# APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1 — FINAL_REPORT

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

'''
t=prod['AL16_GPU_TIME'];report+=f"- canonical Runner started_at→completed_at 累计 **{t['runner_real_solver_call_hours']:.6f} GPUh**，每有效几何{t['per_valid_geometry_solver_minutes']:.4f}min；包含native LOAD/run/save，不冒充纯GPU kernel计时。\n- entry→科学验收服务时间合计 **{t['entry_to_science_hours_sum']:.6f}h**，每有效几何{t['per_valid_geometry_service_minutes']:.4f}min。\n- 首entry至末案科学验收墙钟 **{t['first_entry_to_last_acceptance_wall_hours']:.6f}h**，含案间注册/门禁间隔。\n"
first=min(datetime.datetime.fromisoformat(r['entered_utc']) for r in art);last=max(datetime.datetime.fromisoformat(r['accepted_utc']) for r in art);tz=datetime.timezone(datetime.timedelta(hours=8));report+=f"- 北京时间 {first.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')} 至 {last.astimezone(tz).strftime('%Y-%m-%d %H:%M:%S')}。实际有效产出率16/16；这不是下一批成功率保证。\n"
report+='''
历史预计端到端3.11–3.13h与本轮3.1224h服务合计接近；调度等待、案间门禁与模型CPU成本分别记录。所有16案原生status=1到最大3ps，不是auto-shutoff收敛证据；采用训练级资格，不将“完成/标签有效”改写为严格收敛。

## 2. 原生数据、科学验收和资源安全

固定5nm内层mesh/最大3ps、auto-shutoff1e-6、440–460nm每1nm、3D正入射X/P_XLIKE、固定975nm MDC/237nm spacer/500nm有序六TiO2圆柱；保持原生材料、两冻结源对象、monitor、reference1722nm、Floquet/TE-TM/C_hat/P_scale/609D/H1/H2。理想几何仿真准入已获用户批准，实际制造资格仍UNRESOLVED。

每案均有真实RTX3080日志、唯一REAL entry、已保存输出FSP、原生H5和有限复E/H、独立science truth.h5、609D NPZ、21点native/H2 eta(+1)、P_scale、H2 P(+1)、停止日志、SHA/provenance及SCIENCE_RECEIPT。Native freshLOAD提取后关闭自己会话，未对已求解FSP switchtolayout/save。完整路径逐案见NATIVE_ARTIFACT_INDEX.json / CASE_RESULTS.csv；SHA复用Runner和receipt，未全量重哈希旧数据。

所有功率/标签有限，P_scale为正，七阶routing与原冻结numeric/profile检查通过，原生monitor总通量与EH积分一致。'''
report+=f"全新批次P_scale范围{energy['P_scale_global_range'][0]:.8f}…{energy['P_scale_global_range'][1]:.8f}，monitor/EH相对差最大{energy['monitor_vs_EH_max']:.3g}。"
report+='''原R/T/A proxy范围与残差见ENERGY_ROUTING_NORMALIZATION_AUDIT；A=1−R−T的代数闭合不是独立体吸收验证，不把legacy Tproxy混同P_scale。所有case记录包括风险标记，未调松旧门槛。

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
'''
for k in ['Mean','KRR','ExtraTrees','MLP']:
 m=models[k];fmt=lambda a:'未定义' if a is None else f'{a:.5f}';report+=f"|{k}|{m['P_plus1_H2']['MAE_before']:.7f}→{m['P_plus1_H2']['MAE_after_same124']:.7f}|{m['eta']['MAE_before']:.7f}→{m['eta']['MAE_after_same124']:.7f}|{m['P_scale']['MAE_before']:.7f}→{m['P_scale']['MAE_after_same124']:.7f}|{fmt(m['P_plus1_H2']['mean_fold_Spearman_before'])}→{fmt(m['P_plus1_H2']['mean_fold_Spearman_after'])}|\n"
report+='''
ExtraTrees P+略改善但仍不优于Mean，P_scale仍有部分预测信号，eta/P+未知K6排序仍不可靠；新增16没有带来可信的设计精度跃升。KRR/MLP排序没有改善，不选择性只报有利指标。完整450nm、谱MAE/RMSE、fold/pooled Spearman、invalid prediction fraction及seed信息见MODEL_METRICS_AFTER与FOLD_METRICS。Mean的跨fold pooled rho可受折间常数偏移影响，正式比较采用同定义mean-fold rho，常量预测未定义。

Top候选在原124每折按450nmP+选ceil(20%n)，稳定Case ID打破ties。'''
report+=f"本轮平均Top20%召回：KRR {meanrecall['KRR']:.4f}，ExtraTrees {meanrecall['ExtraTrees']:.4f}，MLP {meanrecall['MLP']:.4f}；相同k/n随机选择期望约{chance:.4f}，未形成可靠富集证据。"
report+='''历史pooledOOF丢失，旧Top召回不可重建，明确NOT_AVAILABLE，没有重训基线补造before。新16为主动选择的极小样本，不是独立随机全空间测试；其OOF单独列，不能以某个P_scale rho正值宣称P+排序可靠。

合库前消费者误把原pack_model_target容器(1,609)当(609,)；在0拟合时修正本轮形状检查，原标签不变。没有FDTD重复，之后40拟合一次完成；细节ML_UPDATE_REPAIR.json。

## 5. 几何覆盖和信息价值

'''
reduction=1-cov['after']/cov['same_remaining_pool_mean_distance_before'];report+=f"唯一几何156→172（+10.26%），原8192池已有16新计算、尚余8176未计算。以同一剩余池计算，归一化最近数据点距离均值{cov['same_remaining_pool_mean_distance_before']:.6f}→{cov['after']:.6f}（下降{100*reduction:.2f}%）；全池距离中位数{cov['pool_min_distance_before_quantiles'][2]:.6f}→{cov['pool_min_distance_after_quantiles'][2]:.6f}。\n"
report+='''轴级覆盖仍[27,25,27,27,27,27]，D2=130/185nm仍未补到；本轮主要增加六维组合覆盖，而非新轴值。距离变小部分是新增点的机械结果，不证明泛化提高。数据生产稳定性和可追溯性已得到本批证据，学习增益微弱也是本轮信息价值，不能用算得更多替代学习曲线判断。

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
'''
(D/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
verdict={k:prod[k] for k in ['AL16_REAL_SOLVER_ENTRIES','AL16_LABELS_VALID','AL16_LABELS_INVALID','AL16_REPLAY_COUNT','AL16_GPU_TIME']};verdict.update(STATUS='PASS_PRODUCTION_COMPLETE_MODELS_NOT_RANKING_READY',FAST_DATASET_TOTAL=172,MODEL_MAE_BEFORE_AFTER=models,MODEL_RANKING_BEFORE_AFTER={k:models[k]['P_plus1_H2'] for k in models},GEOMETRY_COVERAGE_CHANGE=cov,DIAG2='1/2',A2='HOLD',DOE56='HOLD',NEXT_ROUND_ENTRIES_AUTHORIZED=0,NEW_FDTD_THIS_TASK=16)
put('FINAL_VERDICT.json',verdict)
ledger.update(current_task_closed=True,remaining=0,execution_authorized=False,closed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),canonical_entry_authority=str(P/'data/runner_v31.db'),note='scientificprojection reconcilescanonicalREAL entry;16consumed permanently, noReplay');put('AL16_SCIENCE_LEDGER.json',ledger)
put('CURRENT_AUTHORITY.json',{'task':'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1','state':'COMPLETE','AL16_used':16,'AL16_total':16,'AL16_remaining':0,'AL16_labels_valid':16,'FAST_TOTAL':172,'second_round_authorized_entries':0,'DIAG2_used':1,'DIAG2_total':2,'A2':'HOLD','DOE56':'HOLD','inverse_optimization':'NOT_AUTHORIZED','numerical_final_validation':'NOT_CERTIFIED','continuation':str(D/'CONTINUATION.md')})
(D/'CONTINUATION.md').write_text('''# CONTINUATION — AL16 complete

Read FINAL_REPORT.md, FINAL_VERDICT.json, INDEPENDENT_PRODUCTION_RECONCILIATION.json and ML_UPDATE/TRAINING_COMPLETE.json.
16/16 REAL solverentries consumed,16labelsvalid,0invalid,0Replay. Allnewnativeoutputs retained underRunnerbatch3..18, scientificoutputs under preparedpackage/science_outputs. OldDIAG2ledger unchanged,1/2,A2HOLD;DOE56HOLD.
FAST_DATASET172 unique traininggrade geometries; original156immutable. Modelsupdated40fits, previousbaseline reused, old32train-only/new124fixedCV+new16grouped. OOFcheckpoint safe. Ranking stillunreliable (ET450nmP+meanfoldrho -0.044545); no inverseproduction certification.
This authorization CLOSED/remaining0. No more submit/run. Do not restart controller (exclusive forensiclock retained); do not replay anyentry. Firstspawn connection ended before jobs/entry, provednoentry then foregroundcontroller completed16once.
Next priority: review independent secondFAST16 proposal from originalpool; prioritizeD2=130/185coverage and sparsecombinations, refreshprotectionmetadata/manufacturingidealchecks before freeze. Newbudget0; usermustseparatelyauthorizeanynextproduction. No convergenceengineering expansion.
''',encoding='utf-8')
runner_sha=hashlib.sha256((P/'minimal_batch_runner_v3.1_final.py').read_bytes()).hexdigest();assert runner_sha=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7'
put('SHA_INVENTORY.json',{'hash_policy':'No new canonical scheme or fullnative rehash. Native/source/H5/label hashes reusedfrompercase receipts/canonicalDB; selectivecode/data identity hashes only.','runner':{'path':str(P/'minimal_batch_runner_v3.1_final.py'),'sha256':runner_sha},'source_setup_inventory':str(B/'SHA_INVENTORY.json'),'native_and_labels':art,'source_code':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [D/'AL16_SCIENCE_EXECUTION_CONTROLLER.py',D/'AL16_ML_UPDATE_SOURCE.py',B/'al16_extract_native_v1.py']],'merged_dataset':{'path':str(O/'FAST_DATASET_172G.npz'),'sha256':hashlib.sha256((O/'FAST_DATASET_172G.npz').read_bytes()).hexdigest()}})
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a],text=True).strip();old=read(D/'PROTECTED_OLD_LEDGER_SNAPSHOT.json');assert read(old['path'])==old['content'];assert git('diff','--cached','--name-only')==baseline['staged']
put('FINAL_GIT_AUDIT.json',{'branch':git('branch','--show-current'),'HEAD':git('rev-parse','HEAD'),'ahead_behind':git('rev-list','--left-right','--count','HEAD...@{u}'),'dirty_count':len(git('status','--short').splitlines()),'original_staged_unchanged':True,'commit':False,'push':False,'old_DIAG2_ledger_unchanged':True,'runner_sha_unchanged':True,'model_fits_complete':40,'dataset_geometry_unique':172,'original124heldout_preserved':True,'sealed_response_access':0,'scope':'Only task-owned production/science/MLoutputs created; no cleanup/reset or unrelatedstaging'})
allow=[str(p.relative_to(R)).replace('\\','/') for p in sorted(D.rglob('*')) if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py'] and 'ML_SOURCE_BEFORE' not in p.name];allow.append(str((D/'TASK_ALLOWLIST.txt').relative_to(R)).replace('\\','/'));(D/'TASK_ALLOWLIST.txt').write_text('\n'.join(allow)+'\n',encoding='utf-8')
print('FINAL_SUMMARY',json.dumps({'entries':16,'labels':16,'dataset':172,'fit':40,'gpu_hours':t['runner_real_solver_call_hours'],'service_hours':t['entry_to_science_hours_sum'],'git':read(D/'FINAL_GIT_AUDIT.json')}));print('DELIVERY_BEGIN')
for p in sorted(D.rglob('*')):
 if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py','.txt'] and 'ML_SOURCE_BEFORE' not in p.name:
  # Avoid huge oldbaseline fullgit status/source inventories, protectedoldledger and rawlogs; scientific artifacts stayremote.
  if p.name in ['GIT_BASELINE.json','PROTECTED_OLD_LEDGER_SNAPSHOT.json']:continue
  print(json.dumps({'name':p.relative_to(D).as_posix(),'base64':base64.b64encode(p.read_bytes()).decode()}))
