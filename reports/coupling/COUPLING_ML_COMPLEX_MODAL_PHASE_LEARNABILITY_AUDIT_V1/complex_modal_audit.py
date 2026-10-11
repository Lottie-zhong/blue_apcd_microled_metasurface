"""Zero-fit complex/modal mathematics; never invokes a model fit or solver."""
from pathlib import Path
import sys,json,csv,hashlib,subprocess,datetime,itertools
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics.pairwise import rbf_kernel,euclidean_distances
import joblib
from k6_v2_pipeline.amended156 import adapter as A,engine as E,evaluation as V
from k6_v2_pipeline import contracts as C,h1,np88_fusion_pilot_v1 as NP

TASK='COUPLING_ML_COMPLEX_MODAL_PHASE_LEARNABILITY_AUDIT_V1'
OUT=A.ROOT/'reports/coupling'/TASK
EPS=np.finfo(float).eps
THRESHOLDS=(1e-6,1e-5,1e-4,1e-3,1e-2)
def req(x,m):
    if not x:raise ValueError(m)
def put(n,d):A.write(OUT/n,d)
def summary(x):
    x=np.asarray(x,float).reshape(-1);x=x[np.isfinite(x)]
    return V.summary(x) if len(x) else None
def corr(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float);keep=np.isfinite(x)&np.isfinite(y)
    if keep.sum()<3 or x[keep].std()==0 or y[keep].std()==0:return {'count':int(keep.sum()),'pearson':None,'spearman':None}
    return {'count':int(keep.sum()),'pearson':float(np.corrcoef(x[keep],y[keep])[0,1]),'spearman':float(spearmanr(x[keep],y[keep]).statistic),'causal_or_significance_claim':False}
def pin(p):return {'path':str(p),'sha256':A.sha(p),'bytes':Path(p).stat().st_size}
def unit(c):
    c=np.asarray(c,complex);a=abs(c);u=np.ones_like(c);np.divide(c,a,out=u,where=a>0);return a,u
def error_decomposition(truth,pred):
    a,u=unit(truth);b,v=unit(pred)
    amp=(b-a)**2;delta=np.angle(v*np.conj(u));phase=2*a*b*(1-np.cos(delta));total=abs(pred-truth)**2
    residual=float(np.max(abs(total-amp-phase)));req(residual<=1e-12*max(1.,float(total.max())),'complex_SSE_identity_failed')
    return amp,phase,total,delta
def gauge(c,reference='dominant'):
    z=np.asarray(c,complex);f=z.reshape(z.shape[:-2]+(14,));a,u=unit(f)
    idx=np.argmax(a,axis=-1) if reference=='dominant' else np.full(a.shape[:-1],7,dtype=int) # m0 TM flattened index7
    frac=a*a/np.maximum((a*a).sum(-1,keepdims=True),1e-300)
    if reference=='fixed0_switch':idx=np.where(frac[...,7]>=1e-4,idx,np.argmax(a,-1))
    com=np.take_along_axis(u,idx[...,None],-1)[...,0]
    relative=f*com.conj()[...,None]
    return com,relative.reshape(z.shape),idx
def oracle_alignment(truth,pred,per_wavelength=False):
    axes=(-2,-1) if per_wavelength else (-3,-2,-1)
    dot=np.sum(truth*pred.conj(),axis=axes,keepdims=True);a,u=unit(dot)
    return pred*u # exact zero dot -> fixed unit; no predictive use

def tests():
    rng=np.random.default_rng(156041);t=rng.normal(size=(5,21,7,2))+1j*rng.normal(size=(5,21,7,2));p=rng.normal(size=t.shape)+1j*rng.normal(size=t.shape)
    t[0]=0;t[1,:,0,:]=1e-30;p[2]=0
    a,ph,e,_=error_decomposition(t,p);req(np.all(ph[0]==0) and np.all(ph[2]==0),'zero_phase_SSE_must_be_zero')
    aa,uu=unit(t);req(np.allclose(aa*uu,t,rtol=0,atol=1e-15),'polar_roundtrip')
    for reference in ['dominant','fixed0_switch']:
        com,rel,idx=gauge(t,reference);req(np.allclose(com[...,None,None]*rel,t,rtol=0,atol=2e-15),'gauge_roundtrip')
    phi=np.array([np.pi-.001,-np.pi+.001]);req(abs(np.angle(np.exp(1j*(phi[1]-phi[0])))-.002)<1e-12,'wrap_vs_physical_increment')
    q=t*np.exp(1j*.8);req(np.allclose(oracle_alignment(t,q),t,rtol=0,atol=1e-14),'oracle_common_phase_sign')
    req(float(np.sum(abs(oracle_alignment(t,p)-t)**2))<=float(np.sum(e))+1e-12,'oracle_minimum')
    return {'status':'PASS','fits':0,'checks':['exact amplitude-phase SSE identity including zero/1e-30','reversiblepolar zero phase=unit1','dominant and fixed0/reference-switch gauge roundtrip','2pi wrapping principal increment','oracle optimalcommonphase sign/minimum; diagnostic only']}

