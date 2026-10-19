"""Zero-solver 272G development study: grouped inner early stopping and P_scale residuals."""
import os
for _k in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_k]='2'
os.environ['CUDA_VISIBLE_DEVICES']=''
from pathlib import Path
import csv,json,time,sys,warnings,collections
import numpy as np
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.neural_network import MLPRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
from sklearn.exceptions import ConvergenceWarning
from threadpoolctl import threadpool_limits

R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
Q=R/'reports'/'coupling'
B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1'/'STAGE_50'
P=Q/'APCD_COUPLING_272G_PSCALE_DECOUPLING_V1'
OLD=Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1'/'ML_UPDATE'
TASK=Q/'APCD_COUPLING_CLEANUP_FAST_CLOSE_AND_FORWARD_RESUME_V1'
if TASK.exists():
    unexpected=[p.name for p in TASK.iterdir() if p.name not in {'RUN_OFFLINE_EXPERIMENTS.py','PREREGISTRATION.json'}]
    if unexpected: raise RuntimeError('task_output_exists_refuse_overwrite:'+','.join(unexpected))
TASK.mkdir(parents=True,exist_ok=True)

def readj(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def putj(name,obj):
    p=TASK/name;tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False,default=lambda a:a.tolist() if hasattr(a,'tolist') else a.item()),encoding='utf-8');os.replace(tmp,p)
def putcsv(name,rows):
    if not rows: return
    p=TASK/name
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in rows for k in row)));w.writeheader();w.writerows(rows)

z=np.load(B/'COMPLEX_DATASET.npz',allow_pickle=False)
ids=np.asarray(z['case_ids']).astype(str);idix={s:i for i,s in enumerate(ids)}
assert len(ids)==272 and len(idix)==272 and len({tuple(x) for x in z['D_nm']})==272
lam=np.asarray(z['wavelengths_nm'],dtype=float)
assert np.array_equal(lam,np.arange(440,461,dtype=float))
assert np.allclose(z['target29'][:,:,28],np.log(z['P_scale']),rtol=1e-12,atol=1e-12)
folds=readj(B/'FOLDS.json');oldfolds=readj(OLD/'FOLDS.json')
families=readj(B/'LOCAL_FAMILY_COMPONENTS.json');fam_of={}
for j,comp in enumerate(families):
    for case in comp:
        if case in fam_of: raise RuntimeError('family_component_duplicate:'+case)
        fam_of[case]=f'local_family_{j+1:02d}'
def family(case): return fam_of.get(case,'singleton:'+case)
def features(ix): return np.column_stack((np.repeat(z['D_nm'][ix],len(lam),axis=0),np.tile(lam,len(ix))))
valids=[];fold_info=[];fold_arrays=[];fitrows=[];curve_rows=[];p_rows=[];forward_rows=[];seed_rows=[];ridge_timing=[]
decoder=None
sys.path.insert(0,str(R/'scripts'/'coupling_ml'))
from k6_v2_pipeline import h1 as H
decoder=H.load_h2_decoder()

def mcfg(seed,hidden,max_iter):
    return MLPRegressor(hidden_layer_sizes=hidden,activation='tanh',solver='adam',max_iter=max_iter,
        early_stopping=False,random_state=int(seed),batch_size=256,tol=0.0,n_iter_no_change=max_iter+1,
        warm_start=False,alpha=0.0001,learning_rate_init=0.001)

