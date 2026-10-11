"""Four matched phase-only KRR fits; train-only nearest-neighbor kernel scale."""
from pathlib import Path
import sys,json,hashlib,datetime,subprocess,time,os
import numpy as np
import joblib
from sklearn.kernel_ridge import KernelRidge
from k6_v2_pipeline.amended156 import adapter as A,evaluation as V
from k6_v2_pipeline import h1,contracts as C
ROOT=A.ROOT;TASK='COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1';OUT=ROOT/'reports/coupling'/TASK
OLD=ROOT/'reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
AUD=ROOT/'reports/coupling/COUPLING_ML_ORDER_RESOLVED_PHASE_AND_LOCAL_CONDITIONING_AUDIT_V1'
sys.path.insert(0,str(OLD));import structured_phase_pilot as S
D=S.D
def req(v,msg):
    if not v:raise ValueError(msg)
def put(n,d):A.write(OUT/n,d)
def read(n):return A.read(OUT/n)
def pin(p):return {'path':str(p),'sha256':A.sha(p),'bytes':Path(p).stat().st_size}
def stats(x):
    x=np.asarray(x).reshape(-1);x=x[np.isfinite(x)]
    return V.summary(x) if len(x) else {'median':None,'q95':None,'mean':None,'worst':None}
def scale(x):
    x=np.asarray(x,float);req(x.ndim==2 and x.shape[1]==6 and len(x)>=2 and np.isfinite(x).all(),'scale_input_invalid')
    ds=((x[:,None]-x[None,:])**2).sum(-1);np.fill_diagonal(ds,np.inf);nn=ds.min(1)
    req(np.isfinite(nn).all() and (nn>0).all(),'duplicate_or_missing_neighbors')
    ell2=float(np.median(nn));return 1/(2*ell2),ell2,nn
def kernel(x,y,gamma):return np.exp(-gamma*((x[:,None]-y[None,:])**2).sum(-1))
def numerical(x,gamma):
    k=kernel(x,x,gamma);eig=np.linalg.eigvalsh(k);tol=64*np.finfo(float).eps*len(x)*max(1,float(eig[-1]));sym=float(abs(k-k.T).max());condition=float(np.linalg.cond(k+np.eye(len(x))))
    req(sym<=1e-12 and eig[0]>=-tol and condition<=1e12,'kernel_invalid')
    return {'symmetry_max_abs':sym,'min_eigenvalue':float(eig[0]),'max_eigenvalue':float(eig[-1]),'PSD_tolerance':tol,'condition_K':float(np.linalg.cond(k)),'condition_K_plus_alphaI':condition,'regularization_alpha':1.,'condition_limit':1e12,'positive_semidefinite':True}
def synthetic():
    rng=np.random.default_rng(731564);x=rng.normal(size=(12,6));g,l,nn=scale(x);req(g==1/(2*np.median(nn)),'scale_formula');audit=numerical(x,g)
    y=rng.normal(size=(12,588));dual=np.linalg.solve(kernel(x,x,g)+np.eye(12),y);req(np.linalg.norm((kernel(x,x,g)+np.eye(12))@dual-y)/np.linalg.norm(y)<1e-12,'synthetic_solve_residual')
    q=rng.normal(size=(3,6))*20;req(scale(x)[0]==g,'heldout_input_cannot_change_train_scale');req(kernel(q,x,g).shape==(3,12),'query kernel shape')
    for bad in [np.zeros((2,6)),x[:1],np.full((3,6),np.nan)]:
        failed=False
        try:scale(bad)
        except ValueError:failed=True
        req(failed,'invalid_scale_must_fail')
    zero,inf=S.reconstruct(np.ones((3,294)),np.zeros((3,588)),np.ones((21,7,2),complex));req(np.all(zero==1) and inf['fallback_mask'].all(),'old_zero_phase_rule')
    z=rng.normal(size=(3,21,7,2))+1j*rng.normal(size=(3,21,7,2));z[0,0,0,0]=0;a,u=D.unit(z);xy=np.stack([u.real,u.imag],-1).reshape(3,588);rec,info=S.reconstruct(np.sqrt(a).reshape(3,294),xy,np.ones((21,7,2),complex));req(abs(rec-z).max()<2e-15,'complete_complex_roundtrip')
    dec=h1.load_h2_decoder();p=np.ones((3,21));h=h1.reconstruct_h2(z,p,dec);hr=h1.reconstruct_h2(rec,p,dec);req(max(abs(h[k]-hr[k]).max() for k in ['eta','absolute_order','total_power'])<1e-12,'H2 roundtrip')
    return {'status':'PASS','synthetic_estimator_fits':0,'checks':10,'kernel_audit':audit,'scope':'linear solve math, not sklearn modelfit; targets synthetic only'}
