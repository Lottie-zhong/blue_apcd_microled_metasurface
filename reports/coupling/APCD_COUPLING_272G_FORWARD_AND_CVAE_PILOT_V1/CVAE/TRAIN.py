from pathlib import Path
import os
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='2'
os.environ['MKL_NUM_THREADS']='2'
import json,csv,time,sys,numpy as np,torch
from torch import nn
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.preprocessing import StandardScaler
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1');Q=R/'reports/coupling';D=Q/'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1/CVAE';B=Q/'APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1/STAGE_50';D.mkdir(parents=True,exist_ok=True)
torch.set_num_threads(2);torch.set_num_interop_threads(1)
rd=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def put(n,v):(D/n).write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist() if hasattr(x,'tolist') else x.item()),encoding='utf-8')
def csvout(n,rows):
 with (D/n).open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline import h1 as H
z=np.load(B/'COMPLEX_DATASET.npz',allow_pickle=False);ids=list(z['case_ids']);ix={x:i for i,x in enumerate(ids)};g=z['D_nm'];xx=(g-100)/130;et=z['eta_H2'];ps=z['P_scale'];ap=z['absolute_H2'];conditions=np.column_stack([et[:,10,4],ps[:,10],et[:,:,4].mean(1),ps.mean(1)])
folds=rd(B/'FOLDS.json');old=rd(Q/'APCD_COUPLING_AL16_FAST_GPU_PRODUCTION_V1/ML_UPDATE/FOLDS.json');oldids={x for f in old for x in f['heldout_old_ids']};assert len(oldids)==124
manifest={'task':'APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1','branch':'CVAE exploratory only','dataset':str(B/'COMPLEX_DATASET.npz'),'n_geometry':272,'condition':['H2 eta(+1) 450nm','P_scale 450nm','21-wavelength mean H2 eta(+1)','21-wavelength mean P_scale'],'condition_redundancy':'450 and spectral means correlated; P(+1) omitted because determined by eta times P_scale. Low-dimensional descriptors do not identify full609D.','encoder':'10->64 SiLU ->32 SiLU ->mu3/logvar3','decoder':'7->32 SiLU ->64 SiLU ->6 sigmoid','latent_dim':3,'seeds':[17,29],'epochs':400,'batch_size':64,'lr':0.001,'beta_KL':0.005,'KL_warmup_epochs':80,'weight_decay':0.0001,'device':'CPU','threads':2,'validation':'fixed original124 OOF; train IDs exact original272 family-purged folds. No heldout early stopping/hyperparameter selection. All training scalers fit train-only.','candidate_budget_per_target_per_method':16,'checker':'fold train-only B29 ExtraTrees128/minleaf3 seed17; not formal3seed model; no direct eta surrogate','baselines':['prior CVAE','uniform ordered grid random','nearest training geometry retrieval by standardized condition'],'checks':'retrospective known-target pilot, no true forward observations for newly generated geometry. Proxy discrepancies are not truth certification.','NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0,'DIAG2':'1/2','A2':'HOLD','DOE56':'HOLD'}
put('PREREGISTRATION.json',manifest)
class VAE(nn.Module):
 def __init__(self):
  super().__init__();self.enc=nn.Sequential(nn.Linear(10,64),nn.SiLU(),nn.Linear(64,32),nn.SiLU());self.mu=nn.Linear(32,3);self.lv=nn.Linear(32,3);self.dec=nn.Sequential(nn.Linear(7,32),nn.SiLU(),nn.Linear(32,64),nn.SiLU(),nn.Linear(64,6),nn.Sigmoid())
 def encode(self,x,c):
  h=self.enc(torch.cat([x,c],1));return self.mu(h),self.lv(h).clamp(-8,8)
 def decode(self,c,a):return self.dec(torch.cat([c,a],1))
 def forward(self,x,c):
  mu,lv=self.encode(x,c);return self.decode(c,mu+torch.exp(.5*lv)*torch.randn_like(mu)),mu,lv
def quant(x):return np.clip(np.rint((100+130*x)/5)*5,100,230)
def ckcond(gg,checker,scale,decoder):
 unique,inv=np.unique(gg.reshape(-1,6),axis=0,return_inverse=True);n=len(unique);features=np.column_stack([np.repeat(unique,21,axis=0),np.tile(z['wavelengths_nm'],n)]);out=checker.predict(scale.transform(features)).reshape(n,21,29);cc=out[:,:,:28].reshape(n,21,7,2,2);cc=cc[...,0]+1j*cc[...,1];pp=np.exp(out[:,:,28]);hh=H.reconstruct_h2(cc,pp,decoder);e=hh['eta'];cond=np.column_stack([e[:,10,4],pp[:,10],e[:,:,4].mean(1),pp.mean(1)]);return cond[inv].reshape(gg.shape[:-1]+(4,))
ledger=[];metrics=[];allcandidates=[];hist=[];start=time.perf_counter();decoder=H.load_h2_decoder();gtuples={tuple(a) for a in g}
for f in folds:
 fold=f['fold'];tr=np.array([ix[a] for a in f['train_ids']]);va=np.array([ix[a] for a in f['heldout_ids'] if a in oldids]);assert len(set(tr)&set(va))==0
 condscale=StandardScaler().fit(conditions[tr]);cs=condscale.transform(conditions).astype('float32');xtr=torch.tensor(xx[tr],dtype=torch.float32);ctr=torch.tensor(cs[tr]);xva=torch.tensor(xx[va],dtype=torch.float32);cva=torch.tensor(cs[va]);trainset={tuple(a) for a in g[tr]}
 checkerfile=D/('checker_fold'+str(fold)+'.joblib')
 import joblib
 if checkerfile.exists():checker,fs=joblib.load(checkerfile)
 else:
  fs=StandardScaler();features=np.column_stack([np.repeat(g[tr],21,axis=0),np.tile(z['wavelengths_nm'],len(tr))]);checker=ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3,random_state=17,n_jobs=2);checker.fit(fs.fit_transform(features),z['target29'][tr].reshape(-1,29));joblib.dump((checker,fs),checkerfile,compress=3)
 for seed in [17,29]:
  run=D/('fold'+str(fold)+'_seed'+str(seed));run.mkdir(exist_ok=True)
  if (run/'COMPLETE.json').exists():
   a=rd(run/'COMPLETE.json');metrics.extend(a['metrics']);ledger.append(a['ledger']);continue
  torch.manual_seed(seed);rng=np.random.default_rng(seed+fold*100);model=VAE();opt=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001);t=time.perf_counter();lossrows=[]
  for ep in range(400):
   model.train();perm=torch.randperm(len(tr));vals=[]
   for b in perm.split(64):
    out,mu,lv=model(xtr[b],ctr[b]);rec=((out-xtr[b])**2).mean();kl=-.5*(1+lv-mu.square()-lv.exp()).sum(1).mean();beta=.005*min(1,(ep+1)/80);loss=rec+beta*kl;opt.zero_grad();loss.backward();opt.step();vals.append([loss.item(),rec.item(),kl.item()])
   v=np.mean(vals,axis=0);lossrows.append({'epoch':ep+1,'loss':v[0],'reconstruction_MSE_norm':v[1],'KL':v[2],'beta':beta})
  model.eval()
  with torch.no_grad():
   mut,lvt=model.encode(xtr,ctr);muv,lvv=model.encode(xva,cva);reco=model.decode(cva,muv).numpy();trainreco=model.decode(ctr,mut).numpy();prior=rng.normal(size=(len(va),16,3)).astype('float32');cc=np.repeat(cs[va,None,:],16,axis=1);priorgeo=quant(model.decode(torch.tensor(cc.reshape(-1,4)),torch.tensor(prior.reshape(-1,3))).numpy().reshape(len(va),16,6));zero=quant(model.decode(cva,torch.zeros(len(va),3)).numpy());shuffle=quant(model.decode(torch.tensor(cs[va][::-1].copy()),torch.zeros(len(va),3)).numpy());latvar=mut.numpy().var(0);klva=(-.5*(1+lvv-muv.square()-lvv.exp()).sum(1)).numpy()
  randomgeo=100+5*rng.integers(0,27,size=(len(va),16,6));dist=((cs[va,None,:]-cs[None,tr,:])**2).mean(-1);nearest=np.argsort(dist,axis=1)[:,:16];retrieval=g[tr][nearest]
  runmetrics=[];arrays={'heldout_ids':np.array(ids)[va],'target_condition':conditions[va],'geometry_truth':g[va],'posterior_reconstruction_nm':quant(reco),'posterior_mu':muv.numpy(),'posterior_logvar':lvv.numpy(),'prior_z':prior}
  common={'fold':fold,'seed':seed,'heldout_count':len(va),'training_count':len(tr),'posterior_reconstruction_MAE_nm':float(abs(100+130*reco-g[va]).mean()),'posterior_quantized_MAE_nm':float(abs(quant(reco)-g[va]).mean()),'train_posterior_MAE_nm':float(abs(100+130*trainreco-g[tr]).mean()),'posterior_KL_mean':float(klva.mean()),'latent_mu_variance_train':latvar.tolist(),'active_latent_dims_threshold_0_01':int((latvar>.01).sum()),'posterior_std_mean':float(np.exp(.5*lvv.numpy()).mean()),'condition_shuffle_geometry_shift_nm':float(abs(shuffle-zero).mean()),'posterior_reconstruction_is_not_inverse_generation':True}
  for name,gg in [('CVAE_prior',priorgeo),('uniform_random',randomgeo),('training_retrieval',retrieval)]:
   pred=ckcond(gg,checker,fs,decoder);err=np.sqrt(np.mean(((pred-conditions[va,None,:])/condscale.scale_)**2,axis=-1));best=err.argmin(1);chosen=gg[np.arange(len(va)),best];tuplelist=[tuple(a) for a in gg.reshape(-1,6)];unique=len(set(tuplelist));gaps=290-(gg+np.roll(gg,-1,axis=-1))/2
   diversity=np.mean(np.sqrt(np.mean((gg[:,:,None,:]-gg[:,None,:,:])**2,axis=-1))[:,np.triu_indices(16,1)[0],np.triu_indices(16,1)[1]])
   mm=dict(common,method=name,n_candidates=int(gg.shape[0]*16),legal_fraction=float(np.mean(np.all((gg>=100)&(gg<=230)&(gg%5==0),axis=-1))),minimum_periodic_gap_nm=float(gaps.min()),unique_fraction=unique/len(tuplelist),training_exact_duplicate_fraction=float(np.mean([a in trainset for a in tuplelist])),all272_exact_overlap_fraction=float(np.mean([a in gtuples for a in tuplelist])),within_target_pairwise_RMS_nm=float(diversity),proxy_condition_RMSE_standardized_all=float(np.mean(err)),proxy_best_of_16_RMSE_standardized=float(np.mean(err.min(1))),proxy_best_of_16_condition_abs_error=np.mean(abs(pred[np.arange(len(va)),best]-conditions[va]),axis=0).tolist(),proxy_condition_success_is_not_truth=True)
   if name=='training_retrieval':
    truecond=conditions[tr][nearest];mm['retrieval_oracle_true_best_of16_condition_RMSE']=float(np.sqrt(np.mean(((truecond-conditions[va,None,:])/condscale.scale_)**2,axis=-1)).min(1).mean());mm['retrieval_true_error_of_proxy_selected']=float(np.sqrt(np.mean(((truecond[np.arange(len(va)),best]-conditions[va])/condscale.scale_)**2,axis=-1)).mean())
   runmetrics.append(mm);arrays[name+'_geometry_nm']=gg;arrays[name+'_proxy_condition']=pred;arrays[name+'_proxy_selected_index']=best
   for j in range(len(va)):
    for k in range(16):allcandidates.append(dict(fold=fold,seed=seed,heldout_target_id=ids[va[j]],method=name,candidate_index=k,**{'D'+str(h+1)+'_nm':int(v) for h,v in enumerate(gg[j,k])},proxy_error_standardized=float(err[j,k]),proxy_selected=bool(k==best[j]),status='EXPLORATORY_ONLY_NO_FDTD_NO_SCIENCE_ID'))
  torch.save({'state_dict':model.state_dict(),'condition_mean':condscale.mean_,'condition_scale':condscale.scale_,'train_ids':np.array(ids)[tr].tolist(),'heldout_ids':np.array(ids)[va].tolist(),'manifest':manifest},run/'MODEL.pt');np.savez_compressed(run/'EVALUATION.npz',**arrays)
  with (run/'LOSS.csv').open('w',encoding='utf-8',newline='') as out:w=csv.DictWriter(out,fieldnames=lossrows[0].keys());w.writeheader();w.writerows(lossrows)
  ll={'fold':fold,'seed':seed,'epochs':400,'train_n':len(tr),'validation_n':len(va),'elapsed_sec':time.perf_counter()-t,'device':'CPU','complete':True};put(str(run.relative_to(D)/'COMPLETE.json'),{'metrics':runmetrics,'ledger':ll});metrics.extend(runmetrics);ledger.append(ll);print('CVAE_COMPLETE',fold,seed,flush=True)