def early_refit(ix_train, ix_val, ycube, seed, foldno, kind, hidden, max_epochs=800, patience=60):
    """Group-only inner stopping; fit preprocessors separately inside and outside the inner split."""
    n=len(ix_train);groups=np.asarray([family(ids[i]) for i in ix_train])
    splitter=GroupShuffleSplit(n_splits=1,test_size=0.18,random_state=seed+1009*foldno+(1 if kind=='Joint29' else 503))
    ip,it=next(splitter.split(np.arange(n),groups=groups))
    inner_train_groups=set(groups[ip]);inner_val_groups=set(groups[it])
    if inner_train_groups & inner_val_groups: raise RuntimeError('inner_family_leakage')
    ix_i_train=ix_train[ip];ix_i_val=ix_train[it]
    xitr=features(ix_i_train);xiv=features(ix_i_val)
    yitr=ycube[ix_i_train].reshape(-1,ycube.shape[-1]);yiv=ycube[ix_i_val].reshape(-1,ycube.shape[-1])
    sx_i=StandardScaler().fit(xitr);sy_i=StandardScaler().fit(yitr)
    Xtr=sx_i.transform(xitr);Ytr=sy_i.transform(yitr);Xiv=sx_i.transform(xiv);Yiv=sy_i.transform(yiv)
    chooser=mcfg(seed,hidden,1);chooser.warm_start=True
    best=float('inf');best_epoch=0;stale=0;history=[];t0=time.perf_counter()
    with threadpool_limits(limits=2):
        for epoch in range(1,max_epochs+1):
            chooser.partial_fit(Xtr,Ytr)
            vp=chooser.predict(Xiv)
            if np.ndim(vp)==1: vp=np.asarray(vp).reshape(-1,1)
            loss=float(mean_squared_error(Yiv,vp))
            trloss=float(chooser.loss_)
            history.append((epoch,trloss,loss))
            if loss < best-1e-4:
                best=loss;best_epoch=epoch;stale=0
            else: stale+=1
            if epoch%10==0 or epoch==1:
                curve_rows.append({'model':kind,'fold':foldno,'seed':seed,'epoch':epoch,'inner_train_loss':trloss,'inner_validation_mse':loss})
            if stale>=patience: break
    stop_reason='patience' if stale>=patience else 'max_epochs'
    if best_epoch<1: raise RuntimeError('early_stopping_no_best_epoch')
    xall=features(ix_train);yall=ycube[ix_train].reshape(-1,ycube.shape[-1])
    sx=StandardScaler().fit(xall);sy=StandardScaler().fit(yall)
    final=mcfg(seed,hidden,best_epoch)
    t1=time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',ConvergenceWarning)
        final_y=sy.transform(yall)
        if final_y.shape[1]==1: final_y=final_y.ravel()
        with threadpool_limits(limits=2): final.fit(sx.transform(xall),final_y)
    elapsed=time.perf_counter()-t0
    xval=features(ix_val);scaled=final.predict(sx.transform(xval))
    if np.ndim(scaled)==1: scaled=np.asarray(scaled).reshape(-1,1)
    pred=sy.inverse_transform(scaled).reshape(len(ix_val),len(lam),ycube.shape[-1])
    fitrows.append({'model':kind,'fold':foldno,'seed':seed,'inner_train_geometries':len(ip),'inner_validation_geometries':len(it),
        'inner_family_overlap':0,'max_epochs':max_epochs,'patience':patience,'selected_epoch':best_epoch,'stop_reason':stop_reason,
        'best_inner_validation_mse':best,'final_fit_epochs':int(final.n_iter_),'final_training_loss':float(final.loss_),
        'fit_seconds_including_inner_selection':elapsed})
    return pred,{'selected_epoch':best_epoch,'stop_reason':stop_reason,'best_inner_validation_mse':best,'history':history,
        'final_loss':float(final.loss_),'seconds':elapsed}

def ridge_residual(ix_train,ix_val,mu):
    t0=time.perf_counter()
    dscale=StandardScaler().fit(z['D_nm'][ix_train])
    def px(ix):
        d=dscale.transform(z['D_nm'][ix]);ds=np.repeat(d,len(lam),axis=0);w=np.tile((lam-450.0)/10.0,len(ix))
        return np.column_stack((ds,w,w*w,ds*w[:,None]))
    xtr=px(ix_train);xv=px(ix_val)
    logp=np.log(z['P_scale']);yt=(logp[ix_train]-mu[None,:]).reshape(-1,1)
    sx=StandardScaler().fit(xtr);sy=StandardScaler().fit(yt)
    model=Ridge(alpha=1.0);model.fit(sx.transform(xtr),sy.transform(yt).ravel())
    r=sy.inverse_transform(model.predict(sx.transform(xv)).reshape(-1,1)).reshape(len(ix_val),len(lam))
    ridge_timing.append({'fold':len(ridge_timing)+1,'seconds':time.perf_counter()-t0,'alpha':1.0,'feature_count':14})
    return np.exp(mu[None,:]+r)