def freeze():
    OUT.mkdir(parents=True,exist_ok=True);req(not(OUT/'INPUT_PINS.json').exists(),'existing_task_do_not_refreeze')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=A.ROOT,text=True).strip();req(head=='d481a82796d3b2998313f7e21f19cec80eae3cab','start_HEAD_conflict')
    sources={};verified={}
    for base in [A.OUT,NP.OUT]:
        inventory=base/'SHA_INVENTORY.json';d=A.read(inventory);count=0
        for q in d['files']:
            req(A.sha(q['path'])==q['sha256'],'frozen_artifact_changed:'+q['path']);sources[q['path']]=q['sha256'];count+=1
        sources[str(inventory)]=A.sha(inventory);verified[str(base)]=count
    sources[str(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json')]=A.INVENTORY_SHA
    for p in [A.ROOT/'reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json',A.ROOT/'scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py',A.ROOT/'scripts/coupling_ml/k6_v2_pipeline/ingest.py',A.ROOT/'reports/coupling/COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1/EXT02_TWO_AIR_PLANES_EVALUATION_REPORT_V2.md',A.ROOT/'reports/coupling/COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1/EXT02_TWO_AIR_PLANES_EVALUATION_V2.json']:
        sources[str(p)]=A.sha(p)
    put('INPUT_PINS.json',{'source_HEAD':head,'source_inventory_files_verified':verified,'files':[{'path':p,'sha256':s} for p,s in sorted(sources.items())],'foreign_index_sha256':hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=A.ROOT)).hexdigest(),'source_code_sha256':A.sha(Path(__file__)),'confirmation_response_access':0})
    put('DIAGNOSTIC_PROTOCOL.json',{'utc_before_analysis':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase_reference':'fixed POSTNP1722nm, input IN-50nm TM source gauge, never redefined for official prediction','comparison':'same124new OOF IDs; KRR124/MLP124complex seedmean/NP88. Truth descriptiveall156. Originalpredictors/gates unchanged.','zero_amplitude':'A=0 -> unitphase1 for roundtrip; phaseSSE0 automatically. Exact0 coordinates no phase angle statistic.','significant_fraction_threshold_sensitivity':list(THRESHOLDS),'mask':'truth coordinate |C|^2 / all14 perlambda energy; phase statistic weights truthenergy, predictiondefined >64eps*sqrt(perlambda truthenergy); report coverage','field_strength_bins':[0,1e-6,1e-4,1e-2,1.000001],'complex_SSE_identity':'(A_pred-A)^2+2*A_pred*A*(1-cos(delta_phi)); raw original coordinates, no alignment','oracle_label':'RETROSPECTIVE_ORACLE_DIAGNOSTIC; truthA/predphase, predA/truthphase, optimal onegeometryphase and perlambda commonphase; not H1 or prediction','distance':'ordered Euclidean ||D_i-D_j||/130nm; symmetricresponse ||Ci-Cj||/sqrt(.5*(||Ci||²+||Cj||²)); physicalreference unchanged','neighbor_bins':[0,.1,.25,.5,1,3],'pooling':'pooledSSE shares and geometrymedian separate; pairrows sharegeometries, no independentpair/21lambda claims','local':'S31 anchor+11axes;D6minusmissing; no validated six-dimensional +/- response. Singlecase crossheight error is not controlledrunrepeatability.','fits':0,'P_scale_fits':0,'FDTD':0,'replay':0,'confirmation_response_access':0})
    put('MATHEMATICAL_IMPLEMENTATION_TESTS.json',tests());print('INPUT_PIN_AND_ZERO_FIT_TEST_PASS',verified,flush=True)

def angular_stats(t,p,threshold):
    sq=abs(t)**2;frac=sq/sq.sum((2,3),keepdims=True);mask=frac>=threshold
    defined=abs(p)>64*EPS*np.sqrt(sq.sum((2,3),keepdims=True));keep=mask&defined&(sq>0);w=sq*keep
    phase=np.angle(p*t.conj());den=w.sum((1,2,3));r=np.sqrt(np.divide((w*phase**2).sum((1,2,3)),den,out=np.full(len(t),np.nan),where=den>0))
    rn=np.zeros(len(t));rd=np.zeros(len(t))
    for i,j in itertools.combinations(range(7),2):
        u=keep[:,:,i,:]&keep[:,:,j,:];delta=np.angle(p[:,:,i,:]*p[:,:,j,:].conj()*t[:,:,i,:].conj()*t[:,:,j,:]);ww=abs(t[:,:,i,:])*abs(t[:,:,j,:])*u
        rn+=(ww*delta**2).sum((1,2));rd+=ww.sum((1,2))
    rel=np.sqrt(np.divide(rn,rd,out=np.full(len(t),np.nan),where=rd>0))
    return {'threshold':threshold,'truth_energy_retained_fraction':float((sq*mask).sum()/sq.sum()),'truth_weight_phase_coverage':float(w.sum()/max(float((sq*mask).sum()),1e-300)),'absolute_phase_RMSE':summary(r),'relative_phase_RMSE':summary(rel),'per_geometry_absolute':r.tolist(),'per_geometry_relative':[None if not np.isfinite(q) else float(q) for q in rel]}

def decompose_models(ct,predictions,ids):
    out={};oracle={}
    for kind,(cp,pp) in predictions.items():
        amp,phase,error,delta=error_decomposition(ct,cp);den=error.sum();sq=abs(ct)**2;frac=sq/sq.sum((2,3),keepdims=True)
        rows=[]
        for i,cid in enumerate(ids):
            rows.append({'case_id':cid,'state_relative_RMSE':float(np.sqrt(error[i].sum()/sq[i].sum())),'amplitude_SSE':float(amp[i].sum()),'phase_SSE':float(phase[i].sum()),'amplitude_fraction':float(amp[i].sum()/error[i].sum()),'phase_fraction':float(phase[i].sum()/error[i].sum()),'by_order_amplitude_SSE':amp[i].sum((0,2)).tolist(),'by_order_phase_SSE':phase[i].sum((0,2)).tolist(),'by_TE_TM_amplitude_SSE':amp[i].sum((0,1)).tolist(),'by_TE_TM_phase_SSE':phase[i].sum((0,1)).tolist(),'by_wavelength_amplitude_SSE':amp[i].sum((1,2)).tolist(),'by_wavelength_phase_SSE':phase[i].sum((1,2)).tolist()})
        bins=[]
        for low,high in zip([0,1e-6,1e-4,1e-2],[1e-6,1e-4,1e-2,1.000001]):
            use=(frac>=low)&(frac<high);bins.append({'fraction_range':[low,high],'coordinate_count':int(use.sum()),'truth_energy_fraction':float(sq[use].sum()/sq.sum()),'state_SSE_fraction':float(error[use].sum()/den),'amplitude_SSE_fraction':float(amp[use].sum()/den),'phase_SSE_fraction':float(phase[use].sum()/den)})
        out[kind]={'identity_max_abs_residual':float(np.max(abs(error-amp-phase))),'pooled_amplitude_SSE_fraction':float(amp.sum()/den),'pooled_phase_SSE_fraction':float(phase.sum()/den),'per_geometry_amplitude_fraction':summary([q['amplitude_fraction'] for q in rows]),'per_geometry_phase_fraction':summary([q['phase_fraction'] for q in rows]),'by_order_SSE_fraction':(error.sum((0,1,3))/den).tolist(),'by_order_amplitude_SSE_fraction':(amp.sum((0,1,3))/den).tolist(),'by_order_phase_SSE_fraction':(phase.sum((0,1,3))/den).tolist(),'by_TE_TM_SSE_fraction':(error.sum((0,1,2))/den).tolist(),'by_TE_TM_amplitude_SSE_fraction':(amp.sum((0,1,2))/den).tolist(),'by_TE_TM_phase_SSE_fraction':(phase.sum((0,1,2))/den).tolist(),'by_wavelength_SSE_fraction':(error.sum((0,2,3))/den).tolist(),'field_strength_bins':bins,'angular_threshold_sensitivity':[angular_stats(ct,cp,v) for v in THRESHOLDS],'geometry_rows':rows,'loss_weight_warning':'SSEshares retrospective, not optimal lossweights; suppressedAp reducesphaseSSEevenwhenphasepredictionbad'}
        a,u=unit(ct);b,v=unit(cp);candidates={'true_amplitude_predicted_phase':a*v,'predicted_amplitude_true_phase':b*u,'one_phase_per_geometry':oracle_alignment(ct,cp,False),'one_common_phase_per_wavelength':oracle_alignment(ct,cp,True)}
        oo={}
        for name,c in candidates.items():
            err=abs(c-ct)**2;oo[name]={'state_relative_RMSE':summary(np.sqrt(err.sum((1,2,3))/sq.sum((1,2,3)))),'pooled_SSE_over_original':float(err.sum()/den),'per_geometry':[{'case_id':cid,'relative_RMSE':float(np.sqrt(err[i].sum()/sq[i].sum()))} for i,cid in enumerate(ids)]}
        oracle[kind]={'label':'RETROSPECTIVE_ORACLE_DIAGNOSTIC','forbidden_for_H1_prediction_admission':True,'diagnostics':oo,'common_perlambda_SSE_explained_fraction':float(1-oo['one_common_phase_per_wavelength']['pooled_SSE_over_original']),'common_onegeom_SSE_explained_fraction':float(1-oo['one_phase_per_geometry']['pooled_SSE_over_original'])}
    put('COMPLEX_ERROR_AMPLITUDE_PHASE_DECOMPOSITION.json',out);put('RETROSPECTIVE_ORACLE_DIAGNOSTIC.json',oracle)
    return out,oracle

def modal_energy(allc,ct,preds,ids):
    dec=h1.load_h2_decoder();w=h1.h2_weights(dec);eta0=float(dec.ETA0);q=w*2*eta0
    power=(abs(allc)**2*q).sum((2,3));req(np.max(abs(power-1))<1e-10,'C_hat_unit_modal_normalization_conflict')
    physical={};scope={'TRUTH_156G':allc,'TRUTH_MATCHED_124G':ct,**{k:v[0] for k,v in preds.items()}}
    for name,c in scope.items():
        sq=abs(c)**2;modal=sq*q;total=modal.sum((2,3));counts=np.bincount(np.argmax(modal.reshape(len(c),21,14),-1).reshape(-1),minlength=14)
        physical[name]={'Cartesian_coordinate_energy_by_order_fraction':(sq.sum((0,1,3))/sq.sum()).tolist(),'power_metric_energy_by_order_fraction':(modal.sum((0,1,3))/modal.sum()).tolist(),'Cartesian_TE_TM_energy_fraction':(sq.sum((0,1,2))/sq.sum()).tolist(),'power_metric_TE_TM_fraction':(modal.sum((0,1,2))/modal.sum()).tolist(),'unit_power_metric_norm_squared':summary(total),'dominant_order_polarization_counts':[{'m':m,'pol':pol,'count':int(counts[2*j+k])} for j,m in enumerate(range(-3,4)) for k,pol in enumerate(['TE','TM'])]}
    h2stats={};pt=np.array([GLOBALS['by'][cid].p_scale for cid in ids]);et=np.array([GLOBALS['by'][cid].eta for cid in ids]);at=np.array([GLOBALS['by'][cid].absolute_order for cid in ids])
    for name,(cp,pp) in preds.items():
        h=h1.reconstruct_h2(cp,pp,dec);amp,phase,err,_=error_decomposition(ct,cp)
        state=np.sqrt(err.sum((1,2,3))/(abs(ct)**2).sum((1,2,3)));routing=np.sqrt(np.mean((h['eta']-et)**2,(1,2)));ps=np.sqrt(np.mean(((pp-pt)/pt)**2,1));phasefrac=phase.sum((1,2,3))/err.sum((1,2,3));normratio=np.linalg.norm(cp.reshape(len(ct),-1),axis=1)/np.linalg.norm(ct.reshape(len(ct),-1),axis=1)
        h2stats[name]={'phase_SSE_vs_routing_RMSE':corr(np.sqrt(phase.sum((1,2,3))/(abs(ct)**2).sum((1,2,3))),routing),'phase_angle_vs_routing_RMSE':corr(angular_stats(ct,cp,1e-4)['per_geometry_absolute'],routing),'state_vs_P_scale_RMSE':corr(state,ps),'routing_vs_P_scale_RMSE':corr(routing,ps),'norm_ratio_vs_state_RMSE':corr(normratio,state),'order_norm_prediction_truth_ratio':[{ 'm':m,'ratio':summary(np.linalg.norm(cp[:,:,j,:].reshape(len(ct),-1),axis=1)/np.linalg.norm(ct[:,:,j,:].reshape(len(ct),-1),axis=1))} for j,m in enumerate(range(-3,4))],'H2_routing_phase_independence':'H2=sum_polarization positiveweights*|C|² normalizedperlambda; no TE/TMcross terms, phases do not directly alter routing. Correlations reflect shared geometry/amplitude effects, not phasecauses routing.','raw_predicted_power_metric_norm_not_corrected':summary((abs(cp)**2*q).sum((2,3)))}
    put('MODAL_ENERGY_AND_ERROR_CONTRIBUTIONS.json',{'scope':physical,'model_relations':h2stats,'power_weight_kz_over_k0':q.tolist(),'truth_unit_modal_norm_max_abs_error':float(abs(power-1).max()),'no_polarization_selectivity_claim':'oneP_XLIKEincomingstate; no fullJonesoperator'})
    return physical,h2stats,q

def phase_structure(allc,allids,q):
    a,u=unit(allc);rec=a*u;com,rel,idx=gauge(allc);c0,r0,i0=gauge(allc,'fixed0_switch')
    roundtrip={'polar_max_abs':float(abs(rec-allc).max()),'dominant_gauge_max_abs':float(abs(com[...,None,None]*rel-allc).max()),'fixed0_fallback_gauge_max_abs':float(abs(c0[...,None,None]*r0-allc).max()),'zero_coordinates':int((a==0).sum()),'zero_rule':'unitphase1, magnitude0; commonphase1 if all14zero','dominant_spectral_reference_switches':int((idx[:,1:]!=idx[:,:-1]).sum()),'fixed0_to_dominant_fallback_wavelengths':int((i0!=7).sum()),'dominant_reference_histogram':np.bincount(idx.reshape(-1),minlength=14).tolist(),'state_scalar_warning':'14complex perlambda, never scalarperorder','validity':'invertibleonly; commonphase must still be predicted. Adaptivegauge usesfullstate (availabletruthfortransform), not a heldouttruth predictionrule.'}
    # Power-orthonormal basis is reversible but changes loss weighting, not H1.
    b=np.sqrt(q)*allc;back=b/np.sqrt(q)
    dec=h1.load_h2_decoder();p=np.array([GLOBALS['by'][cid].p_scale for cid in allids]);h0=h1.reconstruct_h2(allc,p,dec);hback=h1.reconstruct_h2(back,p,dec)
    roundtrip.update(power_basis_max_abs=float(abs(back-allc).max()),power_basis_unit_Euclidean_norm_max_abs=float(abs((abs(b)**2).sum((2,3))-1).max()),H2_roundtrip_eta_max_abs=float(abs(h0['eta']-hback['eta']).max()),H2_roundtrip_absolute_max_abs=float(abs(h0['absolute_order']-hback['absolute_order']).max()))
    req(max(roundtrip[k] for k in ['polar_max_abs','dominant_gauge_max_abs','fixed0_fallback_gauge_max_abs','power_basis_max_abs','H2_roundtrip_eta_max_abs','H2_roundtrip_absolute_max_abs'])<1e-12,'representation_roundtrip_or_H2_parity')
    mask=(a*a)/(a*a).sum((2,3),keepdims=True)>=1e-4;valid=mask[:,1:]&mask[:,:-1];angle=np.angle(allc);raw=np.diff(angle,axis=1);wrapped=np.angle(allc[:,1:]*allc[:,:-1].conj());ww=a[:,1:]*a[:,:-1]*valid
    denom=ww.sum((1,2,3));r=np.sqrt((ww*wrapped**2).sum((1,2,3))/denom)
    nearzero=((a*a)/(a*a).sum((2,3),keepdims=True)<1e-4);changes=(nearzero[:,1:]!=nearzero[:,:-1]).sum()
    spectral={'raw_2pi_wrap_count_significant':int(((abs(raw)>np.pi)&valid).sum()),'significant_adjacent_pairs':int(valid.sum()),'principal_phase_step_weighted_RMSE_rad_per_nm':summary(r),'max_significant_principal_phase_step_rad':float(np.max(abs(wrapped[valid]))),'fraction_significant_steps_gt_pi_over2':float(((abs(wrapped)>np.pi/2)&valid).sum()/valid.sum()),'amplitude_significance_crossing_count':int(changes),'largest_phase_steps':[],'wrapping_note':'principal adjacentphase is invariant to2piwrapping; truevariation remains. Unwraponlywithincontiguoussignificantsegments; an actualnearzero crossing cannotbevalidatedfrom1nmsamplesalone.'}
    indices=np.argwhere(valid)
    for flat in np.argsort(abs(wrapped[valid]))[-20:][::-1]:
        i,w,m,pol=indices[flat];spectral['largest_phase_steps'].append({'case_id':allids[i],'lambda_pair':[int(440+w),int(441+w)],'m':int(m-3),'pol':['TE','TM'][pol],'principal_delta_rad':float(wrapped[i,w,m,pol]),'raw_delta_rad':float(raw[i,w,m,pol]),'coordinate_power_fraction_low':float(a[i,w,m,pol]**2/(a[i,w]**2).sum()),'coordinate_power_fraction_high':float(a[i,w+1,m,pol]**2/(a[i,w+1]**2).sum())})
    # Mean/covariance/descriptive rank are not fitted prediction preprocessing.
    z=allc.reshape(156,-1);cart=np.stack([z.real,z.imag],-1).reshape(156,-1);absx=abs(z);phasor=u.reshape(156,-1)
    structure={'Cart_ReIm_global_sample_variance':float(np.var(cart,axis=0).sum()),'amplitude_global_sample_variance':float(np.var(absx,axis=0).sum()),'phase_unitcomplex_circular_coherence_truthweighted':float(abs(np.sum((a*a)*u))/np.sum(a*a)),'common_dominant_unitphase_resultant':float(abs(com.mean())),'common_fixed0_unitphase_resultant':float(abs(c0.mean())),'common_spectral_phase_step':summary(abs(np.angle(com[:,1:]*com[:,:-1].conj()))),'relative_phase_retained':True,'global_statistical_scope':'all156descriptive only; no learnedPCA/scaler/basis usedinheldout path','ReIm_vs_sincos':'sincos solveswrapping but cannotrestoreunknownphysicalphase; commonphase/relativephase changes must preservefullabsolutephase','dominant_phase_rule':'referenceindex=maxAperlambda, deterministicargmaxfirsttie; reportedreference switchescancreate apparentcommon/relative discontinuity'}
    coordinate_coherence=abs(np.sum(a*a*u,axis=0))/np.sum(a*a,axis=0)
    structure['per_coordinate_geometry_phase_coherence']=coordinate_coherence.tolist()
    structure['per_coordinate_coherence_summary']=summary(coordinate_coherence)
    structure['pooled_phase_coherence_caveat']='pooled cross-mode/wavelength phasor statistic is descriptive only; per-coordinate coherence measures across geometries'
    # Fixed mode basis signs and reference shifts are diagonal unitary transforms.
    k0=2*np.pi/(np.arange(440,461)*1e-9);kz=np.array([[dec._mode(m,0,float(w),1.,1,'TM')['kz_rad_m'].real for m in range(-3,4)] for w in range(440,461)])
    rotation=np.exp(1j*kz[:,:,None]*100e-9);fixed=allc*rotation;back2=fixed*rotation.conj()
    structure['fixed_reference_shift_math_only']={'delta_z_nm':100,'inverse_max_abs':float(abs(back2-allc).max()),'KRR_unitary_equivariance':'sharedRMS/channelmean plus scalarlinear kernel: rotatingalltrainingtargets rotatespredictions exactly (operatorlinearity); originalEuclideanstateSSE/H2power invariant. Thus fixedreferencephasechoice alone cannot improve thisuncompressedKRR. No newphysicalfieldplane or independentvalidation.','MLP_note':'no claim samefiniteoptimizationtrajectory underrotatedoutputs'}
    put('PHASE_REPRESENTATION_DIAGNOSTIC.json',{'roundtrip':roundtrip,'spectral':spectral,'representation_structure':structure,'original_reference_unchanged':True})
    return roundtrip,spectral,structure

GLOBALS={}
def pair_metrics(c1,c2,p1,p2,e1,e2):
    sq1=abs(c1)**2;sq2=abs(c2)**2;den=.5*(sq1.sum((1,2,3))+sq2.sum((1,2,3)))
    am,ph,err,d=error_decomposition(c1,c2)
    frac1=sq1/sq1.sum((2,3),keepdims=True);frac2=sq2/sq2.sum((2,3),keepdims=True);ww=abs(c1)*abs(c2)*(frac1>=1e-4)*(frac2>=1e-4);wd=ww.sum((1,2,3))
    return {'state_distance':np.sqrt(err.sum((1,2,3))/den),'amplitude_distance':np.sqrt(am.sum((1,2,3))/den),'phase_component_distance':np.sqrt(ph.sum((1,2,3))/den),'weighted_phase_RMSE':np.sqrt(np.divide((ww*d*d).sum((1,2,3)),wd,out=np.full(len(c1),np.nan),where=wd>0)),'routing_RMSE':np.sqrt(np.mean((e1-e2)**2,(1,2))),'P_scale_symmetric_relative_RMSE':np.sqrt(np.mean((2*(p1-p2)/(p1+p2))**2,1))}

def geometry_analysis(col,ct,preds,ids):
    by=GLOBALS['by'];allids=[c.case_id for c in col.cases];meta={q['case_id']:q for q in A.inventory()['cases']};x=np.array([c.ordered_D_nm for c in col.cases],float);c=np.array([cc.c_hat for cc in col.cases]);p=np.array([cc.p_scale for cc in col.cases]);eta=np.array([cc.eta for cc in col.cases]);ii,jj=np.triu_indices(156,1);dist=np.linalg.norm((x[ii]-x[jj])/130,axis=1);metrics=pair_metrics(c[ii],c[jj],p[ii],p[jj],eta[ii],eta[jj])
    with np.load(NP.OUT/'NP88_FEATURES.npz',allow_pickle=False) as z:fb=dict(zip(z['case_ids'].tolist(),z['features']))
    f=np.array([fb[cid] for cid in allids]);std=f.std(0);zf=(f-f.mean(0))/np.where(std==0,1,std);npdist=np.linalg.norm((zf[ii]-zf[jj])*np.sqrt(6/88),axis=1)
    rows=[{'case_i':allids[i],'case_j':allids[j],'role_i':by[allids[i]].role,'role_j':by[allids[j]].role,'stratum_i':meta[allids[i]]['stratum'],'stratum_j':meta[allids[j]]['stratum'],'geometry_distance':float(dist[k]),'NP_distance_descriptive_all156_only':float(npdist[k]),**{n:(float(v[k]) if np.isfinite(v[k]) else None) for n,v in metrics.items()}} for k,(i,j) in enumerate(zip(ii,jj))]
    with (OUT/'ALL_GEOMETRY_PAIRS.csv').open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    groups={}
    for name,keep in [('all156',np.ones(len(ii),bool)),('global113_only',np.array([by[allids[i]].role==C.ROLE_GLOBAL_DEV and by[allids[j]].role==C.ROLE_GLOBAL_DEV for i,j in zip(ii,jj)]))]:
        groups[name]={'count':int(keep.sum()),'geometry_distance':summary(dist[keep]),'response_metrics':{n:summary(v[keep]) for n,v in metrics.items()},'geometry_vs_response_correlations':{n:corr(dist[keep],v[keep]) for n,v in metrics.items()},'NPdistance_vs_response_correlations':{n:corr(npdist[keep],v[keep]) for n,v in metrics.items()},'bins':[]}
        for low,high in zip([0,.1,.25,.5,1],[.1,.25,.5,1,3]):
            mask=keep&(dist>low)&(dist<=high);groups[name]['bins'].append({'distance_range':[low,high],'count':int(mask.sum()),'response':{n:summary(v[mask]) for n,v in metrics.items()}})
    strata={}
    for st in sorted(set(meta[cid]['stratum'] for cid in allids)):
        keep=np.array([meta[allids[i]]['stratum']==st and meta[allids[j]]['stratum']==st for i,j in zip(ii,jj)]);strata[st]={'pair_count':int(keep.sum()),'response':{n:summary(v[keep]) for n,v in metrics.items()},'distance':summary(dist[keep])}
    anchor=by['K6V1_S31'];req(anchor.ordered_D_nm==(220,195,210,150,140,210),'S31_identity_conflict');local=[];axis={}
    for case in col.cases:
        if case.role!=C.ROLE_LOCAL_AXIS:continue
        delta=np.array(case.ordered_D_nm)-np.array(anchor.ordered_D_nm);req(np.count_nonzero(delta)==1 and np.max(abs(delta))==5,'local_axis_geometry')
        dim=int(np.flatnonzero(delta)[0]);sign=int(np.sign(delta[dim]));m=pair_metrics(anchor.c_hat[None],case.c_hat[None],anchor.p_scale[None],case.p_scale[None],anchor.eta[None],case.eta[None]);row={'case_id':case.case_id,'D_coordinate':dim+1,'signed_delta_nm':5*sign,'geometry_distance':5/130,**{k:float(v[0]) for k,v in m.items()}};local.append(row);axis[(dim,sign)]=case
    curvature=[]
    for dim in range(6):
        if (dim,-1) not in axis or (dim,1) not in axis:curvature.append({'D_coordinate':dim+1,'two_sided_available':False,'central_difference':None});continue
        lo=axis[(dim,-1)].c_hat;hi=axis[(dim,1)].c_hat;deriv=(hi-lo)/10;second=(hi+lo-2*anchor.c_hat)/25
        curvature.append({'D_coordinate':dim+1,'two_sided_available':True,'central_C_change_norm_per_nm':float(np.linalg.norm(deriv)/np.linalg.norm(anchor.c_hat)),'central_second_change_norm_per_nm2':float(np.linalg.norm(second)/np.linalg.norm(anchor.c_hat)),'nonlinearity_over_linear_symmetric_step_ratio':float(np.linalg.norm(hi+lo-2*anchor.c_hat)/np.linalg.norm(hi-lo)),'not_training_jacobian':True})
    # Actual matched outertrain-nearest neighbors, response diagnostics only.
    near={};neighborrows=[];folds=A.build_plan().outer_validation_ids
    baseruns=NP.baseline_runs(col)
    for fold,modeldir,run in baseruns:
        tr=run.task.train_case_ids;va=run.prediction_case_ids;xx=np.array([by[cid].ordered_D_nm for cid in tr]);vx=np.array([by[cid].ordered_D_nm for cid in va]);d=np.linalg.norm((vx[:,None]-xx[None])/130,axis=2);ind=np.argmin(d,1)
        mm=pair_metrics(np.array([by[cid].c_hat for cid in va]),np.array([by[tr[i]].c_hat for i in ind]),np.array([by[cid].p_scale for cid in va]),np.array([by[tr[i]].p_scale for i in ind]),np.array([by[cid].eta for cid in va]),np.array([by[tr[i]].eta for i in ind]))
        for j,cid in enumerate(va):neighborrows.append({'case_id':cid,'fold':fold,'nearest_train_case_id':tr[ind[j]],'geometry_distance':float(d[j,ind[j]]),**{k:float(v[j]) for k,v in mm.items()}})
    nr={q['case_id']:q for q in neighborrows}
    for kind,(cp,pp) in preds.items():
        err=np.linalg.norm((cp-ct).reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)
        near[kind]={k:corr([nr[cid][k] for cid in ids],err) for k in ['geometry_distance','state_distance','amplitude_distance','weighted_phase_RMSE','routing_RMSE','P_scale_symmetric_relative_RMSE']}
    put('GEOMETRY_LOCAL_RESPONSE_REGULARITY.json',{'geometry_scale_authority':pin(A.ROOT/'reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json'),'normalization':'ordered130nmspan','groups':groups,'boundary_strata':strata,'S31_local11':local,'central_finite_difference_diagnostic':curvature,'missing_local_axis':'D6_M05; six-dimensional two-sided learnability unverified','local_scope':'anchor+11:5 completeaxes,D6+only; descriptive response, no numericalrepeatability bound','closest_pairs':sorted(rows,key=lambda q:q['geometry_distance'])[:60],'actual_train_neighbor_rows':neighborrows,'neighbor_response_vs_model_error':near,'no_phase_alignment':True,'pair_statistical_caution':'pairs share geometries; correlations descriptive only; neither wavelength nor pair is independentgeometryreplicate','NP_input_statistic_scope':'all156 feature means/stds are descriptive only; never enter predictedpath'})
    return groups,local,curvature,near

def shrink_analysis(col,ct,preds,ids,q):
    by=GLOBALS['by'];norms={};operators={};baseruns=NP.baseline_runs(col);allf=NP.read('MATCHED_OUTER_FOLD_MANIFEST.json')['folds']
    with np.load(NP.OUT/'NP88_FEATURES.npz',allow_pickle=False) as z:fb=dict(zip(z['case_ids'].tolist(),z['features']))
    for kind,(cp,pp) in preds.items():
        rows=[];op=[]
        for fold,p,base in baseruns:
            tr=base.task.train_case_ids;va=base.prediction_case_ids;ix=np.array([ids.index(cid) for cid in va]);train=np.array([by[cid].c_hat for cid in tr]);mu=train.mean(0);truth=ct[ix];pred=cp[ix];dv=truth-mu;pv=pred-mu
            var_t=float(np.mean(abs(dv)**2));var_p=float(np.mean(abs(pv)**2));center_error=float(np.mean(abs(pv-dv)**2));align=float(np.real(np.vdot(dv,pv))/np.sqrt(np.sum(abs(dv)**2)*np.sum(abs(pv)**2)))
            rows.append({'fold':fold,'prediction_residual_energy_over_target_residual_energy':var_p/var_t,'real_complex_alignment_about_train_mean':align,'train_mean_state_norm_over_mean_true_norm':float(np.linalg.norm(mu)/np.mean(np.linalg.norm(truth.reshape(len(truth),-1),axis=1))),'mean_squared_residual_identity':{'target':var_t,'prediction':var_p,'error':center_error,'twice_real_cross_mean':float(2*np.real(np.mean(pv*np.conj(dv))))},'prediction_geometry_variance_over_truth_variance':float(np.var(pred,axis=0).sum()/np.var(truth,axis=0).sum())})
            if kind not in ['KRR','NP88']:continue
            if kind=='KRR':
                xt=base.x_scaler.transform(np.array([by[cid].ordered_D_nm for cid in tr],float));xv=base.x_scaler.transform(np.array([by[cid].ordered_D_nm for cid in va],float));gamma=base.model.gamma;alpha=base.model.ridge_alpha
            else:
                saved=joblib.load(NP.OUT/'models'/f'NP88_outer_{fold}'/'model.joblib');xt=saved['input_scaler'].transform(np.array([by[cid].ordered_D_nm for cid in tr],float),np.array([fb[cid] for cid in tr]));xv=saved['input_scaler'].transform(np.array([by[cid].ordered_D_nm for cid in va],float),np.array([fb[cid] for cid in va]));gamma=base.model.gamma;alpha=base.model.ridge_alpha
            k=rbf_kernel(xt,gamma=gamma);kv=rbf_kernel(xv,xt,gamma=gamma)
            weights=np.linalg.solve(k+alpha*np.eye(124),kv.T).T # fixed kernel influence operator, no target fit
            centered=train-mu;calculated=mu+np.einsum('ij,jwop->iwop',weights,centered);req(np.max(abs(calculated-pred))<1e-12,'saved_KRR_influence_operator_parity')
            num=np.linalg.norm((calculated-mu).reshape(len(va),-1),axis=1);den=abs(weights)@np.linalg.norm(centered.reshape(124,-1),axis=1);coherence=num/den
            op.append({'fold':fold,'operator_prediction_max_abs_error':float(np.max(abs(calculated-pred))),'weight_sum':summary(weights.sum(1)),'negative_weight_abs_fraction':summary(np.sum(abs(weights)*(weights<0),1)/np.sum(abs(weights),1)),'absolute_weight_effective_neighbors':summary(np.sum(abs(weights),1)**2/np.sum(weights**2,1)),'weighted_centered_vector_coherence':summary(coherence),'average_max_kernel_similarity':float(kv.max(1).mean()),'operator_only_no_fit':'solvedfixedkernel influence weights usingtraininputs only; no targetcoefficientfit orhyperparameterselection','not_convex_average':'signedridgeweights; coherence quantifies vectorcancellation but not uniquephysicalcausality'})
        norms[kind]={'folds':rows,'state_norm_ratio':summary(np.linalg.norm(cp.reshape(len(ids),-1),axis=1)/np.linalg.norm(ct.reshape(len(ids),-1),axis=1)),'raw_power_metric_norm_squared':summary((abs(cp)**2*q).sum((2,3)))};operators[kind]=op
    train=A.read(A.OUT/'TRAIN_VS_HELDOUT_DIAGNOSTIC.json');summaries={}
    for kind in ['RBF_KRR','CARTESIAN_MLP']:
        summaries[kind]={}
        for n in [32,64,124]:
            rr=[r for r in train['fits'] if r['task']['phase']=='learning_curve' and r['task']['model_kind']==kind and r['task']['training_geometry_count']==n]
            summaries[kind][str(n)]={'fits':len(rr),'train_state_medians':summary([r['train_state_relative_RMSE']['median'] for r in rr]),'train_norm_ratio_medians':summary([r['train_state_norm_ratio']['median'] for r in rr]),'normalized_training_loss':summary([r['normalized_training_loss'] for r in rr]),'refit_updates':summary([r['actual_updates'] for r in rr]),'same_config_selected_once_perouter_notperN':True}
    mmanifest=[]
    for p in (A.OUT/'models/inner').glob('*/fit_manifest.json'):
        d=A.read(p)
        if d['task']['model_kind']=='CARTESIAN_MLP':mmanifest.append({'task_id':d['task']['task_id'],'actual_updates':d['actual_updates'],'best_update':d['best_update']})
    mlp={'saved_inner_fits':len(mmanifest),'best_update':summary([d['best_update'] for d in mmanifest]),'actual_updates':summary([d['actual_updates'] for d in mmanifest]),'best_below100':sum(d['best_update']<100 for d in mmanifest),'best_below200':sum(d['best_update']<200 for d in mmanifest),'full_update_limit_reached':sum(d['actual_updates']==1000 for d in mmanifest),'no_new_training':True}
    put('STATE_NORM_COLLAPSE_ANALYSIS.json',{'models':norms,'fixed_kernel_influence_analysis':operators,'train_vs_heldout_existing_logs':summaries,'MLP_existing_inner_checkpoint_selection':mlp,'normalization_warning':'C_hat is weightedunitnorm, not unconstrainedamplitude. Regularizedconditionalmean naturally contracts with unresolvedphase; splitA/phase losses maytradebiasedradius forangularerror. No renormalization applied to officialpredictions.','counterexample':'all-zero prediction hasstateRMSE1; low outputnorm doesnotalone proveconstantfunction or brokentraining.'})
    return norms,operators,summaries,mlp

def physical_contract(col,q):
    dec=h1.load_h2_decoder();h1.load_h1_authority();rows=[]
    # Read-only basis evidence; airfixedbycontract independentofD.
    for m in range(-3,4):
        mm=dec._mode(m,0,450.,1.,1,'TM');ee=dec._mode(m,0,450.,1.,1,'TE');rows.append({'m':m,'TM_e_hat_real':mm['e_hat'].real.tolist(),'TE_e_hat_real':ee['e_hat'].real.tolist(),'kz_rad_m':float(mm['kz_rad_m'].real),'propagating':mm['propagating']})
    source=A.ROOT/'scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py';ing=A.ROOT/'scripts/coupling_ml/k6_v2_pipeline/ingest.py'
    lines=source.read_text(encoding='utf-8').splitlines();ilines=ing.read_text(encoding='utf-8').splitlines();evidence=[]
    for file,ll,tokens in [(source,lines,['s_hat =','p_hat =','factor = np.exp','gauge =','scale =','sampled[component_index] =','modal, _, rank','wx, wy =']),(ing,ilines,['den=np.sum','chat=coeff','p_scale=','p_scale ='])]:
        evidence.extend({'file':str(file),'line':i+1,'text':l.strip()} for i,l in enumerate(ll) if any(t in l for t in tokens))
    two=A.read(A.ROOT/'reports/coupling/COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1/EXT02_TWO_AIR_PLANES_EVALUATION_V2.json')
    put('PHYSICAL_CONTRACT_CONSISTENCY_AUDIT.json',{'status':'NO_CONTRACT_CONFLICT_FOUND','scope':'156label/provenance verified bySHA-gatedloader; sourceaudit, noFSPload/solver','state':'ordered21x7x2 +z TE/TM afterinputgauge; noJonesoperator','reference':'POSTNP1722nm; actualsamplecoordinates useddeembed; IN-50nm sourceTM gauge reusedalloutputs','phase_deembed':'dz=zref-zsample; +z exp(+ikz dz), -z exp(-ikz dz)','extraction':'actualcoordinates fullperiodsixE/H Fourier trapezoid endpoints halfweight; sixfield/4channel complexLS ±zTE/TM; notpointfield','C_hat':'C_PW / sqrt(sum_(7orders,TE/TM) kz/k0*|C_PW|²); positive scalar only, phasepreserved. Weightednormunit1. P_scale separatelyfromsource-normalizedPOSTNP E/H Poynting. Not generally C_PW/sqrt(P_scale).','H2':'routing proportional modal |C_hat|²; no phasecross terms; absolute=eta*predictedP_scale, total=predictedP_scale','basis_450nm':rows,'basis_effect':'negativekx modes TEandTM sign differsfromm0/+kx; fixedbyorder, notgeometry. Diagonalunitarybasis correction is invertible but cannotimproveuncompressedKRR under matchedscalaroperator/sharedRMS; no basislabels changed.','source_evidence':evidence,'single_EXT02_crossheight':'allfrozenconsistencythresholdsmet; propagatingL2max0.0077824, phaseRMSEmax0.0064994rad. Noabsoluteconvergence/globalproof/controlledcrossrunrepeatability. Older monitor reportmissingsecondplane supersededbyV2savedcomparison.','remaining_uncertainty':['actualmeshtransition/PMLreadbacks missinginEXT02diagnostic','no controlledcrossrunrepeatability bound forlocal+/-5nm','one-plane/percase provenance auditdoesnotproveglobalphysicalconvergence'],'original_truth_H1_H2_unchanged':True})

def main():
    if not(OUT/'INPUT_PINS.json').exists():freeze()
    req(A.sha(Path(__file__))==A.read(OUT/'INPUT_PINS.json')['source_code_sha256'],'audit_source_changed')
    col=A.load_collection(False);by={c.case_id:c for c in col.cases};GLOBALS['by']=by
    predictions={};ids=None
    for name,path in [('KRR',A.OUT/'RBF_KRR_n124_OOF_PREDICTIONS.npz'),('MLP',A.OUT/'CARTESIAN_MLP_n124_OOF_PREDICTIONS.npz'),('NP88',NP.OUT/'B_OOF_PREDICTIONS.npz')]:
        with np.load(path,allow_pickle=False) as z:
            zi=z['case_ids'].tolist();req(ids is None or zi==ids,'matchedOOFidentity');ids=zi;c=z['C_hat_real']+1j*z['C_hat_imag'];p=z['P_scale'];c=c.mean(0) if c.ndim==5 else c;p=p.mean(0) if p.ndim==3 else p;predictions[name]=(c,p)
    req(len(ids)==124 and not any(by[c].role not in C.DEVELOPMENT_ROLES for c in ids),'developmentonly')
    ct=np.array([by[c].c_hat for c in ids]);allids=[c.case_id for c in col.cases];allc=np.array([c.c_hat for c in col.cases])
    decomp,oracle=decompose_models(ct,predictions,ids);energy,relations,q=modal_energy(allc,ct,predictions,ids);roundtrip,spectral,phase=phase_structure(allc,allids,q);groups,local,curvature,near=geometry_analysis(col,ct,predictions,ids);norms,ops,train,mlp=shrink_analysis(col,ct,predictions,ids,q);physical_contract(col,q)
    put('KRR_MLP_NP88_FAILURE_COMPARISON.json',{'models':{name:{'amplitude_fraction':d['pooled_amplitude_SSE_fraction'],'phase_fraction':d['pooled_phase_SSE_fraction'],'state_norm':norms[name]['state_norm_ratio'],'oracle_common_perlambda_SSE_fraction_explained':oracle[name]['common_perlambda_SSE_explained_fraction'],'phase_routing_Pscale_relationship':relations[name],'local_neighbor_error_correlation':near[name]} for name,d in decomp.items()},'observed':['amplitude/phaseSSEexactdecomposition','truthweightedunitnorm and undernormpredictions','signedKRRinfluenceoperator/reloadparity','MLPtrainingandselectedcheckpointlogs','NPdescriptorcorrelations and negative matchedpilot'],'supported_hypothesis':['unresolvedphysicalphase and samplevariance causeconditionalmeanvectorcancellation','sparse six-dimensionalcoverage limitsfullstateinterpolation','MLPfixedprotocol/earlyselectedupdates can constrainstatefit','NPpowerfeaturemetric does not necessarilytrackHFphase, changeskernelneighborweights'],'unresolved':['uniquecausalroot ofMLPplateau','whetherstructuredphasecandidategeneralizes','controllednumericalrepeatability for±5nm response','whetherdifferentlegalNPkernelweight wouldhelp; nottested'],'no_new_fits':True})
    brief={'decomposition':{k:{'amplitude':v['pooled_amplitude_SSE_fraction'],'phase':v['pooled_phase_SSE_fraction'],'order':v['by_order_SSE_fraction'],'weak':v['field_strength_bins'],'angular':v['angular_threshold_sensitivity'][2]} for k,v in decomp.items()},'energy':energy,'oracle':{k:{'common_lambda':v['common_perlambda_SSE_explained_fraction'],'common_geometry':v['common_onegeom_SSE_explained_fraction'],'table':{n:d['state_relative_RMSE'] for n,d in v['diagnostics'].items()}} for k,v in oracle.items()},'roundtrip':roundtrip,'spectral':spectral,'local':local,'curvature':curvature,'neighbors':{k:v['bins'] for k,v in groups.items()},'norms':norms,'operator':ops,'train':train,'MLPearlystop':mlp}
    put('RESULT_SUMMARY_FOR_SCIENTIFIC_REVIEW.json',brief)
    print('SCIENCE_SUMMARY',json.dumps(brief),flush=True)
    pins=A.read(OUT/'INPUT_PINS.json')
    for p in pins['files']:req(A.sha(p['path'])==p['sha256'],'source_changed_aftermath:'+p['path'])
    put('ZERO_EXECUTION_AND_ISOLATION_AUDIT.json',{'status':'PASS','FDTD':0,'replay':0,'CPU_model_fits':0,'P_scale_fits':0,'NP_MDC_retraining':0,'confirmation_response_access':0,'all_original_input_model_prediction_SHA_unchanged':True,'mathematical_kernel_operator_solve':'diagnosticinfluenceonly,nottargetfit','oracle_not_H1':True,'model_candidate_execution':0})
    (OUT/'CONTINUATION.md').write_bytes((f'# {TASK}\nMathematicalauditcomplete, reportcompilationpending. Read INPUT_PINS, DIAGNOSTIC_PROTOCOL, RESULT_SUMMARY_FOR_SCIENTIFIC_REVIEW, ZERO_EXECUTION_AND_ISOLATION_AUDIT. Alloriginal156G268fit/NP88resultsunchanged.0fit/solver/replay/confirmation; no newMLauthorized. Sourceworktree {A.ROOT}, hostDESKTOP-NNE313K/dell, PythonN:\\anaconda_envs\\RCP_LCP\\python.exe. OracleoutputsstrictdiagnosticnotH1.\n').encode())

if __name__=='__main__':main()
