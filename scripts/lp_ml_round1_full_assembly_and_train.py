import csv,json,hashlib,math,statistics,random,time
from pathlib import Path
from collections import defaultdict,Counter
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4'); O=R/'outputs/lp_ml_dataset_v1'; S=O/'staging'; A=O/'analysis'; A.mkdir(parents=True,exist_ok=True)
def rd(p):
 with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wr(p,rows,fields):
 p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def dump(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def sh(p): return hashlib.sha256(p.read_bytes()).hexdigest()
src=[S/'lp_ml_dataset_v1_round1_smoke_attempt2_v1/candidate_wavelength_jones_v1.csv',S/'lp_ml_dataset_v1_round1_production_attempt1_v1/candidate_wavelength_jones_v1.csv',S/'lp_ml_dataset_v1_round1_continuation_attempt1_v1/candidate_wavelength_jones_v1.csv']
rows=[]
for p in src: rows+=rd(p)
rows=[r for r in rows if r['candidate_id']!='LPML_R1_GLOBAL_SOBOL_054']
ids=defaultdict(list)
for r in rows:ids[r['candidate_id']].append(r)
assert len(ids)==255 and all(len(v)==9 for v in ids.values())
plan={r['candidate_id']:r for r in rd(O/'plans/lp_ml_dataset_v1_round1_recovery_389_plan_v1.csv')}
plan.update({r['candidate_id']:r for r in rd(O/'plans/lp_ml_dataset_v1_round1_remaining_240_plan_v1.csv')})
plan.update({r['candidate_id']:r for r in rd(O/'plans/lp_ml_dataset_v1_round1_smoke_16_plan_v1.csv')})
missing=[c for c in ids if c not in plan or c=='LPML_R1_GLOBAL_SOBOL_054']
print('MISSING_PLAN',missing)
assert not missing
waves=[450+i*.5 for i in range(9)]
for c,v in ids.items():
 assert sorted(round(float(r['wavelength_nm']),3) for r in v)==[round(x,3) for x in waves]
 assert all(r['model_fill'] in ('NONE','') and r['Jones_complete'].lower()=='true' for r in v)
 for r in v:
  for k in ('category','J1_side_nm','J2_length_nm','J2_width_nm','D_nm','Psi_deg','exact_geometry_hash_sha256','canonical_relative_geometry_hash_sha256','symmetry_equivalence_geometry_hash_sha256','material','H_nm','period_x_nm','period_y_nm'):r[k]=plan[c][k]
 # group symmetry-equivalent geometries before assigning the split
 groups={}
 for cc in ids: groups.setdefault(plan[cc].get('symmetry_equivalence_geometry_hash_sha256','') or plan[cc]['exact_geometry_hash_sha256'],[]).append(cc)
 ordered=sorted(groups.items(),key=lambda kv:hashlib.sha256(kv[0].encode()).hexdigest()); total=len(ids);cuts=(.70*total,.85*total);assigned={};n=0
 for g,cs in ordered:
  target='train' if n<cuts[0] else ('validation' if n<cuts[1] else 'test')
  for cc in cs:assigned[cc]=target
  n+=len(cs)
 split=assigned[c]
 for r in v:r['split_geometry_level']=split
allrows=sorted(rows,key=lambda r:(r['candidate_id'],float(r['wavelength_nm'])))
ds=O/'lp_ml_dataset_v1_round1_complete_255_geometry_2295_rows.csv';wr(ds,allrows,list(allrows[0]))
strata=Counter(plan[c]['category'] for c in ids)
manifest={'contract':'LP_ML_DATASET_V1_ROUND1_COMPLETE_255_GEOMETRY_2295_ROWS','geometry_count':255,'row_count':len(allrows),'excluded_geometry':'LPML_R1_GLOBAL_SOBOL_054','excluded_rows':0,'waves':waves,'strata_counts':dict(strata),'model_filled_rows':0,'feature_order':['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm'],'target_order':['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag'],'split':'geometry-level deterministic SHA256 symmetry-group 70/15/15','split_group':'symmetry_equivalence_geometry_hash_sha256','solver_authorized':False}
dump(A/'lp_ml_dataset_v1_round1_complete_255_manifest_v1.json',manifest)
gm=[{'candidate_id':c,'category':plan[c]['category'],'split':ids[c][0]['split_geometry_level'],'geometry_hash_sha256':ids[c][0]['geometry_hash_sha256'],'symmetry_equivalence_geometry_hash_sha256':plan[c].get('symmetry_equivalence_geometry_hash_sha256','')} for c in sorted(ids)]
wr(A/'lp_ml_dataset_v1_round1_complete_255_geometry_manifest_v1.csv',gm,list(gm[0]))
feat=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm']; targ=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']
def fx(r):
 p=math.radians(float(r['Psi_deg']));return [float(r['J1_side_nm']),float(r['J2_length_nm']),float(r['J2_width_nm']),float(r['D_nm']),math.sin(p),math.cos(p),float(r['wavelength_nm'])]
