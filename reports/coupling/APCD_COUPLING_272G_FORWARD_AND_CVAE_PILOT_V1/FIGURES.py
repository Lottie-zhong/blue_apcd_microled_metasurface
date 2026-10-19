"""Python-only quantitative figures for observed 272G forward/CVAE pilot; no fits/solvers."""
from pathlib import Path
import json,csv,sys,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';F=D/'figures';F.mkdir(exist_ok=True);rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
h2=H.load_h2_decoder();data=np.load(B/'COMPLEX_DATASET.npz');ids=list(data['case_ids']);idx={v:i for i,v in enumerate(ids)};old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');m=rd(D/'FORWARD/METRICS_FIXED124.json');keys=['Mean','KRR','ExtraTrees','Balanced','Leaf1'];names=['Complex Mean','KRR','ET leaf3','Balanced','ET leaf1'];col=['#777777','#4676A9','#337E73','#BC8B54','#765A8C'];pred={};raw=np.load(B/'PREDICTIONS_B.npz')
for k in keys[:3]:pred[k]=(raw[k+'_C_hat'],raw[k+'_P_scale'])
for k in keys[3:]:p=np.load(D/'FORWARD'/(k+'_PREDICTIONS.npz'));pred[k]=(p['C_hat'],p['P_scale'])
fields=[('complex_NRMSE','Complex NRMSE'),('TM_magnitude_RMSE','TM magnitude RMSE'),('routing_MAE','All-order Routing MAE'),('P_scale_MAE','P_scale MAE'),('Pplus_MAE','H2 P(+1) MAE'),('rho450_mean','450 nm mean-fold Spearman')];foldmetrics={}
for k,(cc,pp) in pred.items():
 rr=[]
 for f in old:
  fi=f['fold']-1;vi=np.array([idx[v] for v in f['heldout_old_ids']]);t=data['C_hat'][vi];c=cc[fi,vi];p=pp[fi,vi];hh=H.reconstruct_h2(c,p,h2);rr.append({'complex_NRMSE':float(np.sqrt(np.sum(abs(c-t)**2)/np.sum(abs(t)**2))),'TM_magnitude_RMSE':float(np.sqrt(np.mean((abs(c[:,:,:,1])-abs(t[:,:,:,1]))**2))),'routing_MAE':float(abs(hh['eta']-data['eta_H2'][vi]).mean()),'P_scale_MAE':float(abs(p-data['P_scale'][vi]).mean()),'Pplus_MAE':float(abs(hh['absolute_order'][:,:,4]-data['absolute_H2'][vi,:,4]).mean()),'rho450_mean':m[k]['rho450_folds'][fi]})
 foldmetrics[k]=rr
(F/'FORWARD_FOLD_SOURCE.json').write_text(json.dumps(foldmetrics,indent=2))
contract={'claim':'Compare small complex-state contrasts and bounded generative feasibility; preserve remaining failures and proxy/truth distinctions','archetype':'quantitative grid','backend':'Python','width_mm':183,'font_pt':8,'n_geometries':124,'CVAE_seeds':2,'forward_seeds':3,'all_wavelengths':21,'forward_errorbars':'range of4fixedfolds, not CI','CVAE_errorbars':'range of8foldseedruns, not CI or8independentdatasets; pooled124 geometry-weighted means','inverse_condition_error':'4D condition RMSE standardized by trainingfold s.d.; all newgeometry optical values are proxy only','posterior_reconstruction':'uses geometryinput, not prior inverse generation','geometry_legal':'100..230,5nm rounding, periodicgap>=60 by construction, no manufacturingcertification','no_smoothing_or_excluded_queries':True,'tree_diagnostic_scope':'fold1seed17,32geometries,128trees; not entire domain'};(F/'FIGURE_CONTRACT.json').write_text(json.dumps(contract,indent=2))
def save(fig,n):
 fig.savefig(F/(n+'.pdf'));fig.savefig(F/(n+'.svg'));fig.savefig(F/(n+'.png'),dpi=600);plt.close(fig)
