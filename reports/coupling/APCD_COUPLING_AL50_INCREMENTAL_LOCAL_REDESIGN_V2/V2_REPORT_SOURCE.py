from pathlib import Path
import json,csv,hashlib,subprocess,base64,datetime
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';V=Q/'APCD_COUPLING_AL50_COVERAGE_DRIVEN_SELECTION_V1';D=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';AL=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
a=read(D/'OFFLINE_INTERFACE_ACCEPTANCE.json');extra=read(D/'V2_ADDITIONAL_TARGETED_CHECKS.json');assert a['passed']==55 and a['failed']==extra['failed']==0
sup=read(D/'SUPERSEDED_ZERO_ENTRY.json');canon=read(D/'DEDUPLICATION_AUDIT.json');assert not any(e['case_id'] in {c['case_id'] for c in sup} for e in canon['canonical_entries']);extra['tests'].append({'test':'superseded10canonicalREALentrycountzero','pass':True});extra['passed']=len(extra['tests']);put('V2_ADDITIONAL_TARGETED_CHECKS.json',extra)
put('BASE_VERIFIER_METADATA_LOGGING_REPAIR.json',{'issue':'After55testsandacceptanceJSONcompleted, reusedterminalprintlookedforV1coveragefilename inV2folder','resolved':'V2source usesCOVERAGE_V1_V2_COMPARISON andLOCAL_DESIGN_SUMMARY; no science/testlogic changed','repeated_fits':0,'repeated55tests':False,'validated_results_preserved':True})
m=read(D/'AL50_FAST_PRODUCTION_MANIFEST_V2.json');summary=read(D/'LOCAL_DESIGN_SUMMARY.json');cov=read(D/'COVERAGE_V1_V2_COMPARISON.json');decision=read(D/'INCREMENTAL_SELECTION_DECISION.json');v1=read(V/'AL50_FAST_PRODUCTION_MANIFEST.json');old={c['case_id']:c for c in v1['cases']};cases=m['cases'];ret=[c for c in cases if c['case_id'] in old];new=[c for c in cases if c['case_id'] not in old]
assert len(ret)==40 and len(new)==10
m['status']='AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY';m['active_authority']='V2only; V1archivedinplace; single50entryproposal, neverapprovebothversions';m['local_pair_graph']=str(D/'AL50_LOCAL_PAIR_GRAPH.csv');m['interaction_groups']=str(D/'AL50_INTERACTION_GROUPS.csv');m['budget_proposal']['authorized_entries']=0;put('AL50_FAST_PRODUCTION_MANIFEST_V2.json',m)
put('BUDGET_CANDIDATE_NOT_AUTHORIZED_V2.json',{'id':m['budget_proposal']['id'],'inherited_single_maximum_entries':50,'authorized_entries':0,'per_case_max':1,'V1_V2_mutually_exclusive':True,'active_manifest':str(D/'AL50_FAST_PRODUCTION_MANIFEST_V2.json'),'archive_V1_manifest':str(V/'AL50_FAST_PRODUCTION_MANIFEST.json'),'superseded_for_future_admission':[c['case_id'] for c in sup],'new_credit':0,'DIAG2_allocation':0,'cases':[{'case_id':c['case_id'],'external_execution_id':c['external_execution_id'],'source_fsp_sha256':c['source_fsp_sha256'],'entry_id':None,'solver_entered':False,'authorized_entries':0} for c in cases]})
runner_sha=hashlib.sha256((P/'minimal_batch_runner_v3.1_final.py').read_bytes()).hexdigest();assert runner_sha=='5778eefb6eb07457b4447cadcfd4ca3f51bb4983ed7d14466cf0a5f64a067cb7';put('SHA_INVENTORY_V2.json',{'rule':'Originalphysicscanonicalruleunchanged; reuse40sourcepins, new10sourceSHAoncreation+installedinterfaceverification; oldsuperseded10checkedunchanged. No oldtruth/fullnativehashrepeat.','runner_sha256':runner_sha,'original_V1_manifest':str(V/'AL50_FAST_PRODUCTION_MANIFEST.json'),'cases':[{'case_id':c['case_id'],'input_fsp':c['input_fsp'],'source_fsp_sha256':c['source_fsp_sha256'],'external_execution_id':c['external_execution_id'],'retained_from_V1':c['case_id'] in old} for c in cases]})
groups=list(csv.DictReader((D/'AL50_INTERACTION_GROUPS.csv').open(encoding='utf-8')));cost=read(V/'TIME_AND_VALID_YIELD_ESTIMATE.json');put('TIME_ESTIMATE_V2.json',{'unchanged_total_prospective_entries':50,'authorized_entries':0,'source':str(V/'TIME_AND_VALID_YIELD_ESTIMATE.json'),'solver_hours':cost['50_solver_call_hours'],'science_service_hours':cost['50_service_hours'],'wall_hours_same_gate_intervals':cost['50_wall_hours_if_same_gate_intervals'],'setup_FSPs_regenerated':10,'retained_FSPs_reused':40,'noextra_local_solver_budget':True,'uncertainty':'PlanningfromAL16, notguarantee. No budgetincrease to completefailedcorners. Localgroupsremainincomplete ifany requiredtruthinvalid.'})
report='''# AL50_V1_V2_DIFF_REPORT

## 最终裁决

**AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY**，理想几何FAST准备态。NEW_FDTD=0、NEW_ENTRY=0、NEW_FITS=0、AL50_AUTHORIZED=0。保留原40案，仅替换10案，不增加原50entry候选上限。

|角色|V1|V2|
|---|---:|---:|
|全局覆盖|30|30|
|模型分歧|10|8|
|分层随机|10|2|
|单柱局部|0|8|
|双柱交互补充|0|2|
|合计|50|50|

原30coverage、所有D2=130/185补充案例均保留；分歧组保留前8，随机组强制保留D2=185的G050，再用全池覆盖损失最小原则选另1案。'''
report+=f"实际保留随机案为{decision['random_keep']}与K6AL_FAST_R02_G050。\n"
report+='''
## 1. 先审计既有局部信息

对历史172G与V1固定50案逐几何枚举单轴恰5nm邻边和六维任意双轴四角，不排序柱径。172G有11条原已labels-valid单柱配对，围绕K6V1_S31；V1计划50案没有新增这种邻边，原172+50中完整四角设计0。11条历史配对全部保留并优先利用，不为它们再求解。

标签溯源在LOCAL_GEOMETRY_NODE_INDEX.json、AL50_LOCAL_PAIR_GRAPH.csv：包含有序几何、Case ID、原生/输入FSP、SHA及标签/缓存Case键。历史609D仍指向原inventory/标签，新点标记NOT_RUN；旧32共享标签容器通过Case键区分。EXISTING_VALID_PAIR_DIFFERENCES.json保存11条已有配对的21λ P(+1)/eta/P_scale真实差分，仅描述既有全波响应，不冒充模型验证。

当前有效配对仍为11；新增12条是设计/混合边，必须等待新标签，不能称23条已有效。完整四角**设计2组、真值完整0组**。

## 2. 局部设计及新10案

D3=170nm唯一历史合法锚点K6GDP2_DEV_G059=[115,110,170,105,225,225]。对六柱各+5nm，再对D2/D3各−5nm，形成8个单柱新点；加D2+D3各+5nm交互角。另复用K6V1_S31=[220,195,210,150,140,210]及其已有D1+5/D6+5标签，只补D6+D1各+5nm角。

|新Case|有序D1…D6 nm|角色/原因|
|---|---|---|
'''
for c in new:report+=f"|{c['case_id']}|{','.join(map(str,c['ordered_D_nm']))}|{c['selection_reason']}|\n"
report+='''
|组|锚点|柱对|既有有效角|待求解角|当前状态|
|---|---|---|---:|---:|---|
'''
for g in groups:report+=f"|{g['group_id']}|{g['anchor']}|D{g['axis_i']}-D{g['axis_j']}|{g['existing_valid_corners']}|{4-int(g['existing_valid_corners'])}|设计完整，真值未完整|\n"
report+='''
两个不同锚点、两个不同柱对，包括D2与周期边界D6-D1。S31复用3角、G059复用1角，不重复消耗历史预算。新增8单柱点与2双柱角都采用完整集成MDC+K6 3DFDTD FAST，未使用孤立柱叠加，也不把交互索引写入/修改正式609D目标。本文仅实施用户明确的局部四角设计，不外推未提供论文的机理结论。

## 3. 覆盖取舍与信息收益边界

'''
report+=f"相同剩余原8192池上最近数据点距离均值：V1 {cov['same_remaining_pool_mean_V1']:.6f}→V2 {cov['same_remaining_pool_mean_V2']:.6f}，增加{100*cov['relative_coverage_distance_increase']:.2f}%（覆盖损失）；最坏距离均为{cov['fullpool_max_V1']:.6f}，未恶化。若全50有效，D2=130/185各仍2例，D3=170从V1的1例增至V2的7例；六轴各27档保持。\n"
report+='''
局部组故意相距5nm，不再适用V1全局采样最小距离0.4；这是实验角色改变，非几何非法或制造门槛放宽。原30覆盖未动，只用10非覆盖槽换取12条新待验局部边及2个四角设计。新增局部点由用户明确5nm扰动规则派生，可能不属于原8192离散抽样行，但均在100–230/5nm合法理想域；来源不伪装成原池选中。

预计信息收益是同锚点差分、符号和非加性交互可以被观察；并未证明代理MAE、排序或全空间泛化会改善。有效四角依赖所有必要角labels-valid，若失败不补额、不把缺角组标为完整。

## 4. V1归档、身份与预算

V1原目录及50个FSP/manifest原样保留，V1_ARCHIVE_REFERENCE记录归档引用。40保留案复用完全相同的FSP路径/字节SHA、Case ID、Attempt、ExternalExecutionID与单案Runner manifest；输出目录也沿原映射。10被移出案在本轮声明SUPERSEDED_ZERO_ENTRY，原文件不删除、不改写，futureconsumer不得再把这些案算作V2候选。

10新案使用K6AL_FAST_R02V2_L001…L008及I001/I002，独立输入路径/SHA/ExecutionID；没有把旧ExecutionID绑定到新FSP。V1与V2是同一50-entry候选预算的互斥版本，当前只能审阅V2，不允许两版分别授权后叠加100entry。没有生产submit/Entry；fixture注册只在隔离SQLite，Entry0。全历史保护/失败/DOE56/DIAG2/sealed仅几何元数据、172已计算、全部V1保留及移出几何、已知runtimequeue与canonicalDB已刷新去重；新10与保护集合冲突0，V2内部50唯一。

## 5. 精度与接口不变

原5nm/最大3ps、auto-shutoff1e-6、21λ440–460nm、Native-M1、固定975nm顶部MDC与237nmSpacer、500nm柱高、290nm心距、两冻结X/P_XLIKE源、monitor/reference/TE-TM/Floquet/H1/H2/609D均不变。10新FSP仅修改有序半径及恢复3ps，与模板其余审计属性一致；40旧FSP无重建。实际制造资格仍UNRESOLVED，理想几何仿真准入；训练级不是最终收敛级。

独立新consumer仅将原只读提取器指向V2manifest，保留案及新案均按case-record输出，不改冻结后处理。Runner冻结源码SHA5778eefb…cb7不变，无部署或平台开发。输入、预算映射和单案V3.1 manifests见AL50_FAST_PRODUCTION_MANIFEST_V2.json / SHA_INVENTORY_V2.json。

## 6. 家族防泄漏与评估

原124heldout几何身份与指标口径保留。发现历史S31锚点属old32，而其11扰动分布在原四折验证中，因此不能把旧几何分组成绩冒称局部家族独立泛化。

双轨报告：原协议继续作为legacy对比，不宣称family-independent；额外严格轨保持相同124heldout IDs，对任何触及验证的局部连通家族，清除其所有训练成员。被purge的old32不移入验证。未来172G baseline与V2 after必须采用相同purge重算后再比，不能拿未purge旧指标与purge新指标混比。本轮只做索引验证，不训练。

G059及9个新家族成员统一归原锚点第3折，整个家族同时留出。S31旧32锚点不作测试样本；其完整四角可在truth闭合后报告真实物理非加性交互，但不宣称该family模型out-of-sample局部能力。严格局部模型指标只有一个可测锚点家族，样本范围有限；两个设计组不等于两个独立的heldout泛化家族。

指标：局部差分MAE=mean|ΔYhat−ΔY|，局部方向sign一致率（精确tie单列），家族内局部排序/成对次序一致率；非加性I=Yij−Yi−Yj+YD及|Ihat−I|（仅整个组符合heldout资格时）。Y使用同冻结21λ H2P(+1)、eta、P_scale。绝对差/原参考量并列，近零分母不虚构稳定相对量；5nm FAST差分仍带数值风险，不宣称制程导数或最终精度。无孤立柱近似。

继续新增有效16/32/50的零求解模型评估计划，固定Mean/KRR/ExtraTrees/小MLP与训练折预处理；模型不改善不改冻结科学合同。局部组不完整时留缺失状态，不伪造交互数值。

## 7. 验收与预计成本

'''
report+=f"V2完整55项输入/接口/旧OOF复核全部PASS，新增{extra['passed']}项身份复用、归档保护、D2/coverage保留、新SHA/ExecutionID、23边差分/溯源、2四角/穷举、family泄漏purge及预算检查全部PASS；合计{55+extra['passed']}PASS/0FAIL。隔离fixture50schemaJob/0Entry，real/fake run均0。复用验证器最后的终端打印路径已修正，没有重跑已通过55项，也没有科学改动。\n"
report+=f"\n总候选仍50，预计求解调用{cost['50_solver_call_hours']:.2f}h、科学服务{cost['50_service_hours']:.2f}h、同门禁节奏墙钟{cost['50_wall_hours_if_same_gate_intervals']:.2f}h；没有额外局部求解预算。仅10新setup，40重用。估计非保证，失败不Replay或自动补角。北京时间21:00–次日10:00为优先窗口，可跨夜和资源安全时白天运行，不强制截断。\n"
report+='''
最终：AL50_AUTHORIZED=0，NEW_FDTD=0，DIAG2=1/2，A2 HOLD，DOE56 HOLD。下一步仅等待对此V2固定50案的独立真实求解授权及启动前实时资源/registry复核。
'''
(D/'AL50_V1_V2_DIFF_REPORT.md').write_text(report,encoding='utf-8')
(D/'AL50_V2_PRODUCTION_READINESS.md').write_text(f'''# AL50_V2_PRODUCTION_READINESS

**AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY**。

保留40/替换10；30coverage+8disagreement+2random+8单柱+2交互。V1整包原位归档，40案复用原Case/ExecutionID/FSP/SHA，10旧案SUPERSEDED_ZERO_ENTRY，10新案独立身份。V1/V2同一50entry候选预算，互斥而非叠加；当前授权0。

已有有效5nm局部边11，新增待求解边12，图总23；四角设计2组/2锚点，**truth完整0**。G059D2-D3待3角，S31D6-D1待1角。所有future真值必须是完整集成MDC+K6全波FDTD，609D不变。

覆盖平均距离较V1增加1.17%，最坏距离不变；原30coverage及D2补洞全保留，D3=170预计1→7。无局部必然改善代理的承诺。

原55项PASS+新增{extra['passed']}项PASS，总{55+extra['passed']}；新10FSP保存freshLOAD，40旧FSP不重建，全部active50在隔离安装Runner接口验收。无real/fake run、无生产submit/Entry、无模型fit。物理输入5nm3ps/440–46021点/MDC+237nmSpacer/有序TiO2六柱冻结，actual制造UNRESOLVED。

未来仅可基于AL50_FAST_PRODUCTION_MANIFEST_V2.json的active50授权，科学budgetcandidate授权前为0。读取单案runner_batches，逐案submit/run/status，fresh资源与全历史去重后入场，单案最多1、失败也计预算、NoReplay、truth-before-next。旧V1移出10案不得被消费者继续提交；不要运行旧V1总包。

16/32/50阶段采用LOCAL_FAMILY_EVALUATION_PLAN.json：保留124heldout身份；legacy与family-purged轨分开，matched172baseline也purge，G059全family第3折，S31old32不作为局部heldout测试；禁止锚点/扰动跨train/val。现阶段只验证路由，无新训练。

预计50次8.02h求解/9.76h科学服务；21:00–次日10:00优先非硬截止，跨夜/白天资源安全可灵活。当前AL50_AUTHORIZED=0，NEW_FDTD=0；DIAG2=1/2、A2 HOLD、DOE56 HOLD。停止于Solver入场前，等待用户单独授权V2。
''',encoding='utf-8')
put('CURRENT_AUTHORITY.json',{'task':'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2','status':'AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY','active_manifest':str(D/'AL50_FAST_PRODUCTION_MANIFEST_V2.json'),'V1_status':'ARCHIVED_NOT_ACTIVE','budget_single_maximum':50,'authorized_entries':0,'new_FDTD':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','no_automatic_local_truth_completeness':True})
(D/'CONTINUATION.md').write_text('''# CONTINUATION

AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY. ActivecandidateV2only; V1immutablearchive, same50entryproposal notadditionalbudget.40retainedexactidentities/FSP/SHA,10supersededzeroentry,10newlocalidentities/inputs. No productionregistration/run, authorized0.
Read AL50_V1_V2_DIFF_REPORT.md, AL50_FAST_PRODUCTION_MANIFEST_V2.json, AL50_LOCAL_PAIR_GRAPH.csv, AL50_INTERACTION_GROUPS.csv andreadiness.
Validexistingedges11/newpending12;2fourcornerdesigngroups(twoanchors),0truthcomplete. G059familyD3=170,D2-D3 interaction; S31boundaryD6-D1 reuses3historicalcorners. Preserveall30coverage/D2gaps. Mean coveragedistance+1.17%vsV1,maxsame; D3170prospective1→7.
Legacy124holdouts kept; strictfamilypurging separate matchedbaseline, G059allfamilyfold3, S31old32notlocalheldouttest. Currentfits0. Original55+10newchecksPASS. No inference localmodelimprovementbeforetruth.
Nextpriority: explicituserrealrunapprovalforthisexactV2active50, freshregistry/resources, neverrunV1supersededcases. DIAG2=1/2,A2HOLD,DOE56HOLD.
''',encoding='utf-8')
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a],text=True).strip();base=read(D/'GIT_BASELINE.json');assert git('diff','--cached','--name-only')==base['staged'];put('FINAL_GIT_AUDIT.json',{'branch':git('branch','--show-current'),'HEAD':git('rev-parse','HEAD'),'ahead_behind':git('rev-list','--left-right','--count','HEAD...@{u}'),'dirty_count':len(git('status','--short').splitlines()),'staged_unchanged':True,'commit':False,'push':False,'retained':40,'replaced':10,'new_FDTD':0,'new_fits':0,'AL50_authorized':0,'runner_unchanged':True,'V1_archive_preserved':True,'checks_passed':55+extra['passed']})
(D/'TASK_ALLOWLIST.txt').write_text('\n'.join(str(p.relative_to(R)).replace('\\','/') for p in sorted(D.rglob('*')) if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py'] and 'offline_interface_fixture' not in str(p))+'\nreports/coupling/APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2/TASK_ALLOWLIST.txt\n',encoding='utf-8')
print('FINAL',json.dumps(read(D/'FINAL_GIT_AUDIT.json')));print('DELIVERY_BEGIN')
for p in sorted(D.rglob('*')):
 if p.is_file() and p.suffix.lower() in ['.json','.csv','.md','.py','.txt'] and 'offline_interface_fixture' not in str(p) and p.name!='GIT_BASELINE.json':print(json.dumps({'name':p.relative_to(D).as_posix(),'base64':base64.b64encode(p.read_bytes()).decode()}))
