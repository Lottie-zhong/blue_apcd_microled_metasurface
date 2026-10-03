"""Two-config, CPU-only 32G amplitude/circular-phase LOGO POC; no solver interfaces."""
from __future__ import annotations
import os,sys,json,hashlib,subprocess,statistics,random,csv,datetime,importlib.util,math
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='-1';os.environ['OMP_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
import numpy as np
import torch
from torch import nn
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

ROOT=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
NAME='COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1'
OUT=ROOT/'reports'/'coupling'/NAME
BASE=ROOT/'reports'/'coupling'/'PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1'
PREV=ROOT/'reports'/'coupling'/'COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1'
V2=ROOT/'reports'/'coupling'/'COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2'
MODEL_PATH=ROOT/'scripts'/'coupling_ml'/'pw_k6_stage1_32g_frozen_model_v1.py'
TEST_PATH=ROOT/'tests'/'coupling'/'test_amplitude_circular_phase_forward_poc_v1.py'
TEST_REPORT_PATH=OUT/'pretraining_tests.json'
FOLD_SHA='4a2c40339f58073e46f9e830d5b619bd620f6ab26091c8a3961c532f000a944a'
MODEL_SHA='919471fce7d9d324947c9dfa4fc63e1ae7384061195f174d943879a745d6712f'
DATA_SHA='fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28'
PRED_SHA='68c78cb437cdde8e222fd12aee323f906c8501cf5777bcfdcf5a49f6d24044a0'
H1_SHA='8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd'
H2_SHA='b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15'
SEEDS=(0,1,2);WL=tuple(range(440,461));ORD=tuple(range(-3,4));THRESH_WEAK=.01;EPS_PHASE=1e-8
torch.set_num_threads(1)
assert torch.empty(0).device.type=='cpu' and not torch.cuda.is_available(),'CPU-only device mask failed.'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def atomic_json(p,x):
 t=Path(str(p)+'.tmp');t.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8');os.replace(t,p)
def req(x,msg):
 if not x:raise RuntimeError(msg)
def git(*args):return subprocess.run(['git','-C',str(ROOT),*args],capture_output=True,text=True,check=True).stdout.strip()
def import_model():
 s=importlib.util.spec_from_file_location('frozen_m5_model',MODEL_PATH);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def pack_order(c,o):
 q=c[:,:,o,:];return np.stack([q[...,0].real,q[...,1].real,q[...,0].imag,q[...,1].imag],axis=-1).reshape(len(c),-1)
def unpack_order(x,n):
 q=x.reshape(n,21,4);return np.stack([q[...,0]+1j*q[...,2],q[...,1]+1j*q[...,3]],axis=-1)
def pack_geometry(x):return np.stack([x.real,x.imag],axis=-1).reshape(len(x),-1)
def unpack_geometry(x,shape):
 q=x.reshape(*shape,2);return q[...,0]+1j*q[...,1]
def weak_mask(c):
 amp=np.abs(c);peak=np.max(amp,axis=(-2,-1),keepdims=True)
 return amp<=THRESH_WEAK*np.maximum(peak,1e-30)
def unit_safe_torch(v,eps=EPS_PHASE):
 mag=torch.abs(v);good=mag>=eps
 return torch.where(good,v/mag.clamp_min(eps),torch.ones_like(v))

class C1Basis:
 def __init__(self):self.amp=[];self.phase=[];self.amp_ref=None;self.amp_loss_scale=None;self.c_scale=None;self.y_mean=None;self.y_scale=None
 def fit(self,c,indices):
  tr=c[indices];a=np.abs(tr);weak=weak_mask(tr);u=np.ones_like(tr);u[~weak]=tr[~weak]/a[~weak]
  self.amp_ref=max(float(np.mean(a)),1e-12)
  lg=np.log1p(a/self.amp_ref);self.amp_loss_scale=max(float(np.std(lg)),1e-6)
  self.c_scale=max(float(np.mean(a*a)**.5),1e-12)
  targets=[]
  for o in range(7):
   af=lg[:,:,o,:].reshape(len(tr),-1)
   pf=np.concatenate([u[:,:,o,:].real.reshape(len(tr),-1),u[:,:,o,:].imag.reshape(len(tr),-1)],axis=1)
   pa=PCA(n_components=2,svd_solver='full').fit(af);pp=PCA(n_components=2,svd_solver='full').fit(pf)
   self.amp.append(pa);self.phase.append(pp)
   targets.extend([pa.transform(af),pp.transform(pf)])
  y=np.concatenate(targets,axis=1);sc=StandardScaler().fit(y)
  self.y_mean=sc.mean_;self.y_scale=np.maximum(sc.scale_,1e-12)
  return self
 def encode(self,c):
  y=[]
  for o in range(7):
   a=np.abs(c);weak=weak_mask(c);u=np.ones_like(c);u[~weak]=c[~weak]/a[~weak]
   lg=np.log1p(a[:,:,o,:]/self.amp_ref).reshape(len(c),-1)
   pf=np.concatenate([u[:,:,o,:].real.reshape(len(c),-1),u[:,:,o,:].imag.reshape(len(c),-1)],axis=1)
   y.extend([self.amp[o].transform(lg),self.phase[o].transform(pf)])
  return (np.concatenate(y,axis=1)-self.y_mean)/self.y_scale
 def _inverse_torch(self,score,pca):
  comp=torch.as_tensor(pca.components_,dtype=score.dtype);mean=torch.as_tensor(pca.mean_,dtype=score.dtype)
  return score@comp+mean
 def decode_torch(self,y):
  raw=y*torch.as_tensor(self.y_scale,dtype=y.dtype)+torch.as_tensor(self.y_mean,dtype=y.dtype)
  aa=[];uu=[];k=0
  for o in range(7):
   alog=self._inverse_torch(raw[:,k:k+2],self.amp[o]).reshape(-1,21,2);k+=2
   # 50 is a floating-point overflow guard, not a fitted target or tunable parameter.
   alog=torch.clamp(alog,min=0.,max=50.);aa.append(self.amp_ref*torch.expm1(alog))
   pv=self._inverse_torch(raw[:,k:k+2],self.phase[o]);k+=2
   vr=pv[:,:42].reshape(-1,21,2);vi=pv[:,42:].reshape(-1,21,2)
   uu.append(unit_safe_torch(torch.complex(vr,vi)))
  return torch.stack(aa,dim=2).to(torch.complex64)*torch.stack(uu,dim=2)
 def decode_numpy(self,y):
  with torch.no_grad():return self.decode_torch(torch.as_tensor(y,dtype=torch.float32)).cpu().numpy().astype(np.complex128)

class C1Net(nn.Module):
 def __init__(self):
  super().__init__();self.enc=nn.Sequential(nn.Linear(6,32),nn.ReLU(),nn.Linear(32,32),nn.ReLU())
  self.heads=nn.ModuleList([nn.Linear(32,4) for _ in range(7)])
  self.fuse=nn.Sequential(nn.Linear(28,32),nn.ReLU(),nn.Linear(32,28))
 def forward(self,x):
  q=self.enc(x);local=torch.cat([h(q) for h in self.heads],dim=1);return local+self.fuse(local)

def c1_loss(yp,yt,basis,ct):
 pred=basis.decode_torch(yp);truth=torch.as_tensor(ct,dtype=torch.complex64)
 latent=torch.mean((yp-yt)**2)
 amp=np.abs(ct);tr_amp=torch.as_tensor(amp,dtype=torch.float32)
 lg=torch.log1p(tr_amp/basis.amp_ref);pa=torch.abs(pred)
 amp_loss=torch.mean(((torch.log1p(pa/basis.amp_ref)-lg)/basis.amp_loss_scale)**2)
 weak=torch.as_tensor(weak_mask(ct),dtype=torch.bool)
 phase_loss=circular_phase_loss(pred,truth,weak)
 cs=torch.as_tensor(basis.c_scale**2,dtype=torch.float32).clamp_min(1e-12)
 complex_loss=torch.mean(torch.abs(pred-truth)**2)/cs
 total=latent+amp_loss+phase_loss+complex_loss
 return total,(latent,amp_loss,phase_loss,complex_loss)

def circular_phase_loss(predicted_complex,truth_complex,weak):
 weak=torch.as_tensor(weak,dtype=torch.bool)
 truth_amp=torch.abs(truth_complex)
 unit_truth=torch.where(weak,torch.ones_like(truth_complex),truth_complex/truth_amp.clamp_min(1e-30))
 unit_pred=unit_safe_torch(predicted_complex)
 phase_weight=(~weak).to(torch.float32)
 circular=(1.0-torch.real(unit_pred*torch.conj(unit_truth)))*phase_weight
 return circular.sum()/phase_weight.sum().clamp_min(1.0)

def fit_c1(Xtr,Ytr,Ctr,Xv,Yv,Cv,basis,seed,max_epochs=320,patience=45,return_epochs=False):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);model=C1Net().cpu();assert all(p.device.type=='cpu' for p in model.parameters());assert sum(p.numel() for p in model.parameters())==4056
 opt=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001)
 xt,yt,xv,yv=[torch.as_tensor(z,dtype=torch.float32,device='cpu') for z in (Xtr,Ytr,Xv,Yv)]
 best=float('inf');bestep=0;stale=0
 for ep in range(1,max_epochs+1):
  model.train();opt.zero_grad(set_to_none=True);pred=model(xt);loss,_=c1_loss(pred,yt,basis,Ctr);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.);opt.step()
  model.eval()
  # Shared C0/C1 stopping criterion: inner-validation standardized latent MSE.
  # Phase loss weights are therefore derived exclusively from inner-training truth.
  with torch.no_grad():val=torch.mean((model(xv)-yv)**2).item()
  if val<best:
   best,bestep,stale=val,ep,0
  else:stale+=1
  if stale>=patience:break
 req(bestep>0 and math.isfinite(best),'C1 early stop did not find finite validation loss')
 if return_epochs:return bestep,{'best_validation_loss':best,'epochs_run':ep}
 return bestep

