"""Python scientific figures: actual fixed-124 complex-state OOF only, no solvers/fits."""
from pathlib import Path
import json,csv,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1';C=Q/'APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';F=D/'figures';F.mkdir(exist_ok=True);rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
counts=[222,238,254,272];sources={222:C,238:D/'STAGE_16',254:D/'STAGE_32',272:D/'STAGE_50'};metrics={n:rd(sources[n]/'METRICS_FIXED124.json') for n in counts};colors={'Mean':'#777777','KRR':'#4676A9','ExtraTrees':'#337E73'};w=np.arange(440,461)
def save(fig,n):
 fig.savefig(F/(n+'.pdf'));fig.savefig(F/(n+'.svg'));fig.savefig(F/(n+'.png'),dpi=600);plt.close(fig)
contract={'claim':'Measure actual complex-state learning gains and remaining amplitude/routing/local limitations under fixed validation','backend':'Python','archetype':'quantitative grid','width_mm':183,'minimum_target_font_pt':8,'evaluation_geometries':124,'folds':4,'ET_seeds':3,'errorbars':'fourfold range, not confidence intervals; local test one family without pseudo-replicate CI','wavelengths':21,'no_interpolation_or_clipping':True,'best_median_worst_rule':'B_ET Pplus per-geometry MAE sorted, positions0,62,123, examples only; primary metrics all124','new_fourcorner_groups':'truth-only old32train-only anchors; no in-sample generalization claim','not_final_convergence':True,'sources':'MODEL_LEARNING_CURVE.json, STAGE_*/OOF and complex truth, original222diagnostic'};(F/'FIGURE_CONTRACT.json').write_text(json.dumps(contract,indent=2))
fig,axs=plt.subplots(2,3,figsize=(7.20472440945,132/25.4),layout='constrained');fields=[('state_relative_RMSE','Complex NRMSE'),('magnitude_RMSE','Magnitude RMSE'),('relative_phase_MAE_deg','Relative phase MAE (deg)'),('P_scale_MAE','P_scale MAE'),('Pplus_MAE','H2 P(+1) MAE'),('rho450_meanfold','450 nm mean-fold Spearman')]
for j,(key,label) in enumerate(fields):
 ax=axs.flat[j]
 for kind,col in colors.items():
  for arch,ls in [('A','--'),('B','-')]:
   if kind=='Mean' and (arch=='B' or key=='rho450_meanfold'):continue
   yy=[metrics[n][arch+'_'+kind][key] for n in counts];lower=[];upper=[]
   for n,y in zip(counts,yy):
    v=metrics[n][arch+'_'+kind];vals=v['rho450_by_fold'] if key=='rho450_meanfold' else [r[key] for r in v['fold_metrics']];vals=[a for a in vals if a is not None];lower.append(max(0,y-min(vals)));upper.append(max(0,max(vals)-y))
   ax.errorbar(counts,yy,yerr=[lower,upper],color=col,ls=ls,marker='o',ms=3,lw=1,capsize=2,elinewidth=.55,label=arch+' '+('Complex Mean' if kind=='Mean' else kind))
 ax.set(xlabel='Valid development geometries',ylabel=label,xticks=counts);ax.set_title(chr(97+j),loc='left')
strong=[rd(C/'OUTPUT_DOMAIN_CONSTANT_BASELINE.json')['Pplus_MAE']]+[rd(D/f'STAGE_{k}/OUTPUT_DOMAIN_MEAN_REFERENCE.json')['Pplus_MAE'] for k in [16,32,50]]
reference=axs.flat[4].plot(counts,strong,color='#222222',ls=':',lw=1.2,label='Power constant Mean (reference)')[0]
handles,labels=axs.flat[0].get_legend_handles_labels();fig.legend(handles+[reference],labels+['Power constant Mean (reference)'],loc='outside lower center',ncol=3,frameon=False);save(fig,'COMPLEX_LEARNING_CURVES')
# All seven TM channels; TE is retained in all primary state metrics, phase dark guard unchanged.
chans={n:list(csv.DictReader((sources[n]/'PER_CHANNEL_ERRORS.csv').open(encoding='utf-8'))) for n in [222,272]};fig,axs=plt.subplots(2,2,figsize=(7.20472440945,124/25.4),layout='constrained')
for j,(field,label) in enumerate([('complex_RMSE','TM complex RMSE'),('magnitude_RMSE','TM magnitude RMSE'),('phase_MAE_deg','TM phase MAE (deg)'),('eta_order_MAE','Order Routing MAE')]):
 for n,ls in [(222,'--'),(272,'-')]:
  for arch,col in [('A','#4676A9'),('B','#337E73')]:
   rr=[r for r in chans[n] if r['model']==arch+'_ExtraTrees' and r['polarization']=='TM'];axs.flat[j].plot([int(r['order']) for r in rr],[float(r[field]) for r in rr],color=col,ls=ls,marker='o',ms=3,label=f'{arch} ET, {n}G')
 axs.flat[j].set(xlabel='Diffraction order m',ylabel=label,xticks=range(-3,4));axs.flat[j].set_title(chr(97+j),loc='left')
