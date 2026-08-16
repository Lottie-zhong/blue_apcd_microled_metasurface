import csv, gzip, hashlib, json, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
OUT=ROOT/'outputs/np_k6_m8_20g_forward_retraining_v1'
HF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'
LF=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_lf_baseline_440rows.csv'
M7A=ROOT/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1'
M7DES=ROOT/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1'
EXT=ROOT/'outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json'
ORDERS=[-3,-2,-1,0,1,2,3]; WLS=list(range(445,456)); SEEDS=[17,29,43]
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def jread(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def jwrite(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
if OUT.exists() and (OUT/'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json').exists(): raise RuntimeError('refusing_existing_m8_prereg')
with HF.open(encoding='utf-8-sig',newline='') as f: hrows=list(csv.DictReader(f))
with LF.open(encoding='utf-8-sig',newline='') as f: lrows=list(csv.DictReader(f))
if len(hrows)!=440 or len(lrows)!=440: raise RuntimeError('row_count')
hk=[(r['case_id'],int(float(r['wavelength_nm']))) for r in hrows]; lk=[(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in lrows]
if len(set(hk))!=440 or len(set(lk))!=440: raise RuntimeError('duplicates')
geos=sorted({r['geometry_id'] for r in hrows}); pairs=sorted({(r['geometry_id'],r['polarization'].lower()) for r in hrows})
if len(geos)!=20 or len(pairs)!=40: raise RuntimeError('membership')
for g in geos:
 vals=[(r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in hrows if r['geometry_id']==g]
 if set(vals)!={(p,w) for p in ('p','s') for w in WLS}: raise RuntimeError('coverage:'+g)
 if any(r.get('quality_gate_pass')!='true' or r.get('diagnostic_only')!='false' or not (r.get('training_label')=='true' or r.get('m5_training_label')=='true') for r in hrows if r['geometry_id']==g): raise RuntimeError('flags:'+g)
 if 'D110_D125_D130_D135_D140_D175' in g: raise RuntimeError('quarantine')
if {r['geometry_id'] for r in lrows}!=set(geos): raise RuntimeError('lf_geometry_coverage')
if set(lk)!=set((r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in hrows): raise RuntimeError('lf_hf_key_mismatch')
if jread(EXT).get('sealed_hf_target_read',0)!=0: raise RuntimeError('sealed_registry')
prereg={
 'preregistration_id':'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1',
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'solver_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'new_development_hf':0,
 'dataset':{'path':str(HF.relative_to(ROOT)),'sha256':sha(HF),'lf_path':str(LF.relative_to(ROOT)),'lf_sha256':sha(LF),'rows':440,'geometries':20,'paired_PS_cases':40,'wavelengths_nm':WLS,'u_x':[0.0],'k_y':[0.0],'capability':'NORMAL_INCIDENCE_ONLY','g01_quarantined_geometry_absent':True,'duplicate_or_conflicting_provenance':0},
 'input_contract':{'ordered_geometry':['D1','D2','D3','D4','D5','D6'],'condition':['wavelength_nm','u_x','polarization'],'diameter_sorting':False,'permutation_invariant_encoding':False,'mean_std_only_compression':False,'H_nm':500,'period_x_nm':1740,'period_y_nm':290},
 'output_contract':{'primary':['R']+[f'eta_m{m:+d}' for m in ORDERS],'derived':['T_total','directionality','target_non_target_ratio','leakage_score'],'T_definition':'sum_all_tracked_eta','symbolic_eta_plus1_key':'eta_m+1','complex_labels':'COMPLEX_ORDER_CONTRACT_NOT_YET_READY'},
 'model_families':[
  {'name':'LF_only','type':'deterministic_reference','trainable':False},
  {'name':'LF_global_bias','type':'LF_plus_global_bias','features':'LF-compatible outputs only'},
  {'name':'LF_affine','type':'LF_plus_condition_affine_correction','features':'LF-compatible outputs only'},
  {'name':'LF_ridge_residual','type':'LF_plus_ridge_residual','features':'ordered geometry + condition + LF'},
  {'name':'LF_paired_shared_contrast','type':'paired_PS_structured_residual','features':'paired P/S LF residual'},
  {'name':'corrected_residual_mlp','type':'compact_residual_mlp','hidden':[64,64],'activation':'GELU','features':'ordered geometry + condition + LF'},
  {'name':'direct_mlp','type':'compact_direct_mlp','hidden':[64,64],'activation':'GELU','features':'ordered geometry + condition'},
  {'name':'resmlp','type':'compact_resmlp','hidden':[64,64,64],'activation':'GELU','features':'ordered geometry + condition'},
  {'name':'circular_cnn','type':'frozen_M7_incumbent','architecture':'M7 circular 1D CNN'}],
 'cv_protocol':{'outer':'20-fold Leave-One-Geometry-Out','holdout_unit':'geometry including both P/S and all 11 wavelengths','row_random_split':False,'normalization':'fit within each training fold only','seeds':SEEDS,'epochs':80,'torch_threads':2},
 'loss_contract':{'primary':'mean squared error on [R,eta_m-3..eta_m+3] or LF residual target where legal','residual_reconstruction':'HF_hat = LF + delta_hat','no_hf_to_lf_calibration':True,'constraints':'raw and nonnegative/energy constrained projection both reported'},
 'metrics':{'numerical':['full_order_profile_MAE','full_order_profile_RMSE','eta_plus1_MAE_RMSE','eta_0_MAE_RMSE','eta_minus1_MAE_RMSE','per_order_MAE','R_MAE','T_MAE','median_abs_error','P90_abs_error','max_abs_error','per_geometry','per_polarization','per_wavelength','worst_geometry','worst_geometry_polarization','seed_dispersion'],'ranking':['broadband_eta_plus1_Spearman','Top3_recall','Top5_recall','true_champion_rank','near_champion_retrieval','pairwise_ordering','seed_stability'],'physics':['negative_power_violation','order_bookkeeping','T_order_consistency','energy_residual','R_T_legality','order_sign_identity','P_S_identity','wavelength_identity','out_of_scope_attempts'],'ps':['contrast_MAE','worst_geometry','worst_wavelength']},
 'comparison_contract':{'common_HF16':'M7 16G frozen OOF vs M8 20G LOGO on original HF16 geometries; report paired geometry deltas','M7A_new4':'separate held-out difficulty audit','prospective_like':'M7 selection-time predictions only vs M7A HF truth; never use M8 predictions for selection-time claim'},
 'promotion_gate':{'criteria':['eta_plus1_not_worse_than_strong_LF_calibrated_incumbent','full_order_not_materially_worse_than_physics_baseline','champion_and_top3_reliable','worst_case_controlled','physics_consistency_pass','P_S_contrast_predictive','R_T_quantitatively_usable','geometry_level_consistency','common_HF16_no_systematic_regression'],'decision_values':['EXTERNAL_HF_PROMOTION_READY','MORE_TARGETED_DEVELOPMENT_HF_REQUIRED','FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED','MODEL_FORMULATION_REQUIRES_REVISION'],'external_remains_metadata_only':True},
 'governance':{'external_registry':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','external_geometry_count':12,'future_logical_cases':24,'external_target_reads':0,'sealed_target_reads':0,'concurrency3':'CONCURRENCY3_FUNCTIONAL_STABILITY_EVIDENCE_PRESENT; continuous CPU/RAM unavailable; not throughput-optimal validation'},
 'fit_order_lock':'This artifact and its SHA must exist before any M8 fit artifact.'}
OUT.mkdir(parents=True)
pr=OUT/'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json'; jwrite(pr,prereg)
ph=sha(pr); jwrite(OUT/'preregistration_sha256.json',{'path':str(pr.relative_to(ROOT)),'sha256':ph,'fit_started_after_preregistration':False})
jwrite(OUT/'authority_audit_pre_fit.json',{'status':'PASS','rows':440,'geometries':20,'paired_cases':40,'wavelengths':WLS,'u_x':[0.0],'duplicate_or_conflicting_provenance':0,'lf_rows':440,'lf_key_mismatch':0,'g01_quarantined_absent':True,'external_target_reads':0,'sealed_target_reads':0,'solver_calls':0,'m7a_selection_manifest_sha256':sha(M7DES/'selection_manifest.json'),'m7a_selection_manifest_preserved':True})
jwrite(OUT/'solver_zero_pre_fit.json',{'fdtd_run_calls':0,'lumapi_solver_run_calls':0,'new_development_hf':0,'external_hf_calls':0,'sealed_hf_target_reads':0,'inverse_design':0,'active_solver_processes':False})
print(json.dumps({'status':'PASS','preregistration_sha256':ph,'rows':440,'geometries':20,'paired_cases':40,'solver_calls':0},indent=2))
