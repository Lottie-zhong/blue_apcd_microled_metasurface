import csv, json
from collections import defaultdict
from pathlib import Path
import numpy as np
R=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1'); O=R/'outputs/np_k6_m8_20g_forward_retraining_v1'; HF=R/'outputs/np_k6_m7a_primary4_targeted_hf_acquisition_closeout_v1/m7a_formal_development_hf_observations_440rows.csv'; OLD=R/'outputs/np_k6_m7_16g_forward_retraining_v1/oof_predictions_16g.csv'; NEW=O/'oof_predictions_20g.csv'; SEL=R/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1/selection_manifest.json'
ORD=(-3,-2,-1,0,1,2,3)
def rd(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wr(name,rs):
 fields=[]
 for r in rs:
  for k in r:
   if k not in fields:fields.append(k)
 with (O/name).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rs)
hf=rd(HF); old=rd(OLD); new=rd(NEW); hm={(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in hf}; nm={(r['model'],r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in new}; om={(r['model'],r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in old}; oldgeos=sorted({r['geometry_id'] for r in old}); selected=set(json.loads(SEL.read_text(encoding='utf-8-sig'))['Primary4'][i]['geometry_id'] for i in range(4)); common=sorted(set(oldgeos)&{r['geometry_id'] for r in hf})
def vals(r,prefix):return np.asarray([float(r[f'{prefix}{m:+d}']) for m in ORD])
def t(r):return float(r.get('pred_T',sum(vals(r,'pred_eta_m'))))
models=sorted({r['model'] for r in old})
full=[]; summary=[]
for model in models:
 geo_rows=[]
 for g in common:
  items=[(p,w) for p in ('p','s') for w in range(445,456)]
  eold=[];enew=[];aold=[];anew=[];rold=[];rnew=[];told=[];tnew=[]; cold=[];cnew=[]
  for p,w in items:
   k=(g,p,w); y=hm[k]; po=om[(model,)+k]; pn=nm[(model,)+k]; yeta=vals(y,'eta_m'); eo=np.abs(vals(po,'pred_eta_m')-yeta); en=np.abs(vals(pn,'pred_eta_m')-yeta); eold.extend(eo);enew.extend(en);aold.append(abs(float(po['pred_eta_m+1'])-float(y['eta_m+1'])));anew.append(abs(float(pn['pred_eta_m+1'])-float(y['eta_m+1']))); rold.append(abs(float(po['pred_R'])-float(y['R_total'])));rnew.append(abs(float(pn['pred_R'])-float(y['R_total']))); told.append(abs(t(po)-float(y['T_total'])));tnew.append(abs(t(pn)-float(y['T_total'])))
  for w in range(445,456):
   yp=hm[(g,'p',w)];ys=hm[(g,'s',w)];po=om[(model,g,'p',w)];ps=om[(model,g,'s',w)];pn=nm[(model,g,'p',w)];qs=nm[(model,g,'s',w)]; cold.append(abs((float(po['pred_eta_m+1'])-float(ps['pred_eta_m+1']))-(float(yp['eta_m+1'])-float(ys['eta_m+1'])))); cnew.append(abs((float(pn['pred_eta_m+1'])-float(qs['pred_eta_m+1']))-(float(yp['eta_m+1'])-float(ys['eta_m+1']))))
  row={'model':model,'geometry_id':g,'M7_order_profile_mae':float(np.mean(eold)),'M8_order_profile_mae':float(np.mean(enew)),'delta_order':float(np.mean(enew)-np.mean(eold)),'M7_eta_plus1_mae':float(np.mean(aold)),'M8_eta_plus1_mae':float(np.mean(anew)),'delta_eta_plus1':float(np.mean(anew)-np.mean(aold)),'M7_R_mae':float(np.mean(rold)),'M8_R_mae':float(np.mean(rnew)),'delta_R':float(np.mean(rnew)-np.mean(rold)),'M7_T_mae':float(np.mean(told)),'M8_T_mae':float(np.mean(tnew)),'delta_T':float(np.mean(tnew)-np.mean(told)),'M7_PS_contrast_mae':float(np.mean(cold)),'M8_PS_contrast_mae':float(np.mean(cnew)),'delta_PS_contrast':float(np.mean(cnew)-np.mean(cold))}
  full.append(row);geo_rows.append(row)
 summary.append({'model':model,'geometry_count':len(geo_rows),'improved_order':sum(x['delta_order']<0 for x in geo_rows),'degraded_order':sum(x['delta_order']>0 for x in geo_rows),'median_delta_order':float(np.median([x['delta_order'] for x in geo_rows])),'improved_eta_plus1':sum(x['delta_eta_plus1']<0 for x in geo_rows),'degraded_eta_plus1':sum(x['delta_eta_plus1']>0 for x in geo_rows),'median_delta_eta_plus1':float(np.median([x['delta_eta_plus1'] for x in geo_rows])),'M7_R_mean':float(np.mean([x['M7_R_mae'] for x in geo_rows])),'M8_R_mean':float(np.mean([x['M8_R_mae'] for x in geo_rows])),'M7_T_mean':float(np.mean([x['M7_T_mae'] for x in geo_rows])),'M8_T_mean':float(np.mean([x['M8_T_mae'] for x in geo_rows])),'M7_PS_mean':float(np.mean([x['M7_PS_contrast_mae'] for x in geo_rows])),'M8_PS_mean':float(np.mean([x['M8_PS_contrast_mae'] for x in geo_rows]))})
wr('common_HF16_full_metric_delta.csv',full);wr('common_HF16_full_learning_value.csv',summary)
# New4 detailed held-out audit, including R/T and paired P/S contrast.
newrows=[]
for g in sorted(selected):
 for model in models:
  ix=[(p,w) for p in ('p','s') for w in range(445,456)]; oe=[];ae=[];re=[];te=[];ce=[]
  for p,w in ix:
   y=hm[(g,p,w)];q=nm[(model,g,p,w)];oe.append(np.mean(np.abs(vals(q,'pred_eta_m')-vals(y,'eta_m'))));ae.append(abs(float(q['pred_eta_m+1'])-float(y['eta_m+1'])));re.append(abs(float(q['pred_R'])-float(y['R_total'])));te.append(abs(t(q)-float(y['T_total'])))
  for w in range(445,456):
   yp=hm[(g,'p',w)];ys=hm[(g,'s',w)];qp=nm[(model,g,'p',w)];qs=nm[(model,g,'s',w)];ce.append(abs((float(qp['pred_eta_m+1'])-float(qs['pred_eta_m+1']))-(float(yp['eta_m+1'])-float(ys['eta_m+1']))))
  role=next(x['acquisition_role'] for x in json.loads(SEL.read_text(encoding='utf-8-sig'))['Primary4'] if x['geometry_id']==g);newrows.append({'model':model,'geometry_id':g,'role':role,'order_profile_mae':float(np.mean(oe)),'eta_plus1_mae':float(np.mean(ae)),'R_mae':float(np.mean(re)),'T_mae':float(np.mean(te)),'PS_contrast_mae':float(np.mean(ce))})
wr('new4_heldout_full_difficulty.csv',newrows)
# HF20 paired truth distributions for primary outputs and P/S contrasts.
truth=[];pair=defaultdict(dict)
for r in hf:pair[(r['geometry_id'],int(float(r['wavelength_nm'])))][r['polarization'].lower()]=r
for metric,field in [('eta_plus1','eta_m+1'),('eta_0','eta_m+0'),('eta_minus1','eta_m-1'),('R','R_total'),('T','T_total')]:
 for scope,gs in [('HF16',set({r['geometry_id'] for r in hf})-selected),('M7A_new4',selected),('HF20',set({r['geometry_id'] for r in hf}))]:
  a=np.asarray([float(r[field]) for r in hf if r['geometry_id'] in gs]);truth.append({'scope':scope,'metric':metric,'n':len(a),'mean':float(a.mean()),'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),'max':float(a.max())})
for metric,field in [('eta_plus1','eta_m+1'),('eta_0','eta_m+0'),('eta_minus1','eta_m-1')]:
 for scope,gs in [('HF16',set({r['geometry_id'] for r in hf})-selected),('M7A_new4',selected),('HF20',set({r['geometry_id'] for r in hf}))]:
  a=np.asarray([abs(float(v['p'][field])-float(v['s'][field])) for (g,w),v in pair.items() if g in gs]);truth.append({'scope':scope,'metric':'PS_abs_'+metric,'n':len(a),'mean':float(a.mean()),'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),'max':float(a.max())})
wr('hf20_ps_truth_distribution_summary.csv',truth)
# OOF residual structure for LF, global-bias, affine and ridge outputs by geometry/polarization/order.
res=[]
for model in ('LF_only','LF_global_bias','LF_affine','LF_ridge_residual'):
 for g in sorted({r['geometry_id'] for r in hf}):
  for pol in ('p','s'):
   for m in ORD:
    a=[]
    for w in range(445,456):
     y=hm[(g,pol,w)];q=nm[(model,g,pol,w)];a.append(float(y[f'eta_m{m:+d}'])-float(q[f'pred_eta_m{m:+d}']))
    z=np.asarray(a);res.append({'model':model,'geometry_id':g,'polarization':pol,'order_n':m,'mean_hf_minus_model':float(z.mean()),'mae_hf_minus_model':float(np.abs(z).mean()),'p90_abs_hf_minus_model':float(np.quantile(np.abs(z),.9)),'max_abs_hf_minus_model':float(np.abs(z).max())})
wr('residual_structure_oof_by_geometry.csv',res)
print(json.dumps({'status':'PASS','common_rows':len(full),'new4_rows':len(newrows),'hf_truth_rows':len(truth),'residual_rows':len(res)}))
