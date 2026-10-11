"""Single full-rank structured state candidate: four folds / eight CPU fits."""
from pathlib import Path
import sys,json,os,time,hashlib,datetime,subprocess,importlib.util
import numpy as np
import joblib
from sklearn.kernel_ridge import KernelRidge
from k6_v2_pipeline.amended156 import adapter as A,evaluation as V
from k6_v2_pipeline import contracts as C,h1,np88_fusion_pilot_v1 as NP

TASK='COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
ROOT=A.ROOT;OUT=ROOT/'reports/coupling'/TASK
AUDIT=ROOT/'reports/coupling/COUPLING_ML_COMPLEX_MODAL_PHASE_LEARNABILITY_AUDIT_V1'
spec=importlib.util.spec_from_file_location('frozen_modal_math',AUDIT/'complex_modal_audit.py');D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
EPS=np.finfo(np.float64).eps;WEAK=1e-4;PHASE_EPS=64*EPS
def req(v,msg):
    if not v:raise ValueError(msg)
def put(n,d):A.write(OUT/n,d)
def read(n):return A.read(OUT/n)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stats(x):return V.summary(np.asarray(x).reshape(-1))
def pin(p):return {'path':str(p),'sha256':A.sha(p),'bytes':Path(p).stat().st_size}
def head_scaler(y):
    mean=y.mean(0);scale=float(np.sqrt(np.mean((y-mean)**2)))
    return {'mean':mean,'scale':scale if scale>0 else 1.,'constant_head':scale==0}
def transform(y,s):return (y-s['mean'])/s['scale']
def inverse(y,s):return y*s['scale']+s['mean']
def targets(c):
    c=np.asarray(c,np.complex128);req(c.ndim==4 and c.shape[1:]==(21,7,2) and np.isfinite(c).all(),'state_shape_finiteness')
    a,u=D.unit(c);den=(a*a).sum((2,3),keepdims=True);fraction=np.divide(a*a,den,out=np.zeros_like(a),where=den>0)
    reliable=(fraction>=WEAK)&(a>0);canonical=np.where(reliable,u,1+0j)
    amp=np.sqrt(a).reshape(len(c),294)
    phase=np.stack([canonical.real,canonical.imag],axis=-1).reshape(len(c),588)
    return amp,phase,reliable,a,u
def fallback_from_training(c):
    _,_,mask,a,u=targets(c);den=mask.sum(0);v=np.divide((u*mask).sum(0),den,out=np.zeros_like(u[0]),where=den>0)
    _,fallback=D.unit(v);return fallback,den
def reconstruct(amp_sqrt,phase_raw,fallback):
    req(amp_sqrt.ndim==2 and amp_sqrt.shape[1]==294 and phase_raw.shape==(len(amp_sqrt),588),'head_shapes')
    req(np.isfinite(amp_sqrt).all() and np.isfinite(phase_raw).all(),'head_nonfinite')
    a=(amp_sqrt*amp_sqrt).reshape(-1,21,7,2)
    xy=phase_raw.reshape(-1,21,7,2,2);v=xy[...,0]+1j*xy[...,1];norm=np.abs(v);use=norm<=PHASE_EPS
    unit=np.array(np.broadcast_to(fallback,v.shape),copy=True);np.divide(v,norm,out=unit,where=~use)
    c=a*unit;req(np.isfinite(c).all() and np.all(a>=0),'complex_reconstruction_nonfinite_or_negative')
    return c,{'phase_vector_norm':norm,'fallback_mask':use,'negative_sqrt_mask':amp_sqrt.reshape(-1,21,7,2)<0,'amplitude':a,'unit_phase':unit}