def fit_c1_fixed(X,Y,C,seed,epochs,basis,xtest):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);model=C1Net().cpu();assert all(p.device.type=='cpu' for p in model.parameters());assert sum(p.numel() for p in model.parameters())==4056
 opt=torch.optim.AdamW(model.parameters(),lr=.002,weight_decay=.0001)
 xt,yt=torch.as_tensor(X,dtype=torch.float32,device='cpu'),torch.as_tensor(Y,dtype=torch.float32,device='cpu')
 for _ in range(int(epochs)):
  model.train();opt.zero_grad(set_to_none=True);loss,_=c1_loss(model(xt),yt,basis,C);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5.);opt.step()
 model.eval()
 with torch.no_grad():return basis.decode_numpy(model(torch.as_tensor(xtest,dtype=torch.float32)).numpy())

def save_npz(path,**arrays):
 tmp=Path(str(path)+'.tmp.npz');np.savez_compressed(tmp,**arrays);os.replace(tmp,path)
def summarize(a):
 a=np.asarray(a,float);mx=float(np.max(a));return {'median':float(np.median(a)),'q95':float(np.quantile(a,.95)),'max':mx,'worst':mx,'min':float(np.min(a))}
def state_detail(t,p):
 at=np.abs(t);ap=np.abs(p);se=np.abs(p-t)**2;ampse=(ap-at)**2;phse=np.maximum(se-ampse,0.)
 den=max(float(np.sum(at**2)),1e-30);weak=weak_mask(t);dphi=np.angle(p*np.conj(t));wt=at**2
 magw=at*ap;cs=np.sum(magw*np.exp(1j*dphi),axis=(-2,-1));common=np.angle(cs)
 dr=np.angle(np.exp(1j*(dphi-common[...,None,None])))
 aligned=p*np.exp(-1j*common[...,None,None]);aligned_sse=float(np.sum(np.abs(aligned-t)**2));state_sse=float(np.sum(se))
 strong=~weak
 return {'state':float(np.sqrt(np.sum(se)/den)),'amplitude':float(np.sqrt(np.sum(ampse)/den)),
  'amplitude_sse_fraction':float(np.sum(ampse)/max(np.sum(se),1e-30)),
  'phase_sse_fraction':float(np.sum(phse)/max(np.sum(se),1e-30)),
  'phase_weighted_rmse_rad':float(np.sqrt(np.sum(wt*dphi**2)/max(np.sum(wt),1e-30))),
  'circular_phase_chord_rmse':float(np.sqrt(np.sum(wt*2.0*(1.0-np.cos(dphi)))/max(np.sum(wt),1e-30))),
  'strong_phase_rmse_rad':float(np.sqrt(np.sum(wt*dphi**2*strong)/max(np.sum(wt*strong),1e-30))),
  'weak_coordinate_fraction':float(np.mean(weak)),'weak_truth_energy_fraction':float(np.sum(wt*weak)/den),
  'relative_phase_rmse_rad':float(np.sqrt(np.sum(magw*dr**2)/max(np.sum(magw),1e-30))),
  'oracle_common_phase_rmse_rad':float(np.sqrt(np.sum(wt*common[...,None,None]**2)/max(np.sum(wt),1e-30))),
  'oracle_common_phase_aligned_state':float(np.sqrt(aligned_sse/den)),
  'oracle_common_phase_explained_sse_fraction':float((state_sse-aligned_sse)/max(state_sse,1e-30))}