def check():
    p=read('LOCAL_SCALE_PHASE_FROZEN_SPEC.json');req(A.sha(Path(__file__))==p['code_sha256'],'frozen_code_modified')
    for f in p['protected_files']:req(A.sha(f['path'])==f['sha256'],'protected_hash_changed:'+f['path'])
    return p
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);req(not (OUT/'FIT_LEDGER.json').exists(),'no_refreeze_existing_task')
    req(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='cc53c98d4027b68756ff979ccfc9fd5954c70e2d','HEAD_requires_authority_review')
    pins={}
    for base in [AUD,OLD,A.OUT,S.NP.OUT,S.AUDIT]:
        inv=base/'SHA_INVENTORY.json'
        for f in A.read(inv)['files']:req(A.sha(f['path'])==f['sha256'],'input_hash:'+f['path']);pins[f['path']]=f['sha256']
        pins[str(inv)]=A.sha(inv)
    col=A.load_collection(False);req(len(col.cases)==156,'156_identity');by={case.case_id:case for case in col.cases};folds=A.read(OLD/'FOUR_FOLD_MATCHING_AND_SHA.json')['folds'];proposal=A.read(AUD/'PRIORITIZED_MINIMUM_MODEL_SPEC.json');dry={f['fold']:f for f in proposal['gamma_input_only_dry_run']};foldmanifest=[];audits=[]
    ids=sum([f['heldout_case_ids'] for f in folds],[]);req(len(ids)==len(set(ids))==124,'OOF_ids')
    bb=[];aa=[];pp=[];am=[]
    for f in folds:
        req(len(f['train_case_ids'])==124 and not set(f['train_case_ids'])&set(f['heldout_case_ids']),'geometry_leakage')
        p=OLD/'models'/f['task_id'];payload=joblib.load(p/'model.joblib');tr=f['train_case_ids'];x=np.array([by[i].ordered_D_nm for i in tr],float);xb=payload['input_scaler'].transform(x);g,l,nn=scale(xb);req(g==dry[f['fold']]['proposed_phase_gamma'],'proposal_gamma_exact')
        ct=np.array([by[i].c_hat for i in tr]);_,phase,_,_,_=S.targets(ct);sc=S.head_scaler(phase);req(np.array_equal(sc['mean'],payload['phase_scaler']['mean']) and sc['scale']==payload['phase_scaler']['scale'],'phase_scaler_or_targets_changed')
        xv=np.array([by[i].ordered_D_nm for i in f['heldout_case_ids']],float);cb,inf=S.save_prediction(payload,xv)
        with np.load(p/'predictions.npz',allow_pickle=False) as z:
            req(z['case_ids'].tolist()==f['heldout_case_ids'] and np.array_equal(cb,z['C_hat_real']+1j*z['C_hat_imag']),'B_reload_exact');req(np.array_equal(inf['phase_vector_norm'],z['phase_vector_norm']),'rho_reload_exact');bb.append(cb);pp.append(z['P_scale'].copy());am.append(inf['amplitude'])
        with np.load(Path(f['baseline_artifacts'][2]['path']),allow_pickle=False) as z:
            # Original amended156 predictions store physical C_hat and P_scale under established names.
            keys=list(z.files);aa.append({'path':str(f['baseline_artifacts'][2]['path']),'keys':keys})
        audit=numerical(xb,g);audit.update(fold=f['fold'],gamma=g,median_nearest_squared_distance=l,nearest_squared_distance=stats(nn));audits.append(audit)
        foldmanifest.append({**f,'new_task_id':f'local_phase_outer_{f["fold"]}','gamma':g,'alpha':1.,'phase_targets_sha256':hashlib.sha256(phase.tobytes()).hexdigest(),'phase_normalized_targets_sha256':hashlib.sha256(S.transform(phase,sc).tobytes()).hexdigest(),'source_payload':pin(p/'model.joblib'),'nearest_squared_distance':nn.tolist(),'train_geometry_scaler_source':'original payload, unchanged'})
    ct=np.array([by[i].c_hat for i in ids]);pt=np.array([by[i].p_scale for i in ids]);eta=np.array([by[i].eta for i in ids]);absolute=np.array([by[i].absolute_order for i in ids]);cpB=np.concatenate(bb);pP=np.concatenate(pp)
    with np.load(OLD/'A_OOF_PREDICTIONS.npz',allow_pickle=False) as z:req(z['case_ids'].tolist()==ids and np.array_equal(z['P_scale'],pP),'A_P_scale');cpA=z['C_hat_real']+1j*z['C_hat_imag']
    dec=h1.load_h2_decoder();oldH=A.read(OLD/'H1_H2_FINAL_EVALUATION.json');req(h1.evaluate_original_h1(ct,cpA,pt,pP,eta,absolute,dec)==oldH['A'],'A_H1_parity');req(h1.evaluate_original_h1(ct,cpB,pt,pP,eta,absolute,dec)==oldH['B'],'B_H1_parity')
    put('LOCAL_SCALE_PHASE_FROZEN_SPEC.json',{'task':TASK,'utc_before_fit':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_HEAD':'cc53c98d4027b68756ff979ccfc9fd5954c70e2d','code_sha256':A.sha(Path(__file__)),'protected_files':[{'path':p,'sha256':s} for p,s in sorted(pins.items())],'foreign_index_sha':hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest(),'proposal_source':pin(AUD/'PRIORITIZED_MINIMUM_MODEL_SPEC.json'),'geometry_normalization':'original per-fold training geometry mean/std, ordered6D; same as B. Distance is Euclidean in standardizedspace, not the descriptive130nm metric.','kernel':'K(x,y)=exp(-gamma||x-y||^2), stationaryGaussianRBF; NOT query-local refitting or nonstationary kernel','scale':'ell2=median_i min_j!=i ||x_i-x_j||² using only124training geometries; gamma=1/(2ell2)','regularization':'alpha1, float64, same sklearnKernelRidge asB','neighbors':'requires >=2 distinct finite geometries and everynearest squared distance>0; otherwise BLOCKED; no epsilon, clipping, rank/search','boundary':'same kernel, no mirror/periodicdiameter/shifting/sorting/response correction','inference':'one frozen gamma per fold; K(query,all124train); no label-drivenneighborchoice andno querymodel fit','phase_targets':'identical588 [cos,sin] interleaved coordinates; weak trainingfraction<1e-4 orzero ->[1,0]; trainingmeans+globalheadRMS exactlyB; no PCA','reconstruction':'originalS.reconstruct after inverseheadscale; unitcircle; norm<=64float64eps originaltraining-only fallback; amplitude sqrt head exactlyreused then squared; no disk/oraclealignment/fullstate normalization','fit_budget':{'new_phase_fits':4,'amplitude':0,'P_scale':0,'baseline':0,'MLP':0,'FDTD':0,'replay':0,'confirmation_access':0},'numerical_contract':{'kernel_symmetry_abs':1e-12,'PSD_tol':'64eps*n*max(1,lambda_max)','cond_K_plus_alphaI_max':1e12,'linear_solve_relative_residual_max':1e-10,'save_reload':'elementwise exact','amplitude_head_and_P_scale':'elementwise exact','reconstructed_abs_and_H2_B_C_tolerance':1e-12},'density_bins':'nearest training querydistance in standardized6D: <=1, (1,2], >2. Frozen before anynewfit, descriptive only. Exact/nearboundary/deepinterior fromfrozeninventory.','selection':'GAIN_SUPPORTED requires state median/q95 betterthanA+B, absolutephase andnonzerostate median/q95 betterthanB, >=62state wins vsA and>=3foldnegative state pairedmedian vsA/B, samepowerbenefits andworststate<=worstA+.1. PARTIAL ifphase orstate improvesvsB withoutfullcriteria. NO_CLEAR_GAIN otherwise; incomplete->INCONCLUSIVE. Research verdict only, originalH1 unchanged.','strong_threshold':1e-4,'phase_threshold_sensitivity':[1e-6,1e-5,1e-4,1e-3,1e-2],'reference_nm':1722,'orders':list(range(-3,4)),'output':'588realC_hat+21positiveP_scale','development_limitation':'Repeatedly reviewed124heldouts not independentconfirm;32responses sealed,28inputforecasts unchanged.'})
    put('FOUR_FOLD_FIT_MANIFEST.json',{'folds':foldmanifest,'count':4,'train_count_per_fold':124,'heldout_count':124,'dataset_count':156});put('LOCAL_KERNEL_NUMERICAL_AUDIT.json',{'status':'PASS','folds':audits});test=synthetic();put('ZERO_FIT_PREFLIGHT.json',{'status':'PASS','fits':0,'synthetic_tests':test,'156_identity':True,'four_folds':True,'amp_restore_exact':True,'P_scale_exact':True,'A_B_original_H1_exact':True,'allprotected_hashes_verified':True,'no_confirmation_response_access':True})
    put('FIT_LEDGER.json',{'authorized':4,'fits':{f['new_task_id']:{'status':'PENDING','fit_invocations':0,'fold':f['fold']} for f in foldmanifest}})
    print('ZERO_FIT_PREFLIGHT_PASS',json.dumps(audits),flush=True)
def train():
    check();req(read('ZERO_FIT_PREFLIGHT.json')['status']=='PASS','preflight_required');col=A.load_collection(False);by={c.case_id:c for c in col.cases};ledger=read('FIT_LEDGER.json')
    for f in read('FOUR_FOLD_FIT_MANIFEST.json')['folds']:
        row=ledger['fits'][f['new_task_id']];p=OUT/'models'/f['new_task_id'];p.mkdir(parents=True,exist_ok=True)
        if row['status']=='COMPLETE':req(A.sha(p/'model.joblib')==row['model_sha256'],'completed_model_hash');continue
        req(row['status']=='PENDING' and row['fit_invocations']==0,'ambiguous_fit_do_not_retrain')
        payload=joblib.load(f['source_payload']['path']);tr=f['train_case_ids'];x=np.array([by[i].ordered_D_nm for i in tr],float);xb=payload['input_scaler'].transform(x);_,phase,_,_,_=S.targets(np.array([by[i].c_hat for i in tr]));req(hashlib.sha256(phase.tobytes()).hexdigest()==f['phase_targets_sha256'],'phase_target_identity');y=S.transform(phase,payload['phase_scaler']);req(hashlib.sha256(y.tobytes()).hexdigest()==f['phase_normalized_targets_sha256'],'target_scale_identity');req(scale(xb)[0]==f['gamma'],'train_only_gamma')
        row.update(status='FITTING',fit_invocations=1,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),gamma=f['gamma'],alpha=1.,train_ids_sha=hashlib.sha256(json.dumps(tr).encode()).hexdigest());put('FIT_LEDGER.json',ledger);start=time.perf_counter()
        model=KernelRidge(kernel='rbf',alpha=1.,gamma=f['gamma']).fit(xb,y)
        residual=float(np.linalg.norm((kernel(xb,xb,f['gamma'])+np.eye(124))@model.dual_coef_-y)/np.linalg.norm(y));joblib.dump(model,p/'phase_head.joblib',compress=3);req(residual<=1e-10,'solve_residual_invalid')
        final={**payload,'phase_model':model,'local_phase_task':f,'local_phase_spec_sha':A.sha(OUT/'LOCAL_SCALE_PHASE_FROZEN_SPEC.json')};joblib.dump(final,p/'model.joblib',compress=3)
        xv=np.array([by[i].ordered_D_nm for i in f['heldout_case_ids']],float);cp,info=S.save_prediction(final,xv);base,baseinfo=S.save_prediction(payload,xv);req(np.array_equal(info['amplitude'],baseinfo['amplitude']),'amplitude_head_not_exact')
        source=OLD/'models'/f['task_id']/'predictions.npz'
        with np.load(source,allow_pickle=False) as z:pP=z['P_scale'].copy();req(z['case_ids'].tolist()==f['heldout_case_ids'],'prediction_identity')
        again,ai=S.save_prediction(joblib.load(p/'model.joblib'),xv);req(np.array_equal(cp,again),'save_reload_not_exact');ctp,ti=S.save_prediction(final,x)
        raw=S.inverse(model.predict(final['input_scaler'].transform(xv)),final['phase_scaler']).reshape(-1,21,7,2,2)
        np.savez_compressed(p/'predictions.npz',case_ids=np.array(f['heldout_case_ids']),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=pP,amplitude_head=info['amplitude'],phase_vector_norm=info['phase_vector_norm'],raw_cos=raw[...,0],raw_sin=raw[...,1],fallback_mask=info['fallback_mask'])
        np.savez_compressed(p/'training_predictions.npz',case_ids=np.array(tr),C_hat_real=ctp.real,C_hat_imag=ctp.imag,phase_vector_norm=ti['phase_vector_norm'])
        row.update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,model_sha256=A.sha(p/'model.joblib'),phase_head_sha256=A.sha(p/'phase_head.joblib'),solve_relative_residual=residual,prediction_sha256=A.sha(p/'predictions.npz'));put('FIT_LEDGER.json',ledger)
        put(f['new_task_id']+'_PROVENANCE.json',{'task':f,'models':[pin(p/n) for n in ['model.joblib','phase_head.joblib','predictions.npz','training_predictions.npz']],'head_amplitude_exact':True,'P_scale_exact_source':pin(source),'save_reload_exact':True,'fallback_count':int(info['fallback_mask'].sum()),'fallback_amplitude_squared_share':float((info['amplitude']**2*info['fallback_mask']).sum()/(info['amplitude']**2).sum()),'negative_sqrt_count':int(info['negative_sqrt_mask'].sum()),'solve_relative_residual':residual})
        print('PHASE_FIT_COMPLETE',f['new_task_id'],row['elapsed_seconds'],flush=True)
    req(sum(v['fit_invocations'] for v in ledger['fits'].values())==4 and all(v['status']=='COMPLETE' for v in ledger['fits'].values()),'fitcount');print('ALL_4_PHASE_FITS_COMPLETE',flush=True)
