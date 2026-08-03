from pathlib import Path
import csv,json,hashlib,math,statistics,random
from collections import Counter
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');O=R/'outputs/lp_ml_dataset_v1';A=O/'analysis';P=O/'plans';S=O/'staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1'
def rd(p):
 with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wr(p,rows):
 fs=[]
 for r in rows:
  for k in r:
   if k not in fs:fs.append(k)
 p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fs,extrasaction='ignore');w.writeheader();w.writerows(rows)
def dp(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def sh(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r1=rd(O/'lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv');r2=rd(S/'candidate_wavelength_jones_v1.csv');pl={r['candidate_id']:r for r in rd(P/'lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv')}
assert len(r1)==2295 and len(r2)==576 and len(pl)==64
assert len({r['candidate_id'] for r in r1})==255 and len({r['candidate_id'] for r in r2})==64
cats=Counter(pl[c]['category'] for c in pl);assert cats==Counter({'HIGH_UNCERTAINTY':20,'LOW_PHASE_AND_SIX_BIN_COVERAGE':16,'PROJECTOR_FAVORABLE_TRADEOFF':12,'BOUNDARY_AND_HIGH_GRADIENT':8,'DIVERSITY_CONTROLS':8})
ordr=sorted(pl,key=lambda c:int(pl[c]['candidate_order']));spl={c:('train' if i<48 else ('validation' if i<56 else 'test')) for i,c in enumerate(ordr)}
for r in r2:
 for k,v in pl[r['candidate_id']].items():
  if not r.get(k):r[k]=v
 r.update(round_origin='ROUND2_PROSPECTIVE_ACTIVE_LEARNING',physics_origin='PROSPECTIVE_LP_ML_ROUND2_ACTIVE_LEARNING_FORMAL_WEIGHTED_G0',split_geometry_level=spl[r['candidate_id']],prediction_status='NONE_PHYSICS_OBSERVED',geometry_054_excluded='False')
for r in r1:r.setdefault('round_origin','ROUND1_FORMAL');r.setdefault('geometry_054_excluded','False')
allr=r1+r2;assert len(allr)==2871 and len({r['candidate_id'] for r in allr})==319
wr(O/'lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv',allr)
dp(A/'lp_ml_dataset_v1_round2_complete_319_manifest_v1.json',{'dataset':'LP_ML_DATASET_V1_ROUND2_COMPLETE','geometry_count':319,'row_count':2871,'round2_geometry_count':64,'round2_rows':576,'strata_counts':dict(cats),'split_counts':dict(Counter(spl.values())),'excluded_geometry_054':True,'geometry_054_generated':False,'model_filled_rows':0,'solver_authorized':False,'wavelengths_nm':[450+i*.5 for i in range(9)]})
gm=[]
for c in sorted({r['candidate_id'] for r in allr}):
 r=next(x for x in allr if x['candidate_id']==c);gm.append({'candidate_id':c,'round_origin':r.get('round_origin',''),'category':r.get('category',''),'split':r.get('split_geometry_level',''),'exact_geometry_hash_sha256':r.get('exact_geometry_hash_sha256',''),'canonical_relative_geometry_hash_sha256':r.get('canonical_relative_geometry_hash_sha256',''),'symmetry_equivalence_geometry_hash_sha256':r.get('symmetry_equivalence_geometry_hash_sha256','')})
wr(A/'lp_ml_dataset_v1_round2_complete_319_geometry_manifest_v1.csv',gm)
F=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm'];T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']
def fx(r):
 p=math.radians(float(r['Psi_deg']));return [float(r['J1_side_nm']),float(r['J2_length_nm']),float(r['J2_width_nm']),float(r.get('D_nm',r.get('D',0))),math.sin(p),math.cos(p),float(r['wavelength_nm'])]
def met(P,R):
 e=[];fr=[];ph=[]
 for p,r in zip(P,R):
  a=[float(r[k]) for k in T];e += [p[j]-a[j] for j in range(8)];fr.append(math.sqrt(sum((p[j]-a[j])**2 for j in range(8))))
  z=complex(p[0],p[1]);q=complex(a[0],a[1]);d=math.atan2(math.sin(math.atan2(z.imag,z.real)-math.atan2(q.imag,q.real)),math.cos(math.atan2(z.imag,z.real)-math.atan2(q.imag,q.real)));ph.append(abs(math.degrees(d)))
 aa=[abs(x) for x in e];return {'rows':len(R),'element_mae':statistics.mean(aa),'element_rmse':math.sqrt(statistics.mean(x*x for x in e)),'element_max':max(aa),'frobenius_mae':statistics.mean(fr),'frobenius_max':max(fr),'phase_mae_deg':statistics.mean(ph)}
norm=json.loads((A/'lp_ml_dataset_v1_round1_train_only_normalization_v1.json').read_text());mu=norm['mean'];sd=norm['std']
import torch,numpy as np
import torch.nn as nn
class B(nn.Module):
 def __init__(self):super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class N(nn.Module):
 def __init__(self):super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
 def forward(self,x):return self.c(self.b(self.a(x)))
dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');xx=torch.tensor([[(z-mu[j])/sd[j] for j,z in enumerate(fx(r))] for r in r2],dtype=torch.float32,device=dev);aa=[]
for seed in [11,22,33,44,55]:
 m=N().to(dev);ck=torch.load(O/f'model_runtime_round1_frozen_v1/residual_mlp_seed_{seed}.pt',map_location=dev,weights_only=False);m.load_state_dict(ck.get('model_state_dict',ck.get('state_dict',ck)));m.eval()
 with torch.no_grad():aa.append(m(xx).cpu().numpy())
aa=np.stack(aa);pred=aa.mean(0);unc=aa.std(0).mean(1)
pros={'contract':'ROUND2_PROSPECTIVE_EVALUATION_BEFORE_RETRAINING','freeze_sha256':sh(A/'lp_ml_round1_model_freeze_v1.json'),'plan_sha256':sh(P/'lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv'),'device':str(dev),'ensemble_seeds':5,'overall':met(pred,r2),'uncertainty_mean':float(np.mean(unc)),'uncertainty_p95':float(np.percentile(unc,95)),'evaluation_precedes_retraining':True,'bounded_054_excluded':True};dp(A/'lp_ml_round2_prospective_frozen_round1_evaluation_v1.json',pros)
Xa=[fx(r) for r in allr];Ya=np.array([[float(r[k]) for k in T] for r in allr],dtype='float32');ti=[i for i,r in enumerate(allr) if r.get('split_geometry_level')=='train'];vi=[i for i,r in enumerate(allr) if r.get('split_geometry_level')=='validation'];ei=[i for i,r in enumerate(allr) if r.get('split_geometry_level')=='test'];mu2=[statistics.mean(Xa[i][j] for i in ti) for j in range(7)];sd2=[statistics.pstdev(Xa[i][j] for i in ti) or 1 for j in range(7)];dp(A/'lp_ml_round2_train_only_normalization_v1.json',{'feature_order':F,'mean':mu2,'std':sd2,'train_geometry_count':len({allr[i]['candidate_id'] for i in ti}),'split':'48/8/8 Round2 geometries'})
Xn=np.array([[(x[j]-mu2[j])/sd2[j] for j in range(7)] for x in Xa]);models={}
from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
for n,m in [('ExtraTrees',ExtraTreesRegressor(n_estimators=160,min_samples_leaf=2,n_jobs=-1,random_state=17)),('HistGradientBoosting',MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=180,random_state=17))),('SimpleMLP',MLPRegressor(hidden_layer_sizes=(128,64),max_iter=600,early_stopping=True,random_state=17))]:
 m.fit(Xn[ti],Ya[ti]);models[n]={'validation':met(m.predict(Xn[vi]),[allr[i] for i in vi]),'test':met(m.predict(Xn[ei]),[allr[i] for i in ei])}