fig,axs=plt.subplots(2,3,figsize=(7.20472440945,134/25.4),layout='constrained')
for j,(key,label) in enumerate(fields):
 ax=axs.flat[j]
 for i,k in enumerate(keys):
  val=m[k][key]
  if val is None:ax.text(i,0,'NA',ha='center',va='bottom');continue
  vals=[v[key] for v in foldmetrics[k] if v[key] is not None];ax.bar(i,val,color=col[i],width=.7,yerr=[[max(0,val-min(vals))],[max(0,max(vals)-val)]],capsize=2,error_kw={'elinewidth':.7})
 ax.set(xticks=range(5),xticklabels=names,ylabel=label,xlim=(-.6,4.6));ax.set_title(chr(97+j),loc='left')
 for tick in ax.get_xticklabels():tick.set_rotation(35);tick.set_rotation_mode('anchor');tick.set_ha('right')
save(fig,'FORWARD_LIGHTWEIGHT_COMPARISON')
fig,axs=plt.subplots(2,2,figsize=(7.20472440945,124/25.4),layout='constrained');core=['ExtraTrees','Balanced','Leaf1'];corelabels=['ET leaf3','Balanced','ET leaf1'];ccol=[col[2],col[3],col[4]]
axs[0,0].bar(range(3),[m[k]['weighted_norm_mean'] for k in core],color=ccol);axs[0,0].axhline(1,color='.4',ls=':',lw=.8);axs[0,0].set(xticks=range(3),xticklabels=corelabels,ylabel='Mean predicted weighted norm');axs[0,0].set_title('a  Truth norm = 1',loc='left')
axs[0,1].bar(range(3),[m[k]['TM_between_geometry_variance_ratio'] for k in core],color=ccol);axs[0,1].axhline(1,color='.4',ls=':',lw=.8);axs[0,1].set(xticks=range(3),xticklabels=corelabels,ylabel='TM magnitude variance / truth variance');axs[0,1].set_title('b  Between-geometry variation',loc='left')
t=rd(D/'FORWARD/TREE_AVERAGING_DIAGNOSTIC.json');axs[1,0].bar([0,1],[t['individual_tree_weighted_norm_mean'],t['forest_mean_weighted_norm_mean']],color=['#777777','#765A8C']);axs[1,0].set(xticks=[0,1],xticklabels=['Single-tree mean','Forest mean'],ylabel='Weighted norm');axs[1,0].set_title('c  Fold1 / seed17 / 32 geometries',loc='left')
for k,c in zip(core,ccol):axs[1,1].plot([0,1],[m[k]['complex_NRMSE'],m[k]['unit_norm_projection_complex_NRMSE']],color=c,marker='o',lw=1,label=corelabels[core.index(k)])
axs[1,1].set(xticks=[0,1],xticklabels=['Raw prediction','Unit-norm projection'],ylabel='Complex NRMSE');axs[1,1].set_title('d  Projection does not fix Routing',loc='left');axs[1,1].legend(fontsize=7)
save(fig,'TM_SHRINKAGE_AND_TREE_AVERAGING')
# Eight actual training curves; ranges represent run heterogeneity, not independentdata confidence.
runs=sorted((D/'CVAE').glob('fold*_seed*'));loss=[];kl=[]
for r in runs:
 rows=list(csv.DictReader((r/'LOSS.csv').open()));loss.append([float(v['reconstruction_MSE_norm']) for v in rows]);kl.append([float(v['KL']) for v in rows])
fig,axs=plt.subplots(1,3,figsize=(7.20472440945,82/25.4),layout='constrained')
for ax,arr,label,title in [(axs[0],np.array(loss),'Training reconstruction MSE','a'),(axs[1],np.array(kl),'Training KL','b')]:
 for row in arr:ax.plot(range(1,401),row,color='#4676A9',alpha=.23,lw=.65)
 ax.plot(range(1,401),arr.mean(0),color='#337E73',lw=1.3,label='Eight-run mean');ax.set(xlabel='Epoch',ylabel=label);ax.set_title(title,loc='left');ax.legend(fontsize=7)
evalm=rd(D/'CVAE/EVALUATION_METRICS.json');rows=[r for r in evalm if r['method']=='CVAE_prior'];weighted=rd(D/'CVAE/SUMMARY_WEIGHTED124.json')['CVAE_prior']
for i,(field,lab) in enumerate([('train_posterior_MAE_nm','Train'),('posterior_reconstruction_MAE_nm','Heldout')]):
 yy=[r[field] for r in rows];v=weighted[field];axs[2].bar(i,v,color=['#777777','#337E73'][i],yerr=[[max(0,v-min(yy))],[max(0,max(yy)-v)]],capsize=2,error_kw={'elinewidth':.7})