def pscale_rows(name,foldno,truth,pred,train_threshold):
    e=pred-truth;peak=np.argmax(truth,axis=1);atpeak=e[np.arange(len(truth)),peak]
    high=truth>=train_threshold[None,:];slope=np.diff(truth,axis=1);pslope=np.diff(pred,axis=1);active=abs(slope)>1e-12
    vt=np.var(truth,axis=0,ddof=1);vp=np.var(pred,axis=0,ddof=1)
    row={'model':name,'fold':foldno,'n':len(truth),'P_scale_MAE':float(abs(e).mean()),'P_scale_RMSE':float(np.sqrt(np.mean(e**2))),
      'P_scale_bias':float(e.mean()),'geometry_variance_ratio':float(vp.sum()/vt.sum()),
      'centered_spectral_RMSE':float(np.sqrt(np.mean(((pred-pred.mean(axis=1,keepdims=True))-(truth-truth.mean(axis=1,keepdims=True)))**2))),
      'true_peak_MAE':float(abs(atpeak).mean()),'true_peak_bias':float(atpeak.mean()),
      'train_q90_region_count':int(high.sum()),'train_q90_region_MAE':float(abs(e[high]).mean()) if high.any() else None,
      'train_q90_region_bias':float(e[high].mean()) if high.any() else None,
      'spectral_slope_sign_accuracy':float(np.mean(np.sign(slope[active])==np.sign(pslope[active]))) if active.any() else None}
    p_rows.append(row)
    return row

def phase_metric(ct,cp,foldno):
    aa=ct.reshape(len(ct),21,14);bb=cp.reshape(len(cp),21,14)
    ref=np.asarray(readj(B/f'PHASE_REFERENCE_fold{foldno}.json')['channel_flat_indices'],dtype=int)
    if ref.shape!=(21,):raise RuntimeError('phase_reference_shape')
    rr=np.broadcast_to(ref[None,:,None],(len(ct),21,1));ar=np.take_along_axis(aa,rr,axis=2);br=np.take_along_axis(bb,rr,axis=2)
    floor=.001*np.abs(aa).max(axis=2,keepdims=True)
    mask=(np.abs(aa)>=floor)&(np.abs(ar)>=floor)&(np.abs(bb)>1e-12)&(np.abs(br)>1e-12)&(np.arange(14)[None,None,:]!=ref[None,:,None])
    wt=np.abs(aa)**2;pe=np.abs(np.angle(bb*np.conj(br)*np.conj(aa*np.conj(ar))))
    return float((wt[mask]*pe[mask]).sum()*180/np.pi/wt[mask].sum()),float(wt[mask].sum()),float((wt[mask]*pe[mask]).sum())

