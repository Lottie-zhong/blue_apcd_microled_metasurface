from pathlib import Path
import json,csv,sys,numpy as np
from scipy.stats import spearmanr
D=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_272G_PSCALE_DECOUPLING_V1');R=D.parents[2];Q=D.parent;B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';S=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1';rd=lambda p:json.loads(Path(p).read_text());assert rd(D/'COMPLETE.json')['status']=='COMPLETE';z=np.load(B/'COMPLEX_DATASET.npz');ix={s:i for i,s in enumerate(z['case_ids'])};sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
dec=H.load_h2_decoder();base=np.load(D/'NN3_Joint_OOF.npz');va=np.array([ix[s] for s in base['case_ids']]);tp=z['P_scale'][va];eta=z['eta_H2'][va];checks=[];diag=[];wav=[]
for kind in ['Joint','PSNet','PMean','Ridge','ET3','Leaf1']:
 a=np.load(D/f'NN3_{kind}_OOF.npz');p=a['P'];c=a['C'];assert np.array_equal(a['case_ids'],base['case_ids']);assert np.array_equal(c,base['C']);hh=H.reconstruct_h2(c,p,dec);assert np.max(abs(hh['absolute_order']-a['absolute']))<1e-12;assert np.max(abs(a['eta']-base['eta']))<1e-12
 le=np.log(p/tp);linear=tp*le;curve=tp*(np.expm1(le)-le);assert np.max(abs(p-tp-linear-curve))<1e-12
 qtrue=tp-tp.mean(1,keepdims=True);qpred=p-p.mean(1,keepdims=True);peak=np.argmax(tp,axis=1);err=p-tp;prho=[]
 for j in range(21):
  rr=float(spearmanr(tp[:,j],p[:,j]).statistic) if np.std(p[:,j])>1e-14 else None;prho.append(rr);wav.append({'model':kind,'wavelength_nm':440+j,'n':124,'MAE':float(abs(err[:,j]).mean()),'bias':float(err[:,j].mean()),'geometry_Spearman':rr,'truth_mean':float(tp[:,j].mean()),'pred_mean':float(p[:,j].mean()),'true_std':float(tp[:,j].std(ddof=1)),'pred_std':float(p[:,j].std(ddof=1))})
 diag.append({'model':kind,'P_MAE':float(abs(err).mean()),'P_bias':float(err.mean()),'log_bias':float(le.mean()),'log_RMSE':float(np.sqrt(np.mean(le**2))),'linear_log_error_bias_contribution':float(linear.mean()),'positive_exponential_curvature_bias':float(curve.mean()),'geometry_variance_ratio_pooled124':float(np.var(p,axis=0,ddof=1).sum()/np.var(tp,axis=0,ddof=1).sum()),'within_geometry_spectral_variance_ratio':float(np.var(p,axis=1).sum()/np.var(tp,axis=1).sum()),'geometry_mean_Spearman':float(spearmanr(tp.mean(1),p.mean(1)).statistic),'peak_MAE':float(abs(err[np.arange(124),peak]).mean()),'peak_bias':float(err[np.arange(124),peak].mean()),'P_min':float(p.min()),'P_max':float(p.max()),'predicted_P_above1':int(np.sum(p>1)),'spectral_centered_RMSE':float(np.sqrt(np.mean((qpred-qtrue)**2)))})
 checks.append({'model':kind,'same_complex_state':True,'H2_power_recomputed':True,'identical_eta_all_P_models':True,'positive_P':bool((p>0).all())})
for n,rows in [('PSCALE_POOLED_DIAGNOSTIC.csv',diag),('PSCALE_WAVELENGTH_POOLED.csv',wav)]:
 with (D/n).open('w',newline='',encoding='utf-8') as f:wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
fr=list(csv.DictReader((D/'MODEL_FOLD_METRICS.csv').open()));seedsummary=[]
for seed in [17,29,43]:
 n=f'NN_seed{seed}';a=[r for r in fr if r['model']==n]
 for model in ['Leaf1','ET3']:
  b=[r for r in fr if r['model']==model+'_seed'+str(seed)];seedsummary.append({'seed':seed,'baseline':model,'NN_Pplus_MAE':sum(float(r['Pplus_MAE'])*int(r['n']) for r in a)/124,'baseline_Pplus_MAE':sum(float(r['Pplus_MAE'])*int(r['n']) for r in b)/124,'NN_rho_foldmean':float(np.mean([float(r['rho450']) for r in a])),'baseline_rho_foldmean':float(np.mean([float(r['rho450']) for r in b])),'folds_NN_better_Pplus':sum(float(ar['Pplus_MAE'])<float(br['Pplus_MAE']) for ar,br in zip(a,b))})
(D/'SEED_STABILITY_SUMMARY.json').write_text(json.dumps(seedsummary,indent=2))
# Additional P-scale MAE uncertainty, fixed models and family clusters.
fam=rd(B/'LOCAL_FAMILY_COMPONENTS.json');ids=list(base['case_ids']);g={s:s for s in ids}
for n,ff in enumerate(fam):
 for cid in ff:
  if cid in g:g[cid]='family_'+str(n)
units=[np.array([j for j,c in enumerate(ids) if g[c]==u]) for u in dict.fromkeys(g.values())];rng=np.random.default_rng(9051);bootstrap={};ej=abs(base['P']-tp).mean(1)
for kind in ['PSNet','ET3','Leaf1','Ridge','PMean']:
 p=np.load(D/f'NN3_{kind}_OOF.npz')['P'];delta=abs(p-tp).mean(1)-ej;val=[]
 for _ in range(2000):ii=np.concatenate([units[k] for k in rng.integers(len(units),size=len(units))]);val.append(delta[ii].mean())
 bootstrap[kind]={'P_scale_MAE_delta_vs_Joint':float(delta.mean()),'family_percentile95':np.quantile(val,[.025,.975]).tolist()}
(D/'PSCALE_PAIRED_STABILITY.json').write_text(json.dumps(bootstrap,indent=2));(D/'INDEPENDENT_RECONSTRUCTION_AUDIT.json').write_text(json.dumps({'all_six_combinations':checks,'frozen_H2_used':True,'P_exponential_bias_identity_verified':True,'truth_not_used_as_formal_model_input':True},indent=2))
gates=rd(D/'FROZEN_H1_DIAGNOSTIC.json');print('H1_TOP_KEYS',list(gates['NN3_Joint']));print('H1_GATE',rd(D/'H1_FROZEN_THRESHOLDS.json'));print('POOLED',diag);print('SEEDS',seedsummary);print('P_CI',bootstrap)
