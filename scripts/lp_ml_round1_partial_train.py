from __future__ import annotations
import csv, json, math, hashlib, random, time
from pathlib import Path
from collections import defaultdict
import numpy as np

R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4')
OUT=R/'outputs/lp_ml_dataset_v1/analysis'; OUT.mkdir(parents=True,exist_ok=True)
MODEL_DIR=R/'outputs/lp_ml_dataset_v1/model_runtime_partial'; MODEL_DIR.mkdir(parents=True,exist_ok=True)
SMOKE=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_smoke_attempt2_v1/candidate_wavelength_jones_v1.csv'
PROD=R/'outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round1_production_attempt1_v1/candidate_wavelength_jones_v1.csv'
PLAN=R/'outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round1_256_candidate_plan_v1.csv'
def read(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rs):
 p.parent.mkdir(parents=True,exist_ok=True); fs=[]
 for r in rs:
  for k in r:
   if k not in fs:fs.append(k)
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fs);w.writeheader();w.writerows(rs)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=read(SMOKE)+read(PROD); plan=read(PLAN); pmap={r['candidate_id']:r for r in plan}
ids=sorted({r['candidate_id'] for r in rows}); assert len(ids)==61
assert all(i in pmap for i in ids)
byid=defaultdict(list)
for r in rows:byid[r['candidate_id']].append(r)
assert all(len(v)==9 for v in byid.values())
fields=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg','sin_Psi','cos_Psi']
labels=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']
X=[];Y=[];meta=[]
for r in rows:
 p=pmap[r['candidate_id']]; X.append([float(p['J1_side_nm']),float(p['J2_length_nm']),float(p['J2_width_nm']),float(p['D_nm']),float(p['Psi_deg']),math.sin(math.radians(float(p['Psi_deg']))),math.cos(math.radians(float(p['Psi_deg'])))])
 Y.append([float(r[k]) for k in labels]);meta.append(r)
X=np.asarray(X,np.float64);Y=np.asarray(Y,np.float64)
# Union exact geometry plus canonical/symmetry aliases into one split group.
parent={i:i for i in ids}
def find(x):
 while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
 return x
def union(a,b):
 a,b=find(a),find(b)
 if a!=b:parent[b]=a
for fld in ['canonical_relative_geometry_hash_sha256','symmetry_equivalence_geometry_hash_sha256']:
 d=defaultdict(list)
 for i in ids:d[pmap[i][fld]].append(i)
 for g in d.values():
  for i in g[1:]:union(g[0],i)
groups=defaultdict(list)
for i in ids:groups[find(i)].append(i)
rng=random.Random(20260803)
gs=list(groups.values());rng.shuffle(gs)
target={'train':0.70*len(ids),'val':0.15*len(ids),'test':0.15*len(ids)}; assign={};counts=defaultdict(int)
for g in gs:
 best=min(['train','val','test'],key=lambda s:(counts[s]-target[s], {'train':0,'val':1,'test':2}[s]))
 for i in g:assign[i]=best
 counts[best]+=len(g)
split_rows=[{'candidate_id':i,'split':assign[i],'group_id':find(i),'category':pmap[i]['category'],'canonical_hash':pmap[i]['canonical_relative_geometry_hash_sha256'],'symmetry_hash':pmap[i]['symmetry_equivalence_geometry_hash_sha256']} for i in ids]
write(OUT/'lp_ml_dataset_v1_round1_partial_split_manifest_v1.csv',split_rows)
idx={s:np.array([j for j,r in enumerate(meta) if assign[r['candidate_id']]==s],dtype=int) for s in ['train','val','test']}
mu=Y[idx['train']].mean(0); sd=Y[idx['train']].std(0);sd=np.where(sd<1e-12,1.0,sd)
(OUT/'lp_ml_dataset_v1_round1_partial_normalization_v1.json').write_text(json.dumps({'features':fields,'train_only_label_mean':mu.tolist(),'train_only_label_std':sd.tolist(),'split_seed':20260803,'partial_coverage':True},indent=2)+'\n')
Xz=(X-X[idx['train']].mean(0))/np.where(X[idx['train']].std(0)<1e-12,1.0,X[idx['train']].std(0)); Yz=(Y-mu)/sd
def pred_metrics(pr,truth):
 Jp=pr[:,0]+1j*pr[:,1]; Jq=pr[:,2]+1j*pr[:,3]; Jr=pr[:,4]+1j*pr[:,5]; Js=pr[:,6]+1j*pr[:,7]
 T=lambda a:np.abs(a)**2
 phase=lambda a:np.degrees(np.angle(a));
 out={}
 out['mae']=float(np.mean(np.abs(pr-truth)));out['rmse']=float(np.sqrt(np.mean((pr-truth)**2)))
 fro=[];ph=[];tx=[];ty=[];leak=[];rank=[];proj=[]
 for k in range(len(pr)):
  P=np.array([[Jp[k],Jq[k]],[Jr[k],Js[k]]]);Q=np.array([[truth[k,0]+1j*truth[k,1],truth[k,2]+1j*truth[k,3]],[truth[k,4]+1j*truth[k,5],truth[k,6]+1j*truth[k,7]]])
  fro.append(np.linalg.norm(P-Q)/max(np.linalg.norm(Q),1e-12));ph.append(abs(((phase(Jp[k])-phase(Q[0,0])+180)%360)-180));tx.append(abs(T(Jp[k])-T(Q[0,0])));ty.append(abs(T(Js[k])-T(Q[1,1])));leak.append(abs((T(Jq[k])+T(Jr[k])+T(Js[k]))-(T(Q[0,1])+T(Q[1,0])+T(Q[1,1]))));rank.append(abs(np.linalg.svd(P,compute_uv=False)[1]/max(np.linalg.svd(P,compute_uv=False)[0],1e-12)-np.linalg.svd(Q,compute_uv=False)[1]/max(np.linalg.svd(Q,compute_uv=False)[0],1e-12)));proj.append(abs((1-(abs(np.vdot(np.array([[1,0],[0,0]]),P))**2/(np.linalg.norm(P)**2+1e-12)))-(1-(abs(np.vdot(np.array([[1,0],[0,0]]),Q))**2/(np.linalg.norm(Q)**2+1e-12)))))
 for n,v in [('frobenius_relative',fro),('phase_circular_deg',ph),('Txx_abs',tx),('Tyy_abs',ty),('leakage_abs',leak),('sigma_ratio_abs',rank),('projection_error_abs',proj)]:out[n+'_mean']=float(np.mean(v));out[n+'_p95']=float(np.percentile(v,95));out[n+'_max']=float(np.max(v))
 return out
