"""Quantitative report figures, Python only; no labels rescaled for presentation."""
from pathlib import Path
import json,csv,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_272G_PSCALE_DECOUPLING_V1');B=D.parent/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';out=D/'FIGURES';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False})
def read(n):return list(csv.DictReader((D/n).open(encoding='utf-8')))
def export(fig,name):
 fig.savefig(out/(name+'.pdf'));fig.savefig(out/(name+'.svg'));fig.savefig(out/(name+'.png'),dpi=600);fig.savefig(out/(name+'_preview.png'),dpi=300);plt.close(fig)
names=['NN3_Joint','NN3_PSNet','NN3_ET3','NN3_Leaf1','NN3_Ridge','NN3_PMean'];labels=['Joint','PNet','ET3 P','Leaf1 P','Ridge P','Mean P'];colors=['#376E9D','#D17C3F','#59896F','#777777','#9A79A7','#A68B58'];fold=read('MODEL_FOLD_METRICS.csv');oracle=read('ORACLE_FOLD_METRICS.csv');pr=read('PSCALE_WAVELENGTH_DIAGNOSTIC.csv');cancel=read('ERROR_CANCELLATION.csv')
fig,ax=plt.subplots(2,2,figsize=(7.20472440945,5.8));fig.subplots_adjust(left=.095,right=.985,bottom=.12,top=.94,wspace=.34,hspace=.5)
for a,key,title,ylabel in [(ax[0,0],'Pplus_MAE','a  Combined-model power error','P(+1) MAE'),(ax[0,1],'P_scale_MAE','b  P_scale model error','P_scale MAE')]:
 for f in range(1,5):
  yy=[float(next(r for r in fold if r['model']==n and int(r['fold'])==f)[key]) for n in names];a.plot(range(6),yy,'o-',ms=3,lw=.8,label=f'Fold {f}')
 a.set_xticks(range(6),labels,rotation=25,ha='right',rotation_mode='anchor');a.set_ylabel(ylabel);a.set_title(title,loc='left');a.set_ylim(bottom=0)
ax[0,0].legend(ncol=2)
for k,name in enumerate(['NN2','NN3','Leaf1']):
 yy=[];lower=[];upper=[]
 for suffix in ['A_TRUE','B_C_ONLY','C_P_ONLY','D_BOTH']:
  rr=[r for r in oracle if r['model']==name+'_'+suffix];yy.append(sum(float(r['Pplus_MAE'])*int(r['n']) for r in rr)/124);lower.append(yy[-1]-min(float(r['Pplus_MAE']) for r in rr));upper.append(max(float(r['Pplus_MAE']) for r in rr)-yy[-1])
 ax[1,0].errorbar(range(4),yy,yerr=np.array([lower,upper]),fmt='o-',label=name,lw=1,ms=3,capsize=2)
ax[1,0].set_xticks(range(4),['True/True','Pred C only','Pred P only','Both'],rotation=20,ha='right',rotation_mode='anchor');ax[1,0].set_ylabel('P(+1) MAE');ax[1,0].set_title('c  Frozen-H2 Oracle (fold range)',loc='left');ax[1,0].legend()
for n,col in zip(['Joint','PSNet','ET3'],colors[:3]):
 rr=[r for r in pr if r['model']==n];waves=sorted(set(int(r['wavelength_nm']) for r in rr));yy=[sum(float(r['bias'])*int(r['n']) for r in rr if int(r['wavelength_nm'])==w)/124 for w in waves];lo=[min(float(r['bias']) for r in rr if int(r['wavelength_nm'])==w) for w in waves];hi=[max(float(r['bias']) for r in rr if int(r['wavelength_nm'])==w) for w in waves];ax[1,1].fill_between(waves,lo,hi,color=col,alpha=.12,lw=0);ax[1,1].plot(waves,yy,label=n,color=col,lw=1.3)
ax[1,1].axhline(0,color='.6',lw=.7,ls='--');ax[1,1].set_xlabel('Wavelength (nm)');ax[1,1].set_ylabel('P_scale signed bias');ax[1,1].set_title('d  Wavelength-dependent bias',loc='left');ax[1,1].legend()
export(fig,'PSCALE_DECOUPLING_OVERVIEW')
z=np.load(B/'COMPLEX_DATASET.npz');ix={s:i for i,s in enumerate(z['case_ids'])};joint=np.load(D/'NN3_Joint_OOF.npz');pnet=np.load(D/'NN3_PSNet_OOF.npz');et=np.load(D/'NN3_ET3_OOF.npz');va=np.array([ix[s] for s in joint['case_ids']]);error=abs(joint['P']-z['P_scale'][va]).mean(1);order=np.argsort(error);selected=[order[0],order[len(order)//2],order[-1]];wl=z['wavelengths_nm'];roles=['Lowest','Median','Highest'];source=[]
fig,ax=plt.subplots(3,2,figsize=(7.20472440945,7.3));fig.subplots_adjust(left=.095,right=.985,bottom=.08,top=.91,wspace=.28,hspace=.58)
for row,j in enumerate(selected):
 i=va[j];title=f'{roles[row]} joint P_scale MAE: {joint["case_ids"][j]}'
 for col,truth,key,ylabel in [(0,z['P_scale'][i],'P','P_scale'),(1,z['absolute_H2'][i,:,4],'absolute','P(+1)')]:
  a=ax[row,col];a.plot(wl,truth,color='.15',lw=1.6,label='Truth')
  for n,data,c in [('Joint',joint,colors[0]),('PNet',pnet,colors[1]),('ET3 P',et,colors[2])]:a.plot(wl,data[key][j] if key=='P' else data[key][j,:,4],color=c,lw=1.2,label=n)
  a.set_title(f'{chr(97+2*row+col)}  {title}',loc='left',fontsize=7);a.set_xlabel('Wavelength (nm)');a.set_ylabel(ylabel);a.set_ylim(bottom=0)
 for l,w in enumerate(wl):source.append({'role':roles[row],'case_id':str(joint['case_ids'][j]),'wavelength_nm':int(w),'P_true':float(z['P_scale'][i,l]),'P_joint':float(joint['P'][j,l]),'P_PNet':float(pnet['P'][j,l]),'P_ET3':float(et['P'][j,l]),'order_power_true':float(z['absolute_H2'][i,l,4]),'order_power_joint':float(joint['absolute'][j,l,4]),'order_power_PNet':float(pnet['absolute'][j,l,4]),'order_power_ET3':float(et['absolute'][j,l,4])})
fig.legend(*ax[0,0].get_legend_handles_labels(),loc='upper center',ncol=4,bbox_to_anchor=(.5,.98));export(fig,'PSCALE_AND_POWER_SPECTRA')
with (out/'SPECTRA_SOURCE_DATA.csv').open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=list(source[0]));wr.writeheader();wr.writerows(source)
(out/'FIGURE_CONTRACT.json').write_text(json.dumps({'backend':'python','archetype':'quantitative grid','width_mm':183,'claim':'P_scale and modal errors must be separated; a lower combined MAE does not by itself prove each factor improves','evidence':'4 original folds,124 primary geometries, frozenH2; Oracle panel labeled; spectra chosen lowest/median/highest NN3 PscaleMAE without exclusion','uncertainty':'a/b each fixed fold line; c geometry-weighted mean with fold min-max bars; d geometry-weighted mean with fold min-max band; no CI claim or independent wavelength/seed replicates; individual spectra have no replicate bands','export':['PDF editable','SVG editable','PNG600dpi','preview300dpi'],'no_journal_submission_claim':True},indent=2))
print('FIGURES_COMPLETE')
