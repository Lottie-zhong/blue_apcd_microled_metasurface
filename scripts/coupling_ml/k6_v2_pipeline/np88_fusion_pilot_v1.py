"""Matched NP88 feature pilot: four CPU KRR fits, no scientific solver."""
from pathlib import Path
import os, sys, json, hashlib, importlib.util, subprocess, datetime, time
import numpy as np
import joblib
from sklearn.kernel_ridge import KernelRidge
from sklearn.metrics.pairwise import rbf_kernel, euclidean_distances
from .amended156 import adapter as A, engine as E, evaluation as V
from . import contracts as C, models as M, h1

TASK='COUPLING_ML_156G_NP88D_MATCHED_KRR_FUSION_PILOT_V1'
ROOT=A.ROOT
OUT=ROOT/'reports/coupling'/TASK
NP_ROOT=Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
PROVIDER=NP_ROOT/'scripts/np_k6_coupling_forward_feature_interface_v2.py'
PROVIDER_SHA='e68db57c2e144f60cf24f1c03ca6279bd50b6c94c8465e8f9f9f75dec68fdbfd'
SOURCE_HEAD='08254479a2ad19ceff6fa1b770da6fbd9f2cd89c'
FEATURE_NAMES=[f'lambda_{w}_eta_m{m:+d}' for w in range(445,456) for m in range(-3,4)]
# Wavelength-major, seven order fractions followed by T_proxy at each wavelength.
FEATURE_NAMES=[name for w in range(445,456) for name in [*[f'lambda_{w}_eta_m{m:+d}' for m in range(-3,4)],f'lambda_{w}_T_proxy']]

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def put(name,data):A.write(OUT/name,data)
def read(name):return A.read(OUT/name)
def require(cond,why):
    if not cond:raise ValueError(why)
def pin(p):return {'path':str(p),'sha256':A.sha(p),'bytes':Path(p).stat().st_size}
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

class BlockScaler:
    """No data-dependent weight selection. Only means/stds depend on train input."""
    def __init__(self,geometry,np_features):
        self.geometry=M.GeometryStandardizer.fit(geometry)
        f=np.asarray(np_features,np.float64)
        require(f.shape==(len(geometry),88) and np.isfinite(f).all(),'NP_training_feature_shape_or_finiteness')
        self.mean=f.mean(0);self.std=f.std(0);self.constant=self.std==0
        self.scale=np.where(self.constant,1.,self.std)
    def blocks(self,geometry,features):
        f=np.asarray(features,np.float64)
        require(f.shape==(len(geometry),88) and np.isfinite(f).all(),'NP_prediction_feature_shape_or_finiteness')
        z=(f-self.mean)/self.scale
        z[:,self.constant]=0.
        return self.geometry.transform(geometry)/np.sqrt(2.), z*np.sqrt(6./88.)/np.sqrt(2.)
    def transform(self,geometry,features):return np.concatenate(self.blocks(geometry,features),axis=1)
    def to_dict(self):return {'geometry':self.geometry.to_dict(),'NP_mean':self.mean.tolist(),'NP_std':self.std.tolist(),'constant_columns':np.flatnonzero(self.constant).tolist(),'geometry_factor':1/np.sqrt(2.),'NP_factor':np.sqrt(6/88)/np.sqrt(2.),'constant_rule':'outer-train zero variance columns map to zero for train and heldout; no imputation'}

def feature_provider():
    require(A.sha(PROVIDER)==PROVIDER_SHA,'frozen_NP_provider_SHA_mismatch')
    spec=importlib.util.spec_from_file_location('np88_frozen_provider',PROVIDER)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod,mod.NP_LF_FEATURE_PROVIDER_V2_Runtime(NP_ROOT)

def tests():
    # These are transformations/linear algebra tests, not model fits.
    rng=np.random.default_rng(88156);x=rng.normal(size=(12,6));f=rng.normal(size=(12,88));f[:,2]=3
    s=BlockScaler(x,f);before=json.dumps(s.to_dict(),sort_keys=True)
    g,n=s.blocks(x,f);require(np.all(s.transform(x,f)[:,8]==0),'constant_column_rule')
    s.transform(x+1e3,f+1e3);require(before==json.dumps(s.to_dict(),sort_keys=True),'heldout_changed_scaler')
    d=euclidean_distances(s.transform(x,f),s.transform(x,f),squared=True)
    require(np.allclose(d,euclidean_distances(g,g,squared=True)+euclidean_distances(n,n,squared=True),atol=1e-12),'distance_block_sum')
    y=rng.normal(size=(12,609));k=rbf_kernel(x,gamma=1/6);joint=np.linalg.solve(k+np.eye(12),y)
    split=np.concatenate([np.linalg.solve(k+np.eye(12),y[:,:588]),np.linalg.solve(k+np.eye(12),y[:,588:])],axis=1)
    require(np.allclose(joint,split,rtol=1e-12,atol=1e-12),'joint_vs_two_heads_linear_algebra')
    return {'status':'PASS','synthetic_fits':0,'checks':['training-only scaler immutable under extreme heldout input','constant NP columns deterministic zero','94D distance equals block contributions','609D KRR independent head solve equivalence'],'fit_calls':0}

