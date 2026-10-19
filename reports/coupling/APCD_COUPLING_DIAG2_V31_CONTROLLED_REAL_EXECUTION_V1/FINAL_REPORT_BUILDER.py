from pathlib import Path
import json,sys,sqlite3,subprocess,os,hashlib
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3');B=R/'reports/coupling/APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING';T='APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1';D=R/'reports/coupling'/T
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,j):Path(p).write_text(json.dumps(j,indent=2,ensure_ascii=False,allow_nan=False,default=str),encoding='utf-8')
sys.path.insert(0,str(R/'scripts/coupling_ml'));from diag2_v31_bound_admission_view_v1 import reconcile
ledger=read(B/'DIAG2_SCIENCE_LEDGER.json');rec=reconcile(ledger);assert rec['entered_total']<=2;put(D/'FINAL_ENTRY_RECONCILIATION.json',rec)
con=sqlite3.connect(Path(ledger['sole_entry_evidence_db']).as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;jobs=[dict(x) for x in con.execute('SELECT * FROM jobs ORDER BY id')];entries=[dict(x) for x in con.execute('SELECT * FROM solver_entries ORDER BY id')];con.close();assert all(j['status']!='RUNNING' for j in jobs),'Do not finalize while solver still RUNNING'
put(D/'RUNNER_FINAL_READONLY_AUDIT.json',dict(jobs=jobs,entries=entries));results={};comparisons={};errors={}
for i,k in enumerate(['A1','A2']):
 p=D/(k+'_SCIENTIFIC_ACCEPTANCE.json');result=read(p) if p.exists() else None;results[k]=result
 c=D/(k+'_science/TIME_CONVERGENCE_COMPARISON.json')
 if c.exists():comparisons[k]=read(c)
 ep=D/(k+'_SCIENTIFIC_ACCEPTANCE_HOLD.json')
 if ep.exists():errors[k]=read(ep)
 count=rec['cases'][i]['entered_count'];ledger['cases'][i]['entered_count']=count;ledger['cases'][i]['entry']=rec['cases'][i]['entry'];ledger['cases'][i]['entry_id']=rec['cases'][i]['entry']['id'] if rec['cases'][i]['entry'] else None;ledger['cases'][i]['solver_entered']=bool(count)
 if not result:ledger['cases'][i].update(truth_valid=False,labels_valid=False,status='HOLD_SCIENTIFIC_ACCEPTANCE' if count else 'HOLD_NOT_ENTERED')
ledger['entered_total']=rec['entered_total'];ledger['remaining_total']=2-rec['entered_total'];ledger['truth_valid_total']=sum(bool(x.get('truth_valid')) for x in ledger['cases']);ledger['labels_valid_total']=sum(bool(x.get('labels_valid')) for x in ledger['cases']);assert ledger['labels_valid_total']<=ledger['truth_valid_total']<=ledger['entered_total'];ledger['execution_authorized']=False;ledger['current_task_closed']=True;tmp=B/'DIAG2_SCIENCE_LEDGER.final.tmp';put(tmp,ledger);os.replace(tmp,B/'DIAG2_SCIENCE_LEDGER.json')
subset=[]
for i,k in enumerate(['A1','A2']):
 r=results[k];b=ledger['cases'][i]
 if r:
  assert r['case_id']==b['case_id'] and r['attempt_id']==b['attempt_id'] and r['external_execution_id']==b['external_execution_id'] and r['original_case_request_sha256']==b['case_request_sha256'] and r['solver_entry']['id']==rec['cases'][i]['entry']['id'] and r['native']['native_fsp']['sha256']==jobs[i]['output_sha256']
 subset.append(dict(case_id=b['case_id'],entered_count=b['entered_count'],truth_valid=bool(b.get('truth_valid')),labels_valid=bool(b.get('labels_valid')),scientific_acceptance=r['scientific_acceptance'] if r else 'NOT_RUN'))
put(D/'SCIENCE_LEDGER_SUBSET_RECONCILIATION.json',dict(status='PASS',cases=subset,entered_total=ledger['entered_total'],truth_valid_total=ledger['truth_valid_total'],labels_valid_total=ledger['labels_valid_total'],remaining_total=ledger['remaining_total'],independent_runner_sql_evidence=str(D/'RUNNER_FINAL_READONLY_AUDIT.json'),rule='labels-valid subset truth-valid subset entered; numerical advancement remains independent HOLD'))
ok=len(comparisons)==2 and all(r and r['scientific_acceptance']=='PASS' for r in results.values());numerical='TWO_ANCHOR_TIME_SENSITIVITY_WITHIN_FROZEN_FLAGS_NOT_GLOBAL_CONVERGENCE' if ok else 'HOLD_P_SCALE_TIME_SENSITIVITY_EXCEEDS_1PCT_A2_NOT_RUN'
v={}
for i,k in enumerate(['A1','A2']):
 v[k+'_SOLVER_ENTRY']=rec['cases'][i]['entered_count'];v[k+'_TRUTH_VALID']='PASS' if results[k] and results[k]['truth_valid'] else ('HOLD' if rec['cases'][i]['entered_count'] else 'NOT_RUN');v[k+'_LABELS_VALID']='PASS' if results[k] and results[k]['labels_valid'] else ('HOLD' if rec['cases'][i]['entered_count'] else 'NOT_RUN')
v.update(DIAG2_USED_ENTRIES=rec['entered_total'],DIAG2_REMAINING_ENTRIES=2-rec['entered_total'],NUMERICAL_CONVERGENCE_VERDICT=numerical,HISTORICAL_156G_COMPATIBILITY='609D representation retained; unconditional unversioned merge NOT_CERTIFIED',FUTURE_ACTIVE_LEARNING_FDTD_CONTRACT='Not frozen for production: retain native materials/609D/H1/H2; close remaining time/4vs5nm uncertainty before authorizing AL;6ps diagnostic is not global certification',DOE56='HOLD',AL16='NOT_AUTHORIZED',REPLAY=0,NEW_ML_FITS=0,SEALED_RESPONSE_ACCESS=0,NEW_FDTD=rec['entered_total'])
put(D/'FINAL_VERDICT.json',v)
put(D/'SHA_INVENTORY.json',dict(rule='Existing raw SHA256 identities and frozen model-target canonicalizer, no new hash rule',installed_runner_sha256=hashlib.sha256((P/'minimal_batch_runner_v3.1_final.py').read_bytes()).hexdigest(),physics_contract_sha256=ledger['cases'][0]['physical_contract_sha256'],cases=[dict(case_id=b['case_id'],source_fsp_sha256=b['source_fsp_sha256'],original_case_request_sha256=b['case_request_sha256'],external_execution_id=b['external_execution_id'],native=results[k]['native'] if results[k] else None,labels=results[k]['labels'] if results[k] else None,truth_h5=results[k]['truth_h5'] if results[k] else None) for b,k in zip(ledger['cases'],['A1','A2'])]))
git=lambda *a:subprocess.check_output(['git','-C',str(R),*a],text=True).strip();baseline=read(D/'GIT_BASELINE.json');assert git('diff','--cached','--name-only')==baseline['staged']
put(D/'FINAL_GIT_AUDIT.json',dict(branch=git('branch','--show-current'),head=git('rev-parse','HEAD'),ahead_behind=git('rev-list','--left-right','--count','HEAD...@{u}'),dirty_count=len(git('status','--short').splitlines()),staged_preserved=True,committed=False,pushed=False))
rows=['| 案例 | Entry | Truth | Labels | 状态相对L2最大 | Routing最大差 | P_scale最大相对差 | 相位RMSE最大 |','|---|---:|---|---|---:|---:|---:|---:|']
for i,k in enumerate(['A1','A2']):
 c=comparisons.get(k);m=c['metrics'] if c else None;rows.append('| '+k+' | '+str(v[k+'_SOLVER_ENTRY'])+' | '+v[k+'_TRUTH_VALID']+' | '+v[k+'_LABELS_VALID']+' | '+(' | '.join(f'{m[x]:.6g}' for x in ['state_relative_L2_max','routing_max_abs','P_scale_max_relative','phase_energy_weighted_RMSE_max_rad']) if m else '未运行 | 未运行 | 未运行 | 未运行')+' |')
details=[]
for k,r in results.items():
 if r:details.append(k+': 科学验收 '+r['scientific_acceptance']+'；停止 '+r['stop_reason']+'；native FSP `'+r['native']['native_fsp']['path']+'`；native H5 `'+r['native']['native_h5']['path']+'`；truth H5 `'+r['truth_h5']['path']+'`。')
 elif errors.get(k):details.append(k+' 科学后处理 HOLD：'+errors[k]['error'])
 elif k=='A2':details.append('A2 未启动：A1尚未科学验收PASS，严格执行条件授权；原Job保留，不换ID、不恢复或新增预算。')
report=f'''# {T}

## 状态
{'PASS：两案完成原冻结条件下的定向时间敏感度验收；不是全六维空间数值收敛认证。' if ok else 'PARTIAL / HOLD：仅已记录的真实Entry被消耗；A1未获科学PASS时A2不执行。'}

## 执行和科学验收
{chr(10).join(rows)}

原DIAG2预算使用 {rec['entered_total']}/2，剩余 {2-rec['entered_total']}。原A1/A2/attempt_001/External Execution ID全部保留，正式submit Job未重建。Runner源码5778eefb未改、未部署，严格调用已登记单Job批次run；Entry在backend前原子提交，独立SQL与单一科学账本对账，任何失败均不退款、不自动重跑。

{chr(10).join(details)}

A1_CLI_STDOUT/STDERR、各Job runner.log/input_p0.log、OWNED_PROCESS_IDENTITIES、LIVE_RECONCILIATION及RUNNER_FINAL_READONLY_AUDIT记录真实GPU与PID+create_time、停止及输出证据。只有自身API只读会话被关闭，其他CPU FDTD/EDT未停止或修改。

## 原冻结标准
沿用5nm/6ps、auto-shutoff1e-6、21lambda、参考面1722nm、TE/TM、Floquet分解、C_hat、P_scale、609D/H1/H2。使用冻结postprocess、H1.state_data/pscale_eh、H2及coupling_609d_v1数值检查，不改原importer源文件；V31原始科学身份和SHA由权威绑定账本核验。新旧容器合同的六字段投影复用既有resolver函数，不生成替代物理合同。Native输出只读freshLOAD、E/H/H5完整有限、SHA、功率映射及参考面检查见各science目录；必要时仅建立不改字节的Native basename读视图。

时间对照沿用V3_NUMERICAL_VALIDATION_PLAN：相对状态L2<=0.02、Routing和绝对阶功率差<=0.005、P_scale相对差<=0.01、有效模态能量加权相位RMSE<=0.05rad，模态功率mask1e-4，无oracle相位对齐。完整21波长表、609D差异及原始复数场幅度对照见TIME_CONVERGENCE_COMPARISON.json和WAVELENGTH_3PS_6PS_COMPARISON.csv。能量闭合沿用原R+T+A方法，A=1-R-T，不能将其代数闭合当作独立体吸收证明。

停止状态1=完整最大物理时间、2=自动停止、3=发散，依据[Ansys FDTD状态定义](https://optics.ansys.com/hc/en-us/articles/360034382534-FDTD-solver-Simulation-Object)。完整6ps停止不等于达到1e-6；逐案原生日志与status另列，不以Runner COMPLETED代替labels-valid。

## A–E 裁决
A. 历史3ps是否足以支持ML标签：不能按冻结总功率1%要求认证为足够。A1的P_scale最大相对变化2.434%，其余四项通过；原合法156G保留，但这一个反例已阻止对全部3ps标签作无条件时间精度背书。
B. 6ps改善：时域残余下降，但A1以status1到最大6ps停止，没有自动停止完成证明；P_scale变化2.434%仍超过冻结界限，因此不能宣称6ps自身已严格收敛。A2未运行，不能给出第二anchor结果。
C. 4/5nm仍须独立研究：是。本次仅改变最大物理时长，不能解决已知网格敏感度，未新增4nm求解。
D. 后续统一FDTD合同：保留Native材料、几何、源、monitor、参考面、609D和1e-6不变；6ps为本次诊断合同，尚不能替代全域网格/时间认证。新AL生产合同在剩余数值问题关闭前不冻结、不启动。
E. 历史156G与新数据：609D表示兼容；不支持无版本标签直接合并。保留3ps/6ps及诊断角色、数值质量标识，DIAG2不自动转为训练开发集；本次零新模型fits。

Truth/Labels PASS仅代表原生结果及冻结提取有效，不等于时间精度门禁PASS。A1科学推进为HOLD_NUMERICAL_REVIEW，因此未调用A2。标量H5压缩兼容错误已离线修复，部分truth.h5保留，truth_complete.h5与既有E/H和标签逐项一致，见OFFLINE_H5_EXPORT_REPAIR及POST_EXPORT_TARGETED_VALIDATION；没有重提取原生场或重跑Solver。补充MODAL_AMPLITUDE_PHASE_3PS_6PS、ALL_ORDER_ROUTING_3PS_6PS、LABEL_609D_COMPONENT_COMPARISON.csv及RAW_EH_PHASE_3PS_6PS.json保存完整对照。

## 边界和Git
DOE56=HOLD；AL16=NOT_AUTHORIZED；sealed response access=0；replay=0；new ML fits=0。历史FSP/H5和既有11+8证据保持，未重训或重整156G。
branch={git('branch','--show-current')}；HEAD={git('rev-parse','HEAD')}；ahead/behind={git('rev-list','--left-right','--count','HEAD...@{u}')}；dirty，原4项staged保留；未提交/推送。
'''
(D/'FINAL_REPORT.md').write_text(report,encoding='utf-8')
(D/'CONTINUATION.md').write_text(json.dumps(v,ensure_ascii=False)+'\nRead FINAL_REPORT.md, per-case SCIENCE_RECEIPT/TIME_CONVERGENCE_COMPARISON and final canonical ledger reconciliation. Never invoke a consumed case again, never reset jobs/entries or re-ID. No deferred automatic run; task closed with conditional execution disabled in science ledger. DOE56HOLD,AL16NOT_AUTHORIZED,sealed0,ML0. Preserve dirty/staged.\n',encoding='utf-8')
ag=R/'AGENTS.md';ag.write_text(ag.read_text(encoding='utf-8')+'\n'+T+'：本轮用户原2预算真实受控授权，最终已用'+str(rec['entered_total'])+'/2。最新CONTINUATION见reports/coupling/'+T+'/；已入场attempt永久禁止replay，A2仅在A1科学PASS后执行，参见最终账本。DOE56 HOLD、AL16未授权、sealed禁止。\n',encoding='utf-8')
allow=[str(p.relative_to(R)) for p in D.rglob('*') if p.is_file() and p.suffix in ['.md','.json','.csv','.py','.txt'] and p.stat().st_size<1000000 and 'native_read_view' not in str(p) and 'bundle_inventory_view' not in str(p)];allow += ['scripts/coupling_ml/run_diag2_v31_real_acceptance_v1.py'];(D/'TASK_ALLOWLIST.txt').write_text('\n'.join(sorted(allow))+'\n',encoding='utf-8');print(json.dumps(v,indent=2));print('COMPARE', {k:c['metrics'] for k,c in comparisons.items()})

summary=read(D/'A1_FINAL_NUMERICAL_SUMMARY.json')
assert not (D/'A2_CLI_INVOCATION_ONCE.json').exists() and rec['cases'][1]['entered_count']==0
residual_old=summary['old_last_log_progress']['auto_shutoff'];residual_new=summary['new_last_log_progress']['auto_shutoff']
extra=f"""
## A1 重点数值及关闭记录

| 波长 | P_scale 3ps | P_scale 6ps | 相对变化 | eta(+1) 3ps→6ps |
|---|---:|---:|---:|---|
| 446nm | 0.2800307875 | 0.2732148314 | 2.4340% | 0.4085475635→0.4091817621 |
| 450nm | 0.6982029820 | 0.6976702123 | 0.07631% | 0.3656054566→0.3656036759 |

最后日志采样：3ps的99.0003%处AutoShutoff={residual_old:.7g}；6ps的99%处={residual_new:.7g}，约下降{residual_old/residual_new:.3f}倍。它们是日志采样值，不冒充精确终点残余；原生status1证明本次最大6ps停止，未获auto-stop完成证明。状态相对L2最大1.4194%、Routing最大绝对差0.00227734、绝对阶功率最大差0.00261137、有效模态相位RMSE最大0.0137662rad均通过冻结门槛，唯P_scale的2.4340%超过1%。

A2原Job2保持PENDING，无CLI调用、无Entry，剩余原预算1条，未重分配给A1。A1一次真实求解耗时约18分41秒（Entry至CLI返回），本次原预算不会退款。原permittivity潜在发散警告保留在日志中；正常status1及有限E/H不构成实际发散证据，未调整dt/PML。

独立科学账本entered/truth-valid/labels-valid=1/1/1；时间数值推进仍HOLD，详见SCIENCE_LEDGER_SUBSET_RECONCILIATION.json。H5导出修复后的7项定向一致性检查通过，未重跑模型或原生场提取。
"""
report_path=D/'FINAL_REPORT.md';report_path.write_text(report_path.read_text(encoding='utf-8')+extra,encoding='utf-8')
put(D/'CURRENT_AUTHORITY.json',dict(task=T,status='DIAG2_A1_TIME_SENSITIVITY_HOLD_A2_NOT_ENTERED',canonical_science_ledger=str(B/'DIAG2_SCIENCE_LEDGER.json'),used_entries=1,remaining_original_entries=1,A1_scientific_acceptance='HOLD_NUMERICAL_REVIEW',A2='HOLD_NOT_RUN',current_task_execution_authorization_closed=True,next_scientific_priority='Review A1 time sensitivity and still unresolved6ps temporal tail before any A2 continuation; do not replay A1 or expand budget automatically',DOE56='HOLD',AL16='NOT_AUTHORIZED'))
allowpath=D/'TASK_ALLOWLIST.txt';allowpath.write_text(allowpath.read_text(encoding='utf-8')+str((D/'CURRENT_AUTHORITY.json').relative_to(R))+'\n'+str((D/'FINAL_REPORT_BUILDER.py').relative_to(R))+'\n',encoding='utf-8')
print('COMPLETE_ONE_REAL_ENTRY_A2_NOT_RUN',summary['worst_P_scale_wavelength_nm'])
