"""Bounded active-learning bootstrap; frozen truth only; no solver imports."""
import os
for k in ['OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS']:os.environ[k]='2'
from pathlib import Path
import sys,json,time,warnings,csv
import numpy as np
from scipy.stats import spearmanr
from sklearn.dummy import DummyRegressor
from sklearn.kernel_ridge import KernelRidge
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor
from threadpoolctl import threadpool_limits
import joblib
R=Path(r'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1')
O=R/'reports/coupling/APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1'
sys.path.insert(0,str(R/'scripts/coupling_ml'))
from k6_v2_pipeline.amended156 import adapter as A
from k6_v2_pipeline import contracts as C,h1
def put(n,v):
 p=O/n;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(v,indent=2,allow_nan=False,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else x.item())+'\n',encoding='utf-8')
def make(k,s):
 if k=='Mean':reg=DummyRegressor()
 elif k=='KRR':reg=KernelRidge(alpha=.1,kernel='rbf',gamma=1/6)
 elif k=='ExtraTrees':reg=ExtraTreesRegressor(n_estimators=128,min_samples_leaf=3,max_features=1.,random_state=s,n_jobs=2)
 elif k=='MLP':reg=MLPRegressor(hidden_layer_sizes=(32,32),activation='tanh',solver='adam',alpha=1.,learning_rate_init=.003,batch_size=256,max_iter=1000,tol=0.,n_iter_no_change=1001,early_stopping=False,random_state=s)
 return TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(),reg),transformer=StandardScaler())
def rho(a,b):return None if np.std(a)<1e-14 or np.std(b)<1e-14 else float(spearmanr(a,b).statistic)
def measures(y,p):return {'MAE':float(np.abs(y-p).mean()),'RMSE':float(np.sqrt(np.mean((y-p)**2)))}
def evaluate(t,p,truth):
 eta=p[:,:21];ps=np.exp(p[:,21:]);pp=eta*ps
 ans={n:measures(a,b) for n,a,b in [('eta',t[:,:21],eta),('log_P_scale',t[:,21:],p[:,21:]),('P_scale',np.exp(t[:,21:]),ps),('P_plus1_H2',truth,pp)]}
 for n,a,b in [('eta',t[:,:21],eta),('P_scale',np.exp(t[:,21:]),ps),('P_plus1_H2',truth,pp)]:
  ans[n]['450nm']={**measures(a[:,10],b[:,10]),'Spearman':rho(a[:,10],b[:,10])}
  ans[n]['band_mean_Spearman']=rho(a.mean(1),b.mean(1))
 ans['eta_invalid_fraction']=float(np.mean((eta<0)|(eta>1)))
 return ans
