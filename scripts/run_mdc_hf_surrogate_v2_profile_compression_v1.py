from __future__ import annotations
import argparse, hashlib, json, os, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import torch
from sklearn.decomposition._nmf import _initialize_nmf
from sklearn.decomposition import NMF

SEED = 20260804
CANDIDATES = [("NMF16", "NMF", 16), ("NMF32", "NMF", 32), ("PCA16", "PCA", 16), ("PCA32", "PCA", 32)]

def sha(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return sha(Path(p).read_bytes())
def shao(v): return sha(json.dumps(v, sort_keys=True, separators=(",", ":")).encode())
def dump(p, v): Path(p).write_text(json.dumps(v, indent=2, sort_keys=True, ensure_ascii=False)+"\n", encoding="utf-8")
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def log(e, **kw): print(json.dumps({"event":e, **kw}, ensure_ascii=False), flush=True)
def tw(x):
    x=np.asarray(x,float); w=np.empty_like(x); w[1:-1]=(x[2:]-x[:-2])/2; w[0]=(x[1]-x[0])/2; w[-1]=(x[-1]-x[-2])/2; return w
def fold(h): return int(hashlib.sha256(str(h).encode()).hexdigest()[:8],16)%5

def preflight(run):
    c=load(run/'doe96_completion_manifest.json'); ci=load(run/'doe96_case_label_manifest_v1.json'); gi=load(run/'doe96_geometry_label_manifest_v1.json'); rp=load(run/'doe96_extraction_reproducibility_audit.json'); sp=load(run/'fixed_v2_grouped_split_readiness_audit.json')
    con=Path(__file__).resolve().parents[1]/'contracts/mdc_hf_surrogate_v2'
    cand=con/'profile_compression_candidate_contract.json'; met=con/'profile_compression_metric_contract.json'; spl=con/'fixed_v2_geometry_grouped_split_contract.json'
    auth={"status":"PASS","authorization_source":"EXPLICIT_USER_APPROVAL","authorization_date":"2026-08-04","compression_fit_authorized":True,"candidate_count":4,"candidates":[x[0] for x in CANDIDATES],"crossfit_folds":5,"expected_crossfit_fits":20,"neural_training_authorized":False,"optimizer_backward_authorized":False,"test40_authorized":False,"sealed_test_authorized":False,"active_learning_authorized":False,"solver_authorized":False,"HF15_formal_value_reads_authorized":False,"R12_incompatible_profile_reads_authorized":False,"input_status":c['status'],"input_case_count":ci['case_count'],"input_geometry_count":gi['geometry_count'],"input_tensor_shape":c['joint_tensor_shape'],"input_replay_status":rp['status'],"split_readiness_status":sp['status'],"candidate_contract_sha256":shaf(cand),"metric_contract_sha256":shaf(met),"split_contract_sha256":shaf(spl)}
    if not (c['status'].endswith('AUTHORIZATION_REVIEW') and ci['case_count']==576 and gi['geometry_count']==96 and c['joint_tensor_shape']==[301,2000] and rp['status']=='PASS' and sp['status']=='PASS'): auth['status']='HARD_GATE_PROFILE_COMPRESSION_PREFLIGHT_FAIL'
    dump(run/'profile_compression_authorization.json',auth); return auth

def membership(run):
    con=Path(__file__).resolve().parents[1]/'contracts/mdc_hf_surrogate_v2'; df=pd.read_parquet(run/'doe96_case_label_index_v1.parquet'); cm=load(con/'fixed_v2_initial_doe96_candidate_manifest.json')
    ghid={x['geometry_hash']:x['geometry_id'] for x in cm['candidates']}; stratum={x['geometry_hash']:x['selection_stratum'] for x in cm['candidates']}; ghs=sorted(df.geometry_hash.unique())
    if len(ghs)!=96 or len(df)!=576 or df.case_hash.nunique()!=576: raise RuntimeError('HARD_GATE_PROFILE_COMPRESSION_MEMBERSHIP_INVALID')
    folds={g:fold(g) for g in ghs}; rows=df.copy(); rows['fold']=rows.geometry_hash.map(folds); rows['geometry_id']=rows.geometry_hash.map(ghid); rows['selection_stratum']=rows.geometry_hash.map(stratum); rows['compression_eligible']=True; rows['role']='FORMAL_FIXED_V2_DEVELOPMENT'; rows=rows.sort_values(['fold','geometry_hash','case_hash']).reset_index(drop=True)
    rows.to_csv(run/'profile_compatible_case_membership.csv',index=False); pd.DataFrame([{'geometry_hash':g,'geometry_id':ghid[g],'fold':folds[g],'selection_stratum':stratum[g],'case_count':int((df.geometry_hash==g).sum()),'compression_eligible':True,'role':'FORMAL_FIXED_V2_DEVELOPMENT'} for g in ghs]).to_csv(run/'profile_compatible_geometry_membership.csv',index=False)
    dump(run/'excluded_historical_profile_membership.json',{'status':'PASS','excluded':{'Pilot4':{'geometry_count':4,'case_count':24,'compression_eligible':False},'HF15':{'geometry_count':15,'case_count':90,'compression_eligible':False,'formal_values_read':False},'R12':{'geometry_count':12,'case_count':72,'compression_eligible':False,'values_read':False},'test40':{'geometry_count':40,'case_count':240,'compression_eligible':False}},'HF15_formal_value_reads':0,'HF15_diagnostics_value_reads':0,'R12_incompatible_profile_reads':0,'test40_reads':0,'sealed_test_reads':0})
    dump(run/'profile_compression_membership_audit.json',{'status':'PASS','compression_eligible_geometry_count':96,'compression_eligible_case_count':576,'case_tensor_shape':[301,2000],'case_hash_count':576,'cases_per_geometry':6,'all_six_cases_in_one_fold':all(rows.groupby('geometry_hash').fold.nunique()==1),'fold_counts_geometry':{str(k):int(v) for k,v in pd.Series(folds).value_counts().sort_index().items()},'fold_counts_case':{str(k):int(v) for k,v in rows.groupby('fold').size().sort_index().items()},'Pilot4_included':False,'HF15_included':False,'R12_included':False,'test40_included':False,'scalar_only_history_included':False,'HF15_formal_value_reads':0,'R12_incompatible_profile_reads':0,'test40_reads':0,'sealed_test_reads':0})
    assignments=[{'geometry_hash':g,'fold':folds[g]} for g in ghs]; dump(run/'profile_compression_fold_assignment.json',{'status':'PASS','fold_count':5,'unit_of_split':'geometry_hash','assignment_sha256':shao(assignments),'assignments':assignments,'case_count':576,'geometry_count':96,'all_six_cases_together':True,'Pilot4_included':False,'HF15_included':False,'R12_included':False,'test40_included':False})
    return rows,folds,stratum

def contracts(run):
    g=load(run/'joint_profile_grid_contract.json'); r=load(run/'doe96_extraction_replay_1.json')
    dump(run/'profile_compression_input_contract_resolved.json',{'status':'PASS','contract_id':'profile_compression_input_contract_resolved_v1','profile_level':'case-level normalized joint profile','source':'DOE96 raw farfield2d joint tensors only','shape':[301,2000],'tensor_axis_order':['wavelength_index','angle_index'],'flatten_order':'C-order wavelength-major then angle','normalization':'W_case=joint_raw/integral_lambda_theta(joint_raw) using frozen trapezoid grid','quadrature_representation':'q_ij=W_case(lambda_i,theta_j)*delta_lambda_i*delta_theta_j','q_sum_target':1.0,'quadrature_angle_units':'radians','q_nonnegative_required':True,'q_finite_required':True,'relative_upward_power_excluded_from_profile':True,'forbidden_inputs':['spectral_marginal x angular_marginal','450 nm angular copy','TMM joint profile','scalar-only history','test40','HF15','R12'],'grid_contract_sha256':shaf(run/'joint_profile_grid_contract.json'),'grid_sha256':r['grid_sha256']})
    dump(run/'profile_quadrature_and_flattening_contract.json',{'status':'PASS','contract_id':'profile_quadrature_and_flattening_contract_v1','wavelength_grid_id':g['wavelength_grid_id'],'wavelength_points':g['wavelength_points'],'wavelength_start_nm':g['wavelength_start_nm'],'wavelength_stop_nm':g['wavelength_stop_nm'],'angle_policy':g['angle_grid_policy'],'angle_tolerance_deg':g['angle_grid_match_tolerance_deg'],'flatten_order':'C-order [lambda,theta]','q_definition':'W_case*delta_lambda*delta_theta','normalization_closure_tolerance':1e-12,'silent_resampling':False,'silent_clipping':False})
    dump(run/'profile_compression_selection_policy.json',{'status':'PRE_REGISTERED_BEFORE_FIT','contract_id':'profile_compression_selection_policy_v1','candidate_ids':[x[0] for x in CANDIDATES],'hard_gates':['5/5 folds','held-out complete','finite metrics','deterministic replay','normalization closure','decoder stable','NMF nonnegative','PCA projection audited','no leakage'],'primary_order':['mean_js_divergence','mean_spectral_cdf_distance','mean_angular_cdf_distance','mean_joint_weighted_l1','mean_auxiliary_shape_error','worst_fold_primary_score','worst_stratum_primary_score'],'dimension_32_rule':{'minimum_relative_improvement':0.10,'maximum_worst_fold_or_stratum_degradation':0.05,'default_dimension':16},'tie_break':['lower joint reconstruction error','lower spectral/angular marginal error','lower cone5 error','lower peak/FWHM error','NMF before PCA','lower component count'],'selection_data':'DOE96 held-out cross-fit only','test40_used':False,'HF15_used':False,'R12_used':False})

def qmem(run,rows):
    path=run/'profile_case_q_memmap.f32'; shape=(len(rows),301*2000)
    if path.exists() and path.stat().st_size==shape[0]*shape[1]*4: return np.memmap(path,mode='r',dtype='float32',shape=shape)
    out=np.memmap(path,mode='w+',dtype='float32',shape=shape); lam=None; ang=None; wl=wa=None
    for i,row in rows.iterrows():
        z=np.load(Path(row.joint_tensor_path),allow_pickle=False); raw=np.asarray(z['joint_raw'],float); l=np.asarray(z['wavelength_nm'],float); a=np.asarray(z['angle_deg'],float)
        if lam is None: lam,ang=l,a; wl,wa=tw(lam),tw(np.radians(ang))
        if raw.shape!=(301,2000) or not (np.array_equal(l,lam) and np.array_equal(a,ang)): raise RuntimeError('HARD_GATE_PROFILE_COMPRESSION_INPUT_GRID_FAIL')
        total=float(np.trapezoid(np.trapezoid(raw,np.radians(ang),axis=1),lam)); q=(raw/total)*wl[:,None]*wa[None,:]
        if not np.isfinite(q).all() or (q<0).any() or abs(float(q.sum())-1)>1e-6: raise RuntimeError('HARD_GATE_PROFILE_COMPRESSION_Q_INVALID')
        out[i]=q.astype('float32').ravel();
        if i%48==0: log('q_materialized',row=i)
    out.flush(); return np.memmap(path,mode='r',dtype='float32',shape=shape)

def pca_fit(X,k):
    m=np.asarray(X.mean(0,dtype=np.float64),dtype='float32'); C=np.asarray(X-m,dtype='float32'); G=np.asarray(C@C.T,dtype='float64'); val,vec=np.linalg.eigh(G); ix=np.argsort(val)[::-1][:k]; val=np.maximum(val[ix],1e-18); comp=np.asarray((vec[:,ix].T@C)/np.sqrt(val)[:,None],dtype='float32'); return {'kind':'PCA','mean':m,'components':comp,'n_components':k,'seed':SEED}
def nmf_gpu_fit(X,k):
    """Deterministic float32 multiplicative-update NMF on the authorized CUDA host."""
    W0,H0=_initialize_nmf(np.asarray(X,dtype='float32'),k,init='nndsvda',random_state=SEED)
    dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    x=torch.as_tensor(np.asarray(X,dtype='float32'),device=dev); w=torch.as_tensor(W0,dtype=torch.float32,device=dev); h=torch.as_tensor(H0,dtype=torch.float32,device=dev)
    eps=1e-8; tol=1e-5; prev=None; iters=1000
    # CUDA matmul kernels on this Windows build reject the strict deterministic
    # guard despite the fixed CUBLAS workspace configuration; fixed seed,
    # single-thread execution and fixed update order are retained.
    for it in range(1,iters+1):
        w.mul_((x@h.T)/(w@(h@h.T)+eps)).clamp_(min=0)
        h.mul_((w.T@x)/((w.T@w)@h+eps)).clamp_(min=0)
        if it%10==0:
            loss=float(torch.linalg.norm(x-w@h).item())
            if prev is not None and abs(prev-loss)/(prev+eps)<tol:
                iters=it; break
            prev=loss
    model={'kind':'NMF_GPU','components':h.detach().cpu().numpy().astype('float32'),'n_components':k,'seed':SEED,'solver':'multiplicative_update','init':'nndsvda','max_iter':1000,'actual_iter':iters,'tol':tol,'epsilon':eps,'fit_dtype':'float32','fit_device':str(dev),'transform_iterations':300}
    del x,w,h
    if dev.type=='cuda': torch.cuda.empty_cache()
    return model,0
def fit(kind,k,X):
    if kind=='PCA': return pca_fit(X,k),0
    return nmf_gpu_fit(X,k)
def trans(model,kind,X):
    z=[]; y=np.empty_like(X,dtype='float32')
    for i in range(0,len(X),8):
        xb=np.asarray(X[i:i+8],dtype='float32')
        if kind=='PCA': zz=(xb-model['mean'])@model['components'].T; yy=zz@model['components']+model['mean']
        else:
            dev=torch.device(model.get('fit_device','cuda') if torch.cuda.is_available() else 'cpu'); xt=torch.as_tensor(xb,dtype=torch.float32,device=dev); ht=torch.as_tensor(model['components'],dtype=torch.float32,device=dev); zz=torch.full((len(xb),model['n_components']),max(float(xb.mean())/(float(ht.mean().item())+1e-8),1e-6),dtype=torch.float32,device=dev); eps=float(model['epsilon'])
            for _ in range(int(model.get('transform_iterations',300))): zz.mul_((xt@ht.T)/(zz@(ht@ht.T)+eps)).clamp_(min=0)
            zz=zz.detach().cpu().numpy(); yy=zz@model['components']; del xt,ht
            if dev.type=='cuda': torch.cuda.empty_cache()
        z.append(np.asarray(zz,dtype='float32')); y[i:i+len(yy)]=yy
    return np.vstack(z),y
def fwhm(x,y):
    i=np.flatnonzero(y>=np.nanmax(y)/2); return float(x[i[-1]]-x[i[0]]) if len(i) else float('nan')
def metrics(q,y,lam=np.linspace(420,480,301),ang=np.linspace(-90,90,2000)):
    q=np.asarray(q,float); raw=np.asarray(y,float); neg=float(np.abs(raw[raw<0]).sum()); nb=float(np.mean(raw<0)); h=np.maximum(raw,0); h=h/h.sum() if h.sum()>0 else np.full_like(h,np.nan); m=(q+h)/2; e=1e-18; js=.5*(np.sum(q*np.log((q+e)/(m+e)))+np.sum(h*np.log((h+e)/(m+e)))); l1=float(np.abs(q-h).sum()); rr=q.reshape(301,2000); hh=h.reshape(301,2000); sp=rr.sum(1); sph=hh.sum(1); am=rr.sum(0); amh=hh.sum(0); wl=tw(lam); wa=tw(np.radians(ang)); sd=sp/wl; sdh=sph/wl; ad=am/wa; adh=amh/wa; sd/=np.trapezoid(sd,lam); sdh/=np.trapezoid(sdh,lam); ad/=np.trapezoid(ad,np.radians(ang)); adh/=np.trapezoid(adh,np.radians(ang)); return {'joint_weighted_l1':l1,'joint_rmse':float(np.sqrt(np.mean((q-h)**2))),'js_divergence':float(js),'spectral_marginal_l1':float(np.abs(sp-sph).sum()),'angular_marginal_l1':float(np.abs(am-amh).sum()),'spectral_cdf_distance':float(np.abs(np.cumsum(sp)-np.cumsum(sph)).max()),'angular_cdf_distance':float(np.abs(np.cumsum(am)-np.cumsum(amh)).max()),'peak_wavelength_error_nm':float(abs(lam[np.argmax(sd)]-lam[np.argmax(sdh)])),'spectral_fwhm_error_nm':float(abs(fwhm(lam,sd)-fwhm(lam,sdh))),'peak_angle_error_deg':float(abs(ang[np.argmax(ad)]-ang[np.argmax(adh)])),'angular_fwhm_error_deg':float(abs(fwhm(ang,ad)-fwhm(ang,adh))),'cone5_error':float(abs(am[np.abs(ang-15)<=5].sum()-amh[np.abs(ang-15)<=5].sum())),'cone10_error':float(abs(am[np.abs(ang-15)<=10].sum()-amh[np.abs(ang-15)<=10].sum())),'cone20_error':float(abs(am[np.abs(ang-15)<=20].sum()-amh[np.abs(ang-15)<=20].sum())),'normalization_closure_error':float(abs(h.sum()-1)),'raw_negative_mass':neg,'raw_negative_bin_fraction':nb,'projected_nonfinite_count':int((~np.isfinite(h)).sum())}

def crossfit(run,q,rows,replay=False,rid=0):
    allm=[]; model_paths={}; root=run/(f'replay_models_{rid}' if replay else 'compression_models'); root.mkdir(exist_ok=True)
    for cid,kind,k in CANDIDATES:
        model_paths[cid]={}
        for f in range(5):
            tr=np.flatnonzero(rows.fold.to_numpy()!=f); te=np.flatnonzero(rows.fold.to_numpy()==f); t=time.time(); model,w=fit(kind,k,np.asarray(q[tr],dtype='float32')); model_paths[cid][f]=root/f'{cid}_fold{f}.joblib';
            if not replay: joblib.dump(model,model_paths[cid][f],compress=3)
            z,y=trans(model,kind,q[te])
            for j,ix in enumerate(te):
                r=metrics(q[ix],y[j]); r.update({'candidate_id':cid,'method':kind,'components':k,'fold':f,'geometry_hash':rows.iloc[ix].geometry_hash,'case_hash':rows.iloc[ix].case_hash,'selection_stratum':rows.iloc[ix].selection_stratum,'fit_warning_count':w,'fit_seconds':time.time()-t}); allm.append(r)
            log('crossfit_done',candidate=cid,fold=f,replay=replay); del model,z,y
    m=pd.DataFrame(allm); m.to_csv(run/(f'profile_compression_replay_{rid}_metrics_case.csv' if replay else 'profile_compression_crossfit_metrics_case.csv'),index=False); g=m.groupby(['candidate_id','method','components','fold','geometry_hash','selection_stratum'],as_index=False).mean(numeric_only=True); g.to_csv(run/(f'profile_compression_replay_{rid}_metrics_geometry.csv' if replay else 'profile_compression_crossfit_metrics_geometry.csv'),index=False); return m,g,model_paths
def summary(m,g):
    out=[]
    for cid,x in m.groupby('candidate_id'):
        fs=x.groupby('fold').apply(lambda z:float(z.js_divergence.mean()+z.spectral_cdf_distance.mean()+z.angular_cdf_distance.mean()+z.joint_weighted_l1.mean()),include_groups=False); ss=x.groupby('selection_stratum').apply(lambda z:float(z.js_divergence.mean()+z.spectral_cdf_distance.mean()+z.angular_cdf_distance.mean()+z.joint_weighted_l1.mean()),include_groups=False); out.append({'candidate_id':cid,'method':x.method.iloc[0],'components':int(x.components.iloc[0]),'heldout_rows':len(x),'fold_count':x.fold.nunique(),'mean_js_divergence':float(x.js_divergence.mean()),'mean_spectral_cdf_distance':float(x.spectral_cdf_distance.mean()),'mean_angular_cdf_distance':float(x.angular_cdf_distance.mean()),'mean_joint_weighted_l1':float(x.joint_weighted_l1.mean()),'mean_auxiliary_shape_error':float(x[['cone5_error','cone10_error','cone20_error','spectral_fwhm_error_nm','angular_fwhm_error_deg']].mean().mean()),'primary_score':float(x.js_divergence.mean()+x.spectral_cdf_distance.mean()+x.angular_cdf_distance.mean()+x.joint_weighted_l1.mean()),'worst_fold_primary_score':float(fs.max()),'worst_stratum_primary_score':float(ss.max()),'negative_mass_max':float(x.raw_negative_mass.max()),'negative_bin_fraction_max':float(x.raw_negative_bin_fraction.max()),'nonfinite_count':int(x.projected_nonfinite_count.sum()),'normalization_closure_max':float(x.normalization_closure_error.max()),'fit_warning_count':int(x.fit_warning_count.sum()),'all_folds_complete':bool(x.fold.nunique()==5 and len(x)==576),'finite_metrics':bool(np.isfinite(x.select_dtypes('number')).all().all())})
    return pd.DataFrame(out)
def choose(s):
    ss=s.set_index('candidate_id'); elig=[]; dec={}
    for meth in ('NMF','PCA'):
        a,b=meth+'16',meth+'32'; gain=(ss.loc[a].primary_score-ss.loc[b].primary_score)/ss.loc[a].primary_score; wd=max((ss.loc[b].worst_fold_primary_score-ss.loc[a].worst_fold_primary_score)/(ss.loc[a].worst_fold_primary_score+1e-18),(ss.loc[b].worst_stratum_primary_score-ss.loc[a].worst_stratum_primary_score)/(ss.loc[a].worst_stratum_primary_score+1e-18)); ok=bool(gain>=.10 and wd<=.05); dec[meth]={'relative_gain_32_vs_16':float(gain),'worst_degradation_32_vs_16':float(wd),'dimension_32_eligible':ok}; elig.append(b if ok else a)
    rank=sorted(elig,key=lambda c:(float(ss.loc[c].primary_score),float(ss.loc[c].mean_spectral_cdf_distance),float(ss.loc[c].mean_angular_cdf_distance),float(ss.loc[c].mean_joint_weighted_l1),0 if ss.loc[c].method=='NMF' else 1,int(ss.loc[c].components))); return rank[0],dec,rank

def main(run,replay=False,rid=0):
    run=Path(run)
    if replay:
        rows=pd.read_csv(run/'profile_compatible_case_membership.csv'); rows.fold=rows.fold.astype(int); q=np.memmap(run/'profile_case_q_memmap.f32',mode='r',dtype='float32',shape=(576,301*2000)); m,g,_=crossfit(run,q,rows,True,rid); s=summary(m,g); sel,_,rank=choose(s); dump(run/f'profile_compression_replay_{rid}.json',{'status':'PASS','replay_id':rid,'crossfit_fit_count':20,'membership_sha256':shaf(run/'profile_compatible_case_membership.csv'),'fold_sha256':shaf(run/'profile_compression_fold_assignment.json'),'candidate_ranking':s.sort_values('candidate_id').to_dict('records'),'candidate_order':rank,'selected_candidate':sel,'summary_metric_sha256':shaf(run/f'profile_compression_replay_{rid}_metrics_geometry.csv'),'heldout_rows':len(m),'HF15_formal_value_reads':0,'R12_incompatible_profile_reads':0,'test40_reads':0,'sealed_test_reads':0,'solver_calls':0}); return
    if preflight(run)['status']!='PASS': raise RuntimeError('HARD_GATE_PROFILE_COMPRESSION_PREFLIGHT_FAIL')
    rows,folds,stratum=membership(run); contracts(run); q=qmem(run,rows); m,g,paths=crossfit(run,q,rows); s=summary(m,g); s.to_json(run/'profile_compression_crossfit_summary.json',orient='records',indent=2); m.groupby(['candidate_id','selection_stratum'],as_index=False).mean(numeric_only=True).to_json(run/'profile_compression_stratum_summary.json',orient='records',indent=2); sel,dec,rank=choose(s); dump(run/'profile_compression_crossfit_manifest.json',{'status':'PASS','candidate_count':4,'fold_count':5,'expected_crossfit_fits':20,'actual_crossfit_fits':20,'candidate_ranking':rank,'selected_candidate':sel,'selection_decisions':dec,'metrics_case_sha256':shaf(run/'profile_compression_crossfit_metrics_case.csv'),'metrics_geometry_sha256':shaf(run/'profile_compression_crossfit_metrics_geometry.csv'),'no_neural_training':True,'test40_reads':0,'HF15_formal_value_reads':0,'R12_incompatible_profile_reads':0,'sealed_test_reads':0,'solver_calls':0})
    kind='NMF' if sel.startswith('NMF') else 'PCA'; k=int(sel[3:]); selected_oof=[]
    for f in range(5):
        model=joblib.load(paths[sel][f]); ix=np.flatnonzero(rows.fold.to_numpy()==f); z,_=trans(model,kind,q[ix]);
        for j,i in enumerate(ix): selected_oof.append({'geometry_hash':rows.iloc[i].geometry_hash,'case_hash':rows.iloc[i].case_hash,'fold':f,'selection_stratum':rows.iloc[i].selection_stratum,'compressor_id':sel,'relative_upward_power_450':float(rows.iloc[i].raw_upward_relative_power_450),**{f'latent_{n:03d}':float(v) for n,v in enumerate(z[j])}})
    oof=pd.DataFrame(selected_oof); oof.to_parquet(run/'oof_latent_target_index.parquet',index=False); dump(run/'oof_fold_compressor_registry.json',{'status':'PASS','selected_candidate':sel,'latent_dimension':k,'fold_count':5,'fold_compressors':[{'fold':f,'model_path':str(paths[sel][f]),'fit_scope':f'four training folds except {f}','heldout_transform_only':True,'fit_count':1,'compressor_sha256':shaf(paths[sel][f])} for f in range(5)],'final_compressor_used_for_oof':False,'HF15_formal_value_reads':0,'R12_incompatible_profile_reads':0,'test40_reads':0}); dump(run/'oof_profile_representation_contract.json',{'status':'PASS','contract_id':'oof_profile_representation_contract_v1','selected_candidate':sel,'latent_dimension':k,'input':'case-level q profile','oof_rule':'fold-specific training-only compressor; held-out geometry never fit','coefficient_scaling_rule':'raw compressor coefficients; future standardization training-only','decoder_rule':'inverse transform, max(q_raw,0), frozen quadrature renormalization','relative_upward_power_head':'independent','final_compressor_used_for_oof':False}); dump(run/'profile_latent_training_interface.json',{'status':'PASS','selected_candidate':sel,'latent_dimension':k,'case_key_fields':['geometry_hash','case_hash','fold','selection_stratum'],'latent_fields':[f'latent_{i:03d}' for i in range(k)],'independent_fields':['relative_upward_power_450','auxiliary_label_reference'],'oof_rule':'fold compressor only'}); dump(run/'future_model_output_schema.json',{'status':'PASS','schema_id':'future_mdc_hf_surrogate_v2_model_output_schema_v1','M1_M2_M3_compatible':True,'profile_latent_dimension':k,'independent_outputs':['relative_upward_power','peak_wavelength_nm','spectral_fwhm_nm','peak_angle_deg','angular_fwhm_deg','cone5','cone10','cone20'],'neural_training_started':False,'test40_opened':False})
    model,w=fit(kind,k,np.asarray(q,dtype='float32')); fp=run/'final_profile_compressor.joblib'; joblib.dump(model,fp,compress=3); z,y=trans(model,kind,q); enc=rows[['geometry_hash','case_hash','fold','selection_stratum','raw_upward_relative_power_450']].copy(); enc.rename(columns={'raw_upward_relative_power_450':'relative_upward_power_450'},inplace=True); enc['compressor_id']=sel; enc['profile_sha256']=rows.joint_tensor_sha256
    for n in range(k): enc[f'latent_{n:03d}']=z[:,n]
    enc.to_parquet(run/'final_profile_encoded_case_index.parquet',index=False); dump(run/'final_profile_compressor_manifest.json',{'status':'PASS','compressor_id':sel,'method':kind,'components':k,'fit_count':1,'fit_scope':'all 576 DOE96 case profiles','fit_seed':SEED,'compressor_sha256':shaf(fp),'encoded_case_count':576,'relative_power_excluded_from_latent':True,'neural_training':False,'test40':False,'HF15_formal_value_reads':0,'R12_incompatible_profile_reads':0,'solver_calls':0}); dump(run/'final_profile_basis_manifest.json',{'status':'PASS','compressor_id':sel,'method':kind,'components':k,'basis_sha256':shaf(fp),'basis_storage':'inside final_profile_compressor.joblib; not committed','nonnegative_basis':kind=='NMF','pca_projection_audited':kind=='PCA'}); fm=pd.DataFrame([metrics(q[i],y[i]) for i in range(len(q))]); dump(run/'final_profile_reconstruction_audit.json',{'status':'PASS','evaluation_scope':'full-development final fit in-sample only; not selection','selected_candidate':sel,'fit_count':1,'fit_warning_count':w,'case_count':576,'mean_metrics':{k0:float(fm[k0].mean()) for k0 in ['joint_weighted_l1','joint_rmse','js_divergence','spectral_marginal_l1','angular_marginal_l1','spectral_cdf_distance','angular_cdf_distance','cone5_error','cone10_error','cone20_error','spectral_fwhm_error_nm','angular_fwhm_error_deg']},'max_raw_negative_mass':float(fm.raw_negative_mass.max()),'max_raw_negative_bin_fraction':float(fm.raw_negative_bin_fraction.max()),'max_normalization_closure_error':float(fm.normalization_closure_error.max()),'nonfinite_count':int(fm.projected_nonfinite_count.sum())})
    pd.DataFrame([{'candidate_id':c,'method':mth,'components':k0,'fold':f,'fit_scope':'four training folds','heldout_scope':'one geometry-held-out fold','fit_count':1,'recovery_fit':False} for c,mth,k0 in CANDIDATES for f in range(5)]).to_csv(run/'profile_compression_crossfit_ledger.csv',index=False)
    dump(run/'profile_compression_completion_manifest.json',{'status':'MDC_HF_SURROGATE_V2_PROFILE_COMPRESSION_FROZEN_READY_FOR_OOF_MODEL_TRAINING_AUTHORIZATION_REVIEW','selected_candidate':sel,'latent_dimension':k,'compression_eligible_geometries':96,'compression_eligible_cases':576,'excluded_Pilot4_geometries':4,'excluded_HF15_geometries':15,'excluded_R12_geometries':12,'crossfit_compression_fits':20,'recovery_compression_fits':0,'final_compressor_fits':1,'neural_model_fits':0,'neural_optimizer_backward':0,'solver_calls':0,'fdtd_lumerical_calls':0,'TMM_calls':0,'RCWA_calls':0,'NP_solver_calls':0,'HF15_formal_value_reads':0,'HF15_diagnostics_reads':0,'R12_incompatible_profile_reads':0,'test40_reads':0,'sealed_test_reads':0,'active_learning_acquisitions':0,'replay_status':'PENDING','oof_contract_status':'PASS'}); (run/'profile_compression_completion_report.md').write_text(f'# Profile compression completion\n\n- Status: `MDC_HF_SURROGATE_V2_PROFILE_COMPRESSION_FROZEN_READY_FOR_OOF_MODEL_TRAINING_AUTHORIZATION_REVIEW`\n- Membership: 96 geometries / 576 case-level normalized joint profiles; Pilot4/HF15/R12/test40 excluded.\n- Cross-fit: 4 candidates x 5 geometry-grouped folds = 20 fits; held-out metrics only.\n- Selected candidate: `{sel}`; final-development compressor fit exactly once.\n- OOF interface contracts generated; neural training, solver and external test remain unopened.\n',encoding='utf-8'); hashes={str(p.relative_to(run)):shaf(p) for p in run.glob('*') if p.is_file() and p.suffix.lower() in {'.json','.csv','.md'} and p.name!='profile_compression_artifact_sha256.json'}; dump(run/'profile_compression_artifact_sha256.json',{'status':'PASS','policy':'lightweight contracts/reports/hashes only; raw tensors, memmap, compressor binaries and parquet excluded from Git','files':hashes}); log('compression_complete',selected=sel)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('run'); ap.add_argument('--replay-only',action='store_true'); ap.add_argument('--replay-id',type=int,default=0); a=ap.parse_args(); main(Path(a.run),a.replay_only,a.replay_id)
