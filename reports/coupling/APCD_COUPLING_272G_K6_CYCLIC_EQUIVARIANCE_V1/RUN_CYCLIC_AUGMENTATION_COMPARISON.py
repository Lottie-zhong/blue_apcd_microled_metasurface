"""Zero-solver cyclic augmentation comparison for the frozen 272G FAST set.

This script reuses the fixed 124-geometry grouped development folds and saved
NN3 baseline checkpoints. It fits only the preregistered six-cycle augmented
NN3 models. No electromagnetic solver, Runner, ledger or sealed data is used.
"""
from pathlib import Path
import os,sys,csv,json,time,hashlib,joblib
for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[key]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits

R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
Q=R/'reports'/'coupling'
OUT=Q/'APCD_COUPLING_272G_K6_CYCLIC_EQUIVARIANCE_V1'
DATA=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'STAGE_50'/'COMPLEX_DATASET.npz'
FOLD=Q/'APCD_COUPLING_CLEANUP_FAST_CLOSE_AND_FORWARD_RESUME_V1'/'FOLD_IDENTITY.csv'
BASE=Q/'APCD_COUPLING_272G_COMPLEX_ENSEMBLE_SHRINKAGE_V1'
PS=Q/'APCD_COUPLING_272G_PSCALE_DECOUPLING_V1'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R/'scripts'/'coupling_ml'))
from k6_v2_pipeline import h1 as H

