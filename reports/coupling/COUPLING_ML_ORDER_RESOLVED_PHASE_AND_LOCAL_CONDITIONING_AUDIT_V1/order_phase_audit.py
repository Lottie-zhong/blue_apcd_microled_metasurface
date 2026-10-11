"""Read-only predictions and zero-fit phase diagnostics; no estimator fitting."""
from pathlib import Path
import sys,json,hashlib,datetime,subprocess,csv
import numpy as np
import joblib
from scipy.stats import spearmanr,pearsonr
from k6_v2_pipeline.amended156 import adapter as A,evaluation as V
from k6_v2_pipeline import h1,contracts as C
ROOT=A.ROOT
TASK='COUPLING_ML_ORDER_RESOLVED_PHASE_AND_LOCAL_CONDITIONING_AUDIT_V1'
OUT=ROOT/'reports/coupling'/TASK
OLD=ROOT/'reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1'
sys.path.insert(0,str(OLD))
import structured_phase_pilot as S
D=S.D
def req(x,m):
    if not x:raise ValueError(m)
def put(n,d):A.write(OUT/n,d)
def stats(x):
    x=np.asarray(x).reshape(-1);x=x[np.isfinite(x)]
    return {'count':len(x),**V.summary(x)} if len(x) else {'count':0,'median':None,'q95':None,'worst':None,'mean':None}
def corr(x,y):
    x=np.asarray(x).reshape(-1);y=np.asarray(y).reshape(-1);k=np.isfinite(x)&np.isfinite(y);x=x[k];y=y[k]
    if len(x)<3 or np.std(x)==0 or np.std(y)==0:return {'n':len(x),'Pearson':None,'Spearman':None}
    return {'n':len(x),'Pearson':float(pearsonr(x,y).statistic),'Spearman':float(spearmanr(x,y).statistic),'interpretation':'descriptive association, not calibrated uncertainty or causation; coordinates/pairs correlated'}
def disk(v):return v/np.maximum(1.,abs(v))
def frac(c):
    e=abs(c)**2;return e/e.sum((-2,-1),keepdims=True)
def wrms(delta,w,axes=None):
    num=(delta**2*w).sum(axis=axes);den=w.sum(axis=axes)
    return np.sqrt(np.divide(num,den,out=np.full(np.shape(num),np.nan),where=den>0))
def fixed_gauge(c):
    a,u=D.unit(c);com=u[...,3,1];return a,com,u*com.conj()[...,None,None]
def spectral_encode(c):
    a,u=D.unit(c);return a,u[:,0],u[:,1:]*u[:,:-1].conj()
