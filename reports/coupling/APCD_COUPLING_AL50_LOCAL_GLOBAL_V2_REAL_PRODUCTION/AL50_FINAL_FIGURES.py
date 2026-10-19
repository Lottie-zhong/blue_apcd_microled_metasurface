"""Plots only saved AL50 truth/OOF; never generates data or calls a solver."""
from pathlib import Path
import json,csv,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';S=D/'STAGE_50';F=D/'figures';read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7})
COLORS={'Mean':'#747474','KRR':'#4676A9','ExtraTrees':'#337E73','MLP':'#B87943'}
AXISC=['#4676A9','#337E73','#B87943','#8B6DA4','#B86274','#75843B']
def save(fig,name):
 for ext in ['svg','pdf','png']:fig.savefig(F/(name+'.'+ext),dpi=300)
 plt.close(fig)
def main():
 assert read(S/'STAGE_COMPLETE.json')['stage_new_valid']==50;F.mkdir(exist_ok=True)
 contract={'core_claim':'ObservedFASTlocalresponsesandinteractiontruthplusmatched-familyguardedlearningchanges; not assumebenefit oruniquenearfieldcause','archetype':'quantitativegrid','backend':'Pythonmatplotlib','final_width_mm':183,'glyph_floor_pt':5,'font_pt':8,'outputs':['editableSVG','PDF','PNGpreview'],'source':'savedSTAGE16/32/50JSONandCSVonly, no smoothed/interpolated/excludedrows','stats':'21lambda are not independentreplicates;2anchortruthfamilies,1eligibleheldoutlocalfamily;learningerrorbarsrangeoffourfixedfolds, notCI;seedensemblesaveraged','panels':['all23localedges,twofamilies,threeoutputs','twofourcornerinteractiongroups,threeoutputs','primary124fixedholdoutlearningmetrics,stage0/16/32/50'],'numerical_reference':'A1timechanges are differentgeometryreference, notuncertaintyband'};(F/'FIGURE_CONTRACT.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
 rows=list(csv.DictReader((S/'LOCAL_RESPONSE_SPECTRA.csv').open(encoding='utf-8')));edge=list(csv.DictReader((B/'AL50_LOCAL_PAIR_GRAPH.csv').open(encoding='utf-8')));families=read(B/'LOCAL_FAMILY_COMPONENTS.json');gf=next(set(v) for v in families if 'K6GDP2_DEV_G059' in v);sf=next(set(v) for v in families if 'K6V1_S31' in v);labels={'P_plus1_H2':'Delta P(+1), H2','eta':'Delta eta(+1), native','P_scale':'Delta P_scale'};targets=list(labels);fig,axs=plt.subplots(2,3,figsize=(183/25.4,125/25.4),layout='constrained')
 for r,(family,root) in enumerate([(gf,'G059'),(sf,'S31')]):
  selected=[e for e in edge if e['case_low'] in family and e['case_high'] in family]
  for c,t in enumerate(targets):
   ax=axs[r,c]
   for e in selected:
    rr=[v for v in rows if v['pair_id']==e['pair_id'] and v['target']==t];assert len(rr)==21
    conditional='I00' in e['case_low'] or 'I00' in e['case_high'];ax.plot([float(v['wavelength_nm']) for v in rr],[float(v['delta']) for v in rr],color=AXISC[int(e['axis'])-1],lw=.8,ls='--' if conditional else '-',alpha=.85)
   ax.axhline(0,color='.65',lw=.6);ax.set(xlabel='Wavelength (nm)',ylabel=labels[t]);ax.set_title(f'{chr(97+r*3+c)}  {root}, {len(selected)} edges',loc='left');ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2));ax.set_xticks([440,450,460])
 handles=[plt.Line2D([],[],color=AXISC[k],label=f'D{k+1} +5 nm') for k in range(6)];fig.legend(handles=handles,loc='outside lower center',ncol=3,frameon=False);save(fig,'LOCAL_RESPONSE_SPECTRA')
 groups=read(S/'INTERACTION_TRUTH_AND_PREDICTION.json');assert len(groups)==2 and all(g['complete_truth'] for g in groups);fig,axs=plt.subplots(2,3,figsize=(183/25.4,115/25.4),layout='constrained')
 for r,g in enumerate(groups):
  for c,t in enumerate(targets):
   ax=axs[r,c];v=g['targets'][t];ax.plot(range(440,461),v['I_21'],color='#4676A9',lw=1.5,label='Full-wave interaction')
   if isinstance(v['prediction_errors'],dict):ax.plot(range(440,461),v['prediction_errors']['ALL_V2_AVAILABLE']['ExtraTrees']['Ihat_21'],color='#B87943',ls='--',lw=1,label='ExtraTrees, family held out')
   ax.axhline(0,color='.65',lw=.6);ax.set(xlabel='Wavelength (nm)',ylabel='Interaction '+t.replace('_H2',''));ax.set_title(f'{chr(97+r*3+c)}  '+('G059: D2-D3' if r==0 else 'S31: D6-D1 (truth only)'),loc='left');ax.set_xticks([440,450,460]);ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
 handles=[plt.Line2D([],[],color='#4676A9',label='Full-wave interaction'),plt.Line2D([],[],color='#B87943',ls='--',label='ExtraTrees: G059 held-out family')];fig.legend(handles=handles,loc='outside lower center',ncol=1,frameon=False);save(fig,'DOUBLE_PILLAR_INTERACTION_SPECTRA')
 # Primarypooledold124MAEmarkers withrangeofsamefourfolds (not confidenceintervals).
 base=np.load(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FAST_DATASET_172G.npz',allow_pickle=False);idx={str(cid):i for i,cid in enumerate(base['case_ids'])};folds=read(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');foldix=[np.array([idx[cid] for cid in f['heldout_old_ids']]) for f in folds];T={'P_plus1_H2':base['P_plus1_H2'],'eta':base['eta'],'P_scale':base['P_scale']};fig,axs=plt.subplots(2,2,figsize=(183/25.4,122/25.4),layout='constrained');plotdata=[]
 for k,color in COLORS.items():
  for panel,t in enumerate(['P_plus1_H2','eta','P_scale','rho']):
   xx=[];yy=[];lo=[];hi=[]
   for stage in [0,16,32,50]:
    stagefolder=D/f'STAGE_{16 if stage==0 else stage:02d}';metrics=read(stagefolder/'MODEL_METRICS_SAME124.json');name='MATCHED_172_BASELINE' if stage==0 else 'ALL_V2_AVAILABLE';metric=metrics[name][k];path=D/'FAMILY_GUARDED_172_BASELINE/PREDICTIONS_BY_FOLD.npz' if stage==0 else stagefolder/'ALL_V2_AVAILABLE_PREDICTIONS_BY_FOLD_CHECKPOINT.npz';p=np.load(path,allow_pickle=False)[k];values=[]
    for f,vi in enumerate(foldix):
     if t=='rho':
      pred=p[f,vi,10]*np.exp(p[f,vi,31]);rval=None if np.std(pred)<1e-14 else float(spearmanr(T['P_plus1_H2'][vi,10],pred).statistic)
      if rval is not None:values.append(rval)
     else:
      pred=p[f,vi,:21] if t=='eta' else np.exp(p[f,vi,21:]) if t=='P_scale' else p[f,vi,:21]*np.exp(p[f,vi,21:]);values.append(float(abs(pred-T[t][vi]).mean()))
    value=metric['450nm_Pplus_mean_fold_Spearman'] if t=='rho' else metric[t]['MAE']
    if value is None:continue
    assert values and min(values)-1e-12<=value<=max(values)+1e-12
    xx.append(stage);yy.append(value);lo.append(max(0,value-min(values)));hi.append(max(0,max(values)-value));plotdata.append({'model':k,'new_valid':stage,'target':t,'pooled_MAE_or_meanfold_rho':value,'fold_min':min(values),'fold_max':max(values)})
   axs.flat[panel].errorbar(xx,yy,yerr=[lo,hi],color=color,marker='o',ms=3,lw=1.1,elinewidth=.55,capsize=2,label=k)
 for i,ax in enumerate(axs.flat):
  ax.set(xlabel='New labels-valid geometries',ylabel=['P(+1) spectral MAE','eta(+1) spectral MAE','P_scale spectral MAE','450 nm mean-fold Spearman'][i]);ax.set_title(chr(97+i),loc='left');ax.set_xticks([0,16,32,50])
  if i==3:ax.axhline(0,color='.65',lw=.7)
 handles=[plt.Line2D([],[],color=c,marker='o',label=k) for k,c in COLORS.items()];fig.legend(handles=handles,loc='outside lower center',ncol=4,frameon=False);save(fig,'MODEL_LEARNING_CURVES_FIXED124')
 with (F/'LEARNING_CURVE_SOURCE.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(plotdata[0]));w.writeheader();w.writerows(plotdata)
 (F/'FIGURE_QA_NOTES.md').write_text('''# Figure QA notes

Pythonmatplotlibonly; editableSVG/PDF +PNG. 183mmwide,8ptalltext, no smoothing or dataexclusions. All23localedgesshown,21wavelengthseach, groupedtwoanchorrows; dashed conditionaledges differfromsingleaxisanchorarms. PositiveDelta refers diameterincreasing5nm alonglistededge, includingminus→anchor edges. Twointeractiontruthgroups;S31notheldoutmodeltest. Modelcurvesprimary124fixedholdouts,family-purgedmatchedbaseline. Errorbarsrangeacrossfourfixedfolds, NOT confidenceinterval;Meanrankundefinedexcludedonlyrankingpanel. ThreeensembleseedpredictionsaveragedinET/MLP. Onlyoneeligiblelocalheldoutfamily, noindependentλreplicates orstatisticalnoiseclaim. Nonadditivitynotuniquenearfieldmechanism. Automatedsource/PDFaudit+visualinspectiontobeperformedbeforefinaldelivery.
''',encoding='utf-8')
 print('FIGURES_RENDERED',3)
if __name__=='__main__':main()