def baseline_runs(col):
    by={c.case_id:c for c in col.cases};plan=A.build_plan();items=[]
    inv={q['path']:q['sha256'] for q in A.read(A.OUT/'SHA_INVENTORY.json')['files']}
    for fold in range(1,5):
        task=next(t for t in plan.curve_templates if t.model_kind=='RBF_KRR' and t.outer_fold==fold and t.training_geometry_count==124)
        p=A.OUT/'models/learning_curve'/task.task_id
        for name in ['fit.joblib','fit_manifest.json','predictions.npz','AMENDMENT_PROVENANCE_AND_RELOAD.json']:
            q=p/name;require(str(q) in inv and A.sha(q)==inv[str(q)],'baseline_artifact_SHA:'+str(q))
        manifest=A.read(p/'fit_manifest.json');require(manifest['status']=='COMPLETE','baseline_incomplete')
        run=joblib.load(p/'fit.joblib')
        require(run.task.task_id==task.task_id and run.task.train_case_ids==task.train_case_ids and run.prediction_case_ids==task.prediction_case_ids,'baseline_task_identity')
        require(len(run.task.train_case_ids)==124 and not(set(run.task.train_case_ids)&set(run.prediction_case_ids)),'baseline_split')
        x=np.array([by[c].ordered_D_nm for c in task.train_case_ids],float)
        y=C.pack_model_target(np.array([by[c].c_hat for c in task.train_case_ids]),np.array([by[c].p_scale for c in task.train_case_ids]))
        require(run.x_scaler.to_dict()==M.GeometryStandardizer.fit(x).to_dict(),'baseline_geometry_statistics')
        require(run.target_scaler.to_dict()==M.V2TargetNormalizer.fit(y).to_dict(),'baseline_output_statistics')
        require(run.model.gamma==manifest['task']['gamma'] and run.model.ridge_alpha==manifest['task']['ridge_alpha'],'baseline_hyperparameters')
        xp=np.array([by[c].ordered_D_nm for c in task.prediction_case_ids],float);cp,pp=E.predict_fit_run(run,xp)
        require(np.array_equal(cp,run.predicted_c_hat) and np.array_equal(pp,run.predicted_p_scale),'baseline_reload_prediction_parity')
        items.append((fold,p,run))
    return items

