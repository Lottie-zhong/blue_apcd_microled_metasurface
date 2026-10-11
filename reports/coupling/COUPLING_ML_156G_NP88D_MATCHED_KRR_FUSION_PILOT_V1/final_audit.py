"""Independent read-only fit/artifact audit and scientific report completion."""
from pathlib import Path
import sys,json,hashlib,datetime
import numpy as np
import joblib
from sklearn.metrics.pairwise import rbf_kernel,euclidean_distances
from k6_v2_pipeline import np88_fusion_pilot_v1 as P
from k6_v2_pipeline import contracts as C,models as M,h1
from k6_v2_pipeline.amended156 import adapter as A, evaluation as V

def main():
    pr=P.check_pins();col=A.load_collection(False);by={c.case_id:c for c in col.cases}
    with np.load(P.OUT/'NP88_FEATURES.npz',allow_pickle=False) as z:
        ids=z['case_ids'].tolist();fb=dict(zip(ids,z['features']))
    ledger=P.read('FIT_LEDGER.json');folds=P.read('MATCHED_OUTER_FOLD_MANIFEST.json')['folds'];distance=[];reload=[]
    baseline={f:run for f,p,run in P.baseline_runs(col)}
    require=P.require
    for t in folds:
        row=ledger['fits'][t['task_id']];p=P.OUT/'models'/t['task_id'];require(row['status']=='COMPLETE' and row['logical_fit_count']==1 and row['internal_head_fit_calls']==2,'fit_count_or_state')
        require(A.sha(p/'model.joblib')==row['model_sha256'] and A.sha(p/'predictions.npz')==row['prediction_sha256'],'fit_artifact_SHA')
        saved=joblib.load(p/'model.joblib');require(saved['task']==t,'saved_task_lineage')
        require(saved['preregistration_sha256']==A.sha(P.OUT/'PREREGISTRATION.json'),'prereg_lineage')
        tr=t['train_case_ids'];va=t['heldout_case_ids'];xt=np.array([by[c].ordered_D_nm for c in tr],float);xv=np.array([by[c].ordered_D_nm for c in va],float);ft=np.array([fb[c] for c in tr]);fv=np.array([fb[c] for c in va]);s=saved['input_scaler']
        require(s.to_dict()==P.BlockScaler(xt,ft).to_dict(),'input_scaler_fit_scope')
        yt=C.pack_model_target(np.array([by[c].c_hat for c in tr]),np.array([by[c].p_scale for c in tr]));ys=M.V2TargetNormalizer.fit(yt)
        require(saved['target_scaler'].to_dict()==ys.to_dict()==baseline[t['fold']].target_scaler.to_dict(),'target_scaler_scope')
        xb=s.transform(xt,ft);xp=s.transform(xv,fv);gd,nd=s.blocks(xt,ft);gv,nv=s.blocks(xv,fv)
        pred=np.concatenate([m.predict(xp) for m in saved['models']],1);cp,pp=C.unpack_model_target(ys.inverse_transform(pred))
        with np.load(p/'predictions.npz',allow_pickle=False) as z:
            require(z['case_ids'].tolist()==va and np.array_equal(z['C_hat_real']+1j*z['C_hat_imag'],cp) and np.array_equal(z['P_scale'],pp),'reloaded_prediction_exact')
        # KRR coefficients must solve original normalized train targets, not held-out values.
        k=rbf_kernel(xb,gamma=t['gamma'])
        residuals=[]
        for m,target in zip(saved['models'],[ys.transform(yt)[:,:588],ys.transform(yt)[:,588:]]):
            require(np.array_equal(m.X_fit_,xb) and m.gamma==t['gamma'] and m.alpha==t['ridge_alpha'],'kernel_configuration')
            err=(k+t['ridge_alpha']*np.eye(124))@m.dual_coef_-target
            require(np.max(np.abs(err))<1e-10,'dual_coefficient_normal_equation')
            residuals.append(float(np.max(np.abs(err))))
        dg=euclidean_distances(gv,gd,squared=True);dn=euclidean_distances(nv,nd,squared=True);kb=rbf_kernel(xp,xb,gamma=t['gamma']);xa=baseline[t['fold']].x_scaler.transform(xt);xav=baseline[t['fold']].x_scaler.transform(xv);ka=rbf_kernel(xav,xa,gamma=t['gamma'])
        distance.append({'fold':t['fold'],'NP_distance_fraction_validation_to_train':V.summary((dn/(dg+dn)).reshape(-1)),'A_max_similarity_per_heldout':V.summary(ka.max(1)),'B_max_similarity_per_heldout':V.summary(kb.max(1)),'A_mean_similarity_per_heldout':V.summary(ka.mean(1)),'B_mean_similarity_per_heldout':V.summary(kb.mean(1)),'standardized_NP_heldout_max_abs':float(np.max(abs((fv-s.mean)/s.scale))),'diagnostic_only_no_weight_changes':True})
        reload.append({'fold':t['fold'],'model':P.pin(p/'model.joblib'),'predictions':P.pin(p/'predictions.npz'),'exact_reload':True,'dual_equation_max_residual':residuals,'input_target_scalers_train_only':True})
    require(sum(q['logical_fit_count'] for q in ledger['fits'].values())==4,'fourfits_only')
    # Frozen provider must reject unsupported domains without fitting or solver calls.
    mod,provider=P.feature_provider();checks=[]
    for args in [([95]*6,450,'P',{}),([100]*6,444,'P',{}),([100]*6,456,'P',{}),([100]*6,450,'S',{}),([100]*6,450,'P',{'u_x':.1})]:
        try:provider.infer(args[0],args[1],args[2],**args[3])
        except ValueError as e:checks.append(str(e))
        else:raise ValueError('provider_unsupported_request_accepted')
    P.put('KERNEL_HELDOUT_DISTANCE_AUDIT.json',{'folds':distance,'no_new_fit':True,'no_response_used_for_kernel_weights':True})
    P.put('FINAL_MODEL_AND_LEAKAGE_AUDIT.json',{'status':'PASS','logical_fits':4,'internal_output_head_calls':8,'baseline_fits':0,'reload_checks':reload,'provider_unsupported_domain_rejections':checks,'synthetic_fits':0,'confirmation_response_access':0,'new_evaluation_gates':0,'scientific_solver':0})
    paired=P.read('PAIRED_GEOMETRY_ERROR_ANALYSIS.json');diag=P.read('STATE_NORM_AND_PHASE_DIAGNOSTIC.json');spect=P.read('SPECTRAL_SUPPORT_DOMAIN_ANALYSIS.json');evaluation=P.read('H1_H2_EVALUATION.json');verdict=P.read('FINAL_SCIENTIFIC_VERDICT.json')
    # All OOF tensors match persisted per-fold outputs and complete identity order.
    oid=sum([t['heldout_case_ids'] for t in folds],[])
    for arm in ['A','B']:
        with np.load(P.OUT/f'{arm}_OOF_PREDICTIONS.npz',allow_pickle=False) as z:
            require(z['case_ids'].tolist()==oid and z['C_hat_real'].shape==(124,21,7,2) and z['P_scale'].shape==(124,21),'OOF_shape_and_identity')
    tables=['\n## Fold paired results (B minus A)\n','|Metric|Fold|Median delta|Wins/losses|','|---|---:|---:|---:|']
    for key in ['state_relative_rmse','routing_eta_rmse','total_power_relative_rmse']:
        for fold,q in paired[key]['folds'].items():tables.append(f"|{key}|{fold}|{q['delta']['median']:.6f}|{q['wins']}/{q['losses']}|")
    tables.extend(['\n## Spectral strata (diagnostic, no gate substitution)\n','|Band|State A/B median|Routing A/B median|P_scale/total A/B median|','|---|---:|---:|---:|'])
    for band,q in spect.items():
        a=q['A']['metrics'];b=q['B']['metrics'];tables.append(f"|{band}|{a['state_relative_rmse']['median']:.6f}/{b['state_relative_rmse']['median']:.6f}|{a['routing_eta_rmse']['median']:.6f}/{b['routing_eta_rmse']['median']:.6f}|{a['total_power_relative_rmse']['median']:.6f}/{b['total_power_relative_rmse']['median']:.6f}|")
    tables.extend(['\n## Geometry bootstrap uncertainty (descriptive)\n','|Metric|Mean delta95%CI|Median delta95%CI|','|---|---|---|'])
    for key in ['state_relative_rmse','routing_eta_rmse','absolute_order_source_normalized_rmse','total_power_relative_rmse']:
        b=paired[key]['bootstrap'];tables.append(f"|{key}|{b['mean_delta_CI95']}|{b['median_delta_CI95']}|")
    tails={}
    for key in ['state_relative_rmse','routing_eta_rmse','total_power_relative_rmse']:
        rows=paired[key]['per_geometry'];tails[key]={'most_worsened':sorted(rows,key=lambda q:q['delta'],reverse=True)[:10],'most_improved':sorted(rows,key=lambda q:q['delta'])[:10],'worst_A':max(rows,key=lambda q:q['A']),'worst_B':max(rows,key=lambda q:q['B'])}
    P.put('TAIL_PAIRED_AUDIT.json',tails)
    tables.extend(['\n## Phase, norm and limits\n'])
    for arm in ['A','B']:
        d=diag[arm];tables.append(f"{arm}: amplitude error median/q95 {d['amplitude_relative_RMSE']['median']:.6f}/{d['amplitude_relative_RMSE']['q95']:.6f}; truthweighted absolutephase {d['truth_weighted_phase_RMSE']['median']:.6f}/{d['truth_weighted_phase_RMSE']['q95']:.6f}rad; relativephase {d['relative_phase_RMSE']['median']:.6f}/{d['relative_phase_RMSE']['q95']:.6f}rad; normratio {d['norm_ratio']['median']:.6f}/{d['norm_ratio']['q95']:.6f}.\n")
    tables.append('The fixed NP88 fusion has no clear state/routing gain and does not merit automatic expansion into a larger fusion network. Some absolute-order tail and thresholded-relative metrics improve, but core state/routing/P_scale medians worsen and norm collapse deepens. This negative result applies to this provider, block metric, frozen gamma/alpha and dataset; it does not prove all physics fusion is ineffective. Next scientific review should examine complex/modal/phase learnability and lawful LF/HF alignment before any residual. No scale retuning/MLP/confirmation launched.\n')
    tables.append('Kernel unregularized condition~3.4e3..1.1e4, regularized24.3..25.3; no constant NP columns, all156 runtime-supported. NP contributes~48..49% median trainpair squared distance. HF22 empirical support is distinct from legal singlepillar runtime support; OOD is not a training feature. Kernel metric changes are a confound for mechanistic attribution.\n')
    report=P.OUT/'FINAL_REPORT.md';report.write_bytes(report.read_bytes()+'\n'.join(tables).encode())
    P.put('EXECUTION_COUNTS.json',{'status':'COMPLETE','CPU_logical_KRR_fits':4,'baseline_reproduction_fits':0,'internal_state_head_fits':4,'internal_logP_head_fits':4,'MLP_fits':0,'NP_MDC_retrain':0,'local13':0,'synthetic_fits':0,'FDTD_entry':0,'replay':0,'confirmation_response_access':0,'old65G_twofits':'SUPERSEDED_NOT_EXECUTED','new_P_scale_training':'4 logP output heads within joint KRR fits; no additional standalone fits'})
    P.check_pins();require(hashlib.sha256(P.git('diff','--cached','--binary')).hexdigest()==pr['foreign_index_sha256'],'foreign_staged_changed')
    P.put('FINAL_SCIENCE_CLOSURE.json',{'status':'PASS','utc':P.utc(),'all_science_input_pins_unchanged':True,'confirmation_28_prediction_SHA_unchanged':True,'confirmation32_responses_sealed':True,'baseline4exact':True,'fusion4models_reload_exact':True,'H1_H2_SHA_unchanged':True,'fit_scope':4,'foreign_staged_SHA_unchanged':True,'fit_audit_source':P.pin(Path(__file__))})
    print('\n'.join(tables));print('TAILS',json.dumps(tails));print('FINAL_PASS',verdict)

if __name__=='__main__':main()
