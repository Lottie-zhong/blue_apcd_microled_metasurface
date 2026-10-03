"""Frozen-protocol G0 ordered periodic graph development POC; CPU-only, zero solver."""
import os,sys
os.environ['CUDA_VISIBLE_DEVICES']='-1'; os.environ['OMP_NUM_THREADS']='1'; os.environ['MKL_NUM_THREADS']='1'; os.environ['OPENBLAS_NUM_THREADS']='1'; os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
import json,hashlib,subprocess,importlib.util,random,statistics,datetime,csv,math
from pathlib import Path
import numpy as np
import torch
from torch import nn

ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
NAME='COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1'
OUT=ROOT/'reports'/'coupling'/NAME
TASK_REL='reports/coupling/'+NAME+'/'
START_HEAD='aeae982ecb555df1b38ab08173119408486a7b10'
BRANCH='work/mdc-np-coupling-ml-v1'
POC_DIR=ROOT/'reports'/'coupling'/'COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1'
POC_PATH=ROOT/'scripts'/'coupling_ml'/'coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py'
HYB_PATH=ROOT/'scripts'/'coupling_ml'/'coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py'
MODEL_PATH=OUT/'g0_ordered_periodic_model.py'
RUN_PATH=OUT/'g0_run.py'
EXPECTED_DIRTY_SHA=''
torch.set_num_threads(1)
assert torch.empty(0).device.type=='cpu' and not torch.cuda.is_available()


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def readj(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def atomic_json(path,obj):
    path=Path(path);tmp=Path(str(path)+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,path)
def atomic_npz(path,**arrays):
    path=Path(path);tmp=Path(str(path)+'.tmp.npz');np.savez_compressed(tmp,**arrays);os.replace(tmp,path)
def git(*args): return subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True,check=True).stdout.strip()
def loadmod(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path));mod=importlib.util.module_from_spec(spec);sys.modules[name]=mod;spec.loader.exec_module(mod);return mod
def req(ok,msg):
    if not ok: raise RuntimeError(msg)
def status_base():
    raw=subprocess.run(['git','-C',str(ROOT),'status','--porcelain=v1','-z','--untracked-files=all'],capture_output=True,check=True).stdout
    entries=[e for e in raw.split(b'\0') if e and not e[3:].replace(b'\\',b'/').startswith(TASK_REL.encode())]
    entries=sorted(entries)
    return {'count':len(entries),'sha256':hashlib.sha256(b'\0'.join(entries)).hexdigest()}
def verify_git(expected_head=None,baseline=None):
    req(git('branch','--show-current')==BRANCH,'branch changed')
    if expected_head:req(git('rev-parse','HEAD')==expected_head,'HEAD changed; inspect authority before proceeding')
    if baseline:req(status_base()==baseline,'pre-existing worktree status changed outside this task')

def load_authorities():
    poc=loadmod('g0_frozen_c0_poc',POC_PATH);hyb=loadmod('g0_frozen_h1_h2_audit',HYB_PATH)
    ctx=poc.load_context()
    return poc,hyb,ctx

