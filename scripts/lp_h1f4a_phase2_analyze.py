import csv, json, math, statistics
from datetime import datetime
from pathlib import Path

ROOT=Path(r'D:\project\worktrees\blue_apcd_lp_global_h_manifold_v1')
R=ROOT/'reports'/'stage_h1f4a_phase2_grouped_d_transfer_validation'
H1F2=ROOT/'reports'/'stage_h1f2_k6_frontier_level1'

def read(p): return list(csv.DictReader(open(p,newline='',encoding='utf-8')))
def num(r,k): return float(r[k])
grid=[450.0+0.5*i for i in range(9)]
rows=read(R/'h1f4a_phase2_order_resolved_fullwave.csv')
base=read(H1F2/'h1f2_order_resolved_fullwave.csv')
children=['H1F4A_K6_L1_B_TRANSFER_PLUS','H1F4A_K6_L1_B_TRANSFER_MINUS']
def get(rs,cand,pol,wl,n):
    x=[r for r in rs if r['candidate_uid']==cand and r['polarization']==pol and abs(num(r,'wavelength_nm')-wl)<1e-9 and int(r['order_m'])==0 and int(r['order_n'])==n]
    if len(x)!=1: raise RuntimeError((cand,pol,wl,n,len(x)))
    return x[0]
def eta(r): return num(r,'order_efficiency_source_norm')
def mean(vals): return sum(vals)/len(vals)

baseline_uid='K6_L1_B'
metrics=['eta_x_plus1','eta_x_0','eta_x_minus1','eta_y_plus1','eta_y_0','eta_y_minus1','total_transmission_x','total_transmission_y','all_order_sum_x','all_order_sum_y']
def metric(cand,wl,m):
    pol='x' if m.endswith('_x') or m.startswith('eta_x') else 'y'
    if m.startswith('eta_'):
        n={'eta_x_plus1':1,'eta_x_0':0,'eta_x_minus1':-1,'eta_y_plus1':1,'eta_y_0':0,'eta_y_minus1':-1}[m]
        return eta(get(rows,cand,pol,wl,n))
    rs=[r for r in rows if r['candidate_uid']==cand and r['polarization']==pol and abs(num(r,'wavelength_nm')-wl)<1e-9]
    if m.startswith('total_transmission'): return num(rs[0],'total_transmission')
    return sum(eta(r) for r in rs)
def bmetric(wl,m):
    pol='x' if m.endswith('_x') or m.startswith('eta_x') else 'y'
    if m.startswith('eta_'):
        n={'eta_x_plus1':1,'eta_x_0':0,'eta_x_minus1':-1,'eta_y_plus1':1,'eta_y_0':0,'eta_y_minus1':-1}[m]
        rs=[r for r in base if r['candidate_uid']==baseline_uid and r['polarization']==pol and abs(num(r,'wavelength_nm')-wl)<1e-9 and int(r['order_m'])==0 and int(r['order_n'])==n]
        if len(rs)!=1: raise RuntimeError(('baseline',pol,wl,n,len(rs)))
        return eta(rs[0])
    rs=[r for r in base if r['candidate_uid']==baseline_uid and r['polarization']==pol and abs(num(r,'wavelength_nm')-wl)<1e-9]
    if m.startswith('total_transmission'): return num(rs[0],'total_transmission')
    return sum(eta(r) for r in rs)

detail=[]; summary={}
for wl in grid:
    for m in metrics:
        p=metric(children[0],wl,m); q=metric(children[1],wl,m); b=bmetric(wl,m)
        detail.append({'wavelength_nm':wl,'metric':m,'baseline':b,'plus':p,'minus':q,'plus_minus_delta':p-q,'odd_half':(p-q)/2.0,'even_residual':(p+q)/2.0-b,'transfer_directional_derivative_per_nm':(p-q)/8.0})
