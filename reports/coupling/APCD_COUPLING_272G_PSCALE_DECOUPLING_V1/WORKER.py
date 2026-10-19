"""Cached FAST272 only; no electromagnetic API or production mutation."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import sys,json,csv,time,sqlite3,subprocess,joblib,socket
import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_PSCALE_DECOUPLING_V1';S=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';F=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD'
D.mkdir(exist_ok=True);sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):
 p=D/n;tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda a:a.tolist() if hasattr(a,'tolist') else a.item()),encoding='utf-8');os.replace(tmp,p)
def csvout(n,rows):
 with (D/n).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)
def git():return {str(a):subprocess.run(['git','-C',str(R),*a],capture_output=True,text=True).stdout for a in [['status','--short'],['branch','--show-current'],['rev-parse','HEAD'],['rev-list','--left-right','--count','HEAD...@{u}'],['diff','--cached','--name-only']]}
def entries():
 p=Path(r'D:\apcd_runtime\gpu_platform_v2_serial_production_v1\minimal_runner_v3\data\runner_v31.db');co=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);a=co.execute('select * from solver_entries').fetchall();co.close();return a
if not (D/'GIT_BEFORE.json').exists():put('GIT_BEFORE.json',git());put('ENTRY_BEFORE.json',entries())
protected=[Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/AL50_SCIENCE_LEDGER.json',Q/'APCD_COUPLING_DIAG2_V31_CONTROLLED_REAL_EXECUTION_V1/DIAG2_SCIENCE_LEDGER.json']
protected += [p for p in (Q/'APCD_COUPLING_ML_V3_DOE56_FULL_SCIENCE_PRODUCTION_V1/v3_execution_authority_v1').glob('*LEDGER*.json')]
protected += [R/p for p in rd(D/'GIT_BEFORE.json')["['diff', '--cached', '--name-only']"].splitlines()]
import base64
if not (D/'PROTECTED_BYTES_BEFORE.json').exists():put('PROTECTED_BYTES_BEFORE.json',{str(p):base64.b64encode(p.read_bytes()).decode() for p in protected if p.exists()})
put('PREREGISTRATION.json',{'host':socket.gethostname(),'validation':'same primary124 IDs, original family-purged four train folds; all wavelength rows of a geometry grouped','reuse':'8 saved NN29 seeds17/29; baseline Mean/KRR/ET and Leaf1 predictions; no CVAE fits','additional_joint':'same7-64-64-29 tanh StandardScaler X/Y Adam300epochs seed43 each fold only (4fits)','independent_P':'7-32-32-1 tanh StandardScaler X/logP Adam300epochs seeds17/29/43 (12fits)','baselines':'wavelength-conditioned training-geometry physical mean; Ridge alpha1 lnP with6 geometry + centered wavelength + squared wavelength, train-only scaling (4fits); frozen ETleaf1 and ETleaf3','all_MLP':'batch256 tol0 n_iter_no_change301; no early stopping/tuning; CPU2threads','combination':'same NN3 complex state plus each independent P; no truth as model input','oracle':'trueC/trueP, predC/trueP, trueC/predP, predC/predP all frozenH2; explicitly diagnostic','seed_aggregation':'Cartesian complex arithmetic mean; P arithmetic physical mean after inverse-log per seed','selection':'report all preregistered variants; heldout model choice remains development evidence, not nested test','NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0})
z=np.load(B/'COMPLEX_DATASET.npz');ids=list(z['case_ids']);idx={s:i for i,s in enumerate(ids)};assert len(ids)==len(set(ids))==len(set(map(tuple,z['D_nm'])))==272
folds=rd(B/'FOLDS.json');old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');dec=H.load_h2_decoder();fitlog=rd(D/'FIT_LEDGER.json') if (D/'FIT_LEDGER.json').exists() else [];fold_data=[];trainrows=[]
def features(ii):return np.c_[np.repeat(z['D_nm'][ii],21,axis=0),np.tile(z['wavelengths_nm'],len(ii))]
def ridgefeature(x):v=x[:,6]-450.;return np.c_[x[:,:6],v,v*v]
def fitpredict(kind,fi,seed,xt,xv,y):
 stem=f'{kind}_fold{fi+1}_seed{seed}';p=D/(stem+'.npz');mp=D/(stem+'.joblib')
 if p.exists():v=np.load(p);return v['Y_validation'],v['Y_train']
 assert not mp.exists(),'Saved model without predictions: recover predictions, do not refit'
 sx=StandardScaler().fit(xt);target=y.reshape(-1,1) if y.ndim==1 else y;sy=StandardScaler().fit(target);t=time.perf_counter()
 if kind=='Ridge':m=Ridge(alpha=1.0)
 else:m=MLPRegressor(hidden_layer_sizes=(64,64) if kind=='Joint29' else (32,32),activation='tanh',solver='adam',max_iter=300,early_stopping=False,random_state=seed,batch_size=256,tol=0,n_iter_no_change=301)
 with threadpool_limits(limits=2):m.fit(sx.transform(xt),sy.transform(target).ravel() if target.shape[1]==1 else sy.transform(target))
 def predict(x):a=m.predict(sx.transform(x));return sy.inverse_transform(a[:,None] if a.ndim==1 else a)
 yt=predict(xt);yv=predict(xv);joblib.dump({'model':m,'X':sx,'Y':sy,'train_ids':folds[fi]['train_ids'],'target':'formal29D' if kind=='Joint29' else 'logP'},mp);np.savez_compressed(p,Y_validation=yv,Y_train=yt);fitlog.append({'kind':kind,'fold':fi+1,'seed':seed,'seconds':time.perf_counter()-t,'epochs':getattr(m,'n_iter_',None),'state':'COMPLETE'});put('FIT_LEDGER.json',fitlog);return yv,yt
for fi,f in enumerate(folds):
 va=np.array([idx[s] for s in old[fi]['heldout_old_ids']]);tr=np.array([idx[s] for s in f['train_ids']]);assert not set(f['train_ids'])&set(f['heldout_ids']);assert f['family_overlap']==0;xt=features(tr);xv=features(va);cp=[];jp=[];sp=[];ntrain=[]
 for seed in [17,29,43]:
  if seed in [17,29]:
   v=np.load(S/f'NN_fold{fi+1}_seed{seed}.npz');c=v['C'];p=v['P'];a=joblib.load(S/f'NN_fold{fi+1}_seed{seed}.joblib');t=a['model'].predict(a['X'].transform(xt));yt=a['Y'].inverse_transform(t).reshape(len(tr),21,29)
  else:
   yy,yt=fitpredict('Joint29',fi,seed,xt,xv,z['target29'][tr].reshape(-1,29));yy=yy.reshape(len(va),21,29);yt=yt.reshape(len(tr),21,29);a=yy[:,:,:28].reshape(len(va),21,7,2,2);c=a[...,0]+1j*a[...,1];p=np.exp(yy[:,:,28])
  cp.append(c);jp.append(p);ntrain.append(np.exp(yt[:,:,28]));yy,ytp=fitpredict('PSNet',fi,seed,xt,xv,np.log(z['P_scale'][tr]).reshape(-1));sp.append(np.exp(yy.reshape(len(va),21)));trainrows.append({'model':'PSNet','fold':fi+1,'seed':seed,'train_P_MAE':float(abs(np.exp(ytp.reshape(len(tr),21))-z['P_scale'][tr]).mean()),'validation_P_MAE':float(abs(sp[-1]-z['P_scale'][va]).mean())});trainrows.append({'model':'Joint29','fold':fi+1,'seed':seed,'train_P_MAE':float(abs(ntrain[-1]-z['P_scale'][tr]).mean()),'validation_P_MAE':float(abs(p-z['P_scale'][va]).mean())})
 yy,yyt=fitpredict('Ridge',fi,0,ridgefeature(xt),ridgefeature(xv),np.log(z['P_scale'][tr]).reshape(-1));rp=np.exp(yy.reshape(len(va),21));mp=np.broadcast_to(z['P_scale'][tr].mean(0),(len(va),21)).copy();et=np.load(B/'PREDICTIONS_B.npz');leaf=np.load(F/'Leaf1_PREDICTIONS.npz')
 data={'fold':fi+1,'va':va,'tr':tr,'C_seeds':np.array(cp),'Joint_P_seeds':np.array(jp),'PSNet_P_seeds':np.array(sp),'PMean':mp,'Ridge':rp,'ET3_P_seeds':et['ExtraTrees_P_scale_seeds'][fi,:,va].transpose(1,0,2) if False else np.array([et['ExtraTrees_P_scale_seeds'][fi,s,va] for s in range(3)]),'Leaf1_P_seeds':np.array([leaf['P_scale_seeds'][fi,s,va] for s in range(3)]),'ET3_C_seeds':np.array([et['ExtraTrees_C_hat_seeds'][fi,s,va] for s in range(3)]),'Leaf1_C_seeds':np.array([leaf['C_hat_seeds'][fi,s,va] for s in range(3)]),'Joint_train_P':np.array(ntrain)}
 np.savez_compressed(D/f'FOLD{fi+1}_PREDICTIONS.npz',**data);fold_data.append(data);print('FIT_FOLD_COMPLETE',fi+1,flush=True)
csvout('TRAIN_VALIDATION_PSCALE.csv',trainrows)
put('TRAINING_COMPLETE.json',{'new_joint_fits':4,'new_PNet_fits':12,'new_Ridge_fits':4,'existing_NN_fits_reused':8,'tree_fits':0,'CVAE_fits':0})
metricrows=[];psrows=[];wavrows=[];georows=[];orows=[];cancel=[];variant_cs={};variant_ps={};arrayparts={};phase_ref=[]
def evaluate(name,fi,va,cc,pp,kind='formal'):
 tc=z['C_hat'][va];tp=z['P_scale'][va];te=z['eta_H2'][va];target=z['absolute_H2'][va];h=H.reconstruct_h2(cc,pp,dec);ep=h['eta'];ap=h['absolute_order'];a=tc.reshape(len(va),21,14);b=cc.reshape(len(va),21,14);ref=np.array(rd(B/f'PHASE_REFERENCE_fold{fi+1}.json')['channel_flat_indices']);rr=np.broadcast_to(ref[None,:,None],(len(va),21,1));ar=np.take_along_axis(a,rr,2);br=np.take_along_axis(b,rr,2);floor=.001*abs(a).max(2,keepdims=True);mask=(abs(a)>=floor)&(abs(ar)>=floor)&(abs(b)>1e-12)&(abs(br)>1e-12)&(np.arange(14)[None,None,:]!=ref[None,:,None]);wt=abs(a)**2;pe=abs(np.angle(b*np.conj(br)*np.conj(a*np.conj(ar))));n=int(np.ceil(.2*len(va)));truth450=target[:,10,4];pred450=ap[:,10,4];rho=float(spearmanr(truth450,pred450).statistic) if np.std(pred450)>1e-14 else None
 # Spectral shape uses per-geometry centered RMSE and Pearson; all21 points remain grouped.
 t=target[:,:,4];p=ap[:,:,4];center=(p-p.mean(1,keepdims=True))-(t-t.mean(1,keepdims=True));corr=[]
 for ta,pa in zip(t,p):
  if np.std(ta)>1e-12 and np.std(pa)>1e-12:corr.append(float(np.corrcoef(ta,pa)[0,1]))
 row={'model':name,'kind':kind,'fold':fi+1,'n':len(va),'complex_SSE':float((abs(cc-tc)**2).sum()),'complex_energy':float((abs(tc)**2).sum()),'complex_NRMSE':float(np.linalg.norm(cc-tc)/np.linalg.norm(tc)),'TM_magnitude_MAE':float(abs(abs(cc[:,:,:,1])-abs(tc[:,:,:,1])).mean()),'routing_MAE':float(abs(ep-te).mean()),'phase_num':float((wt[mask]*pe[mask]).sum()),'phase_den':float(wt[mask].sum()),'relative_phase_deg':float((wt[mask]*pe[mask]).sum()/wt[mask].sum()*180/np.pi),'P_scale_MAE':float(abs(pp-tp).mean()),'P_scale_bias':float((pp-tp).mean()),'eta_plus_MAE':float(abs(ep[:,:,4]-te[:,:,4]).mean()),'Pplus_MAE':float(abs(p-t).mean()),'rho450':rho,'Top20_recall':float(len(set(np.argsort(truth450)[-n:])&set(np.argsort(pred450)[-n:]))/n) if rho is not None else None,'Pplus_centered_spectral_RMSE':float(np.sqrt(np.mean(center**2))),'Pplus_spectral_Pearson_mean':float(np.mean(corr)) if corr else None}
 if kind=='formal':metricrows.append(row)
 else:orows.append(row)
 arrayparts.setdefault(name,[]).append({'va':va,'C':cc,'P':pp,'eta':ep,'absolute':ap})
 return h
for fi,d in enumerate(fold_data):
 va=d['va'];tr=d['tr'];tc=z['C_hat'][va];tp=z['P_scale'][va];cs=d['C_seeds'];joint=d['Joint_P_seeds'];q=cs.mean(0);p=joint.mean(0);psets={'Joint':joint,'PSNet':d['PSNet_P_seeds'],'PMean':np.repeat(d['PMean'][None],3,0),'Ridge':np.repeat(d['Ridge'][None],3,0),'ET3':d['ET3_P_seeds'],'Leaf1':d['Leaf1_P_seeds']}
 formal={'NN2_Joint':(cs[:2],joint[:2]),'NN3_Joint':(cs,joint),'ET3_Joint':(d['ET3_C_seeds'],d['ET3_P_seeds']),'Leaf1_Joint':(d['Leaf1_C_seeds'],d['Leaf1_P_seeds'])}
 for name,ps in psets.items():
  if name!='Joint':formal['NN3_'+name]=(cs,ps)
 for name,(carr,parr) in formal.items():
  evaluate(name,fi,va,carr.mean(0),parr.mean(0));variant_cs.setdefault(name,[]).append(carr);variant_ps.setdefault(name,[]).append(parr)
 for seedidx,seed in enumerate([17,29,43]):
  evaluate('NN_seed'+str(seed),fi,va,cs[seedidx],joint[seedidx]);evaluate('Leaf1_seed'+str(seed),fi,va,d['Leaf1_C_seeds'][seedidx],d['Leaf1_P_seeds'][seedidx]);evaluate('ET3_seed'+str(seed),fi,va,d['ET3_C_seeds'][seedidx],d['ET3_P_seeds'][seedidx]);evaluate('NN_PSNet_seed'+str(seed),fi,va,cs[seedidx],d['PSNet_P_seeds'][seedidx])
 for name,cc,pp in [('NN2',cs[:2].mean(0),joint[:2].mean(0)),('NN3',q,p),('Leaf1',d['Leaf1_C_seeds'].mean(0),d['Leaf1_P_seeds'].mean(0)),('ET3',d['ET3_C_seeds'].mean(0),d['ET3_P_seeds'].mean(0)),('NN3_PSNet',q,d['PSNet_P_seeds'].mean(0)),('NN3_ET3',q,d['ET3_P_seeds'].mean(0))]:
  aa=evaluate(name+'_A_TRUE',fi,va,tc,tp,'oracle');bb=evaluate(name+'_B_C_ONLY',fi,va,cc,tp,'oracle');ccp=evaluate(name+'_C_P_ONLY',fi,va,tc,pp,'oracle');dd=evaluate(name+'_D_BOTH',fi,va,cc,pp,'oracle');true=aa['absolute_order'][:,:,4];eb=bb['absolute_order'][:,:,4]-true;ec=ccp['absolute_order'][:,:,4]-true;ed=dd['absolute_order'][:,:,4]-true;cross=(dd['eta'][:,:,4]-aa['eta'][:,:,4])*(pp-tp);assert np.max(abs(ed-eb-ec-cross))<1e-12
  cancel.append({'model':name,'fold':fi+1,'n':len(va),'C_only_MAE':float(abs(eb).mean()),'P_only_MAE':float(abs(ec).mean()),'both_MAE':float(abs(ed).mean()),'interaction_MAE':float(abs(cross).mean()),'opposite_sign_fraction':float(np.mean(eb*ec<0)),'signed_error_correlation':float(np.corrcoef(eb.ravel(),ec.ravel())[0,1]),'cancellation_fraction_of_component_abs_sum':float(1-abs(ed).mean()/(abs(eb).mean()+abs(ec).mean()+abs(cross).mean())),'MSE_B':float((eb**2).mean()),'MSE_C':float((ec**2).mean()),'MSE_cross':float((cross**2).mean()),'MSE_total':float((ed**2).mean()),'MSE_cross_covariance_terms':float((2*eb*ec+2*eb*cross+2*ec*cross).mean()),'identity_max_error':float(abs(ed-eb-ec-cross).max())})
  np.savez_compressed(D/f'ORACLE_{name}_fold{fi+1}.npz',case_ids=z['case_ids'][va],true=true,C_only=bb['absolute_order'][:,:,4],P_only=ccp['absolute_order'][:,:,4],both=dd['absolute_order'][:,:,4],error_C=eb,error_P=ec,interaction=cross)
 for name,ps in psets.items():
  pp=ps.mean(0);error=pp-tp;logerror=np.log(pp)-np.log(tp);vartrue=np.var(tp,axis=0,ddof=1);varpred=np.var(pp,axis=0,ddof=1);peak=np.argmax(tp,axis=1);atpeak=error[np.arange(len(va)),peak];high=tp>=np.quantile(z['P_scale'][tr],.9,axis=0)[None,:];slope=np.diff(tp,axis=1);predslope=np.diff(pp,axis=1);active=abs(slope)>1e-12
  psrows.append({'model':name,'fold':fi+1,'n':len(va),'MAE':float(abs(error).mean()),'RMSE':float(np.sqrt(np.mean(error**2))),'bias':float(error.mean()),'median_error':float(np.median(error)),'log_bias':float(logerror.mean()),'log_RMSE':float(np.sqrt(np.mean(logerror**2))),'overprediction_fraction':float(np.mean(error>0)),'geometry_variance_ratio':float(varpred.sum()/vartrue.sum()),'within_geometry_spectral_variance_ratio':float(np.var(pp,axis=1).sum()/np.var(tp,axis=1).sum()),'centered_spectral_RMSE':float(np.sqrt(np.mean(((pp-pp.mean(1,keepdims=True))-(tp-tp.mean(1,keepdims=True)))**2))),'peak_MAE':float(abs(atpeak).mean()),'peak_bias':float(atpeak.mean()),'train_q90_region_MAE':float(abs(error[high]).mean()),'train_q90_region_bias':float(error[high].mean()),'slope_sign_accuracy_nonzero':float(np.mean(np.sign(slope[active])==np.sign(predslope[active]))),'arithmetic_vs_geometric_seed_P_gap':float((pp-np.exp(np.log(ps).mean(0))).mean())})
  for j,wl in enumerate(z['wavelengths_nm']):wavrows.append({'model':name,'fold':fi+1,'wavelength_nm':int(wl),'n':len(va),'true_mean':float(tp[:,j].mean()),'pred_mean':float(pp[:,j].mean()),'MAE':float(abs(error[:,j]).mean()),'bias':float(error[:,j].mean()),'true_geometry_variance':float(vartrue[j]),'pred_geometry_variance':float(varpred[j])})
  for j,ind in enumerate(va):georows.append({'model':name,'fold':fi+1,'case_id':ids[ind],'D_nm':','.join(map(str,z['D_nm'][ind])),'MAE':float(abs(error[j]).mean()),'bias':float(error[j].mean()),'true_mean':float(tp[j].mean()),'pred_mean':float(pp[j].mean()),'true_peak_wavelength_nm':int(z['wavelengths_nm'][peak[j]]),'true_peak':float(tp[j,peak[j]]),'error_at_true_peak':float(atpeak[j])})
 print('ANALYZED_FOLD',fi+1,flush=True)
for n,rows in [('MODEL_FOLD_METRICS.csv',metricrows),('ORACLE_FOLD_METRICS.csv',orows),('ERROR_CANCELLATION.csv',cancel),('PSCALE_FOLD_DIAGNOSTIC.csv',psrows),('PSCALE_WAVELENGTH_DIAGNOSTIC.csv',wavrows),('PSCALE_GEOMETRY_DIAGNOSTIC.csv',georows)]:csvout(n,rows)
def pool(rows):
 results=[]
 for name in dict.fromkeys(r['model'] for r in rows):
  a=[r for r in rows if r['model']==name];out={'model':name,'n':sum(r['n'] for r in a)}
  for k in a[0]:
   if k in ['model','fold','n','kind']:continue
   valid=[r for r in a if r[k] is not None];out[k]=float(np.mean([r[k] for r in valid])) if k in ['rho450','Top20_recall'] else float(sum(r[k]*r['n'] for r in valid)/sum(r['n'] for r in valid)) if valid else None
  if 'complex_SSE' in a[0]:out['complex_NRMSE']=float(np.sqrt(sum(r['complex_SSE'] for r in a)/sum(r['complex_energy'] for r in a)));out['relative_phase_deg']=float(sum(r['phase_num'] for r in a)/sum(r['phase_den'] for r in a)*180/np.pi)
  results.append(out)
 return results
summary=pool(metricrows);oracle=pool(orows);put('MODEL_SUMMARY.json',summary);put('ORACLE_SUMMARY.json',oracle);csvout('MODEL_COMPARISON.csv',summary);csvout('ORACLE_COMPARISON.csv',oracle);put('PSCALE_SUMMARY_FOLD_WEIGHTED.json',pool(psrows));put('CANCELLATION_SUMMARY.json',pool(cancel));allva=np.concatenate([d['va'] for d in fold_data]);gates={}
for name in variant_cs:
 c=np.concatenate(variant_cs[name],axis=1);p=np.concatenate(variant_ps[name],axis=1);gates[name]=H.evaluate_original_h1(z['C_hat'][allva],c,z['P_scale'][allva],p,z['eta_native'][allva],z['eta_native'][allva]*z['P_scale'][allva,:,None],decoder=dec)
put('FROZEN_H1_DIAGNOSTIC.json',gates);put('H1_SUMMARY.json',{k:{'gates':a['gates'],'production_admission':a['production_admission'],'seed_stability_status':a['seed_stability_status']} for k,a in gates.items()});put('H1_FROZEN_THRESHOLDS.json',H.load_h1_authority())
for name,a in arrayparts.items():np.savez_compressed(D/(name+'_OOF.npz'),case_ids=z['case_ids'][allva],C=np.concatenate([r['C'] for r in a]),P=np.concatenate([r['P'] for r in a]),eta=np.concatenate([r['eta'] for r in a]),absolute=np.concatenate([r['absolute'] for r in a]))
# Fixed-model uncertainty by existing connected family, not wavelength or seed pseudoreplication.
fam=rd(B/'LOCAL_FAMILY_COMPONENTS.json');caseids=list(z['case_ids'][allva]);gid={s:s for s in caseids}
for j,f in enumerate(fam):
 for cid in f:
  if cid in gid:gid[cid]='local_family_'+str(j)
groups=list(dict.fromkeys(gid.values()));unit=[np.array([j for j,c in enumerate(caseids) if gid[c]==g]) for g in groups];rng=np.random.default_rng(5201);boot={};powertrue=z['absolute_H2'][allva,:,4]
def error(name):return abs(np.concatenate([r['absolute'][:,:,4] for r in arrayparts[name]])-powertrue).mean(1)
for candidate,baseline in [('NN2_Joint','Leaf1_Joint'),('NN3_Joint','Leaf1_Joint'),('NN3_Joint','ET3_Joint'),('NN3_PSNet','NN3_Joint'),('NN3_ET3','NN3_Joint'),('NN3_Leaf1','NN3_Joint'),('NN3_Ridge','NN3_Joint'),('NN3_PMean','NN3_Joint')]:
 delta=error(candidate)-error(baseline);bs=[]
 for _ in range(2000):jj=np.concatenate([unit[k] for k in rng.integers(len(unit),size=len(unit))]);bs.append(delta[jj].mean())
 boot[candidate+' minus '+baseline]={'Pplus_MAE_delta':float(delta.mean()),'family_percentile95':np.quantile(bs,[.025,.975]).tolist(),'folds_improved':sum(next(r for r in metricrows if r['model']==candidate and r['fold']==f)['Pplus_MAE']<next(r for r in metricrows if r['model']==baseline and r['fold']==f)['Pplus_MAE'] for f in range(1,5))}
put('PAIRED_FAMILY_STABILITY.json',{'family_units':len(unit),'replicates':2000,'conditional_on_fixed_models_not_nested_test':True,'comparisons':boot})
oldmetrics=list(csv.DictReader((S/'COMPLEX_AGGREGATION_ABLATION.csv').open()));oldnn=next(r for r in oldmetrics if r['model']=='D_NN29');newnn=next(r for r in summary if r['model']=='NN2_Joint');assert abs(newnn['Pplus_MAE']-float(oldnn['Pplus_MAE']))<1e-12 and abs(newnn['rho450']-float(oldnn['rho450']))<1e-12;assert all(next(r for r in orows if r['model']==f'{n}_A_TRUE' and r['fold']==f)['Pplus_MAE']<1e-12 for n in ['NN2','NN3','Leaf1','ET3','NN3_PSNet','NN3_ET3'] for f in range(1,5))
after=git();eb=rd(D/'ENTRY_BEFORE.json');ea=entries();assert [list(r) for r in ea]==eb;before=rd(D/'GIT_BEFORE.json');assert before["['diff', '--cached', '--name-only']"]==after["['diff', '--cached', '--name-only']"]
for p,v in rd(D/'PROTECTED_BYTES_BEFORE.json').items():assert Path(p).read_bytes()==base64.b64decode(v),p
put('GIT_AFTER.json',after);put('BOUNDARY_AUDIT.json',{'solver_entries_before':len(eb),'solver_entries_after':len(ea),'rows_identical':True,'protected_files_byte_identical':len(rd(D/'PROTECTED_BYTES_BEFORE.json')),'four_staged_preserved':True,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'FAST':272,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD','CVAE':'FROZEN'});put('COMPLETE.json',{'status':'COMPLETE','validation_geometries':124,'folds':4,'seeds':[17,29,43],'NN2_prior_metrics_reproduced':True});print(json.dumps({'models':summary,'cancellation':pool(cancel),'stability':boot},indent=2),flush=True)