def freeze_protocol():
    verify_git(START_HEAD)
    poc,hyb,ctx=load_authorities()
    OUT.mkdir(parents=True,exist_ok=True)
    m=loadmod('g0_periodic_model',MODEL_PATH)
    priordir=POC_DIR
    inputs=poc.context_hashes(ctx)
    review=ROOT/'reports'/'coupling'/'COUPLING_ML_COUPLING_REPOSITORY_ADAPTATION_REVIEW_V1'
    for p in [review/'CONTINUATION.md',review/'COUPLING_ML_COUPLING_REPOSITORY_ADAPTATION_REVIEW_V1.md',review/'adaptation_matrix.md',review/'data_physics_gaps.md',review/'recommendations.md',review/'evidence_index.json',POC_DIR/'protocol.json',POC_DIR/'results.json',POC_DIR/'oof_predictions.npz',POC_DIR/'CONTINUATION.md']:
        inputs[str(p.relative_to(ROOT))]=sha(p)
    inputs[str(MODEL_PATH.relative_to(ROOT))]=sha(MODEL_PATH)
    inputs[str(RUN_PATH.relative_to(ROOT))]=sha(RUN_PATH)
    baseline=status_base()
    geometry={'K':6,'ordered_slots':['D1','D2','D3','D4','D5','D6'],'diameter_sorting':False,'x_nm':m.X_NM.tolist(),'y_nm':[0.0]*6,'phase_origin_nm':[0.0,0.0],'period_nm':[1740.0,290.0],'pitch_nm':290.0,'x_periodic':True,'y_periodic':True,'z_boundary':'PML'}
    cfg={'candidate':'G0','purpose':'geometry-to-integrated-C_hat surrogate; not a Maxwell solver or validated MDC-NP feedback model','hidden_width':4,'message_rounds':3,'parameters':m.parameter_budget(),'input':'per physical node [outer-train-fitted C0 StandardScaler(D/130), x_nm/1740]; no learned positional scaler','edges':'directed left/right periodic ring, each with signed dx/1740 and integer periodic image shift; distinct learned left/right transforms','readout':'restore physical slots D1..D6, flatten 6x4 to 24, Linear(24,32), then exact C0 seven rank-2 heads and 14->32->14 residual fusion','output':'Cartesian 14 rank-2 PCA scores, inverse outer-train PCA to original C_hat schema (21,7,2 complex)','pca':'one independent rank-2 PCA per diffraction order, fit on outer train; inner validation PCA fit on inner train','loss':'mean squared standardized 14-score error; output scales are std(training scores), floor 1e-12; same C0 loss','optimizer':{'name':'AdamW','lr':0.002,'weight_decay':0.0001,'full_batch':True,'gradient_clip_norm':5.0},'initialization':'PyTorch default Linear initialization; Python/NumPy/PyTorch seeds reset to 0,1,2 before each fit; CPU only','early_stopping':{'inner_validation':'standardized latent MSE','max_epochs':320,'patience':45,'selected_final_epochs':'integer floor of median of 3 geometry-grouped inner best epochs','final_checkpoint':'refit from deterministic initialization on all 31 outer-train geometries for selected epoch count; no outer-test selection'},'folds':'existing frozen 32 geometry LOGO; all 21 wavelengths from held-out geometry remain together','seeds':[0,1,2],'inner_folds':'the exact 3 pre-existing geometry-grouped splits per outer fold','fit_budget':{'inner_fits':288,'final_fits':96,'total_fits':384,'max_optimizer_steps':122880,'max_epochs_per_fit':320,'no_extra_fits':True},'P_scale':'same frozen OOF RBF KRR predictions for C0, G0, and historical FULL; no refit','candidate_selection':'H1 gates first. If all candidates fail, call consistent gain only when G0-C0 paired geometry median and q95 deltas are negative and wins exceed losses for both state and routing, with no worsening in state/routing/relative-phase on S31, S33, EXT08 or any new overall worst. Central gains with tail worsening are mixed/tail deterioration; otherwise no clear gain. Descriptive development rule, not admission gate.','statistics':'geometry is paired unit; 32 geometries only; wavelengths and seeds are not independent replicates','forbidden':'no other model config, architecture search, NP features, residual, P_scale training, rank expansion, inverse search, solver, Runner, HF, or reserve'}
    protocol={'task':NAME,'status':'FROZEN_BEFORE_TRAINING','frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'start_head':START_HEAD,'branch':BRANCH,'zero_solver':True,'zero_c0_refit':True,'geometry_authority':geometry,'config':cfg,'folds_and_seeds':{'geometry_ids':ctx['ids'],'folds':ctx['folds'],'seeds':[0,1,2]},'input_sha256':inputs,'preexisting_worktree_status_excluding_this_task':baseline,'comparison':['G0 vs saved C0 seed OOF','G0 vs historical FULL seed OOF','same original H1/H2 and shared P_scale'],'evaluation':'frozen hybrid-audit H1/H2 implementation and original conjunctive gates; complex arithmetic seed mean','phase_diagnostics':'truth-amplitude-squared and prediction-amplitude-squared absolute-phase weights; existing common-phase-removed relative phase; oracle fields remain diagnostics only','leakage':'outer-fold PCA and geometry scaler use outer train only; inner PCA and scaler use inner train only; no wavelength/node/window random split'}
    atomic_json(OUT/'protocol.json',protocol)
    atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':'PROTOCOL_FROZEN','solver_invocations':0,'runner_invocations':0,'new_hf_invocations':0,'fit_invocations':0,'resume':'read CONTINUATION.md, protocol.json and checkpoint.json; run --preflight, --lock, then --train'})
    print('PROTOCOL_FROZEN',sha(OUT/'protocol.json'),json.dumps(baseline),flush=True)


def preflight():
    verify_git(START_HEAD)
    proto=readj(OUT/'protocol.json');verify_git(START_HEAD,proto['preexisting_worktree_status_excluding_this_task'])
    poc,hyb,ctx=load_authorities();m=loadmod('g0_periodic_model_preflight',MODEL_PATH)
    model_test=m.preflight()
    saved=np.load(POC_DIR/'oof_predictions.npz',allow_pickle=False)
    c0=np.asarray(saved['C0_seed'],complex);c0mean=np.asarray(saved['C0_mean'],complex)
    req(c0.shape==(3,32,21,7,2) and np.array_equal(c0mean,c0.mean(axis=0)),'saved C0 OOF prediction schema/mean mismatch')
    req(np.array_equal(saved['P_scale_predicted'],ctx['pred']['32g_pred_pscale']),'frozen P_scale branch mismatch')
    pc,ys=poc.build_c0_basis(poc.import_model(),ctx['c'],list(range(31)))
    enc=poc.c0_encode(poc.import_model(),ctx['c'],list(range(31)),pc);dec=poc.c0_decode(poc.import_model(),enc,pc)
    req(enc.shape==(31,14) and dec.shape==(31,21,7,2) and np.isfinite(dec.real).all() and np.isfinite(dec.imag).all(),'frozen Cartesian PCA encode/decode interface check failed')
    threshold=ctx['gate']['chart_numeric_authority']['thresholded_absolute_order_relative']['significance_threshold']
    data={'c':ctx['c'],'eta':ctx['eta'],'absolute':ctx['absolute'],'pscale':ctx['ps'],'pscale_pred':ctx['pred']['32g_pred_pscale'],'weights':ctx['weights']}
    c0_eval=hyb.evaluate_arm('C0',c0,c0mean,data,threshold,hyb.get_gate_values(ctx['gate']))
    prior=readj(POC_DIR/'results.json')['arms']['C0']['summary'];mapping={'state':'state','routing':'routing','absolute':'absolute','thresholded_relative':'thresholded_relative','pscale':'pscale'}
    parity={}
    for new,old in mapping.items():
        parity[new]={stat:abs(c0_eval['summary'][new][stat]-prior[old][stat]) for stat in ('median','q95','max')}
        req(max(parity[new].values())<=1e-10,'saved C0 frozen-evaluator parity failed for '+new)
    _,fac=hyb.build_h2_factor(ctx['decoder']);h2=hyb.h2_reconstruct(c0mean,data['pscale_pred'],fac)
    h2err=float(np.max(np.abs(h2['total']-data['pscale_pred'])))
    h1norm=ctx['weights'];h2norm=fac/fac[:,3,0][:,None,None]
    h2h1err=float(np.max(np.abs(h2norm[None,...]-h1norm[...,None])))
    req(h2err<=1e-12,'frozen H2 physical total-power closure failed')
    req(len(proto['folds_and_seeds']['folds'])==32 and all(len(f['inner_group_folds'])==3 for f in ctx['folds']),'frozen fold cardinality')
    report={'status':'PASS','zero_solver':True,'zero_training_before_lock':True,'C0_refits':0,'C0_OOF_shape':list(c0.shape),'C0_saved_prediction_hash':sha(POC_DIR/'oof_predictions.npz'),'C0_frozen_H1_summary_parity_abs_error':parity,'H2_total_power_closure_max_abs':h2err,'H2_vs_H1_modal_weight_max_abs_after_m0_normalization':h2h1err,'H2_absolute_m0_coefficient_by_wavelength':fac[:,3,0].tolist(),'graph_checks':model_test,'outer_folds':32,'seeds':[0,1,2],'inner_folds_per_outer':3,'outer_geometry_leakage':'none, verified by frozen loader','runtime':'CPU only','checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(OUT/'implementation_fix_log.json',{'issues':[{'issue':'initial H2-vs-H1 audit diagnostic compared arrays with incompatible geometry/polarization axes','cause':'the audit-only calculation omitted explicit axes','fix':'broadcast coefficient axes before comparison; no evaluator or prediction changed'},{'issue':'raw H2 coefficient values differ from H1 modal_weights','cause':'H1 modal_weights are normalized modal power ratios while H2 power_z_per_abs_e2 uses absolute wavelength-dependent units','fix':'normalize frozen H2 coefficients by the m=0 TE coefficient at each wavelength, then compare ratios; record the removed physical scale separately'}],'training_or_solver_invocations_before_fix':0,'science_path_changed':False})
    atomic_json(OUT/'pretraining_tests.json',report)
    print('PREFLIGHT_PASS',sha(OUT/'pretraining_tests.json'),flush=True)

def lock_training():
    verify_git(START_HEAD)
    proto=readj(OUT/'protocol.json');test=readj(OUT/'pretraining_tests.json')
    verify_git(START_HEAD,proto['preexisting_worktree_status_excluding_this_task'])
    req(test['status']=='PASS' and test['zero_training_before_lock'] and test['zero_solver'],'pretraining tests did not pass')
    req(proto['input_sha256'][str(MODEL_PATH.relative_to(ROOT))]==sha(MODEL_PATH),'model source changed after protocol freeze')
    req(proto['input_sha256'][str(RUN_PATH.relative_to(ROOT))]==sha(RUN_PATH),'runner source changed after protocol freeze')
    lock={'status':'TRAINING_LOCKED','protocol_sha256':sha(OUT/'protocol.json'),'pretraining_tests_sha256':sha(OUT/'pretraining_tests.json'),'model_sha256':sha(MODEL_PATH),'runner_sha256':sha(RUN_PATH),'start_head':START_HEAD,'preexisting_worktree_status_excluding_this_task':proto['preexisting_worktree_status_excluding_this_task'],'fit_budget':proto['config']['fit_budget'],'locked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    atomic_json(OUT/'training_lock.json',lock)
    atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':'TRAINING_LOCKED','solver_invocations':0,'runner_invocations':0,'new_hf_invocations':0,'fit_invocations':0,'resume':'run --train; completed inner fits and final folds are skipped'})
    print('TRAINING_LOCKED',sha(OUT/'training_lock.json'),flush=True)


def setseed(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
def lossfn(pred,target,scale): return torch.mean(((pred-target)/scale)**2)
def fitstop(x,y,xv,yv,seed):
    setseed(seed);m=loadmod('g0_fit_model',MODEL_PATH).OrderedPeriodicG0().cpu()
    req(sum(p.numel() for p in m.parameters())==2444,'G0 fit parameter count changed')
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    xt,yt,xvt,yvt=[torch.as_tensor(a,dtype=torch.float32,device='cpu') for a in (x,y,xv,yv)]
    sd=torch.as_tensor(np.maximum(np.std(y,axis=0),1e-12),dtype=torch.float32)
    best=float('inf');bestep=0;stale=0;executed=0
    for ep in range(1,321):
        executed=ep
        m.train();opt.zero_grad(set_to_none=True);lv=lossfn(m(xt),yt,sd);lv.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),5.);opt.step()
        m.eval()
        with torch.no_grad(): val=float(lossfn(m(xvt),yvt,sd).item())
        if val<best:best,bestep,stale=val,ep,0
        else:stale+=1
        if stale>=45:break
    req(bestep>0 and math.isfinite(best),'inner fit had no finite validation epoch')
    return bestep,best,executed

def fitfixed(x,y,xtest,seed,epochs):
    setseed(seed);mod=loadmod('g0_final_model',MODEL_PATH);m=mod.OrderedPeriodicG0().cpu()
    opt=torch.optim.AdamW(m.parameters(),lr=.002,weight_decay=.0001)
    x_t,y_t=[torch.as_tensor(a,dtype=torch.float32,device='cpu') for a in (x,y)]
    sd=torch.as_tensor(np.maximum(np.std(y,axis=0),1e-12),dtype=torch.float32)
    for _ in range(int(epochs)):
        m.train();opt.zero_grad(set_to_none=True);lv=lossfn(m(x_t),y_t,sd);lv.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),5.);opt.step()
    m.eval();xt=torch.as_tensor(xtest,dtype=torch.float32,device='cpu')
    with torch.no_grad():
        yhat=m(xt).numpy().astype(float);ytrain=m(x_t).numpy().astype(float);tloss=float(lossfn(torch.as_tensor(ytrain),y_t,sd).item())
    flat=np.concatenate([p.detach().cpu().numpy().reshape(-1) for p in m.parameters()]).astype(np.float32)
    req(flat.size==2444 and np.isfinite(yhat).all() and np.isfinite(flat).all(),'invalid final G0 output/checkpoint')
    return yhat,ytrain,tloss,flat