def h1_metrics(ct,cp,eta_t,abs_t,ps_t,ps_p,weights,threshold):
 modal=weights*np.sum(np.abs(cp)**2,axis=-1);eta_p=modal/np.maximum(modal.sum(axis=-1,keepdims=True),1e-30)
 abs_p=eta_p*ps_p[...,None]
 rows=[]
 for g in range(len(ct)):
  st=state_detail(ct[g],cp[g]);mask=abs_t[g]>=threshold
  rows.append({**st,'routing':float(np.sqrt(np.mean((eta_p[g]-eta_t[g])**2))),
   'absolute':float(np.sqrt(np.mean((abs_p[g]-abs_t[g])**2))),
   'thresholded_relative':float(np.median(np.abs(abs_p[g][mask]-abs_t[g][mask])/np.maximum(abs_t[g][mask],1e-30))),
   'pscale':float(np.sqrt(np.mean(((ps_p[g]-ps_t[g])/np.maximum(ps_t[g],1e-30))**2)))})
 return rows,eta_p,abs_p
def summarize_rows(rows):
 return {k:summarize([r[k] for r in rows]) for k in rows[0]}

def attribution_rows(label,ct,cp,eta_t,abs_t,ps_t,ps_p,weights,threshold,ids,wavelengths):
 modal=weights*np.sum(np.abs(cp)**2,axis=-1);eta_p=modal/np.maximum(modal.sum(axis=-1,keepdims=True),1e-30);abs_p=eta_p*ps_p[...,None]
 per_wl=[];per_order=[]
 for g,gid in enumerate(ids):
  for wi,wl in enumerate(wavelengths):
   truth=ct[g,wi];pred=cp[g,wi];se=np.abs(pred-truth)**2;power=np.abs(truth)**2
   mask=abs_t[g,wi]>=threshold
   per_wl.append({'model':label,'case_id':gid,'wavelength_nm':int(wl),
    'state_relative_rmse':float(np.sqrt(se.sum()/max(power.sum(),1e-30))),
    'routing_eta_rmse':float(np.sqrt(np.mean((eta_p[g,wi]-eta_t[g,wi])**2))),
    'absolute_order_rmse':float(np.sqrt(np.mean((abs_p[g,wi]-abs_t[g,wi])**2))),
    'thresholded_absolute_relative_median':float(np.median(np.abs(abs_p[g,wi,mask]-abs_t[g,wi,mask])/np.maximum(abs_t[g,wi,mask],1e-30))) if np.any(mask) else float('nan'),
    'pscale_relative_abs_error':float(abs(ps_p[g,wi]-ps_t[g,wi])/max(ps_t[g,wi],1e-30))})
  for oi,order in enumerate(ORD):
   oer=np.abs(cp[g,:,oi,:]-ct[g,:,oi,:])**2;op=np.abs(ct[g,:,oi,:])**2
   per_order.append({'model':label,'case_id':gid,'order_m':order,
    'state_relative_rmse':float(np.sqrt(oer.sum()/max(op.sum(),1e-30))),
    'routing_eta_rmse':float(np.sqrt(np.mean((eta_p[g,:,oi]-eta_t[g,:,oi])**2))),
    'absolute_order_rmse':float(np.sqrt(np.mean((abs_p[g,:,oi]-abs_t[g,:,oi])**2))),
    'absolute_order_mean_abs_error':float(np.mean(np.abs(abs_p[g,:,oi]-abs_t[g,:,oi])))})
 return per_wl,per_order
