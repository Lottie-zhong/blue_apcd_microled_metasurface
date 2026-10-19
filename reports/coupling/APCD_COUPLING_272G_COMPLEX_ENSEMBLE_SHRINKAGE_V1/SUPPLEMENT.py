from pathlib import Path
import json,numpy as np,csv,subprocess,sys
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';rd=lambda p:json.loads(Path(p).read_text());z=np.load(B/'COMPLEX_DATASET.npz');ix={s:i for i,s in enumerate(z['case_ids'])};sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
dec=H.load_h2_decoder();stats=[];seedstats=[]
for fold in range(1,5):
 p=np.load(D/f'A_ReIm_fold{fold}.npz');va=np.array([ix[s] for s in p['case_ids']]);c=np.concatenate([np.load(D/f'trees_fold{fold}_seed{s}.npz')['C'] for s in [17,29,43]]);mag=abs(c);mean=c.mean(0);ratio=abs(mean)/np.maximum(mag.mean(0),1e-15)
 for k in range(7):
  weight=mag[:,:,:,k,1].mean(0);d={'fold':fold,'order':k-3,'Re_tree_variance':float(c[:,:,:,k,1].real.var(0).mean()),'Im_tree_variance':float(c[:,:,:,k,1].imag.var(0).mean()),'TM_true_amplitude_q10_q50_q90':np.quantile(abs(z['C_hat'][va,:,k,1]),[.1,.5,.9]).tolist(),'TM_tree_amplitude_q10_q50_q90':np.quantile(mag[:,:,:,k,1],[.1,.5,.9]).tolist(),'TM_mean_amplitude_q10_q50_q90':np.quantile(abs(mean[:,:,k,1]),[.1,.5,.9]).tolist(),'TM_circular_resultant_q10_q50_q90':np.quantile(ratio[:,:,k,1],[.1,.5,.9]).tolist(),'amplitude_weighted_one_minus_circular_resultant':float((weight*(1-ratio[:,:,k,1])).sum()/weight.sum())};stats.append(d)
 for seed in [17,29,43]:
  t=np.load(D/f'trees_fold{fold}_seed{seed}.npz')['C'];a=t.mean(0);b=abs(t).mean(0)*np.exp(1j*np.angle(a))
  for name,cc in [('A_ReIm',a),('B_MagnitudeCircular',b)]:
   # Same physical Pscale per seed, taken from frozen saved predictions.
   pp=np.load(Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD/Leaf1_PREDICTIONS.npz')['P_scale_seeds'][fold-1,[17,29,43].index(seed),va];hh=H.reconstruct_h2(cc,pp,dec);seedstats.append({'model':name,'fold':fold,'seed':seed,'complex_NRMSE':float(np.linalg.norm(cc-z['C_hat'][va])/np.linalg.norm(z['C_hat'][va])),'Pplus_MAE':float(abs(hh['absolute_order'][:,:,4]-z['absolute_H2'][va,:,4]).mean())})
 for seed in [17,29]:
  a=np.load(D/f'NN_fold{fold}_seed{seed}.npz');hh=H.reconstruct_h2(a['C'],a['P'],dec);seedstats.append({'model':'D_NN29','fold':fold,'seed':seed,'complex_NRMSE':float(np.linalg.norm(a['C']-z['C_hat'][va])/np.linalg.norm(z['C_hat'][va])),'Pplus_MAE':float(abs(hh['absolute_order'][:,:,4]-z['absolute_H2'][va,:,4]).mean())})
(D/'MODAL_DISTRIBUTIONS.json').write_text(json.dumps(stats,indent=2))
with (D/'SEED_METRICS.csv').open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(seedstats[0]));wr.writeheader();wr.writerows(seedstats)
summary=list(csv.DictReader((D/'COMPLEX_AGGREGATION_ABLATION.csv').open()));(D/'SUMMARY_POOLED_VARIANCE_NOTE.json').write_text(json.dumps({'authoritative_summary':'COMPLEX_AGGREGATION_ABLATION.csv','reason':'TM_variance_ratio corrected to pooled124 geometry variance matching predecessor, FOLD_METRICS remains foldwise'},indent=2))
text='''
## Final comparative decision

Magnitude/circular aggregation B reduces TM amplitude MAE by38.2% and all-order Routing MAE by21.2%, but P+MAE worsens8.37%, rho falls0.499→0.191 and TM geometry variance falls14.18%→5.81% of truth. Only1/4folds improves P+. Power-onlyC shows the same limitation. Neither is promoted. Restoring average amplitude does not recover geometry-dependent modal allocation. Re/Im averaging is a main norm-loss mechanism, not a sufficient explanation or cure of target-power error.

New fixed29D NN is the most consistent tested improvement: stateNRMSE0.75471→0.57420 (23.9% lower), TM amplitudeMAE0.22314→0.12294 (44.9% lower), RoutingMAE0.11591→0.06814 (41.2% lower), P+MAE0.028486→0.021560 (24.3% lower), rho0.499→0.680 and Top20recall0.482→0.661. All4folds improve P+; paired family bootstrap P+delta95%[-0.01063,-0.00337], conditional on fixed fits. Relative phase49.22°→42.69°. TM variance recovery14.18%→66.75% is substantial but incomplete. PscaleMAE worsens0.05312→0.06127 (15.3% higher). Therefore this is a multi-metric development improvement with an explicit total-power weakness, not full scientific qualification. Mean baseline predecessor P+MAE0.04338 and KRR0.03897 are exceeded on pooled development metrics; stronger power-outputMean and truly external validation remain separate evidence.

FrozenH1 remains HOLD: NN state, Routing, thresholded absolute-order and total-power gates FAIL; absolute-order and seed-stability gates PASS. No reliable inverse optimization or full unknown-space certification. Capacity/representation matters in addition to geometry coverage; this small controlled probe does not establish the optimal model or guarantee more-data benefit.

MODAL_DISTRIBUTIONS.json records per-order tree/forest/truth amplitude quantiles, Re/Im variances and circular resultant distributions across all folds. SEED_METRICS.csv records individual seed performance; no best-seed selection. Broad low resultants represent phase/distribution ambiguity. No independent phase alignment is applied.
'''
for name in ['COMPLEX_ENSEMBLE_SHRINKAGE_REPORT.md','TM_ROUTING_AND_PHASE_REPORT.md','FORWARD_H1_GAP_AND_NEXT_STAGE.md']:
 p=D/name;p.write_text(p.read_text(encoding='utf-8')+text,encoding='utf-8')
(D/'CURRENT_AUTHORITY.json').write_text(json.dumps({'task':'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1','task_status':'PASS_OFFLINE_DIAGNOSTIC_COMPLETE','shrinkage_source':'CROSS_TREE_CANCELLATION_SUPPORTED_4FOLD_3SEED','preferred_tested_model':'D_NN29_CONDITIONAL_DEVELOPMENT_IMPROVEMENT','H1':'HOLD','FAST':272,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','CVAE':'FROZEN'},indent=2))
print('Supplement COMPLETE',len(stats),len(seedstats))