def fit_sklearn():
 from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor
 from sklearn.neural_network import MLPRegressor
 from sklearn.multioutput import MultiOutputRegressor
 models={
  'ExtraTreesRegressor':ExtraTreesRegressor(n_estimators=160,random_state=20260803,n_jobs=-1,min_samples_leaf=1),
  'HistGradientBoostingRegressor':MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=200,learning_rate=.05,max_leaf_nodes=15,random_state=20260803)),
  'SimpleMLPRegressor':MLPRegressor(hidden_layer_sizes=(128,128),activation='relu',solver='adam',early_stopping=True,random_state=20260803,max_iter=500)
 }
 out={}
 for name,m in models.items():
  t=time.time();m.fit(Xz[idx['train']],Yz[idx['train']]); pr=m.predict(Xz[idx['test']])*sd+mu; out[name]={'hyperparameters':str(m.get_params()),'training_seconds':time.time()-t,'metrics':pred_metrics(pr,Y[idx['test']])}
 return out
baseline=fit_sklearn();(OUT/'lp_ml_dataset_v1_round1_partial_baseline_metrics_v1.json').write_text(json.dumps(baseline,indent=2,sort_keys=True)+'\n')
import torch, torch.nn as nn
class Block(nn.Module):
 def __init__(self,w):
  super().__init__();self.net=nn.Sequential(nn.Linear(w,w),nn.LayerNorm(w),nn.SiLU(),nn.Dropout(.03),nn.Linear(w,w),nn.LayerNorm(w),nn.SiLU(),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class Net(nn.Module):
 def __init__(self):
  super().__init__();self.stem=nn.Sequential(nn.Linear(7,256),nn.LayerNorm(256),nn.SiLU());self.blocks=nn.Sequential(*[Block(256) for _ in range(4)]);self.out=nn.Linear(256,8)
 def forward(self,x):return self.out(self.blocks(self.stem(x)))
def lossfn(p,t,amp_floor):
 raw=nn.functional.smooth_l1_loss(p,t)
 pp=p*torch.tensor(sd,dtype=p.dtype)+torch.tensor(mu,dtype=p.dtype);tt=t*torch.tensor(sd,dtype=t.dtype)+torch.tensor(mu,dtype=t.dtype)
 def cj(z):return torch.complex(z[:,0],z[:,1])
 P=torch.stack([cj(pp[:,0:2]),cj(pp[:,2:4]),cj(pp[:,4:6]),cj(pp[:,6:8])],1).reshape(-1,2,2);Q=torch.stack([cj(tt[:,0:2]),cj(tt[:,2:4]),cj(tt[:,4:6]),cj(tt[:,6:8])],1).reshape(-1,2,2)
 rel=torch.sum(torch.abs(P-Q)**2,dim=(1,2))/(torch.sum(torch.abs(Q)**2,dim=(1,2))+1e-8);powp=torch.abs(P)**2;powq=torch.abs(Q)**2;lp=torch.mean((powp[:,0,0]-powq[:,0,0])**2+(powp[:,1,1]-powq[:,1,1])**2+(powp[:,0,1]+powp[:,1,0]-powq[:,0,1]-powq[:,1,0])**2)
 sp=torch.linalg.svdvals(P);sq=torch.linalg.svdvals(Q);rank=torch.mean((sp[:,1]/(sp[:,0]+1e-8)-sq[:,1]/(sq[:,0]+1e-8))**2);proj=torch.mean((1-(torch.abs(P[:,0,0])**2/(torch.sum(torch.abs(P)**2,dim=(1,2))+1e-8))-(1-(torch.abs(Q[:,0,0])**2/(torch.sum(torch.abs(Q)**2,dim=(1,2))+1e-8))))**2);mask=(torch.abs(Q[:,0,0])>amp_floor).float();phase=torch.mean(mask*(1-torch.cos(torch.angle(P[:,0,0])-torch.angle(Q[:,0,0])))/(torch.sum(mask)+1e-8))
 return raw+.25*torch.mean(rel)+.10*lp+.05*rank+.05*proj+.05*phase
ensemble=[];train_idx=idx['train'];val_idx=idx['val'];test_idx=idx['test'];amp_floor=float(np.percentile(np.abs(Y[train_idx,0]+1j*Y[train_idx,1]),10));
for seed in [11,22,33,44,55]:
 torch.manual_seed(seed);np.random.seed(seed);m=Net();opt=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=500,eta_min=1e-6);best=None;bestv=float('inf');stall=0
 tx=torch.tensor(Xz[train_idx],dtype=torch.float32);ty=torch.tensor(Yz[train_idx],dtype=torch.float32);vx=torch.tensor(Xz[val_idx],dtype=torch.float32);vy=torch.tensor(Yz[val_idx],dtype=torch.float32)
 for ep in range(500):
  m.train();opt.zero_grad();l=lossfn(m(tx),ty,amp_floor);l.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step();sched.step();m.eval();
  with torch.no_grad():v=float(lossfn(m(vx),vy,amp_floor))
  if v<bestv-1e-8:bestv=v;best={k:v.detach().cpu().clone() for k,v in m.state_dict().items()};stall=0
  else:stall+=1
  if stall>=50:break
 m.load_state_dict(best);m.eval();
 with torch.no_grad():pr=m(torch.tensor(Xz[test_idx],dtype=torch.float32)).cpu().numpy()*sd+mu
 path=MODEL_DIR/f'residual_mlp_seed_{seed}.pt';torch.save(m.state_dict(),path);ensemble.append({'seed':seed,'epochs':ep+1,'best_val_loss':bestv,'checkpoint_path':str(path.relative_to(R)).replace('\\','/'),'checkpoint_sha256':sha(path),'metrics':pred_metrics(pr,Y[test_idx])})
 preds=[]
