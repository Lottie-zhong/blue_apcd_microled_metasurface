"""Quantitative forensic panels, Python backend. Inputs are audited CSV files only."""
from pathlib import Path
import csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_V3_NUMERICAL_GATE_FAILURE_FORENSIC_V1')
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'xtick.labelsize':7,'ytick.labelsize':7,'legend.fontsize':7,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
data=list(csv.DictReader((O/'WAVELENGTH_ERROR.csv').open()));modes=list(csv.DictReader((O/'MODAL_AMPLITUDE_PHASE.csv').open()))
colors=['#0072B2','#D55E00']
fig,axs=plt.subplots(2,3,figsize=(7.2,4.5),layout='constrained')
items=[('state_relative_L2','State relative L2',.02),('routing_max_abs','Routing max abs',.005),('P_scale_relative','Power relative difference',.01),('absolute_order_max_abs','Absolute-order max abs',.005),('phase_weighted_rmse','Significant phase RMSE (rad)',.05),('post_flux_ratio_4_over_5','Raw flux ratio (4nm/5nm)',1)]
for i,(key,label,limit) in enumerate(items):
 ax=axs.flat[i]
 for a,c in zip(['A1','A2'],colors):
  rows=[r for r in data if r['anchor']==a];ax.plot([float(r['wavelength_nm']) for r in rows],[float(r[key]) for r in rows],label=a,color=c)
 ax.axhline(limit,color='#555555',linestyle='--',linewidth=.8,label='Frozen limit' if i<5 else 'Equal flux');ax.set(xlabel='Wavelength (nm)',ylabel=label);ax.set_title(chr(97+i),loc='left',fontweight='bold');ax.legend(frameon=False)
fig.savefig(O/'WAVELENGTH_COMPARISON.svg');fig.savefig(O/'WAVELENGTH_COMPARISON.pdf');fig.savefig(O/'WAVELENGTH_COMPARISON.png',dpi=600)
plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(7.2,4.7),layout='constrained')
for ai,a in enumerate(['A1','A2']):
 for pi,pol in enumerate(['TE','TM']):
  rows=[r for r in modes if r['anchor']==a and r['polarization']==pol];z=np.array([float(r['complex_sse']) for r in rows]).reshape(21,7).T;z/=sum(float(r['complex_sse']) for r in modes if r['anchor']==a)
  im=axs[ai,pi].imshow(z,aspect='auto',origin='lower',extent=[439.5,460.5,-3.5,3.5],cmap='cividis',vmin=0,vmax=(1.1e-8 if pol=='TE' else .14));axs[ai,pi].set(xlabel='Wavelength (nm)',ylabel='Order m',title=a+' '+pol+' | fraction of total SSE');fig.colorbar(im,ax=axs[ai,pi],label='SSE fraction per coordinate')
fig.savefig(O/'ORDER_POLARIZATION_ERROR.svg');fig.savefig(O/'ORDER_POLARIZATION_ERROR.pdf');fig.savefig(O/'ORDER_POLARIZATION_ERROR.png',dpi=600)
plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(7.2,4.7),layout='constrained')
for ai,a in enumerate(['A1','A2']):
 for m,style in [(1,'-'),(2,'--'),(-3,':')]:
  rows=[r for r in modes if r['anchor']==a and r['polarization']=='TM' and int(r['m'])==m];wl=np.array([float(r['wavelength_nm']) for r in rows]);axs[ai,0].plot(wl,[float(r['amplitude_5nm']) for r in rows],color=colors[0],linestyle=style,label='5 nm, m='+str(m));axs[ai,0].plot(wl,[float(r['amplitude_4nm']) for r in rows],color=colors[1],linestyle=style,label='4 nm, m='+str(m));axs[ai,1].plot(wl,[float(r['phase_difference_rad']) for r in rows],linestyle=style,label='m='+str(m))
 axs[ai,0].set(xlabel='Wavelength (nm)',ylabel='C_hat amplitude',title=a+' TM amplitude');axs[ai,1].set(xlabel='Wavelength (nm)',ylabel='Wrapped phase difference (rad)',title=a+' TM phase (no alignment)')
 axs[ai,1].legend(frameon=False,ncol=3,loc='upper right')
handles,labels=axs[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=3,frameon=False)
fig.savefig(O/'COMPLEX_AMPLITUDE_PHASE.svg');fig.savefig(O/'COMPLEX_AMPLITUDE_PHASE.pdf');fig.savefig(O/'COMPLEX_AMPLITUDE_PHASE.png',dpi=600)
plt.close(fig)
(O/'FIGURE_QA.md').write_text('# Figure QA\n\nPython-only backend; raw 21-wavelength paired records, no confidence intervals or independent-sample claims. Two physical anchor pairs. No smoothing, phase alignment, data exclusion, log color scale, or image manipulation. Source: WAVELENGTH_ERROR.csv and MODAL_AMPLITUDE_PHASE.csv. TE/TM panels use separate linear scales and show SSE fractions explicitly; weak TE must not be compared by color intensity to dominant TM. Amplitude panel selects m=+1,+2,-3 for readability; full seven-order TE/TM data retained in CSV and heatmap. SVG/PDF editable text, 600dpi PNG preview.\n')
print('FIGURES_READY')
