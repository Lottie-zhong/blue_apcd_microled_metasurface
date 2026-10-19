from pathlib import Path
import json,hashlib,sqlite3,subprocess,csv,numpy as np,base64,shutil
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';B=Q/'APCD_COUPLING_AL16_FAST_PRODUCTION_PACKAGE_V1';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
package=read(D/'AL50_FAST_PRODUCTION_MANIFEST.json');cases=package['cases'];cov=read(D/'COVERAGE_AND_SPARSE_DIMENSIONS.json');tests=read(D/'OFFLINE_INTERFACE_ACCEPTANCE.json');assert len(cases)==50 and tests['failed']==0
contract=read(B/'FAST_NUMERICAL_CONTRACT_V1.json');put('FAST_NUMERICAL_CONTRACT_V1.json',contract)
accept=read(B/'LABEL_EXTRACTION_AND_ACCEPTANCE.json');accept['extractor']=str(D/'al50_extract_native_v1.py');accept['command_after_completed_job']=['N:\\anaconda_envs\\RCP_LCP\\python.exe',str(D/'al50_extract_native_v1.py'),'--case','<exact_AL50_case_id>'];accept['diagnostics_not_available']='No prospective50truth/labels exists before separatelyauthorizedrealruns';put('LABEL_EXTRACTION_AND_ACCEPTANCE.json',accept)
policy=read(Q/'APCD_COUPLING_AL16_CLOSEOUT_AND_FLEXIBLE_OVERNIGHT_POLICY/FLEXIBLE_OVERNIGHT_POLICY.json');put('SCHEDULING_POLICY_REFERENCE.json',{'source':str(Q/'APCD_COUPLING_AL16_CLOSEOUT_AND_FLEXIBLE_OVERNIGHT_POLICY/FLEXIBLE_OVERNIGHT_POLICY.json'),'preferred_window':policy['PREFERRED_GPU_WINDOW'],'timezone':'Asia/Shanghai','daytime_allowed_if_resource_safe_and_authorized':True,'force_stop_at10':False,'cross_window':True,'current_authorized_entries':0})
put('BUDGET_CANDIDATE_NOT_AUTHORIZED.json',{'proposal_id':'AL50_FAST_R02_BUDGET_PROPOSAL_V1','maximum_requested_entries':50,'authorized_entries':0,'registered_production_jobs':0,'registered_real_entries':0,'per_case_max':1,'do_not_top_up_failures':True,'DIAG2_allocation':0,'cases':[{'case_id':c['case_id'],'external_execution_id':c['external_execution_id'],'attempt_id':c['attempt_id'],'source_fsp_sha256':c['source_fsp_sha256'],'physical_contract_sha256':c['physical_contract_sha256'],'entry_id':None,'runner_job_id':None,'solver_entered':False,'authorized':False} for c in cases],'authority_rule':'Only explicit humanrealrun authorization may activate separateAL50scientificbudget; Runner flags do not themselves enforceScienceOwnerauthority'})
put('STAGED_MODEL_EVALUATION_PLAN.json',{'current_new_fits':0,'checkpoints_new_labels_valid':[16,32,50],'prospective_dataset_sizes':[188,204,222],'final_if_failures':'At50enteredclose evaluate actualvalidcount; no newentries to fill missing50valid','GPU_solver_calls_during_evaluation':0,'base172_split':str(AL/'ML_UPDATE/FOLDS.json'),'preserve':'old32train-only; base140geometryheldoutIDs/folds unchanged; assignnew50caseordinalmod4, no geometry acrossfolds; preprocessing/trainonly','comparability':'same140baseline172holdouts forbeforeafter; old124also separate continuitytable; newAL50OOF separate; keep activelysampledcohort bias visible','models':'Reuse fixedMean/KRR/ExtraTrees128leaf3/6-32-32-42MLP andseeds17/29/43, no hyperparamselection onheldout','metrics':['spectralP+MAE/RMSE','nativeeta+MAE/RMSE','PscaleMAE/RMSE','samegeometrygroupedOOF','450nmP+meanfoldSpearman andseparatepooled','top20percentceil(n*.2)recall/regret withfrozenIDtiebreak;constantpredictionundefined','coverageall6marginalcounts+jointdistances','validuniquegeometries/GPUhour,failedentriescost'],'baseline':'Useexisting172OOF tocompute matched140baseline withoutrefitting previousmodels; checkpoint newOOF beforemodelreload','authority':'Futurewhole50budget permitsstagedexecution, model-no-gain alone does notchange frozenphysics; no currentexecutionauthorization','safety':'Pause newentry forsystemiccontract/native/normalization/resourceerror; do notabortcurrentlyrunningFDTD forclockdeadline; no solverreplay'})
prod=read(AL/'INDEPENDENT_PRODUCTION_RECONCILIATION.json');t=prod['AL16_GPU_TIME'];cost={'source':str(AL/'INDEPENDENT_PRODUCTION_RECONCILIATION.json'),'measured16_solver_minutes':t['per_valid_geometry_solver_minutes'],'measured16_service_minutes':t['per_valid_geometry_service_minutes'],'50_solver_call_hours':50*t['per_valid_geometry_solver_minutes']/60,'50_service_hours':50*t['per_valid_geometry_service_minutes']/60,'50_wall_hours_if_same_gate_intervals':50*prod['AL16_GPU_TIME']['first_entry_to_last_acceptance_wall_hours']/16,'preferred_window_hours':13,'planning_not_guarantee':True,'excluded':'newgeometrycostvariance,externalresourceconflict/queue,downtime,stagedCPUevaluationintermissions','50_entry_yield_scenarios':[{'valid_fraction':p,'expected_valid_geometries':50*p,'expected_FAST_total':172+50*p,'service_minutes_per_valid_geometry':t['per_valid_geometry_service_minutes']/p} for p in [1.,.9,.8]],'currency_cost':'UNKNOWN_TARIFF','approved_entries':0};put('TIME_AND_VALID_YIELD_ESTIMATE.json',cost)
counts=np.array(cov['axis_counts_172']);after=np.array(cov['axis_counts_prospective222']);levels=cov['axis_levels_nm'];diag=[]
for k in range(6):
 p=counts[k]/counts[k].sum();q=after[k]/after[k].sum();entropy=lambda a:float(-np.sum(a[a>0]*np.log(a[a>0]))/np.log(27));diag.append({'axis':'D'+str(k+1),'missing172':[d for d,c in zip(levels,counts[k]) if not c],'sparse_le2_172':[d for d,c in zip(levels,counts[k]) if c<=2],'selected_min_max_count_per_level':[int((after-counts)[k].min()),int((after-counts)[k].max())],'normalized_entropy172':entropy(p),'normalized_entropy_prospective222':entropy(q),'minimum_count_prospective':int(after[k].min()),'meaning':'Marginaluniformity is diagnostic, not soleacquisitiontarget; jointcoverage is primary'})