def train():
    verify_git(START_HEAD)
    proto=readj(OUT/'protocol.json');verify_git(START_HEAD,proto['preexisting_worktree_status_excluding_this_task']);lock=readj(OUT/'training_lock.json')
    req(lock['status']=='TRAINING_LOCKED' and lock['protocol_sha256']==sha(OUT/'protocol.json'),'training lock mismatch')
    req(lock['model_sha256']==sha(MODEL_PATH) and lock['runner_sha256']==sha(RUN_PATH),'training code changed after lock')
    req(proto['input_sha256'][str(MODEL_PATH.relative_to(ROOT))]==sha(MODEL_PATH),'model differs from frozen protocol')
    poc,hyb,ctx=load_authorities();M=poc.import_model();mgraph=loadmod('g0_graph_train',MODEL_PATH)
    req(torch.empty(0).device.type=='cpu' and not torch.cuda.is_available(),'training must remain CPU-only')
    ids=ctx['ids'];geo=ctx['geometry'];c=ctx['c'];idx={gid:i for i,gid in enumerate(ids)}
    shape=(3,32,21,7,2)
    sp=OUT/'g0_predictions_partial.npz';pp=OUT/'seed_progress.json'
    if sp.exists():
        old=np.load(sp,allow_pickle=False);pred=np.asarray(old['G0_seed'],complex);trainstate=np.asarray(old['train_state'],float);trainloss=np.asarray(old['train_latent_mse'],float);params=np.asarray(old['final_parameters'],np.float32)
    else:
        pred=np.full(shape,np.nan+1j*np.nan);trainstate=np.full((3,32,32),np.nan);trainloss=np.full((3,32),np.nan);params=np.full((3,32,2444),np.nan,np.float32)
    prog=readj(pp) if pp.exists() else {'inner_completed':{},'final_completed':{}}
    def checkpoint(phase,last=''):
        atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':phase,'protocol_sha256':sha(OUT/'protocol.json'),'solver_invocations':0,'runner_invocations':0,'new_hf_invocations':0,'model_fit_invocations':len(prog['inner_completed'])+len(prog['final_completed']),'inner_fits_completed':len(prog['inner_completed']),'final_fits_completed':len(prog['final_completed']),'total_inner_fits':288,'total_final_fits':96,'last_completed':last,'resume':'run --train; each completed inner validation fit and final outer fold is skipped'})
    checkpoint('TRAINING')
    for fi,fold in enumerate(ctx['folds']):
        testid=fold['test_geometry_id'];test=idx[testid];outer=[idx[g] for g in fold['train_geometry_ids']]
        inners=[([idx[g] for g in f['train_geometry_ids']],[idx[g] for g in f['validation_geometry_ids']]) for f in fold['inner_group_folds']]
        opcs,oy=poc.build_c0_basis(M,c,outer);xf,xouter=poc.input_x(M,geo,outer);xouter=mgraph.node_features(xouter)
        for si,seed in enumerate((0,1,2)):
            inner_epochs=[]
            for ii,(tr,va) in enumerate(inners):
                key=f'{fi}|{seed}|{ii}'
                if key in prog['inner_completed']:
                    rec=prog['inner_completed'][key]
                else:
                    ipcs,iy=poc.build_c0_basis(M,c,tr);iv=poc.c0_encode(M,c,va,ipcs)
                    xfm,xtr=poc.input_x(M,geo,tr);xv=xfm.transform(geo[va])
                    ep,vbest,executed=fitstop(mgraph.node_features(xtr),iy,mgraph.node_features(xv),iv,seed)
                    rec={'outer_fold':fi,'test_geometry_id':testid,'seed':seed,'inner_fold':ii,'best_epoch':int(ep),'epochs_executed':int(executed),'best_validation_standardized_latent_mse':float(vbest),'train_geometry_ids':[ids[j] for j in tr],'validation_geometry_ids':[ids[j] for j in va]}
                    prog['inner_completed'][key]=rec;atomic_json(pp,prog);checkpoint('TRAINING',key);print('INNER_COMPLETE',key,'epoch',ep,'val',f'{vbest:.8g}',flush=True)
                inner_epochs.append(int(rec['best_epoch']))
            fkey=f'{fi}|{seed}'
            if fkey in prog['final_completed']:
                continue
            epochs=int(statistics.median(inner_epochs))
            yhat,ytrain,tloss,flat=fitfixed(xouter,oy,mgraph.node_features(xf.transform(geo[[test]])),seed,epochs)
            out=poc.c0_decode(M,yhat,opcs)[0]
            trainout=poc.c0_decode(M,ytrain,opcs)
            req(np.isfinite(out.real).all() and np.isfinite(out.imag).all(),'non-finite G0 C_hat '+fkey)
            pred[si,test]=out;params[si,fi]=flat;trainloss[si,fi]=tloss
            trrows=[]
            for j,gidx in enumerate(outer):
                val=hyb.state_detail(c[gidx],trainout[j])['state'];trainstate[si,fi,gidx]=val;trrows.append(val)
            rec={'outer_fold':fi,'heldout_geometry_id':testid,'seed':seed,'selected_epochs':epochs,'inner_best_epochs':inner_epochs,'train_latent_mse':tloss,'train_state_median':float(np.median(trrows)),'train_state_q95':float(np.quantile(trrows,.95)),'train_geometry_ids':[ids[j] for j in outer],'heldout_geometry_ids':[testid],'checkpoint_parameter_count':int(flat.size),'basis':'outer-train-only 7 x rank-2 Cartesian PCA'}
            prog['final_completed'][fkey]=rec
            atomic_npz(sp,G0_seed=pred,train_state=trainstate,train_latent_mse=trainloss,final_parameters=params)
            atomic_json(pp,prog);checkpoint('TRAINING',fkey)
            print('FINAL_COMPLETE',fkey,'epochs',epochs,'train_latent_mse',f'{tloss:.8g}','state_train_med',f'{rec["train_state_median"]:.8g}',flush=True)
    req(len(prog['inner_completed'])==288 and len(prog['final_completed'])==96,'fit budget count incomplete')
    req(np.isfinite(pred.real).all() and np.isfinite(pred.imag).all() and np.isfinite(params).all(),'OOF predictions or final checkpoints incomplete')
    atomic_npz(OUT/'g0_predictions_partial.npz',G0_seed=pred,train_state=trainstate,train_latent_mse=trainloss,final_parameters=params)
    atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':'TRAINING_COMPLETE','protocol_sha256':sha(OUT/'protocol.json'),'solver_invocations':0,'runner_invocations':0,'new_hf_invocations':0,'inner_fits_completed':288,'final_fits_completed':96,'total_model_fits':384,'optimizer_step_upper_bound':122880,'resume':'read CONTINUATION.md; predictions and fit provenance are complete'})
    finalize()


