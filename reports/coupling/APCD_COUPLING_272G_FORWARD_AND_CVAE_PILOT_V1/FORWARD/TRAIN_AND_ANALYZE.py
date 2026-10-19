import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
from pathlib import Path
import sys,json,time,csv,joblib
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor
from scipy.stats import spearmanr
from threadpoolctl import threadpool_limits
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';D=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/FORWARD';D.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'scripts/coupling_ml'));from k6_v2_pipeline import contracts as C,h1 as H
rd=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
z=np.load(B/'COMPLEX_DATASET.npz');ids=list(z['case_ids']);idx={s:i for i,s in enumerate(ids)};folds=rd(B/'FOLDS.json');old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');vi=np.array([idx[s] for f in old for s in f['heldout_old_ids']]);ff={s:f['fold']-1 for f in folds for s in f['heldout_ids']};assert len(vi)==124
put('PREREGISTRATION.json',{'models':['Balanced_ET128_leaf3','Raw_ET128_leaf1'],'seeds':[17,29,43],'new_fit_limit':24,'CPU_threads':2,'target':'formal29D raw Cartesian28 + natural logP; train-only invertible output scaling for Balanced','TM_scaling':'multiply each TM Re/Im by common train TM median std / own std floored .05; TE unchanged; logP multiplied commonTMstd / logPstd','folds_source':str(B/'FOLDS.json'),'no_hyperparameter_search':True,'baseline_reused':True,'NEW_FDTD':0})
ledger=rd(D/'FIT_LEDGER.json') if (D/'FIT_LEDGER.json').exists() else []
for kind in ['Balanced','Leaf1']:
 cs=[];ps=[]
 for f in folds:
  tr=np.array([idx[s] for s in f['train_ids']]);assert not set(f['train_ids'])&set(f['heldout_ids']);X=np.c_[np.repeat(z['D_nm'][tr],21,axis=0),np.tile(z['wavelengths_nm'],len(tr))];Xa=np.c_[np.repeat(z['D_nm'],21,axis=0),np.tile(z['wavelengths_nm'],len(ids))];sc=StandardScaler().fit(X);xt=sc.transform(X);xa=sc.transform(Xa);Y=z['target29'][tr].reshape(-1,29);scale=np.ones(29)
  if kind=='Balanced':
   tm=np.array([4*k+2+j for k in range(7) for j in range(2)]);std=Y.std(axis=0);ref=np.median(std[tm]);scale[tm]=ref/np.maximum(std[tm],.05);scale[28]=ref/max(std[28],.05)
  put(kind+'_fold'+str(f['fold'])+'_target_scale.json',{'scale':scale,'train_ids':f['train_ids']})
  cc=[];pp=[]
  for seed in [17,29,43]:
   ident=f'{kind}_fold{f["fold"]}_seed{seed}';p=D/(ident+'.npz');modelp=D/(ident+'.joblib')
   if p.exists():a=np.load(p);cc.append(a['C_hat']);pp.append(a['P_scale']);continue
   row={'id':ident,'state':'STARTED','n_train_geometries':len(tr)};ledger.append(row);put('FIT_LEDGER.json',ledger);t=time.perf_counter()
   with threadpool_limits(limits=2):
    m=ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3 if kind=='Balanced' else 1,n_jobs=2,random_state=seed);m.fit(xt,Y*scale);y=m.predict(xa)/scale
   yy=y.reshape(len(ids),21,29);a=np.c_[yy[:,:,:28].reshape(len(ids),588),yy[:,:,28]];ch,pw=C.unpack_model_target(a);np.savez_compressed(p,C_hat=ch,P_scale=pw);joblib.dump({'model':m,'input_scaler':sc,'target_scale':scale,'train_ids':f['train_ids'],'heldout_ids':f['heldout_ids'],'purged_ids':f['purged_ids'],'formal_layout':'28 Cartesian + natural logP','kind':kind},modelp,compress=3);row.update(state='COMPLETE',seconds=time.perf_counter()-t);put('FIT_LEDGER.json',ledger);cc.append(ch);pp.append(pw)
  cs.append(cc);ps.append(pp)
 np.savez_compressed(D/(kind+'_PREDICTIONS.npz'),case_ids=np.array(ids),C_hat_seeds=np.array(cs),P_scale_seeds=np.array(ps),C_hat=np.mean(cs,axis=1),P_scale=np.mean(ps,axis=1))
