"""Python-only source-data figures for complex609D diagnostic; no fits or solves."""
from pathlib import Path
import json,csv,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');D=R/'reports/coupling/APCD_COUPLING_609D_COMPLEX_FORWARD_DIAGNOSTIC_V1';F=D/'figures';rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
KINDS=['Mean','KRR','ExtraTrees'];COL=['#777777','#4676A9','#337E73'];KEYS=[a+'_'+k for a in ['A','B'] for k in KINDS]
def save(fig,name):
 fig.savefig(F/(name+'.pdf'));fig.savefig(F/(name+'.svg'));fig.savefig(F/(name+'.png'),dpi=600);plt.close(fig)
def main():
 assert (D/'ANALYSIS_COMPLETE.json').exists();F.mkdir(exist_ok=True);m=rd(D/'METRICS_FIXED124.json');constant=rd(D/'OUTPUT_DOMAIN_CONSTANT_BASELINE.json');ch=list(csv.DictReader((D/'PER_CHANNEL_ERRORS.csv').open(encoding='utf-8')));wl=list(csv.DictReader((D/'PER_WAVELENGTH_ERRORS.csv').open(encoding='utf-8')));local=rd(D/'LOCAL_PREDICTION_METRICS.json')
 (F/'FIGURE_CONTRACT.json').write_text(json.dumps({'claim':'Compare official whole609 and wavelength29 learning; preserve complex errors, dark-channel phase coverage and weak decoded ranking','archetype':'quantitative grid','backend':'Python','width_mm':183,'font_pt':8,'primary_n':124,'folds':4,'ET_seeds':3,'local_edges':23,'local_predictive_edges':10,'independent_local_test_families':1,'statistics':'fixed geometry OOF aggregates, no independent wavelength replicates; main comparison errorbars=fourfold range, notCI; one-family local panels have no independent-family variance estimate; no significance claims','weak_phase':'truthrelative amplitude floor.001, sensitivity.01/.05; undefined dark phase shownNA','no_smoothing_or_excluded_geometries':True},indent=2),encoding='utf-8')
 # Six different units: no composite score or misleading shared y-axis.
 fig,axs=plt.subplots(2,3,figsize=(7.20472440945,119/25.4),layout='constrained');fields=['state_relative_RMSE','magnitude_RMSE','phase_deg','relative_phase_MAE_deg','P_scale_MAE','Pplus_MAE'];labels=['Complex relative RMSE','Magnitude RMSE','Absolute phase MAE (deg)','Relative phase MAE (deg)','P_scale MAE','H2 P(+1) MAE']
 for j,(field,label) in enumerate(zip(fields,labels)):
  ax=axs.flat[j]
  for k,arch in enumerate(['A','B']):
   vals=[m[arch+'_'+kind]['phase']['MAE_deg'] if field=='phase_deg' else m[arch+'_'+kind][field] for kind in KINDS];bounds=[(max(0,v-min(r[field] for r in m[arch+'_'+kind]['fold_metrics'])),max(0,max(r[field] for r in m[arch+'_'+kind]['fold_metrics'])-v)) for kind,v in zip(KINDS,vals)];ax.bar(np.arange(3)+(k-.5)*.34,vals,width=.32,color=COL,alpha=.45 if arch=='A' else 1,edgecolor=COL,hatch='//' if arch=='A' else None,yerr=np.array(bounds).T,capsize=2,error_kw={'elinewidth':.65})
  ax.set(xticks=range(3),xticklabels=['Complex Mean','KRR','ExtraTrees'],ylabel=label);ax.set_title(chr(97+j),loc='left')
  if field in ['P_scale_MAE','Pplus_MAE']:ax.axhline(constant[field],color='.2',ls=':',lw=.8)
  for tick in ax.get_xticklabels():tick.set_rotation(25);tick.set_rotation_mode('anchor');tick.set_ha('right')
 fig.legend(handles=[plt.Rectangle((0,0),1,1,fc='.7',hatch='//',label='A: geometry -> 609D'),plt.Rectangle((0,0),1,1,fc='.4',label='B: geometry + wavelength -> 29D'),Line2D([],[],color='.2',ls=':',label='Output-domain constant Mean: reference only')],loc='outside lower center',ncol=1,frameon=False);save(fig,'STRUCTURE_A_B_COMPARISON')
 # All14channels andall6models. Dark/undefined phase is explicitly NA, never zero.
 fig,axs=plt.subplots(2,2,figsize=(7.20472440945,137/25.4),layout='constrained');channel_labels=[str(i)+' '+p for i in range(-3,4) for p in ['T','M']]
 for j,(field,title) in enumerate([('real_RMSE','Real-part RMSE'),('imag_RMSE','Imaginary-part RMSE'),('magnitude_RMSE','Magnitude RMSE'),('phase_MAE_deg','Phase MAE (deg), dark = NA')]):
  a=np.array([[float(next(r[field] for r in ch if r['model']==key and int(r['order'])==k//2-3 and r['polarization']==['TE','TM'][k%2]) or 'nan') for k in range(14)] for key in KEYS]);ax=axs.flat[j];cmap=plt.get_cmap('cividis').copy();cmap.set_bad('#eeeeee');im=ax.imshow(np.ma.masked_invalid(a),aspect='auto',cmap=cmap,vmin=0);ax.set(yticks=range(6),yticklabels=[k.replace('ExtraTrees','ET') for k in KEYS],xticks=range(14),xticklabels=channel_labels,xlabel='Order m; T = TE, M = TM');ax.set_title(title,loc='left');fig.colorbar(im,ax=ax,shrink=.8)
  for tick in ax.get_xticklabels():tick.set_rotation(60);tick.set_rotation_mode('anchor');tick.set_ha('right')
  for r,c in zip(*np.where(~np.isfinite(a))):ax.text(c,r,'NA',ha='center',va='center',fontsize=6)
 save(fig,'ALL_ORDER_CHANNEL_ERRORS')
 fig,axs=plt.subplots(2,2,figsize=(7.20472440945,116/25.4),layout='constrained')
 for j,(field,label) in enumerate([('complex_RMSE','Complex RMSE'),('P_scale_MAE','P_scale MAE'),('eta_plus1_MAE','H2 eta(+1) MAE'),('Pplus_MAE','H2 P(+1) MAE')]):
  for kind,col in zip(KINDS,COL):
   for arch,ls in [('A','--'),('B','-')]:
    if arch=='B' and kind=='Mean':continue
    rr=[r for r in wl if r['model']==arch+'_'+kind];axs.flat[j].plot([float(r['wavelength_nm']) for r in rr],[float(r[field]) for r in rr],color=col,ls=ls,lw=1,label=kind+' '+arch)
  axs.flat[j].set(xlabel='Wavelength (nm)',ylabel=label,xticks=[440,450,460]);axs.flat[j].set_title(chr(97+j),loc='left')
 fig.legend(*axs.flat[0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False);save(fig,'SPECTRAL_ERROR_DISTRIBUTION')
 fig,axs=plt.subplots(1,3,figsize=(7.20472440945,91/25.4),layout='constrained')
 for j,(field,label) in enumerate([('delta_complex_relative_RMSE','Delta complex relative RMSE'),('delta_magnitude_relative_RMSE','Delta magnitude relative RMSE'),('relative_phase_delta_MAE_deg','Delta relative-phase MAE (deg)')]):
  for a,arch in enumerate(['A','B']):
   vals=[local[arch+'_'+kind][field] for kind in KINDS];axs[j].bar(np.arange(3)+(a-.5)*.34,vals,width=.32,color=COL,alpha=.45 if arch=='A' else 1,hatch='//' if arch=='A' else None)
  axs[j].set(xticks=range(3),xticklabels=['Complex Mean','KRR','ExtraTrees'],ylabel=label);axs[j].set_title('G059: 10 edges, one family',loc='left')
  if j<2:axs[j].axhline(1,color='.4',ls=':',lw=.8)
  for tick in axs[j].get_xticklabels():tick.set_rotation(25);tick.set_rotation_mode('anchor');tick.set_ha('right')
 fig.legend(handles=[plt.Rectangle((0,0),1,1,fc='.7',hatch='//',label='Structure A'),plt.Rectangle((0,0),1,1,fc='.4',label='Structure B'),Line2D([],[],color='.4',ls=':',label='Zero-delta relative RMSE = 1')],loc='outside lower center',ncol=2,frameon=False);save(fig,'LOCAL_COMPLEX_PREDICTION')
 # Fixed target+1TM channel forreadableinteraction; all14channelsprovided inNPZ andCSV.
 figs=rd(D/'DOUBLE_PILLAR_COMPLEX_INTERACTION.json');fig,axs=plt.subplots(2,2,figsize=(7.20472440945,113/25.4),layout='constrained');data=np.load(D/'COMPLEX_DATASET_222G.npz',allow_pickle=False);ids=list(data['case_ids']);groups=list(csv.DictReader((R/'reports/coupling/APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2/AL50_INTERACTION_GROUPS.csv').open(encoding='utf-8')))
 for row,g in enumerate(groups):
  truth=np.load(D/(g['group_id']+'_COMPLEX_TRUTH.npz'),allow_pickle=False)['I_C_hat'][:,4,1];ix=[ids.index(g[n]) for n in ['D','D_i','D_j','D_ij']]
  for col,component in enumerate(['real','imag']):
   ax=axs[row,col];ax.plot(range(440,461),getattr(truth,component),color='#222222',lw=1.5,label='Saved truth')
   if row==0:
    for kind,color in zip(KINDS[1:],COL[1:]):
     for arch,ls in [('A','--'),('B','-')]:
      p=np.load(D/('PREDICTIONS_'+arch+'.npz'),allow_pickle=False)[kind+'_C_hat'][2];ii=p[ix[3]]-p[ix[1]]-p[ix[2]]+p[ix[0]];ax.plot(range(440,461),getattr(ii[:,4,1],component),color=color,ls=ls,lw=.9,label=kind+' '+arch)
   ax.axhline(0,color='.7',lw=.6);ax.set(xlabel='Wavelength (nm)',ylabel=component.capitalize()+' I(C_hat), +1 TM',xticks=[440,450,460]);ax.set_title('G059 D2-D3, family held out' if row==0 else 'S31 D6-D1, truth only',loc='left');ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False);save(fig,'DOUBLE_PILLAR_COMPLEX_INTERACTION')
 rows=list(csv.DictReader((D/'PER_GEOMETRY_ERRORS.csv').open(encoding='utf-8')));fig,axs=plt.subplots(2,3,figsize=(7.20472440945,123/25.4),layout='constrained')
 for ax,key,col in zip(axs.flat,KEYS,COL*2):
  rr=[r for r in rows if r['model']==key];assert len(rr)==124;a=np.array([float(r['truth_Pplus450']) for r in rr]);b=np.array([float(r['pred_Pplus450']) for r in rr]);ax.scatter(a,b,s=9,color=col,alpha=.65);lim=[min(a.min(),b.min()),max(a.max(),b.max())];ax.plot(lim,lim,color='.5',ls=':',lw=.7);r=m[key]['rho450_meanfold'];ax.set_title(key.replace('ExtraTrees','ET').replace('Mean','Complex Mean')+', rho='+('NA' if r is None else format(r,'.3f')),loc='left');ax.set(xlabel='True H2 P(+1), 450 nm',ylabel='OOF H2 prediction')
 save(fig,'H2_DECODED_RANKING')
 print('COMPLEX609_FIGURES_RENDERED',6)
if __name__=='__main__':main()