def run():
 O.mkdir(parents=True,exist_ok=True)
 if (O/'FIT_LEDGER.json').exists():raise RuntimeError('Existing task fit ledger: do not replay')
 specs=[('Mean',17),('KRR',17)]+[(k,s) for k in ['ExtraTrees','MLP'] for s in [17,29,43]]
 put('TRAINING_PLAN.json',{'authority':'latest user APCD_COUPLING_ML_GPU_ACTIVE_LEARNING_MAINLINE_V1','estimator_fit_limit':104,'targets':'21 native eta(+1),21 natural log(P_scale); reduced H2 power factorization eta*exp(logP), no complex reconstruction claim','split':'frozen four geometry folds;old32 train-only;124 distinct heldout','learning_train_sizes':'old32 + 24,56,all available new; nested seeded subsets','hyperparameters':'fixed before new fits: KRR alpha.1 gamma1/6;ET128 leaf3;MLP6-32-32-42 tanh Adam1000 alpha1 lr.003 seeds17,29,43; no validation selection','uncertainty':'raw ensemble dispersion; heldout error association, not calibrated confidence','sealed_response_access':0,'real_solver_budget':0})
 col=A.load_collection(False);cs=col.training_cases();plan=A.build_plan();h1.load_h1_authority();dec=h1.load_h2_decoder()
 ids=np.array([c.case_id for c in cs]);roles=np.array([c.role for c in cs]);x=np.array([c.ordered_D_nm for c in cs],float)
 eta=np.array([c.eta[:,4] for c in cs]);ps=np.array([c.p_scale for c in cs]);ab=h1.reconstruct_h2(np.array([c.c_hat for c in cs]),ps,dec)['absolute_order'][:,:,4]
 assert len(cs)==len(set(map(tuple,x)))==156 and np.all(ps>0)
 y=np.c_[eta,np.log(ps)];idx={s:i for i,s in enumerate(ids)};folds=[];ledger=[];results={};oof={k:np.full((156,42),np.nan) for k in ['Mean','KRR','ExtraTrees','MLP']};sd={k:np.full((156,42),np.nan) for k in ['ExtraTrees','MLP']}
 put('DATA_AUDIT.json',{'valid_geometries':156,'roles':{r:int((roles==r).sum()) for r in set(roles)},'inventory_sha':col.manifest_sha256,'H1':C.H1_AUTHORITY_SHA256,'H2':C.H2_DECODER_SHA256,'H2_power_vs_native_factorization_max_abs':float(np.max(np.abs(eta*ps-ab))),'confirmation_responses':0,'DOE56_training_rows':0,'full_native_rehash':False,'frozen_adapter_checks':'existing required label/provenance hashes, native existence and size'})
 def fit(m,ti,tag):
  row={'id':tag,'n_train':len(ti),'state':'STARTED'};ledger.append(row);put('FIT_LEDGER.json',ledger);start=time.perf_counter()
  try:
   with warnings.catch_warnings(record=True) as ws:warnings.simplefilter('always');m.fit(x[ti],y[ti])
   row.update(state='COMPLETE',seconds=time.perf_counter()-start,warnings=[str(z.message) for z in ws])
  except BaseException as ex:row.update(state='FAILED',error=repr(ex));put('FIT_LEDGER.json',ledger);raise
  put('FIT_LEDGER.json',ledger);return m
 for f in range(1,5):
  va=np.array([idx[i] for i in plan.outer_validation_ids[f]]);tr=np.array([i for i in range(156) if i not in set(va)]);old=tr[roles[tr]==C.ROLE_OLD32];new=tr[roles[tr]!=C.ROLE_OLD32];order=np.random.default_rng(20261017+f).permutation(new)
  assert not set(map(tuple,x[tr]))&set(map(tuple,x[va]))
  folds.append({'fold':f,'train_ids':ids[tr],'heldout_ids':ids[va]})
  for count in [24,56,len(new)]:
   ti=np.r_[old,order[:count]];pred={};train={}
   for k,s in specs:
    m=fit(make(k,s),ti,f'fold{f}/new{count}/{k}/seed{s}');pred.setdefault(k,[]).append(m.predict(x[va]));train.setdefault(k,[]).append(float(np.sqrt(np.mean((m.predict(x[ti])-y[ti])**2))))
   rows={}
   for k,v in pred.items():
    p=np.mean(v,axis=0);rows[k]={'metrics':evaluate(y[va],p,ab[va]),'train_mixed_target_RMSE':float(np.mean(train[k])),'seed_prediction_sd':float(np.std(v,axis=0).mean())}
    if count==len(new):
     oof[k][va]=p
     if k in sd:sd[k][va]=np.std(v,axis=0)
   results[f'fold{f}/n{len(ti)}']=rows;put('LEARNING_CURVES.json',results)
  print('TRAIN_FOLD_COMPLETE',f,len(ledger),flush=True)
 vi=np.array(sorted(i for row in folds for i in [idx[s] for s in row['heldout_ids']]))
 summary={k:evaluate(y[vi],v[vi],ab[vi]) for k,v in oof.items()}
 uncertainty={}
 for k in sd:
  err=np.abs(oof[k][vi,:21]-eta[vi]);u=sd[k][vi,:21]
  uncertainty[k]={'geometry_mean_uncertainty_error_Spearman':rho(err.mean(1),u.mean(1)),'mean_eta_sd':float(u.mean()),'raw_2sd_pointwise_coverage':float(np.mean(err<=2*u)),'calibrated':False}
 np.savez_compressed(O/'TRAINING_DATA_AND_OOF.npz',case_ids=ids,roles=roles,D_nm=x,eta=eta,P_scale=ps,P_plus1_H2=ab,heldout=vi,**oof,**{k+'_sd':v for k,v in sd.items()})
 put('FOLDS.json',folds);put('MODEL_METRICS.json',summary);put('UNCERTAINTY.json',uncertainty)
 (O/'models').mkdir(exist_ok=True);final=[]
 for k,s in specs:
  m=fit(make(k,s),np.arange(156),f'final/{k}/seed{s}');p=O/f'models/{k}_{s}.joblib';joblib.dump(m,p);assert np.allclose(m.predict(x[:3]),joblib.load(p).predict(x[:3]),rtol=1e-12,atol=1e-12);final.append({'kind':k,'seed':s,'path':str(p)})
 assert len(ledger)==104 and all(z['state']=='COMPLETE' for z in ledger)
 np.savez_compressed(O/'TRAINING_DATA_AND_OOF.npz',case_ids=ids,roles=roles,D_nm=x,eta=eta,P_scale=ps,P_plus1_H2=ab,heldout=vi,**oof,**{k+'_sd':v for k,v in sd.items()})
 put('FOLDS.json',folds);put('MODEL_METRICS.json',summary);put('UNCERTAINTY.json',uncertainty);put('FINAL_MODELS.json',final)
 put('TRAINING_COMPLETE.json',{'fits':len(ledger),'fit_wall_seconds_sum':sum(z['seconds'] for z in ledger),'warning_fits':sum(bool(z['warnings']) for z in ledger),'heldout_geometries':len(vi),'real_entries':0,'FDTD':0,'sealed_responses':0})
 print('TRAINING_COMPLETE',json.dumps(summary),flush=True)
if __name__=='__main__':
 with threadpool_limits(limits=2):run()