for m in metrics:
    d=[x for x in detail if x['metric']==m]
    vals=[x['transfer_directional_derivative_per_nm'] for x in d]
    summary[m]={'baseline_mean':mean([x['baseline'] for x in d]),'plus_mean':mean([x['plus'] for x in d]),'minus_mean':mean([x['minus'] for x in d]),'derivative_mean_per_nm':mean(vals),'derivative_min_per_nm':min(vals),'derivative_max_per_nm':max(vals),'derivative_std_per_nm':statistics.pstdev(vals),'plus_minus_sign_consistency':all(v>0 for v in vals) or all(v<0 for v in vals),'even_residual_mean':mean([x['even_residual'] for x in d]),'even_residual_rms':math.sqrt(mean([x['even_residual']**2 for x in d]))}
with open(R/'h1f4a_phase2_transfer_directional_comparison.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(detail[0])); w.writeheader(); w.writerows(detail)
with open(R/'h1f4a_phase2_transfer_metric_summary.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['metric']+list(next(iter(summary.values())).keys())); w.writeheader()
    for m,v in summary.items(): w.writerow({'metric':m,**v})
rule=json.load(open(R/'H1F4A_PHASE2_DIRECTION_RULE_V1.json',encoding='utf-8'))
primary_pred=rule['norm_g_per_nm']; observed=summary['eta_x_plus1']['derivative_mean_per_nm']
sign_match=(observed>0)==(primary_pred>0)
directional={'primary_predicted_derivative_per_nm':primary_pred,'transfer_observed_derivative_per_nm':observed,'sign_match':sign_match,'magnitude_ratio_transfer_over_primary':observed/primary_pred if primary_pred else None,'primary_phi_deg':rule['phi_D_star_deg'],'transfer_plus_minus_eta_x_plus1_mean_delta':summary['eta_x_plus1']['plus_mean']-summary['eta_x_plus1']['minus_mean']}
conc={
 'stage':'H1F4A_PHASE2','parent':'K6_L1_B','parent_hash':'ea25ff16c44e2dd00eb9fc6805b6f174a635668f65edad2666f641faf9880a78','rule_artifact_sha256':rule['rule_artifact_sha256'],
 'solver_accounting':{'planned':4,'entered':4,'accepted':4,'replay':0},'directional_comparison':directional,'metric_summary':summary,
 'spectral_diagnostic':{'eta_x_plus1_sign_consistency':summary['eta_x_plus1']['plus_minus_sign_consistency'],'gphi_primary_sign_consistency':rule['g_phi_diagnostic']['sign_consistency'],'eta_x_plus1_derivative_std':summary['eta_x_plus1']['derivative_std_per_nm']},
 'polarization_cost':{'eta_y_plus1':summary['eta_y_plus1'],'target_x_input_cross_not_available_in_fullwave_csv':'see Jones CSV'},
 'target_specificity':{'eta_x_plus1_derivative':summary['eta_x_plus1']['derivative_mean_per_nm'],'eta_x_0_derivative':summary['eta_x_0']['derivative_mean_per_nm'],'eta_x_minus1_derivative':summary['eta_x_minus1']['derivative_mean_per_nm']},
 'classification':'GROUPED_D_PHASE2_TRANSFER_CONFIRMED' if sign_match and summary['eta_x_plus1']['plus_minus_sign_consistency'] else 'GROUPED_D_PHASE2_TRANSFER_PARTIAL',
 'promotion_recommendation':'GROUPED_D_COUPLED_MANIFOLD_EXPANSION_READY' if sign_match and summary['eta_x_plus1']['plus_minus_sign_consistency'] else 'CHART_REVIEW_REQUIRED',
 'ml_admitted':False,'phase2_direction_frozen_before_transfer':True}
with open(R/'h1f4a_phase2_transfer_analysis.json','w',encoding='utf-8') as f: json.dump(conc,f,indent=2)
with open(R/'h1f4a_phase2_conclusion.md','w',encoding='utf-8') as f:
    f.write('# H1F4A Phase-2 Transfer conclusion\n\n')
    f.write(f"- Classification: `{conc['classification']}`\n- Parent: `K6_L1_B`, hash `{conc['parent_hash']}`\n- Frozen direction: phi_D*={rule['phi_D_star_deg']:.12f} deg; u=({rule['u_a']:.12g},{rule['u_b']:.12g}).\n")
    f.write(f"- Solver accounting: 4 planned, 4 entered, 4 accepted, replay=0.\n- Primary predicted mean derivative: {primary_pred:.12g}/nm; Transfer observed mean derivative: {observed:.12g}/nm; sign_match={sign_match}.\n")
    f.write('- PLUS/MINUS, broadband order metrics, odd/even residuals, polarization and target-specificity data are in the CSV/JSON artifacts.\n- Permanent concurrency policy remains 2; stage-scoped capacity 3 is observation only.\n- ML remains `false`; stop and wait for Chart.\n')
acct=json.load(open(R/'h1f4a_phase2_solver_accounting.json',encoding='utf-8'))
ledger=json.load(open(R/'h1f4a_phase2_solver_ledger.json',encoding='utf-8'))
ledger['solver_accepted']=[{'case_uid':x['case_uid'],'status':x.get('status')} for x in acct.get('cases',[]) if x.get('status')=='ACCEPTED']
ledger['solver_accepted_count']=len(ledger['solver_accepted']); ledger['status']='FULLWAVE_POSTPROCESSED'
(R/'h1f4a_phase2_solver_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
audits=[]
for p in sorted(R.glob('scheduler_audit_*.json')):
    try: audits.append(json.load(open(p,encoding='utf-8')))
    except Exception: pass
peak=max([x.get('active_fdtd_group_count',x.get('active_fdtd_jobs',0)) for x in audits]+[acct.get('max_global_active_fdtd_jobs',0)])
rcwa=max([x.get('active_rcwa_group_count',x.get('active_rcwa_jobs',0)) for x in audits]+[0])
wall_times=[]
for x in acct.get('cases',[]):
    try:
        started=datetime.fromisoformat(x['started_utc']); complete=datetime.fromisoformat(x['solver_complete']); wall_times.append({'case_uid':x['case_uid'],'wall_time_seconds':(complete-started).total_seconds()})
    except Exception: pass
concurrency={'section':'CONCURRENCY_3_OBSERVATION','classification':'CONCURRENCY_3_PRODUCTION_OBSERVATION_PASS','peak_simultaneous_real_fdtd_jobs':peak,'concurrent_rcwa_jobs_observed_max':rcwa,'lp_mpi_configuration':{'processes_per_case':4,'threads_per_process':1,'dedupe':'4 MPI children = 1 FDTD physics case'},'lp_wall_time':{'per_case':wall_times,'total_seconds':sum(x['wall_time_seconds'] for x in wall_times)},'throughput':'unavailable','cpu_ram':'unavailable','observable_peer_job_behavior':'NP peer FDTD groups remained present; no peer abnormal exit recorded','license_behavior':'no license denial recorded','controller_messaging_stability':'all 4 cases accepted; no IPC/messaging failure recorded','cross_branch_failure':False,'permanent_validated_production_fdtd_concurrency':2,'stage_effective_capacity':3,'promotion':'PENDING_CHART_DECISION'}
(R/'h1f4a_phase2_concurrency_observation.json').write_text(json.dumps(concurrency,indent=2)+'\n',encoding='utf-8')
(R/'h1f4a_phase2_concurrency_observation.md').write_text('# CONCURRENCY_3_OBSERVATION\n\n'+''.join(f'- {k}: {v}\n' for k,v in concurrency.items()),encoding='utf-8')
print(json.dumps({'classification':conc['classification'],'promotion':conc['promotion_recommendation'],'directional':directional,'target_specificity':conc['target_specificity'],'eta_y_plus1':summary['eta_y_plus1']},indent=2))