put('SIX_AXIS_MARGINAL_DIAGNOSTIC.json',diag)
runner_sha=hashlib.sha256((P/'minimal_batch_runner_v3.1_final.py').read_bytes()).hexdigest();assert runner_sha=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7'
put('SHA_INVENTORY.json',{'hash_rule':'OriginalI._canon physics fields reused; existinggeometry fingerprint convention ifneeded, no newcanonicalization. RequestedsourceFSP SHAcomputedonsave andindependentlyverified once duringofflineinstalledsubmit.','runner':{'path':str(P/'minimal_batch_runner_v3.1_final.py'),'sha256':runner_sha},'physics_contract_sha256':cases[0]['physical_contract_sha256'],'inputs':[{'case_id':c['case_id'],'input_fsp':c['input_fsp'],'source_fsp_sha256':c['source_fsp_sha256']} for c in cases]})
package['status']='AL50_FAST_PRODUCTION_READY';package['readiness_scope']='Ideal-geometry input/science package READY; actualfabricationUNRESOLVED; userrealrun authorization0; freshresourceandregistrycheckrequired beforefuturestart';package['extractor']=str(D/'al50_extract_native_v1.py');package['acceptance_contract']=str(D/'LABEL_EXTRACTION_AND_ACCEPTANCE.json');package['staged_model_plan']=str(D/'STAGED_MODEL_EVALUATION_PLAN.json');put('AL50_FAST_PRODUCTION_MANIFEST.json',package)
report='''# AL50_SELECTION_AND_COVERAGE_REPORT

## 状态与AL16正式收尾

**AL50_FAST_PRODUCTION_READY**，仅理想几何FAST生产包准备。NEW_FDTD=0，NEW_ENTRY=0，NEW_ML_FITS=0，AL50_AUTHORIZED=0。

172G合法开发集完整，AL16为16REALentries/16labelsvalid/0Replay，16案FSP/原生H5/scienceH5/609D路径均存在且原验收/独立对账保留。原156与新增16具有同冻结physics、21lambda/7order/TE-TM/reference/H1/H2定义及5nm3ps训练级合同，实际制造资格未建立、严格收敛未闭合。sealedresponse未访问，DOE56/DIAG2不入训练。

基于已保存OOF零拟合重算同124heldout几何，逐目标MAE与原报告误差<1e-12，450nmmeanfoldrho同样一致；旧32保持train-only，原new124分折未改。历史before指标复用原保存结果，未伪造已丢失的旧pooledOOF/Topk。见AL16_MODEL_METRIC_RECHECK_ZERO_FIT.json。ExtraTreesP+谱MAE0.0315207→0.0313934，rho−0.04649→−0.04455；仍无可靠排名，不能以预测最高功率作为选样依据。

## 六维覆盖与稀疏诊断

172G轴覆盖[D1..D6]=[27,25,27,27,27,27]。D2=130/185nm各0，AL16并未补到。其余五轴虽都有27档，样本数不均匀，不能当作覆盖充分。

|轴|172G缺失档位|172G样本数<=2的档位nm|归一化边际熵172→候选222|候选222最小档位样本数|
|---|---|---|---|---:|
'''
for d in diag:report+=f"|{d['axis']}|{d['missing172'] or '无'}|{d['sparse_le2_172'] or '无'}|{d['normalized_entropy172']:.4f}→{d['normalized_entropy_prospective222']:.4f}|{d['minimum_count_prospective']}|\n"
reduction=1-cov['same_remaining_pool_mean_distance_prospective222']/cov['same_remaining_pool_mean_distance_172'];report+=f"\n若全部50有效：总开发集222G、六轴均27档，D2=130/185各增至2例。其余未选原池上最近样本距离均值{cov['same_remaining_pool_mean_distance_172']:.6f}→{cov['same_remaining_pool_mean_distance_prospective222']:.6f}（预计下降{100*reduction:.2f}%）；全池距离中位数{cov['fullpool_quantiles_172'][2]:.6f}→{cov['fullpool_quantiles_prospective222'][2]:.6f}。候选间最小归一化距离{cov['minimum_selected_pair_distance']:.6f}，距离为Euclidean(D/130nm)。这是前瞻几何指标，没有新的物理数据或学习增益。\n"
report+='''
D3=170nm仍只有1例，部分边界档位较多；边际熵可能略降，不隐瞒。联合maximin为主、六轴稀疏bonus为辅，不声称50案使边际分布完全均匀。应在未来16/32/50阶段复查这些稀疏区与实际误差。D2仅2个强制补洞名额，不占用整个覆盖组；50案来自原8192有序池，不重新生成或扩域。

## 选样规则与完整50案

30coverage(60%)+10rawdisagreement(20%)+10stratifiedrandom(20%)。前两coverage分别在D2=130/185中选六维最远点；另外28coverage按联合最近距离乘温和六轴占用补偿得分，已在生成前记录算法。10disagreement直接复用172G模型已保存的未校准分歧，要求多样性目标距离>=0.4；不是置信区间、更不是最高预测效率。随机组seed20261018，在均值柱径十个分位层各选1案，保持有序维度。

|Case|D1,D2,D3,D4,D5,D6 nm|组别|原池索引|
|---|---|---|---:|
'''
for c in cases:report+=f"|{c['case_id']}|{','.join(map(str,c['ordered_D_nm']))}|{c['selection_role']}|{c['original_pool_index']}|\n"
report+='''
每案具体理由、原池位置、到172G及已选集距离、原始分歧值见AL50_SELECTED_GEOMETRIES.csv；完整六轴计数见COVERAGE_AND_SPARSE_DIMENSIONS.json。没有坐标排序或置换，没有新模型训练/预测来改变选样结论。

## 合法性、去重及科学身份

理想TiO2六柱：D100–230nm/5nm步长，中心x=[−725,−435,−145,145,435,725]nm、y0，节距290、柱高500、固定975nm MDC与237nmSiO2Spacer；周期1740×290nm。逐案检查相邻及周期D6→D1间隙、Y周期间隙、halfcell余量和H/D；全50非重叠且满足原mesh覆盖。实际工艺最小间隙/侧壁/最大深宽比未获得独立规范，保留UNRESOLVED，不以几何测量发明制程硬门槛。

刷新全部先前已核验保护几何、已计算172G、失败/历史Entry、DOE56全56预留、DIAG2两身份、sealed仅几何元数据、已知runtime queue/source/batch manifests及正式V31jobs/entries。50案内部唯一，对全部已核验保护集合交集0。DEDUPLICATION_AUDIT列明完整来源和canonical快照；未登记的外部手动任务无法穷尽，正式授权前需刷新同一已知registry，不宣称全服务器未知任务绝无冲突。

Case为K6AL_FAST_R02_G001…G050，attempt_001，ExecutionID=coupling:<case>/attempt_001。科学预算候选AL50_FAST_R02_BUDGET_PROPOSAL_V1请求最多50entry，每案1，当前授权0；所有Job/Entry映射null，未生产submit，不复用AL16或DIAG2身份/预算。隔离接口fixture含50schema注册记录、0Entry，不是生产登记。

## FSP、SHA和正式接口

50独立setupFSP已保存并重新LOAD核验。复用已认证setup-only模板，只恢复最大3ps及修改各案有序半径；其余已审计材料、源、MDC、Spacer、monitor、boundary、网格与reference不变；两个既有冻结X-forward源对象保持原样，不自行重建源。5nm/3ps/auto-shutoff1e-6，440–460nm21点，3D/P_XLIKE；FDTD物理时长与平台排程分开。

原physics SHA32e60a…dea5的哈希范围沿用原六字段规则，完整时间/mesh由FAST_NUMERICAL_CONTRACT、FSP SHA及实际readback绑定，不伪称physics SHA独自编码全部setup。逐案输入路径、完整SHA、ExternalExecutionID、输出目录、checks与预算候选都在AL50_FAST_PRODUCTION_MANIFEST.json/SHA_INVENTORY。没有覆盖任何历史FSP/H5。

科学总包是wrapper；正式Runner输入为runner_manifests/每案单Job JSON，以submit/run/status执行，保持truth-before-next。已安装冻结Runner解析器在隔离SQLite接受50输入，跨batch重复身份和错误SHA均被拒；含提取脚本import/无solver静态检查及旧模型指标复核，共55PASS/0FAIL，real/fake run均0。安装RunnerSHA5778eefb…cb7不变，无部署/调度平台开发。

提取脚本复用AL16已实证的只读FSP→复杂EH→原生H5检查→冻结post/H1/H2→609D及21eta/P_scale/H2P+；只改新包路径/案例角色，不改科学公式。前瞻50案尚无truth/labels，离线PASS不等于物理有效。labels-valid receipt且Entry独立对账后才可进入FAST，所有失败原生证据保留、禁止solverReplay。science_entry_authorized=false不是Runner强制安全锁，Coupling必须依据未来明确人类授权与科学预算控制入场。

## 预算、成本与调度

'''
report+=f"沿用AL16实测9.6232min/Runner调用、11.7091min/至科学验收服务：50次规划求解调用约{cost['50_solver_call_hours']:.2f}h、服务约{cost['50_service_hours']:.2f}h；若案间门禁节奏相同，墙钟约{cost['50_wall_hours_if_same_gate_intervals']:.2f}h。均非保证，不含未来几何差异/资源等待和阶段性模型评估延迟。\n"
report+='''50entry在100%/90%/80%有效率情景下分别新增50/45/40有效几何，即222/217/212G；90/80%为规划情景，不是已测新批次成功率。失败消耗entry，不自动补足50、不借DIAG2预算；无报价依据不报货币成本。

北京时间21:00–次日10:00仅PREFERRED_GPU_WINDOW，可跨夜；白天实际资源安全且获得授权时可运行，10:00不截断既有FDTD。允许他人CPUFDTD/EDT/GUI，只有实际GPU/CPU/RAM/许可证/磁盘或未知资源门禁冲突延后新entry。正式入场必须实时检查，准备态不对未来资源背书。

## 16/32/50阶段科学与学习验收计划

未来若获完整授权，逐案串行入场、native保存、科学receipt与Entry原子对账。新增有效几何到16/32/50时，暂停新增entry做零求解模型评估（可用CPU），总开发规模188/204/222。若50entry结束仅有较少有效标签，则按实际数做最终评估，不自动新建case补额。

保留172G基线的old32train-only与既有140个heldoutID/四折；新增50按冻结case顺序mod4分折，同几何不跨折，预处理仅训练折。相同140heldout给出before/after，旧124另列长期可比表，新50cohort独立OOF，避免主动选样偏倚伪装随机总体测试。采用原固定Mean/KRR/ExtraTrees/小MLP及种子，不新建复杂网络。

每阶段报告谱P+/eta/Pscale MAE/RMSE、450nmmeanfoldSpearman及独立pooled、Top20%ceil(n*.2)recall/regret及固定IDties规则、invalid预测、六轴与联合覆盖、有效几何/GPUh、失败成本。OOF先持久化再reload；已有172OOF可零拟合给出同140基线，历史缺失OOF不伪造。模型暂不改善不授权修改冻结物理合同；只有系统性科学合同/数据/安全异常暂停新entry，不因时间窗口kill solver。

## 最终边界

准备态理想几何科学输入与接口准入READY，实际可制造性UNRESOLVED，真实生产需用户单独授权及启动前实时资源/registry复核。本轮NEW_FDTD=0，AL50_AUTHORIZED=0，DIAG2=1/2，A2 HOLD，DOE56 HOLD。原科学Ledger和172G/模型资产保留。
'''
(D/'AL50_SELECTION_AND_COVERAGE_REPORT.md').write_text(report,encoding='utf-8')
(D/'AL50_PRODUCTION_READINESS.md').write_text('''# AL50_PRODUCTION_READINESS

**AL50_FAST_PRODUCTION_READY** — 理想几何FAST输入与科学接口包完成；实际制造UNRESOLVED，求解授权0。

50原池有序几何，30coverage/10disagreement/10stratifiedrandom。D2=130/185缺口各安排2案（其中首两案专门补洞），兼顾其余五轴和六维联合覆盖。50独立FSP保存+freshLOAD检查通过，源SHA/contract/ExternalExecutionID/输出路径/单案Runner manifests与预算映射完整。55定向检查PASS，生产DB无新Job/Entry；隔离fixture50Job/0Entry。

读取AL50_FAST_PRODUCTION_MANIFEST.json及SHA_INVENTORY；科学wrapper不是可一次跳过验收的bulk run请求。正式接口：C:\\Users\\DELL\\anaconda3\\python.exe <frozenRunner> submit <percase batch_name> --manifest <percase path>；run <same batch_name>；status <same batch_name>。本轮没有执行生产submit或run，false科学标记本身也不是Runner安全锁。

未来授权应明确此固定50案、最多50真实entry、每案1次/noReplay。启动前刷新保护registry/队列与GPU/CPU/RAM/许可证/磁盘实时资源，绑定独立AL50预算投影，不改旧Ledger。逐案Solver→nativeFSP/H5→冻结609D/21目标→science receipt→Entry对账→FAST入库。只允许labels-valid；失败证据保留，不退额度、不换身份重跑。原模板/FAST数值/H1H2不变，不以训练级忽略非法功率/监视器/标签。

新增有效16/32/50进行零求解模型评估，保留172基线140heldout和old32train-only；总预算结束按实际有效数量最终评估，不自动补样。详细计划STAGED_MODEL_EVALUATION_PLAN.json。指标暂不改善不能改合同；系统性科学/安全故障暂停新entry。

夜间21:00–次日10:00优先，非硬截止；允许白天安全运行、跨夜完成，不终止运行中solver或其他用户任务。50次规划约8.02h求解调用、9.76h科学服务、同门禁节奏约10.13h墙钟；并非一夜完成保证。

批准后可由Coupling独立执行，当前等待用户单独真实求解授权。NEW_FDTD=0，NEW_FITS=0，AL50_AUTHORIZED=0；DIAG2=1/2，A2 HOLD，DOE56 HOLD。
''',encoding='utf-8')
(D/'CONTINUATION.md').write_text('''# CONTINUATION

AL50_FAST_PRODUCTION_READY. Read AL50_SELECTION_AND_COVERAGE_REPORT.md, AL50_FAST_PRODUCTION_MANIFEST.json, AL50_PRODUCTION_READINESS.md.
50fixedidealgeometries fromoriginal8192pool,30coverage10disagreement10random, no newfit. D2missing130/185 addressed, otheraxes/jointcoverage measured; D3170 remains sparse. 50FSP saved+reloaded, SHA andpercaseV31manifests frozen.55offlinechecksPASS, production0newjobs/entries; fixture0entry.
BudgetproposalAL50_FAST_R02_BUDGET_PROPOSAL_V1 max50/requested, authorized0. No submit/run until explicituserauthorization. Do notreplayAL16 (16/16closed), noDIAG2budgetuse; DIAG2=1/2,A2HOLD,DOE56HOLD.
Future stagedMLat16/32/50newvalid, base172heldout140fixed+old32trainonly, no contractualchangeifmodelnoprogress. Night21–10preferredonly, flexibledaytime/crossnight/resourcesafe. Nextpriority: userseparaterealrunapprovalforthisexactpackage, thenfreshresource/registrycheck.
''',encoding='utf-8')
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a],text=True).strip();base=read(D/'GIT_BASELINE.json');assert git('diff','--cached','--name-only')==base['staged'];put('FINAL_AUDIT.json',{'status':'AL50_FAST_PRODUCTION_READY','branch':git('branch','--show-current'),'HEAD':git('rev-parse','HEAD'),'ahead_behind':git('rev-list','--left-right','--count','HEAD...@{u}'),'dirty_count':len(git('status','--short').splitlines()),'original_staged_preserved':True,'commit':False,'push':False,'geometry_count':50,'saved_reloaded_inputs':50,'tests_passed':55,'new_FDTD':0,'new_entries':0,'new_fits':0,'AL50_authorized':0,'sealed_responses':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','runner_sha_unchanged':True,'old_science_ledgers_unchanged':True})
(D/'TASK_ALLOWLIST.txt').write_text('\n'.join(str(p.relative_to(R)).replace('\\','/') for p in sorted(D.rglob('*')) if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py'] and 'offline_interface_fixture' not in str(p))+'\nreports/coupling/APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1/TASK_ALLOWLIST.txt\n',encoding='utf-8')
print('FINAL',json.dumps(read(D/'FINAL_AUDIT.json')));print('DELIVERY_BEGIN')
for p in sorted(D.rglob('*')):
 if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py','.txt'] and 'offline_interface_fixture' not in str(p) and p.name!='GIT_BASELINE.json':print(json.dumps({'name':p.relative_to(D).as_posix(),'base64':base64.b64encode(p.read_bytes()).decode()}))