def forward_metric(name,foldno,ct,cp,pt,pp,eta_true,absolute_true):
    h=H.reconstruct_h2(cp,pp,decoder);eta=h['eta'];absolute=h['absolute_order']
    n=len(ct);ordidx=int(np.where(np.asarray(z['orders'])==1)[0][0]);wlidx=int(np.where(lam==450)[0][0])
    rho=float(spearmanr(absolute_true[:,wlidx,ordidx],absolute[:,wlidx,ordidx]).statistic) if np.std(absolute[:,wlidx,ordidx])>1e-14 else None
    kk=int(np.ceil(.2*n));truth_top=set(np.argsort(absolute_true[:,wlidx,ordidx])[-kk:]);pred_top=set(np.argsort(absolute[:,wlidx,ordidx])[-kk:])
    tmidx=int(np.where(np.asarray(z['polarizations']).astype(str)=='TM')[0][0])
    phase_deg,phase_den,phase_num=phase_metric(ct,cp,foldno)
    centered=(absolute[:,:,ordidx]-absolute[:,:,ordidx].mean(axis=1,keepdims=True))-(absolute_true[:,:,ordidx]-absolute_true[:,:,ordidx].mean(axis=1,keepdims=True))
    row={'model':name,'fold':foldno,'n':n,'complex_SSE':float((np.abs(cp-ct)**2).sum()),'complex_energy':float((np.abs(ct)**2).sum()),
      'complex_NRMSE':float(np.linalg.norm(cp-ct)/np.linalg.norm(ct)),'TM_amplitude_MAE':float(np.abs(np.abs(cp[:,:,:,tmidx])-np.abs(ct[:,:,:,tmidx])).mean()),
      'relative_phase_weighted_deg':phase_deg,'phase_weight':phase_den,'phase_weighted_error_rad':phase_num,
      'routing_allorders_MAE':float(np.abs(eta-eta_true).mean()),'eta_plus_MAE':float(np.abs(eta[:,:,ordidx]-eta_true[:,:,ordidx]).mean()),
      'P_scale_MAE':float(np.abs(pp-pt).mean()),'P_scale_bias':float((pp-pt).mean()),
      'Pplus_MAE':float(np.abs(absolute[:,:,ordidx]-absolute_true[:,:,ordidx]).mean()),
      'Pplus_centered_spectral_RMSE':float(np.sqrt(np.mean(centered**2))),'rho450':rho,
      'Top20_recall':float(len(truth_top&pred_top)/kk)}
    forward_rows.append(row);return row

putj('PREREGISTRATION.json',{'task':'APCD_COUPLING_CLEANUP_FAST_CLOSE_AND_FORWARD_RESUME_V1','solver_invocations':0,
 'dataset':'272G COMPLEX_DATASET.npz; existing labels only; no FDTD, Runner, sealed data, or validation-based tuning',
 'primary_validation':'fixed124 geometry IDs and original four old-train-only fold mapping; all 21 wavelengths remain per geometry',
 'outer_split':'existing STAGE_50/FOLDS.json train IDs plus AL16 ML_UPDATE/FOLDS.json heldout_old_ids; existing family_overlap must be zero',
 'inner_split':'GroupShuffleSplit over outer-train geometry IDs only; four frozen local connected family components preserved; 18% groups, deterministic fold/seed-specific split',
 'NN29':'7-64-64-29 tanh Adam; train-fold StandardScaler for X/Y; inner MSE early stop, min improvement 1e-4, patience60, max800 epochs; refit fresh on full outer train for selected epoch; seeds17/29/43',
 'P_scale':'logP common wavelength mean from outer train only; residual targets logP-mu(lambda); Ridge alpha1 on standardized D, lambda, lambda^2 and D*lambda (14 features); MLP 7-32-32-1 tanh with same inner-group early-stop, seeds17/29/43',
 'baseline_reuse':'previous fold OOF from APCD_COUPLING_272G_PSCALE_DECOUPLING_V1 only; no baseline retraining',
 'aggregation':'complex Cartesian arithmetic mean; P_scale arithmetic mean of each seed prediction after exp; Frozen H2 decoder and original normalization; no direct eta/Pplus regression',
 'evidence_scope':'development OOF only; repeated 124 set and adaptive dataset prevent final generalization certification; H1 remains HOLD'})