put('FIT_LEDGER.json',ledger);put('EVALUATION_METRICS.json',metrics)
if allcandidates:csvout('EXPLORATORY_CANDIDATES.csv',allcandidates)
summary={}
for name in ['CVAE_prior','uniform_random','training_retrieval']:
 rows=[a for a in metrics if a['method']==name];keys=['posterior_reconstruction_MAE_nm','posterior_quantized_MAE_nm','train_posterior_MAE_nm','posterior_KL_mean','active_latent_dims_threshold_0_01','condition_shuffle_geometry_shift_nm','legal_fraction','minimum_periodic_gap_nm','unique_fraction','training_exact_duplicate_fraction','all272_exact_overlap_fraction','within_target_pairwise_RMS_nm','proxy_condition_RMSE_standardized_all','proxy_best_of_16_RMSE_standardized'];summary[name]={k:float(np.mean([a[k] for a in rows])) for k in keys};summary[name]['proxy_best_of16_by_fold_seed']=[a['proxy_best_of_16_RMSE_standardized'] for a in rows]
put('SUMMARY.json',summary);put('COMPLETE.json',{'status':'PASS_OFFLINE_PILOT_COMPLETE','fits_CVAE':len(ledger),'fits_checker':4,'epochs':400,'candidate_budget':16,'elapsed_total_sec':time.perf_counter()-start,'NEW_FDTD':0,'NEXT_BATCH_AUTHORIZED':0});print('CVAE_ALL_COMPLETE',json.dumps(summary),flush=True)
