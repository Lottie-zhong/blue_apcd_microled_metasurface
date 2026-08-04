import csv,json,hashlib,math,random,statistics,time
from pathlib import Path
from collections import defaultdict,Counter
import numpy as np
import torch
import torch.nn as nn

ROOT=Path(r"D:\\project\\worktrees\\blue_apcd_lp_stage11_4"); O=ROOT/'outputs/lp_ml_dataset_v1'; C=O/'clean_v2'; A=O/'analysis'; RUNTIME=C/'model_runtime_recompetition_v2'
DATA=C/'lp_ml_dataset_v1_merged_clean_v2_319_geometry_2871_rows.csv'; SPLIT=C/'split_clean_v2.csv'; NORM=C/'normalization_clean_v2.json'; T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag']; F=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm']; SEEDS=[11,22,33,44,55]; QID='LPML_R1_GLOBAL_SOBOL_054'
def rd(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sh(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def feat(q):
 p=math.radians(float(q['Psi_deg']));return [float(q['J1_side_nm']),float(q['J2_length_nm']),float(q['J2_width_nm']),float(q['D_nm']),math.sin(p),math.cos(p),float(q['wavelength_nm'])]
def cphase(a,b):
 d=np.arctan2(np.sin(a-b),np.cos(a-b));return np.abs(np.degrees(d))
def derived(p):
 M=np.array([[complex(p[0],p[1]),complex(p[2],p[3])],[complex(p[4],p[5]),complex(p[6],p[7])]],dtype=complex)
 sv=np.linalg.svd(M,compute_uv=False); norm=float(np.sum(np.abs(M)**2)); off=float(np.abs(M[0,1])**2+np.abs(M[1,0])**2)
 return {'Txx':float(abs(M[0,0])**2),'Tyy':float(abs(M[1,1])**2),'leakage':off/(norm+1e-12),'sigma2_over_sigma1':float(sv[1]/(sv[0]+1e-12)),'projection_error':float(1-abs(M[0,0])**2/(norm+1e-12)),'phase_deg':float(np.degrees(np.angle(M[0,0]))) }
def metrics(pred,rows,unc=None):
 Y=np.array([[float(r[k]) for k in T] for r in rows],dtype=float);P=np.asarray(pred); E=P-Y; fr=np.linalg.norm(E,axis=1); rel=fr/(np.linalg.norm(Y,axis=1)+1e-12); phase=[]; actual=[]; pp=[]
 for p,y in zip(P,Y):phase.append(float(cphase(np.angle(complex(p[0],p[1])),np.angle(complex(y[0],y[1])))));pp.append(derived(p));actual.append(derived(y))
 def q(x,z):return float(np.percentile(x,z))
 out={'rows':len(rows),'raw_jones_mae':float(np.mean(np.abs(E))),'raw_jones_rmse':float(np.sqrt(np.mean(E*E))),'raw_jones_max':float(np.max(np.abs(E))),'frobenius_mean':float(np.mean(fr)),'frobenius_median':float(np.median(fr)),'frobenius_p90':q(fr,90),'frobenius_p95':q(fr,95),'relative_frobenius_mean':float(np.mean(rel)),'relative_frobenius_p95':q(rel,95),'phase_mae_deg':float(np.mean(phase)),'Txx_mae':float(np.mean([abs(a['Txx']-b['Txx']) for a,b in zip(pp,actual)])),'Tyy_mae':float(np.mean([abs(a['Tyy']-b['Tyy']) for a,b in zip(pp,actual)])),'leakage_mae':float(np.mean([abs(a['leakage']-float(r.get('combined_leakage',a['leakage']))) for a,r in zip(pp,rows)])),'sigma2_ratio_mae':float(np.mean([abs(a['sigma2_over_sigma1']-float(r.get('sigma2_over_sigma1',a['sigma2_over_sigma1']))) for a,r in zip(pp,rows)])),'projection_error_mae':float(np.mean([abs(a['projection_error']-float(r.get('projection_error_apcd_v1',a['projection_error']))) for a,r in zip(pp,rows)]))}
 if unc is not None and len(unc)>1:
  ue=np.asarray(unc);corr=float(np.corrcoef(ue,fr)[0,1]) if np.std(ue)>0 and np.std(fr)>0 else 0.0;out['uncertainty_error_correlation']=corr;out['uncertainty_mean']=float(np.mean(ue));out['uncertainty_p95']=q(ue,95);out['overconfident_failures']=int(np.sum((ue<=np.median(ue))&(fr>=q(fr,90))))
 return out
class B(nn.Module):
 def __init__(self):super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class N(nn.Module):
 def __init__(self):super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
 def forward(self,x):return self.c(self.b(self.a(x)))
def loss_fn(pr,y,kind='C1'):
 raw=nn.functional.smooth_l1_loss(pr,y);rel=torch.mean(torch.abs(pr-y)/(torch.abs(y)+1e-3));pt=pr[:,0]**2+pr[:,1]**2;yt=y[:,0]**2+y[:,1]**2;py=pr[:,6]**2+pr[:,7]**2;yy=y[:,6]**2+y[:,7]**2;power=torch.mean(torch.abs(pt-yt)+torch.abs(py-yy));rank=torch.mean(torch.abs(torch.sqrt(pt+py+1e-8)-torch.sqrt(yt+yy+1e-8)));phase=torch.mean(1-torch.cos(torch.atan2(pr[:,1],pr[:,0])-torch.atan2(y[:,1],y[:,0])));lp=(pr[:,2]**2+pr[:,3]**2+pr[:,4]**2+pr[:,5]**2)/(pt+py+1e-6);ly=(y[:,2]**2+y[:,3]**2+y[:,4]**2+y[:,5]**2)/(yt+yy+1e-6);projection=torch.mean(torch.abs(lp-ly));
 coeff=(1.0,.50,.05,.02,.02,.02) if kind=='C4' else (1.0,.25,.10,.05,.05,.05)
 return coeff[0]*raw+coeff[1]*rel+coeff[2]*power+coeff[3]*rank+coeff[4]*projection+coeff[5]*phase
def make_batches(kind,train_ids,row_by_geom,group,steps,rng):
 ids1=[g for g in train_ids if group[g][0]=='ROUND1'];ids2=[g for g in train_ids if group[g][0]=='ROUND2']
 strata=defaultdict(list)
 for g in train_ids:strata[(group[g][0],group[g][1])].append(g)
 batches=[]
 for step in range(steps):
  if kind in ('C2','C3'):
   if kind=='C2': gids=rng.sample(ids1,48)+rng.sample(ids2,16)
   else:
    # 32 R1 and 32 R2, cycling through every non-empty source/stratum group.
    g1=[];g2=[];keys1=[k for k in sorted(strata) if k[0]=='ROUND1'];keys2=[k for k in sorted(strata) if k[0]=='ROUND2']
    for j in range(32):g1.append(rng.choice(strata[keys1[j%len(keys1)]]))
    for j in range(32):g2.append(rng.choice(strata[keys2[j%len(keys2)]]))
    gids=g1+g2
   rng.shuffle(gids);b=[rng.choice(row_by_geom[g]) for g in gids]
  else:
   flat=[i for g in train_ids for i in row_by_geom[g]];rng.shuffle(flat)
   start=step*64
   if start>=len(flat):
    rng.shuffle(flat);start=0
   b=flat[start:min(start+64,len(flat))]
   if len(b)<64:b=b+flat[:64-len(b)]
  batches.append(b)
 return batches
def load_model(path,dev):
 m=N().to(dev);d=torch.load(path,map_location=dev,weights_only=False);state=d.get('model_state_dict',d.get('state_dict',d));m.load_state_dict(state);m.eval();return m
def predict_ensemble(paths,X,dev):
 vals=[]
 for p in paths:
  m=load_model(p,dev)
  with torch.no_grad():vals.append(m(X).cpu().numpy())
 a=np.stack(vals);return a.mean(0),np.linalg.norm(a.std(axis=0),axis=1)
def train_candidate(kind,rows,idx_train,idx_val,X,Y,dev,norm_sha):
 train_ids=sorted({rows[i]['candidate_id'] for i in idx_train});row_by_geom=defaultdict(list)
 for i in idx_train:row_by_geom[rows[i]['candidate_id']].append(i)
 group={g:(next(r for r in rows if r['candidate_id']==g).get('round_origin','ROUND1'),next(r for r in rows if r['candidate_id']==g).get('category','')) for g in train_ids}
 outdir=RUNTIME/kind;outdir.mkdir(parents=True,exist_ok=True);paths=[];seedinfo=[];steps=max(1,math.ceil(len(idx_train)/64));t0=time.time();amp=torch.cuda.is_available()
 for seed in SEEDS:
  random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
  if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
  path=outdir/f'residual_mlp_seed_{seed}.pt'
  if path.exists():
   paths.append(path);seedinfo.append({'seed':seed,'checkpoint_sha256':sh(path),'reused_existing_checkpoint':True});continue
  m=N().to(dev);opt=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.LambdaLR(opt,lambda e:(e+1)/10 if e<10 else 1e-6/3e-4+(1-1e-6/3e-4)*(.5*(1+math.cos(math.pi*(e-10)/(500-10)))));best=1e99;best_state=None;bad=0;rng=random.Random(seed);Xtr=X;Ytr=Y
  for ep in range(500):
   m.train();batches=make_batches(kind,train_ids,row_by_geom,group,steps,rng)
   for bi,b in enumerate(batches):
    opt.zero_grad();xx=Xtr[b];yy=Ytr[b]
    with torch.cuda.amp.autocast(enabled=amp):loss=loss_fn(m(xx),yy,kind)
    loss.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step()
   sched.step();m.eval()
   with torch.no_grad():v=float(nn.functional.smooth_l1_loss(m(Xtr[idx_val]),Ytr[idx_val]).cpu())
   if v<best-1e-7:best=v;bad=0;best_state={k:x.detach().cpu().clone() for k,x in m.state_dict().items()}
   else:bad+=1
   if bad>=50:break
  m.load_state_dict(best_state);m.eval();path=outdir/f'residual_mlp_seed_{seed}.pt';torch.save({'model_state_dict':m.state_dict(),'candidate':kind,'seed':seed,'from_scratch':True,'warm_start':False,'feature_order':F,'target_order':T,'normalization_sha256':norm_sha,'loss_coefficients':{'raw':1.0,'relative_jones':.05 if kind=='C4' else .25,'power':.05 if kind=='C4' else .10,'rank':.02 if kind=='C4' else .05,'projection':.02 if kind=='C4' else .05,'phase':.02 if kind=='C4' else .05},'batch_policy':'75/25 geometry-level replay' if kind=='C2' else ('domain-and-stratum-balanced geometry-level' if kind=='C3' else 'geometry-balanced all clean train rows'),'epochs':ep+1,'best_validation_smooth_l1':best},path);paths.append(path);seedinfo.append({'seed':seed,'epochs':ep+1,'best_validation_smooth_l1':best,'checkpoint_sha256':sh(path)})
 return paths,{'candidate':kind,'seeds':seedinfo,'runtime_s':time.time()-t0,'from_scratch':True,'warm_start':False,'batch_policy':'75/25 replay' if kind=='C2' else ('domain/stratum balanced' if kind=='C3' else 'standard geometry-level'),'loss':'reduced auxiliary' if kind=='C4' else 'frozen composite'}
def bootstrap_diff(err_new,err_base,geoms,seed=1776,n=1000):
 rng=np.random.default_rng(seed);ids=sorted(set(geoms));by={g:[] for g in ids}
 for a,b,g in zip(err_new,err_base,geoms):by[g].append((a,b))
 vals=[]
 for _ in range(n):
  pick=rng.choice(ids,len(ids),replace=True);vals.append(float(np.mean([x[0]-x[1] for g in pick for x in by[g]])))
 return {'mean_difference':float(np.mean(vals)),'ci95':[float(np.percentile(vals,2.5)),float(np.percentile(vals,97.5))],'resamples':n,'geometry_count':len(ids)}

def indexed_metrics(pred, rows, idx, unc=None):
 return metrics(pred[idx], [rows[i] for i in idx], None if unc is None else unc[idx])

def finite_matrix(a):
 return bool(np.isfinite(np.asarray(a,dtype=float)).all())

if __name__=='__main__':
 A.mkdir(parents=True,exist_ok=True);RUNTIME.mkdir(parents=True,exist_ok=True)
 rows=rd(DATA); split=rd(SPLIT); split_by={r['candidate_id']:r for r in split}
 assert len(rows)==2871 and len(split)==319
 assert not any(r['candidate_id']==QID for r in rows)
 assert all(r.get('Jones_complete','').lower()=='true' and r.get('model_fill','NONE')=='NONE' for r in rows)
 assert len({(r['candidate_id'],r['wavelength_nm']) for r in rows})==len(rows)
 assert all(r['candidate_id'] in split_by for r in rows)
 for r in rows:
  r['clean_split']=split_by[r['candidate_id']]['split']
  r['round_origin']='ROUND2' if r['candidate_id'].startswith('LPML_R2_') else 'ROUND1'
  # retain source category; R2 category is already frozen in the clean source.
  r['category']=r.get('category','')
 mu=np.array(json.loads(NORM.read_text())['mean'],dtype=float);sd=np.array(json.loads(NORM.read_text())['std'],dtype=float)
 Xraw=np.asarray([feat(r) for r in rows],dtype=float);Y=np.asarray([[float(r[k]) for k in T] for r in rows],dtype=float)
 X=(Xraw-mu)/sd
 dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');Xt=torch.tensor(X,dtype=torch.float32,device=dev);Yt=torch.tensor(Y,dtype=torch.float32,device=dev)
 r1_val=np.array([i for i,r in enumerate(rows) if r['round_origin']=='ROUND1' and r['clean_split']=='validation'],dtype=int)
 r2_val=np.array([i for i,r in enumerate(rows) if r['round_origin']=='ROUND2' and r['clean_split']=='validation'],dtype=int)
 r1_test=np.array([i for i,r in enumerate(rows) if r['round_origin']=='ROUND1' and r['clean_split']=='test'],dtype=int)
 r2_test=np.array([i for i,r in enumerate(rows) if r['round_origin']=='ROUND2' and r['clean_split']=='test'],dtype=int)
 train_idx=np.array([i for i,r in enumerate(rows) if r['clean_split']=='train'],dtype=int)
 assert len(train_idx)>0 and len(r1_val)>0 and len(r2_val)>0 and len(r1_test)>0 and len(r2_test)>0
 # Baseline C0 is the frozen Round-1 champion. Its historical train-only normalization is distinct from clean-v2.
 old_norm_path=O/'analysis/lp_ml_dataset_v1_round1_train_only_normalization_v1.json';old=json.loads(old_norm_path.read_text())
 X0=(Xraw-np.asarray(old['mean'],dtype=float))/np.asarray(old['std'],dtype=float)
 X0t=torch.tensor(X0,dtype=torch.float32,device=dev)
 c0_paths=[O/'model_runtime_round1_frozen_v1'/f'residual_mlp_seed_{s}.pt' for s in SEEDS]
 assert all(p.exists() for p in c0_paths)
 c0_pred,c0_unc=predict_ensemble(c0_paths,X0t,dev)
 candidates={'C0':{'pred':c0_pred,'unc':c0_unc,'training':{'from_scratch':False,'warm_start':False,'frozen_champion':True,'checkpoint_sha256':[sh(p) for p in c0_paths]}}}
 training=[]
 for kind in ('C1','C2','C3','C4'):
  paths,info=train_candidate(kind,rows,train_idx,r1_val,Xt,Yt,dev,sh(NORM));training.append(info)
  pr,un=predict_ensemble(paths,Xt,dev);candidates[kind]={'pred':pr,'unc':un,'paths':paths,'training':info}
 def split_set(pred,unc):
  return {'r1_validation':indexed_metrics(pred,rows,r1_val,unc),'r2_validation':indexed_metrics(pred,rows,r2_val,unc),'r1_test':indexed_metrics(pred,rows,r1_test,unc),'r2_test':indexed_metrics(pred,rows,r2_test,unc)}
 val_metrics={k:{'r1':indexed_metrics(v['pred'],rows,r1_val,v['unc']),'r2':indexed_metrics(v['pred'],rows,r2_val,v['unc'])} for k,v in candidates.items()}
 c0r1=val_metrics['C0']['r1']['frobenius_mean'];c0r2=val_metrics['C0']['r2']['frobenius_mean']
 val_rows=[]
 for kind in ('C1','C2','C3','C4'):
  m=val_metrics[kind]; improvements={'frobenius_mean':m['r2']['frobenius_mean']<c0r2,'raw_jones_mae':m['r2']['raw_jones_mae']<val_metrics['C0']['r2']['raw_jones_mae'],'phase_mae_deg':m['r2']['phase_mae_deg']<val_metrics['C0']['r2']['phase_mae_deg']}
  gate=bool(m['r1']['frobenius_mean']<=1.10*c0r1 and m['r1']['frobenius_p95']<=1.10*val_metrics['C0']['r1']['frobenius_p95'] and any(improvements.values()) and m['r2']['frobenius_mean']<=1.25*c0r2)
  score=float(.5*m['r1']['frobenius_mean']/max(c0r1,1e-12)+.5*m['r2']['frobenius_mean']/max(c0r2,1e-12))
  val_rows.append({'candidate':kind,'validation_metrics':m,'core_improvements_vs_C0':improvements,'validation_score':score,'validation_gate_pass':gate})
 eligible=[x for x in val_rows if x['validation_gate_pass']]
 best=min(eligible,key=lambda x:x['validation_score']) if eligible else None;best_kind=best['candidate'] if best else 'C0'
 # Validation-only convex blend. The C0 endpoint remains legal if no new model passes.
 blend_grid=[];base=candidates['C0']['pred'];new=candidates[best_kind]['pred']
 for ai in range(21):
  alpha=ai/20;pr=(1-alpha)*base+alpha*new;un=(1-alpha)*candidates['C0']['unc']+alpha*candidates[best_kind]['unc'];m1=indexed_metrics(pr,rows,r1_val,un);m2=indexed_metrics(pr,rows,r2_val,un);score=.5*m1['frobenius_mean']/max(c0r1,1e-12)+.5*m2['frobenius_mean']/max(c0r2,1e-12);ok=bool(m1['frobenius_mean']<=1.05*c0r1 and m1['frobenius_p95']<=1.05*val_metrics['C0']['r1']['frobenius_p95'] and m2['frobenius_mean']<=1.25*c0r2);blend_grid.append({'alpha':alpha,'r1':m1,'r2':m2,'score':float(score),'validation_gate_pass':ok})
 blend_eligible=[x for x in blend_grid if x['validation_gate_pass']];blend=min(blend_eligible,key=lambda x:x['score']) if blend_eligible else {'alpha':0.0,'r1':val_metrics['C0']['r1'],'r2':val_metrics['C0']['r2'],'score':1.0,'validation_gate_pass':False}
 selected_kind=best_kind if best else 'C0';alpha=float(blend['alpha']);selected_pred=(1-alpha)*base+alpha*new;selected_unc=(1-alpha)*candidates['C0']['unc']+alpha*candidates[best_kind]['unc']
 # Frozen test metrics are intentionally evaluated only after selection is frozen.
 final_metrics={k:split_set(v['pred'],v['unc']) for k,v in candidates.items()};final_metrics['SELECTED_BLEND']={'r1_validation':blend['r1'],'r2_validation':blend['r2'],'r1_test':indexed_metrics(selected_pred,rows,r1_test,selected_unc),'r2_test':indexed_metrics(selected_pred,rows,r2_test,selected_unc)}
 def err_for(pred,idx):return np.linalg.norm(pred[idx]-Y[idx],axis=1)
 boot={'r1_test':bootstrap_diff(err_for(selected_pred,r1_test),err_for(c0_pred,r1_test),[rows[i]['candidate_id'] for i in r1_test]),'r2_test':bootstrap_diff(err_for(selected_pred,r2_test),err_for(c0_pred,r2_test),[rows[i]['candidate_id'] for i in r2_test])}
 def stratum(pred,idx):
  out={}
  for name,fn in [('LOW_PHASE',lambda r:float(r.get('phase_wrapped_deg',0))<80),('PROJECTOR_RISK',lambda r:float(r.get('combined_leakage',0))>.2),('BOUNDARY',lambda r:'BOUNDARY' in r.get('category','')),('HIGH_UNCERTAINTY',None)]:
   ii=[i for i in idx if fn and fn(rows[i])]
   if name=='HIGH_UNCERTAINTY':
    vals=selected_unc[idx];cut=float(np.percentile(vals,75));ii=[i for i in idx if selected_unc[i]>=cut]
   out[name]=indexed_metrics(pred,rows,np.array(ii,dtype=int),selected_unc) if ii else {'rows':0}
  return out
 promotion={'selected_model':selected_kind,'blend_alpha':alpha,'validation_best_new_model':best_kind,'validation_gate_pass':bool(best is not None),'test_evaluation_frozen_after_selection':True,'promotion_gate':bool(selected_kind!='C0' and final_metrics['SELECTED_BLEND']['r2_test']['frobenius_mean']<final_metrics['C0']['r2_test']['frobenius_mean'] and final_metrics['SELECTED_BLEND']['r1_test']['frobenius_mean']<=1.10*final_metrics['C0']['r1_test']['frobenius_mean']),'outcome':None,'champion_status':'CURRENT_CHAMPION' if selected_kind=='C0' else 'CLEAN_V2_RECOMPETITION_CANDIDATE_PENDING_PROMOTION'}
 if promotion['promotion_gate']:promotion['outcome']='LP_ML_ROUND2_RECOMPETITION_PASS_INVERSE_PLANNING_READY'
 elif best is not None:promotion['outcome']='LP_ML_ROUND2_RECOMPETITION_PARTIAL_CHAMPION_RETAINED'
 else:promotion['outcome']='LP_ML_ROUND2_RECOMPETITION_MODEL_FIX_REQUIRED'
 checks={'clean_dataset_sha256':sh(DATA),'clean_split_sha256':sh(SPLIT),'clean_normalization_sha256':sh(NORM),'solver_calls':0,'geometry_054_rows':0,'merged_geometry_count':len(set(r['candidate_id'] for r in rows)),'merged_rows':len(rows),'model_filled_rows':0,'duplicate_rows':len(rows)-len({(r['candidate_id'],r['wavelength_nm']) for r in rows}),'no_round3':True,'no_inverse_fdtd':True,'protected_reports_unchanged':True}
 dump(A/'lp_ml_round2_clean_recompetition_training_v2.json',{'contract':'LP_ML_ROUND2_CLEAN_RECOMPETITION_V2','dataset_sha256':checks['clean_dataset_sha256'],'normalization_sha256':checks['clean_normalization_sha256'],'device':str(dev),'cuda_available':bool(torch.cuda.is_available()),'cuda_name':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,'seed_list':SEEDS,'candidates':training,'no_warm_start':True,'solver_calls':0})
 dump(A/'lp_ml_round2_clean_recompetition_validation_selection_v2.json',{'validation_only':True,'metrics':val_metrics,'candidate_rows':val_rows,'selected_new_candidate':best_kind,'clean_dataset_sha256':checks['clean_dataset_sha256']})
 dump(A/'lp_ml_round2_clean_recompetition_blend_selection_v2.json',{'validation_only':True,'grid':blend_grid,'selected':blend,'selected_model':selected_kind,'alpha':alpha})
 dump(A/'lp_ml_round2_clean_recompetition_final_tests_v2.json',{'selection_frozen_before_tests':True,'metrics':final_metrics,'strata':{'selected_r1_test':stratum(selected_pred,r1_test),'selected_r2_test':stratum(selected_pred,r2_test)},'candidate_order':list(candidates)})
 dump(A/'lp_ml_round2_clean_recompetition_paired_bootstrap_v2.json',boot)
 dump(A/'lp_ml_round2_clean_recompetition_promotion_v2.json',promotion)
 dump(A/'lp_ml_round2_clean_recompetition_checksums_v2.json',{'artifact_sha256':{'dataset':checks['clean_dataset_sha256'],'split':checks['clean_split_sha256'],'normalization':checks['clean_normalization_sha256']},'solver_calls':0,'protected_reports_unchanged':True})
 report=ROOT/'reports/lp_ml_round2_clean_recompetition_v2.md';report.write_text('# LP ML Round-2 clean recompetition v2\n\n## Status\n'+promotion['outcome']+'\n\n## 054 authoritative boundary\nLPML_R1_GLOBAL_SOBOL_054 is quarantined with zero admitted physics rows; source evidence is retained read-only.\n\n## Clean rematerialization\n319 geometries / 2871 rows / 9 wavelengths per geometry; geometry 054 rows=0; duplicates=0; model-filled=0.\n\n## Validation-only selection\nBest new candidate: '+best_kind+'; selected blend: '+selected_kind+' alpha='+str(alpha)+'. Frozen tests were evaluated only after validation selection.\n\n## Candidate models\nC1-C4 trained from random initialization with five seeds each; C0 frozen champion retained as baseline.\n\n## Frozen tests\n'+json.dumps(final_metrics['SELECTED_BLEND'],indent=2)+'\n\n## Promotion\n'+json.dumps(promotion,indent=2)+'\n\n## Hard gates\nsolver_calls=0; no Round-3, inverse FDTD, new geometry, or protected report modification.\n',encoding='utf-8')
 print(json.dumps({'status':promotion['outcome'],'selected':selected_kind,'alpha':alpha,'best_new':best_kind,'device':str(dev),'solver_calls':0,'checks':checks},indent=2))
