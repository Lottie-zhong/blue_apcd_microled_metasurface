"""Zero-solver final scientific audit, existing-prediction plots, one missing matched156 reference."""
import os
for key in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[key]='2'
from pathlib import Path
import json,csv,time,warnings,importlib.util,sqlite3,subprocess
import numpy as np
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_AL50_LOCAL_GLOBAL_V2_REAL_PRODUCTION';S=D/'STAGE_50';B=Q/'APCD_COUPLING_AL50_INCREMENTAL_LOCAL_REDESIGN_V2';A=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE';C=Q/'APCD_COUPLING_AL50_V2_FINAL_SCIENTIFIC_CLOSEOUT';F=C/'figures';P=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3')
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(name,v):
 p=C/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
def csvout(name,rows):
 with (C/name).open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def rho(a,b):return None if np.std(a)<1e-14 or np.std(b)<1e-14 else float(spearmanr(a,b).statistic)
def decode(z):return {'eta':z[...,:21],'P_scale':np.exp(z[...,21:]),'P_plus1_H2':z[...,:21]*np.exp(z[...,21:])}
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=600)
 fig.savefig(F/(name+'.pdf'))
 fig.savefig(F/(name+'.svg'))
 plt.close(fig)
def main():
 C.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
 baseline_git={}
 for k,args in [('status',['status','--short']),('staged',['diff','--cached','--name-only']),('HEAD',['rev-parse','HEAD']),('branch',['branch','--show-current']),('ahead_behind',['rev-list','--left-right','--count','HEAD...@{u}'])]:baseline_git[k]=subprocess.run(['git','-C',str(R),*args],capture_output=True,text=True).stdout
 if not (C/'GIT_BASELINE.json').exists():put('GIT_BASELINE.json',baseline_git)
 ledger=rd(D/'AL50_SCIENCE_LEDGER.json');assert ledger['entered']==ledger['labels_valid']==50 and ledger['replay_count']==0
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);con.row_factory=sqlite3.Row;caseids=set(ledger['cases']);entries=[dict(v) for v in con.execute('select * from solver_entries') if v['case_id'] in caseids];count_before=con.execute('select count(*) from solver_entries').fetchone()[0];con.close();assert len(entries)==len({e['external_execution_id'] for e in entries})==50
 z=np.load(S/'FAST_DATASET_222G.npz',allow_pickle=False);ids=list(z['case_ids']);x=z['D_nm'];T={t:z[t] for t in ['eta','P_scale','P_plus1_H2']};assert np.all(T['P_scale'] > 0), 'P_scale must be strictly positive before log';idx={cid:i for i,cid in enumerate(ids)};folds=rd(A/'FOLDS.json');fixed=np.array([idx[c] for f in folds for c in f['heldout_old_ids']]);assert len(fixed)==len(set(fixed))==124
 foldfor={c:f['fold'] for f in folds for c in f['heldout_old_ids']+f['heldout_new_ids']};families=rd(B/'LOCAL_FAMILY_COMPONENTS.json');gf=next(set(v) for v in families if 'K6GDP2_DEV_G059' in v);sf=next(set(v) for v in families if 'K6V1_S31' in v)
 kinds=['Mean','KRR','ExtraTrees','MLP'];colors=['#777777','#4676A9','#337E73','#B87943'];views={n:{k:np.load(S/(n+'_PREDICTIONS_BY_FOLD_CHECKPOINT.npz'),allow_pickle=False)[k] for k in kinds} for n in ['ALL_V2_AVAILABLE','GLOBAL_ONLY_ABLATION','MATCHED_40_ACQUISITIONS_MIXED']};base={k:np.load(D/'FAMILY_GUARDED_172_BASELINE/PREDICTIONS_BY_FOLD.npz',allow_pickle=False)[k] for k in kinds};allp=views['ALL_V2_AVAILABLE']
 policy=[]
 for name in views:
  fs=rd(S/(name+'_FOLDS.json'))
  for f in fs:
   tr=set(f['train_ids']);va=set(f['heldout_ids']);assert not(tr&va) and not any(tr&set(g) and va&set(g) for g in families)
   policy.append({'view':name,'fold':f['fold'],'train_count':len(tr),'heldout_count':len(va),'local_training_ids':[v for v in sorted(tr) if 'R02V2' in v],'purged_count':len(f['purged_ids']),'family_overlap':0})
 put('EVALUATION_FAMILY_AUDIT.json',policy)
 # Missing comparable156 reference only: same factory, fixed hyperparameters, seeds, val IDs, family purge; never repeat prior fits.
 p156=C/'MATCHED_156_PREDICTIONS.npz';spec=importlib.util.spec_from_file_location('frozen_models',R/'scripts/coupling_ml/gpu_active_learning_mainline_v1.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
 if not p156.exists():
  assert not (C/'MATCHED_156_FIT_LEDGER.json').exists(),'partial fit ledger: inspect before resuming, no blind refit'
  refs=rd(D/'STAGE_16/MATCHED_172_BASELINE_FOLDS.json');y=np.c_[T['eta'],np.log(T['P_scale'])];out={k:np.zeros((4,222,42)) for k in kinds};fits=[];note=[];old156=set(ids[:156]);specs=[('Mean',17),('KRR',17)]+[(k,s) for k in ['ExtraTrees','MLP'] for s in [17,29,43]]
  put('MATCHED_156_FIT_PREREGISTRATION.json',{'fits':32,'reason':'missing family-purged156 reference required for comparable156/172/222 curve; existing172/222 models reused','factory':'frozen original make(); no tuning','new_solver':0})
  for f in refs:
   ti=np.array([idx[c] for c in f['train_ids'] if c in old156]);tr={ids[i] for i in ti};va=set(f['heldout_ids']);assert not any(tr&set(g) and va&set(g) for g in families);note.append({'fold':f['fold'],'train_ids':sorted(tr),'heldout_old124_ids':[c for c in va if idx[c] in set(fixed)]});est={}
   for k,seed in specs:
    row={'fold':f['fold'],'model':k,'seed':seed,'state':'STARTED'};fits.append(row);put('MATCHED_156_FIT_LEDGER.json',fits);model=M.make(k,seed);tick=time.perf_counter()
    with warnings.catch_warnings(record=True) as ws:warnings.simplefilter('always');model.fit(x[ti],y[ti])
    row.update(state='COMPLETE',seconds=time.perf_counter()-tick,warnings=[str(w.message) for w in ws]);put('MATCHED_156_FIT_LEDGER.json',fits);est.setdefault(k,[]).append(model.predict(x))
   for k,v in est.items():out[k][f['fold']-1]=np.mean(v,axis=0)
  np.savez_compressed(p156,case_ids=np.array(ids),**out);put('MATCHED_156_FOLDS.json',note)
 ref156={k:np.load(p156,allow_pickle=False)[k] for k in kinds}
 def oof(p,indices=fixed):return np.array([p[foldfor[ids[i]]-1,i] for i in indices])
 def metrics(p):
  res={}
  for k in kinds:
   dec=decode(oof(p[k]));r={}
   for t in T:r[t]={'MAE':float(abs(dec[t]-T[t][fixed]).mean()),'RMSE':float(np.sqrt(np.mean((dec[t]-T[t][fixed])**2)))}
   rr=[];rec=[];fr=[]
   for f in range(1,5):
    vi=np.array([i for i in fixed if foldfor[ids[i]]==f]);pred=decode(p[k][f-1,vi])['P_plus1_H2'][:,10];truth=T['P_plus1_H2'][vi,10];rv=rho(truth,pred);n=int(np.ceil(.2*len(vi)));top=None if rv is None else len(set(np.lexsort((np.array(ids)[vi],-truth))[:n])&set(np.lexsort((np.array(ids)[vi],-pred))[:n]))/n;rr.append(rv);rec.append(top);fr.append(float(abs(decode(p[k][f-1,vi])['P_plus1_H2']-T['P_plus1_H2'][vi]).mean()))
   r.update(rho450_meanfold=float(np.mean([v for v in rr if v is not None])) if any(v is not None for v in rr) else None,rho450_by_fold=rr,top20_recall=float(np.mean([v for v in rec if v is not None])) if any(v is not None for v in rec) else None,top20_by_fold=rec,Pplus_MAE_by_fold=fr);res[k]=r
  return res
 histories={'156':metrics(ref156),'172':metrics(base),'222':metrics(allp)};published=rd(S/'MODEL_METRICS_SAME124.json')
 for k in kinds:
  for t in T:assert np.isclose(histories['222'][k][t]['MAE'],published['ALL_V2_AVAILABLE'][k][t]['MAE'],atol=1e-13,rtol=0)
 put('MATCHED_EVALUATION_METRICS.json',histories)
 plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Arial','DejaVu Sans'],'font.size':8,'axes.labelsize':8,'axes.titlesize':8,'xtick.labelsize':8,'ytick.labelsize':8,'legend.fontsize':8,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
 put('FIGURE_CONTRACT.json',{'claim':'Production valid; useful out-of-family ranking and repeatable local-sampling gain not established','backend':'Python matplotlib','width_mm':183,'glyph_floor_pt':5,'n_fixed_validation':124,'folds':4,'seed_averaging':'ET/MLP17,29,43','physical_local_truth':'23 edges at2anchors, one eligible out-of-family local test anchor','wavelengths_not_independent_replicates':True,'no_clipping_or_truth_exclusion':True,'source':'saved222dataset+existingOOF; only missing matched156reference fitted32models'})
 # Matched learning curves, errorbars show fixed-fold min-max, not CI.
 fig,axs=plt.subplots(2,2,figsize=(7.20472440945,124/25.4),layout='constrained');lr=[]
 for k,col in zip(kinds,colors):
  for j,t in enumerate(['P_plus1_H2','eta','P_scale','rho']):
   yy=[];lo=[];hi=[];xx=[]
   for n in ['156','172','222']:
    pp={'156':ref156,'172':base,'222':allp}[n][k];r=histories[n][k];vals=[]
    for f in range(1,5):
     vi=np.array([i for i in fixed if foldfor[ids[i]]==f]);dec=decode(pp[f-1,vi]);vv=rho(T['P_plus1_H2'][vi,10],dec['P_plus1_H2'][:,10]) if t=='rho' else float(abs(dec[t]-T[t][vi]).mean())
     if vv is not None:vals.append(vv)
    v=r['rho450_meanfold'] if t=='rho' else r[t]['MAE']
    if v is None:continue
    xx.append(int(n));yy.append(v);lo.append(max(0,v-min(vals)));hi.append(max(0,max(vals)-v));lr.append({'model':k,'dataset_size':n,'target':t,'value':v,'fold_min':min(vals),'fold_max':max(vals)})
   axs.flat[j].errorbar(xx,yy,yerr=[lo,hi],color=col,marker='o',ms=3,lw=1,capsize=2,label=k)
 for j,ax in enumerate(axs.flat):ax.set(xlabel='FAST development geometries',ylabel=['P(+1), H2: spectral MAE','eta(+1), native: spectral MAE','P_scale: spectral MAE','450 nm mean-fold Spearman'][j],xticks=[156,172,222]);ax.set_title(chr(97+j),loc='left')
 axs.flat[3].axhline(0,color='.6',lw=.6);fig.legend(handles=[plt.Line2D([],[],color=c,marker='o',label=k) for k,c in zip(kinds,colors)],loc='outside lower center',ncol=4,frameon=False);save(fig,'LEARNING_156_172_222_MATCHED');csvout('LEARNING_CURVE_SOURCE.csv',lr)
 # Objective best, median, worst by ET spectral P+ MAE among all124. No cherry-picked cases.
 dec=decode(oof(allp['ExtraTrees']));mean=decode(oof(allp['Mean']));err=abs(dec['P_plus1_H2']-T['P_plus1_H2'][fixed]).mean(1);order=np.lexsort((np.array(ids)[fixed],err));chosen=[order[0],order[len(order)//2],order[-1]];selected=[];source=[];fig,axs=plt.subplots(3,3,figsize=(7.20472440945,159/25.4),layout='constrained')
 for row,(n,a) in enumerate(zip(['Best','Median (upper)','Worst'],chosen)):
  i=fixed[a];selected.append({'role':n,'case_id':ids[i],'fixed124_rank':int(np.where(order==a)[0][0])+1,'ET_Pplus_spectral_MAE':float(err[a]),'geometry':x[i]})
  for col,t in enumerate(['P_plus1_H2','eta','P_scale']):
   ax=axs[row,col];ax.plot(range(440,461),T[t][i],color='#222222',label='Saved FDTD label');ax.plot(range(440,461),dec[t][a],color=colors[2],ls='--',label='ExtraTrees OOF');ax.plot(range(440,461),mean[t][a],color=colors[0],ls=':',label='Mean OOF');ax.set(xlabel='Wavelength (nm)',ylabel={'P_plus1_H2':'P(+1), H2','eta':'eta(+1), native','P_scale':'P_scale'}[t],xticks=[440,450,460]);ax.set_title(f'{chr(97+row*3+col)}  {n}: '+ids[i].replace('K6GDP2_DEV_','').replace('K6LDA1_DEV_',''),loc='left')
   for w in range(21):source.append({'case_id':ids[i],'selection':n,'target':t,'wavelength_nm':440+w,'truth':float(T[t][i,w]),'ET_OOF':float(dec[t][a,w]),'Mean_OOF':float(mean[t][a,w])})
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False);save(fig,'SPECTRAL_BEST_MEDIAN_WORST');put('SPECTRAL_CASE_SELECTION.json',selected);csvout('SPECTRAL_EXAMPLES_SOURCE.csv',source)
 # Ranking scatter: all124 points, fold and pooled rho distinguished; no response clipping.
 fig,axs=plt.subplots(2,2,figsize=(7.20472440945,139/25.4),layout='constrained');rankrows=[]
 for k,col,ax in zip(kinds,colors,axs.flat):
  truth=T['P_plus1_H2'][fixed,10];pred=decode(oof(allp[k]))['P_plus1_H2'][:,10];ax.scatter(truth,pred,s=11,alpha=.7,color=col);lims=[min(truth.min(),pred.min()),max(truth.max(),pred.max())];ax.plot(lims,lims,color='.5',ls=':',lw=.7);ax.set(xlabel='Saved P(+1), 450 nm (H2)',ylabel='OOF prediction');ax.set_title(k+': mean-fold rho='+('undefined' if k=='Mean' else format(histories['222'][k]['rho450_meanfold'],'.3f')),loc='left')
  for i,t,p in zip(fixed,truth,pred):rankrows.append({'case_id':ids[i],'model':k,'fold':foldfor[ids[i]],'truth_Pplus450':float(t),'pred_Pplus450':float(p)})
 save(fig,'RANKING_SCATTER_FIXED124');csvout('RANKING_SOURCE.csv',rankrows)
 # Baseline comparison with identical fold range; no significance stars.
 fig,axs=plt.subplots(1,3,figsize=(7.20472440945,82/25.4),layout='constrained')
 for j,t in enumerate(['P_plus1_H2','eta','P_scale']):
  vals=[histories['222'][k][t]['MAE'] for k in kinds];bounds=[]
  for k,v in zip(kinds,vals):
   ff=[]
   for f in range(1,5):vi=np.array([i for i in fixed if foldfor[ids[i]]==f]);ff.append(float(abs(decode(allp[k][f-1,vi])[t]-T[t][vi]).mean()))
   bounds.append((max(0,v-min(ff)),max(0,max(ff)-v)))
  axs[j].bar(range(4),vals,color=colors,yerr=np.array(bounds).T,capsize=2,error_kw={'elinewidth':.7});axs[j].set(xticks=range(4),xticklabels=kinds,ylabel='Spectral MAE',title={'P_plus1_H2':'P(+1), H2','eta':'eta(+1), native','P_scale':'P_scale'}[t]);
  for label in axs[j].get_xticklabels():label.set_rotation(30);label.set_rotation_mode('anchor');label.set_ha('right')
 save(fig,'MEAN_BASELINE_COMPARISON')
 edges=list(csv.DictReader((B/'AL50_LOCAL_PAIR_GRAPH.csv').open(encoding='utf-8')));pairrows=[];scores=[];localpred={};gpred={k:decode(allp[k][2]) for k in kinds};eligible=[e for e in edges if e['case_low'] in gf and e['case_high'] in gf];assert len(edges)==23 and len(eligible)==10
 refs=list(csv.DictReader((Q/'APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1/A1_science/WAVELENGTH_3PS_6PS_COMPARISON.csv').open(encoding='utf-8')));reference={t:np.array([abs(float(v[b])-float(v[a])) for v in refs]) for t,a,b in [('P_plus1_H2','Pplus1_3ps','Pplus1_6ps'),('eta','eta_plus1_3ps','eta_plus1_6ps'),('P_scale','P_scale_3ps','P_scale_6ps')]}
 for e in edges:
  i,j=idx[e['case_low']],idx[e['case_high']];assert np.count_nonzero(x[i]!=x[j])==1 and x[j,int(e['axis'])-1]-x[i,int(e['axis'])-1]==5
  for t in T:
   delta=T[t][j]-T[t][i];row={'pair_id':e['pair_id'],'case_low':e['case_low'],'case_high':e['case_high'],'target':t,'eligible_family_holdout':e in eligible,'mean_abs_signal':float(abs(delta).mean()),'max_abs_signal':float(abs(delta).max()),'wavelengths_above_unmatched_A1_time_reference':int((abs(delta)>reference[t]).sum())};pairrows.append(row)
   for w in range(21):
    r={'pair_id':e['pair_id'],'case_low':ids[i],'case_high':ids[j],'target':t,'wavelength_nm':440+w,'truth_delta':float(delta[w]),'heldout_family':e in eligible}
    for k in kinds:r[k+'_delta']=float(gpred[k][t][j,w]-gpred[k][t][i,w]) if e in eligible else ''
    scores.append(r)
 csvout('ALL23_PAIR_ANALYSIS.csv',pairrows);csvout('LOCAL_PREDICTION_SOURCE.csv',scores)
 fig,axs=plt.subplots(1,3,figsize=(7.20472440945,84/25.4),layout='constrained')
 for ax,k,col in zip(axs,kinds[1:],colors[1:]):
  rr=[v for v in scores if v['target']=='P_plus1_H2' and v['heldout_family']];a=np.array([v['truth_delta'] for v in rr]);b=np.array([v[k+'_delta'] for v in rr]);ax.scatter(a,b,s=10,color=col,alpha=.65);lim=[min(a.min(),b.min()),max(a.max(),b.max())];ax.plot(lim,lim,ls=':',color='.5',lw=.7);ax.set(xlabel='True +5 nm delta P(+1)',ylabel='Predicted delta P(+1)',title=f'{k}: 10 edges, 1 family');ax.ticklabel_format(axis='both',style='sci',scilimits=(-2,2))
 save(fig,'LOCAL_DIFFERENCE_PREDICTIONS')
 groups=rd(S/'INTERACTION_TRUTH_AND_PREDICTION.json');fig,axs=plt.subplots(2,3,figsize=(7.20472440945,123/25.4),layout='constrained')
 for r,g in enumerate(groups):
  assert g['complete_truth']
  for col,t in enumerate(['P_plus1_H2','eta','P_scale']):
   ax=axs[r,col];v=g['targets'][t];ax.plot(range(440,461),v['I_21'],color='#222222',label='Full-wave label interaction',lw=1.4)
   if isinstance(v['prediction_errors'],dict):
    for k,c in zip(kinds[1:],colors[1:]):ax.plot(range(440,461),v['prediction_errors']['ALL_V2_AVAILABLE'][k]['Ihat_21'],color=c,ls='--',lw=.9,label=k+' held-out family')
   ax.axhline(0,color='.7',lw=.6);ax.set(xlabel='Wavelength (nm)',ylabel='Interaction '+{'P_plus1_H2':'P(+1), H2','eta':'eta(+1)','P_scale':'P_scale'}[t],xticks=[440,450,460]);ax.set_title(('G059: D2-D3' if r==0 else 'S31: D6-D1, truth only'),loc='left');ax.ticklabel_format(axis='y',style='sci',scilimits=(-2,2))
 fig.legend(*axs[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=2,frameon=False);save(fig,'TWO_INTERACTION_GROUPS')
 # Zero-solver error attribution: association, never causal classification.
 diagnostic=[];et=decode(oof(allp['ExtraTrees']));ep=abs(et['P_plus1_H2']-T['P_plus1_H2'][fixed]).mean(1);fs=rd(S/'ALL_V2_AVAILABLE_FOLDS.json')
 for a,i in enumerate(fixed):
  tr=np.array([idx[c] for c in fs[foldfor[ids[i]]-1]['train_ids']]);truth=T['P_plus1_H2'][i];row={'case_id':ids[i],'fold':foldfor[ids[i]],'ET_Pplus_MAE':float(ep[a]),'train_nearest6D_normalized':float(np.linalg.norm((x[tr]-x[i])/130,axis=1).min()),'Pplus_mean':float(truth.mean()),'Pplus_range':float(np.ptp(truth)),'max_abs_second_difference':float(abs(np.diff(truth,n=2)).max()),'absolute_relative_to_range':float(ep[a]/np.ptp(truth)) if np.ptp(truth)>1e-12 else None};diagnostic.append(row)
 csvout('ZERO_SOLVER_ERROR_ATTRIBUTION.csv',diagnostic);association={k:rho(ep,np.array([r[k] for r in diagnostic])) for k in ['train_nearest6D_normalized','Pplus_mean','Pplus_range','max_abs_second_difference']};put('ERROR_ASSOCIATIONS_NOT_CAUSAL.json',association)
 allglobaldelta={k:float(np.max(abs(allp[k][2]-views['GLOBAL_ONLY_ABLATION'][k][2]))) for k in kinds};put('LOCAL_ABLATION_IDENTIFIABILITY.json',{'G059_fold3_max_prediction_delta_ALL_vs_GLOBAL':allglobaldelta,'reason':'all G059 family held out; S31 family also purged in fold3. Same training data, so before/after local improvement cannot be attributed to added local training rows','S31_predictive_validation':'NOT_ELIGIBLE old32 train-only anchor; full-family purge prevents 13 old/mixed edges scoring','local_truth_edges':23,'eligible_predictive_edges':10})
 warning_summary={}
 for n in [16,32,50]:
  rows=rd(D/f'STAGE_{n:02d}/FIT_LEDGER.json');warning_summary[str(n)]={w:sum(w in r.get('warnings',[]) for r in rows) for w in sorted({w for r in rows for w in r.get('warnings',[])})}
 put('TRAINING_WARNINGS_EXISTING.json',warning_summary)
 con=sqlite3.connect((P/'data/runner_v31.db').as_uri()+'?mode=ro',uri=True);count_after=con.execute('select count(*) from solver_entries').fetchone()[0];con.close();assert count_before==count_after
 for v in rd(D/'PROTECTED_LEDGER_SNAPSHOTS.json'):assert rd(v['path'])==v['content']
 put('ZERO_SOLVER_CLOSEOUT_AUDIT.json',{'canonical_entries_before':count_before,'canonical_entries_after':count_after,'AL50_entries':50,'valid_labels':50,'replay':0,'NEW_FDTD':0,'new_fit_count':32,'completed_existing_models_refit':0,'validation124_preserved':True,'protected_ledgers_unchanged':True,'all23_pairs_21wavelengths':True,'complete_interactions':2,'NEXT_BATCH_AUTHORIZED':0,'figure_count':6,'visual_QA':'PENDING'})
 print('CLOSEOUT_ANALYSIS_RENDER_COMPLETE',json.dumps({'metrics':histories['222'],'associations':association,'fold3_ALL_GLOBAL_maxdelta':allglobaldelta}))
if __name__=='__main__':
 with threadpool_limits(limits=2):main()
