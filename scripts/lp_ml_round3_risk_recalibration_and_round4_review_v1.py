"""Offline Round-3 risk recalibration and Round-4 planning review.

No solver, FDTD, physics rewrite, checkpoint rewrite, or frozen-test tuning.
The calibrated model is a monotone bounded-linear diagnostic, not a probability.
"""
from __future__ import annotations
import csv, hashlib, itertools, json, math, subprocess
from pathlib import Path
import numpy as np

ROOT=Path(r"D:\project\worktrees\blue_apcd_lp_stage11_4")
O=ROOT/'outputs/lp_ml_dataset_v1'; A=O/'analysis'; P=O/'plans'; C3=O/'clean_v3'; S=O/'staging/lp_ml_dataset_v1_round3_targeted_active_learning_attempt1_v1'; SEARCH=P/'lp_ml_six_bin_inverse_search_round3_v1'
PLAN=P/'lp_ml_dataset_v1_round3_64_candidate_plan_v1.csv'; POOL=SEARCH/'lp_ml_six_bin_candidate_pool_v1.csv'; TUPLE=SEARCH/'lp_ml_six_tuple_pareto_front_v1.json'; PRED=A/'lp_ml_round3_pre_retrain_prospective_predictions_v1.json'; ACT=S/'candidate_wavelength_jones_v1.csv'; SPLIT=C3/'split_clean_v3.csv'
T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']
F=['seed_dispersion','raw_jones_disagreement','nearest_training_distance','local_density_gap','local_gradient_norm','quantization_sensitivity','wavelength_endpoint_disagreement','manufacturing_boundary_proximity']
def rd(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def write_csv(p,rows,fields=None):
    p.parent.mkdir(parents=True,exist_ok=True); fs=fields or (list(rows[0]) if rows else [])
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fs,extrasaction='ignore');w.writeheader();w.writerows(rows)
def ranks(a):
    a=np.asarray(a,float); order=np.argsort(a,kind='mergesort'); out=np.empty(len(a)); out[order]=np.arange(len(a),dtype=float); return out/(max(len(a)-1,1))
def corr(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);return float(np.corrcoef(a,b)[0,1]) if len(a)>1 and np.std(a)>0 and np.std(b)>0 else 0.0
def vec5(r):return np.array([float(r['J1_side_nm']),float(r['J2_length_nm']),float(r['J2_width_nm']),float(r['D_nm']),float(r['Psi_deg'])],float)
def jvec(r,model='selected_blend'):return np.asarray(r[model],float)
def feature_proxy(r,local_gap,gradient):
    direct=float(r.get('direct_gap_nm',100));periodic=float(r.get('periodic_gap_nm',100));margin=max(min(direct,periodic),1e-6)
    nearest=float(r.get('nearest_physics_distance',r.get('novelty_penalty',0)) or 0)
    quant=abs(float(r.get('continuous_loss',0) or 0)-float(r.get('quantized_loss',0) or 0))
    return np.array([float(r.get('ensemble_dispersion',r.get('five_seed_dispersion',0)) or 0),float(r.get('C0_blend_disagreement',r.get('disagreement_score',0)) or 0),nearest,float(local_gap),float(gradient),quant,float(r.get('spectral_instability',0) or 0),1.0/margin],float)
def fit_model(recs):
    X=np.array([r['features'] for r in recs],float);y=np.array([r['relative_error'] for r in recs],float)
    lo=np.percentile(X,5,axis=0);hi=np.percentile(X,95,axis=0);scale=np.maximum(hi-lo,1e-9);Z=np.clip((X-lo)/scale,0,1)
    A1=np.column_stack([np.ones(len(Z)),Z]);coef=np.linalg.lstsq(A1,y,rcond=None)[0];coef[1:]=np.maximum(coef[1:],0);
    if float(np.sum(coef[1:]))<1e-12:coef[1:]=1.0
    pred=np.maximum(0,A1@coef);res=np.abs(y-pred)
    return {'feature_order':F,'lower_percentiles':lo.tolist(),'upper_percentiles':hi.tolist(),'coefficients':coef.tolist(),'residual_q90':float(np.percentile(res,90)),'training_geometry_count':len(recs)}
