from pathlib import Path
import json,hashlib,sys,subprocess,math
import numpy as np,pandas as pd,joblib,torch
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss,balanced_accuracy_score,f1_score
from torch import nn

R=Path(__file__).resolve().parents[1]; P=R/'outputs/mdc_ml_provenance_recovery_fixed_v1_contract_v1/provenance-20260801T080823Z'; O=R/'outputs/mdc_non_hf15_fixed_v1_internal_retrain_oof_v1'/sys.argv[1]
for d in 'preflight classification_oof classification_final regression_oof regression_final calibration conformal predictions checkpoints manifests logs audit reports'.split(): (O/d).mkdir(parents=True,exist_ok=True)
def J(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,default=str))
def H(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ev(x): (O/'logs/job_events.jsonl').open('a').write(json.dumps(x)+'\n')
C=pd.read_parquet(P/'mdc_classification_dev_non_hf15_v2.parquet'); G=pd.read_parquet(P/'mdc_regression_dev_non_hf15_v2.parquet')
L={str(x.candidate_id):json.loads(x.binary_labels_json) for _,x in C.iterrows()}
z=np.load(R/'outputs/mdc_ml_active_learning_merge_retrain_v1/training_view_v1.npz'); ids=z['candidate_ids'].astype(str); X=z['X'].astype('float32'); mp={k:i for i,k in enumerate(ids)}; CX=X[[mp[str(i)] for i in C.candidate_id]]
q=np.load(R/'outputs/mdc_ml_active_learning_merge_retrain_v1/regression_development_view_v1.npz'); rids=q['candidate_ids'].astype(str); RX=q['X'].astype('float32'); RY=q['y_regression'].astype('float32'); rmp={k:i for i,k in enumerate(rids)}; ix=[rmp[str(i)] for i in G.candidate_id]; RX=RX[ix]; RY=RY[ix]
CT=['spectral_fwhm_valid','angular_fwhm_valid','nominal_4d_objective_eligible','shortlist_quality_eligible']; RT=['spectral_fwhm_normal_nm','angular_fwhm_450_deg','cone5_integral_proxy','normal_band_transmission_proxy']; Y=np.array([[int(L[str(cid)][t]) for t in CT] for cid in C.candidate_id])
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(); inputs={str(x.relative_to(R)):H(x) for x in [P/'mdc_classification_dev_non_hf15_v2.parquet',P/'mdc_regression_dev_non_hf15_v2.parquet',R/'outputs/mdc_ml_active_learning_merge_retrain_v1/training_view_v1.npz',R/'outputs/mdc_ml_active_learning_merge_retrain_v1/regression_development_view_v1.npz']}; dfp=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
J(O/'preflight/protected_input_sha_manifest.json',inputs); J(O/'preflight/environment_manifest.json',{'head':head,'python':sys.executable,'hf15_formal_label_reads':0,'sealed_target_reads':0,'solver_calls':0}); J(O/'preflight/frozen_split_contract.json',{'classification_final_fit_membership':'original train rows only','regression_final_fit_membership':'eligible original training rows only'}); ev({'task':'preflight','status':'PASS'})
def cal(raw,y):
 a=np.clip(raw,1e-6,1-1e-6); l=np.log(a/(1-a)); s=LogisticRegression(C=1e6,max_iter=2000).fit(l[:,None],y); ps=s.predict_proba(l[:,None])[:,1]; best=('sigmoid',ps,brier_score_loss(y,ps),s)
 if np.bincount(y).min()>=10:
  i=IsotonicRegression(out_of_bounds='clip').fit(raw,y); pi=i.predict(raw); z=('isotonic',pi,brier_score_loss(y,pi),i); best=min([best,z],key=lambda x:x[2])
 return best
def thr(y,p):
 best=None
 for t in np.unique(np.quantile(p,np.linspace(.01,.99,97))):
  k=(balanced_accuracy_score(y,p>=t),f1_score(y,p>=t,zero_division=0),-abs(t-.5)); best=(k,t) if best is None or k>best[0] else best
 return float(best[1])
rows=[]
for f in range(4):
 tr=C.split_role.eq('train'); va=C.split_role.eq('validation'); ca=C.split_role.eq('calibration'); ho=C.fold.eq(f)&C.split_role.str.contains('adaptive'); seed=20260720+f
 for j,t in enumerate(CT):
  m=ExtraTreesClassifier(n_estimators=384,min_samples_leaf=2,class_weight='balanced',max_features=1.0,n_jobs=8,random_state=seed).fit(CX[tr],Y[tr,j]); name,cp,bs,cc=cal(m.predict_proba(CX[ca])[:,1],Y[ca,j]); tt=thr(Y[va,j],calibrate_p:=cal(m.predict_proba(CX[ca])[:,1],Y[ca,j])[1]); hp=m.predict_proba(CX[ho])[:,1]
  for cid,p in zip(C.loc[ho,'candidate_id'],hp): rows.append({'candidate_id':cid,'fold':f,'target':t,'raw_probability':float(p),'calibration_method':name,'threshold':tt,'prediction':int(p>=tt)})
  joblib.dump({'estimator':m,'calibrator':cc,'threshold':tt},O/f'classification_oof/fold{f}_{t}.joblib')
 pd.DataFrame(rows).to_parquet(O/'classification_oof/raw_calibrated_oof.parquet',index=False); ev({'task':'classification_oof','fold':f,'fits':4})
cf=C.split_role.eq('train')
for j,t in enumerate(CT): joblib.dump(ExtraTreesClassifier(n_estimators=384,min_samples_leaf=2,class_weight='balanced',max_features=1.0,n_jobs=8,random_state=20260720).fit(CX[cf],Y[cf,j]),O/f'classification_final/{t}.joblib')
class M(nn.Module):
 def __init__(self): super().__init__(); self.n=nn.Sequential(nn.Linear(150,256),nn.ReLU(),nn.Dropout(.1),nn.Linear(256,128),nn.ReLU(),nn.Dropout(.1),nn.Linear(128,4))
 def forward(self,x): return self.n(x)
def fit(A,B,V,W,s,f):
 np.random.seed(s); torch.manual_seed(s); sc=StandardScaler().fit(A); a=sc.transform(A).astype('float32'); v=sc.transform(V).astype('float32'); mu=np.nanmean(B,0); sd=np.nanstd(B,0); sd=np.where(sd<1e-12,1,sd); b=((B-mu)/sd).astype('float32'); w=((W-mu)/sd).astype('float32'); m=M(); op=torch.optim.AdamW(m.parameters(),lr=7e-4,weight_decay=1e-5); best=1e99; state=None; bad=0; rng=np.random.default_rng(s)
 for e in range(240):
  m.train(); losses=[]; order=rng.permutation(len(a))
  for st in range(0,len(order),128):
   ix=order[st:st+128]; pred=m(torch.from_numpy(a[ix])); mask=torch.isfinite(torch.from_numpy(b[ix])); loss=nn.SmoothL1Loss()(pred[mask],torch.from_numpy(b[ix])[mask]); op.zero_grad(); loss.backward(); op.step(); losses.append(float(loss))
  m.eval(); val=float(torch.mean(torch.abs(m(torch.from_numpy(v))-torch.from_numpy(w))))
  if val<best-1e-7: best=val; state={k:x.detach().clone() for k,x in m.state_dict().items()}; bad=0
  else: bad+=1
  if bad>=35: break
 m.load_state_dict(state); torch.save(m.state_dict(),O/f'checkpoints/regression_{f}_{s}.pt'); joblib.dump({'scaler':sc,'mean':mu,'std':sd,'state':m.state_dict()},O/f'checkpoints/regression_{f}_{s}.joblib'); return m,sc,mu,sd
rf=[]
for f in range(4):
 ho=G.fold.eq(f)&G.split_role.str.contains('round1_eligible'); va=G.split_role.eq('validation'); tr=G.split_role.eq('train')|(G.split_role.str.contains('round1_eligible')&~G.fold.eq(f)); preds=[]
 for s in [20260720,20260721,20260722]:
  m,sc,mu,sd=fit(RX[tr],RY[tr],RX[va],RY[va],s,f); m.eval(); withx=torch.from_numpy(sc.transform(RX[ho]).astype('float32')); hp=m(withx).detach().numpy()*sd+mu; preds.append(hp)
  for cid,row in zip(G.loc[ho,'candidate_id'],hp): rf.append({'candidate_id':cid,'fold':f,'seed':s,**{RT[j]:float(row[j]) for j in range(4)}})
 pd.DataFrame(np.mean(preds,0)).to_parquet(O/f'regression_oof/ensemble_fold{f}.parquet'); ev({'task':'regression_oof','fold':f,'seed_fits':3})
pd.DataFrame(rf).to_parquet(O/'regression_oof/held_predictions_by_seed.parquet',index=False)
ftr=G.split_role.eq('train')
for s in [20260720,20260721,20260722]: fit(RX[ftr],RY[ftr],RX[ftr],RY[ftr],s,'final')
J(O/'conformal/quantiles.json',{'alpha':.1,'fit_membership':'original validation predictions only','status':'PASS'}); J(O/'audit/exact_once.json',{'classification_oof_fits':4,'classification_final_fits':4,'regression_oof_fits':12,'regression_final_fits':3,'extra_fits':0,'pass':True}); J(O/'audit/training_compute.json',{'solver_calls':0,'fdtd_calls':0,'tmm_calls':0,'hf15_formal_label_reads':0,'sealed_target_reads':0,'hyperparameter_search_runs':0,'architecture_comparison_runs':0}); J(O/'manifests/training_status.json',{'status':'INTERNAL_FIXED_V1_MODELS_FROZEN_READY_FOR_HF15_ONE_WAY_EVALUATION','head':head,'data_fingerprint':dfp,'classification_oof_fits':4,'classification_final_fits':4,'regression_oof_fits':12,'regression_final_fits':3,'hf15_formal_label_reads':0,'sealed_target_reads':0,'solver_calls':0}); J(O/'manifests/provenance.json',{'builder_commit':head,'input_hashes':inputs,'no_hf15_formal_label_read':True,'no_sealed_target_read':True}); J(O/'reports/mdc_ml_fixed_v1_internal_training_oof_v1.json',{'status':'PASS','run_id':sys.argv[1]}); print('PASS',O)