print('FIT_COMPLETE',len(ledger),flush=True)
# Metrics preserve frozen H2 and original H1 gates.
dec=H.load_h2_decoder();truth=z['C_hat'][vi];pt=z['P_scale'][vi];eta=z['eta_H2'][vi];power=z['absolute_H2'][vi];w=z['cos_weights'];metrics={};channel=[];geom=[];gates={}
base=np.load(B/'PREDICTIONS_B.npz');models={k:(base[k+'_C_hat'],base[k+'_P_scale'],base[k+'_C_hat_seeds'],base[k+'_P_scale_seeds']) for k in ['Mean','KRR','ExtraTrees']}
for k in ['Balanced','Leaf1']:
 a=np.load(D/(k+'_PREDICTIONS.npz'));models[k]=(a['C_hat'],a['P_scale'],a['C_hat_seeds'],a['P_scale_seeds'])
for name,(ca,pa,csa,psa) in models.items():
 cp=np.array([ca[ff[ids[i]],i] for i in vi]);pw=np.array([pa[ff[ids[i]],i] for i in vi]);hh=H.reconstruct_h2(cp,pw,dec);norm=np.sqrt(np.sum(w[None,:,:,None]*abs(cp)**2,axis=(2,3)));proj=cp/np.maximum(norm[:,:,None,None],1e-12);hp=H.reconstruct_h2(proj,pw,dec);tm=truth[:,:,:,1];pm=cp[:,:,:,1];num=den=0.;rhos=[];tops=[]
 for f in range(4):
  jj=np.array([j for j,i in enumerate(vi) if ff[ids[i]]==f]);train=[idx[s] for s in folds[f]['train_ids']];ref=np.argmax(np.mean(abs(z['C_hat'][train])**2,axis=0).reshape(21,14),axis=-1);a=truth[jj].reshape(-1,21,14);b=cp[jj].reshape(-1,21,14);refs=np.broadcast_to(ref[None,:,None],(len(jj),21,1));ar=np.take_along_axis(a,refs,2);br=np.take_along_axis(b,refs,2);floor=.001*abs(a).max(axis=-1,keepdims=True);mask=(abs(a)>=floor)&(abs(ar)>=floor)&(abs(b)>1e-12)&(abs(br)>1e-12)&(np.arange(14)[None,None,:]!=ref[None,:,None]);ww=abs(a)**2;num+=np.sum(ww[mask]*abs(np.angle(b*np.conj(br)*np.conj(a*np.conj(ar)))[mask]));den+=ww[mask].sum();tt=power[jj,10,4];pr=hh['absolute_order'][jj,10,4];rho=float(spearmanr(tt,pr).statistic) if np.std(pr)>1e-14 else None;rhos.append(rho);n=int(np.ceil(.2*len(jj)));tops.append(len(set(np.argsort(tt)[-n:])&set(np.argsort(pr)[-n:]))/n if rho is not None else None)
 ns=csa.shape[1];cs=np.array([[csa[ff[ids[i]],s,i] for i in vi] for s in range(ns)]);ps=np.array([[psa[ff[ids[i]],s,i] for i in vi] for s in range(ns)]);gates[name]=H.evaluate_original_h1(truth,cs,pt,ps,z['eta_native'][vi],z['eta_native'][vi]*pt[:,:,None],decoder=dec)
 varianceT=np.var(abs(tm),axis=0,ddof=1);varianceP=np.var(abs(pm),axis=0,ddof=1);ratio=varianceP.sum()/varianceT.sum();err=abs(hh['absolute_order'][:,:,4]-power[:,:,4]).mean(axis=1);disagreement=np.mean(np.var(cs,axis=0).real,axis=(1,2,3));disrho=float(spearmanr(disagreement,err).statistic) if ns>1 else None
 metrics[name]={'complex_NRMSE':float(np.linalg.norm(cp-truth)/np.linalg.norm(truth)),'TM_magnitude_MAE':float(abs(abs(pm)-abs(tm)).mean()),'TM_magnitude_RMSE':float(np.sqrt(np.mean((abs(pm)-abs(tm))**2))),'routing_MAE':float(abs(hh['eta']-eta).mean()),'relative_phase_power_weighted_MAE_deg':float(num/den*180/np.pi),'P_scale_MAE':float(abs(pw-pt).mean()),'eta_plus_MAE':float(abs(hh['eta'][:,:,4]-eta[:,:,4]).mean()),'Pplus_MAE':float(err.mean()),'rho450_folds':rhos,'rho450_mean':float(np.mean([x for x in rhos if x is not None])) if any(x is not None for x in rhos) else None,'top20_recall':float(np.mean([x for x in tops if x is not None])) if any(x is not None for x in tops) else None,'weighted_norm_mean':float(norm.mean()),'TM_between_geometry_variance_ratio':float(ratio),'unit_norm_projection_complex_NRMSE':float(np.linalg.norm(proj-truth)/np.linalg.norm(truth)),'projection_eta_max_change':float(abs(hp['eta']-hh['eta']).max()),'seed_disagreement_vs_P_error_Spearman':disrho}
 for k in range(7):channel.append({'model':name,'order':k-3,'TM_magnitude_MAE':float(abs(abs(pm[:,:,k])-abs(tm[:,:,k])).mean()),'true_magnitude_between_geometry_variance':float(varianceT[:,k].mean()),'pred_magnitude_between_geometry_variance':float(varianceP[:,k].mean()),'routing_MAE':float(abs(hh['eta'][:,:,k]-eta[:,:,k]).mean()),'phase_powerweighted_MAE_deg':float(np.sum(abs(tm[:,:,k])**2*abs(np.angle(pm[:,:,k]*np.conj(tm[:,:,k]))))/np.sum(abs(tm[:,:,k])**2)*180/np.pi)})
 for j,i in enumerate(vi):geom.append({'model':name,'case_id':ids[i],'Pplus_MAE':float(err[j]),'seed_disagreement':float(disagreement[j]),'true_Pplus450':float(power[j,10,4]),'pred_Pplus450':float(hh['absolute_order'][j,10,4])})
put('METRICS_FIXED124.json',metrics);put('FROZEN_H1_DIAGNOSTIC.json',gates)
for n,rows in [('TM_ORDER_DIAGNOSTIC.csv',channel),('GEOMETRY_DIAGNOSTIC.csv',geom)]:
 with (D/n).open('w',newline='',encoding='utf-8') as f:wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
# Raw target-variance contributions are explanatory, not a new physics target.
var=np.var(z['target29'].reshape(-1,29),axis=0);put('TARGET_VARIANCE_CONTRIBUTIONS.json',{'TE_Cartesian_fraction':float(var[[4*k+j for k in range(7) for j in range(2)]].sum()/var.sum()),'TM_Cartesian_fraction':float(var[[4*k+2+j for k in range(7) for j in range(2)]].sum()/var.sum()),'logP_fraction':float(var[28]/var.sum()),'not_train_preprocessing':'all272 summary descriptive only; model scales fit trainfold'})
put('COMPLETE.json',{'new_sklearn_fits':len(ledger),'all_complete':all(x['state']=='COMPLETE' for x in ledger),'new_FDTD':0,'validation':124,'CPU_threads':2,'baseline_fits_reused':True});print(json.dumps(metrics),flush=True)