axs[2].set(xticks=[0,1],xticklabels=['Train','Heldout'],ylabel='Posterior reconstruction MAE (nm)');axs[2].set_title('c  Geometry supplied to encoder',loc='left');save(fig,'CVAE_TRAINING_AND_RECONSTRUCTION')
# Candidate comparison is proxy only; known library truth gets a distinct panel.
sm=rd(D/'CVAE/SUMMARY_WEIGHTED124.json');audit=rd(D/'CVAE/PILOT_AUDIT.json');diag=rd(D/'CVAE/CONDITION_AND_BASELINE_DIAGNOSTICS.json');methods=['CVAE_prior','uniform_random','training_retrieval'];labels=['CVAE','Random','Library'];colors=['#337E73','#777777','#4676A9'];fig,axs=plt.subplots(2,3,figsize=(7.20472440945,135/25.4),layout='constrained')
for ax,key,label,title in [(axs[0,0],'proxy_best_of_16_RMSE_standardized','Best-of-16 condition RMSE (proxy)','a'),(axs[1,0],'within_target_pairwise_RMS_nm','Within-target diversity (nm)','d')]:
 for i,(method,c) in enumerate(zip(methods,colors)):
  yy=[r[key] for r in evalm if r['method']==method];v=sm[method][key];ax.bar(i,v,color=c,yerr=[[max(0,v-min(yy))],[max(0,max(yy)-v)]],capsize=2,error_kw={'elinewidth':.7})
 ax.set(xticks=range(3),xticklabels=labels,ylabel=label);ax.set_title(title,loc='left')
# Paired eight-run truth errors; library nearest by knowntruth is definitionally optimal withinlibrary.
rr=[r for r in evalm if r['method']=='training_retrieval'];true_nn=[r['retrieval_oracle_true_best_of16_condition_RMSE'] for r in rr];proxy_pick=[r['retrieval_true_error_of_proxy_selected'] for r in rr]
for a,b in zip(true_nn,proxy_pick):axs[0,1].plot([0,1],[a,b],color='#777777',alpha=.45,lw=.8,marker='.',ms=3)
axs[0,1].plot([0,1],[sm['training_retrieval']['retrieval_oracle_true_best_of16_condition_RMSE'],sm['training_retrieval']['retrieval_true_error_of_proxy_selected']],color='#BC8B54',lw=1.6,marker='o',ms=4);axs[0,1].set(xticks=[0,1],xticklabels=['Truth NN','Proxy-picked'],ylabel='Known library TRUE condition RMSE');axs[0,1].set_title('b  Retrospective library check',loc='left')
for r in diag:axs[0,2].plot([0,1],[r['same_condition_best16_proxy_error_mean'],r['shuffled_condition_best16_proxy_error_mean']],color='#4676A9',alpha=.55,lw=.9,marker='.',ms=3)
axs[0,2].set(xticks=[0,1],xticklabels=['Correct condition','Shuffled'],ylabel='Best-of-16 condition RMSE (proxy)');axs[0,2].set_title('c  Same latent samples',loc='left')
for i,(method,c) in enumerate(zip(methods,colors)):
 yy=[r['all272_exact_overlap_fraction'] for r in evalm if r['method']==method];axs[1,1].bar(i,sm[method]['all272_exact_overlap_fraction'],color=c)
axs[1,1].set(xticks=range(3),xticklabels=labels,ylabel='Exact overlap with 272G',ylim=(0,1.05));axs[1,1].set_title('e  Library overlap is intentional',loc='left')
latent=np.array([r['latent_mu_variance_train'] for r in rows]);im=axs[1,2].imshow(latent,aspect='auto',cmap='cividis');axs[1,2].set(xticks=range(3),xticklabels=['z1','z2','z3'],yticks=range(8),yticklabels=[f"F{r['fold']} S{r['seed']}" for r in rows],xlabel='Latent component');axs[1,2].set_title('f  Train posterior-mean variance',loc='left');fig.colorbar(im,ax=axs[1,2],shrink=.8)
for ax in [axs[0,1],axs[0,2]]:
 for tick in ax.get_xticklabels():tick.set_rotation(25);tick.set_rotation_mode('anchor');tick.set_ha('right')
save(fig,'CVAE_CONDITIONS_BASELINES_AND_DIVERSITY')
(F/'RENDER_COMPLETE.json').write_text(json.dumps({'figures':4,'formats':['PDF','SVG','600dpiPNG'],'no_fits':True,'new_FDTD':0,'visual_QA':'PENDING'},indent=2));print('PILOT_FIGURES_RENDERED',4)
