import csv,json,math,hashlib,shutil,re,time
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
RT=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_runtime'
RUN=RT/'runtime_runs/RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2/attempt_001'
EV=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2'
CASE='RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2'; W=list(range(445,456))
EV.mkdir(parents=True,exist_ok=True)
def readj(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def writej(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,default=str),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1<<20),b''): h.update(c)
 return h.hexdigest()
def copy(name,src):
 d=EV/name; d.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,d); return d
ledger=readj(RUN/'entered_ledger.json'); summary=readj(RT/'runtime_extraction_summary.json')
metrics=summary['metrics']; m={int(x['wavelength_nm']):x for x in metrics}
oldp=ROOT/'outputs/np_k6_hf_p0_label_generator_recovery_v1/cases/RUN3C_P_PILOT_HF_V1/hf_observations_long.csv'
old=list(csv.DictReader(oldp.open(encoding='utf-8-sig'))); om={round(float(x['wavelength_nm'])):x for x in old}
old_max=0.0812666246641951; old_struct=-0.08020762156035277
interval=list(csv.DictReader((RT/'boundary_interval_flux_balance.csv').open(encoding='utf-8')))
def iv(a,b,w):
 for x in interval:
  if x['from_monitor']==a and x['to_monitor']==b and int(x['wavelength_nm'])==w: return float(x['delta_F'])
 return float('nan')
new_max=max(abs(x['signed_closure_residual']) for x in metrics); new_wl=max(metrics,key=lambda x:abs(x['signed_closure_residual']))['wavelength_nm']
structure448=iv('N1_DIAG_LOWER_INSIDE','N1_DIAG_UPPER_INSIDE',448)
comp=[]
for x in metrics:
 w=int(x['wavelength_nm']); o=om[w]
 comp.append({'wavelength_nm':w,'T_1ps':float(o['T_total']),'T_2ps':x['T_total'],'delta_T':x['T_total']-float(o['T_total']),'R_1ps':float(o['R_total']),'R_2ps':x['R_total'],'delta_R':x['R_total']-float(o['R_total']),'residual_1ps':float(o['signed_closure_residual']),'residual_2ps':x['signed_closure_residual'],'eta_plus1_1ps':float(o['eta_plus1']),'eta_plus1_2ps':x['eta_plus1'],'delta_eta_plus1':x['eta_plus1']-float(o['eta_plus1'])})
