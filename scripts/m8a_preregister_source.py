import csv, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
O=R/'outputs/np_k6_m8a_final_targeted_acquisition_design_v1'
M7A=R/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1'
M8=R/'outputs/np_k6_m8_20g_forward_retraining_v1'
HF=R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'
LF=R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_lf_baseline_440rows.csv'
EXT=R/'outputs/np_k6_m5_fullk6_forward_v0/external_set_registry.json'
CAND=M7A/'candidate_acquisition_features.csv'; AUD=M7A/'candidate_universe_audit.json'; SEL=M7A/'selection_manifest.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
if O.exists() and (O/'NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PREREG_V1.json').exists(): raise RuntimeError('refusing_existing_m8a_prereg')
hf=csvrows(HF); lf=csvrows(LF); cand=csvrows(CAND); audit=json.loads(AUD.read_text(encoding='utf-8-sig')); sel=json.loads(SEL.read_text(encoding='utf-8-sig'))['Primary4']
tail=[x['geometry_id'] for x in sel if x['acquisition_role']=='RESIDUAL-TAIL'][0]
if len(hf)!=440 or len(lf)!=440 or audit['eligible_candidate_count']!=len(cand): raise RuntimeError('authority_count')
O.mkdir(parents=True,exist_ok=True)
pr={
 'preregistration_id':'NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PREREG_V1',
 'created_utc':datetime.now(timezone.utc).isoformat(),
 'solver_calls':0,'new_hf':0,'external_hf':0,'sealed_target_reads':0,'inverse_design':0,
 'authority':{'m8_preregistration_sha256':'fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9','hf_rows':440,'geometries':20,'paired_PS_cases':40,'wavelengths_nm':list(range(445,456)),'u_x':[0.0],'capability':'NORMAL_INCIDENCE_ONLY','candidate_universe_source':str(CAND.relative_to(R)),'candidate_universe_sha256':sha(CAND),'candidate_universe_audit_sha256':sha(AUD),'eligible_candidate_count':len(cand),'external_registry_sha256':sha(EXT),'m7a_selection_manifest_sha256':sha(SEL),'G01_residual_tail_geometry':tail},
 'exclusions':{'formal_HF20_overlap':True,'formal_HF16_overlap':True,'external_registry_overlap':True,'sealed_pool_overlap':True,'duplicate_geometry_hash':True,'historical_quarantined_G01':'K6X_D110_D125_D130_D135_D140_D175','external_target_reads':0,'sealed_target_reads':0},
 'scope':{'ordered_D1_D6':True,'diameter_sorting':False,'u_x_only':0.0,'no_angular_acquisition':True,'no_new_truth':True},
 'roles':{'TAIL-LOCALIZATION':'localize whether M7A G01 residual-tail is isolated, smooth local, diameter-jump-driven, P/S-dependent, or order-redistribution cluster','RANKING-DISAMBIGUATION':'reduce champion/Top-K ambiguity near current Pareto frontier'},
 'normalization':'min-max fit on eligible candidate universe only; no HF truth, external metadata, or sealed metadata used for score fitting',
 'feature_contract':{'tail':['ordered_D1_D6','adjacent_diameter_jumps','diameter_span','distance_to_G01','LF_order_profile_similarity','LF_eta_plus1_similarity','LF_to_HF_residual_proxy','Ridge_CNN_disagreement','P_S_proxy','wavelength_robustness'],'ranking':['broadband_eta_plus1_potential','model_rank_variance','pairwise_rank_reversal','distance_to_Top3_boundary','Ridge_CNN_disagreement','calibrated_LF_vs_learned_disagreement','spectral_robustness','P_S_proxy'],'anti_duplication':['nearest_HF20_distance','candidate_pairwise_redundancy']},
 'scoring':{'tail_score':'0.30*G01_physical_proximity + 0.20*G01_LF_response_similarity + 0.20*residual_proxy + 0.15*Ridge_CNN_disagreement + 0.10*PS_proxy + 0.05*spectral_robustness','ranking_score':'0.25*model_rank_variance + 0.20*pairwise_rank_reversal + 0.20*near_Top3_margin + 0.15*broadband_eta_plus1_potential + 0.10*Ridge_CNN_disagreement + 0.10*PS_proxy','all_terms_minmax_on_eligible_pool':True},
 'selection_rule':{'primary_count':2,'primary_roles':['TAIL-LOCALIZATION','RANKING-DISAMBIGUATION'],'one_candidate_per_role':True,'tail_pick':'highest tail_score, then lowest physical redundancy, then descending geometry_hash','ranking_pick':'highest ranking_score excluding tail pick, then lowest physical redundancy, then descending geometry_hash','backup_count':6,'backup_order':'deterministic interleaving tail/ranking/mixed queues by frozen score and geometry_hash','optional_first4':'Primary2 plus next two backups only; not default recommendation','no_automatic_backup_substitution':True},
 'baseline_comparison':['proposed_Primary2','residual_score_top2','performance_only_top2','ranking_ambiguity_top2','random2_seeded_20260816'],
 'marginal_value_contract':'compare Primary2 versus Primary2+next2 backups on tail localization, ranking ambiguity, P/S information, redundancy, LF response diversity',
 'future_solver_cost':{'primary2_formal_cases':4,'primary2_rows':44,'optional_first4_formal_cases':8,'optional_first4_rows':88,'runtime':'4 MPI x 1 thread compliant authority','concurrency3_governance':'functional stability evidence only; not throughput optimal'},
 'future_success_criteria':{'tail':'continuous/error-cluster localization OR informative negative result showing isolated/proxy failure','ranking':'near-champion ordering materially clarified OR agreement confirmed','no_giant_error_required':True},
 'plateau_stop_rule':'If after Primary2 and M9 no model passes all gates, common-HF20 lacks consistent improvement, and tail/champion failures do not converge, stop automatic development-HF loop and enter FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED.',
 'identity_freeze_order':'This preregistration hash must precede final candidate identity generation.'}
p=O/'NP_K6_M8A_FINAL_TARGETED_ACQUISITION_PREREG_V1.json'; p.write_text(json.dumps(pr,indent=2,sort_keys=True)+'\n',encoding='utf-8'); ph=sha(p)
(O/'preregistration_sha256.json').write_text(json.dumps({'path':str(p.relative_to(R)),'sha256':ph,'candidate_identities_generated_after_hash':False},indent=2)+'\n',encoding='utf-8')
(O/'solver_zero_pre_design.json').write_text(json.dumps({'solver_calls':0,'new_hf':0,'external_hf':0,'sealed_target_reads':0,'inverse_design':0},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','preregistration_sha256':ph,'eligible_candidate_count':len(cand),'g01_tail_geometry':tail}))
