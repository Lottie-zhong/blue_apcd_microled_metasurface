from pathlib import Path
import csv,json,math,statistics,random,time
import numpy as np,torch
import torch.nn as nn
R=Path(r'D:\project\worktrees\blue_apcd_lp_stage11_4');O=R/'outputs/lp_ml_dataset_v1';A=O/'analysis'
def rd(p):
 with open(p,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
r=rd(O/'lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv');T=['txx_real','txx_imag','txy_real','txy_imag','tyx_real','tyx_imag','tyy_real','tyy_imag'];F=['J1_side_nm','J2_length_nm','J2_width_nm','D_nm','sin_Psi','cos_Psi','wavelength_nm']
def fx(q):
 p=math.radians(float(q['Psi_deg']));return [float(q['J1_side_nm']),float(q['J2_length_nm']),float(q['J2_width_nm']),float(q.get('D_nm',q.get('D',0))),math.sin(p),math.cos(p),float(q['wavelength_nm'])]
def met(P,R):
 e=[];fr=[];ph=[]
 for p,q in zip(P,R):
  a=np.array([float(q[k]) for k in T]);e.extend((p-a).tolist());fr.append(float(np.linalg.norm(p-a)));z=complex(float(p[0]),float(p[1]));w=complex(a[0],a[1]);d=math.atan2(math.sin(math.atan2(z.imag,z.real)-math.atan2(w.imag,w.real)),math.cos(math.atan2(z.imag,z.real)-math.atan2(w.imag,w.real)));ph.append(abs(math.degrees(d)))
 return {'rows':len(R),'element_mae':float(np.mean(np.abs(e))),'element_rmse':float(np.sqrt(np.mean(np.array(e)**2))),'element_max':float(np.max(np.abs(e))),'frobenius_mae':float(np.mean(fr)),'frobenius_max':float(np.max(fr)),'phase_mae_deg':float(np.mean(ph))}
class B(nn.Module):
 def __init__(self):super().__init__();self.net=nn.Sequential(nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03),nn.Linear(256,256),nn.SiLU(),nn.LayerNorm(256),nn.Dropout(.03))
 def forward(self,x):return x+self.net(x)
class N(nn.Module):
 def __init__(self):super().__init__();self.a=nn.Sequential(nn.Linear(7,256),nn.SiLU(),nn.LayerNorm(256));self.b=nn.Sequential(B(),B(),B(),B());self.c=nn.Linear(256,8)
 def forward(self,x):return self.c(self.b(self.a(x)))