def synthetic():
    rng=np.random.default_rng(731560);z=rng.normal(size=(3,21,7,2))+1j*rng.normal(size=(3,21,7,2));z[0,:,3,1]=0;z[1,8,4,1]=1e-30;z[2,0]=0
    a,common,relative=fixed_gauge(z);req(abs(a*common[...,None,None]*relative-z).max()<2e-15,'fixed gauge roundtrip')
    for ref in ['dominant','fixed0_switch']:
        com,rel,idx=D.gauge(z,ref);req(abs(com[...,None,None]*rel-z).max()<2e-15,'switched roundtrip')
    aa,first,steps=spectral_encode(z);u=np.concatenate([first[:,None],first[:,None]*np.cumprod(steps,axis=1)],axis=1)
    req(abs(aa*u-z).max()<1e-14,'spectral roundtrip zero crossing')
    v=np.array([0,1e-30,.3+.4j,2j,1+0j]);q=disk(v)
    req(abs(q).max()<=1 and q[0]==0 and q[2]==v[2] and q[3]==1j,'disk bound')
    req(np.allclose(np.angle(q[1:]),np.angle(v[1:]),atol=1e-15),'disk direction unchanged')
    req(abs(np.angle(np.exp(1j*((-np.pi+.001)-(np.pi-.001))))-.002)<1e-12,'wrapping')
    am,ph,e,dt=D.error_decomposition(z,z*.7*np.exp(.8j));req(abs(e-am-ph).max()<2e-14,'SSE identity')
    dec=h1.load_h2_decoder();p=np.ones((3,21));hz=z.copy();hz[2,0,0,1]=1
    rejected=False
    try:h1.reconstruct_h2(z,p,dec)
    except ValueError as exc:rejected=str(exc)=='h2_modal_total_invalid'
    req(rejected,'H2 must reject zero-energy wavelength')
    base=h1.reconstruct_h2(hz,p,dec);rot=h1.reconstruct_h2(hz*np.exp(.7j),p,dec)
    req(abs(base['eta']-rot['eta']).max()<1e-12,'H2 phase preservation')
    zz=hz.copy();zz[:,:,4]*=.2;modified=h1.reconstruct_h2(zz,p,dec);req(abs(base['eta']-modified['eta']).max()>1e-3,'disk can change routing')
    req(np.array_equal(modified['total_power'],base['total_power']),'total is independent Pscale')
    source=Path(__file__).read_text();import ast
    calls=[n.func.attr for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
    req('fit' not in calls,'unexpected fit invocation')
    return {'status':'PASS','check_count':12,'fits':0,'raw_roundtrip_max':float(abs(a*common[...,None,None]*relative-z).max()),'checks':['fixed gauge throughzero','dominant/switch gauge','spectral phase increments throughzero','disk bounded includingtiny','unchanged nonzero phase direction','2pi wrapping','amplitude-phase identity','H2 rejects zero-energy wavelength','H2 phase-only invariance','radius change routing','same independent totalpower','AST no fit call']}
def prepare():
    OUT.mkdir(parents=True,exist_ok=True);req(not (OUT/'DIAGNOSTIC_PROTOCOL.json').exists(),'do not refreeze')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();req(head=='2f798d8d9393cfba346829b1ced50558d1f270e2','authority HEAD conflict')
    pins={}
    for base in [OLD,S.AUDIT,A.OUT,S.NP.OUT]:
        inv=base/'SHA_INVENTORY.json'
        for f in A.read(inv)['files']:
            req(A.sha(f['path'])==f['sha256'],'source SHA:'+f['path']);pins[f['path']]=f['sha256']
        pins[str(inv)]=A.sha(inv)
    pins[str(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json')]=A.INVENTORY_SHA
    req(A.sha(A.CLOSURE/'DEVELOPMENT_156G_DATASET_INVENTORY.json')==A.INVENTORY_SHA,'dataset inventory')
    put('DIAGNOSTIC_PROTOCOL.json',{'task':TASK,'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_HEAD':head,'code_sha256':A.sha(Path(__file__)),'disk_rule':'v/max(1,abs(v)); raw zero stayszero. No fallback direction needed forzero; any allzero wavelength would fail H2 and be reported, not repaired.','comparison':'Cartesian saved / formal unit-circle / ONE raw-unit-disk retrospective diagnostic. Same frozen amplitude head andphysicalP_scale; disk effective amplitude A*min(rho,1) explicitly changes powers. No thresholds/exponents searched.','weak_threshold':1e-4,'threshold_sensitivity':[1e-6,1e-5,1e-4,1e-3,1e-2],'rho_bins':[0,.1,.25,.5,.75,1,2],'geometry_scale_nm':130,'neighbors':'nearest geometry by normalizedEuclideanD; ties lexicographic caseID; no response selection. Allpairs descriptive only.','gauges':'fixedm0TM; truthdominant math only; fixed/common + relative; sameorderTM reference; spectralfirstphase+unitincrements. Rawzero phase unit1, retain full amplitude. No truthreference inference.','fit_counters':{'CPU':0,'P_scale':0,'FDTD':0,'replay':0,'confirmation_response_access':0},'foreign_index_sha':hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest(),'protected_files':[{'path':p,'sha256':s} for p,s in sorted(pins.items())]})
    put('MATHEMATICAL_TESTS.json',synthetic());print('PREREGISTERED_ZERO_FIT',len(pins),flush=True)
def check():
    prot=A.read(OUT/'DIAGNOSTIC_PROTOCOL.json');req(A.sha(Path(__file__))==prot['code_sha256'],'audit code changed')
    for f in prot['protected_files']:req(A.sha(f['path'])==f['sha256'],'protected changed:'+f['path'])
    return prot
def run():
    prot=check();col=A.load_collection(False);by={c.case_id:c for c in col.cases};meta={r['case_id']:r for r in A.inventory()['cases']};folds=A.read(OLD/'FOUR_FOLD_MATCHING_AND_SHA.json')['folds']
    ids=sum([f['heldout_case_ids'] for f in folds],[]);ct=np.array([by[i].c_hat for i in ids]);pt=np.array([by[i].p_scale for i in ids]);eta=np.array([by[i].eta for i in ids]);absolute=np.array([by[i].absolute_order for i in ids])
    with np.load(OLD/'A_OOF_PREDICTIONS.npz',allow_pickle=False) as z:
        req(z['case_ids'].tolist()==ids,'A IDs');ca=z['C_hat_real']+1j*z['C_hat_imag'];pp=z['P_scale'].copy()
    vectors=[];amps=[];bs=[];reload=[]
    for f in folds:
        p=OLD/'models'/f['task_id'];payload=joblib.load(p/'model.joblib');x=np.array([by[i].ordered_D_nm for i in f['heldout_case_ids']],float);xb=payload['input_scaler'].transform(x)
        amp=S.inverse(payload['amplitude_model'].predict(xb),payload['amplitude_scaler']);phase=S.inverse(payload['phase_model'].predict(xb),payload['phase_scaler']);cb,info=S.reconstruct(amp,phase,payload['fallback'])
        xy=phase.reshape(-1,21,7,2,2);v=xy[...,0]+1j*xy[...,1]
        with np.load(p/'predictions.npz',allow_pickle=False) as z:
            req(z['case_ids'].tolist()==f['heldout_case_ids'],'B IDs');req(np.array_equal(cb,z['C_hat_real']+1j*z['C_hat_imag']),'unit reconstruction exact');req(np.array_equal(abs(v),z['phase_vector_norm']),'rho exact');ix=[ids.index(i) for i in f['heldout_case_ids']];req(np.array_equal(pp[ix],z['P_scale']),'Pscale exact')
        req(not info['fallback_mask'].any() and not info['negative_sqrt_mask'].any(),'previous prediction exceptions');vectors.append(v);amps.append(info['amplitude']);bs.append(cb);reload.append({'fold':f['fold'],'exact_C_hat':True,'exact_rho':True,'exact_P_scale':True,'model_sha':A.sha(p/'model.joblib'),'source_prediction_sha':A.sha(p/'predictions.npz'),'fallbacks':0,'negative_sqrt':0})
    raw=np.concatenate(vectors);amp=np.concatenate(amps);cb=np.concatenate(bs);rho=abs(raw);cd=amp*disk(raw);req(np.isfinite(cd).all(),'disk finite');req(np.all((abs(cd)**2).sum((2,3))>0),'disk zero wavelength fails H2')
    np.savez_compressed(OUT/'RAW_PHASE_RECOVERY.npz',case_ids=np.array(ids),raw_cos=raw.real,raw_sin=raw.imag,rho=rho,amplitude_head=amp)
    np.savez_compressed(OUT/'DISK_DIAGNOSTIC_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=cd.real,C_hat_imag=cd.imag,P_scale=pp)
    dec=h1.load_h2_decoder();reports={};diag={};per={};decomp={}
    for name,cp in [('Cartesian',ca),('Unit',cb),('Disk',cd)]:
        report=h1.evaluate_original_h1(ct,cp,pt,pp,eta,absolute,dec);reports[name]=report;diag[name]=V.diagnostics(ct,cp,ids,meta);am,ph,err,delta=D.error_decomposition(ct,cp);sq=abs(ct)**2;den=sq.sum((1,2,3));angular=D.angular_stats(ct,cp,1e-4)
        per[name]={k:np.array([r[k] for r in report['aggregate']['per_geometry']]) for k in report['aggregate']['per_geometry'][0]}
        per[name].update(amplitude_relative_rmse=np.sqrt(am.sum((1,2,3))/den),absolute_phase_rmse=np.array(angular['per_geometry_absolute']),relative_phase_rmse=np.array(angular['per_geometry_relative']),norm_ratio=np.sqrt((abs(cp)**2).sum((1,2,3))/den))
        decomp[name]={'amplitude_SSE':float(am.sum()),'phase_SSE':float(ph.sum()),'phase_fraction':float(ph.sum()/err.sum()),'order_phase_SSE_fraction':(ph.sum((0,1,3))/err.sum()).tolist(),'order_total_SSE_fraction':(err.sum((0,1,3))/err.sum()).tolist(),'TE_TM_SSE_fraction':(err.sum((0,1,2))/err.sum()).tolist(),'weak_threshold_sensitivity':[D.angular_stats(ct,cp,v) for v in prot['threshold_sensitivity']]}
    original=A.read(OLD/'H1_H2_FINAL_EVALUATION.json');req(reports['Cartesian']==original['A'] and reports['Unit']==original['B'],'formal H1 not reproducedexactly')
    comparisons={}
    for key in per['Unit']:
        rows=[{'case_id':cid,'fold':next(f['fold'] for f in folds if cid in f['heldout_case_ids']),**{name:float(per[name][key][k]) for name in per}} for k,cid in enumerate(ids)]
        dd=per['Disk'][key]-per['Unit'][key];da=per['Disk'][key]-per['Cartesian'][key]
        comparisons[key]={**{name:stats(per[name][key]) for name in per},'Disk_minus_Unit':stats(dd),'Disk_minus_Cartesian':stats(da),'Disk_vs_Unit_wins':int((dd< -1e-12).sum()),'Disk_vs_Cartesian_wins':int((da< -1e-12).sum()),'per_geometry':rows,'per_fold':{str(f['fold']):{'Disk_minus_Unit':stats([dd[ids.index(i)] for i in f['heldout_case_ids']]),'Disk_minus_Cartesian':stats([da[ids.index(i)] for i in f['heldout_case_ids']])} for f in folds}}
    put('RAW_VS_UNIT_CIRCLE_ZERO_FIT_DIAGNOSTIC.json',{'label':'RETROSPECTIVE_ZERO_FIT_DIAGNOSTIC','metrics':comparisons,'H1_gate_attainment_diagnostic_only':reports,'decomposition':decomp,'P_scale_exact':True,'phase_direction_max_difference_rad':float(abs(np.angle(cd*cb.conj())).max()),'unit_vs_disk_pooled_SSE_reduction_fraction':float(1-np.sum(abs(cd-ct)**2)/np.sum(abs(cb-ct)**2)),'nonzero_rho_above1_count':int((rho>1).sum()),'rho_above1_amplitude_power_share':float((amp**2*(rho>1)).sum()/(amp**2).sum()),'amplitude_warning':'Frozen A head is identical but effective disk amplitude changes to A*min(rho,1). Power/routing can change. Direction unchanged; lower complex SSE is not better phase prediction.'})
    oldpaired=A.read(OLD/'PAIRED_CARTESIAN_KRR_COMPARISON.json');put('AMPLITUDE_HEAD_REUSE_AUDIT.json',{'status':'PASS','dimensions':294,'sqrt_nonnegative_prediction':True,'amplitude_nonnegative':bool((amp>=0).all()),'fold_reload':reload,'P_scale_exact':True,'amplitude_wins':oldpaired['amplitude_relative_rmse']['wins'],'routing_wins':oldpaired['routing_eta_rmse']['wins'],'absolute_wins':oldpaired['absolute_order_source_normalized_rmse']['wins'],'no_test_scaling_or_dropped_modes':True,'formal_amplitude_metrics':oldpaired['amplitude_relative_rmse'],'per_order_pol':[{'m':j-3,'pol':['TE','TM'][k],'truth_energy_fraction':float((abs(ct[:,:,j,k])**2).sum()/(abs(ct)**2).sum()),'amplitude_RMSE_A':float(np.sqrt(np.sum((abs(ca[:,:,j,k])-abs(ct[:,:,j,k]))**2)/np.sum(abs(ct[:,:,j,k])**2))),'amplitude_RMSE_Unit':float(np.sqrt(np.sum((amp[:,:,j,k]-abs(ct[:,:,j,k]))**2)/np.sum(abs(ct[:,:,j,k])**2)))} for j in range(7) for k in range(2)],'status_meaning':'Useful DEVELOPMENT amplitude baseline, not complete609D admission'})
    strong=frac(ct)>=1e-4;sq=abs(ct)**2;angle=abs(np.angle(cb*ct.conj()));phase_loss=1-np.cos(angle);stateerr=abs(cb-ct)**2;amperr=(amp-abs(ct))**2
    cr={'strong_rho':stats(rho[strong]),'weak_rho':stats(rho[~strong]),'all_rho':stats(rho),'strong_phase_rmse':wrms(angle[strong],sq[strong]),'per_order':[{'m':j-3,'strong_rho':stats(rho[:,:,j,:][strong[:,:,j,:]]),'weak_rho':stats(rho[:,:,j,:][~strong[:,:,j,:]]),'rho_vs_circular_loss':corr(rho[:,:,j,1][strong[:,:,j,1]],phase_loss[:,:,j,1][strong[:,:,j,1]])} for j in range(7)],'per_wavelength':[{'lambda_nm':440+j,'strong_rho':stats(rho[:,j][strong[:,j]])} for j in range(21)],'bins':[],'interpretation':'rho is length of an unscaled KRR vector, not a probability; greater than1 values can occur; association does not calibrate uncertainty'}
    for lo,hi in zip(prot['rho_bins'][:-1],prot['rho_bins'][1:]):
        mask=strong&(rho>=lo)&(rho<hi);cr['bins'].append({'rho_range':[lo,hi],'n':int(mask.sum()),'truth_energy_fraction':float(sq[mask].sum()/sq.sum()),'truth_weighted_phase_RMSE':float(wrms(angle[mask],sq[mask])) if mask.any() else None,'amplitude_error':stats(amperr[mask]),'state_error':stats(stateerr[mask])})
    rho_geom=np.array([np.average(rho[k][strong[k]],weights=sq[k][strong[k]]) for k in range(124)])
    cr['geometry_correlations']={name:corr(rho_geom,per['Unit'][name]) for name in ['absolute_phase_rmse','relative_phase_rmse','amplitude_relative_rmse','state_relative_rmse']};cr['geometry_rows']=[{'case_id':cid,'weighted_rho':float(rho_geom[k]),**{name:float(per['Unit'][name][k]) for name in ['absolute_phase_rmse','relative_phase_rmse','amplitude_relative_rmse','state_relative_rmse']}} for k,cid in enumerate(ids)]
    cr['strong_coordinate_rho_vs_circular_loss']=corr(rho[strong],phase_loss[strong]);put('CIRCULAR_PHASE_CONFIDENCE_ANALYSIS.json',cr)
    print('RECONSTRUCTION_COMPLETE',json.dumps({k:{n:v[n]['median'] for n in ['Cartesian','Unit','Disk']} for k,v in comparisons.items() if k in ['state_relative_rmse','routing_eta_rmse','absolute_order_source_normalized_rmse','amplitude_relative_rmse']}),flush=True)
    allids=[case.case_id for case in col.cases];cc=np.array([case.c_hat for case in col.cases]);x=np.array([case.ordered_D_nm for case in col.cases],float);sqall=abs(cc)**2;mask=frac(cc)>=1e-4;aa,u=D.unit(cc);tm=u[:,:,:,1];r=u*u[:,:,3,1].conj()[:,:,None,None];tmrel=r[:,:,:,1];com=u[:,:,3,1]
    absolute_step=np.angle(tm[:,1:]*tm[:,:-1].conj());relative_step=np.angle(tmrel[:,1:]*tmrel[:,:-1].conj());keep=mask[:,1:,:,1]&mask[:,:-1,:,1];refkeep=mask[:,1:,3,1]&mask[:,:-1,3,1];w=aa[:,1:,:,1]*aa[:,:-1,:,1]*keep
    structure=[]
    for j in range(7):
        sj=strong[:,:,j,1];ww=sq[:,:,j,1]*sj;dlt=np.angle(cb[:,:,j,1]*ct[:,:,j,1].conj());ss=abs(cb[:,:,j,1]-ct[:,:,j,1])**2
        structure.append({'m':j-3,'truth_energy_fraction':float(sqall[:,:,j,1].sum()/sqall.sum()),'across_geometry_absolute_coherence':stats(abs(np.sum(tm[:,:,j]*sqall[:,:,j,1],axis=0)/np.sum(sqall[:,:,j,1],axis=0))),'across_geometry_relative_coherence':stats(abs(np.sum(tmrel[:,:,j]*sqall[:,:,j,1],axis=0)/np.sum(sqall[:,:,j,1],axis=0))),'absolute_spectral_step_RMSE_rad':float(wrms(absolute_step[:,:,j],w[:,:,j])),'relative_spectral_step_RMSE_rad':float(wrms(relative_step[:,:,j],w[:,:,j]*refkeep)),'unit_phase_error_RMSE_rad':float(wrms(dlt,ww)),'unit_state_SSE_fraction':float(ss.sum()/stateerr.sum()),'principal_step_abs':stats(abs(absolute_step[:,:,j][keep[:,:,j]])),'raw_angle_wraps':int(((abs(np.diff(np.angle(tm[:,:,j]),axis=1))>np.pi)&keep[:,:,j]).sum())})
    pairwise=[]
    for i in range(7):
        for j in range(i+1,7):
            rel=tm[:,:,i]*tm[:,:,j].conj();ww=aa[:,:,i,1]*aa[:,:,j,1]*mask[:,:,i,1]*mask[:,:,j,1];steps=np.angle(rel[:,1:]*rel[:,:-1].conj());weights=np.sqrt(ww[:,1:]*ww[:,:-1]);coh=abs(np.sum(rel*ww,axis=0)/np.sum(ww,axis=0));pairwise.append({'orders':[i-3,j-3],'spectral_step_RMSE':float(wrms(steps,weights)),'geometry_relative_coherence':stats(coh)})
    put('ORDER_RESOLVED_PHASE_STRUCTURE.json',{'physical_reference_nm':1722,'all_geometry_count':156,'TM_orders':structure,'TM_pairwise_relative':pairwise,'TE_true_energy_fraction':float(sqall[:,:,:,0].sum()/sqall.sum()),'TE_warning':'Weak TE not a model selection driver; still retained in full output. Single P_XLIKE input is not a full Jones operator.','per_geometry_spectral':[{'case_id':cid,'absolute_spectral_RMSE':float(wrms(absolute_step[k],w[k])),'m0_relative_spectral_RMSE':float(wrms(relative_step[k],w[k]*refkeep[k,:,None]))} for k,cid in enumerate(allids)],'weak_crossings_by_order':np.logical_xor(mask[:,1:,:,1],mask[:,:-1,:,1]).sum((0,1)).tolist()})
    a0,common,rel=fixed_gauge(cc);rec=a0*common[:,:,None,None]*rel;roundtrip=float(abs(rec-cc).max());a1,first,inc=spectral_encode(cc);recovered=np.concatenate([first[:,None],first[:,None]*np.cumprod(inc,axis=1)],axis=1)*a1
    dom=np.argmax(aa.reshape(156,21,14),axis=-1);pred_dom=np.argmax(amp.reshape(124,21,14),axis=-1);truth_dom=np.argmax(abs(ct).reshape(124,21,14),axis=-1)
    com2,rr2,idx2=D.gauge(cc,'dominant');rg2=float(abs(com2[:,:,None,None]*rr2-cc).max())
    common_pred=D.unit(cb)[1][:,:,3,1];relative_pred=D.unit(cb)[1]*common_pred.conj()[:,:,None,None]
    relerr=np.angle(relative_pred*rel[[allids.index(i) for i in ids]].conj());aw=sq*strong;relw=aw*strong[:,:,3,1][:,:,None,None]
    gauges={'fixed_m0_TM':{'raw_roundtrip_max':roundtrip,'reference_zero_count':int((aa[:,:,3,1]==0).sum()),'reference_weak_count':int((~mask[:,:,3,1]).sum()),'minimum_reference_energy_fraction':float(frac(cc)[:,:,3,1].min()),'legal_inference':'Fixed coordinate identity is known; common phase must be predicted, never read fromHF. Canonicalunit1 at exactzero plus fullrelative coordinates is mathematically reversible. Training support does not guarantee future reference stays strong.'},'dominant_reference':{'raw_roundtrip_max':rg2,'spectral_switch_count':int((np.diff(dom,axis=1)!=0).sum()),'predicted_amplitude_reference_matches_HF_fraction_diagnostic':float((pred_dom==truth_dom).mean()),'legal_inference':'HF argmax unavailable at inference. Truth-selected identity cannot be assumed; predicted-amplitude selection is legal but produces switching/misregistration and requires a separately frozen design; not prioritized.'},'per_order_TM_reference':{'zero_reference_counts_by_order':(aa[:,:,:,1]==0).sum((0,1)).tolist(),'weak_reference_counts_by_order':(~mask[:,:,:,1]).sum((0,1)).tolist(),'legal_inference':'Seven absolute/common order phases still required; TE/TM relative phase cannot remove cross-order phase requirement.'},'spectral_differences':{'raw_roundtrip_max':float(abs(recovered-cc).max()),'legal_inference':'Need21 amplitude arrays, first-wavelength absolute phases for all14coords, and20 unitincrements. Zeroscanonicalunit1; accumulation may amplify prediction error, no trained evidence.'},'common_and_relative_existing_errors':{'m0_TM_common_phase_RMSE':float(wrms(np.angle(common_pred*D.unit(ct)[1][:,:,3,1].conj()),sq[:,:,3,1])),'relative_to_m0_TM_RMSE':float(wrms(relerr,relw))},'production_claim':False}
    req(roundtrip<2e-15 and rg2<2e-15 and abs(recovered-cc).max()<1e-14,'truth math parity');put('RELATIVE_PHASE_REFERENCE_FEASIBILITY.json',gauges)
    dd=np.linalg.norm((x[:,None]-x[None,:])/130,axis=-1);np.fill_diagonal(dd,np.inf);nearest=np.array([min(range(156),key=lambda j:(dd[k,j],allids[j])) for k in range(156)]);ii,jj=np.triu_indices(156,1)
    def pair(i,j):
        delta=np.angle(tm[i]*tm[j].conj());reldelta=np.angle(tmrel[i]*tmrel[j].conj());ww=aa[i,:,:,1]*aa[j,:,:,1]*mask[i,:,:,1]*mask[j,:,:,1];rw=ww*(mask[i,:,3,1]&mask[j,:,3,1])[:,None]
        met=D.pair_metrics(cc[i:i+1],cc[j:j+1],np.array([by[allids[i]].p_scale]),np.array([by[allids[j]].p_scale]),np.array([by[allids[i]].eta]),np.array([by[allids[j]].eta]))
        return {'case_i':allids[i],'case_j':allids[j],'geometry_distance':float(dd[i,j]),**{k:float(v[0]) for k,v in met.items()},'order_absolute_phase_RMSE':[float(wrms(delta[:,k],ww[:,k])) for k in range(7)],'order_relative_phase_RMSE':[float(wrms(reldelta[:,k],rw[:,k])) for k in range(7)],'relative_phase_RMSE':float(wrms(reldelta,rw))}
    nn=[pair(k,j) for k,j in enumerate(nearest)];anchor=allids.index('K6V1_S31');local=[pair(anchor,k) for k in range(156) if by[allids[k]].role==C.ROLE_LOCAL_AXIS]
    for row in local:row['ordered_D_delta_nm']=(x[allids.index(row['case_j'])]-x[anchor]).tolist()
    grouped={}
    for st in sorted(set(meta[i]['stratum'] for i in allids)):
        selected=[q for q in nn if meta[q['case_i']]['stratum']==st];grouped[st]={'n':len(selected),'nearest_distance':stats([q['geometry_distance'] for q in selected]),'nearest_absolute_phase_RMSE':stats([q['weighted_phase_RMSE'] for q in selected]),'nearest_relative_phase_RMSE':stats([q['relative_phase_RMSE'] for q in selected])}
    global_indices=[k for k,i in enumerate(allids) if by[i].role==C.ROLE_GLOBAL_DEV];globaldist=dd[np.ix_(global_indices,global_indices)];nearcount=int(((globaldist<=.25)&np.isfinite(globaldist)).sum()//2)
    fold_nn=[]
    for f in folds:
        train=f['train_case_ids']
        for cid in f['heldout_case_ids']:
            k=allids.index(cid);n=min(train,key=lambda q:(np.linalg.norm((x[k]-x[allids.index(q)])/130),q));q=pair(k,allids.index(n));oi=ids.index(cid);q.update(fold=f['fold'],unit_error=float(per['Unit']['state_relative_rmse'][oi]),unit_phase_error=float(per['Unit']['absolute_phase_rmse'][oi]),rho=float(rho_geom[oi]));fold_nn.append(q)
    geo={'geometry_scale_nm':130,'all156_nearest':nn,'local_S31_axis11':local,'missing':'D6_M05','global113_pairs_within_point25':nearcount,'strata':grouped,'fold_training_nearest':fold_nn,'fold_nearest_correlations':{k:corr([q[k] for q in fold_nn],[q['unit_phase_error'] for q in fold_nn]) for k in ['geometry_distance','weighted_phase_RMSE','relative_phase_RMSE']},'local_absolute_phase':stats([q['weighted_phase_RMSE'] for q in local]),'local_relative_phase':stats([q['relative_phase_RMSE'] for q in local]),'global_sparse_warning':'Global113 has no pair at normalizeddistance<=.25; does not establish physical discontinuity or local generalization. Repeated/shared nearest pairs are correlated.','repeatability':'No controlled cross-run numerical errorfloor; samecase crossheight consistency is different evidence; +/-5nm resolvability unproven.'};put('GEOMETRY_LOCAL_CONDITIONING_EVIDENCE.json',geo)
    # All pairs order-resolved quantities; descriptive, no response-dependent selection.
    rows=[pair(i,j) for i,j in zip(ii,jj)]
    with (OUT/'ALL156_ORDER_PHASE_PAIRS.csv').open('w',encoding='utf-8',newline='') as handle:
        names=['case_i','case_j','geometry_distance','state_distance','amplitude_distance','weighted_phase_RMSE','relative_phase_RMSE']+[f'absolute_m{j-3}' for j in range(7)]+[f'relative_m{j-3}' for j in range(7)]
        writer=csv.DictWriter(handle,fieldnames=names,lineterminator='\n');writer.writeheader()
        for row in rows:
            q={n:row[n] for n in names[:7]};q.update({f'absolute_m{j-3}':row['order_absolute_phase_RMSE'][j] for j in range(7)});q.update({f'relative_m{j-3}':row['order_relative_phase_RMSE'][j] for j in range(7)});writer.writerow(q)
    put('ALL156_PAIR_SUMMARY.json',{'pair_count':len(rows),'geometry_vs_absolute_phase':corr([q['geometry_distance'] for q in rows],[q['weighted_phase_RMSE'] for q in rows]),'geometry_vs_relative_phase':corr([q['geometry_distance'] for q in rows],[q['relative_phase_RMSE'] for q in rows]),'all_absolute':stats([q['weighted_phase_RMSE'] for q in rows]),'all_relative':stats([q['relative_phase_RMSE'] for q in rows]),'near_point1_absolute':stats([q['weighted_phase_RMSE'] for q in rows if q['geometry_distance']<=.1]),'near_point1_relative':stats([q['relative_phase_RMSE'] for q in rows if q['geometry_distance']<=.1])})
    put('PHYSICAL_CONTRACT_CONSISTENCY.json',{'source':'previous verified PHYSICAL_CONTRACT_CONSISTENCY_AUDIT.json and unchanged inputs','reference_nm':1722,'orders':list(range(-3,4)),'polarization':['TE','TM'],'label_dimensions':[21,7,2],'source_normalization':'C_hat weighted modal unit state; P_scale independent source-normalized transmittedpower. H2 eta from weightedabsstate; absolute=eta*P_scale,total=P_scale. No phase cross terms. Disk state norm need not beunit; original H2 uses its own power/routing normalization, no unsolicited fullstate renormalization.','new_contract_change':False,'no_oracle_alignment':True})
    check();foreign=hashlib.sha256(subprocess.check_output(['git','diff','--cached','--binary'],cwd=ROOT)).hexdigest();req(foreign==prot['foreign_index_sha'],'foreign staged changed')
    put('FINAL_ISOLATION_CHECK.json',{'status':'PASS','CPU_training_fits':0,'P_scale_fits':0,'FDTD':0,'replay':0,'confirmation_response_access':0,'original_artifact_hashes_unchanged':True,'original_formal_H1_exact':True,'confirmation_predictions_unchanged':True,'foreign_index_sha256':foreign,'saved_checkpoint_prediction_calls_only':True,'all_original_amplitude_8_fit_ledger_unchanged':True})
    print('AUDIT_COMPLETE_ZERO_FITS',json.dumps({'common_relative_errors':gauges['common_and_relative_existing_errors'],'local_abs':geo['local_absolute_phase'],'local_relative':geo['local_relative_phase'],'rho_geometry_corr':cr['geometry_correlations']}),flush=True)
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='run':run()
    else:raise ValueError('unknown command')