def evaluate():
    prot=check();col=A.load_collection(False);by={c.case_id:c for c in col.cases};meta={r['case_id']:r for r in A.inventory()['cases']};folds=read('FOUR_FOLD_FIT_MANIFEST.json')['folds'];ids=sum([f['heldout_case_ids'] for f in folds],[]);ct=np.array([by[i].c_hat for i in ids]);pt=np.array([by[i].p_scale for i in ids]);eta=np.array([by[i].eta for i in ids]);absolute=np.array([by[i].absolute_order for i in ids]);preds={};rhos={};amp=[];new=[];train=[]
    for arm in ['A','B']:
        with np.load(OLD/f'{arm}_OOF_PREDICTIONS.npz',allow_pickle=False) as z:req(z['case_ids'].tolist()==ids,'savedOOFIDs');preds[arm]=z['C_hat_real']+1j*z['C_hat_imag'];pp=z['P_scale'].copy()
    bnorm=[]
    for f in folds:
        p=OUT/'models'/f['new_task_id'];req(A.sha(p/'predictions.npz')==read('FIT_LEDGER.json')['fits'][f['new_task_id']]['prediction_sha256'],'prediction_sha');source=OLD/'models'/f['task_id']/'predictions.npz';payload=joblib.load(f['source_payload']['path']);x=np.array([by[i].ordered_D_nm for i in f['heldout_case_ids']],float);_,bi=S.save_prediction(payload,x)
        with np.load(p/'predictions.npz',allow_pickle=False) as z:
            req(z['case_ids'].tolist()==f['heldout_case_ids'],'C_predictionID');ix=[ids.index(i) for i in f['heldout_case_ids']];req(np.array_equal(z['P_scale'],pp[ix]) and np.array_equal(z['amplitude_head'],bi['amplitude']),'heldout_ampP_exact');new.append(z['C_hat_real']+1j*z['C_hat_imag']);amp.append(z['amplitude_head']);rhos.setdefault('C',[]).append(z['phase_vector_norm'])
        with np.load(source,allow_pickle=False) as z:bnorm.append(z['phase_vector_norm'])
        with np.load(p/'training_predictions.npz',allow_pickle=False) as z:
            tr=np.array([by[i].c_hat for i in f['train_case_ids']]);pc=z['C_hat_real']+1j*z['C_hat_imag'];train.append({'fold':f['fold'],'state':stats(np.linalg.norm((tr-pc).reshape(124,-1),axis=1)/np.linalg.norm(tr.reshape(124,-1),axis=1)),'phase':D.angular_stats(tr,pc,1e-4),'rho':stats(z['phase_vector_norm'])})
    preds['C']=np.concatenate(new);rhos={'B':np.concatenate(bnorm),'C':np.concatenate(rhos['C'])};amp=np.concatenate(amp);dec=h1.load_h2_decoder();reports={};hd={};per={};decomp={};phaseout={};modal={};diag={}
    for arm,cp in preds.items():
        reports[arm]=h1.evaluate_original_h1(ct,cp,pt,pp,eta,absolute,dec);hd[arm]=h1.reconstruct_h2(cp,pp,dec);diag[arm]=V.diagnostics(ct,cp,ids,meta);per[arm]={k:np.array([q[k] for q in reports[arm]['aggregate']['per_geometry']]) for k in reports[arm]['aggregate']['per_geometry'][0]};am,ph,err,delta=D.error_decomposition(ct,cp);sq=abs(ct)**2;den=sq.sum((1,2,3));angles=D.angular_stats(ct,cp,1e-4)
        per[arm].update(amplitude_relative_rmse=np.sqrt(am.sum((1,2,3))/den),absolute_phase_rmse=np.array(angles['per_geometry_absolute']),relative_phase_rmse=np.array(angles['per_geometry_relative']),norm_ratio=np.sqrt((abs(cp)**2).sum((1,2,3))/den),nonzero_state_rmse=np.sqrt(err[:,:,[0,1,2,4,5,6]].sum((1,2,3))/sq[:,:,[0,1,2,4,5,6]].sum((1,2,3))))
        decomp[arm]={'amplitude_SSE':float(am.sum()),'phase_SSE':float(ph.sum()),'phase_SSE_fraction':float(ph.sum()/err.sum()),'order_total_SSE_fraction':(err.sum((0,1,3))/err.sum()).tolist(),'order_phase_SSE_fraction':(ph.sum((0,1,3))/err.sum()).tolist(),'TE_TM_SSE_fraction':(err.sum((0,1,2))/err.sum()).tolist()}
        phaseout[arm]={'angular':angles,'threshold_sensitivity':[D.angular_stats(ct,cp,v) for v in prot['phase_threshold_sensitivity']]}
        modal[arm]=[]
        for j in range(7):
            frac=sq/sq.sum((2,3),keepdims=True);w=sq[:,:,j,1]*(frac[:,:,j,1]>=1e-4);errphase=np.angle(cp[:,:,j,1]*ct[:,:,j,1].conj());pr=np.sqrt((w*errphase**2).sum(1)/w.sum(1));st=np.sqrt(err[:,:,j,:].sum((1,2))/sq[:,:,j,:].sum((1,2)))
            modal[arm].append({'m':j-3,'strong_TM_phase_RMSE':stats(pr),'order_state_RMSE':stats(st),'per_geometry':[{'case_id':i,'strong_TM_phase_RMSE':float(pr[k]),'order_state_RMSE':float(st[k])} for k,i in enumerate(ids)]})
    old=A.read(OLD/'H1_H2_FINAL_EVALUATION.json');req(reports['A']==old['A'] and reports['B']==old['B'],'A_B_official_scores_changed')
    powerdelta={k:float(abs(hd['B'][k]-hd['C'][k]).max()) for k in ['eta','absolute_order','total_power']};req(max(powerdelta.values())<=1e-12,'B_C_H2_changed');absdelta=float(abs(abs(preds['B'])-abs(preds['C'])).max());req(absdelta<=1e-12,'B_C_amplitude_changed')
    paired={}
    for key in per['A']:
        arr={arm:per[arm][key] for arm in per};pairs={}
        for base,new in [('A','B'),('B','C'),('A','C')]:
            dd=arr[new]-arr[base];rows=[{'case_id':i,'fold':next(f['fold'] for f in folds if i in f['heldout_case_ids']),'base':float(arr[base][k]),'new':float(arr[new][k]),'delta':float(dd[k])} for k,i in enumerate(ids)];pairs[new+'_minus_'+base]={'delta':stats(dd),'wins':int((dd< -1e-12).sum()),'losses':int((dd>1e-12).sum()),'ties':int((abs(dd)<=1e-12).sum()),'per_geometry':rows,'worst10':sorted(rows,key=lambda q:q['delta'],reverse=True)[:10],'folds':{str(f['fold']):{'delta':stats(dd[[ids.index(i) for i in f['heldout_case_ids']]]),'wins':int((dd[[ids.index(i) for i in f['heldout_case_ids']]]< -1e-12).sum()),'losses':int((dd[[ids.index(i) for i in f['heldout_case_ids']]]>1e-12).sum())} for f in folds}}
        paired[key]={**{arm:stats(arr[arm]) for arm in arr},'paired':pairs,'interpretation':'norm_ratio is closeness-to1, not lower-is-better; otherreportedmetrics errors'}
    sq=abs(ct)**2;strong=sq/sq.sum((2,3),keepdims=True)>=1e-4
    for arm in ['B','C']:phaseout[arm].update(all_rho=stats(rhos[arm]),strong_rho=stats(rhos[arm][strong]),weak_rho=stats(rhos[arm][~strong]),strong_rho_below_point5=float((rhos[arm][strong]<.5).mean()),strong_rho_below_point1=float((rhos[arm][strong]<.1).mean()),strong_rho_by_order=[{'m':j-3,'stats':stats(rhos[arm][:,:,j,:][strong[:,:,j,:]])} for j in range(7)])
    density=[]
    for f in folds:
        payload=joblib.load(f['source_payload']['path']);xt=payload['input_scaler'].transform(np.array([by[i].ordered_D_nm for i in f['train_case_ids']],float));xv=payload['input_scaler'].transform(np.array([by[i].ordered_D_nm for i in f['heldout_case_ids']],float));d2=((xv[:,None]-xt[None,:])**2).sum(-1);nearest=d2.argmin(1)
        for k,i in enumerate(f['heldout_case_ids']):
            oi=ids.index(i);dist=float(np.sqrt(d2[k,nearest[k]]));density.append({'case_id':i,'fold':f['fold'],'nearest_train_case':f['train_case_ids'][nearest[k]],'nearest_distance':dist,'density':'CLOSE' if dist<=1 else ('MEDIUM' if dist<=2 else 'SPARSE'),'stratum':meta[i]['stratum'],'role':by[i].role,'state_C_minus_B':float(per['C']['state_relative_rmse'][oi]-per['B']['state_relative_rmse'][oi]),'phase_C_minus_B':float(per['C']['absolute_phase_rmse'][oi]-per['B']['absolute_phase_rmse'][oi]),'state_C_minus_A':float(per['C']['state_relative_rmse'][oi]-per['A']['state_relative_rmse'][oi])})
    groups={}
    for name,sel in [(s,[q for q in density if q['density']==s]) for s in ['CLOSE','MEDIUM','SPARSE']]+[(s,[q for q in density if q['stratum']==s]) for s in sorted(set(q['stratum'] for q in density))]+[('LOCAL_AXIS',[q for q in density if q['role']==C.ROLE_LOCAL_AXIS])]:
        groups[name]={'n':len(sel),'state_C_minus_B':stats([q['state_C_minus_B'] for q in sel]),'phase_C_minus_B':stats([q['phase_C_minus_B'] for q in sel]),'state_C_minus_A':stats([q['state_C_minus_A'] for q in sel]),'nearest_distance':stats([q['nearest_distance'] for q in sel])}
    from scipy.stats import spearmanr
    assoc={'nearest_distance_vs_state_delta':float(spearmanr([q['nearest_distance'] for q in density],[q['state_C_minus_B'] for q in density]).statistic),'nearest_distance_vs_phase_delta':float(spearmanr([q['nearest_distance'] for q in density],[q['phase_C_minus_B'] for q in density]).statistic),'meaning':'descriptive association only, not causal; repeateddevelopmentselection'}
    put('H1_H2_EVALUATION.json',{'reports':reports,'P_scale_exact':True,'amplitude_head_exact':True,'reconstructed_abs_max_B_C':absdelta,'H2_B_C_max_abs':powerdelta,'seed_stability':'N/A deterministicKRR, not PASS'})
    put('PHASE_HEAD_RESULTS.json',{'arms':phaseout,'SSE_decomposition':decomp,'training':train});put('RECONSTRUCTED_COMPLEX_STATE.json',diag);put('THREE_WAY_PAIRED_COMPARISON.json',paired);put('NONZERO_ORDER_PHASE_ANALYSIS.json',modal);put('NEIGHBORHOOD_DENSITY_DIAGNOSTIC.json',{'rows':density,'groups':groups,'associations':assoc,'missing':'D6_M05','repeatability':'No independent +/-5nm numericalerrorfloor','norm_scale':'original foldtrainingstandardizer, no queryfit'})
    def improves(key,base):return paired[key]['C']['median']<paired[key][base]['median'] and paired[key]['C']['q95']<paired[key][base]['q95']
    phasegain=improves('absolute_phase_rmse','B');stategain=improves('state_relative_rmse','B');nonzerogain=improves('nonzero_state_rmse','B');cartgain=improves('state_relative_rmse','A');pair=paired['state_relative_rmse']['paired'];consistent=all(sum(v['delta']['median']<0 for v in pair[k]['folds'].values())>=3 for k in ['C_minus_A','C_minus_B']);tail=paired['state_relative_rmse']['C']['worst']<=paired['state_relative_rmse']['A']['worst']+.1
    gain=phasegain and stategain and nonzerogain and cartgain and consistent and pair['C_minus_A']['wins']>=62 and tail
    verdict='LOCAL_SCALE_PHASE_GAIN_SUPPORTED' if gain else ('LOCAL_SCALE_PHASE_PARTIAL_GAIN' if phasegain or stategain else 'LOCAL_SCALE_PHASE_NO_CLEAR_GAIN')
    put('FINAL_SCIENTIFIC_VERDICT.json',{'status':'PASS','verdict':verdict,'phase_gain_vs_B':phasegain,'state_gain_vs_B':stategain,'nonzero_gain_vs_B':nonzerogain,'state_gain_vs_A':cartgain,'consistent_state_folds':consistent,'worst_tail_research_rule':tail,'unchanged_amplitude_and_power':True,'H1':{k:r['all_applicable_numeric_gates_attained'] for k,r in reports.items()},'development_only':True,'confirmation_pass':False,'fits':4})
    np.savez_compressed(OUT/'C_OOF_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=preds['C'].real,C_hat_imag=preds['C'].imag,P_scale=pp,amplitude_head=amp,phase_vector_norm=rhos['C'])
    check();ledger=read('FIT_LEDGER.json');req(sum(q['fit_invocations'] for q in ledger['fits'].values())==4,'fitcount');put('FINAL_ISOLATION_CHECK.json',{'status':'PASS','phase_head_fits':4,'amplitude_fits':0,'P_scale_fits':0,'baseline_fits':0,'FDTD':0,'replay':0,'confirmation_access':0,'protected_hashes_unchanged':True,'confirmation28forecasts_unchanged':True,'A_B_original_H1_exact':True,'amplitude_head_exact':True,'P_scale_exact':True,'model_reloads_exact':True})
    print('THREE_WAY_RESULTS',json.dumps({k:{arm:v[arm] for arm in ['A','B','C']} for k,v in paired.items() if k in ['state_relative_rmse','absolute_phase_rmse','nonzero_state_rmse','routing_eta_rmse']}),flush=True);print('VERDICT',verdict,flush=True)
if __name__=='__main__':
    os.environ['CUDA_VISIBLE_DEVICES']=''
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='train':train()
    elif sys.argv[1]=='evaluate':evaluate()
    else:raise ValueError('unknown command')