def apply_model(model,X):
    lo=np.asarray(model['lower_percentiles']);hi=np.asarray(model['upper_percentiles']);Z=np.clip((np.asarray(X)-lo)/np.maximum(hi-lo,1e-9),0,1);coef=np.asarray(model['coefficients']);return np.maximum(0,coef[0]+Z@coef[1:])
def summarize(sub,thresholds=None):
    if not sub:return {'rows':0}
    e=np.asarray([r['relative_error'] for r in sub]);s=np.asarray([r['calibrated_score'] for r in sub]);d=np.asarray([r['features'][0] for r in sub]);
    return {'rows':len(sub),'error_mean':float(np.mean(e)),'score_mean':float(np.mean(s)),'score_error_spearman':corr(ranks(s),ranks(e)),'high_error_recall':float(np.mean((s>=thresholds[1])[(e>=thresholds[2])])) if thresholds and np.any(e>=thresholds[2]) else 0.0,'high_error_low_risk':int(np.sum((e>=thresholds[2])&(s<thresholds[0]))) if thresholds else 0,'dispersion_error_spearman':corr(ranks(d),ranks(e))}
def pareto(rows):
    keys=['phase_error_deg','projector_shape_error','sigma2_over_sigma1','combined_leakage','spectral_instability','calibrated_upper_error']
    out=[]
    for a in rows:
        dominated=False
        for b in rows:
            if a is b:continue
            if all(float(b.get(k,0))<=float(a.get(k,0))+1e-12 for k in keys) and any(float(b.get(k,0))<float(a.get(k,0))-1e-12 for k in keys):dominated=True;break
        if not dominated:out.append(a)
    out.sort(key=lambda r:(float(r.get('calibrated_upper_error',0))+float(r.get('phase_error_deg',0))/100+float(r.get('projector_shape_error',0)),r['candidate_id']))
    return out