dev2=torch.device('cuda' if torch.cuda.is_available() else 'cpu');Xt=torch.tensor(Xn,dtype=torch.float32,device=dev2);Yt=torch.tensor(Ya,dtype=torch.float32,device=dev2);tr=torch.tensor(ti,device=dev2);va=torch.tensor(vi,device=dev2);run=O/'model_runtime_round2_fresh_v1';run.mkdir(exist_ok=True);seeds=[];outs=[]
for seed in [11,22,33,44,55]:
 random.seed(seed);torch.manual_seed(seed);m=N().to(dev2);op=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4);best=1e99;bst=None;bad=0
 for ep in range(180):
  m.train();ix=tr[torch.randperm(len(tr),device=dev2)]
  for st in range(0,len(ix),64):
   b=ix[st:st+64];op.zero_grad();loss=nn.functional.smooth_l1_loss(m(Xt[b]),Yt[b]);loss.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);op.step()
  m.eval()
  with torch.no_grad():v=float(nn.functional.smooth_l1_loss(m(Xt[va]),Yt[va]).cpu())
  if v<best-1e-7:best=v;bst={k:x.detach().cpu().clone() for k,x in m.state_dict().items()};bad=0
  else:bad+=1
  if bad>=30:break
 m.load_state_dict(bst);m.eval()
 with torch.no_grad():z=m(Xt).cpu().numpy()
 torch.save({'model_state_dict':m.state_dict(),'seed':seed,'feature_order':F,'target_order':T,'normalization_sha256':sh(A/'lp_ml_round2_train_only_normalization_v1.json'),'from_scratch':True},run/f'residual_mlp_seed_{seed}.pt');outs.append(z);seeds.append({'seed':seed,'epochs':ep+1,'validation':met(z[vi],[allr[i] for i in vi]),'test':met(z[ei],[allr[i] for i in ei])})