X=[fx(r) for r in allrows];Y=[[float(r[k]) for k in targ] for r in allrows];ti=[i for i,r in enumerate(allrows) if r['split_geometry_level']=='train'];tei=[i for i,r in enumerate(allrows) if r['split_geometry_level']=='test']
mu=[statistics.mean(X[i][j] for i in ti) for j in range(7)];sd=[statistics.pstdev(X[i][j] for i in ti) or 1 for j in range(7)]
dump(A/'lp_ml_dataset_v1_round1_train_only_normalization_v1.json',{'feature_order':feat,'mean':mu,'std':sd,'train_only':True})
def met(P,I):
 e=[float(P[i][j]-Y[i][j]) for i in I for j in range(8)];f=[float(math.sqrt(sum((P[i][j]-Y[i][j])**2 for j in range(8)))) for i in I];a=[abs(x) for x in e]
 out={'mae':float(statistics.mean(a)),'rmse':float(math.sqrt(statistics.mean(x*x for x in e))),'max_abs':float(max(a)),'frobenius_mean':float(statistics.mean(f)),'frobenius_median':float(statistics.median(f)),'frobenius_p90':float(sorted(f)[int(.9*len(f))-1]),'frobenius_p95':float(sorted(f)[int(.95*len(f))-1])}
 phase=[];tx=[];ty=[];sig=[];leak=[];proj=[]
 for i in I:
  z=complex(P[i][0],P[i][1]);zt=complex(Y[i][0],Y[i][1]); phase.append(abs(math.degrees(math.atan2(math.sin(math.atan2(z.imag,z.real)-math.atan2(zt.imag,zt.real)),math.cos(math.atan2(z.imag,z.real)-math.atan2(zt.imag,zt.real))))) if abs(z)>1e-9 and abs(zt)>1e-9 else 0.0);tx.append(abs(z)**2-(Y[i][0]**2+Y[i][1]**2));ty.append((P[i][6]**2+P[i][7]**2)-(Y[i][6]**2+Y[i][7]**2));leak.append((P[i][2]**2+P[i][3]**2+P[i][4]**2+P[i][5]**2)/(sum(P[i][j]**2 for j in range(8))+1e-9)-(Y[i][2]**2+Y[i][3]**2+Y[i][4]**2+Y[i][5]**2)/(sum(Y[i][j]**2 for j in range(8))+1e-9));proj.append(abs(leak[-1]))
 out.update({'phase_circular_deg_mae':float(statistics.mean(phase)),'Txx_mae':float(statistics.mean(abs(x) for x in tx)),'Tyy_mae':float(statistics.mean(abs(x) for x in ty)),'leakage_fraction_mae':float(statistics.mean(abs(x) for x in leak)),'projection_error_proxy_mae':float(statistics.mean(proj))});return out
try:
 import numpy as np
 from sklearn.ensemble import ExtraTreesRegressor,HistGradientBoostingRegressor
 from sklearn.multioutput import MultiOutputRegressor
 from sklearn.neural_network import MLPRegressor
 xn=np.array([[(z[j]-mu[j])/sd[j] for j in range(7)] for z in X]);yn=np.array(Y);bm={}
 for n,m in [('ExtraTreesRegressor',ExtraTreesRegressor(n_estimators=120,min_samples_leaf=2,n_jobs=-1,random_state=17)),('HistGradientBoosting',MultiOutputRegressor(HistGradientBoostingRegressor(max_iter=160,random_state=17))),('SimpleMLP',MLPRegressor(hidden_layer_sizes=(128,64),max_iter=500,early_stopping=True,random_state=17))]:m.fit(xn[ti],yn[ti]);bm[n]={'test':met(m.predict(xn),tei)}
 dump(A/'lp_ml_round1_full_tree_and_simple_baselines_v1.json',{'from_scratch':True,'feature_order':feat,'models':bm})