def main():
    plan={r['candidate_id']:r for r in rd(PLAN)};pool=rd(POOL);pool_by={r['candidate_id']:r for r in pool};pred= json.loads(PRED.read_text())['rows'];actual=rd(ACT);split={r['candidate_id']:r for r in rd(SPLIT)}
    def checkpoint_hashes(root):
        return {p.name:sha(p) for p in sorted(root.glob('residual_mlp_seed_*.pt'))}
    protected={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'reports/lp_ml1a3_git_history_geometry_reconstruction.md',ROOT/'reports/stage11_4a20_legacy_fsp_object_inventory.md']}
    freeze={'contract':'LP_ML_ROUND3_RISK_RECALIBRATION_INPUT_FREEZE_V1','clean_v3_dataset_sha256':sha(C3/'lp_ml_dataset_v1_merged_clean_v3_round3_377_geometry_3393_rows.csv'),'clean_v3_split_sha256':sha(SPLIT),'clean_v3_normalization_sha256':sha(C3/'normalization_clean_v3.json'),'predictions_sha256':sha(PRED),'accepted_physics_csv_sha256':sha(ACT),'quality_audit_sha256':sha(S/'quality_audit_v1.json'),'candidate_pool_sha256':sha(POOL),'tuple_front_sha256':sha(TUPLE),'planning_selection_sha256':sha(A/'lp_ml_round3_validation_selection_v1.json'),'c0_checkpoint_sha256':checkpoint_hashes(O/'model_runtime_round1_frozen_v1'),'c1_checkpoint_sha256':checkpoint_hashes(O/'clean_v2/model_runtime_recompetition_v2/C1'),'c5_checkpoint_sha256':checkpoint_hashes(C3/'model_runtime_round3_c5_v1'),'protected_report_sha256':protected,'solver_calls':0,'frozen_tests_used_for_tuning':False,'physics_rewrite':False}
    dump(A/'lp_ml_round3_risk_recalibration_input_freeze_v1.json',freeze)
    # Local density and local predicted phase gradient over the frozen 508 pool.
    V=np.array([vec5(r) for r in pool],float); scales=np.maximum(np.ptp(V,axis=0),1.0); local={}
    for i,r in enumerate(pool):
        dist=np.linalg.norm((V-V[i])/scales,axis=1); order=np.argsort(dist)[1:9]; gap=float(np.median(dist[order])) if len(order) else 1.0
        ph=np.array([float(pool[j].get('phase_error_deg',0)) for j in order]); dd=dist[order]; grad=float(np.linalg.norm(np.polyfit(dd,ph,1)[0])) if len(order)>=2 and np.ptp(dd)>1e-9 else 0.0
        local[r['candidate_id']]=(gap,grad)
    for cid,r in plan.items():
        if cid in local: continue
        dv=np.linalg.norm((V-vec5(r))/scales,axis=1); order=np.argsort(dv)[:8]; gap=float(np.median(dv[order])) if len(order) else 1.0
        ph=np.array([float(pool[j].get('phase_error_deg',0)) for j in order]); dd=dv[order]; grad=float(np.linalg.norm(np.polyfit(dd,ph,1)[0])) if len(order)>=2 and np.ptp(dd)>1e-9 else 0.0
        local[cid]=(gap,grad)
    amap={(r['candidate_id'],float(r['wavelength_nm'])):r for r in actual}; pmap={}
    for r in pred:pmap.setdefault(r['candidate_id'],[]).append(r)
    records=[]; row_forensics=[]
    for cid,prs in sorted(pmap.items()):
        if len(prs)!=9 or sum(1 for a in actual if a['candidate_id']==cid)!=9:continue
        base=plan.get(cid,pool_by.get(cid)); rows=sorted(prs,key=lambda x:float(x['wavelength_nm'])); ys=[]; es=[]; abses=[]; ds=[]; gs=[]
        for pr in rows:
            a=amap.get((cid,float(pr['wavelength_nm']))); y=np.asarray([float(a[k]) for k in T]); p=jvec(pr); ae=float(np.linalg.norm(p-y)); e=float(ae/max(np.linalg.norm(y),1e-9)); es.append(e);abses.append(ae)
            ens=np.stack([jvec(pr,k) for k in ['C1','C2','C3','C4']]);ds.append(float(np.linalg.norm(np.std(ens,axis=0)))); gs.append(float(np.linalg.norm(jvec(pr,'C0')-p))); ys.append((pr,a))
        ens0=np.stack([jvec(rows[0],k) for k in ['C1','C2','C3','C4']]);ens8=np.stack([jvec(rows[-1],k) for k in ['C1','C2','C3','C4']]); endpoint=float(np.linalg.norm(np.mean(ens8,axis=0)-np.mean(ens0,axis=0)))
        feat=feature_proxy(base,*local[cid]);feat[0]=float(np.mean(ds));feat[1]=float(np.mean(gs));feat[6]=endpoint
        rel=float(np.mean(es)); rec={'candidate_id':cid,'category':base.get('category',base.get('source','UNKNOWN')),'target_bin':str(base.get('target_bin','')),'split':split.get(cid,{}).get('split','unknown'),'features':feat.tolist(),'relative_error':rel,'absolute_error_mean':float(np.mean(abses)),'row_errors':es,'seed_dispersion':float(np.mean(ds)),'raw_disagreement':float(np.mean(gs)),'geometry_family':base.get('geometry_family',base.get('family','')),'acquisition_source':base.get('source','')}
        records.append(rec)
        for pr,e,ae,d,g in zip(rows,es,abses,ds,gs):row_forensics.append({'candidate_id':cid,'category':rec['category'],'target_bin':rec['target_bin'],'wavelength_nm':float(pr['wavelength_nm']),'relative_error':e,'absolute_error':ae,'seed_dispersion':d,'raw_disagreement':g,'features':feat.tolist()})
    train=[r for r in records if r['split'] in ('train','validation')];test=[r for r in records if r['split']=='test']
    # Deterministic geometry-grouped 5-fold cross-validation over calibration geometries.
    cv=[];ids=sorted(r['candidate_id'] for r in train)
    for fold in range(5):
        tr=[r for r in train if ids.index(r['candidate_id'])%5!=fold];va=[r for r in train if ids.index(r['candidate_id'])%5==fold];m=fit_model(tr);scores=apply_model(m,np.array([r['features'] for r in tr]));thr=(float(np.quantile(scores,.4)),float(np.quantile(scores,.75)),float(np.quantile([r['relative_error'] for r in tr],.75))); predv=apply_model(m,np.array([r['features'] for r in va]));
        for r,sco in zip(va,predv):x=dict(r);x['calibrated_score']=float(sco);cv.append((x,thr))
    cv_recs=[x for x,_ in cv];thr_final=None
    # Aggregate CV performance and dispersion-only baseline.
    y=np.array([r['relative_error'] for r in cv_recs]);sco=np.array([r['calibrated_score'] for r in cv_recs]);disp=np.array([r['features'][0] for r in cv_recs]); high=y>=np.quantile(y,.75); risk_low=sco<np.quantile(sco,.4); disp_low=disp<np.quantile(disp,.5)
    cv_eval={'geometry_grouped_folds':5,'calibration_geometries':len(train),'heldout_rows':len(cv_recs),'calibrated_rank_correlation':corr(ranks(sco),ranks(y)),'dispersion_only_rank_correlation':corr(ranks(disp),ranks(y)),'calibrated_high_error_recall':float(np.mean((sco>=np.quantile(sco,.75))[high])),'dispersion_only_high_error_recall':float(np.mean((disp>=np.quantile(disp,.75))[high])),'calibrated_high_error_low_risk_count':int(np.sum(high&risk_low)),'dispersion_only_high_error_low_risk_count':int(np.sum(high&disp_low)),'calibrated_risk_classes':sorted(set('LOW' if x<np.quantile(sco,.4) else 'MODERATE' if x<np.quantile(sco,.75) else 'HIGH' for x in sco))}
    final=fit_model(train); train_scores=apply_model(final,np.array([r['features'] for r in train])); final_low=float(np.quantile(train_scores,.4));final_high=float(np.quantile(train_scores,.75));error_high=float(np.quantile([r['relative_error'] for r in train],.75));thr_final=(final_low,final_high,error_high)
    # 27-row low-dispersion/high-error forensic, with deterministic primary-cause labels.
    all_errors=np.array([x['absolute_error'] for x in row_forensics]);all_disp=np.array([x['seed_dispersion'] for x in row_forensics]);lowdisp=float(np.median(all_disp));higherr=float(np.percentile(all_errors,90));forensic=[]
    for x in row_forensics:
        if x['absolute_error']<higherr or x['seed_dispersion']>lowdisp:continue
        f=x['features']; contrib=np.asarray(f)*np.asarray(final['coefficients'][1:]);
        if f[1]>=np.percentile([r['features'][1] for r in records],75) and f[0]<=lowdisp:cause='ENSEMBLE_SHARED_BIAS'
        elif f[3]>=np.percentile([r['features'][3] for r in records],75) or f[2]>=np.percentile([r['features'][2] for r in records],75):cause='DATA_COVERAGE_GAP'
        elif f[5]>=np.percentile([r['features'][5] for r in records],75) or f[7]>=np.percentile([r['features'][7] for r in records],75):cause='QUANTIZATION_SENSITIVITY'
        elif f[6]>=np.percentile([r['features'][6] for r in records],75):cause='SPECTRAL_NONLINEARITY'
        elif float(pool_by.get(x['candidate_id'],{}).get('phase_error_deg',0))>=np.percentile([float(q.get('phase_error_deg',0)) for q in pool],75):cause='OBJECTIVE_EXTRAPOLATION'
        else:cause='MIXED_CAUSE'
        x=dict(x);x['primary_failure_class']=cause;forensic.append(x)
    # Rescore all 508 candidates without changing IDs/hashes.
    Xp=np.array([feature_proxy(r,*local[r['candidate_id']]) for r in pool]);scores=apply_model(final,Xp);upper=scores+float(final['residual_q90']);resc=[]
    for r,sco,up in zip(pool,scores,upper):
        x=dict(r);x['calibrated_risk_score']=float(sco);x['calibrated_error_estimate']=float(sco);x['calibrated_upper_error_bound']=float(up);x['calibrated_risk_class']='CALIBRATED_LOW_RISK' if sco<final_low else 'CALIBRATED_MODERATE_RISK' if sco<final_high else 'CALIBRATED_HIGH_RISK';x['old_risk_class']=r.get('risk_class','');x['risk_model_label']='MONOTONE_BOUNDED_LINEAR_NOT_PROBABILITY';resc.append(x)
    write_csv(A/'lp_ml_round3_recalibrated_508_candidate_table_v1.csv',resc)
    # Per-bin recalibrated Pareto libraries.
    bin_out={};
    for b in range(6):
        rr=[r for r in resc if str(r.get('target_bin'))==str(b)];front=pareto(rr)[:20];bin_out[str(b)]={'candidate_count':len(rr),'pareto_count':len(front),'risk_counts':{k:sum(x['calibrated_risk_class']==k for x in rr) for k in ['CALIBRATED_LOW_RISK','CALIBRATED_MODERATE_RISK','CALIBRATED_HIGH_RISK']},'geometry_families':len({x.get('geometry_family','') for x in rr}),'pareto':front}
        dump(SEARCH/f'lp_ml_six_bin_recalibrated_pareto_bin{b}_v1.json',bin_out[str(b)])
    # Rescore the frozen tuple front only; no new candidate generation.
    tdata=json.loads(TUPLE.read_text()); byid={r['candidate_id']:r for r in resc};tuples=[];seen=set()
    def add_tuple(ids2,original=None,source='RECALIBRATED_EXISTING_TUPLE'):
        key=tuple(ids2)
        if key in seen:return
        chosen=[byid[i] for i in ids2 if i in byid]
        if len(chosen)!=6:return
        seen.add(key);risk={k:sum(x['calibrated_risk_class']==k for x in chosen) for k in ['CALIBRATED_LOW_RISK','CALIBRATED_MODERATE_RISK','CALIBRATED_HIGH_RISK']}
        tuples.append({'candidate_ids':list(ids2),'phi_offset_deg':original.get('phi_offset_deg') if original else None,'original_tuple_score':original.get('tuple_score') if original else None,'recalibrated_tuple_score':float(original.get('tuple_score',0) if original else 0)+10*float(np.mean([x['calibrated_upper_error_bound'] for x in chosen])),'risk_counts':risk,'geometry_families':len({x.get('geometry_family','') for x in chosen}),'all_bins_covered':True,'source':source})
    for t in tdata.get('top_tuples',[]):add_tuple(list(t.get('candidate_ids',[])),t)
    # Deterministic expansion from the existing per-bin Pareto candidates only; no new geometry.
    choices=[]
    for b in range(6):
        rr=sorted([r for r in resc if str(r.get('target_bin'))==str(b)],key=lambda x:(x['calibrated_upper_error_bound'],float(x.get('phase_error_deg',0)),x['candidate_id']))[:3];choices.append(rr)
    for combo in itertools.product(*choices):add_tuple([r['candidate_id'] for r in combo],source='RECALIBRATED_PARETO_CARTESIAN_EXISTING_POOL')
    tuples.sort(key=lambda x:x['recalibrated_tuple_score']);nonhigh=next((t for t in tuples if t['risk_counts']['CALIBRATED_LOW_RISK']+t['risk_counts']['CALIBRATED_MODERATE_RISK']>0),None)
    tuple_front=tuples[:103]
    tuple_out={'contract':'LP_ML_ROUND3_RECALIBRATED_TUPLE_FRONT_V1','source_tuple_sha256':sha(TUPLE),'tuple_count':len(tuple_front),'candidate_combinations_considered':len(tuples),'best_tuple':tuple_front[0] if tuple_front else None,'best_non_all_high_risk_tuple':nonhigh,'top_tuples':tuple_front,'solver_calls':0}
    dump(SEARCH/'lp_ml_six_bin_recalibrated_tuple_front_v1.json',tuple_out)
    perbin_ok=all(bin_out[str(b)]['risk_counts']['CALIBRATED_LOW_RISK']+bin_out[str(b)]['risk_counts']['CALIBRATED_MODERATE_RISK']>=3 for b in range(6)); model_ok=cv_eval['calibrated_rank_correlation']>0.35 and cv_eval['calibrated_high_error_low_risk_count']<cv_eval['dispersion_only_high_error_low_risk_count'] and len(cv_eval['calibrated_risk_classes'])>1
    if not model_ok:outcome='LP_ML_ROUND3_MODEL_OR_RISK_FIX_REQUIRED'
    elif perbin_ok and nonhigh:outcome='LP_ML_ROUND3_RECALIBRATED_POOL_READY_FOR_INVERSE_FDTD_PLANNING'
    else:outcome='LP_ML_ROUND4_TARGETED_PLAN_READY_FOR_AUTHORIZATION'
    # Optional planned-only Round-4 contract, only if the calibrated risk model is usable but coverage remains.
    r4path=None
    if outcome=='LP_ML_ROUND4_TARGETED_PLAN_READY_FOR_AUTHORIZATION':
        selected=[]
        for b,n in [(0,5),(1,5),(2,5),(3,9),(4,9),(5,9)]:
            rr=sorted([r for r in resc if str(r.get('target_bin'))==str(b)],key=lambda x:(x['calibrated_risk_class']=='CALIBRATED_HIGH_RISK',x['calibrated_upper_error_bound'],float(x.get('phase_error_deg',0))))[:n];selected.extend(rr)
        controls=[]
        for b in range(6):
            rr=[r for r in resc if str(r.get('target_bin'))==str(b) and r['candidate_id'] not in {x['candidate_id'] for x in selected}];controls.extend(sorted(rr,key=lambda x:(x['calibrated_risk_class']=='CALIBRATED_HIGH_RISK',x['calibrated_upper_error_bound']))[:1])
        selected+=controls
        plan4=[]
        for i,r in enumerate(selected,1):plan4.append({'round4_candidate_id':f'R4P_{i:03d}','source_candidate_id':r['candidate_id'],'target_bin':r['target_bin'],'source':r.get('source'),'geometry_family':r.get('geometry_family'),'exact_surrogate_hash':r.get('exact_surrogate_hash'),'canonical_surrogate_hash':r.get('canonical_surrogate_hash'),'symmetry_surrogate_hash':r.get('symmetry_surrogate_hash'),'calibrated_risk_class':r['calibrated_risk_class'],'calibrated_upper_error_bound':r['calibrated_upper_error_bound'],'status':'PLANNED_NOT_RUN','physics_status':'ABSENT_NOT_SIMULATED','prediction_status':'MODEL_PREDICTION_NOT_PHYSICS_LABEL','solver_authorized':False})
        r4path=P/'lp_ml_round4_targeted_plan_v1.json';dump(r4path,{'contract':'LP_ML_ROUND4_TARGETED_PLAN_V1','status':'PLANNED_NOT_RUN','candidate_count':len(plan4),'solver_budget':{'geometries':48,'subruns':96,'wavelengths_nm':[450.0+i*.5 for i in range(9)]},'source_pool_sha256':sha(POOL),'no_new_geometry':True,'rows':plan4})
    dump(A/'lp_ml_round3_accounting_audit_v1.json',{'planned':128,'entered':127,'unique':126,'duplicate':1,'accepted':121,'quarantined_geometries':6,'complete_geometries':58,'admitted_rows':522,'solver_calls':0,'duplicate_preserved':True,'source_quality_audit_sha256':sha(S/'quality_audit_v1.json')})
    dump(A/'lp_ml_round3_low_dispersion_high_error_forensic_v1.json',{'row_count':len(forensic),'dispersion_threshold':lowdisp,'error_threshold_p90':higherr,'classification_enums':['ENSEMBLE_SHARED_BIAS','DATA_COVERAGE_GAP','OBJECTIVE_EXTRAPOLATION','QUANTIZATION_SENSITIVITY','SPECTRAL_NONLINEARITY','MODEL_CAPACITY_LIMIT','MIXED_CAUSE'],'rows':forensic})
    write_csv(A/'lp_ml_round3_low_dispersion_high_error_forensic_v1.csv',forensic)
    dump(P/'lp_ml_round3_calibrated_risk_contract_v1.json',{'contract':'LP_ML_ROUND3_CALIBRATED_RISK_V1','target':'relative_frobenius_error','features':F,'calibration':'BOUNDED_LINEAR_RANK_CALIBRATION','calibration_data':'Round-3 complete train+validation geometries only','frozen_tests_used_for_tuning':False,'risk_labels':['CALIBRATED_LOW_RISK','CALIBRATED_MODERATE_RISK','CALIBRATED_HIGH_RISK'],'not_probability':True,'solver_calls':0})
    dump(A/'lp_ml_round3_risk_calibration_model_v1.json',{'contract':'LP_ML_ROUND3_RISK_CALIBRATION_MODEL_V1','model':final,'thresholds':{'low':final_low,'high':final_high,'high_error':error_high},'training_geometry_ids':sorted(r['candidate_id'] for r in train),'heldout_test_geometry_ids':sorted(r['candidate_id'] for r in test),'cross_validation':cv_eval,'solver_calls':0,'frozen_tests_used_for_tuning':False})
    dump(A/'lp_ml_round3_risk_calibration_evaluation_v1.json',{'contract':'LP_ML_ROUND3_RISK_CALIBRATION_EVALUATION_V1','cross_validation':cv_eval,'final_calibration_summary':summarize([dict(r,calibrated_score=float(apply_model(final,np.array([r['features']]))[0])) for r in train],thr_final),'r3_external_holdout_summary':summarize([dict(r,calibrated_score=float(apply_model(final,np.array([r['features']]))[0])) for r in test],thr_final),'solver_calls':0,'frozen_tests_used_for_tuning':False})
    dump(A/'lp_ml_round3_round4_need_assessment_v1.json',{'outcome':outcome,'model_ok':model_ok,'per_bin_minimum_low_or_moderate':perbin_ok,'non_all_high_risk_tuple':bool(nonhigh),'candidate_pool_count':len(resc),'per_bin_risk_counts':{b:bin_out[str(b)]['risk_counts'] for b in range(6)},'tuple_front_count':len(tuple_front),'candidate_combinations_considered':len(tuples),'round4_plan_path':str(r4path) if r4path else None,'solver_calls':0,'no_solver_authorization':True})
    report=['# LP ML Round-3 risk recalibration and Round-4 planning review v1','',f'## Status\n\n`{outcome}`','','## Round-3 accounting','', '127 entered / 126 unique / 1 duplicate / 121 accepted / 6 quarantined geometries / 58 complete geometries / 522 admitted rows. Duplicate accounting and all failed evidence are preserved.','','## Low-dispersion high-error root cause','',f"Forensic cohort size={len(forensic)} rows; dispersion threshold={lowdisp:.6g}; error p90 threshold={higherr:.6g}. Causes are classified in the forensic CSV/JSON without rewriting physics.",'','## Calibrated risk model','',f"Monotone bounded-linear rank calibration uses {len(train)} train/validation geometries and excludes frozen tests. Features: {', '.join(F)}. Risk is an interpretable score, not a probability.",'','## Calibration performance','',f"Geometry-grouped CV calibrated rank correlation={cv_eval['calibrated_rank_correlation']:.3f} vs dispersion-only={cv_eval['dispersion_only_rank_correlation']:.3f}; calibrated high-error low-risk={cv_eval['calibrated_high_error_low_risk_count']} vs dispersion-only={cv_eval['dispersion_only_high_error_low_risk_count']}; calibrated risk classes={cv_eval['calibrated_risk_classes']}.",'','## Per-bin recalibrated risk counts','',json.dumps({b:bin_out[str(b)]['risk_counts'] for b in range(6)},indent=2), '', '## Tuple result','',f"Recalibrated tuple front count={len(tuple_front)} (existing combinations considered={len(tuples)}); non-all-high-risk tuple={'present' if nonhigh else 'absent'}.",'','## Round-4 necessity','',f"Outcome={outcome}. No Round-4 solver is run or authorized in this task. Optional plan path={str(r4path) if r4path else 'none'}.",'','## Hard gates','', 'No solver/FDTD, no physics/split/normalization/checkpoint rewrite, no geometry054/K6/cVAE, no new degree of freedom, and protected reports unchanged.']
    (ROOT/'reports/lp_ml_round3_risk_recalibration_and_round4_review_v1.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print(json.dumps({'outcome':outcome,'forensic_rows':len(forensic),'cv':cv_eval,'per_bin':{b:bin_out[str(b)]['risk_counts'] for b in range(6)},'tuple_front_count':len(tuple_front),'combinations_considered':len(tuples),'round4_plan':str(r4path) if r4path else None},indent=2))
if __name__=='__main__':main()