def load_context():
 req(git('branch','--show-current')=='work/mdc-np-coupling-ml-v1','wrong work branch')
 authority=read(BASE/'PW_K6_32G_DATASET_AUTHORITY_V1.json');ah=read(BASE/'artifact_hashes.json')
 req(sha(BASE/'artifact_hashes.json')=='c19ba975817bde9ea09f0b42ffb09fb16eec11b67adc5bb06e933f43ef8edc03','32G artifact manifest changed')
 req(sha(BASE/'dataset_truth_32g.npz')==DATA_SHA and ah['oof_predictions_20g_32g.npz']==PRED_SHA,'data/prediction hash')
 req(sha(MODEL_PATH)==MODEL_SHA and sha(V2/'fold_manifest_v2.json')==FOLD_SHA,'frozen model/fold changed')
 req(authority['geometry_count']==32 and authority['wavelengths_nm']==list(WL),'32G geometry authority')
 gatep=ROOT/'reports'/'coupling'/'PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json';decoder=ROOT/'scripts'/'shared_fdtd'/'tools'/'pw_complex_floquet_state_v1.py'
 req(sha(gatep)==H1_SHA and sha(decoder)==H2_SHA,'frozen H1/H2 hash')
 z=np.load(BASE/'dataset_truth_32g.npz',allow_pickle=False);pred=np.load(BASE/'oof_predictions_20g_32g.npz',allow_pickle=False)
 ids=z['case_ids'].tolist();folds=read(V2/'fold_manifest_v2.json')['fold_assignments']['folds']
 req(len(ids)==32 and z['C_hat'].shape==(32,21,7,2) and [f['test_geometry_id'] for f in folds]==ids and pred['case_ids'].tolist()==ids and authority['ordered_geometry_ids']==ids,'ordered data/folds')
 for f in folds:
  req(set(f['train_geometry_ids'])==set(ids)-{f['test_geometry_id']},'outer fold leakage')
  for inner in f['inner_group_folds']:
   req(not(set(inner['train_geometry_ids'])&set(inner['validation_geometry_ids'])) and f['test_geometry_id'] not in inner['train_geometry_ids']+inner['validation_geometry_ids'],'inner fold leakage')
 dam=read(PREV/'artifact_hashes.json');dh=next((v for k,v in dam.items() if k.lower().endswith('\\results.json')),None)
 req(dh==sha(PREV/'results.json') and read(PREV/'audit.json')['ZERO_SOLVER'] is True,'diagnostic authority hash/status')
 c=np.asarray(z['C_hat'],complex);weights=np.asarray(z['modal_weights'],float)
 req(np.isfinite(c.real).all() and np.isfinite(c.imag).all() and np.allclose(pred['P_scale_truth_32g'],z['P_scale']),'truth/scale parity')
 return {'ids':ids,'geometry':z['ordered_D_nm'].astype(float),'c':c,'ps':z['P_scale'].astype(float),'eta':z['eta'].astype(float),'absolute':z['absolute_order_power'].astype(float),'weights':weights,'pred':pred,'folds':folds,'authority':authority,'gate':read(gatep),'decoder':decoder}
def context_hashes(ctx):
 ps=[BASE/'artifact_hashes.json',BASE/'dataset_truth_32g.npz',BASE/'oof_predictions_20g_32g.npz',BASE/'PW_K6_FROZEN_FORWARD_H1_32G_V1.json',ROOT/'reports'/'coupling'/'PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json',MODEL_PATH,V2/'fold_manifest_v2.json',PREV/'CONTINUATION.md',PREV/'protocol.json',PREV/'checkpoint.json',PREV/'results.json',PREV/'audit.json',PREV/'artifact_hashes.json',ctx['decoder'],TEST_PATH,TEST_REPORT_PATH]
 return {str(p.relative_to(ROOT)):sha(p) for p in ps}

def build_c0_basis(M,c,idx):
 pcs=[];scores=[]
 for o in range(7):
  pc=PCA(n_components=2,svd_solver='full').fit(pack_order(c[idx],o));pcs.append(pc);scores.append(pc.transform(pack_order(c[idx],o)))
 return pcs,np.concatenate(scores,axis=1)
def c0_encode(M,c,idx,pcs):return np.concatenate([pcs[o].transform(pack_order(c[idx],o)) for o in range(7)],axis=1)
def c0_decode(M,y,pcs):return M.decode(y,pcs)
def input_x(M,x,idx):
 xf=M.Xform().fit(x[idx]);return xf,xf.transform(x[idx])
def pca_record(c0,c1):
 return {'c0_order_rank2_explained_variance_ratio':[p.explained_variance_ratio_.tolist() for p in c0],
  'c1_amplitude_rank2_explained_variance_ratio':[p.explained_variance_ratio_.tolist() for p in c1.amp],
  'c1_phase_rank2_explained_variance_ratio':[p.explained_variance_ratio_.tolist() for p in c1.phase],
  'c1_amp_reference':c1.amp_ref,'c1_amp_loss_scale':c1.amp_loss_scale,'c1_complex_loss_scale':c1.c_scale,
  'c1_latent_mean':c1.y_mean.tolist(),'c1_latent_scale':c1.y_scale.tolist()}

