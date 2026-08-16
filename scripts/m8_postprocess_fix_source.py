import csv,json,hashlib
from pathlib import Path
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1');O=R/'outputs/np_k6_m8_20g_forward_retraining_v1';D=R/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1'
sel=json.loads((D/'selection_manifest.json').read_text(encoding='utf-8-sig'))['Primary4']
rows=[]
for s in sel:
 for field,model in [('lf_eta_plus1','LF_only'),('calibrated_eta_plus1','LF_global_bias'),('ridge_eta_plus1','LF_ridge_residual'),('residual_mlp_eta_plus1','corrected_residual_mlp'),('cnn_eta_plus1','circular_cnn')]:
  rows.append({'geometry_id':s['geometry_id'],'role':s['acquisition_role'],'selection_model':model,'selection_time_predicted_broadband_eta_plus1':float(s[field])})
# Recover truth from authoritative HF rows.
with (R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv').open(encoding='utf-8-sig',newline='') as f: hf=list(csv.DictReader(f))
by={}
for g in {r['geometry_id'] for r in hf}:
 by[g]=sum(float(r['eta_m+1']) for r in hf if r['geometry_id']==g)/sum(1 for r in hf if r['geometry_id']==g)
pred= {r['geometry_id']:r['selection_time_predicted_broadband_eta_plus1'] for r in rows}
order_true={g:i+1 for i,g in enumerate(sorted(by,key=by.get,reverse=True))};order_pred={g:i+1 for i,g in enumerate(sorted(pred,key=pred.get,reverse=True))}
for r in rows:
 r['M7A_true_broadband_eta_plus1']=by[r['geometry_id']];r['absolute_error']=abs(r['selection_time_predicted_broadband_eta_plus1']-by[r['geometry_id']]);r['true_rank_within_primary4']=order_true[r['geometry_id']];r['predicted_rank_within_primary4']=order_pred[r['geometry_id']]
with (O/'m7a_prospective_like_selection_time_audit.csv').open('w',encoding='utf-8',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'status':'PASS','rows':len(rows),'models':sorted({r['selection_model'] for r in rows}),'solver_calls':0},indent=2))