def metric_attribution(label,prediction,data,ids,threshold,hyb):
    perwl=[];perorder=[]
    rows,eta,absp=hyb.h1_metrics(data['c'],prediction,data['eta'],data['absolute'],data['pscale'],data['pscale_pred'],data['weights'],threshold)
    for gi,gid in enumerate(ids):
        for wi,wl in enumerate(range(440,461)):
            sd=hyb.state_detail(data['c'][gi,wi],prediction[gi,wi])
            mask=data['absolute'][gi,wi]>=threshold
            perwl.append({'model':label,'case_id':gid,'wavelength_nm':wl,**sd,'routing_rmse':float(np.sqrt(np.mean((eta[gi,wi]-data['eta'][gi,wi])**2))),'absolute_order_rmse':float(np.sqrt(np.mean((absp[gi,wi]-data['absolute'][gi,wi])**2))),'thresholded_relative_median':float(np.median(np.abs(absp[gi,wi][mask]-data['absolute'][gi,wi][mask])/np.maximum(data['absolute'][gi,wi][mask],1e-30))) if np.any(mask) else 0.0})
        for oi,order in enumerate(range(-3,4)):
            sd=hyb.state_detail(data['c'][gi,:,oi,:],prediction[gi,:,oi,:])
            mask=data['absolute'][gi,:,oi]>=threshold
            perorder.append({'model':label,'case_id':gid,'order_m':order,**sd,'routing_rmse':float(np.sqrt(np.mean((eta[gi,:,oi]-data['eta'][gi,:,oi])**2))),'absolute_order_rmse':float(np.sqrt(np.mean((absp[gi,:,oi]-data['absolute'][gi,:,oi])**2))),'thresholded_relative_median':float(np.median(np.abs(absp[gi,:,oi][mask]-data['absolute'][gi,:,oi][mask])/np.maximum(data['absolute'][gi,:,oi][mask],1e-30))) if np.any(mask) else 0.0})
    return perwl,perorder