for fi,f in enumerate(folds):
    foldno=fi+1;tr_ids=list(f['train_ids']);va_ids=list(oldfolds[fi]['heldout_old_ids'])
    if f.get('family_overlap')!=0:raise RuntimeError('frozen_outer_family_overlap_not_zero')
    if set(tr_ids)&set(va_ids):raise RuntimeError('outer_geometry_overlap')
    if {family(x) for x in tr_ids}&{family(x) for x in va_ids}:raise RuntimeError('outer_family_overlap_detected')
    tr=np.array([idix[x] for x in tr_ids],dtype=int);va=np.array([idix[x] for x in va_ids],dtype=int)
    valids.extend(va_ids)
    for s in tr_ids:fold_info.append({'fold':foldno,'role':'outer_train','case_id':s,'family_id':family(s)})
    for s in va_ids:fold_info.append({'fold':foldno,'role':'outer_validation_development','case_id':s,'family_id':family(s)})
    # Inner group split below only sees these outer-train IDs. The outer validation labels are never loaded by early_refit.
    mu=np.mean(np.log(z['P_scale'][tr]),axis=0)
    p_logmean=np.broadcast_to(np.exp(mu)[None,:],(len(va),21)).copy()
    p_physmean=np.broadcast_to(np.mean(z['P_scale'][tr],axis=0)[None,:],(len(va),21)).copy()
    p_ridge=ridge_residual(tr,va,mu)
    p_resid_seeds=[];c_seeds=[];p_joint_seeds=[]
    for seed in (17,29,43):
        pred,_=early_refit(tr,va,z['target29'],seed,foldno,'Joint29',(64,64),max_epochs=800,patience=60)
        cpair=pred[:,:,:28].reshape(len(va),21,7,2,2);cp=cpair[...,0]+1j*cpair[...,1]
        pj=np.exp(pred[:,:,28]);c_seeds.append(cp);p_joint_seeds.append(pj)
        residual_cube=(np.log(z['P_scale'])-mu[None,:])[:,:,None]
        pr,_=early_refit(tr,va,residual_cube,seed,foldno,'PScaleResidualMLP',(32,32),max_epochs=800,patience=60)
        p_resid_seeds.append(np.exp(mu[None,:]+pr[:,:,0]))
    c_seeds=np.asarray(c_seeds);p_joint_seeds=np.asarray(p_joint_seeds);p_resid_seeds=np.asarray(p_resid_seeds)
    if not (np.isfinite(p_resid_seeds).all() and (p_resid_seeds>0).all()):raise RuntimeError('residual_mlp_invalid_physical_pscale')
    # Reuse existing same-fold predictions, validating the exact fixed124 identity list.
    prior=np.load(P/f'FOLD{foldno}_PREDICTIONS.npz',allow_pickle=False)
    if set(ids[prior['va']].astype(str))!=set(va_ids):raise RuntimeError('prior_oof_case_set_mismatch')
    if set(ids[prior['va']].astype(str))!=set(ids[va].astype(str)):raise RuntimeError('prior_oof_index_set_mismatch')
    # Align arrays to current va_ids ordering.
    ppos={s:i for i,s in enumerate(ids[prior['va']].astype(str))};perm=np.array([ppos[s] for s in va_ids],dtype=int)
    oldc=np.asarray(prior['C_seeds'])[:,perm];oldjoint=np.asarray(prior['Joint_P_seeds'])[:,perm]
    oldpmean=np.asarray(prior['PMean'])[perm];oldridge=np.asarray(prior['Ridge'])[perm]
    oldpsnet=np.asarray(prior['PSNet_P_seeds'])[:,perm];oldet=np.asarray(prior['ET3_P_seeds'])[:,perm];oldleaf=np.asarray(prior['Leaf1_P_seeds'])[:,perm]
    c_old=oldc.mean(axis=0);c_new=c_seeds.mean(axis=0)
    # P_scale diagnostics use all predictions but never feed validation labels to fitting.
    pmodels={'PhysicalMean':p_physmean,'LogTrendOnly':p_logmean,'ResidualRidge':p_ridge,
        'ResidualMLP':p_resid_seeds.mean(axis=0),'JointNN3':oldjoint.mean(axis=0),
        'JointPSNet3':oldpsnet.mean(axis=0),'FrozenLeaf1P':oldleaf.mean(axis=0),
        'FrozenET3P':oldet.mean(axis=0),'FrozenDirectRidge':oldridge}
    train_q90=np.quantile(z['P_scale'][tr],.90,axis=0)
    for nm,predp in pmodels.items():pscale_rows(nm,foldno,z['P_scale'][va],predp,train_q90)
    # Full frozen H2 chain; one output is the existing state with the new P estimator, never eta regression.
    candidates={
      'NN3_Current_Joint':(c_old,oldjoint.mean(axis=0)),
      'NN3_Current_ResidualRidge':(c_old,p_ridge),
      'NN3_Current_ResidualMLP':(c_old,p_resid_seeds.mean(axis=0)),
      'NN_EarlyStop_Joint':(c_new,p_joint_seeds.mean(axis=0)),
      'NN_EarlyStop_PhysicalMeanP':(c_new,p_physmean),
      'NN_EarlyStop_LogTrendP':(c_new,p_logmean),
      'NN_EarlyStop_ResidualRidge':(c_new,p_ridge),
      'NN_EarlyStop_ResidualMLP':(c_new,p_resid_seeds.mean(axis=0)),
      'NN_EarlyStop_FrozenLeaf1P':(c_new,oldleaf.mean(axis=0)),
    }
    truth_c=z['C_hat'][va];truth_p=z['P_scale'][va];truth_eta=z['eta_H2'][va];truth_abs=z['absolute_H2'][va]
    for name,(cp,pp) in candidates.items():forward_metric(name,foldno,truth_c,cp,truth_p,pp,truth_eta,truth_abs)
    # Seed-wise outputs retained for honest stability accounting.
    for si,seed in enumerate((17,29,43)):
        forward_metric(f'NN_EarlyStop_seed{seed}',foldno,truth_c,c_seeds[si],truth_p,p_joint_seeds[si],truth_eta,truth_abs)
        forward_metric(f'NN_EarlyStop_ResidualMLP_seed{seed}',foldno,truth_c,c_seeds[si],truth_p,p_resid_seeds[si],truth_eta,truth_abs)
        seed_rows.append({'fold':foldno,'seed':seed,'NN29_C_complex_NRMSE':float(np.linalg.norm(c_seeds[si]-truth_c)/np.linalg.norm(truth_c)),
          'NN29_P_scale_MAE':float(np.abs(p_joint_seeds[si]-truth_p).mean()),
          'ResidualMLP_P_scale_MAE':float(np.abs(p_resid_seeds[si]-truth_p).mean())})
    fold_arrays.append({'fold':foldno,'va':va,'case_ids':va_ids,'C_early_seeds':c_seeds,'P_early_joint_seeds':p_joint_seeds,
        'P_residual_mlp_seeds':p_resid_seeds,'P_residual_ridge':p_ridge,'C_current_seeds':oldc,'P_current_joint_seeds':oldjoint})
    print('FOLD_COMPLETE',foldno,'n_train',len(tr),'n_validation',len(va),'fit_count',len(fitrows),flush=True)