def train():
 ctx=load_context();O=OUT;O.mkdir(parents=True,exist_ok=True)
 proto=read(O/'protocol.json');req(proto['input_sha256']==context_hashes(ctx),'frozen POC inputs changed')
 M=import_model();ids=ctx['ids'];c=ctx['c'];geo=ctx['geometry'];fidx={x:i for i,x in enumerate(ids)}
 ptrue=ctx['ps'];pcommon=ctx['pred']['32g_pred_pscale'];req(np.array_equal(pcommon,ctx['pred']['32g_pred_pscale']),'shared predicted scale')
 shape=(3,32,21,7,2);statepath=O/'predictions_partial.npz';progressp=O/'seed_progress.json'
 if statepath.exists():
  old=np.load(statepath,allow_pickle=False);pred0=old['C0'];pred1=old['C1']
 else:pred0=np.full(shape,np.nan+1j*np.nan);pred1=np.full(shape,np.nan+1j*np.nan)
 progress=read(progressp) if progressp.exists() else {'completed':{},'inner_logs':{},'outer_pca':{}}
 atomic_json(O/'checkpoint.json',{'task':NAME,'phase':'TRAINING','protocol_sha256':sha(O/'protocol.json'),'solver_invocations':0,'runner_invocations':0,'completed_seed_fits':len(progress['completed']),'total_seed_fits':192,'resume':'rerun the preregistered script; completed config/fold/seed predictions are loaded and skipped'})
 for fi,fold in enumerate(ctx['folds']):
  testid=fold['test_geometry_id'];test=fidx[testid];outer=[fidx[x] for x in fold['train_geometry_ids']]
  inners=[([fidx[x] for x in s['train_geometry_ids']],[fidx[x] for x in s['validation_geometry_ids']]) for s in fold['inner_group_folds']]
  # Fit fold-local targets only on the outer training geometries.
  pcs,y0=build_c0_basis(M,c,outer);b1=C1Basis().fit(c,outer);y1=b1.encode(c[outer]);xf,xo=input_x(M,geo,outer)
  progress['outer_pca'][testid]=pca_record(pcs,b1)
  for si,seed in enumerate(SEEDS):
   for config in ['C0','C1']:
    key=f'{config}|{testid}|{seed}'
    if key in progress['completed']:continue
    inner_best=[];inner_eval=[]
    for tr,va in inners:
     xfm,xtr=input_x(M,geo,tr);xv=xfm.transform(geo[va])
     if config=='C0':
      ip,iy=build_c0_basis(M,c,tr);iv=c0_encode(M,c,va,ip)
      ep=M.fitstop(xtr,iy,xv,iv,seed);inner_best.append(int(ep));inner_eval.append({'best_epoch':int(ep)})
     else:
      ib=C1Basis().fit(c,tr);iy=ib.encode(c[tr]);iv=ib.encode(c[va])
      ep,ev=fit_c1(xtr,iy,c[tr],xv,iv,c[va],ib,seed,return_epochs=True)
      inner_best.append(int(ep));inner_eval.append({'best_epoch':int(ep),**ev})
    epochs=int(statistics.median(inner_best))
    if config=='C0':
     yhat=M.fitfixed(xo,y0,xf.transform(geo[[test]]),seed,epochs)
     out=c0_decode(M,yhat,pcs)[0]
    else:
     yhat=b1.encode(c[outer]);out=fit_c1_fixed(xo,yhat,c[outer],seed,epochs,b1,xf.transform(geo[[test]]))[0]
    req(np.isfinite(out.real).all() and np.isfinite(out.imag).all(),'nonfinite state prediction '+key)
    if config=='C0':pred0[si,test]=out
    else:pred1[si,test]=out
    progress['completed'][key]={'outer_fold':fi+1,'heldout_geometry':testid,'seed':seed,'selected_epochs':epochs,'inner_folds':inner_eval,'basis':progress['outer_pca'][testid]}
    save_npz(statepath,C0=pred0,C1=pred1)
    atomic_json(progressp,progress)
    atomic_json(O/'checkpoint.json',{'task':NAME,'phase':'TRAINING','protocol_sha256':sha(O/'protocol.json'),'solver_invocations':0,'runner_invocations':0,'completed_seed_fits':len(progress['completed']),'total_seed_fits':192,'last_completed':key,'resume':'rerun script; completed config/fold/seed fits are loaded and skipped'})
    print('COMPLETED',key,'epochs',epochs,flush=True)
 req(np.isfinite(pred0.real).all() and np.isfinite(pred1.real).all(),'some C0/C1 OOF fits are incomplete')
 # Evaluate every model using original frozen H1 definitions; no oracle values enter predictions.
 preds={'C0':pred0,'C1':pred1,'HISTORICAL_FULL':ctx['pred']['32g_pred_c_hat_seed']}
 pmodels={'C0':pcommon,'C1':pcommon,'HISTORICAL_FULL':pcommon}
 results={};geometries=[];seeds_report={};shared_scale={};threshold=ctx['gate']['chart_numeric_authority']['thresholded_absolute_order_relative']['significance_threshold']
 for label,seeds in preds.items():
  mean=seeds.mean(axis=0);per,eta,absord=h1_metrics(c,mean,ctx['eta'],ctx['absolute'],ptrue,pcommon,ctx['weights'],threshold)
  medseed=[]
  for si,seed in enumerate(SEEDS):
   rows,_,_=h1_metrics(c,seeds[si],ctx['eta'],ctx['absolute'],ptrue,pcommon,ctx['weights'],threshold)
   seeds_report[f'{label}_seed{seed}']=summarize_rows(rows);medseed.append(summarize_rows(rows)['state']['median'])
  summ=summarize_rows(per);rho_route=float(np.corrcoef(ctx['eta'].ravel(),eta.ravel())[0,1]);rho_ps=float(np.corrcoef(ptrue.ravel(),pcommon.ravel())[0,1]);seedstd=float(np.std(medseed))
  lim=ctx['gate']['chart_numeric_authority'];gates={
   'state':summ['state']['median']<=lim['state_relative_rmse']['median_max'] and summ['state']['q95']<=lim['state_relative_rmse']['q95_max'],
   'routing':summ['routing']['median']<=lim['routing_eta_rmse']['median_max'] and summ['routing']['q95']<=lim['routing_eta_rmse']['q95_max'] and rho_route>=lim['routing_eta_rmse']['pearson_min'],
   'absolute':summ['absolute']['median']<=lim['absolute_order_source_normalized_rmse']['median_max'] and summ['absolute']['q95']<=lim['absolute_order_source_normalized_rmse']['q95_max'],
   'thresholded':summ['thresholded_relative']['median']<=lim['thresholded_absolute_order_relative']['median_max'] and summ['thresholded_relative']['q95']<=lim['thresholded_absolute_order_relative']['q95_max'],
   'total_power':summ['pscale']['median']<=lim['total_power_relative']['median_max'] and summ['pscale']['q95']<=lim['total_power_relative']['q95_max'] and rho_ps>=lim['total_power_relative']['pearson_min'],
   'seed_stability':seedstd<=lim['seed_state_median_std_max']}
  results[label]={'summary':summ,'routing_pearson':rho_route,'pscale_pearson':rho_ps,'seed_state_medians':medseed,'seed_state_median_std':seedstd,'gates':gates,'H1':'PASS' if all(gates.values()) else 'FAIL'}
  for i,gid in enumerate(ids):geometries.append({'model':label,'case_id':gid,**per[i]})
 # Verify that the copied original H1 metric path recovers its frozen summary.
 frozen=read(BASE/'PW_K6_FROZEN_FORWARD_H1_32G_V1.json')['metrics']
 mapkeys={'state':'state_relative_rmse','routing':'routing_eta_rmse','absolute':'absolute_order_source_normalized_rmse','thresholded_relative':'thresholded_absolute_order_relative_median','pscale':'total_power_relative_rmse'}
 for metric,oldkey in mapkeys.items():
  for stat in ['median','q95','max']:
   req(abs(results['HISTORICAL_FULL']['summary'][metric][stat]-frozen[oldkey][stat])<=1e-12,'historical FULL metric parity '+metric+'/'+stat)
 # Same P_scale makes state-branch-only comparison direct; physical H2 reconstructed separately.
 for label,ss in preds.items():
  mean=ss.mean(axis=0);rows,_,_=h1_metrics(c,mean,ctx['eta'],ctx['absolute'],ptrue,pcommon,ctx['weights'],threshold)
  shared_scale[label]=summarize_rows(rows)
 # Lossless polar round-trip uses true phases even at weak nonzero coordinates;
 # the frozen +1 weak-label rule is only used for fit targets/losses.
 amp=np.abs(c);utruth=np.ones_like(c);nz=amp>0;utruth[nz]=c[nz]/amp[nz]
 polarrt=amp*utruth
 req(float(np.max(abs(polarrt-c)))<=1e-12,'uncompressed polar round trip failed')
 polar_roundtrip={'max_abs_complex_error':float(np.max(abs(polarrt-c))),'coordinates':int(c.size),'weak_nonzero_count':int(np.sum(weak_mask(c)&nz)),'weak_phase_label_rule_applies_to_training_only':True}
 # Compression ceilings are held-out truth projections through outer-train-only bases (ORACLE ceilings).
 ceilings=[]
 for i,fold in enumerate(ctx['folds']):
  test=fidx[fold['test_geometry_id']];outer=[fidx[x] for x in fold['train_geometry_ids']]
  pcs,_=build_c0_basis(M,c,outer);c0ceil=c0_decode(M,c0_encode(M,c,[test],pcs),pcs)[0]
  b1=C1Basis().fit(c,outer);c1ceil=b1.decode_numpy(b1.encode(c[[test]]))[0]
  weak=weak_mask(c[[test]])[0];u0=np.ones_like(c[test]);nz0=np.abs(c[test])>0;u0[nz0]=c[test][nz0]/np.abs(c[test][nz0]);uweak=u0.copy();uweak[weak]=1+0j
  weakfill=np.abs(c[test])*uweak
  ceilings.append({'case_id':ids[test],'C0':state_detail(c[test],c0ceil),'C1':state_detail(c[test],c1ceil),'C1_weak_rule_only':state_detail(c[test],weakfill),'weak_nonzero_count':int(np.sum(weak&nz0))})
 # Fixed decoder reconstruction: the exact frozen H2 power coefficients set physical scale to shared predicted P_scale.
 spec=importlib.util.spec_from_file_location('frozen_H2_poc',ctx['decoder']);h2=importlib.util.module_from_spec(spec);sys.modules[spec.name]=h2;spec.loader.exec_module(h2)
 factor=np.asarray([[[h2._mode(m,0,float(wl),1.,1,p)['power_z_per_abs_e2'] for p in ('TE','TM')] for m in ORD] for wl in WL],float)
 ref_order_power=np.sum(factor[None,...]*np.abs(c)**2,axis=-1);rt_order_power=np.sum(factor[None,...]*np.abs(polarrt)**2,axis=-1)
 ref_total=ref_order_power.sum(axis=-1);rt_total=rt_order_power.sum(axis=-1)
 ref_eta=ref_order_power/np.maximum(ref_total[...,None],1e-30);rt_eta=rt_order_power/np.maximum(rt_total[...,None],1e-30)
 h2_roundtrip={'max_abs_order_power_error':float(np.max(np.abs(rt_order_power-ref_order_power))),
  'max_abs_routing_error':float(np.max(np.abs(rt_eta-ref_eta))),
  'max_abs_total_power_error':float(np.max(np.abs(rt_total-ref_total))),
  'max_relative_total_power_error':float(np.max(np.abs(rt_total-ref_total)/np.maximum(ref_total,1e-30))),
  'tolerance':1e-12,'decoder_sha256':H2_SHA}
 req(h2_roundtrip['max_abs_order_power_error']<=1e-12 and h2_roundtrip['max_abs_routing_error']<=1e-12 and h2_roundtrip['max_abs_total_power_error']<=1e-12,'frozen H2 polar round-trip preservation failed')
 h2rows=[]
 for label,ss in preds.items():
  for seedix in range(3):
   cp=ss[seedix];norm=np.sum(factor[None,...]*np.abs(cp)**2,axis=(-2,-1));sc=np.sqrt(pcommon/np.maximum(norm,1e-30));physical=cp*sc[...,None,None]
   order_power=np.sum(factor[None,...]*np.abs(physical)**2,axis=-1);total=order_power.sum(axis=-1)
   before=np.sum(factor[None,...]*np.abs(cp)**2,axis=-1);before_total=before.sum(axis=-1);before_eta=before/np.maximum(before_total[...,None],1e-30)
   after_eta=order_power/np.maximum(total[...,None],1e-30)
   h2rows.append({'model':label,'seed':SEEDS[seedix],
    'max_abs_order_power_vs_shared_scale_routing':float(np.max(np.abs(order_power-before_eta*pcommon[...,None]))),
    'max_abs_routing_preservation_error':float(np.max(np.abs(after_eta-before_eta))),
    'max_abs_total_power_closure':float(np.max(abs(total-pcommon))),
    'max_relative_total_power_closure':float(np.max(abs(total-pcommon)/np.maximum(pcommon,1e-30))),
    'physical_scale_min':float(np.min(sc)),'physical_scale_max':float(np.max(sc))})
 # Summarize paired geometry effects; geometry is the unit, not wavelength/seed replication.
 by={(r['model'],r['case_id']):r for r in geometries};paired={}
 for cand,base in [('C1','C0'),('C0','HISTORICAL_FULL'),('C1','HISTORICAL_FULL')]:
  paired[f'{cand}_minus_{base}']={}
  for metric in ['state','amplitude','phase_sse_fraction','phase_weighted_rmse_rad','circular_phase_chord_rmse','relative_phase_rmse_rad','routing','absolute','thresholded_relative','pscale']:
   d=[by[(cand,g)][metric]-by[(base,g)][metric] for g in ids]
   paired[f'{cand}_minus_{base}'][metric]={'delta':summarize(d),'wins':sum(x<0 for x in d),'ties':sum(x==0 for x in d),'losses':sum(x>0 for x in d)}
 tails={}
 for gid in ['K6V1_S31','K6V1_S33','K6V1_EXT08']:
  tails[gid]={label:by[(label,gid)] for label in preds}
 # Persist all seed predictions plus fold and metric provenance.
 save_npz(OUT/'oof_predictions.npz',C0_seed=pred0,C0_mean=pred0.mean(axis=0),C1_seed=pred1,C1_mean=pred1.mean(axis=0),FULL_seed=preds['HISTORICAL_FULL'],P_scale_predicted=pcommon)
 wavelength_rows=[];order_rows=[]
 for label,seeds in preds.items():
  wlrows,orows=attribution_rows(label,c,seeds.mean(axis=0),ctx['eta'],ctx['absolute'],ptrue,pcommon,ctx['weights'],threshold,ids,WL)
  wavelength_rows.extend(wlrows);order_rows.extend(orows)
 def writecsv(path,rows):
  with Path(path).open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 writecsv(OUT/'per_geometry.csv',geometries)
 writecsv(OUT/'compression_ceilings.csv',ceilings)
 writecsv(OUT/'h2_reconstruction.csv',h2rows)
 writecsv(OUT/'per_wavelength.csv',wavelength_rows)
 writecsv(OUT/'per_order.csv',order_rows)
 summaries={'status':'COMPLETE_OFFLINE_POC','arms':results,'polar_roundtrip':polar_roundtrip,'h2_polar_roundtrip':h2_roundtrip,'paired_geometry_deltas':paired,'seed_metrics':seeds_report,'fixed_shared_pscale_metrics':shared_scale,'compression_ceiling':{'label':'held-out truth projection through outer-train-fitted basis; ORACLE REPRESENTATION CEILING, never prediction/H1; C1 also includes preregistered weak-phase +1 imputation, separately quantified','C0':summarize([x['C0']['state'] for x in ceilings]),'C1':summarize([x['C1']['state'] for x in ceilings]),'C1_weak_rule_only':summarize([x['C1_weak_rule_only']['state'] for x in ceilings]),'all_geometry':ceilings},'tails':tails,'NP_feature_training':False,'solver_invocations':0,'gpu_runner_invocations':0,'new_HF':0,'reserve_cases':0,'inverse_search':False,'candidate_selection':'frozen H1 gates first; if all fail, compare state/routing improvement and tail deterioration; no composite admission score'}
 atomic_json(OUT/'results.json',summaries)
 # Provenance audit includes all fold/seed training choices and verifies original baseline parity through direct metrics.
 aud={'status':'PASS','protocol_sha256':sha(OUT/'protocol.json'),'input_sha256':context_hashes(ctx),'fold_manifest_sha256':FOLD_SHA,'strict_geometry_LOGO':True,'inner_grouped_by_geometry':True,'test_geometry_used_for_epoch_selection':False,'all_PCA_and_scalers_outer_train_only':True,'weak_phase_rule':'truth amplitude <=1% of max among 14 coordinates at each geometry/wavelength; phase set +1 and phase loss weight 0 only for training weak labels','phase_loss_weights_fit_on_outer_train_only':True,'predicted_common_phase':True,'oracle_phase_alignment_used_for_prediction_or_gates':False,'P_scale_source':'frozen full-band 32G OOF RBF KRR branch; identical for C0/C1/FULL','h2_sha256':H2_SHA,'H1_gate_sha256':H1_SHA,'leakage_outer_folds_checked':True,'zero_solver':True,'runtime':{'python_executable':sys.executable,'torch_version':torch.__version__,'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),'cuda_available':torch.cuda.is_available(),'training_device':'cpu'},'C0_seed_fits':96,'C1_seed_fits':96,'solver_entries':0,'runner_entries':0}
 atomic_json(OUT/'audit.json',aud)
 atomic_json(OUT/'checkpoint.json',{'task':NAME,'phase':'TRAINED_AUDITED_REVIEW_READY','protocol_sha256':sha(OUT/'protocol.json'),'completed_seed_fits':192,'total_seed_fits':192,'solver_invocations':0,'runner_invocations':0,'continuation':'Read CONTINUATION.md, protocol.json, results.json, audit.json and seed_progress.json before resuming.'})
 make_report(summaries,aud,proto)
 make_hashes()
 print('POC_COMPLETE',json.dumps({'C0':results['C0']['summary'],'C1':results['C1']['summary'],'FULL':results['HISTORICAL_FULL']['summary'],'gates':{k:v['gates'] for k,v in results.items()}},separators=(',',':')),flush=True)

def make_report(j,audit,protocol):
 def fm(v):return f"{v:.6g}"
 lines=['# '+NAME,'','## STATUS','COMPLETE_OFFLINE_POC. No production admission is inferred.','',
 '## AUTHORITY / GIT',f"Frozen from HEAD {protocol['frozen_head']}; branch work/mdc-np-coupling-ml-v1. Dataset/fold/H1/H2/model hashes are in protocol.json and audit.json. Initial pre-POC worktree had preserved unrelated untracked artifacts.",'',
 '## ZERO-SOLVER ASSERTION','FDTD 0; GPU Runner 0; new HF 0; reserve 0; inverse search 0; Runner development 0. C0/C1 CPU training only.','',
 '## PREREGISTERED CONFIGS / TRAINING BUDGET','Exactly two new configurations; geometry-only; full 440–460 nm; 32 LOGO outer folds; 3 seeds (0,1,2); three geometry-grouped inner folds; max 320 epochs, patience 45, median inner best epoch for refit; AdamW lr 0.002, weight decay 0.0001, gradient clip 5; no extra seeds, variants or hyperparameter search. Both configs select epochs on the same inner-validation standardized latent MSE. C1 training phase weak-label threshold 1% row maximum; weak truth phase deterministically +1 and its circular training-loss weight is zero. Equal fixed weights for standardized latent, standardized log-amplitude, masked circular, and normalized complex-reconstruction losses. All scales and phase masks used for optimization derive only from fit-subset labels.','',
 '## REPRESENTATION / PARAMETER COUNTS','C0 is frozen Cartesian M5, width32, local rank2/order and 14 output scores; 2,684 parameters. C1 predicts rank2/order log-amplitude and rank2/order absolute unit-phase (Re/Im spectrum PCA), then reconstructs 14 TE/TM coordinates; same encoder/fusion hidden width32; 28 outputs; 4,056 parameters (+51.1%, output-coordinate dimensionality changes; hidden width stays 32). Softplus-like nonnegative decoder is expm1(max(log-amplitude,0)); unit phase is normalized, fallback +1 when vector norm <1e-8. C1 predicts absolute phase; it retains common phase, uses no reference or held-out alignment.','',
 '## ROUND-TRIP AND COMPRESSION CEILINGS',f"Uncompressed polar max abs error {j['polar_roundtrip']['max_abs_complex_error']:.3g}. Frozen H2 round-trip maximum absolute order-power/routing/total-power errors are {j['h2_polar_roundtrip']['max_abs_order_power_error']:.3g}/{j['h2_polar_roundtrip']['max_abs_routing_error']:.3g}/{j['h2_polar_roundtrip']['max_abs_total_power_error']:.3g}. Rank2 PCA ceilings are held-out-truth projections through each outer-train-fitted basis and are labeled ORACLE REPRESENTATION CEILING; C1 weak-phase +1 imputation is separately measured. See compression_ceilings.csv. These do not measure geometry-to-latent prediction. C0 Cartesian and C1 amplitude/phase ceilings are reported separately.",'',
 '## C0 REPRODUCTION',f"C0 freshly trained under frozen M5 protocol. It is compared both to saved historical FULL and current original H1 thresholds. All H1 metrics: {json.dumps(j['arms']['C0'],separators=(',',':'))}",'',
 '## C1 VS C0 VS HISTORICAL FULL',f"Frozen candidate outcomes: {json.dumps(j['arms'],separators=(',',':'))}. Paired geometry deltas, wins/ties/losses and spread: {json.dumps(j['paired_geometry_deltas'],separators=(',',':'))}. Geometry is the statistical unit; folds are dependent, so no significance claims.",'',
 '## AMPLITUDE / PHASE / RELATIVE-PHASE','Per geometry report includes exact amplitude/phase SSE partition, amplitude-weighted circular and wrapped phase errors, strong-signal phase, and cross-order relative phase. The common-phase fit and aligned residual are ORACLE DIAGNOSTICS only; they are excluded from predictions, candidate selection, and every H1 gate.','',
 '## TAIL ATTRIBUTION',f"S31, S33 and EXT08 per-model rows: {json.dumps(j['tails'],separators=(',',':'))}. Full 32-geometry tails are in per_geometry.csv; geometry-wavelength errors are in per_wavelength.csv and geometry-order errors in per_order.csv. P_scale is wavelength-total and is reported at wavelength granularity, not assigned to orders. No wavelength/seed pseudoreplication.",'',
 '## P_SCALE LIMITATION','All three arms use the same frozen archived full-band 32G OOF RBF KRR P_scale predictions. This isolates state representation; P_scale is not retrained or replaced with truth. A failing P_scale gate remains failing.','',
 '## ORIGINAL H1 GATES',f"Original conjunctive thresholds and statuses: {json.dumps({k:{'gates':v['gates'],'H1':v['H1'],'routing_pearson':v['routing_pearson'],'pscale_pearson':v['pscale_pearson'],'seed_state_median_std':v['seed_state_median_std']} for k,v in j['arms'].items()},separators=(',',':'))}. Same-scale end-to-end summaries: {json.dumps(j['fixed_shared_pscale_metrics'],separators=(',',':'))}. H2 physical reconstruction residuals: see h2_reconstruction.csv.",'',
 '## LEAKAGE AUDIT / TESTS','Outer test geometry excluded from every scaler, PCA, loss scale, weak-label training weight, early-stop decision and final fit. Inner validation is geometry-grouped. Seed predictions and per-fold provenance are persisted incrementally. Tests and H2/split checks are linked by artifact hashes.','',
 '## NEXT PROPOSAL — DO NOT EXECUTE','Decision rule: if C1 improves state/phase without tail harm, representation looks useful and merits review; if compression ceiling is materially worse, review the latent representation; if ceiling is strong but prediction remains poor, review physically conditioned residual mapping. Targeted sampling merits review only if repeatable tail-specific failures persist; this POC does not authorize or run samples. Both new candidates failing gates stops this line for review without automatic follow-up.','','Artifacts and SHA256 values are enumerated in artifact_hashes.json.']
 (OUT/(NAME+'.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
def make_hashes():
 files=[p for p in OUT.iterdir() if p.is_file() and p.name!='artifact_hashes.json']
 atomic_json(OUT/'artifact_hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(files)})
if __name__=='__main__':train()
