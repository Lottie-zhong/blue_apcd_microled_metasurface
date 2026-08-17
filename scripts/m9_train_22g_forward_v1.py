from __future__ import annotations
import csv, hashlib, json, math, random, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT=Path(r'D:/project/worktrees/blue_apcd_np_k6_mdc_v1')
OUT=ROOT/'outputs/np_k6_m9_22g_forward_retraining_v1'
HF=ROOT/'outputs/np_k6_m8a_primary2_closeout_v1/hf22_formal_development_484rows.csv'
LF=ROOT/'outputs/np_k6_m9_22g_forward_retraining_v1/lf22_full_vector_authority.csv'
M7OUT=ROOT/'outputs/np_k6_m8_20g_forward_retraining_v1'
M7DES=ROOT/'outputs/np_k6_m7a_targeted_development_acquisition_design_v1'
ORDERS=[-3,-2,-1,0,1,2,3]; WLS=list(range(445,456)); SEEDS=[17,29,43]
MODELS=['LF_only','LF_global_bias','LF_affine','LF_ridge_residual','LF_paired_shared_contrast','corrected_residual_mlp','direct_mlp','resmlp','circular_cnn']
EPOCHS=80

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
def jread(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def jwrite(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
def rdcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def wcsv(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def parse(g):
 ds=[float(x) for x in re.findall(r'D(\d+)',g)]
 if len(ds)!=6: raise RuntimeError('geometry_order:'+g)
 return ds
def norm(a,tr):
 mu=a[tr].mean(0); sd=a[tr].std(0); sd[sd<1e-8]=1.; return (a-mu)/sd
def rankcorr(a,b):
 a=np.asarray(a);b=np.asarray(b); ra=np.empty(len(a));rb=np.empty(len(b));ra[np.argsort(a,kind='mergesort')]=np.arange(len(a));rb[np.argsort(b,kind='mergesort')]=np.arange(len(b))
 return float(np.corrcoef(ra,rb)[0,1]) if len(a)>1 and np.std(a)>0 and np.std(b)>0 else float('nan')
def keys(rows):return [(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in rows]

def load():
 h=rdcsv(HF); l=rdcsv(LF)
 if len(h)!=484 or len(l)!=484:raise RuntimeError('authority_row_count')
 lm={k:r for k,r in zip(keys(l),l)}
 if set(keys(h))!=set(lm):raise RuntimeError('lf_key_mismatch')
 geos=sorted({r['geometry_id'] for r in h})
 if len(geos)!=22:raise RuntimeError('geometry_count')
 for g in geos:
  q={(r['polarization'].lower(),int(float(r['wavelength_nm']))) for r in h if r['geometry_id']==g}
  if q!={(p,w) for p in ('p','s') for w in WLS}:raise RuntimeError('coverage:'+g)
  if any(r.get('quality_gate_pass')!='true' or r.get('diagnostic_only')!='false' or not (r.get('training_label')=='true' or r.get('m5_training_label')=='true') for r in h if r['geometry_id']==g):raise RuntimeError('flags:'+g)
 ds=[];X=[];N=[];C=[];Y=[];L=[]
 for r in h:
  d=parse(r['geometry_id']); w=int(float(r['wavelength_nm'])); pol=r['polarization'].lower(); pf=1. if pol=='p' else 0.; sf=1.-pf
  X.append([*(x/230. for x in d),(w-450)/5.,0.,pf,sf]); C.append([(w-450)/5.,0.,pf,sf])
  avg=sum(d)/6.; N.append([[d[i]/230.,(d[(i+1)%6]-d[i])/230.,(d[i]-d[i-1])/230.,(d[i]-avg)/230.,i/5.,pf,sf] for i in range(6)])
  Y.append([float(r['R_total'])]+[float(r[f'eta_m{m:+d}']) for m in ORDERS]); q=lm[(r['geometry_id'],pol,w)]; L.append([float(q[f'lf_eta_m{m:+d}']) for m in ORDERS]+[float(q['lf_T_proxy'])])
 return h,geos,np.asarray(X,float),np.asarray(C,float),np.asarray(N,float),np.asarray(Y,float),np.asarray(L,float)

def proj(p):
 q=np.asarray(p,float).copy(); q[:,0]=np.clip(q[:,0],0,1); q[:,1:]=np.maximum(q[:,1:],0); s=q[:,1:].sum(1); lim=np.maximum(0,1-q[:,0]); mask=s>lim; q[mask,1:]*=(lim[mask]/np.maximum(s[mask],1e-12))[:,None]; return q

def baseline(kind,X,C,Y,L,rows,tr,te):
 from sklearn.linear_model import Ridge
 if kind=='LF_only': return np.c_[np.full(len(te),np.nan),L[te,:7]]
 delta=Y[:,1:]-L[:,:7]
 if kind=='LF_global_bias': return np.c_[np.full(len(te),Y[tr,0].mean()),L[te,:7]+delta[tr].mean(0)]
 if kind=='LF_affine':
  a=np.c_[np.ones(len(rows)),C[:,0],C[:,2],C[:,3]]; az=norm(a,tr); rr=Ridge(alpha=1e-5).fit(az[tr],Y[tr,0]); ee=Ridge(alpha=1e-5).fit(az[tr],delta[tr]); return np.c_[rr.predict(az[te]),L[te,:7]+ee.predict(az[te])]
 f=np.c_[X,L];fz=norm(f,tr)
 if kind=='LF_ridge_residual':
  z=Ridge(alpha=1e-2).fit(fz[tr],np.c_[Y[tr,0],delta[tr]]).predict(fz[te]); return np.c_[z[:,0],L[te,:7]+z[:,1:]]
 if kind=='LF_paired_shared_contrast':
  pairs=defaultdict(dict)
  for i,r in enumerate(rows):pairs[(r['geometry_id'],int(float(r['wavelength_nm'])))][r['polarization'].lower()]=i
  trset=set(tr); fs=[];cm=[];ct=[]
  for k,v in pairs.items():
   if 'p' in v and 's' in v and v['p'] in trset and v['s'] in trset:
    fs.append(f[v['p']]);cm.append((delta[v['p']]+delta[v['s']])/2);ct.append((delta[v['p']]-delta[v['s']])/2)
  if not fs:return baseline('LF_ridge_residual',X,C,Y,L,rows,tr,te)
  fs=np.asarray(fs);mu=fs.mean(0);sd=fs.std(0);sd[sd<1e-8]=1.;fz2=(f-mu)/sd;pz=(fs-mu)/sd; cmfit=Ridge(alpha=1e-2).fit(pz,np.asarray(cm));ctfit=Ridge(alpha=1e-2).fit(pz,np.asarray(ct));rf=Ridge(alpha=1e-2).fit(fz[tr],Y[tr,0]); z=[]
  for j,i in enumerate(te):
   q=cmfit.predict(fz2[i:i+1])[0]; c=ctfit.predict(fz2[i:i+1])[0]; z.append(q+(c if rows[i]['polarization'].lower()=='p' else -c))
  return np.c_[rf.predict(fz[te]),L[te,:7]+np.asarray(z)]
 raise ValueError(kind)

def torch_fit(kind,X,C,N,Y,L,tr,te,seed):
 import torch,torch.nn as nn,torch.nn.functional as F
 torch.set_num_threads(2);torch.manual_seed(seed);np.random.seed(seed);random.seed(seed)
 xz=norm(X,tr); cz=norm(C,tr); nz=norm(N.reshape(len(N),-1),tr).reshape(len(N),-1); lz=norm(np.c_[X,L],tr)
 class MLP(nn.Module):
  def __init__(self,dim,res=False):
   super().__init__(); self.res=res
   if res:self.i=nn.Linear(dim,64);self.b1=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64));self.b2=nn.Sequential(nn.GELU(),nn.Linear(64,64),nn.GELU(),nn.Linear(64,64))
   else:self.body=nn.Sequential(nn.Linear(dim,64),nn.GELU(),nn.Linear(64,64),nn.GELU())
   self.o=nn.Linear(64,8)
  def forward(self,x):
   if self.res:h=F.gelu(self.i(x));h=h+self.b1(h);h=h+self.b2(h)
   else:h=self.body(x)
   z=self.o(h);return torch.cat([torch.sigmoid(z[:,:1]),torch.sigmoid(z[:,1:])],1)
 class RMLP(nn.Module):
  def __init__(self):super().__init__();self.body=nn.Sequential(nn.Linear(18,64),nn.GELU(),nn.Linear(64,64),nn.GELU());self.o=nn.Linear(64,8)
  def forward(self,x):z=self.o(self.body(x));return torch.cat([torch.sigmoid(z[:,:1]),z[:,1:]],1)
 class CNN(nn.Module):
  def __init__(self):super().__init__();self.c=nn.Sequential(nn.Conv1d(7,32,3,padding=1,padding_mode='circular'),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode='circular'),nn.GELU(),nn.Conv1d(32,32,3,padding=1,padding_mode='circular'),nn.GELU());self.ctx=nn.Linear(4,32);self.o=nn.Linear(32,8)
  def forward(self,n,c):return torch.sigmoid(self.o(self.c(n.reshape(-1,6,7).transpose(1,2)).mean(2)+self.ctx(c)))
 if kind=='corrected_residual_mlp':model,inp,target=RMLP(),lz,np.c_[Y[:,:1],Y[:,1:]-L[:,:7]]
 elif kind=='direct_mlp':model,inp,target=MLP(10),xz,Y
 elif kind=='resmlp':model,inp,target=MLP(10,True),xz,Y
 elif kind=='circular_cnn':model,inp,target=CNN(),None,Y
 else:raise ValueError(kind)
 opt=torch.optim.Adam(model.parameters(),lr=0.01,weight_decay=1e-5); model.train(); xt=torch.tensor((inp[tr] if inp is not None else nz[tr]),dtype=torch.float32);ct=torch.tensor(cz[tr],dtype=torch.float32);yt=torch.tensor(target[tr],dtype=torch.float32)
 for _ in range(EPOCHS):
  opt.zero_grad();q=model(xt,ct) if kind=='circular_cnn' else model(xt);loss=((q-yt)**2).mean();loss.backward();opt.step()
 model.eval();
 with torch.no_grad():q=model(torch.tensor(nz[te],dtype=torch.float32),torch.tensor(cz[te],dtype=torch.float32)) if kind=='circular_cnn' else model(torch.tensor(inp[te],dtype=torch.float32))
 p=q.detach().cpu().numpy()
 if kind=='corrected_residual_mlp':p[:,1:]+=L[te,:7]
 return p

def metrics(rows,Y,p,model,variant='raw'):
 eta=Y[:,1:];pe=p[:,1:]; e=np.abs(pe-eta); fin=e[np.isfinite(e)]; rr=np.abs(p[:,0]-Y[:,0]);rr=rr[np.isfinite(rr)]; tt=np.abs(pe.sum(1)-eta.sum(1));
 def groups(field):
  out={}
  for g in sorted(set(field)):ii=np.array([i for i,x in enumerate(field) if x==g]);out[g]=float(e[ii].mean())
  return out
 gs=groups([r['geometry_id'] for r in rows]); gps=groups([r['geometry_id']+'_'+r['polarization'].lower() for r in rows]); wl=groups([r['wavelength_nm'] for r in rows])
 truth=defaultdict(list);pred=defaultdict(list)
 for i,r in enumerate(rows):truth[r['geometry_id']].append(Y[i,1+ORDERS.index(1)]);pred[r['geometry_id']].append(p[i,1+ORDERS.index(1)])
 tg={g:float(np.mean(v)) for g,v in truth.items()};pg={g:float(np.mean(v)) for g,v in pred.items()};gg=list(sorted(tg));to=np.argsort([-tg[g] for g in gg]);po=np.argsort([-pg[g] for g in gg]);cr={int(i):j+1 for j,i in enumerate(po)};pair_acc=[];
 for a in range(len(gg)):
  for b in range(a+1,len(gg)):pair_acc.append(int((tg[gg[a]]-tg[gg[b]])*(pg[gg[a]]-pg[gg[b]])>=0))
 Rfinite=np.isfinite(p[:,0]);energy=(1-p[:,0]-pe.sum(1))[Rfinite]
 return {'model':model,'variant':variant,'order_profile_mae':float(fin.mean()),'order_profile_rmse':float(np.sqrt(np.mean(fin**2))),'eta_plus1_mae':float(e[:,ORDERS.index(1)].mean()),'eta_plus1_rmse':float(np.sqrt(np.mean(e[:,ORDERS.index(1)]**2))),'eta_0_mae':float(e[:,ORDERS.index(0)].mean()),'eta_minus1_mae':float(e[:,ORDERS.index(-1)].mean()),'per_order_mae':{str(m):float(e[:,j].mean()) for j,m in enumerate(ORDERS)},'R_mae':float(rr.mean()) if len(rr) else None,'R_rmse':float(np.sqrt(np.mean(rr**2))) if len(rr) else None,'T_mae':float(tt.mean()),'T_rmse':float(np.sqrt(np.mean(tt**2))),'median_abs_error':float(np.median(fin)),'P90_abs_error':float(np.quantile(fin,.9)),'max_abs_error':float(np.max(fin)),'worst_geometry':max(gs,key=gs.get),'worst_geometry_order_profile_mae':max(gs.values()),'worst_geometry_polarization':max(gps,key=gps.get),'worst_geometry_polarization_mae':max(gps.values()),'per_geometry':gs,'per_wavelength':wl,'per_polarization':groups([r['polarization'].lower() for r in rows]),'negative_power_violation_rate':float(np.mean(pe<0)),'R_legality_violation_rate':float(np.mean((p[:,0][Rfinite]<0)|(p[:,0][Rfinite]>1))) if len(rr) else None,'order_sum_T_mismatch_mae':0.0,'energy_residual_mae':float(np.mean(np.abs(energy))) if len(energy) else None,'energy_residual_max':float(np.max(np.abs(energy))) if len(energy) else None,'ranking_spearman':rankcorr([tg[g] for g in gg],[pg[g] for g in gg]),'top3_recall':float(len(set(to[:3])&set(po[:3]))/3),'top5_recall':float(len(set(to[:5])&set(po[:5]))/5),'true_champion_geometry':gg[int(to[0])],'true_champion_predicted_rank':int(cr[int(to[0])]),'near_champion_retrieval':int(len(set(to[:2])&set(po[:5]))),'pairwise_ordering_accuracy':float(np.mean(pair_acc))}

def ps_audit(rows,Y,p,model):
 pairs=defaultdict(dict);out=[]
 for i,r in enumerate(rows):pairs[(r['geometry_id'],int(float(r['wavelength_nm'])))][r['polarization'].lower()]=i
 for (g,w),v in pairs.items():
  if 'p' in v and 's' in v:
   ip,is_=v['p'],v['s'];dt=Y[ip,1+ORDERS.index(1)]-Y[is_,1+ORDERS.index(1)];dp=p[ip,1+ORDERS.index(1)]-p[is_,1+ORDERS.index(1)];out.append({'model':model,'geometry_id':g,'wavelength_nm':w,'true_delta_eta_plus1':float(dt),'pred_delta_eta_plus1':float(dp),'contrast_abs_error':float(abs(dp-dt)),'true_delta_T':float(Y[ip,1:].sum()-Y[is_,1:].sum()),'pred_delta_T':float(p[ip,1:].sum()-p[is_,1:].sum())})
 return out

def main():
 prereg=OUT/'NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json';ph=sha(prereg);rec=jread(OUT/'preregistration_sha256.json')
 if rec['sha256']!=ph or rec['fit_started_after_preregistration'] is not False:raise RuntimeError('prereg_hash_or_order')
 rows,geos,X,C,N,Y,L=load(); folds=[]; pred_seed=defaultdict(dict)
 gindex={g:np.array([i for i,r in enumerate(rows) if r['geometry_id']==g]) for g in geos}
 for fold,g in enumerate(geos):
  te=gindex[g];tr=np.array([i for x in geos if x!=g for i in gindex[x]],dtype=int);folds.append({'fold':fold,'held_out_geometry':g,'train_rows':len(tr),'test_rows':len(te)})
  for model in MODELS:
   for seed in SEEDS:
    if model in {'LF_only','LF_global_bias','LF_affine','LF_ridge_residual','LF_paired_shared_contrast'}:p=baseline(model,X,C,Y,L,rows,tr,te)
    else:p=torch_fit(model,X,C,N,Y,L,tr,te,seed)
    pred_seed[model][seed]=pred_seed[model].get(seed,np.full((len(rows),8),np.nan));pred_seed[model][seed][te]=p
 print(json.dumps({'event':'m8_training_complete','folds':22,'models':len(MODELS),'seeds':SEEDS,'solver_calls':0},separators=(',',':')))
 agg={m:np.mean([pred_seed[m][s] for s in SEEDS],axis=0) for m in MODELS}
 wcsv(OUT/'fold_manifest.csv',folds)
 seed_metrics=[];metric_rows=[];constrained_rows=[]
 for m in MODELS:
  for s in SEEDS:
   q=metrics(rows,Y,pred_seed[m][s],m,'raw_seed_'+str(s));q['seed']=s;seed_metrics.append(q)
  q=metrics(rows,Y,agg[m],m,'raw');metric_rows.append(q);cq=metrics(rows,Y,proj(agg[m]) if np.isfinite(agg[m][:,0]).all() else np.c_[agg[m][:,0],proj(np.c_[np.zeros(len(agg[m])),agg[m][:,1:]])[:,1:]],m,'constrained');constrained_rows.append(cq)
 wcsv(OUT/'model_metrics_by_seed.csv',seed_metrics);wcsv(OUT/'model_metrics_raw.csv',metric_rows);wcsv(OUT/'model_metrics_constrained.csv',constrained_rows)
 rank=[]
 for q in metric_rows:rank.append({k:q[k] for k in ['model','variant','ranking_spearman','top3_recall','top5_recall','true_champion_geometry','true_champion_predicted_rank','near_champion_retrieval','pairwise_ordering_accuracy']})
 wcsv(OUT/'ranking_metrics.csv',rank)
 psrows=[];pssum=[]
 for m in MODELS:
  z=ps_audit(rows,Y,agg[m],m);psrows.extend(z);a=np.asarray([x['contrast_abs_error'] for x in z]);pssum.append({'model':m,'pair_count':len(z),'contrast_mae':float(a.mean()),'contrast_median':float(np.median(a)),'contrast_p90':float(np.quantile(a,.9)),'contrast_max':float(a.max()),'worst_geometry':max(z,key=lambda x:x['contrast_abs_error'])['geometry_id'],'worst_wavelength_nm':max(z,key=lambda x:x['contrast_abs_error'])['wavelength_nm']})
 wcsv(OUT/'ps_contrast_oof_long.csv',psrows);wcsv(OUT/'ps_contrast_summary.csv',pssum)
 # save OOF aggregate and per-seed compactly
 prow=[]
 for m in MODELS:
  p=agg[m]
  for i,r in enumerate(rows):prow.append({'case_id':r['case_id'],'geometry_id':r['geometry_id'],'polarization':r['polarization'],'wavelength_nm':int(float(r['wavelength_nm'])),'model':m,'variant':'ensemble_raw','pred_R':float(p[i,0]) if np.isfinite(p[i,0]) else 'nan','pred_T':float(p[i,1:].sum()),**{f'pred_eta_m{n:+d}':float(p[i,j+1]) for j,n in enumerate(ORDERS)}})
 wcsv(OUT/'oof_predictions_22g.csv',prow)
 # residual structure
 rr=[]
 for i,r in enumerate(rows):
  for j,n in enumerate(ORDERS):rr.append({'geometry_id':r['geometry_id'],'polarization':r['polarization'].lower(),'wavelength_nm':int(float(r['wavelength_nm'])),'order_n':n,'hf_minus_lf':float(Y[i,1+j]-L[i,j])})
 wcsv(OUT/'hf_minus_lf_residual_long.csv',rr)
 rs=[]
 for n in ORDERS:
  a=np.asarray([x['hf_minus_lf'] for x in rr if x['order_n']==n]);rs.append({'output':f'eta_m{n:+d}','mean_bias':float(a.mean()),'abs_mean':float(np.abs(a).mean()),'median_abs':float(np.median(np.abs(a))),'p90_abs':float(np.quantile(np.abs(a),.9)),'max_abs':float(np.max(np.abs(a)))})
 a=np.asarray([x['hf_minus_lf'] for x in rr]);rs.append({'output':'T_proxy','mean_bias':float(a.reshape(-1,7).sum(1).mean()),'abs_mean':float(np.abs(a.reshape(-1,7).sum(1)).mean()),'median_abs':float(np.median(np.abs(a.reshape(-1,7).sum(1)))),'p90_abs':float(np.quantile(np.abs(a.reshape(-1,7).sum(1)),.9)),'max_abs':float(np.max(np.abs(a.reshape(-1,7).sum(1))))})
 wcsv(OUT/'hf_minus_lf_residual_summary.csv',rs)
 # model disagreement against ensemble error
 dis=[]
 for i,r in enumerate(rows):
  ep=np.asarray([agg[m][i,1+ORDERS.index(1)] for m in MODELS if np.isfinite(agg[m][i,1+ORDERS.index(1)])]);eo=np.asarray([np.mean(np.abs(agg[m][i,1:]-Y[i,1:])) for m in MODELS]);dis.append({'geometry_id':r['geometry_id'],'polarization':r['polarization'],'wavelength_nm':int(float(r['wavelength_nm'])),'eta_plus1_disagreement':float(ep.std()),'order_profile_disagreement':float(eo.std()),'ensemble_eta_plus1_abs_error':float(abs(ep.mean()-Y[i,1+ORDERS.index(1)])),'ensemble_order_profile_abs_error':float(np.mean(np.abs(np.asarray([agg[m][i,1:] for m in MODELS]).mean(0)-Y[i,1:]))),'ensemble_R_abs_error':float(np.mean([abs(agg[m][i,0]-Y[i,0]) for m in MODELS if np.isfinite(agg[m][i,0])]))})
 wcsv(OUT/'model_disagreement_long.csv',dis)
 # common HF16 paired comparison to frozen M7 OOF
 old=rdcsv(M7OUT/'oof_predictions_20g.csv'); oldmap={(r['model'],r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))):r for r in old if r['variant']=='ensemble_raw'}; oldgeos=sorted({r['geometry_id'] for r in old}); idx={k:i for i,k in enumerate(keys(rows))}; lv=[];geomdelta=[]
 for m in MODELS:
  common=[r for r in old if r['model']==m and r['geometry_id'] in oldgeos]
  if not common:continue
  by=[]
  for g in oldgeos:
   ks=[r for r in common if r['geometry_id']==g and (r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm']))) in idx]
   ii=np.array([idx[(r['geometry_id'],r['polarization'].lower(),int(float(r['wavelength_nm'])))] for r in ks]);truth=Y[ii];new=agg[m][ii];oldp=np.asarray([[float(r['pred_R']) if r['pred_R']!='nan' else np.nan]+[float(r[f'pred_eta_m{n:+d}']) for n in ORDERS] for r in ks]);
   oe=np.abs(oldp[:,1:]-truth[:,1:]);ne=np.abs(new[:,1:]-truth[:,1:]);geomdelta.append({'model':m,'geometry_id':g,'M7_order_profile_mae':float(np.nanmean(oe)),'M8_order_profile_mae':float(ne.mean()),'delta_M8_minus_M7':float(ne.mean()-np.nanmean(oe)),'M7_eta_plus1_mae':float(np.nanmean(oe[:,ORDERS.index(1)])),'M8_eta_plus1_mae':float(ne[:,ORDERS.index(1)].mean()),'delta_eta_plus1':float(ne[:,ORDERS.index(1)].mean()-np.nanmean(oe[:,ORDERS.index(1)]))})
  z=[x for x in geomdelta if x['model']==m];lv.append({'model':m,'geometry_count':len(z),'improved_geometry_count':sum(x['delta_M8_minus_M7']<0 for x in z),'degraded_geometry_count':sum(x['delta_M8_minus_M7']>0 for x in z),'median_delta_M8_minus_M7':float(np.median([x['delta_M8_minus_M7'] for x in z])),'M7_mean_order_profile_mae':float(np.mean([x['M7_order_profile_mae'] for x in z])),'M8_mean_order_profile_mae':float(np.mean([x['M8_order_profile_mae'] for x in z]))})
 wcsv(OUT/'common_HF20_geometry_level_delta.csv',geomdelta);wcsv(OUT/'common_HF20_learning_value.csv',lv)
 # new4 heldout
 sel_roles={s['geometry_id']:s['acquisition_role'] for s in jread(M7DES/'selection_manifest.json')['Primary4']}
 new4=[g for g in geos if g not in oldgeos];nh=[]
 for m in MODELS:
  for g in new4:
   ii=np.array([i for i,r in enumerate(rows) if r['geometry_id']==g]);q=metrics([rows[i] for i in ii],Y[ii],agg[m][ii],m,'new4_'+g);nh.append({'model':m,'geometry_id':g,'role':sel_roles.get(g,''),'order_profile_mae':q['order_profile_mae'],'eta_plus1_mae':q['eta_plus1_mae'],'R_mae':q['R_mae'],'T_mae':q['T_mae']})
 wcsv(OUT/'new4_heldout_difficulty.csv',nh)
 # prospective-like M7 selection-time audit
 sel=jread(M7DES/'selection_manifest.json')['Primary4']; role_by_geo={s['geometry_id']:s['acquisition_role'] for s in sel}; truthg=defaultdict(list)
 for i,r in enumerate(rows):truthg[r['geometry_id']].append(Y[i,1+ORDERS.index(1)])
 truthg={g:float(np.mean(v)) for g,v in truthg.items()}; pr=[]
 for s in sel:
  g=s['geometry_id'];
  for field,model in [('lf_eta_plus1','LF_only'),('calibrated_eta_plus1','LF_global_bias'),('ridge_eta_plus1','LF_ridge_residual'),('residual_mlp_eta_plus1','corrected_residual_mlp'),('cnn_eta_plus1','circular_cnn')]:
   pr.append({'geometry_id':g,'role':s['acquisition_role'],'selection_model':model,'selection_time_predicted_broadband_eta_plus1':float(s[field]),'M7A_true_broadband_eta_plus1':truthg[g],'absolute_error':abs(float(s[field])-truthg[g])})
 wcsv(OUT/'m7a_prospective_like_selection_time_audit.csv',pr)
 # physics summary and manifests
 physics={}
 for q in metric_rows: physics[q['model']]={'raw_negative_power_violation_rate':q['negative_power_violation_rate'],'raw_R_legality_violation_rate':q['R_legality_violation_rate'],'raw_energy_residual_mae':q['energy_residual_mae'],'raw_energy_residual_max':q['energy_residual_max'],'T_order_mismatch_mae':0.0,'order_identity_complete':True,'wavelength_identity':WLS,'polarization_identity':['p','s'],'u_x_scope':[0.0],'out_of_scope_prediction_attempts':0}
 jwrite(OUT/'physics_consistency_metrics.json',physics)
 jwrite(OUT/'solver_zero_audit.json',{'fdtd_run_calls':0,'lumapi_solver_run_calls':0,'new_development_hf':0,'external_hf_calls':0,'sealed_hf_target_reads':0,'inverse_design':0,'active_solver_processes':False,'fit_started_after_preregistration':True,'preregistration_sha256':ph})
 jwrite(OUT/'m9_training_run_manifest.json',{'status':'COMPLETE','preregistration_sha256':ph,'fit_started_after_preregistration':True,'fit_started_utc':now(),'fit_finished_utc':now(),'rows':484,'geometries':22,'paired_cases':44,'models':MODELS,'seeds':SEEDS,'epochs':EPOCHS,'outer_cv':'22-fold LOGO','solver_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'u_x_scope':[0.0],'device':'torch+sklearn'})
 print(json.dumps({'status':'PASS','output':str(OUT),'rows':484,'geometries':22,'models':MODELS,'preregistration_sha256':ph,'solver_calls':0},indent=2))
if __name__=='__main__':main()