if len(valids)!=124 or len(set(valids))!=124:raise RuntimeError('fixed124_validation_identity_mismatch')
putcsv('NN_EARLY_STOPPING_FITS.csv',fitrows);putcsv('NN_EARLY_STOPPING_CURVES.csv',curve_rows);putcsv('FOLD_IDENTITY.csv',fold_info)
putcsv('PSCALE_RESIDUAL_FOLD_METRICS.csv',p_rows);putcsv('FORWARD_MODEL_FOLD_METRICS.csv',forward_rows);putcsv('FORWARD_MODEL_SEED_STABILITY.csv',seed_rows)

def pool(rows,groupkey):
 out=[]
 for name in dict.fromkeys(r[groupkey] for r in rows):
  a=[r for r in rows if r[groupkey]==name];row={groupkey:name,'n':sum(x['n'] for x in a)}
  for k in a[0]:
   if k in (groupkey,'fold','seed','n'):continue
   vals=[x[k] for x in a if x.get(k) is not None]
   if not vals:row[k]=None
   elif k in ('rho450','Top20_recall'):row[k]=float(np.mean(vals))
   elif k=='complex_NRMSE':row[k]=float(np.sqrt(sum(x['complex_SSE'] for x in a)/sum(x['complex_energy'] for x in a)))
   elif k=='relative_phase_weighted_deg':row[k]=float(sum(x['phase_weighted_error_rad'] for x in a)/sum(x['phase_weight'] for x in a)*180/np.pi)
   elif k in ('complex_SSE','complex_energy','phase_weight','phase_weighted_error_rad'):row[k]=float(sum(x[k] for x in a))
   else:row[k]=float(sum(x[k]*x['n'] for x in a if x.get(k) is not None)/sum(x['n'] for x in a if x.get(k) is not None))
  out.append(row)
 return out