fig.legend(*axs.flat[0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False);save(fig,'TM_AMPLITUDE_PHASE_ROUTING')
local={n:rd(sources[n]/'LOCAL_PREDICTION_METRICS.json') for n in counts};fig,axs=plt.subplots(1,3,figsize=(7.20472440945,91/25.4),layout='constrained')
for j,(key,label) in enumerate([('delta_complex_relative_RMSE','Delta complex NRMSE'),('delta_magnitude_relative_RMSE','Delta magnitude NRMSE'),('relative_phase_delta_MAE_deg','Delta relative phase MAE (deg)')]):
 for kind,col in colors.items():
  for arch,ls in [('A','--'),('B','-')]:
   if kind=='Mean' and arch=='B':continue
   axs[j].plot(counts,[local[n][arch+'_'+kind][key] for n in counts],color=col,ls=ls,marker='o',ms=3,label=arch+' '+kind)
 if j<2:axs[j].axhline(1,color='.4',ls=':',lw=.8)
 axs[j].set(xlabel='Valid development geometries',ylabel=label,xticks=counts);axs[j].set_title('G059: 10 edges, one family',loc='left')
fig.legend(*axs[0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False);save(fig,'LOCAL_COMPLEX_LEARNING')
z=np.load(D/'STAGE_50/COMPLEX_DATASET.npz');ids=list(z['case_ids']);x=z['D_nm'];ct=z['C_hat'];pt=z['P_scale'];power=z['absolute_H2'];oldgroups=list(csv.DictReader((Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2/AL50_INTERACTION_GROUPS.csv').open(encoding='utf-8')));allgroups=[]
for g in oldgroups:allgroups.append((g['anchor'],[ids.index(g[k]) for k in ['D','D_i','D_j','D_ij']],g['axis_i']+'-'+g['axis_j']))
for g in rd(D/'LOCAL_INTERACTION_DESIGN.json'):allgroups.append((g['anchor'],[int(np.flatnonzero(np.all(x==a,axis=1))[0]) for a in [g['anchor_D_nm']]+g['new_geometries']],'-'.join(map(str,g['axes']))))
fig,axs=plt.subplots(4,2,figsize=(7.20472440945,205/25.4),layout='constrained')
for row,(anchor,ix,axes) in enumerate(allgroups):
 ic=ct[ix[3]]-ct[ix[1]]-ct[ix[2]]+ct[ix[0]];ip=power[ix[3]]-power[ix[1]]-power[ix[2]]+power[ix[0]];axs[row,0].plot(w,np.linalg.norm(ic,axis=(1,2)),color='#4676A9',marker='.',ms=3);axs[row,1].plot(w,ip[:,4],color='#337E73',marker='.',ms=3)
 for col,label in [(0,'Complex interaction norm'),(1,'H2 P(+1) interaction')]:
  axs[row,col].axhline(0,color='.6',lw=.6);axs[row,col].set(xlabel='Wavelength (nm)',ylabel=label,xticks=[440,450,460]);axs[row,col].set_title(f'{anchor}, D{axes}'+(' (new, truth only)' if row>=2 else ' (retained truth)'),loc='left')
save(fig,'FOUR_CORNER_TRUTH_SPECTRA')
# Ranking is aggregate fold-wise rho; pooled points show calibration only.
fig,axs=plt.subplots(2,2,figsize=(7.20472440945,143/25.4),layout='constrained');foldcols=['#4676A9','#337E73','#BC8B54','#8C6BA9']
for row,n in enumerate([222,272]):
 pg=list(csv.DictReader((sources[n]/'PER_GEOMETRY_ERRORS.csv').open(encoding='utf-8')))
 for col,arch in enumerate(['A','B']):
  rr=[r for r in pg if r['model']==arch+'_ExtraTrees'];a=np.array([float(r['truth_Pplus450']) for r in rr]);b=np.array([float(r['pred_Pplus450']) for r in rr]);ax=axs[row,col];ax.scatter(a,b,c=[foldcols[int(r['fold'])-1] for r in rr],s=9,alpha=.75,rasterized=True);lim=max(a.max(),b.max())*1.04;ax.plot([0,lim],[0,lim],color='.5',ls=':',lw=.8);ax.set(xlim=(0,lim),ylim=(0,lim),xlabel='Truth H2 P(+1), 450 nm',ylabel='Predicted H2 P(+1), 450 nm');ax.set_title(f'{arch} ET, {n}G; mean-fold rho={metrics[n][arch+"_ExtraTrees"]["rho450_meanfold"]:.3f}',loc='left')
fig.legend(handles=[matplotlib.lines.Line2D([],[],marker='o',ls='',color=c,label=f'Fold {i+1}') for i,c in enumerate(foldcols)],loc='outside lower center',ncol=4,frameon=False);save(fig,'RANKING_AND_CALIBRATION')
# Best/median/worst selected by saved pergeometry error, never cherry-picked to claim aggregate skill.
pg=[r for r in csv.DictReader((D/'STAGE_50/PER_GEOMETRY_ERRORS.csv').open(encoding='utf-8')) if r['model']=='B_ExtraTrees'];pg.sort(key=lambda r:float(r['Pplus_MAE']));examples=[pg[0],pg[len(pg)//2],pg[-1]];pr=np.load(D/'STAGE_50/PREDICTIONS_B.npz');sys_path=R/'scripts/coupling_ml'
import sys
sys.path.insert(0,str(sys_path));from k6_v2_pipeline import h1 as H
dec=H.load_h2_decoder();fig,axs=plt.subplots(3,3,figsize=(7.20472440945,174/25.4),layout='constrained');example_rows=[]
for row,(tag,e) in enumerate(zip(['Best','Median','Worst'],examples)):
 i=ids.index(e['case_id']);fi=int(e['fold'])-1;c=pr['ExtraTrees_C_hat'][fi,i];p=pr['ExtraTrees_P_scale'][fi,i];h=H.reconstruct_h2(c,p,dec)
 for col,(truth,pred,label) in enumerate([(z['eta_H2'][i,:,4],h['eta'][0,:,4],'H2 eta(+1)'),(pt[i],p,'P_scale'),(power[i,:,4],h['absolute_order'][0,:,4],'H2 P(+1)')]):
  axs[row,col].plot(w,truth,color='#222222',lw=1.4,label='Truth');axs[row,col].plot(w,pred,color='#337E73',lw=1,ls='--',label='OOF B ET');axs[row,col].set(xlabel='Wavelength (nm)',ylabel=label,xticks=[440,450,460]);axs[row,col].set_title(f'{tag}: {e["case_id"]}',fontsize=7,loc='left')
  for k in range(21):example_rows.append({'selection':tag,'case_id':e['case_id'],'field':label,'wavelength_nm':440+k,'truth':float(truth[k]),'prediction':float(pred[k])})
fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False);save(fig,'SPECTRAL_BEST_MEDIAN_WORST')
with (F/'SPECTRAL_EXAMPLE_SOURCE.csv').open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(example_rows[0]));wr.writeheader();wr.writerows(example_rows)
cov=rd(D/'COVERAGE_CHANGE_PROSPECTIVE.json');fig,axs=plt.subplots(2,3,figsize=(7.20472440945,120/25.4),layout='constrained')
for k,ax in enumerate(axs.flat):
 for key,label,col,ls in [('before222_axis_counts','222G','#777777','--'),('prospective272_axis_counts','272G actual valid','#337E73','-')]:ax.plot(cov['levels_nm'],cov[key][k],color=col,ls=ls,marker='.',ms=3,label=label)
 ax.set(xlabel=f'D{k+1} (nm)',ylabel='Geometry count',xticks=[100,150,200,230]);ax.set_title(f'D{k+1}',loc='left')
fig.legend(*axs.flat[0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False);save(fig,'SIX_DIMENSION_COVERAGE')
(F/'RENDER_COMPLETE.json').write_text(json.dumps({'figures':7,'formats':['PDF','SVG','600dpiPNG'],'actual_data_only':True,'visual_QA':'PENDING','no_fits':True,'no_solver':True},indent=2));print('FIGURES_RENDERED',7)