def write_json(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8');os.replace(tmp,path)
def write_csv(path,rows):
 if not rows:return
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def enc29(c,p):
 return np.concatenate([np.stack([c.real,c.imag],axis=-1).reshape(len(c),21,28),np.log(p)[...,None]],axis=-1)
def decode29(y):
 a=y[...,:28].reshape(len(y),21,7,2,2)
 return a[...,0]+1j*a[...,1],np.exp(y[...,28])
def x_features(d,wls):
 n=len(d);return np.concatenate([np.repeat(d[:,None,:],len(wls),axis=1),np.broadcast_to(wls[None,:,None],(n,len(wls),1))],axis=2).reshape(n*len(wls),7)
def y_predict(bundle,x):
 sy=bundle['Y'];sx=bundle['X'];model=bundle['model']
 q=model.predict(sx.transform(x));return sy.inverse_transform(q[:,None] if q.ndim==1 else q)
def cycle_phase(k,orders):return np.exp(-2j*np.pi*np.asarray(orders)*int(k)/6.0)
def unique_rotations(d):
 out=[];seen=set()
 for k in range(6):
  v=np.roll(d,k);key=tuple(v.tolist())
  if key not in seen:seen.add(key);out.append((k,v))
 return out

z=np.load(DATA,allow_pickle=False);ids=[str(v) for v in z['case_ids'].tolist()]
D=np.asarray(z['D_nm'],int);C=np.asarray(z['C_hat'],complex);P=np.asarray(z['P_scale'],float)
wl=np.asarray(z['wavelengths_nm'],float);orders=np.asarray(z['orders'],int)
target29=np.asarray(z['target29'],float)
assert len(ids)==272 and len(set(ids))==272 and D.shape==(272,6) and C.shape==(272,21,7,2) and P.shape==(272,21)
assert np.array_equal(wl,np.arange(440.,461.)) and np.array_equal(orders,np.arange(-3,4))
assert np.max(np.abs(enc29(C,P)-target29))==0.0
idx={cid:i for i,cid in enumerate(ids)}
with FOLD.open('r',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
folds={}
for row in rows:
 folds.setdefault(int(row['fold']),{'outer_train':{},'outer_validation_development':{}})
 if row['role'] in folds[int(row['fold'])]:folds[int(row['fold'])][row['role']][row['case_id']]=row['family_id']
assert sorted(folds)==[1,2,3,4]
for fi,fold in folds.items():
 tr=set(fold['outer_train']);va=set(fold['outer_validation_development'])
 assert len(tr)==len(fold['outer_train']) and len(va)==len(fold['outer_validation_development'])
 assert not (tr&va) and (tr|va)<=set(ids)
 assert len(set(fold['outer_train'].values())&set(fold['outer_validation_development'].values()))==0
 # Reuse only the already fixed 124-geometry validation identities.
 old=np.load(PS/f'FOLD{fi}_PREDICTIONS.npz',allow_pickle=False)
 assert set(ids[i] for i in old['va'].tolist())==va
 # The baseline checkpoint's training identities must match this fixed split.
 for seed in (17,29,43):
  cp=(BASE/f'NN_fold{fi}_seed{seed}.joblib') if seed in (17,29) else (PS/f'Joint29_fold{fi}_seed43.joblib')
  assert cp.exists(),f'missing approved baseline checkpoint {cp}'
  m=joblib.load(cp);assert set(m['train_ids'])==tr,(fi,seed,len(m['train_ids']),len(tr))
 # Cyclic orbit exclusion already passed in the independent audit; repeat a direct fold check.
 key_for={}
 for cid in tr|va:
  d=D[idx[cid]];key_for[cid]=min(tuple(np.roll(d,k).tolist()) for k in range(6))
 assert not ({key_for[c] for c in tr}&{key_for[c] for c in va})

# Fit ledger and configuration are written before the first new fit.
view_counts=collections=None
rotation_counts={}
for fi,fold in folds.items():
 counts=[len(unique_rotations(D[idx[cid]])) for cid in sorted(fold['outer_train'])]
 rotation_counts[str(fi)]={'train_geometry_count':len(counts),'unique_rotation_histogram':{str(k):counts.count(k) for k in sorted(set(counts))},'augmented_train_geometry_views':int(sum(counts)),'original_train_geometry_views':len(counts)}
config={'schema':'K6_CYCLIC_AUGMENTATION_CONFIG_V1','dataset':str(DATA),'dataset_cases':272,
 'validation_manifest':str(FOLD),'validation_ids':'original fixed primary124; four folds; family purges retained',
 'architecture':'MLPRegressor 7-64-64-29, tanh, Adam, StandardScaler(X/Y) fit on training fold only',
 'seeds':[17,29,43],'max_iter':300,'batch_size':256,'tol':0,'early_stopping':False,'n_iter_no_change':301,
 'rotation':{'T_D':'np.roll(D,+1)','k_views':'0..5','input_transform':'D_k=np.roll(D,k)','C_label_transform':'C_k[m,pol]=C[m,pol]*exp(-i*2*pi*m*k/6)','P_scale_invariant':True,'augmentation':'unique D rotations per training geometry; all 21 wavelengths retained per view','inference':'all six views, phase-align C back by exp(+i*2*pi*m*k/6), arithmetic mean for C and P'},
 'seed_model_provenance':'A/C reuse saved NN3 seeds 17/29 and saved seed43 checkpoints; B/D use 12 fresh independent augmentation fits; no baseline refit',
 'orbit_dedup':rotation_counts,'h2_sha256':H.H2_DECODER_SHA256,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,
 'disclaimer':'Four folds and three seeds are repeated development evaluation, not an independent final test; existing 124 development geometries have been repeatedly used for model selection.'}
write_json(OUT/'CYCLIC_MODEL_CONFIG.json',config)
prereg={'frozen_before_new_fits':True,'config':'CYCLIC_MODEL_CONFIG.json','compare':['A_original_NN3_no_augmentation','B_train_only_six_cycle_augmentation','C_original_NN3_six_view_inference_ensemble','D_augmented_NN3_plus_six_view_inference_ensemble'],
 'primary_metrics':['609D_complex_NRMSE','TM_magnitude_MAE','routing_MAE','weighted_relative_phase_deg','P_scale_MAE','eta_plus_MAE','Pplus_MAE','450nm_Spearman','Top20_recall','equivariance_relative_L2'],
 'fixed_evaluation':'same original primary124 IDs, same per-fold train lists, family/cyclic purge; no validation use in fitting or preprocessing',
 'stopping':'fixed 300 epochs; no early stopping or tuning; all folds/seeds reported',
 'fit_budget':'12 augmented NN3 fits total; baseline A/C are inference only and reuse saved checkpoints'}
write_json(OUT/'CYCLIC_PREREGISTRATION.json',prereg)

decoder=H.load_h2_decoder()
truth_h=H.reconstruct_h2(C,P,decoder)
eta_truth=np.asarray(z['eta_H2'],float);abs_truth=np.asarray(z['absolute_H2'],float)
assert np.max(np.abs(truth_h['eta']-eta_truth))<1e-12
assert np.max(np.abs(truth_h['absolute_order']-abs_truth))<1e-12

# Load existing A/C baselines and re-derive predictions. Save B checkpoints as produced.
preds={name:{} for name in ('A_original','B_augmented','C_six_view','D_augmented_six_view')}
raw_views={name:{} for name in ('A_original','B_augmented','C_six_view','D_augmented_six_view')}
fit_rows=[];loss_rows=[];metric_rows=[];order_rows=[];equiv_rows=[]
pred_by_model={name:{} for name in preds}
global_order=[str(x) for x in np.load(PS/'NN3_A_TRUE_OOF.npz',allow_pickle=False)['case_ids'].tolist()]
assert len(global_order)==124 and len(set(global_order))==124
global_idx={cid:i for i,cid in enumerate(global_order)}

def fit_augmented(fi,seed,tridx):
 cp=OUT/f'B_AUGMENTED_fold{fi}_seed{seed}.joblib'
 if cp.exists():
  bundle=joblib.load(cp)
  assert bundle.get('train_ids')==[ids[i] for i in tridx] and bundle.get('seed')==seed and bundle.get('fold')==fi
  for epoch,val in enumerate(bundle['model'].loss_curve_,1):loss_rows.append({'model':'B_augmented','fold':fi,'seed':seed,'epoch':epoch,'training_loss':float(val)})
  fit_rows.append({'model':'B_augmented','fold':fi,'seed':seed,'n_train_geometries':len(tridx),'unique_rotation_views':bundle.get('n_unique_rotation_views'),'n_training_rows':bundle.get('n_training_rows'),'epochs':int(bundle['model'].n_iter_),'fit_seconds':bundle.get('training_seconds'),'checkpoint':str(cp),'reused_existing_fit':True})
  return bundle
 xs=[];ys=[];nviews=0
 for gi in tridx:
  d=D[gi]
  for k,dv in unique_rotations(d):
   nviews+=1;ct=C[gi:gi+1]*cycle_phase(k,orders).reshape(1,1,7,1);pt=P[gi:gi+1]
   ys.append(enc29(ct,pt).reshape(21,29));xs.append(x_features(dv[None,:],wl))
 X=np.concatenate(xs,axis=0);Y=np.concatenate(ys,axis=0)
 sx=StandardScaler().fit(X);sy=StandardScaler().fit(Y)
 model=MLPRegressor(hidden_layer_sizes=(64,64),activation='tanh',solver='adam',max_iter=300,early_stopping=False,random_state=seed,batch_size=256,tol=0,n_iter_no_change=301)
 t=time.perf_counter()
 with threadpool_limits(limits=2):model.fit(sx.transform(X),sy.transform(Y))
 elapsed=time.perf_counter()-t
 bundle={'model':model,'X':sx,'Y':sy,'train_ids':[ids[i] for i in tridx],'seed':seed,'fold':fi,'target':'formal29D_cyclic_augmented',
  'n_train_geometries':len(tridx),'n_unique_rotation_views':nviews,'n_training_rows':len(X),'training_seconds':elapsed,'config':str(OUT/'CYCLIC_MODEL_CONFIG.json')}
 joblib.dump(bundle,cp,compress=3)
 for epoch,val in enumerate(model.loss_curve_,1):loss_rows.append({'model':'B_augmented','fold':fi,'seed':seed,'epoch':epoch,'training_loss':float(val)})
 fit_rows.append({'model':'B_augmented','fold':fi,'seed':seed,'n_train_geometries':len(tridx),'unique_rotation_views':nviews,'n_training_rows':len(X),'epochs':int(model.n_iter_),'fit_seconds':elapsed,'checkpoint':str(cp)})
 return bundle

def predict_one(bundle,ds):
 y=y_predict(bundle,x_features(ds,wl)).reshape(len(ds),21,29)
 return decode29(y)
def predict_six(bundle,ds):
 cs=[];ps=[]
 for k in range(6):
  dk=np.roll(ds,k,axis=1);c,p=predict_one(bundle,dk)
  cs.append(c*np.exp(+2j*np.pi*orders*k/6.0).reshape(1,1,7,1));ps.append(p)
 return np.mean(cs,axis=0),np.mean(ps,axis=0),np.stack(cs),np.stack(ps)

for fi,fold in folds.items():
 trids=sorted(fold['outer_train']);vaids=sorted(fold['outer_validation_development'])
 tridx=np.array([idx[c] for c in trids],int);vaidx=np.array([idx[c] for c in vaids],int)
 existing=np.load(PS/f'FOLD{fi}_PREDICTIONS.npz',allow_pickle=False)
 # Preserve old fixed validation order for byte-level prediction parity.
 va_old=np.asarray(existing['va'],int);vaids_old=[ids[i] for i in va_old]
 assert set(vaids_old)==set(vaids)
 for si,seed in enumerate((17,29,43)):
  base_path=(BASE/f'NN_fold{fi}_seed{seed}.joblib') if seed in (17,29) else (PS/f'Joint29_fold{fi}_seed43.joblib')
  base=joblib.load(base_path);rawC,rawP=predict_one(base,D[vaidx])
  # Audit original predictions against the prior saved fold output, never retrain A.
  in_old_order=np.array([vaidx[list(vaids).index(cid)] for cid in vaids_old])
  c_old,p_old=predict_one(base,D[in_old_order])
  c_expect=existing['C_seeds'][si];p_expect=existing['Joint_P_seeds'][si]
  diffC=float(np.max(np.abs(c_old-c_expect)));diffP=float(np.max(np.abs(p_old-p_expect)))
  assert diffC<1e-10 and diffP<1e-10,(fi,seed,diffC,diffP)
  raw_views['A_original'][(fi,seed)]=(rawC,rawP)
  ensC,ensP,viewC,viewP=predict_six(base,D[vaidx])
  raw_views['C_six_view'][(fi,seed)]=(viewC,viewP)
  preds['A_original'][(fi,seed)]=(rawC,rawP)
  preds['C_six_view'][(fi,seed)]=(ensC,ensP)
  aug=fit_augmented(fi,seed,tridx)
  bC,bP=predict_one(aug,D[vaidx]);preds['B_augmented'][(fi,seed)]=(bC,bP)
  raw_views['B_augmented'][(fi,seed)]=(bC,bP)
  dC,dP,dviewC,dviewP=predict_six(aug,D[vaidx]);preds['D_augmented_six_view'][(fi,seed)]=(dC,dP)
  raw_views['D_augmented_six_view'][(fi,seed)]=(dviewC,dviewP)
  # Equivariance discrepancy for raw predictors and exact group-projection diagnostic for C/D.
  base_viewC,base_viewP=raw_views['C_six_view'][(fi,seed)]
  for name,basec,basep,vc,vp in [('A_original',rawC,rawP,base_viewC,base_viewP),('B_augmented',bC,bP,dviewC,dviewP)]:
   cden=max(float(np.linalg.norm(basec)),1e-30);pden=max(float(np.linalg.norm(basep)),1e-30);errs=[]
   for k in range(1,6):
    target=basec*np.exp(-2j*np.pi*orders*k/6.0).reshape(1,1,7,1)
    errs.append(float(np.linalg.norm(vc[k]-target)/cden))
   perr=max(float(np.linalg.norm(vp[k]-basep)/pden) for k in range(1,6))
   equiv_rows.append({'model':name,'fold':fi,'seed':seed,'complex_equivariance_relative_l2_mean_k1_5':float(np.mean(errs)),'complex_equivariance_relative_l2_max_k1_5':float(max(errs)),'P_scale_rotation_relative_l2_max_k1_5':perr})
  # Group averaging is equivariant by construction; numerical reindexing residual is recorded.
  for name,vc,vp in [('C_six_view',base_viewC,base_viewP),('D_augmented_six_view',dviewC,dviewP)]:
   emax=0.0;pmax=0.0
   c0=np.mean([vc[k]*np.exp(+2j*np.pi*orders*k/6.0).reshape(1,1,7,1) for k in range(6)],axis=0)
   p0=np.mean(vp,axis=0)
   for shift in range(1,6):
    # F(T^shift D) expressed in its own reference; compare with T^shift F(D).
    cshift=np.mean([vc[(j+shift)%6]*np.exp(+2j*np.pi*orders*j/6.0).reshape(1,1,7,1) for j in range(6)],axis=0)
    pshift=np.mean([vp[(j+shift)%6] for j in range(6)],axis=0)
    emax=max(emax,float(np.linalg.norm(cshift-c0*np.exp(-2j*np.pi*orders*shift/6.0).reshape(1,1,7,1))/max(np.linalg.norm(c0),1e-30)))
    pmax=max(pmax,float(np.linalg.norm(pshift-p0)/max(np.linalg.norm(p0),1e-30)))
   equiv_rows.append({'model':name,'fold':fi,'seed':seed,'complex_equivariance_relative_l2_mean_k1_5':emax,'complex_equivariance_relative_l2_max_k1_5':emax,'P_scale_rotation_relative_l2_max_k1_5':pmax})
  print(f'FOLD_SEED_DONE fold={fi} seed={seed} baseline_parity_C={diffC:.3g} P={diffP:.3g}',flush=True)

# Metric contract is copied from the prior frozen 272G evaluation: same 124 IDs,
# same fold-level reference channels, H2 decoder, power routing and Top20 tie rule.
def evaluate(name,fi,seed,vaids,cc,pp):
 vi=np.array([idx[c] for c in vaids]);ct=C[vi];pt=P[vi];et=eta_truth[vi];at=abs_truth[vi]
 h=H.reconstruct_h2(cc,pp,decoder);ep=h['eta'];ap=h['absolute_order']
 refpath=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'STAGE_50'/f'PHASE_REFERENCE_fold{fi}.json'
 ref=np.asarray(json.loads(refpath.read_text(encoding='utf-8-sig'))['channel_flat_indices'],int)
 tf=ct.reshape(len(vi),21,14);pf=cc.reshape(len(vi),21,14)
 rr=np.broadcast_to(ref[None,:,None],(len(vi),21,1));tr=np.take_along_axis(tf,rr,axis=2);pr=np.take_along_axis(pf,rr,axis=2)
 floor=.001*np.abs(tf).max(axis=2,keepdims=True)
 mask=(np.abs(tf)>=floor)&(np.abs(tr)>=floor)&(np.abs(pf)>1e-12)&(np.abs(pr)>1e-12)&(np.arange(14)[None,None,:]!=ref[None,:,None])
 phase=np.abs(np.angle(pf*np.conj(pr)*np.conj(tf*np.conj(tr))));weight=np.abs(tf)**2
 pplus=at[:,:,4];predplus=ap[:,:,4];true450=pplus[:,10];pred450=predplus[:,10]
 rho=float(spearmanr(true450,pred450).statistic) if np.std(pred450)>1e-14 else float('nan')
 n_top=max(1,int(np.ceil(.2*len(vi))));top=float(len(set(np.argsort(true450)[-n_top:])&set(np.argsort(pred450)[-n_top:]))/n_top)
 errc=cc-ct;tm=np.abs(ct[:,:,:,1]);tm_pred=np.abs(cc[:,:,:,1]);train_idx=np.array([idx[x] for x in sorted(folds[fi]['outer_train'])]);train_tm=np.abs(C[train_idx,:,:,1]);strong=float(np.quantile(train_tm,.75))
 strong_mask=tm>=strong
 row={'model':name,'fold':fi,'seed':seed,'n_geometry':len(vi),'complex_NRMSE':float(np.linalg.norm(errc)/max(np.linalg.norm(ct),1e-30)),
  'complex_MAE':float(np.abs(errc).mean()),'real_MAE':float(np.abs(errc.real).mean()),'imag_MAE':float(np.abs(errc.imag).mean()),
  'TE_complex_NRMSE':float(np.linalg.norm(errc[:,:,:,0])/max(np.linalg.norm(ct[:,:,:,0]),1e-30)),
  'TM_complex_NRMSE':float(np.linalg.norm(errc[:,:,:,1])/max(np.linalg.norm(ct[:,:,:,1]),1e-30)),
  'TM_magnitude_MAE':float(np.abs(tm_pred-tm).mean()),'TM_strong_q75_train_magnitude_MAE':float(np.abs(tm_pred-tm)[strong_mask].mean()) if strong_mask.any() else float('nan'),
  'TM_strong_threshold_train_q75':strong,'routing_MAE_all7':float(np.abs(ep-et).mean()),
  'relative_phase_weighted_deg':float(np.sum(weight[mask]*phase[mask])/max(np.sum(weight[mask]),1e-30)*180/np.pi),
  'phase_active_channel_count':int(mask.sum()),'P_scale_MAE':float(np.abs(pp-pt).mean()),'P_scale_RMSE':float(np.sqrt(np.mean((pp-pt)**2))),
  'P_scale_bias':float(np.mean(pp-pt)),'eta_plus_MAE':float(np.abs(ep[:,:,4]-et[:,:,4]).mean()),'Pplus_MAE':float(np.abs(predplus-pplus).mean()),
  'Pplus_RMSE':float(np.sqrt(np.mean((predplus-pplus)**2))),'rho450':rho,'Top20_recall450':top}
 order=[]
 for mi,m in enumerate(orders):
  for pi,pol in enumerate(('TE','TM')):
   zerr=errc[:,:,mi,pi];truth=ct[:,:,mi,pi];magerr=np.abs(np.abs(cc[:,:,mi,pi])-np.abs(truth))
   ref_ch=ref
   true_ref=np.take_along_axis(tf,np.broadcast_to(ref_ch[None,:,None],(len(vi),21,1)),axis=2)[:,:,0]
   pred_ref=np.take_along_axis(pf,np.broadcast_to(ref_ch[None,:,None],(len(vi),21,1)),axis=2)[:,:,0]
   channel=mi*2+pi
   phase_rel=np.abs(np.angle(cc[:,:,mi,pi]*np.conj(pred_ref)*np.conj(truth*np.conj(true_ref))))
   phase_weight=np.abs(truth)**2
   phase_mask=(np.abs(truth)>=floor[:,:,0])&(np.abs(true_ref)>floor[:,:,0])&(np.abs(pred_ref)>1e-12)&(channel!=ref_ch)
   order.append({'model':name,'fold':fi,'seed':seed,'order_m':int(m),'polarization':pol,
    'complex_NRMSE':float(np.linalg.norm(zerr)/max(np.linalg.norm(truth),1e-30)),
    'complex_MAE':float(np.abs(zerr).mean()),'magnitude_MAE':float(magerr.mean()),
    'magnitude_truth_mean':float(np.abs(truth).mean()),'magnitude_truth_q90':float(np.quantile(np.abs(truth),.9)),
    'relative_phase_weighted_deg':float(np.sum(phase_weight[phase_mask]*phase_rel[phase_mask])/max(np.sum(phase_weight[phase_mask]),1e-30)*180/np.pi) if phase_mask.any() else float('nan')})
 return row,order,h

all_oof_ids=global_order
for name in preds:
 arrC=np.zeros((3,124,21,7,2),complex);arrP=np.zeros((3,124,21),float);seen=np.zeros(124,bool)
 model_rows=[]
 for fi,fold in folds.items():
  vaids=sorted(fold['outer_validation_development'])
  for si,seed in enumerate((17,29,43)):
   cc,pp=preds[name][(fi,seed)]
   row,orders_out,h=evaluate(name,fi,seed,vaids,cc,pp);metric_rows.append(row);order_rows.extend(orders_out)
   for j,cid in enumerate(vaids):
    g=global_idx[cid];arrC[si,g]=cc[j];arrP[si,g]=pp[j];seen[g]=True
 assert seen.all(),(name,seen.sum())
 # Save per seed OOF tensors, case ID order, and their frozen-H2 outputs.
 eta_arr=np.zeros((3,124,21,7));abs_arr=np.zeros_like(eta_arr)
 for si in range(3):
  hh=H.reconstruct_h2(arrC[si],arrP[si],decoder);eta_arr[si]=hh['eta'];abs_arr[si]=hh['absolute_order']
 np.savez_compressed(OUT/f'CYCLIC_OOF_{name}.npz',case_ids=np.asarray(all_oof_ids),seeds=np.asarray((17,29,43)),C=arrC,P_scale=arrP,eta=eta_arr,absolute_order=abs_arr)
 pred_by_model[name]={'C':arrC,'P':arrP,'eta':eta_arr,'absolute':abs_arr}
# Compare fixed-epoch loss curves for the same baseline and augmented models.
for fi in range(1,5):
 for seed in (17,29,43):
  p=(BASE/f'NN_fold{fi}_seed{seed}.joblib') if seed in (17,29) else (PS/f'Joint29_fold{fi}_seed43.joblib')
  model=joblib.load(p)['model']
  for epoch,value in enumerate(model.loss_curve_,1):loss_rows.append({'model':'A_original','fold':fi,'seed':seed,'epoch':epoch,'training_loss':float(value)})
write_csv(OUT/'CYCLIC_AUGMENTATION_MODEL_COMPARISON.csv',metric_rows)
write_csv(OUT/'CYCLIC_ORDER_POLARIZATION_METRICS.csv',order_rows)
write_csv(OUT/'CYCLIC_EQUIVARIANCE_DIAGNOSTICS.csv',equiv_rows)
write_csv(OUT/'CYCLIC_FIT_LEDGER.csv',fit_rows)
write_csv(OUT/'CYCLIC_TRAINING_CURVES.csv',loss_rows)

# Paired fold/seed deltas plus frozen-H2 metrics across the full original OOF set.
paired=[]
for fi,fold in folds.items():
 vaids=sorted(fold['outer_validation_development'])
 for seed in (17,29,43):
  for a,b,label in [('A_original','B_augmented','B_minus_A'),('C_six_view','D_augmented_six_view','D_minus_C')]:
   ra=next(r for r in metric_rows if r['model']==a and r['fold']==fi and r['seed']==seed)
   rb=next(r for r in metric_rows if r['model']==b and r['fold']==fi and r['seed']==seed)
   paired.append({'contrast':label,'fold':fi,'seed':seed,'n_geometry':ra['n_geometry'],
    **{f'delta_{m}':rb[m]-ra[m] for m in ('complex_NRMSE','TM_magnitude_MAE','TM_strong_q75_train_magnitude_MAE','routing_MAE_all7','relative_phase_weighted_deg','P_scale_MAE','eta_plus_MAE','Pplus_MAE','rho450','Top20_recall450')}})
write_csv(OUT/'CYCLIC_PAIRED_DELTAS.csv',paired)

summary={};gate_results={}
for name,arr in pred_by_model.items():
 summary[name]={}
 for si,seed in enumerate((17,29,43)):
  rows=[r for r in metric_rows if r['model']==name and r['seed']==seed]
  n=sum(r['n_geometry'] for r in rows)
  pooled={'seed':seed,'fold_mean':{m:float(np.mean([r[m] for r in rows])) for m in ('complex_NRMSE','complex_MAE','real_MAE','imag_MAE','TE_complex_NRMSE','TM_complex_NRMSE','TM_magnitude_MAE','TM_strong_q75_train_magnitude_MAE','routing_MAE_all7','relative_phase_weighted_deg','P_scale_MAE','P_scale_RMSE','P_scale_bias','eta_plus_MAE','Pplus_MAE','Pplus_RMSE','rho450','Top20_recall450')},
   'oof_pooled':{}}
  c=arr['C'][si];p=arr['P'][si];truth_c=np.asarray([C[idx[cid]] for cid in all_oof_ids]);truth_p=np.asarray([P[idx[cid]] for cid in all_oof_ids]);truth_abs=np.asarray([abs_truth[idx[cid]] for cid in all_oof_ids]);truth_eta=np.asarray([eta_truth[idx[cid]] for cid in all_oof_ids]);hh=H.reconstruct_h2(c,p,decoder)
  true450=truth_abs[:,10,4];pred450=hh['absolute_order'][:,10,4];nn=max(1,int(np.ceil(.2*len(all_oof_ids))))
  pooled['oof_pooled']={'complex_NRMSE':float(np.linalg.norm(c-truth_c)/np.linalg.norm(truth_c)),
   'complex_MAE':float(np.abs(c-truth_c).mean()),'P_scale_MAE':float(np.abs(p-truth_p).mean()),
   'routing_MAE_all7':float(np.abs(hh['eta']-truth_eta).mean()),
   'eta_plus_MAE':float(np.abs(hh['eta'][:,:,4]-truth_eta[:,:,4]).mean()),
   'Pplus_MAE':float(np.abs(hh['absolute_order'][:,:,4]-truth_abs[:,:,4]).mean()),
   'rho450':float(spearmanr(true450,pred450).statistic),
   'Top20_recall450':float(len(set(np.argsort(true450)[-nn:])&set(np.argsort(pred450)[-nn:]))/nn)}
  summary[name][str(seed)]=pooled
 # H1 is evaluation evidence only; original H1 rules and thresholds remain frozen.
 Cmean=arr['C'].mean(axis=0);Pmean=arr['P'].mean(axis=0)
 tc=np.asarray([C[idx[cid]] for cid in all_oof_ids]);tp=np.asarray([P[idx[cid]] for cid in all_oof_ids]);te=np.asarray([eta_truth[idx[cid]] for cid in all_oof_ids]);ta=np.asarray([abs_truth[idx[cid]] for cid in all_oof_ids])
 gate_results[name]=H.evaluate_original_h1(tc,Cmean,tp,Pmean,te,ta,decoder=decoder)
write_json(OUT/'CYCLIC_MODEL_SUMMARY.json',summary)
write_json(OUT/'CYCLIC_H1_GATE_RESULTS.json',gate_results)

# H1 thresholds and finite training curves/checkpoint provenance; hashes are recorded
# because checkpoint identity is explicitly part of this task's reproducibility record.
write_json(OUT/'FROZEN_H1_THRESHOLDS.json',H.load_h1_authority())
source_path=OUT/'RUN_CYCLIC_AUGMENTATION_COMPARISON.py'
hash_rows=[]
for p in sorted(list(OUT.glob('B_AUGMENTED_fold*_seed*.joblib'))+
                [BASE/f'NN_fold{fi}_seed{s}.joblib' for fi in range(1,5) for s in (17,29)]+
                [PS/f'Joint29_fold{fi}_seed43.joblib' for fi in range(1,5)]+[source_path,OUT/'CYCLIC_MODEL_CONFIG.json']):
 if p.exists():hash_rows.append({'file':str(p),'size_bytes':p.stat().st_size,'sha256':file_sha(p),'role':'augmentation_checkpoint' if p.name.startswith('B_') else ('baseline_checkpoint' if p.suffix=='.joblib' else 'reproducibility_source_or_config')})
write_csv(OUT/'CYCLIC_CHECKPOINT_SHA256.csv',hash_rows)
write_json(OUT/'CYCLIC_RUN_COMPLETE.json',{'status':'PASS','new_augmented_fits':len(fit_rows),'expected_augmented_fits':12,'solver_entries':0,'fdtd_runs':0,'new_ml_fit_count':len(fit_rows),'reused_baseline_checkpoints':12,'cv_folds':4,'seeds':[17,29,43],'validation_geometries':124,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'elapsed_fit_seconds':float(sum(r['fit_seconds'] for r in fit_rows))})
print(json.dumps({'status':'PASS','fit_count':len(fit_rows),'fit_seconds':sum(r['fit_seconds'] for r in fit_rows),'validation_geometries':124,'models':summary,'out':str(OUT)},ensure_ascii=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()))
