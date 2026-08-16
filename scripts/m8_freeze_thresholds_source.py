import hashlib,json
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); O=R/'outputs/np_k6_m8_20g_forward_retraining_v1'; p=O/'NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1.json'
x=json.loads(p.read_text(encoding='utf-8-sig'))
x['promotion_gate']['quantitative_thresholds']={
 'order_profile_mae_relative_to_best_lf_calibrated_max':1.0,
 'eta_plus1_mae_relative_to_best_lf_calibrated_max':1.0,
 'ranking_spearman_min':0.90,
 'top3_recall_min':2/3,
 'true_champion_predicted_rank_max':3,
 'worst_geometry_order_profile_mae_max':0.10,
 'R_mae_max':0.12,
 'T_mae_max':0.12,
 'energy_residual_max':0.05,
 'P_S_contrast_mae_max':0.15,
 'common_HF16_improved_geometries_at_least_degraded':True,
 'all_constraints_frozen_before_fit':True}
p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')
h=hashlib.sha256(p.read_bytes()).hexdigest(); (O/'preregistration_sha256.json').write_text(json.dumps({'path':str(p.relative_to(R)),'sha256':h,'fit_started_after_preregistration':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'preregistration_sha256':h,'fit_started_after_preregistration':False},indent=2))