def numerical_tests():
    rng=np.random.default_rng(44156);c=rng.normal(size=(3,21,7,2))+1j*rng.normal(size=(3,21,7,2));c[0,0,0,0]=0;c[1,1,1,0]=1e-30
    a,u=D.unit(c);raw=np.stack([u.real,u.imag],-1).reshape(3,588);cp,info=reconstruct(np.sqrt(a).reshape(3,294),raw,np.ones((21,7,2),complex))
    req(abs(cp-c).max()<2e-15,'raw_full_rank_roundtrip')
    amp,phase,mask,_,_=targets(c);canonical=phase.reshape(3,21,7,2,2);req(np.all(canonical[~mask]==[1,0]),'weak_phase_convention')
    fb,count=fallback_from_training(c);zero,inf=reconstruct(np.zeros((3,294)),np.zeros((3,588)),fb);req(np.all(zero==0) and inf['fallback_mask'].all(),'zero_amplitude_or_phase_fallback')
    nonzero,inf=reconstruct(np.ones((3,294)),np.zeros((3,588)),fb);req(abs(nonzero-fb).max()<1e-15,'fallback_not_training_mean')
    angles=np.array([np.pi-.001,-np.pi+.001]);req(abs(np.angle(np.exp(1j*(angles[1]-angles[0])))-.002)<1e-12,'wrap')
    scaler=head_scaler(amp);req(abs(inverse(transform(amp,scaler),scaler)-amp).max()<1e-14,'head_scale_roundtrip')
    return {'status':'PASS','fits':0,'raw_roundtrip_max_abs':float(abs(cp-c).max()),'tolerance':2e-15,'weak_rule':'supervision canonicalization is deliberately not invertible at weak coordinates; raw full-rank representation is invertible, reliable coordinates unchanged','checks':['294/588 shapes','polar sqrt amplitude roundtrip includingzero/tiny','training-only weak canonical target','zero-vector fallback','negative sqrt squared nonnegative','2pi wrapping','head scaler inverse']}