except Exception as e:dump(A/'lp_ml_round1_full_tree_and_simple_baselines_v1.json',{'from_scratch':True,'error':repr(e)})
try:
 import torch,torch.nn as nn
 dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');Xt=torch.tensor([[(z[j]-mu[j])/sd[j] for j in range(7)] for z in X],dtype=torch.float32,device=dev);Yt=torch.tensor(Y,dtype=torch.float32,device=dev); tr=torch.tensor(ti,device=dev)
 class B(nn.Module):
  def __init__(self):super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
  def forward(self,x):return x+self.net(x)
 class N(nn.Module):
  def __init__(self):super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
  def forward(self,x):return self.c(self.b(self.a(x)))
 out=[];sm=[];t0=time.time(); vi=torch.tensor([i for i,r in enumerate(allrows) if r['split_geometry_level']=='validation'],device=dev); amp_enabled=torch.cuda.is_available(); scaler=torch.cuda.amp.GradScaler(enabled=amp_enabled)
 for seed in [11,22,33,44,55]:
  random.seed(seed);torch.manual_seed(seed)
  if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
  m=N().to(dev);o=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4); sched=torch.optim.lr_scheduler.LambdaLR(o,lambda e:(e+1)/10 if e<10 else 1e-6/3e-4+(1-1e-6/3e-4)*(.5*(1+math.cos(math.pi*(e-10)/(500-10)))));best=float('inf');best_state=None;bad=0
  for ep in range(500):
   m.train();perm=tr[torch.randperm(len(tr),device=dev)]
   for st in range(0,len(perm),64):
    b=perm[st:st+64];o.zero_grad()
    with torch.cuda.amp.autocast(enabled=amp_enabled):
     pr=m(Xt[b]);raw=nn.functional.smooth_l1_loss(pr,Yt[b]);rel=torch.mean(torch.abs(pr-Yt[b])/(torch.abs(Yt[b])+1e-3));pt=pr[:,0]**2+pr[:,1]**2;yt=Yt[b,0]**2+Yt[b,1]**2;py=pr[:,6]**2+pr[:,7]**2;yy=Yt[b,6]**2+Yt[b,7]**2;power=torch.mean(torch.abs(pt-yt)+torch.abs(py-yy));phase=torch.mean(1-torch.cos(torch.atan2(pr[:,1],pr[:,0])-torch.atan2(Yt[b,1],Yt[b,0])));rank=torch.mean(torch.abs(torch.sqrt(pt+py+1e-8)-torch.sqrt(yt+yy+1e-8)));projection=torch.mean(torch.abs((pr[:,2]**2+pr[:,3]**2+pr[:,4]**2+pr[:,5]**2)/(pt+py+1e-6)-(Yt[b,2]**2+Yt[b,3]**2+Yt[b,4]**2+Yt[b,5]**2)/(yt+yy+1e-6)));loss=raw+.25*rel+.10*power+.05*rank+.05*projection+.05*phase
    scaler.scale(loss).backward();scaler.unscale_(o);nn.utils.clip_grad_norm_(m.parameters(),1.0);scaler.step(o);scaler.update()
   sched.step();m.eval()
   with torch.no_grad():
    vp=m(Xt[vi]);v=float(nn.functional.smooth_l1_loss(vp,Yt[vi]).detach().cpu())
   if v<best-1e-7:best=v;bad=0;best_state={k:x.detach().cpu().clone() for k,x in m.state_dict().items()}
   else:bad+=1
   if bad>=50:break
  if best_state:m.load_state_dict(best_state)
  p=m(Xt).detach().cpu().numpy();out.append(p);sm.append({'seed':seed,'epochs':ep+1,'best_validation_raw_smoothl1':best,'test':met(p,tei)})
 ens=np.mean(np.stack(out),axis=0);stdp=np.std(np.stack(out),axis=0);unc=[float(np.linalg.norm(stdp[i])) for i in tei];err=[float(math.sqrt(sum((ens[i][j]-Y[i][j])**2 for j in range(8)))) for i in tei];corr=float(np.corrcoef(unc,err)[0,1]) if len(unc)>1 else 0.0;bins=[]
 for lo,hi in zip([0,.25,.5,.75],[.25,.5,.75,1.01]):
  jj=[k for k,u in enumerate(unc) if (u>=lo*max(unc) and u<hi*max(unc))];bins.append({'bin':[lo,hi],'count':len(jj),'mean_uncertainty':float(statistics.mean([unc[k] for k in jj])) if jj else None,'mean_error':float(statistics.mean([err[k] for k in jj])) if jj else None})
 dump(A/'lp_ml_round1_full_residual_mlp_5seed_v1.json',{'from_scratch':True,'warm_start':False,'architecture':'7->256 + 4 residual blocks width256 SiLU LayerNorm dropout0.03 -> 8','loss':'1.00 Huber raw + 0.25 relative Jones + 0.10 power + 0.05 rank + 0.05 projection + 0.05 amplitude-masked circular phase','device':str(dev),'cuda_available':bool(torch.cuda.is_available()),'cuda_name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'amp_enabled':amp_enabled,'batch_size':64,'warmup_epochs':10,'cosine_to':1e-6,'max_epochs':500,'patience':50,'gradient_clip':1.0,'seeds':sm,'ensemble_test':met(ens,tei),'uncertainty_error_correlation':corr,'uncertainty_calibration_bins':bins,'ensemble_mean_l2_std':float(statistics.mean(unc)),'runtime_s':time.time()-t0})
except Exception as e:dump(A/'lp_ml_round1_full_residual_mlp_5seed_v1.json',{'from_scratch':True,'warm_start':False,'error':repr(e)})
if 'ens' in globals():
 groups={'GLOBAL_SOBOL':lambda r:r['category']=='GLOBAL_SOBOL','PHASE_REGION':lambda r:r['category']=='PHASE_REGION','PROJECTOR_REGION':lambda r:r['category']=='PROJECTOR_REGION','BOUNDARY_FAILURE':lambda r:r['category']=='BOUNDARY_FAILURE','WAVELENGTH_450':lambda r:float(r['wavelength_nm'])==450.0,'WAVELENGTH_454':lambda r:float(r['wavelength_nm'])==454.0,'PHASE_WRAP_VICINITY':lambda r:abs(abs(float(r.get('phase_wrapped_deg',0)))-180)<20,'LOW_PHASE':lambda r:float(r.get('phase_wrapped_deg',0))<80}
 subgroup={k:met(ens,[i for i,r in enumerate(allrows) if f(r)]) for k,f in groups.items()};dump(A/'lp_ml_round1_residual_mlp_evaluation_v1.json',{'metrics_by_stratum_or_slice':subgroup,'evaluation_contract':'raw Jones / Txx Tyy / phase circular / Frobenius; no threshold labels'})
qa={'geometry_count':len(ids),'row_count':len(allrows),'has_054':any(r['candidate_id']=='LPML_R1_GLOBAL_SOBOL_054' for r in allrows),'duplicate_rows':len(allrows)-len(set((r['candidate_id'],r['wavelength_nm']) for r in allrows)),'duplicate_geometry_hashes':len(ids)-len(set(v[0]['geometry_hash_sha256'] for v in ids.values())),'all_complete_jones':all(r['Jones_complete'].lower()=='true' for r in allrows),'model_filled_rows':0,'positive_T':all(float(r['Txx'])>=0 and float(r['Tyy'])>=0 for r in allrows),'solver_authorized':False,'no_active_learning':True,'no_d9':True}
dump(A/'lp_ml_dataset_v1_round1_complete_255_quality_audit_v1.json',qa);dump(A/'lp_ml_dataset_v1_round1_complete_255_checksums_v1.json',{'dataset_sha256':sh(ds),'manifest_sha256':sh(A/'lp_ml_dataset_v1_round1_complete_255_manifest_v1.json'),'quality_sha256':sh(A/'lp_ml_dataset_v1_round1_complete_255_quality_audit_v1.json')})
print(json.dumps({'geometry_count':len(ids),'rows':len(allrows),'strata':dict(strata),'qa':qa}))