def prepare():
    require(not (OUT/'FIT_LEDGER.json').exists(),'existing_fit_ledger_do_not_refreeze')
    OUT.mkdir(parents=True,exist_ok=True)
    require(git('rev-parse','HEAD').decode().strip()==SOURCE_HEAD,'science_start_HEAD_changed_review')
    col=A.load_collection(False);by={c.case_id:c for c in col.cases};runs=baseline_runs(col)
    module,provider=feature_provider();ids=[c.case_id for c in col.cases];features=[];supports=[]
    for c in col.cases:
        row=[]
        for w in range(445,456):
            q=provider.infer(c.ordered_D_nm,w,'P',u_x=0.,k_y=0.)
            require(q['ordered_D_nm']==list(c.ordered_D_nm) and q['wavelength_nm']==w,'NP_row_alignment')
            fractions=[q['features']['eta_m_proxy'][f'm{m:+d}'] for m in range(-3,4)]
            require(abs(sum(fractions)-1)<2e-6 and min(fractions)>=0,'NP_fraction_invalid')
            row.extend(fractions+[q['features']['T_proxy']])
        features.append(row);supports.append({'case_id':c.case_id,**provider.support_audit(c.ordered_D_nm)})
    features=np.asarray(features,np.float64);require(features.shape==(156,88) and np.isfinite(features).all(),'NP88_incomplete')
    np.savez_compressed(OUT/'NP88_FEATURES.npz',case_ids=np.array(ids),ordered_D_nm=np.array([c.ordered_D_nm for c in col.cases]),feature_names=np.array(FEATURE_NAMES),features=features)
    src=[pin(p) for p in vars(provider).values() if isinstance(p,Path) and p.is_file()]+[pin(PROVIDER)]
    put('NP88D_FEATURE_PROVENANCE.json',{'status':'PASS','provider_id':module.PROVIDER_ID,'interface':module.INTERFACE_ID,'NP_HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=NP_ROOT,text=True).strip(),'provider_source_sha256':PROVIDER_SHA,'provider_provenance_hash':provider.provenance_hash,'source_artifacts':src,'feature_names':FEATURE_NAMES,'shape':[156,88],'dtype':'float64 storage; frozen provider complex64 DFT unchanged','features_sha256':A.sha(OUT/'NP88_FEATURES.npz'),'supports':supports,'legal_runtime_supported_count':156,'HF22_exact_matches':sum(s['hf22_empirical_support']['exact_hf22_match'] for s in supports),'warnings':provider.provenance_warnings,'semantics':'11 wavelengths x (7 tracked normalized DFT-order power fractions + T_proxy). T_proxy=eta_-1+eta_0+eta_+1; not absolute transmission or reflection. Position-index DFT retained; not a Jones/scattering operator.','HF_leakage':'No integrated labels or HF predictions enter features. HF22 manifest geometry-only support metadata is diagnostic, never input.','support':'100..230nm/5nm ordered6, normal P/XLIKE, 445..455 exact integers; no NP interpolation/extrapolation. Output HF440..460 does not extend NP validation.','independent_unknown_geometry_inference':True,'zero_source_solver':True})
    fby=dict(zip(ids,features));folds=[];parity=[];kernel=[]
    for fold,p,run in runs:
        tr=list(run.task.train_case_ids);va=list(run.prediction_case_ids)
        x=np.array([by[c].ordered_D_nm for c in tr],float);ft=np.array([fby[c] for c in tr]);s=BlockScaler(x,ft);gd,npd=s.blocks(x,ft);xb=s.transform(x,ft)
        k=rbf_kernel(xb,gamma=run.model.gamma);dg=euclidean_distances(gd,gd,squared=True);dn=euclidean_distances(npd,npd,squared=True);mask=np.triu(np.ones((124,124),bool),1)
        eigen=np.linalg.eigvalsh(k);alpha=run.model.ridge_alpha
        kernel.append({'fold':fold,'scaler':s.to_dict(),'training_feature_min':ft.min(0).tolist(),'training_feature_max':ft.max(0).tolist(),'training_feature_std':ft.std(0).tolist(),'standardized_NP_max_abs':float(np.max(np.abs((ft-s.mean)/s.scale))),'geometry_distance':V.summary(dg[mask]),'NP_distance':V.summary(dn[mask]),'NP_distance_fraction':V.summary(dn[mask]/(dg[mask]+dn[mask])),'kernel_offdiagonal':V.summary(k[mask]),'kernel_condition_number':float(np.linalg.cond(k)),'regularized_condition_number':float((eigen[-1]+alpha)/(eigen[0]+alpha)),'no_validation_response_used':True})
        folds.append({'fold':fold,'task_id':f'NP88_outer_{fold}','baseline_task_id':run.task.task_id,'train_case_ids':tr,'heldout_case_ids':va,'train_count':124,'heldout_count':len(va),'gamma':run.model.gamma,'ridge_alpha':alpha,'seed':None,'precision':'float64','baseline_artifacts':[pin(p/n) for n in ['fit.joblib','fit_manifest.json','predictions.npz']],'target_normalizer':run.target_scaler.to_dict()})
        parity.append({'fold':fold,'status':'EXACT','reused_baseline_model':str(p/'fit.joblib'),'reused_model_sha256':A.sha(p/'fit.joblib'),'train_target_scaler_exact':True,'train_geometry_scaler_exact':True,'reloaded_predictions_exact':True})
    put('MATCHED_OUTER_FOLD_MANIFEST.json',{'folds':folds,'baseline_reproduction_fits':0,'NP_fusion_fits':4,'total_new_logical_fits':4,'KRR_internal_head_fit_calls':8,'baseline':'reuse original124G refits exactly; outerconfig selected historically from124..126outertrain, no new search','validation_count':124,'old32':'train-only historically exposed','new65_twofit_authorization':'SUPERSEDED_NOT_EXECUTED'})
    put('GEOMETRY_ONLY_BASELINE_PARITY.json',{'status':'PASS','folds':parity,'new_baseline_fits':0})
    put('KERNEL_BLOCK_SCALING_AUDIT.json',{'rule':'x_B=[zD/sqrt(2),sqrt(6/88)*zF/sqrt(2)]; frozen gamma and alpha unchanged. Equivalent gamma_B=gamma_A/2 on [zD,sqrt(6/88)zF]; no scale trials. Standardized train blocks each nominal energy3, total6 (constant NP columns lower actual NP energy).','basis':'dimension balance only; equal block weighting predetermined, not tuned to response or validation','folds':kernel,'selection':'none'})
    put('ZERO_FIT_TESTS.json',tests())
    protected=[A.OUT/'FINAL_MODEL_AND_PREDICTION_FREEZE.json',A.OUT/'FINAL_RBF_KRR_SEALED_GEOMETRY_ONLY_PREDICTIONS.npz',A.OUT/'FINAL_CARTESIAN_MLP_SEALED_GEOMETRY_ONLY_PREDICTIONS.npz',A.OUT/'FIT_EXECUTION_LEDGER.json',Path(A.inventory()['ledger']['path'])]
    protected += [ROOT/'scripts/coupling_ml/k6_v2_pipeline'/n for n in ['contracts.py','models.py','h1.py']]
    protected += [ROOT/'scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py',ROOT/'reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json']
    put('PREREGISTRATION.json',{'utc_before_first_fit':utc(),'status':'FROZEN','authorized_fit_list':[q['task_id'] for q in folds],'actual_planned_fits':4,'scaling_rule':read('KERNEL_BLOCK_SCALING_AUDIT.json')['rule'],'bootstrap':{'unit':'complete geometry, pooled124 OOF','replicates':10000,'seed':8815601,'interval':'percentile2.5..97.5% for mean and median paired delta; descriptive only, not formal significance; folds correlated','within_fold_report':True},'spectral_bands':{'full':list(range(440,461)),'NP_supported':list(range(445,456)),'outside_low':list(range(440,445)),'outside_high':list(range(456,461))},'phase':'frozen1722nm physical reference; truth-weight significant mask>=1e-4, no oracle alignment; all order pairs same polarization. Derived phase diagnostics only.','verdict_rule':'State/routing gain if median paired delta<0 and pooledmedian andq95 decrease for both, improvement in>=3/4 fold median deltas, each>=62/124 geometry wins, and no new worst state exceeds A worst by>0.1. If only routing/power meets analogous directional rule then ROUTING_POWER_ONLY; finite validated results with neither consistent gain -> NO_CLEAR_GAIN; missing/invalid evidence -> INCONCLUSIVE. Descriptive rule not new H1 gate.','confirmation_responses':'SEALED_NO_ACCESS','frozen_H1_H2':True,'source_sha256':A.sha(Path(__file__)),'protected_files':[pin(p) for p in protected],'foreign_index_sha256':hashlib.sha256(git('diff','--cached','--binary')).hexdigest(),'initial_status_count':len(git('status','--short').decode().splitlines()),'runtime':{'python':sys.executable,'numpy':np.__version__,'sklearn':__import__('sklearn').__version__,'CPU_only':True}})
    put('FIT_LEDGER.json',{'fits':{q['task_id']:{'status':'PENDING','logical_fit_count':0} for q in folds},'maximum':4,'baseline_fits':0,'FDTD':0,'replay':0,'MLP_fits':0,'NP_MDC_retraining':0,'confirmation_response_access':0})
    (OUT/'CONTINUATION.md').write_bytes((f'# {TASK}\nRead PREREGISTRATION, NP88D_FEATURE_PROVENANCE, MATCHED_OUTER_FOLD_MANIFEST and FIT_LEDGER first. Prepared4NP KRR fits, original4A reused, no baseline fits, no confirmationresponse access. CPU interpreter {sys.executable}. Run module train only after PASS; an interrupted FITTING entry is not blindly refitted. Original65G2fit authorization superseded. No solver/MLP/local/residual.\n').encode())
    print('PREFLIGHT_PASS',len(ids),'features156x88; baseline4 exact; plannedfits4; provider warnings retained',flush=True)

def check_pins():
    pr=read('PREREGISTRATION.json');require(A.sha(Path(__file__))==pr['source_sha256'],'pilot_source_changed_after_freeze')
    for p in pr['protected_files']:require(A.sha(p['path'])==p['sha256'],'protected_file_changed:'+p['path'])
    for p in read('NP88D_FEATURE_PROVENANCE.json')['source_artifacts']:require(A.sha(p['path'])==p['sha256'],'provider_input_changed')
    require(A.sha(OUT/'NP88_FEATURES.npz')==read('NP88D_FEATURE_PROVENANCE.json')['features_sha256'],'feature_cache_changed')
    return pr

def train():
    check_pins();col=A.load_collection(False);by={c.case_id:c for c in col.cases}
    with np.load(OUT/'NP88_FEATURES.npz',allow_pickle=False) as z:fby=dict(zip(z['case_ids'].tolist(),z['features']))
    baselines={fold:run for fold,p,run in baseline_runs(col)};ledger=read('FIT_LEDGER.json')
    for t in read('MATCHED_OUTER_FOLD_MANIFEST.json')['folds']:
        row=ledger['fits'][t['task_id']];p=OUT/'models'/t['task_id'];p.mkdir(parents=True,exist_ok=True)
        if row['status']=='COMPLETE':
            require(A.sha(p/'model.joblib')==row['model_sha256'],'completed_model_changed');continue
        require(row['status']=='PENDING' and row['logical_fit_count']==0,'ambiguous_fit_do_not_replay')
        tr=t['train_case_ids'];va=t['heldout_case_ids'];base=baselines[t['fold']]
        x=np.array([by[c].ordered_D_nm for c in tr],float);f=np.array([fby[c] for c in tr]);s=BlockScaler(x,f)
        y=C.pack_model_target(np.array([by[c].c_hat for c in tr]),np.array([by[c].p_scale for c in tr]));yn=base.target_scaler.transform(y)
        xp=np.array([by[c].ordered_D_nm for c in va],float);fp=np.array([fby[c] for c in va]);xb=s.transform(x,f);xv=s.transform(xp,fp)
        row.update(status='FITTING',logical_fit_count=1,start_utc=utc(),internal_head_fit_calls=0);put('FIT_LEDGER.json',ledger);start=time.perf_counter()
        mc=KernelRidge(alpha=t['ridge_alpha'],kernel='rbf',gamma=t['gamma']).fit(xb,yn[:,:588]);row['internal_head_fit_calls']=1;put('FIT_LEDGER.json',ledger)
        mp=KernelRidge(alpha=t['ridge_alpha'],kernel='rbf',gamma=t['gamma']).fit(xb,yn[:,588:]);row['internal_head_fit_calls']=2;put('FIT_LEDGER.json',ledger)
        payload={'models':(mc,mp),'input_scaler':s,'target_scaler':base.target_scaler,'task':t,'preregistration_sha256':A.sha(OUT/'PREREGISTRATION.json'),'features_sha256':A.sha(OUT/'NP88_FEATURES.npz')}
        def predict(payload):return C.unpack_model_target(payload['target_scaler'].inverse_transform(np.concatenate([m.predict(payload['input_scaler'].transform(xp,fp)) for m in payload['models']],axis=1)))
        cp,pp=predict(payload);joblib.dump(payload,p/'model.joblib',compress=3);rc,rp=predict(joblib.load(p/'model.joblib'))
        require(np.array_equal(cp,rc) and np.array_equal(pp,rp),'model_reload_mismatch')
        np.savez_compressed(p/'predictions.npz',case_ids=np.array(va),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=pp)
        trainpred=np.concatenate([m.predict(xb) for m in (mc,mp)],axis=1)
        row.update(status='COMPLETE',end_utc=utc(),wall_seconds=time.perf_counter()-start,model_sha256=A.sha(p/'model.joblib'),prediction_sha256=A.sha(p/'predictions.npz'),reload_exact=True,normalized_train_loss=M.numpy_loss_components(trainpred,yn)[2]);put('FIT_LEDGER.json',ledger)
        put('models/'+t['task_id']+'/provenance.json',{'task':t,'fit_ledger':row,'input_scaler':s.to_dict(),'target_scaler_matches_A':True,'output_contract':C.MODEL_TARGET_LAYOUT,'training_ids':tr,'heldout_ids':va,'role':'development','heldout_response_in_fit':False})
        print('COMPLETE',t['task_id'],row['wall_seconds'],flush=True)
    require(sum(r['logical_fit_count'] for r in ledger['fits'].values())==4 and all(r['status']=='COMPLETE' for r in ledger['fits'].values()),'fit_budget')
    evaluate(col,baselines)

def bootstrap(delta):
    d=np.asarray(delta,float);rng=np.random.default_rng(8815601);draw=d[rng.integers(0,len(d),(10000,len(d)))]
    return {'mean_delta_CI95':np.quantile(draw.mean(1),[.025,.975]).tolist(),'median_delta_CI95':np.quantile(np.median(draw,1),[.025,.975]).tolist(),'descriptive_not_significance':True}

def evaluate(col=None,baselines=None):
    check_pins();col=col or A.load_collection(False);baselines=baselines or {f:run for f,p,run in baseline_runs(col)}
    by={c.case_id:c for c in col.cases};meta={q['case_id']:q for q in A.inventory()['cases']};folds=read('MATCHED_OUTER_FOLD_MANIFEST.json')['folds'];ids=sum([t['heldout_case_ids'] for t in folds],[])
    require(len(ids)==len(set(ids))==124,'OOF_ids');ct=np.array([by[c].c_hat for c in ids]);pt=np.array([by[c].p_scale for c in ids]);eta=np.array([by[c].eta for c in ids]);absolute=np.array([by[c].absolute_order for c in ids]);dec=h1.load_h2_decoder()
    cpA=np.concatenate([baselines[t['fold']].predicted_c_hat for t in folds]);ppA=np.concatenate([baselines[t['fold']].predicted_p_scale for t in folds]);cpB=[];ppB=[]
    for t in folds:
        p=OUT/'models'/t['task_id']/'predictions.npz';row=read('FIT_LEDGER.json')['fits'][t['task_id']];require(A.sha(p)==row['prediction_sha256'],'prediction_sha')
        with np.load(p,allow_pickle=False) as z:
            require(z['case_ids'].tolist()==t['heldout_case_ids'],'prediction_identity');cpB.append(z['C_hat_real']+1j*z['C_hat_imag']);ppB.append(z['P_scale'])
    cpB=np.concatenate(cpB);ppB=np.concatenate(ppB);reports={};diags={}
    for arm,cp,pp in [('A',cpA,ppA),('B',cpB,ppB)]:
        reports[arm]=h1.evaluate_original_h1(ct,cp,pt,pp,eta,absolute,dec);diags[arm]=V.diagnostics(ct,cp,ids,meta)
        np.savez_compressed(OUT/f'{arm}_OOF_PREDICTIONS.npz',case_ids=np.array(ids),C_hat_real=cp.real,C_hat_imag=cp.imag,P_scale=pp)
    frozen=A.read(A.OUT/'KRR_LEARNING_CURVE_RESULTS.json')['124'];require(reports['A']['aggregate']==frozen['aggregate'] and reports['A']['gates']==frozen['gates'],'full_A_evaluator_parity')
    parity=read('GEOMETRY_ONLY_BASELINE_PARITY.json');parity['full_aggregate_and_original_gates_exact']=True;put('GEOMETRY_ONLY_BASELINE_PARITY.json',parity)
    put('H1_H2_EVALUATION.json',reports);put('NP_FEATURE_KRR_RESULTS.json',{'A':reports['A']['aggregate'],'B':reports['B']['aggregate'],'original_gate_status':{a:r['gates'] for a,r in reports.items()},'fits':4,'baseline_fits':0,'no_independent_confirmation':True})
    put('STATE_NORM_AND_PHASE_DIAGNOSTIC.json',diags)
    paired={};fm={}
    for key in reports['A']['aggregate']['per_geometry'][0]:
        a=np.array([r[key] for r in reports['A']['aggregate']['per_geometry']]);b=np.array([r[key] for r in reports['B']['aggregate']['per_geometry']]);delta=b-a
        pf={}
        for t in folds:
            ix=[ids.index(c) for c in t['heldout_case_ids']];dd=delta[ix];pf[str(t['fold'])]={'count':len(ix),'delta':V.summary(dd),'wins':int((dd<0).sum()),'losses':int((dd>0).sum()),'ties':int((dd==0).sum())}
        paired[key]={'delta':V.summary(delta),'wins':int((delta<0).sum()),'losses':int((delta>0).sum()),'ties':int((delta==0).sum()),'bootstrap':bootstrap(delta),'folds':pf,'per_geometry':[{'case_id':cid,'fold':next(t['fold'] for t in folds if cid in t['heldout_case_ids']),'role':by[cid].role,'A':float(av),'B':float(bv),'delta':float(d)} for cid,av,bv,d in zip(ids,a,b,delta)]}
    put('PAIRED_GEOMETRY_ERROR_ANALYSIS.json',paired)
    metrics=h1._load(ROOT/'scripts/coupling_ml/pw_k6_stage1_32g_frozen_model_v1.py','np88_frozen_metric_functions',C.MODEL_SOURCE_SHA256)
    hd={a:h1.reconstruct_h2(cp,pp,dec) for a,cp,pp in [('A',cpA,ppA),('B',cpB,ppB)]};spectra={}
    for name,wls in read('PREREGISTRATION.json')['spectral_bands'].items():
        ix=np.array(wls)-440;entry={}
        for arm,cp,pp in [('A',cpA,ppA),('B',cpB,ppB)]:
            rows=[{'case_id':cid,**metrics.met(ct[k,ix],cp[k,ix],eta[k,ix],hd[arm]['eta'][k,ix],absolute[k,ix],hd[arm]['absolute_order'][k,ix],pt[k,ix],pp[k,ix])} for k,cid in enumerate(ids)]
            sq=abs(ct[:,ix])**2;mask=sq/sq.sum((2,3),keepdims=True)>=1e-4;phase=np.angle(cp[:,ix]*ct[:,ix].conj());den=(sq*mask).sum((1,2,3));phase_rmse=np.sqrt((sq*phase**2*mask).sum((1,2,3))/den)
            entry[arm]={'wavelength_nm':wls,'metrics':{k:V.summary([r[k] for r in rows]) for k in rows[0] if k!='case_id'},'per_geometry':rows,'truth_weighted_phase':V.summary(phase_rmse),'routing_pearson':h1._pear(eta[:,ix],hd[arm]['eta'][:,ix]),'total_power_pearson':h1._pear(pt[:,ix],pp[:,ix])}
        entry['paired']={key:{'delta':V.summary([b[key]-a[key] for a,b in zip(entry['A']['per_geometry'],entry['B']['per_geometry'])]),'wins':sum(b[key]<a[key] for a,b in zip(entry['A']['per_geometry'],entry['B']['per_geometry']))} for key in entry['A']['metrics']};spectra[name]=entry
    put('SPECTRAL_SUPPORT_DOMAIN_ANALYSIS.json',spectra)
    detailed={}
    for arm,cp,pp in [('A',cpA,ppA),('B',cpB,ppB)]:
        entries={}
        for name,orders in [('target_plus1',[4]),('other_nonzero',[0,1,2,5,6]),('zero',[3])]:
            a=ct[:,:,orders,:];b=cp[:,:,orders,:];sq=abs(a)**2;phase=np.angle(b*a.conj());mask=sq/sq.sum((2,3),keepdims=True)>=1e-4;den=(sq*mask).sum((1,2,3));nr=np.sqrt(abs(b-a).reshape(len(ids),-1).__pow__(2).sum(1)/sq.sum((1,2,3)))
            entries[name]={'state':V.summary(nr),'truth_weight_phase':V.summary(np.sqrt((sq*phase**2*mask).sum((1,2,3))/den)),'routing_RMSE':V.summary(np.sqrt(np.mean((eta[:,:,orders]-hd[arm]['eta'][:,:,orders])**2,(1,2)))),'absolute_RMSE':V.summary(np.sqrt(np.mean((absolute[:,:,orders]-hd[arm]['absolute_order'][:,:,orders])**2,(1,2))))}
        err=abs(cp-ct)**2;sq=abs(ct)**2
        entries['per_order_TE_TM']=[{'m':m,'polarization':pol,'global_relative_RMSE':float(np.sqrt(err[:,:,j,k].sum()/sq[:,:,j,k].sum())),'per_geometry_relative_RMSE':np.sqrt(err[:,:,j,k].sum(1)/sq[:,:,j,k].sum(1)).tolist(),'note':'TE tiny truth denominator; descriptive, not gate'} for j,m in enumerate(range(-3,4)) for k,pol in enumerate(['TE','TM'])]
        detailed[arm]=entries
    put('ORDER_POLARIZATION_DIAGNOSTIC.json',detailed)
    def gain(key):
        p=paired[key];ma=reports['A']['aggregate']['metrics'][key];mb=reports['B']['aggregate']['metrics'][key]
        return p['delta']['median']<0 and mb['median']<ma['median'] and mb['q95']<ma['q95'] and sum(q['delta']['median']<0 for q in p['folds'].values())>=3 and p['wins']>=62
    sg=gain('state_relative_rmse');rg=gain('routing_eta_rmse');pg=gain('total_power_relative_rmse') or gain('absolute_order_source_normalized_rmse')
    tail_ok=max(r['state_relative_rmse'] for r in reports['B']['aggregate']['per_geometry'])<=max(r['state_relative_rmse'] for r in reports['A']['aggregate']['per_geometry'])+.1
    verdict='NP_FUSION_STATE_AND_ROUTING_GAIN' if sg and rg and tail_ok else ('NP_FUSION_ROUTING_POWER_ONLY' if (rg or pg) and not sg else 'NP_FUSION_NO_CLEAR_GAIN')
    put('FINAL_SCIENTIFIC_VERDICT.json',{'verdict':verdict,'state_consistent_gain':sg,'routing_consistent_gain':rg,'power_consistent_gain':pg,'state_tail_rule_pass':tail_ok,'both_H1_pass':{a:r['all_applicable_numeric_gates_attained'] for a,r in reports.items()},'independent_confirmation':False,'production_admission':False,'note':'post-baseline matched development ablation; deterministic block choice, no new nested search'})
    check_pins()
    put('FINAL_ISOLATION_CHECK.json',{'status':'PASS','protected_inputs_and_confirmation_predictions_unchanged':True,'FDTD':0,'replay':0,'confirmation_response_access':0,'NP_MDC_retrain':0,'MLP_fits':0,'logical_CPU_KRR_fits':4,'internal_KRR_head_calls':8,'baseline_fits':0,'old65G_paired2':'SUPERSEDED_NOT_EXECUTED','synthetic_fits':0,'all_model_reloads_exact':True})
    table=['|Metric|A median/q95|B median/q95|wins/losses|paired median delta|','|---|---|---|---|---|']
    for key in paired:
        a=reports['A']['aggregate']['metrics'][key];b=reports['B']['aggregate']['metrics'][key];p=paired[key];table.append(f"|{key}|{a['median']:.6f}/{a['q95']:.6f}|{b['median']:.6f}/{b['q95']:.6f}|{p['wins']}/{p['losses']}|{p['delta']['median']:.6f}|")
    text='\n'.join(table);(OUT/'NUMERIC_COMPARISON.md').write_bytes((text+'\n').encode())
    report=f'# {TASK}\n\nSTATUS PASS; scientific verdict {verdict}. Four joint state/log-P CPU KRR fits (eight internal output-head solve calls), zero baseline refits, zero solver/replay/confirmation responses. Old65G pair authorization superseded.\n\n'+text+'\n\nA models and all124G heldout predictions are exact original baseline parity. Ordered input sixD and88NP power features. Same124train per fold and fixed heldouts32/31/30/31; old32 train-only historical exposure. Same target normalizer, label contract, gamma/alpha, float64, H1/H2. No new model selection or kernel-scale search.\n\nNP frozen single-pillar-DFT source supports ordered100..230/5nm and445..455/P/XLIKE; descriptors predict fullHF440..460 but do not validate NP outside band. Neither reflection/Jones nor same-reference complexLF exists; no residual. Support distance/HF22 membership diagnostic only. D180 historical setup-link warnings preserved; validated post-FSP and library result source remain bound.\n\n'+f"H1 A {reports['A']['gates']}; B {reports['B']['gates']}. No independent confirmation/production admission. P_scale/total equal by H2 definition, not two independent validations.\n\nState norm ratio median A {diags['A']['norm_ratio']['median']:.6f}, B {diags['B']['norm_ratio']['median']:.6f}; truth-weight phase median A {diags['A']['truth_weighted_phase_RMSE']['median']:.6f}, B {diags['B']['truth_weighted_phase_RMSE']['median']:.6f}; relativephase A {diags['A']['relative_phase_RMSE']['median']:.6f}, B {diags['B']['relative_phase_RMSE']['median']:.6f}. No alignment/rescaling/clipping.\n\n"+'Geometry paired bootstrap10000 seed8815601 descriptiveCI, no wavelength pseudo-replication/significance claims; nested/history-correlated folds limit inference. Full pergeometry, spectral bands, orders/TE/TM, +1/othernonzero, severe tails retained in JSON. Kernel audited train-only; equal block weighting fixed beforefits. Any benefit conflates additional physical nonlinear descriptors with altered metric, not causal proof of coupling physics.\n\nNEXT DO NOT EXECUTE: Chat review of matched pilot, prioritize state/phase representation and modal structure if fullstate gain fails; no automatic widerMLP, newHF, residual or confirmation.\n'
    (OUT/'FINAL_REPORT.md').write_bytes(report.encode())
    (OUT/'CONTINUATION.md').write_bytes((f'# {TASK} COMPLETE\nRestore FINAL_REPORT, FINAL_SCIENTIFIC_VERDICT, SHA_INVENTORY, FIT_LEDGER, PREREGISTRATION first.4/4NPfusion CPU fits,0baselinefits,0solver/replay/confirmation,old65G2superseded. Verdict {verdict}; originalH1/H2 preserved. All32confirmationresponses sealed and old28inputpredictions unchanged. Do not rerun fits or select newscale. Original156G268ledger unchanged. Exact taskcode/report commit only, preserve foreign index.\n').encode())
    print(text,flush=True);print('VERDICT',verdict,'NORM',diags['A']['norm_ratio'],diags['B']['norm_ratio'],flush=True)

if __name__=='__main__':
    os.environ['CUDA_VISIBLE_DEVICES']=''
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='train':train()
    elif sys.argv[1]=='evaluate':evaluate()
    else:raise ValueError('mode must be prepare/train/evaluate')