psummary=pool(p_rows,'model');fsummary=pool(forward_rows,'model')
putcsv('PSCALE_RESIDUAL_MODEL_COMPARISON.csv',psummary);putcsv('FORWARD_MODEL_COMPARISON.csv',fsummary)
allva=np.concatenate([d['va'] for d in fold_arrays]);c_es=np.concatenate([d['C_early_seeds'] for d in fold_arrays],axis=1);p_es=np.concatenate([d['P_early_joint_seeds'] for d in fold_arrays],axis=1);p_rm=np.concatenate([d['P_residual_mlp_seeds'] for d in fold_arrays],axis=1);p_rr=np.concatenate([np.broadcast_to(d['P_residual_ridge'][None,...],(3,*d['P_residual_ridge'].shape)) for d in fold_arrays],axis=1)
truth_c=z['C_hat'][allva];truth_p=z['P_scale'][allva];truth_eta=z['eta_native'][allva];truth_abs=truth_eta*truth_p[:,:,None]
h1={}
for name,pp in [('NN_EarlyStop_Joint',p_es),('NN_EarlyStop_ResidualRidge',p_rr),('NN_EarlyStop_ResidualMLP',p_rm)]:
 h=H.evaluate_original_h1(truth_c,c_es,truth_p,pp,truth_eta,truth_abs,decoder=decoder)
 h1[name]={'gates':h['gates'],'production_admission':h['production_admission'],'seed_stability_status':h['seed_stability_status'],
    'aggregate':h['aggregate'],'seed_state_median_std':h['seed_state_median_std'],'h1_gate_sha256':h['h1_gate_sha256'],'h2_decoder_sha256':h['h2_decoder_sha256']}
prior_h1=readj(P/'H1_SUMMARY.json')
putj('H1_DEVELOPMENT_DIAGNOSTIC.json',{'scope':'fixed 124 development OOF, not independent confirmation','existing_NN3':prior_h1.get('NN3_Joint'),**h1})
arrays={'validation_case_ids':ids[allva],'C_early_seeds':c_es,'P_early_joint_seeds':p_es,'P_residual_mlp_seeds':p_rm,'P_residual_ridge':np.concatenate([d['P_residual_ridge'] for d in fold_arrays]),'C_current_seeds':np.concatenate([d['C_current_seeds'] for d in fold_arrays],axis=1),'P_current_joint_seeds':np.concatenate([d['P_current_joint_seeds'] for d in fold_arrays],axis=1)}
np.savez_compressed(TASK/'OOF_PREDICTIONS.npz',**arrays)
putj('RUN_METADATA.json',{'status':'OFFLINE_DEVELOPMENT_COMPLETE','dataset_geometries':272,'fixed_validation_geometries':124,
  'fixed_fold_sizes':[len(x['case_ids']) for x in fold_arrays],'inner_family_grouped':True,'all_wavelengths_grouped':True,
  'nn29_fit_count':sum(x['model']=='Joint29' for x in fitrows),'pscale_residual_mlp_fit_count':sum(x['model']=='PScaleResidualMLP' for x in fitrows),
  'ridge_fold_fit_count':len(ridge_timing),'new_fdt_count':0,'runner_modified':False,'sealed_access':False,
  'optimizer_stop_reasons':dict(collections.Counter(x['stop_reason'] for x in fitrows)),
  'mean_selected_epoch_by_model':{k:float(np.mean([x['selected_epoch'] for x in fitrows if x['model']==k])) for k in ('Joint29','PScaleResidualMLP')},
  'ridge_fit_seconds':ridge_timing,'H1':'HOLD','FAST':'272G'})
putj('EXPERIMENT_COMPLETE.json',{'complete':True,'fit_rows':len(fitrows),'curve_samples':len(curve_rows),'p_scale_fold_rows':len(p_rows),'forward_fold_rows':len(forward_rows),'validation_ids':124,'new_fdt':0})
print('EXPERIMENT_COMPLETE',json.dumps({'fit_rows':len(fitrows),'p_scale_rows':len(p_rows),'forward_rows':len(forward_rows),'outputs':str(TASK)},ensure_ascii=False),flush=True)