def write_csv(path,rows):
    if not rows:return
    with Path(path).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def finalize():
    proto=readj(OUT/'protocol.json');verify_git(START_HEAD,proto['preexisting_worktree_status_excluding_this_task'])
    poc,hyb,ctx=load_authorities();saved=np.load(OUT/'g0_predictions_partial.npz',allow_pickle=False)
    g0=np.asarray(saved['G0_seed'],complex);trst=np.asarray(saved['train_state'],float);trloss=np.asarray(saved['train_latent_mse'],float);params=np.asarray(saved['final_parameters'],float)
    c0z=np.load(POC_DIR/'oof_predictions.npz',allow_pickle=False);c0=np.asarray(c0z['C0_seed'],complex);full=np.asarray(ctx['pred']['32g_pred_c_hat_seed'],complex);pcommon=np.asarray(ctx['pred']['32g_pred_pscale'],float)
    req(g0.shape==c0.shape==full.shape==(3,32,21,7,2),'prediction shape mismatch')
    threshold=ctx['gate']['chart_numeric_authority']['thresholded_absolute_order_relative']['significance_threshold']
    data={'c':ctx['c'],'eta':ctx['eta'],'absolute':ctx['absolute'],'pscale':ctx['ps'],'pscale_pred':pcommon,'weights':ctx['weights']}
    arms={};predictions={'G0':g0,'C0':c0,'HISTORICAL_FULL':full}
    perwls=[];perorders=[]
    for label,seedpred in predictions.items():
        mean=seedpred.mean(axis=0)
        arm=hyb.evaluate_arm(label,seedpred,mean,data,threshold,hyb.get_gate_values(ctx['gate']))
        for j,row in enumerate(arm['per_geometry']):row['case_id']=ctx['ids'][j]
        arms[label]=arm
        wlrows,orows=metric_attribution(label,mean,data,ctx['ids'],threshold,hyb);perwls.extend(wlrows);perorders.extend(orows)
    paired=hyb.paired_deltas(arms,[('G0','C0'),('G0','HISTORICAL_FULL'),('C0','HISTORICAL_FULL')])
    # Check the historical saved C0 metrics against the reused evaluator before interpreting G0.
    prior=readj(POC_DIR/'results.json')['arms']['C0']['summary'];c0par={}
    for k,old in [('state','state'),('routing','routing'),('absolute','absolute'),('thresholded_relative','thresholded_relative'),('pscale','pscale')]:
        c0par[k]={s:float(arms['C0']['summary'][k][s]-prior[old][s]) for s in ('median','q95','max')}
    req(max(abs(v) for d in c0par.values() for v in d.values())<=1e-10,'C0 parity changed after training')
    summaries={label:arm['summary'] for label,arm in arms.items()}
    pergeom=[]
    for label,arm in arms.items():
        for row in arm['per_geometry']:
            pergeom.append({'model':label,**row})
    seedrows=[]
    for label,arm in arms.items():
        for seed,entry in arm['per_seed'].items():seedrows.append({'model':label,'seed':int(seed),'routing_pearson':entry['routing_pearson'],'pscale_pearson':entry['pscale_pearson'],**{k:v['median'] for k,v in entry['metrics'].items()}})
    _,factors=hyb.build_h2_factor(ctx['decoder']);h2rows=[]
    for label,cpseed in predictions.items():
        for si,seed in enumerate((0,1,2)):
            rec=hyb.h2_reconstruct(cpseed[si],pcommon,factors)
            _,eta_before,_=hyb.h1_metrics(ctx['c'],cpseed[si],ctx['eta'],ctx['absolute'],ctx['ps'],pcommon,ctx['weights'],threshold)
            h2rows.append({'model':label,'seed':seed,'total_power_closure_max_abs':float(np.max(np.abs(rec['total']-pcommon))),'routing_vs_original_H1_max_abs':float(np.max(np.abs(rec['eta']-eta_before))),'scale_min':float(np.min(rec['scale'])),'scale_max':float(np.max(rec['scale']))})
        mean=cpseed.mean(axis=0);rec=hyb.h2_reconstruct(mean,pcommon,factors)
        _,eta_before,_=hyb.h1_metrics(ctx['c'],mean,ctx['eta'],ctx['absolute'],ctx['ps'],pcommon,ctx['weights'],threshold)
        h2rows.append({'model':label+'_complex_seed_mean','seed':'mean','total_power_closure_max_abs':float(np.max(np.abs(rec['total']-pcommon))),'routing_vs_original_H1_max_abs':float(np.max(np.abs(rec['eta']-eta_before))),'scale_min':float(np.min(rec['scale'])),'scale_max':float(np.max(rec['scale']))})
    focus=[gid for gid in ctx['ids'] if any(gid.endswith(s) for s in ('S31','S33','EXT08'))]
    by={(r['model'],r['case_id']):r for r in pergeom}
    tail={gid:{label:by[(label,gid)] for label in arms} for gid in focus}
    worst={}
    for label,arm in arms.items():
        worst[label]={}
        for metric in ('state','amplitude','phase_weighted_rmse_rad','relative_phase_truth_weighted_rmse_rad','routing','absolute','thresholded_relative','pscale'):
            row=max(arm['per_geometry'],key=lambda r:r[metric]);worst[label][metric]={'case_id':ctx['ids'][int(row['case_id'])] if row['case_id'].isdigit() else row['case_id'],'value':row[metric]}
    chosen=paired['G0_minus_C0'];primary=[]
    for k in ('state','routing'):
        d=chosen[k];primary.append(d['delta']['median']<0 and d['delta']['q95']<0 and d['wins']>d['losses'])
    focus_no_worse=all(by[('G0',gid)][metric] <= by[('C0',gid)][metric]+1e-12 for gid in focus for metric in ('state','routing','relative_phase_truth_weighted_rmse_rad'))
    overall_no_worse=all(worst['G0'][metric]['value']<=worst['C0'][metric]['value']+1e-12 for metric in ('state','routing','relative_phase_truth_weighted_rmse_rad'))
    if all(all(v for v in a['gates'].values()) for a in arms.values()):classification='GATES_ATTAINED_POST_HOC_DEVELOPMENT_ONLY'
    elif all(primary) and focus_no_worse and overall_no_worse:classification='CONSISTENT_HELDOUT_GAIN'
    elif any(chosen[k]['delta']['median']<0 for k in ('state','routing','phase_weighted_rmse_rad','relative_phase_truth_weighted_rmse_rad')):classification='MIXED_OR_TAIL_DETERIORATION'
    else:classification='NO_CLEAR_HELDOUT_GAIN'
    trvals=trst[np.isfinite(trst)];tlvals=trloss[np.isfinite(trloss)]
    def dist(a):
        a=np.asarray(a,float);return {'count':int(a.size),'median':float(np.median(a)),'q95':float(np.quantile(a,.95)),'worst':float(np.max(a))}
    perwl=perwls;perorder=perorders
    worstwl=max((r for r in perwl if r['model']=='G0'),key=lambda r:r['state'])
    worstorder=max((r for r in perorder if r['model']=='G0'),key=lambda r:r['state'])
    result={'task':NAME,'development_classification':classification,'posthoc_development_poc':True,'zero_solver':True,'zero_c0_refit':True,'parameter_count':2444,'C0_parameter_count':2684,'P_scale_branch':'frozen identical OOF RBF KRR; no new fit','arms':arms,'paired_geometry_deltas':paired,'C0_frozen_metric_parity_abs_delta':c0par,'tail_geometry_ids':focus,'tail_attribution':tail,'worst_by_metric':worst,'new_worst_G0_within_order_wavelength':{'wavelength':worstwl,'order':worstorder},'training_vs_heldout':{'G0_in_sample_state_across_fold_seed_geometry_examples':dist(trvals),'G0_final_fit_standardized_latent_mse':dist(tlvals),'G0_oof_complex_seed_mean_state':arms['G0']['summary']['state'],'note':'Training examples repeat across outer fits and are descriptive, not independent. Saved C0 in-sample fits were not recomputed.'},'fit_budget':{'inner_completed':288,'final_completed':96,'total':384,'optimizer_step_upper_bound':122880,'actual_optimizer_steps':int(sum(r['epochs_executed'] for r in readj(OUT/'seed_progress.json')['inner_completed'].values())+sum(r['selected_epochs'] for r in readj(OUT/'seed_progress.json')['final_completed'].values()))},'phase_weighting':'amplitude, truth-amplitude-squared absolute phase, prediction-amplitude-squared absolute phase, circular phase and cross-order relative phase are reported by the frozen evaluator. Weight changes do not by themselves imply phase skill changes. Oracle common-phase fields are diagnostic only.','original_H1_all_conjunctive':{label:{'H1':a['H1'],'gates':a['gates']} for label,a in arms.items()},'tails_include_new_worst_geometry_order_wavelength':True}
    atomic_json(OUT/'results.json',result)
    atomic_npz(OUT/'oof_predictions.npz',G0_seed=g0,G0_complex_seed_mean=g0.mean(axis=0),C0_seed=c0,C0_complex_seed_mean=c0.mean(axis=0),HISTORICAL_FULL_seed=full,HISTORICAL_FULL_complex_seed_mean=full.mean(axis=0),P_scale_predicted=pcommon)
    write_csv(OUT/'per_geometry.csv',pergeom);write_csv(OUT/'per_wavelength.csv',perwl);write_csv(OUT/'per_order.csv',perorder);write_csv(OUT/'seed_metrics.csv',seedrows);write_csv(OUT/'h2_reconstruction.csv',h2rows)
    # Continuation and audit are durable before Git operations.
    cont=f'''# {NAME}\n\nRead this file first, then protocol.json, training_lock.json, checkpoint.json, seed_progress.json, results.json, audit.json, and artifact_hashes.json before resuming.\n\nRemote: DESKTOP-NNE313K / dell. Formal worktree: `D:\\project\\worktrees\\blue_apcd_mdc_np_coupling_ml_v1`; canonical root: `D:\\project\\blue_apcd_microled_metasurface`; branch `{BRANCH}`. Start HEAD `{START_HEAD}`.\n\nRecovery script: `reports/coupling/{NAME}/g0_run.py`. Runtime is `N:\\anaconda_envs\\RCP_LCP\\python.exe` with CUDA disabled. Protocol was frozen before training; the graph preflight and C0 evaluator parity are in `pretraining_tests.json`.\n\nScope: one offline G0 ordered periodic graph candidate, 288 grouped inner fits plus 96 outer refits maximum. C0 predictions are reused from the frozen amplitude/circular-phase POC. P_scale is the same frozen OOF RBF KRR. ZERO SOLVER, ZERO FDTD/GPU Runner/HF/reserve/inverse-search/platform work.\n\nCurrent phase: {result['development_classification']}. Training and held-out summaries are in `results.json`; full paired metrics, attribution, checkpoints and predictions are in CSV/NPZ/JSON artifacts. This is a development POC, not an independent geometry confirmation or production admission. Do not change width, rounds, edges, loss, rank, seeds or add candidates.\n\nCommit/push status is recorded in `audit.json`. Stop at science review.\n'''
    (OUT/'CONTINUATION.md').write_text(cont,encoding='utf-8')
    audit={'task':NAME,'status':'COMPLETE_DEVELOPMENT_POC','start_head':START_HEAD,'branch':BRANCH,'zero_solver':True,'zero_fdt_gpu_runner_new_hf_reserve_inverse_search_platform_development':True,'zero_c0_refit':True,'new_candidate_fits':384,'maximum_optimizer_steps':122880,'actual_optimizer_steps':result['fit_budget']['actual_optimizer_steps'],'pretraining_test_sha256':sha(OUT/'pretraining_tests.json'),'protocol_sha256':sha(OUT/'protocol.json'),'training_lock_sha256':sha(OUT/'training_lock.json'),'input_sha256':proto['input_sha256'],'baseline_worktree_status_excluding_task':proto['preexisting_worktree_status_excluding_this_task'],'leakage_audit':{'outer_geometry_LOGO':32,'wavelengths_per_geometry':21,'inner_geometry_grouped_folds_per_outer':3,'outer_heldout_absent_from_inner_splits':True,'PCA_and_scalers_fit_outer_train_or_inner_train_only':True,'random_wavelength_node_patch_split':False,'C0_fit_invocations':0,'P_scale_fit_invocations':0,'heldout_truth_used_for_structure_or_epoch_selection':False},'h1_authority':'original frozen conjunctive gates; all failures retained','h2_authority':'frozen deterministic H2; C_hat plus same predicted P_scale; no projection or renormalization outside H2','warnings':[],'final_artifacts_exclude_hash_manifest_self_hash':True}
    atomic_json(OUT/'audit.json',audit)
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'}
    atomic_json(OUT/'artifact_hashes.json',hashes)
    report=f'''# {NAME} — results\n\nStatus: {classification}. Offline development comparison only; not independent confirmation or production admission. ZERO SOLVER and ZERO C0/P_scale refits.\n\nG0 has 2444 trainable parameters versus C0's 2684. The frozen original evaluator reports C0 H1 parity max absolute delta `{max(abs(v) for d in c0par.values() for v in d.values()):.3g}`. Paired geometry deltas and win/loss are in `results.json`; geometry is the pairing unit.\n\nG0 state median/q95/worst: `{arms['G0']['summary']['state']['median']:.6g}` / `{arms['G0']['summary']['state']['q95']:.6g}` / `{arms['G0']['summary']['state']['worst']:.6g}`. C0: `{arms['C0']['summary']['state']['median']:.6g}` / `{arms['C0']['summary']['state']['q95']:.6g}` / `{arms['C0']['summary']['state']['worst']:.6g}`. Routing median G0/C0: `{arms['G0']['summary']['routing']['median']:.6g}` / `{arms['C0']['summary']['routing']['median']:.6g}`. P_scale median/q95 remains `{arms['G0']['summary']['pscale']['median']:.6g}` / `{arms['G0']['summary']['pscale']['q95']:.6g}` for all arms. See `results.json` for original gates and phase-weighting definitions, and `per_geometry.csv`, `per_wavelength.csv`, `per_order.csv`, `seed_metrics.csv`, `h2_reconstruction.csv` for full details.\n\nTraining-fit state median/q95/worst across repeated outer-fold train examples: `{dist(trvals)}`; G0 OOF complex-seed-mean state median/q95/worst: `{arms['G0']['summary']['state']}`. Repeated training entries are descriptive, not independent.\n\nS31/S33/EXT08 and new worst geometry/order/wavelength are in `results.json`. Shared P_scale keeps its original failing gate. No next experiment was executed.\n'''
    (OUT/f'{NAME}.md').write_text(report,encoding='utf-8')
    # Update the manifest after all other output files exist.
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'}
    atomic_json(OUT/'artifact_hashes.json',hashes)
    atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':'COMPLETE','protocol_sha256':sha(OUT/'protocol.json'),'solver_invocations':0,'runner_invocations':0,'new_hf_invocations':0,'model_fit_invocations':384,'inner_fits_completed':288,'final_fits_completed':96,'optimizer_step_upper_bound':122880,'actual_optimizer_steps':result['fit_budget']['actual_optimizer_steps'],'development_classification':classification,'resume':'read CONTINUATION.md then results/audit/artifact hashes; task complete'})
    # Rebuild artifact hashes with terminal checkpoint state.
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json'}
    atomic_json(OUT/'artifact_hashes.json',hashes)
    print('FINALIZED',classification,'results_sha',sha(OUT/'results.json'),'artifacts',len(hashes),flush=True)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['freeze','preflight','lock','train','finalize']);phase=ap.parse_args().phase
    {'freeze':freeze_protocol,'preflight':preflight,'lock':lock_training,'train':train,'finalize':finalize}[phase]()