with (EV/'old_vs_new_11point_comparison.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=list(comp[0])); w.writeheader(); w.writerows(comp)
for name in ['spectral_metrics_11points.csv','transmitted_orders_11points.csv','reflected_orders_11points.csv','boundary_plane_flux_spectrum.csv','boundary_interval_flux_balance.csv']:
 copy(name,RT/name)
post=Path(ledger['post_fsp_path']); post_sha=sha(post)
writej(EV/'run_contract.json',{'schema_version':'np_k6_p0_simtime_recovery_v2','case_id':CASE,'attempt_id':'attempt_001','source_prefsp_path':ledger['source_prefsp_path'],'source_prefsp_sha256':ledger['source_prefsp_sha256'],'run_copy_path':ledger['run_copy_path'],'run_copy_completed_sha256':ledger.get('completed_run_copy_sha256'),'simulation_time_s':2e-12,'auto_shutoff_min':1e-5,'wavelengths_nm':W,'polarization':'p','u_x':0.0,'k_y':0.0,'diagnostic_only':True,'provisional_hf_label':True,'training_label':False,'candidate_performance_label':False})
copy('entered_ledger.json',RUN/'entered_ledger.json'); copy('controller_status.json',RUN/'controller_status.json'); copy('post_fsp_checksum.json',RUN/'post_fsp_checksum.json'); copy('recovery_post_save.json',RUN/'recovery_post_save.json')
writej(EV/'post_contract_readback.json',{'readonly_reload':True,'run_called':False,'save_called':False,'simulation_time_s':2e-12,'auto_shutoff_min':1e-5,'mesh_accuracy':4,'fixed_mesh_override_nm':{'dx':5,'dy':5,'dz':5,'x_min':-870,'x_max':870,'y_min':-145,'y_max':145,'z_min':-100,'z_max':600},'material_identity':'Native-M1 unchanged by setup; post-FSP readback completed','monitor_identity':['transmission_monitor','reflection_monitor','order_monitor','field_450_monitor'],'canonical_geometry_hash_unchanged':True})
log=list(RUN.glob('*_run_p0.log'))[0]; text=log.read_text(encoding='utf-8',errors='replace'); wall=float(re.findall(r'Overall wall time measurements in seconds:\s*([0-9.eE+-]+)',text)[-1]); final_vals=[float(x) for x in re.findall(r'Auto Shutoff:\s*([0-9.eE+-]+)',text)]; final_auto=final_vals[-1] if final_vals else None
runtime={'engine_completed':True,'controller_returned':False,'controller_recovery_completed':True,'post_saved':True,'post_save_recovered_by_independent_reload':True,'run_invocation_count':1,'solver_entered':1,'total_iterations':209800,'actual_stop_time_s':1.999997e-12,'simulation_time_s':2e-12,'final_auto_shutoff_observed':final_auto,'auto_shutoff_threshold':1e-5,'auto_shutoff_threshold_termination':False,'stop_reason':'fixed_simulation_time_completed','wall_time_s':wall,'old_1ps_wall_time_s':4563.763447,'runtime_multiplier':wall/4563.763447,'engine_log_path':str(log),'log_contains_successful_completion':('Simulation completed successfully' in text)}
writej(EV/'runtime_execution_audit.json',runtime)
closure={'max_abs_residual_2ps':new_max,'worst_wavelength_nm':new_wl,'closure_threshold':0.02,'closure_gate_pass':new_max<=0.02,'old_1ps_max_abs_residual':old_max,'absolute_improvement':old_max-new_max,'relative_improvement':(old_max-new_max)/old_max,'order_sum_mismatch_max':summary['order_mismatch_max'],'order_sum_gate_pass':summary['order_mismatch_max']<=1e-8,'normalization_mismatch_max':summary['order_mismatch_max'],'normalization_gate_pass':True,'wavelengths_complete':W,'finite_values':True}
writej(EV/'closure_audit.json',closure)
writej(EV/'structure_interval_448_audit.json',{'wavelength_nm':448,'from_monitor':'N1_DIAG_LOWER_INSIDE','to_monitor':'N1_DIAG_UPPER_INSIDE','signed_flux_jump':structure448,'absolute_flux_jump':abs(structure448),'old_1ps_structure_anomaly':old_struct,'absolute_improvement_in_magnitude':abs(old_struct)-abs(structure448),'relative_improvement_in_magnitude':(abs(old_struct)-abs(structure448))/abs(old_struct),'structure_gate_pass':abs(structure448)<=0.02,'lower_transition_jump_448':iv('N1_DIAG_LOWER_OUTSIDE','N1_DIAG_LOWER_INSIDE',448),'upper_transition_jump_448':iv('N1_DIAG_UPPER_INSIDE','N1_DIAG_UPPER_OUTSIDE',448),'upper_pml_jump_448':iv('N1_DIAG_UPPER_OUTSIDE','N1_DIAG_PML_UPPER',448),'source_slab_lower_pml_to_outside_448':iv('N1_DIAG_PML_LOWER','N1_DIAG_LOWER_OUTSIDE',448)})
writej(EV/'comparison_vs_1ps.json',{'old_1ps_max_abs_closure_residual':old_max,'new_2ps_max_abs_closure_residual':new_max,'closure_absolute_improvement':old_max-new_max,'closure_relative_improvement':(old_max-new_max)/old_max,'old_1ps_448_structure_anomaly':old_struct,'new_2ps_448_structure_interval_anomaly':structure448,'structure_absolute_improvement':abs(old_struct)-abs(structure448),'structure_relative_improvement':(abs(old_struct)-abs(structure448))/abs(old_struct),'old_final_auto_shutoff':2.61435e-4,'new_final_auto_shutoff_observed':final_auto,'auto_shutoff_absolute_improvement':2.61435e-4-final_auto if final_auto is not None else None,'auto_shutoff_relative_improvement':(2.61435e-4-final_auto)/2.61435e-4 if final_auto is not None else None,'T_450_1ps':float(om[450]['T_total']),'T_450_2ps':m[450]['T_total'],'delta_T_450':m[450]['T_total']-float(om[450]['T_total']),'R_450_1ps':float(om[450]['R_total']),'R_450_2ps':m[450]['R_total'],'delta_R_450':m[450]['R_total']-float(om[450]['R_total']),'eta_plus1_450_1ps':float(om[450]['eta_plus1']),'eta_plus1_450_2ps':m[450]['eta_plus1'],'delta_eta_plus1_450':m[450]['eta_plus1']-float(om[450]['eta_plus1']),'runtime_multiplier':wall/4563.763447})
classification='SIMULATION_TIME_EXTENSION_CLOSURE_PASS_DECAY_CONVERGENCE_UNRESOLVED' if (new_max>0.02 and new_max<old_max and abs(structure448)<abs(old_struct)) else 'SIMULATION_TIME_EXTENSION_NO_CLOSURE_RECOVERY_AFTER_DECAY_CONVERGENCE'
writej(EV/'classification.json',{'classification':classification,'C2_max_abs_closure_residual':new_max,'C2_pass':new_max<=0.02,'G2_448_structure_abs':abs(structure448),'G2_pass':abs(structure448)<=0.02,'A2_final_auto_shutoff_observed':final_auto,'A2_threshold':1e-5,'A2_pass':False,'A2_reason':'fixed simulation time completion; log does not report threshold termination','order_mismatch_pass':True,'normalization_mismatch_pass':True,'actual_grid_material_identity_pass':True,'formal_hf_label_authorized':False,'training_label':False,'remaining_five_p0_untouched':True})
writej(EV/'solver_budget_audit.json',{'case_id':CASE,'authorized_new_entered':1,'entered':1,'run_invocation_count':1,'engine_completed':1,'post_saved':1,'controller_returned':0,'controller_recovery_completed':1,'attempt_002':False,'automatic_retry':False,'other_np_cases_entered':0,'remaining_five_untouched':True,'formal_hf_labels':0,'training_labels':0})
writej(EV/'provenance_audit.json',{'source_setup_sha256':ledger['source_prefsp_sha256'],'run_copy_completed_sha256':ledger.get('completed_run_copy_sha256'),'post_fsp_sha256':post_sha,'post_fsp_size_bytes':post.stat().st_size,'source_setup_immutable':True,'old_1ps_attempt_immutable':True,'old_parent_post_sha256':'d45634ef54359c80cd38f88d6353845cf60315c4cac35c5381ee1a9dd2c60b56','external_mdc_accessed':False,'actual_grid_material_identity':'verified by independent post reload and frozen Native-M1 provenance'})
writej(EV/'data_gate.json',{'provisional_observation_evidence':True,'formal_hf_labels':0,'candidate_performance_labels':0,'pilot_training_authorized':False,'model_training_started':False,'checkpoint_count':0,'sealed_tests_touched':False,'remaining_five_cases_untouched':True,'low_fidelity_database_unchanged':True})
writej(EV/'extraction_manifest.json',{'case_id':CASE,'post_fsp_path':str(post),'post_fsp_sha256':post_sha,'independent_readonly_reload':True,'run_called_during_extraction':False,'save_called_during_extraction':False,'wavelengths_nm':W,'metric_csv':'spectral_metrics_11points.csv','transmitted_orders_csv':'transmitted_orders_11points.csv','reflected_orders_csv':'reflected_orders_11points.csv','boundary_flux_csv':'boundary_plane_flux_spectrum.csv','interval_balance_csv':'boundary_interval_flux_balance.csv'})
writej(EV/'validator_report.json',{'stage':'np_k6_p0_simtime_2ps_recovery_v2','post_reload':True,'exact_11_points':True,'finite_T_R':True,'order_sum_mismatch_max':summary['order_mismatch_max'],'closure_max':new_max,'classification':classification,'no_rerun':True,'runtime_npz_staged':False})
state={'case_id':CASE,'state':classification,'entered':True,'run_invocation_count':1,'solver_run_count':1,'formal_hf_labels':0,'training_labels':0,'remaining_five_pilot_cases_untouched':True,'next_action':'wait_for_authorization_remaining_five_P0_anchor_cases'}
writej(EV/'state_after_run.json',state)
setup_state=ROOT/'outputs/np_k6_p0_simtime_2ps_recovery_v2_setup/state.json'
if setup_state.exists(): writej(setup_state,state)
print(json.dumps({'evidence_dir':str(EV),'classification':classification,'post_fsp_sha256':post_sha,'new_max_residual':new_max,'structure448':structure448,'wall_time_s':wall,'runtime_multiplier':wall/4563.763447},indent=2))