for seed in [11,22,33,44,55]:
 m=Net();m.load_state_dict(torch.load(MODEL_DIR/f'residual_mlp_seed_{seed}.pt',map_location='cpu'));m.eval();
 with torch.no_grad():preds.append(m(torch.tensor(Xz[test_idx],dtype=torch.float32)).numpy()*sd+mu)
arr=np.stack(preds);mean=arr.mean(0);std=arr.std(0);truth=Y[test_idx];unc=np.sqrt(np.sum(std**2,axis=1));err=np.sqrt(np.sum((mean-truth)**2,axis=1));corr=float(np.corrcoef(unc,err)[0,1]) if len(err)>1 else float('nan');order=np.argsort(unc);bins=[]
for b in range(3):
 q=order[b*len(order)//3:(b+1)*len(order)//3];bins.append({'bin':b,'n':int(len(q)),'mean_uncertainty':float(np.mean(unc[q])),'mean_error':float(np.mean(err[q]))})
(OUT/'lp_ml_dataset_v1_round1_partial_residual_mlp_metrics_v1.json').write_text(json.dumps({'architecture':'7->256,4 residual blocks,width256,SiLU,LayerNorm,dropout0.03','optimizer':'AdamW','lr':3e-4,'weight_decay':1e-4,'batch_size':len(train_idx),'warmup_epochs':10,'cosine_eta_min':1e-6,'max_epochs':500,'patience':50,'grad_clip':1.0,'seeds':[11,22,33,44,55],'composite_loss':'1.00 raw SmoothL1 + .25 relative Jones + .10 power + .05 rank + .05 projection + .05 circular phase masked by train-only 10th percentile amplitude','partial_coverage':True,'amp_floor_train_only':amp_floor,'seed_metrics':ensemble,'ensemble_metrics':pred_metrics(mean,truth),'uncertainty_proxy':'5-seed component dispersion','uncertainty_error_correlation':corr,'calibration_bins':bins},indent=2,sort_keys=True)+'\n')
print(json.dumps({'geometries':len(ids),'rows':len(rows),'split_counts':{k:int(len(v)) for k,v in idx.items()},'baseline_models':list(baseline),'ensemble_seeds':5,'test_rows':int(len(test_idx)),'outcome':'LP_ML_ROUND1_DATA_OR_MODEL_FIX_REQUIRED'},indent=2))