Xa=[fx(q) for q in r];Y=np.array([[float(q[k]) for k in T] for q in r],dtype='float32');ti=[i for i,q in enumerate(r) if q.get('split_geometry_level')=='train'];vi=[i for i,q in enumerate(r) if q.get('split_geometry_level')=='validation'];ei=[i for i,q in enumerate(r) if q.get('split_geometry_level')=='test'];mu=[statistics.mean(Xa[i][j] for i in ti) for j in range(7)];sd=[statistics.pstdev(Xa[i][j] for i in ti) or 1 for j in range(7)];X=np.array([[(x[j]-mu[j])/sd[j] for j in range(7)] for x in Xa],dtype='float32');dev=torch.device('cuda' if torch.cuda.is_available() else 'cpu');Xt=torch.tensor(X,device=dev);Yt=torch.tensor(Y,device=dev);tr=torch.tensor(ti,device=dev);va=torch.tensor(vi,device=dev);run=O/'model_runtime_round2_fresh_v1';run.mkdir(exist_ok=True);seeds=[];outs=[];t0=time.time()
for seed in [11,22,33,44,55]:
 random.seed(seed);torch.manual_seed(seed)
 if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
 m=N().to(dev);op=torch.optim.AdamW(m.parameters(),lr=3e-4,weight_decay=1e-4);sched=torch.optim.lr_scheduler.LambdaLR(op,lambda e:(e+1)/10 if e<10 else 1e-6/3e-4+(1-1e-6/3e-4)*(0.5*(1+math.cos(math.pi*(e-10)/(500-10)))));best=1e99;bst=None;bad=0
 for ep in range(500):
  m.train();ix=tr[torch.randperm(len(tr),device=dev)]
  for st in range(0,len(ix),64):
   b=ix[st:st+64];op.zero_grad();pr=m(Xt[b]);raw=nn.functional.smooth_l1_loss(pr,Yt[b]);rel=torch.mean(torch.abs(pr-Yt[b])/(torch.abs(Yt[b])+1e-3));pt=pr[:,0]**2+pr[:,1]**2;yt=Yt[b,0]**2+Yt[b,1]**2;py=pr[:,6]**2+pr[:,7]**2;yy=Yt[b,6]**2+Yt[b,7]**2;power=torch.mean(torch.abs(pt-yt)+torch.abs(py-yy));rank=torch.mean(torch.abs(torch.sqrt(pt+py+1e-8)-torch.sqrt(yt+yy+1e-8)));phase=torch.mean(1-torch.cos(torch.atan2(pr[:,1],pr[:,0])-torch.atan2(Yt[b,1],Yt[b,0])));lp=(pr[:,2]**2+pr[:,3]**2+pr[:,4]**2+pr[:,5]**2)/(pt+py+1e-6);ly=(Yt[b,2]**2+Yt[b,3]**2+Yt[b,4]**2+Yt[b,5]**2)/(yt+yy+1e-6);projection=torch.mean(torch.abs(lp-ly));loss=raw+.25*rel+.10*power+.05*rank+.05*projection+.05*phase;loss.backward();nn.utils.clip_grad_norm_(m.parameters(),1.0);op.step()
  sched.step();m.eval()
  with torch.no_grad():v=float(nn.functional.smooth_l1_loss(m(Xt[va]),Yt[va]).cpu())
  if v<best-1e-7:best=v;bst={k:x.detach().cpu().clone() for k,x in m.state_dict().items()};bad=0
  else:bad+=1
  if bad>=50:break
 m.load_state_dict(bst);m.eval()
 with torch.no_grad():z=m(Xt).cpu().numpy()
 torch.save({'model_state_dict':m.state_dict(),'seed':seed,'feature_order':F,'target_order':T,'normalization_mean':mu,'normalization_std':sd,'normalization_sha256':__import__('hashlib').sha256((A/'lp_ml_round2_train_only_normalization_v1.json').read_bytes()).hexdigest(),'from_scratch':True,'loss':'Round-1 composite raw+relative+power+rank+projection+phase','max_epochs':500,'patience':50,'warm_start':False},run/f'residual_mlp_seed_{seed}.pt');outs.append(z);seeds.append({'seed':seed,'epochs':ep+1,'best_validation_raw_smoothl1':best,'validation':met(z[vi],[r[i] for i in vi]),'test':met(z[ei],[r[i] for i in ei])})
ens=np.mean(np.stack(outs),0);fit=json.loads((A/'lp_ml_round2_fresh_models_and_metrics_v1.json').read_text());fit.update({'from_scratch':True,'warm_start':False,'loss':'Round-1 composite: 1.00 raw + 0.25 relative Jones + 0.10 power + 0.05 rank + 0.05 projection + 0.05 circular phase','max_epochs':500,'patience':50,'gradient_clip':1.0,'train_geometry_count':len({r[i]['candidate_id'] for i in ti}),'validation_geometry_count':len({r[i]['candidate_id'] for i in vi}),'test_geometry_count':len({r[i]['candidate_id'] for i in ei}),'residual_mlp_5seed':{'device':str(dev),'architecture':'7->256 + 4 residual blocks width256 SiLU LayerNorm dropout0.03 ->8','from_scratch':True,'warm_start':False,'loss':'Round-1 composite','seeds':seeds,'ensemble_validation':met(ens[vi],[r[i] for i in vi]),'ensemble_test':met(ens[ei],[r[i] for i in ei]),'runtime_s':time.time()-t0}});fit['models']['residual_mlp_5seed']=fit.pop('residual_mlp_5seed');(A/'lp_ml_round2_fresh_models_and_metrics_v1.json').write_text(json.dumps(fit,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8');print(json.dumps(fit['models']['residual_mlp_5seed']['ensemble_test']))