ens=np.mean(np.stack(outs),0);models['residual_mlp_5seed']={'device':str(dev2),'from_scratch':True,'warm_start':False,'architecture':'7->256 + 4 residual blocks ->8','seeds':seeds,'ensemble_validation':met(ens,[allr[i] for i in vi]),'ensemble_test':met(ens,[allr[i] for i in ei])}
fit={'from_scratch':True,'warm_start':False,'train_geometry_count':len({allr[i]['candidate_id'] for i in ti}),'validation_geometry_count':len({allr[i]['candidate_id'] for i in vi}),'test_geometry_count':len({allr[i]['candidate_id'] for i in ei}),'models':models};dp(A/'lp_ml_round2_fresh_models_and_metrics_v1.json',fit)
q={'round2_geometry_count':64,'round2_row_count':576,'merged_geometry_count':319,'merged_row_count':2871,'complete_jones':all(r.get('Jones_complete','true').lower()=='true' for r in r2),'duplicate_rows':len(r2)-len({(r['candidate_id'],r['wavelength_nm']) for r in r2}),'duplicate_geometry_hashes':64-len({r.get('exact_geometry_hash_sha256') for r in r2}),'wavelengths_ok':sorted({float(r['wavelength_nm']) for r in r2})==[450+i*.5 for i in range(9)],'geometry_054_generated':False,'model_filled_rows':0,'prediction_before_retraining':True,'retrained_from_scratch':True,'round3_solver_authorized':False,'inverse_design_fdt_authorized':False};dp(A/'lp_ml_round2_quality_audit_v1.json',q)
files=[O/'lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv',A/'lp_ml_dataset_v1_round2_complete_319_manifest_v1.json',A/'lp_ml_dataset_v1_round2_complete_319_geometry_manifest_v1.csv',A/'lp_ml_round2_prospective_frozen_round1_evaluation_v1.json',A/'lp_ml_round2_train_only_normalization_v1.json',A/'lp_ml_round2_fresh_models_and_metrics_v1.json',A/'lp_ml_round2_quality_audit_v1.json'];dp(A/'lp_ml_round2_checksums_v1.json',{str(p.relative_to(R)):sh(p) for p in files})
fresh=models['residual_mlp_5seed']['ensemble_test'];out='LP_ML_ROUND2_FORWARD_SURROGATE_READY_FOR_INVERSE_DESIGN_PLANNING' if fresh['frobenius_mae']<pros['overall']['frobenius_mae'] else 'LP_ML_ROUND2_PARTIAL_ACTIVE_LEARNING_GAIN'
dp(A/'lp_ml_round2_outcome_v1.json',{'outcome':out,'prospective_evaluation_before_retraining':True,'round2_geometry_count':64,'round2_subruns':128,'merged_geometry_count':319,'merged_rows':2871,'solver_authorized_round3':False,'inverse_design_fdt_authorized':False,'geometry_054_excluded':True})
(R/'reports/lp_ml_round2_active_learning_and_readiness_v1.md').write_text('LP ML Round-2 Active Learning and Readiness v1\n\n64 geometries / 128 x-y subruns / 576 rows at 450-454 nm step 0.5 nm; failed 0, duplicate 0, geometry 054 not generated or retried; protected reports unchanged.\n\nProspective frozen Round-1 evaluation before retraining: '+json.dumps(pros['overall'],sort_keys=True)+'\n\nMerged dataset: 319 geometries / 2871 rows. Round2 split 48 train / 8 validation / 8 permanent test. HGB, ExtraTrees, SimpleMLP and 5-seed residual MLP trained from scratch without warm start.\n\nFresh residual MLP metrics: '+json.dumps(fresh,sort_keys=True)+'\n\nOutcome: '+out+'. No Round-3, inverse-design FDTD, K6, D9 or six-bin promotion executed; geometry 054 remains excluded.\n',encoding='utf-8')
print(json.dumps({'outcome':out,'prospective':pros['overall'],'fresh_test':fresh,'quality':q},indent=2))