def check_pins():
    p=read('STRUCTURED_MODEL_FROZEN_SPEC.json');req(A.sha(Path(__file__))==p['code_sha256'],'frozen_code_changed')
    for f in p['protected_files']:req(A.sha(f['path'])==f['sha256'],'protected_source_changed:'+f['path'])
    return p
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);req(not(OUT/'FIT_LEDGER.json').exists(),'do_not_refreeze_existing_task')
    req(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='674b36df4bd0f3317590c3402c4f5468c0d13a72','HEAD_changed_review_authority')
    col=A.load_collection(False);by={c.case_id:c for c in col.cases};runs=NP.baseline_runs(col);protected={};inventory_counts={}
    for base in [A.OUT,NP.OUT,AUDIT]:
        inv=base/'SHA_INVENTORY.json';items=A.read(inv)['files'];inventory_counts[str(base)]=len(items)
        for f in items:req(A.sha(f['path'])==f['sha256'],'frozen_artifact_changed');protected[f['path']]=f['sha256']
        protected[str(inv)]=A.sha(inv)
    protected[str(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json')]=A.INVENTORY_SHA
    folds=[];training_audit=[]
    for fold,p,base in runs:
        tr=list(base.task.train_case_ids);va=list(base.prediction_case_ids);c=np.array([by[cid].c_hat for cid in tr]);amp,phase,mask,a,u=targets(c);fb,count=fallback_from_training(c)
        req(np.isfinite(amp).all() and np.isfinite(phase).all(),'target_nonfinite');req(not(set(tr)&set(va)),'geometry_leakage')
        folds.append({'fold':fold,'task_id':f'structured_outer_{fold}','train_case_ids':tr,'heldout_case_ids':va,'gamma':float(base.model.gamma),'alpha':float(base.model.ridge_alpha),'kernel':'rbf','baseline_artifacts':[pin(p/n) for n in ['fit.joblib','fit_manifest.json','predictions.npz','AMENDMENT_PROVENANCE_AND_RELOAD.json']]})
        training_audit.append({'fold':fold,'weak_coordinate_fraction':float((~mask).mean()),'weak_true_energy_fraction':float((a*a*(~mask)).sum()/(a*a).sum()),'reliable_TE_TM_counts':mask.sum((0,1,2)).tolist(),'fallback_no_reliable_training_count':int((count==0).sum()),'phase_head_width':588,'amplitude_head_width':294,'scalers':'separate training channel means +single RMS/head; not per-coordinate variance; no PCA'})
    pins=[{'path':p,'sha256':s} for p,s in sorted(protected.items())]
    put('STRUCTURED_MODEL_FROZEN_SPEC.json',{'task':TASK,'utc_before_any_fit':utc(),'source_HEAD':'674b36df4bd0f3317590c3402c4f5468c0d13a72','code_sha256':A.sha(Path(__file__)),'protected_files':pins,'inventory_counts':inventory_counts,'candidate_count':1,'logical_folds':4,'state_head_fits':8,'P_scale_fits':0,'baseline_refits':0,'NP_MDC_inputs':False,'input':'same6 orderedD geometry scaler as original fold','amplitude':'target sqrt(abs(C_hat)), head inverse-scale then square (no clipping); report negative sqrt predictions','phase':'294 absolute [cos,sin] pairs; training fraction<1e-4 orzero ->[1,0]. No weak mask from heldout enters prediction. phase projection occurs after head inverse-scale.','fallback':'norm<=64float64eps -> unit corresponding mean of reliable training unitphasors; no reliable samples or exactlyzero mean ->unit1. Never heldout phase.','fallback_threshold':PHASE_EPS,'weak_training_threshold':WEAK,'heads':'float64 separate means+globalRMS; RBF gamma/alpha exactly original per-fold, no search; one seed irrelevant deterministic closed form','output':'C_hat294complex=588real +frozen physically predicted21P_scale=609; no fullstate normalization or oracle correction','baseline_P_scale':'elementwise exact reuse; no log/exp or fitting repeated','numeric_tolerances':{'raw_roundtrip_abs':2e-15,'saved_reload':'elementwise exact','H2_roundtrip_abs':1e-12},'bootstrap':{'geometry_units':True,'resamples':10000,'seed':4415601,'descriptive_only':True},'gain_rule':'metric median andq95 improve, pairedmedian<0, >=62/124wins, >=3/4fold pairedmedian<0; severe state tail: worstB<=worstA+0.1 (diagnostic research selector, not new H1 gate)','verdict':'state+routing+amplitude+phase+nonzero consistent gains andtail ->STATE_GAIN; onlyamplitude oronlyphase ->respectivepartial; otherwiseNO_CLEAR_GAIN, incomplete->INCONCLUSIVE','spectral_bands':{'full':list(range(440,461)),'center':list(range(445,456)),'blue':list(range(440,445)),'red':list(range(456,461))},'foreign_index_sha256':hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest(),'confirmation_responses':0,'development_limitation':'124heldouts repeatedly analyzed; not independent confirmation'})
    put('FOUR_FOLD_MATCHING_AND_SHA.json',{'status':'PASS','folds':folds,'train_only_preflight':training_audit,'A_restore_exact':True,'geometry_count':156,'heldout_total':sum(len(f['heldout_case_ids']) for f in folds),'heldout_unique':len(set(sum([f['heldout_case_ids'] for f in folds],[]))),'scientific_contract':{'state':[21,7,2],'reference_nm':1722,'D_order':'D1...D6','H1':C.H1_AUTHORITY_SHA256 if hasattr(C,'H1_AUTHORITY_SHA256') else 'bound by source inventories','P_scale':'frozen positive physical prediction'}})
    tests=numerical_tests();put('ZERO_FIT_NUMERICAL_PREFLIGHT.json',tests)
    req(tests['status']=='PASS','zero_fit_preflight_failed')
    put('FIT_LEDGER.json',{'authorized_state_head_fits':8,'fits':{f'{t["task_id"]}_{head}':{'fold':t['fold'],'head':head,'status':'PENDING','fit_invocations':0} for t in folds for head in ['amplitude','phase']}})
    print('PREFLIGHT_PASS_ZERO_FITS',json.dumps(training_audit),flush=True)
def save_prediction(payload,x):
    xb=payload['input_scaler'].transform(x);amp=inverse(payload['amplitude_model'].predict(xb),payload['amplitude_scaler']);phase=inverse(payload['phase_model'].predict(xb),payload['phase_scaler']);return reconstruct(amp,phase,payload['fallback'])
def train():
    check_pins();req(read('ZERO_FIT_NUMERICAL_PREFLIGHT.json')['status']=='PASS','preflight_notpass');col=A.load_collection(False);by={c.case_id:c for c in col.cases};bases={f:b for f,p,b in NP.baseline_runs(col)};ledger=read('FIT_LEDGER.json')
    for t in read('FOUR_FOLD_MATCHING_AND_SHA.json')['folds']:
        tr=t['train_case_ids'];va=t['heldout_case_ids'];base=bases[t['fold']];p=OUT/'models'/t['task_id'];p.mkdir(parents=True,exist_ok=True)
        x=np.array([by[cid].ordered_D_nm for cid in tr],float);c=np.array([by[cid].c_hat for cid in tr]);amp,phase,mask,a,u=targets(c);fallback,count=fallback_from_training(c);xb=base.x_scaler.transform(x);scalers={'amplitude':head_scaler(amp),'phase':head_scaler(phase)};models={}
        for head,target in [('amplitude',amp),('phase',phase)]:
            taskid=t['task_id']+'_'+head;row=ledger['fits'][taskid];path=p/(head+'_head.joblib')
            if row['status']=='COMPLETE':req(A.sha(path)==row['model_sha256'],'completed_head_hash');models[head]=joblib.load(path);continue
            req(row['status']=='PENDING' and row['fit_invocations']==0,'ambiguous_head_no_automatic_refit')
            yy=transform(target,scalers[head]);req(np.isfinite(yy).all(),'normalized_target_nonfinite')
            row.update(status='FITTING',fit_invocations=1,utc=utc(),training_ids_sha256=hashlib.sha256(json.dumps(tr).encode()).hexdigest());put('FIT_LEDGER.json',ledger);start=time.perf_counter()
            models[head]=KernelRidge(alpha=t['alpha'],gamma=t['gamma'],kernel='rbf').fit(xb,yy)
            joblib.dump(models[head],path,compress=3);row.update(status='COMPLETE',elapsed_seconds=time.perf_counter()-start,model_sha256=A.sha(path),output_coordinates=target.shape[1]);put('FIT_LEDGER.json',ledger);print('HEAD_COMPLETE',taskid,row['elapsed_seconds'],flush=True)
        payload={'amplitude_model':models['amplitude'],'phase_model':models['phase'],'amplitude_scaler':scalers['amplitude'],'phase_scaler':scalers['phase'],'input_scaler':base.x_scaler,'fallback':fallback,'task':t,'spec_sha256':A.sha(OUT/'STRUCTURED_MODEL_FROZEN_SPEC.json'),'P_scale_source':'baseline actual predictions'}
        xv=np.array([by[cid].ordered_D_nm for cid in va],float);cp,info=save_prediction(payload,xv);ct,traininfo=save_prediction(payload,x)
        joblib.dump(payload,p/'model.joblib',compress=3);reloaded=joblib.load(p/'model.joblib');rc,ri=save_prediction(reloaded,xv);req(np.array_equal(cp,rc),'saved_reload_prediction_not_exact')
        np.savez_compressed(p/'predictions.npz',case_ids=np.array(va),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=base.predicted_p_scale,phase_vector_norm=info['phase_vector_norm'],fallback_mask=info['fallback_mask'],negative_sqrt_mask=info['negative_sqrt_mask'])
        np.savez_compressed(p/'training_predictions.npz',case_ids=np.array(tr),C_hat_real=ct.real,C_hat_imag=ct.imag,phase_vector_norm=traininfo['phase_vector_norm'])
        put(f'{t["task_id"]}_PROVENANCE.json',{'fold':t['fold'],'task':t,'model':pin(p/'model.joblib'),'prediction':pin(p/'predictions.npz'),'training_prediction':pin(p/'training_predictions.npz'),'reload_exact':True,'phase_fallback_training_source_only':True,'input_scaler_identical_baseline':True,'P_scale_elementwise_exact':True,'weak_training_fraction':float((~mask).mean()),'negative_sqrt_prediction_fraction':float(info['negative_sqrt_mask'].mean()),'phase_vector_norm':stats(info['phase_vector_norm']),'phase_vector_norm_below_point1':float((info['phase_vector_norm']<.1).mean()),'phase_vector_norm_below_point5':float((info['phase_vector_norm']<.5).mean()),'fallback_count':int(info['fallback_mask'].sum()),'fallback_predicted_amplitude_squared_share':float((abs(cp)**2*info['fallback_mask']).sum()/(abs(cp)**2).sum()),'scalers':{head:{'mean':scalers[head]['mean'].tolist(),'scale':scalers[head]['scale'],'constant_head':scalers[head]['constant_head']} for head in scalers}})
    req(sum(q['fit_invocations'] for q in ledger['fits'].values())==8 and all(q['status']=='COMPLETE' for q in ledger['fits'].values()),'fit_budget_incomplete');print('ALL_8_HEAD_FITS_COMPLETE',flush=True)
def bootstrap(d):
    rng=np.random.default_rng(4415601);d=np.asarray(d);draw=d[rng.integers(len(d),size=(10000,len(d)))];return {'mean_CI95':np.quantile(draw.mean(1),[.025,.975]).tolist(),'median_CI95':np.quantile(np.median(draw,1),[.025,.975]).tolist(),'geometry_unit_descriptive':True}
def evaluate():
    check_pins();col=A.load_collection(False);by={c.case_id:c for c in col.cases};bases={f:b for f,p,b in NP.baseline_runs(col)};meta={q['case_id']:q for q in A.inventory()['cases']};folds=read('FOUR_FOLD_MATCHING_AND_SHA.json')['folds'];ids=sum([t['heldout_case_ids'] for t in folds],[]);req(len(ids)==len(set(ids))==124,'OOF_identity')
    ct=np.array([by[cid].c_hat for cid in ids]);pt=np.array([by[cid].p_scale for cid in ids]);eta=np.array([by[cid].eta for cid in ids]);absolute=np.array([by[cid].absolute_order for cid in ids]);cpA=np.concatenate([bases[t['fold']].predicted_c_hat for t in folds]);pp=np.concatenate([bases[t['fold']].predicted_p_scale for t in folds]);cb=[];bb=[];training=[]
    for t in folds:
        p=OUT/'models'/t['task_id'];prov=read(t['task_id']+'_PROVENANCE.json');req(A.sha(p/'predictions.npz')==prov['prediction']['sha256'],'prediction_hash')
        with np.load(p/'predictions.npz',allow_pickle=False) as z:
            req(z['case_ids'].tolist()==t['heldout_case_ids'] and np.array_equal(z['P_scale'],bases[t['fold']].predicted_p_scale),'Pscale_orID_mismatch');cb.append(z['C_hat_real']+1j*z['C_hat_imag']);bb.append(z['phase_vector_norm'])
        with np.load(p/'training_predictions.npz',allow_pickle=False) as z:
            ctrain=np.array([by[cid].c_hat for cid in t['train_case_ids']]);cp=z['C_hat_real']+1j*z['C_hat_imag'];training.append({'fold':t['fold'],'train_state_relative_RMSE':stats(np.linalg.norm((cp-ctrain).reshape(124,-1),axis=1)/np.linalg.norm(ctrain.reshape(124,-1),axis=1)),'train_amplitude_relative_RMSE':stats(np.linalg.norm((abs(cp)-abs(ctrain)).reshape(124,-1),axis=1)/np.linalg.norm(ctrain.reshape(124,-1),axis=1)),'train_phase':D.angular_stats(ctrain,cp,WEAK),'phase_vector_norm':stats(z['phase_vector_norm'])})
    cpB=np.concatenate(cb);phasevec=np.concatenate(bb);dec=h1.load_h2_decoder();reports={};diag={};decomp={};angular={};modal={};headresults={};hd={};per={}
    for arm,cp in [('A',cpA),('B',cpB)]:
        reports[arm]=h1.evaluate_original_h1(ct,cp,pt,pp,eta,absolute,dec);diag[arm]=V.diagnostics(ct,cp,ids,meta);hd[arm]=h1.reconstruct_h2(cp,pp,dec);am,ph,err,delta=D.error_decomposition(ct,cp);sq=abs(ct)**2;den=sq.sum((1,2,3))
        ar=np.sqrt(am.sum((1,2,3))/den);pr=np.sqrt(ph.sum((1,2,3))/den);angles=D.angular_stats(ct,cp,WEAK);angular[arm]=angles
        headresults[arm]={'amplitude_relative_RMSE':stats(ar),'phase_component_relative_RMSE':stats(pr),'absolute_phase_RMSE':angles['absolute_phase_RMSE'],'relative_phase_RMSE':angles['relative_phase_RMSE'],'per_geometry':[{'case_id':cid,'amplitude_relative_RMSE':float(ar[k]),'phase_component_relative_RMSE':float(pr[k]),'absolute_phase_RMSE':angles['per_geometry_absolute'][k],'relative_phase_RMSE':angles['per_geometry_relative'][k]} for k,cid in enumerate(ids)]};per[arm]={'amplitude_relative_rmse':ar,'phase_component_relative_rmse':pr,'absolute_phase_rmse':np.array(angles['per_geometry_absolute']),'relative_phase_rmse':np.array(angles['per_geometry_relative'])}
        decomp[arm]={'pooled_amplitude_SSE_fraction':float(am.sum()/err.sum()),'pooled_phase_SSE_fraction':float(ph.sum()/err.sum()),'pooled_amplitude_SSE':float(am.sum()),'pooled_phase_SSE':float(ph.sum()),'error_by_order_fraction':(err.sum((0,1,3))/err.sum()).tolist(),'error_TE_TM_fraction':(err.sum((0,1,2))/err.sum()).tolist(),'error_wavelength_fraction':(err.sum((0,2,3))/err.sum()).tolist(),'threshold_sensitivity':[D.angular_stats(ct,cp,v) for v in D.THRESHOLDS],'strength_bins':[]}
        fraction=sq/sq.sum((2,3),keepdims=True)
        for lo,hi in [(0,1e-6),(1e-6,1e-4),(1e-4,1e-2),(1e-2,1.000001)]:
            mask=(fraction>=lo)&(fraction<hi);decomp[arm]['strength_bins'].append({'fraction_range':[lo,hi],'count':int(mask.sum()),'amplitude_SSE':float(am[mask].sum()),'phase_SSE':float(ph[mask].sum()),'state_SSE':float(err[mask].sum())})
        entries={}
        for name,orders in [('zero',[3]),('nonzero',[0,1,2,4,5,6]),('plus1',[4]),('other_nonzero',[0,1,2,5,6])]:
            xx=ct[:,:,orders,:];yy=cp[:,:,orders,:];dd=(abs(xx)**2).sum((1,2,3));rel=np.sqrt((abs(xx-yy)**2).sum((1,2,3))/dd);entries[name]={'state_relative_RMSE':stats(rel),'per_geometry_state_relative_RMSE':rel.tolist(),'norm_ratio':stats(np.linalg.norm(yy.reshape(124,-1),axis=1)/np.linalg.norm(xx.reshape(124,-1),axis=1)),'routing_RMSE':stats(np.sqrt(np.mean((hd[arm]['eta'][:,:,orders]-eta[:,:,orders])**2,(1,2)))),'absolute_order_RMSE':stats(np.sqrt(np.mean((hd[arm]['absolute_order'][:,:,orders]-absolute[:,:,orders])**2,(1,2))))}
        entries['order_TE_TM']=[{'m':j-3,'pol':['TE','TM'][k],'relative_RMSE':float(np.sqrt(err[:,:,j,k].sum()/sq[:,:,j,k].sum())),'SSE':float(err[:,:,j,k].sum()),'truth_energy':float(sq[:,:,j,k].sum()),'note':'weakTErelative denominator diagnostic only'} for j in range(7) for k in range(2)];modal[arm]=entries
        np.savez_compressed(OUT/f'{arm}_OOF_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=pp)
    frozen=A.read(A.OUT/'KRR_LEARNING_CURVE_RESULTS.json')['124'];req(reports['A']['aggregate']==frozen['aggregate'] and reports['A']['gates']==frozen['gates'],'baseline_H1_parity')
    put('H1_H2_FINAL_EVALUATION.json',reports);put('RECONSTRUCTED_COMPLEX_STATE_RESULTS.json',diag);put('AMPLITUDE_PHASE_ERROR_DECOMPOSITION.json',decomp);put('NONZERO_ORDER_MODAL_ANALYSIS.json',modal);put('AMPLITUDE_HEAD_RESULTS.json',{'heldout':headresults,'training':training});put('CIRCULAR_PHASE_HEAD_RESULTS.json',{'heldout':angular,'training':training,'raw_B_phase_vector_norm':stats(phasevec),'fraction_below_point1':float((phasevec<.1).mean()),'fraction_below_point5':float((phasevec<.5).mean()),'unit_phase_norm_max_abs_error':float(abs(abs(D.unit(cpB)[1])-1).max()),'projection_no_test_truth':True})
    metrics={k:np.array([r[k] for r in reports['A']['aggregate']['per_geometry']]) for k in reports['A']['aggregate']['per_geometry'][0]};paired={}
    per['A'].update(metrics);per['B'].update({k:np.array([r[k] for r in reports['B']['aggregate']['per_geometry']]) for k in metrics});per['A']['nonzero_state_rmse']=np.array(modal['A']['nonzero']['per_geometry_state_relative_RMSE']);per['B']['nonzero_state_rmse']=np.array(modal['B']['nonzero']['per_geometry_state_relative_RMSE'])
    for k in per['A']:
        a=per['A'][k];b=per['B'][k];delta=b-a;pf={}
        for t in folds:
            ix=[ids.index(cid) for cid in t['heldout_case_ids']];dd=delta[ix];pf[str(t['fold'])]={'n':len(ix),'delta':stats(dd),'wins':int((dd<0).sum()),'losses':int((dd>0).sum())}
        rows=[{'case_id':cid,'fold':next(t['fold'] for t in folds if cid in t['heldout_case_ids']),'role':by[cid].role,'A':float(a[i]),'B':float(b[i]),'delta':float(delta[i])} for i,cid in enumerate(ids)]
        paired[k]={'A':stats(a),'B':stats(b),'delta':stats(delta),'wins':int((delta<0).sum()),'losses':int((delta>0).sum()),'ties':int((delta==0).sum()),'folds':pf,'bootstrap':bootstrap(delta),'per_geometry':rows,'worst_worsenings':sorted(rows,key=lambda q:q['delta'],reverse=True)[:10]}
    put('PAIRED_CARTESIAN_KRR_COMPARISON.json',paired)
    metric_source=h1._load(ROOT/'scripts/coupling_ml/pw_k6_stage1_32g_frozen_model_v1.py','structured_frozen_metrics',C.MODEL_SOURCE_SHA256);spectra={}
    for name,wls in read('STRUCTURED_MODEL_FROZEN_SPEC.json')['spectral_bands'].items():
        ix=np.array(wls)-440;entry={}
        for arm,cp in [('A',cpA),('B',cpB)]:
            rows=[{'case_id':cid,**metric_source.met(ct[i,ix],cp[i,ix],eta[i,ix],hd[arm]['eta'][i,ix],absolute[i,ix],hd[arm]['absolute_order'][i,ix],pt[i,ix],pp[i,ix])} for i,cid in enumerate(ids)];entry[arm]={'metrics':{k:stats([r[k] for r in rows]) for k in rows[0] if k!='case_id'},'per_geometry':rows}
        spectra[name]=entry
    put('WAVELENGTH_STRATIFIED_RESULTS.json',spectra)
    def gain(k):
        p=paired[k];return p['B']['median']<p['A']['median'] and p['B']['q95']<p['A']['q95'] and p['delta']['median']<0 and p['wins']>=62 and sum(v['delta']['median']<0 for v in p['folds'].values())>=3
    sg=gain('state_relative_rmse');ag=gain('amplitude_relative_rmse');pg=gain('absolute_phase_rmse');rg=gain('routing_eta_rmse');ng=gain('nonzero_state_rmse');tail=paired['state_relative_rmse']['B']['worst']<=paired['state_relative_rmse']['A']['worst']+.1
    verdict='STRUCTURED_COMPLEX_STATE_GAIN_SUPPORTED' if sg and ag and pg and rg and ng and tail else ('STRUCTURED_AMPLITUDE_ONLY_GAIN' if ag and not pg else ('STRUCTURED_PHASE_ONLY_GAIN' if pg and not ag else 'STRUCTURED_COMPLEX_STATE_NO_CLEAR_GAIN'))
    put('FINAL_SCIENTIFIC_VERDICT.json',{'verdict':verdict,'consistent_gain':{'state':sg,'amplitude':ag,'phase':pg,'routing':rg,'nonzero':ng,'state_tail_rule':tail},'H1':{k:r['all_applicable_numeric_gates_attained'] for k,r in reports.items()},'P_scale_exact':True,'independent_confirmation':False,'production_admission':False,'new_head_fits':8})
    check_pins();ledger=read('FIT_LEDGER.json');req(sum(q['fit_invocations'] for q in ledger['fits'].values())==8,'fit_count')
    put('FINAL_ISOLATION_CHECK.json',{'status':'PASS','fits':8,'logical_candidates':4,'baseline_fits':0,'P_scale_fits':0,'FDTD':0,'replay':0,'confirmation_response_access':0,'protected_hashes_unchanged':True,'P_scale_A_B_elementwise_exact':True,'baseline_H1_exact':True,'model_reloads_exact':True,'local13':'SUSPENDED'})
    table=['|Metric|A median/q95|B median/q95|wins/losses|','|---|---:|---:|---:|']+[f"|{k}|{v['A']['median']:.6f}/{v['A']['q95']:.6f}|{v['B']['median']:.6f}/{v['B']['q95']:.6f}|{v['wins']}/{v['losses']}|" for k,v in paired.items()]
    (OUT/'NUMERIC_COMPARISON.md').write_bytes(('\n'.join(table)+'\n').encode());print('\n'.join(table),flush=True);print('VERDICT',verdict,flush=True)
if __name__=='__main__':
    os.environ['CUDA_VISIBLE_DEVICES']=''
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='train':train()
    elif sys.argv[1]=='evaluate':evaluate()
    else:raise ValueError('unknown mode')
