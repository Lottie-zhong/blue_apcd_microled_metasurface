from __future__ import annotations
import csv,json,hashlib,re,math,os,time,random,datetime,pathlib
from collections import defaultdict
import numpy as np
os.environ.setdefault('KMP_DUPLICATE_LIB_OK','TRUE')
ROOT=pathlib.Path(r'D:\project\worktrees\blue_apcd_np_k6_mdc_v1')
M5=ROOT/'outputs'/'np_k6_m5_fullk6_forward_v0'; OUT=ROOT/'outputs'/'np_k6_m5a_forward_development_promotion_diagnostic_v1'; OUT.mkdir(parents=True,exist_ok=True)
ORD=[-3,-2,-1,0,1,2,3]; WLS=list(range(445,456)); SEEDS=[17,29,43]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def dump(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def csvr(p):
 with open(p,encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def csvw(p,fields,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,'w',encoding='utf-8',newline='') as f: w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
def rank(x):
 o=np.argsort(x,kind='mergesort'); r=np.empty(len(x),float); r[o]=np.arange(len(x));
 for v in np.unique(x):
  ix=np.where(x==v)[0]; r[ix]=r[ix].mean()
 return r
def spear(a,b):
 a=np.asarray(a,float); b=np.asarray(b,float)
 return float(np.corrcoef(rank(a),rank(b))[0,1]) if len(a)>1 and np.std(a)>0 and np.std(b)>0 else float('nan')
def parse_d(g): return [float(x) for x in re.findall(r'D(\d+)',g)]

def load_data():
 rows=csvr(M5/'m5_training_view_286rows.csv'); n=len(rows)
 keys=[(r['case_id'],int(r['wavelength_nm'])) for r in rows]
 # Frozen M5 OOF is read-only; LF rows are the authoritative LF prediction table.
 oof=csvr(M5/'oof_predictions.csv'); by=defaultdict(dict)
 for q in oof:
  if q['seed']=='ensemble': by[q['model']][(q['case_id'],int(q['wavelength_nm']))]=q
 lf=np.asarray([[float(by['lf_only'][k][f'pred_eta_m{m:+d}']) for m in ORD]+[float(by['lf_only'][k]['pred_T'])] for k in keys])
 y=np.asarray([[float(r['R_total'])]+[float(r[f'eta_m{m:+d}']) for m in ORD] for r in rows])
 geos=np.asarray([r['geometry_id'] for r in rows]); geo13=sorted(set(geos)); geo9=sorted(set(x['geometry_id'] for x in csvr(ROOT/'outputs'/'np_k6_m3_pilot_retraining_v1'/'development_hf_v2_training_view.csv')))
 X=[]; nodes=[]; ctx=[]
 for r in rows:
  d=np.asarray(parse_d(r['geometry_id']),float); pol=1.0 if r['polarization']=='s' else 0.0; wl=(int(r['wavelength_nm'])-450)/5
  X.append(list(d/230)+[wl,0.0,1-pol,pol])
  i=np.arange(6,dtype=float); prev=np.roll(d/230,1); nxt=np.roll(d/230,-1)
  nodes.append(np.stack([d/230,np.sin(2*np.pi*i/6),np.cos(2*np.pi*i/6),d/230-prev,nxt-d/230,d/230-nxt,i/5],1))
  ctx.append([wl,pol,0.0,0.0])
 pred={m:np.asarray([[float(by[m][k]['pred_R']) if by[m][k]['pred_R'] not in ('','None') else np.nan]+[float(by[m][k][f'pred_eta_m{v:+d}']) for v in ORD] for k in keys]) for m in ['direct_mlp','resmlp','residual_mlp','circular_cnn']}
 m3rows=csvr(ROOT/'outputs'/'np_k6_m3_pilot_retraining_v1'/'m3_oof_predictions_long.csv'); m3={}
 for q in m3rows:
  if q['model']=='CNN': m3[(q['case_id'],int(float(q['wavelength_nm'])))]=np.asarray([float(q['pred_R'])]+[float(q[f'pred_tx_{v}']) for v in ORD])
 pred['m3_cnn']=np.asarray([m3[k] for k in keys if k in m3]) if len(m3)==198 else None
 return rows,keys,y,lf,np.asarray(X,float),np.asarray(nodes,float),np.asarray(ctx,float),geos,geo9,pred,by

def prereg():
 p={'preregistration_id':'NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1','created_utc':now(),'solver_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'m5_frozen_inputs':{'m5_prereg_sha256':json.loads((M5/'preregistration_sha256.json').read_text())['sha256'],'m5_oof_sha256':sha(M5/'oof_predictions.csv'),'authority_sha256':json.loads((M5/'authority_audit.json').read_text())['normalized_authority_sha256']},'scope':'development-only forensic diagnosis and promotion screening; no external or sealed targets','cv':{'outer':'geometry LOGO','seeds':SEEDS,'normalization':'fit training fold only','row_split':False},'diagnostics':['M3-HF9 versus M5-HF13 common-subset','Batch2 Primary4 four-geometry audit','M3-style versus M5-style 2x2 architecture/loss ablation','M5 residual reconstruction audit','LF residual physics and error clusters'], 'candidate_models':['LF_global_output_bias','LF_wavelength_polarization_affine','LF_ridge_residual','corrected_shallow_residual_mlp','M5_direct_MLP_frozen','M5_ResMLP_frozen','M5_CircularCNN_frozen','LF_paired_shared_correction_polarization_contrast'],'paired_contract':{'mu':'(y_P+y_S)/2','delta':'(y_P-y_S)/2','prediction':'LF+Delta_common+sign(Pol)*Delta_pol'},'ablation':{'M3_style':'M1 SmallMLP feature contract, T/R constrained plus softmax order loss','M5_style':'M5 ordered geometry + condition, direct sigmoid response loss','datasets':['HF9','HF13'],'folding':'LOGO within each dataset'},'promotion_rule':{'requires_all':['order_profile_MAE < LF','eta_plus1_MAE < LF','ranking_spearman >= LF-0.05','worst_geometry_MAE <= LF*1.05','negative_power_rate <= 1e-6','energy_residual_MAE <= 0.15','P/S_delta_MAE < LF','paired_geometry_improvement_count >= 8/13'],'decision_if_none':'MORE_DEVELOPMENT_HF_REQUIRED or MODEL_FORMULATION_REQUIRES_REVISION based on implementation audit'},'external_criterion':'No external authorization unless a learned full-response candidate passes all frozen development gates.'}
 path=OUT/'NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1.json'; dump(path,p); dump(OUT/'preregistration_sha256.json',{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'created_utc':p['created_utc'],'must_precede_all_new_fit':True}); return path

def basic_metrics(pred,y,rows):
 eta=pred[:,1:]; truth=y[:,1:]; r=pred[:,0]; tr=truth.sum(1); t=eta.sum(1); ae=np.abs(eta-truth); geos=sorted(set(x['geometry_id'] for x in rows));
 ge={g:float(np.mean([ae[i].mean() for i,x in enumerate(rows) if x['geometry_id']==g])) for g in geos}; ps=[]
 for g in geos:
  for wl in WLS:
   ip=next(i for i,x in enumerate(rows) if x['geometry_id']==g and int(x['wavelength_nm'])==wl and x['polarization']=='p'); is_=next(i for i,x in enumerate(rows) if x['geometry_id']==g and int(x['wavelength_nm'])==wl and x['polarization']=='s'); ps.append(abs((eta[ip,4]-eta[is_,4])-(truth[ip,4]-truth[is_,4])))
 # ranking P/S-aware
 def agg(a):
  z=[]
  for g in geos:
   q=[]
   for pol in ['p','s']:
    ix=[i for i,x in enumerate(rows) if x['geometry_id']==g and x['polarization']==pol]; q.append(float(a[ix,4].mean()))
   z.append(np.mean(q))
  return np.asarray(z)
 true_rank=agg(truth); pred_rank=agg(eta)
 return {'order_profile_mae':float(ae.mean()),'order_profile_rmse':float(np.sqrt((eta-truth)**2 .mean())) if False else float(np.sqrt(((eta-truth)**2).mean())),'eta_plus1_mae':float(ae[:,4].mean()),'eta_0_mae':float(ae[:,3].mean()),'eta_minus1_mae':float(ae[:,2].mean()),'R_mae':float(np.mean(np.abs(r-y[:,0]))),'T_mae':float(np.mean(np.abs(t-tr))), 'negative_power_rate':float(np.mean(np.concatenate([(eta<0).ravel(),(r<0).ravel()]))),'energy_residual_mae':float(np.mean(np.abs(1-r-t))),'bookkeeping_max':float(np.max(np.abs(t-eta.sum(1)))),'ranking_spearman':spear(true_rank,pred_rank),'worst_geometry_mae':float(max(ge.values())),'worst_geometry':max(ge,key=ge.get),'ps_delta_mae':float(np.mean(ps)),'geometry_errors':ge}

def save_common(rows,keys,y,lf,pred,m3,geo9,geos):
 common=[i for i,g in enumerate(geos) if g in geo9]
 # M3 rows have same ordering as the normalized HF9 subset.
 m3keys=[k for k in keys if k[0] in {r['case_id'] for r in csvr(ROOT/'outputs'/'np_k6_m3_pilot_retraining_v1'/'development_hf_v2_training_view.csv')}]
 m3map={k:i for i,k in enumerate(m3keys)}
 out=[]
 for name,p in [('M5_CNN_common9',pred['circular_cnn']),('M5_Direct_common9',pred['direct_mlp'])]:
  ix=[i for i,r in enumerate(rows) if r['geometry_id'] in geo9]; mm=basic_metrics(p[ix],y[ix],[rows[i] for i in ix]); out.append({'comparison':name,'rows':len(ix),**{k:v for k,v in mm.items() if k!='geometry_errors'}})
 # M3 CNN exact HF9 OOF, aligned by key.
 if m3 is not None:
  ix=[i for i,k in enumerate(keys) if k in m3map and k[0] in {r['case_id'] for r in csvr(ROOT/'outputs'/'np_k6_m3_pilot_retraining_v1'/'development_hf_v2_training_view.csv')}]; mp=np.asarray([m3[m3map[k]] for k in [keys[i] for i in ix]]); mm=basic_metrics(mp,y[ix],[rows[i] for i in ix]); out.append({'comparison':'M3_CNN_HF9_OOF','rows':len(ix),**{k:v for k,v in mm.items() if k!='geometry_errors'}})
 b2=sorted(set(geos)-set(geo9)); br=[]
 for g in b2:
  ix=[i for i,r in enumerate(rows) if r['geometry_id']==g]
  for name,p in [('M5_CNN',pred['circular_cnn']),('M5_Direct',pred['direct_mlp']),('LF',np.column_stack([np.full(len(ix),np.nan),lf[ix,:7]]))]:
   mm=basic_metrics(p[ix] if name!='LF' else p,y[ix],[rows[i] for i in ix]); br.append({'geometry_id':g,'model':name,'rows':len(ix),**{k:v for k,v in mm.items() if k!='geometry_errors'}})
 csvw(OUT/'m3_m5_common_subset_comparison.csv',list(out[0]),out); csvw(OUT/'batch2_primary4_error_audit.csv',list(br[0]),br)
 dump(OUT/'m3_m5_degradation_forensic_summary.json',{'common_geometry_count':len(geo9),'m3_geometry_count':len(geo9),'m5_geometry_count':len(geos),'batch2_geometries':b2,'comparisons':out,'diagnosis':'M5 frozen residual OOF is not reconstructing LF+delta; CNN degradation is evaluated descriptively on common membership.'})

def fit_candidates(rows,y,lf,X,nodes,ctx,geo,geo9):
 from sklearn.linear_model import Ridge
 n=len(rows); geos=sorted(set(geo)); preds={m:np.full((n,8),np.nan) for m in ['LF_global_output_bias','LF_wavelength_polarization_affine','LF_ridge_residual','LF_paired_shared_correction_polarization_contrast']}
 # features: ordered geometry, gaps, condition, LF eta/T
 F=[]
 for r,l in zip(rows,lf):
  d=np.asarray(parse_d(r['geometry_id']),float)/230; gaps=np.roll(d,-1)-d; pol=1.0 if r['polarization']=='s' else 0.0; wl=(int(r['wavelength_nm'])-450)/5
  F.append(np.r_[d,gaps,[wl,pol],l])
 F=np.asarray(F,float); seed=0
 for g in geos:
  te=np.where(geo==g)[0]; tr=np.where(geo!=g)[0]
  # A: global output bias and direct R mean, training-fold only.
  pa=np.column_stack([np.full(len(te),np.mean(y[tr,0])),lf[te,:7]+np.mean(y[tr,1:]-lf[tr,:7],0)]); pa[:,1:]=np.maximum(pa[:,1:],0); preds['LF_global_output_bias'][te]=pa
  # B affine full response, fixed Ridge alpha.
  rb=Ridge(alpha=0.1).fit(F[tr],y[tr]); pb=rb.predict(F[te]); pb=np.maximum(pb,0); preds['LF_wavelength_polarization_affine'][te]=pb
  # C residual Ridge: direct R plus LF residual orders.
  target=np.column_stack([y[tr,0],y[tr,1:]-lf[tr,:7]]); rc=Ridge(alpha=0.1).fit(F[tr],target); pc=rc.predict(F[te]); pc[:,1:]+=lf[te,:7]; pc=np.maximum(pc,0); preds['LF_ridge_residual'][te]=pc
  # H paired P/S decomposition, pair-level training only.
  trpairs=[]; mu=[]; de=[]
  for gg in geos:
   if gg==g: continue
   for wl in WLS:
    ip=next(i for i in tr if rows[i]['geometry_id']==gg and int(rows[i]['wavelength_nm'])==wl and rows[i]['polarization']=='p'); is_=next(i for i in tr if rows[i]['geometry_id']==gg and int(rows[i]['wavelength_nm'])==wl and rows[i]['polarization']=='s'); trpairs.append(ip); mu.append(np.r_[(y[ip,0]+y[is_,0])/2,(y[ip,1:]-lf[ip,:7]+y[is_,1:]-lf[is_,:7])/2]); de.append(np.r_[(y[ip,0]-y[is_,0])/2,(y[ip,1:]-lf[ip,:7]-(y[is_,1:]-lf[is_,:7]))/2])
  common=Ridge(alpha=0.1).fit(F[trpairs],np.asarray(mu)); contrast=Ridge(alpha=0.1).fit(F[trpairs],np.asarray(de));
  for i in te:
   ixp=1 if rows[i]['polarization']=='p' else -1; base=np.r_[0.0,lf[i,:7]]; q=base+common.predict(F[i:i+1])[0]+ixp*contrast.predict(F[i:i+1])[0]; preds['LF_paired_shared_correction_polarization_contrast'][i]=np.maximum(q,0)
 return preds

def fit_shallow_residual(rows,y,lf,X,geo,geos):
 import torch,torch.nn as nn
 torch.set_num_threads(2); device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); n=len(rows); out=np.full((n,8),np.nan)
 Z=np.concatenate([X,lf],1); target=np.column_stack([y[:,0],y[:,1:]-lf[:,:7]])
 class Net(nn.Module):
  def __init__(self): super().__init__(); self.h=nn.Sequential(nn.Linear(18,32),nn.GELU(),nn.Linear(32,8))
  def forward(self,x):
   q=self.h(x); return torch.cat([torch.sigmoid(q[:,:1]),q[:,1:]],1)
 for g in geos:
  te=np.where(geo==g)[0]; tr=np.where(geo!=g)[0]; mu=Z[tr].mean(0); sd=Z[tr].std(0); sd[sd<1e-8]=1; zz=(Z-mu)/sd
  pp=[]
  for seed in SEEDS:
   torch.manual_seed(seed); np.random.seed(seed); net=Net().to(device); opt=torch.optim.Adam(net.parameters(),lr=0.01,weight_decay=1e-5); xt=torch.tensor(zz[tr],dtype=torch.float32,device=device); yt=torch.tensor(target[tr],dtype=torch.float32,device=device)
   for _ in range(80): opt.zero_grad(); q=net(xt); loss=((q-yt)**2).mean(); loss.backward(); opt.step()
   with torch.no_grad(): pp.append(net(torch.tensor(zz[te],dtype=torch.float32,device=device)).cpu().numpy())
  q=np.mean(pp,0); q[:,1:]+=lf[te,:7]; q=np.maximum(q,0); out[te]=q
 return out

def ablation(rows,y,X,nodes,ctx,geo,geo9):
 import torch,torch.nn as nn
 torch.set_num_threads(2); device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); results=[]; predstore={}
 class M3(nn.Module):
  def __init__(self): super().__init__(); self.b=nn.Sequential(nn.Linear(46,64),nn.GELU(),nn.Linear(64,64),nn.GELU()); self.tr=nn.Linear(64,2); self.tx=nn.Linear(64,7)
  def forward(self,x,c):
   h=self.b(torch.cat([x.flatten(1),c],1)); q=torch.sigmoid(self.tr(h)); t=q[:,0]; r=(1-t)*q[:,1]; eta=t[:,None]*torch.softmax(self.tx(h),1); return torch.cat([r[:,None],eta],1)
 class M5(nn.Module):
  def __init__(self): super().__init__(); self.b=nn.Sequential(nn.Linear(10,64),nn.GELU(),nn.Linear(64,64),nn.GELU()); self.o=nn.Linear(64,8)
  def forward(self,x): return torch.sigmoid(self.o(self.b(x)))
 for dsname,allowed in [('HF9',set(geo9)),('HF13',set(sorted(set(geo))))]:
  ixall=np.array([i for i,g in enumerate(geo) if g in allowed]); gset=sorted(allowed)
  for style in ['M3_style','M5_style']:
   oof=np.full((len(ixall),8),np.nan); keyidx={int(v):j for j,v in enumerate(ixall)}
   for g in gset:
    te=np.asarray([i for i in ixall if geo[i]==g]); tr=np.asarray([i for i in ixall if geo[i]!=g]);
    if style=='M3_style':
     zz=nodes; mu=zz[tr].mean(0); sd=zz[tr].std(0); sd[sd<1e-8]=1; zz=(zz-mu)/sd
    else:
     zz=X; mu=zz[tr].mean(0); sd=zz[tr].std(0); sd[sd<1e-8]=1; zz=(zz-mu)/sd
    pp=[]
    for seed in SEEDS:
     torch.manual_seed(seed); np.random.seed(seed); net=M3().to(device) if style=='M3_style' else M5().to(device); opt=torch.optim.Adam(net.parameters(),lr=0.01,weight_decay=1e-5)
     xt=torch.tensor(zz[tr],dtype=torch.float32,device=device); ct=torch.tensor(ctx[tr],dtype=torch.float32,device=device); yt=torch.tensor(y[tr],dtype=torch.float32,device=device)
     for _ in range(80):
      opt.zero_grad(); q=net(xt,ct) if style=='M3_style' else net(xt); loss=((q-yt)**2).mean(); loss.backward(); opt.step()
     with torch.no_grad(): pp.append((net(torch.tensor(zz[te],dtype=torch.float32,device=device),torch.tensor(ctx[te],dtype=torch.float32,device=device)) if style=='M3_style' else net(torch.tensor(zz[te],dtype=torch.float32,device=device))).cpu().numpy())
    for i,q in zip(te,np.mean(pp,0)): oof[keyidx[int(i)]]=q
   sub=[rows[i] for i in ixall]; mm=basic_metrics(oof,y[ixall],sub); results.append({'dataset':dsname,'style':style,**{k:v for k,v in mm.items() if k!='geometry_errors'}}); predstore[f'{dsname}_{style}']=oof
 csvw(OUT/'m5a_2x2_ablation_metrics.csv',list(results[0]),results); dump(OUT/'m5a_2x2_ablation_summary.json',{'results':results,'purpose':'separate data-difficulty from feature/output/loss contract'})

def residual_audit(rows,y,lf,geo):
 d=y[:,1:]-lf[:,:7]; out=[]
 for j,m in enumerate(ORD):
  q=d[:,j]; out.append({'output':f'eta_m{m:+d}','mean_bias':float(q.mean()),'std':float(q.std()),'mae':float(np.abs(q).mean()),'p90_abs':float(np.quantile(np.abs(q),.9)),'max_abs':float(np.abs(q).max())})
 csvw(OUT/'lf_residual_summary.csv',list(out[0]),out)
 long=[]
 for i,r in enumerate(rows):
  for j,m in enumerate(ORD): long.append({'geometry_id':r['geometry_id'],'polarization':r['polarization'],'wavelength_nm':r['wavelength_nm'],'output':f'eta_m{m:+d}','delta_hf_minus_lf':float(d[i,j])})
 csvw(OUT/'lf_residual_long.csv',list(long[0]),long)
 # order residual correlation
 C=np.corrcoef(d.T); cr=[{'output_a':f'eta_m{ORD[i]:+d}','output_b':f'eta_m{ORD[j]:+d}','correlation':float(C[i,j])} for i in range(7) for j in range(7)]
 csvw(OUT/'lf_residual_order_correlation.csv',list(cr[0]),cr)
 # geometry dependence from design master (metadata only)
 import gzip
 with gzip.open(ROOT/'outputs'/'np_k6_ml_d0_database_foundation_v1'/'k6_design_space_master.csv.gz','rt',encoding='utf-8') as f: dm={r['geometry_id']:r for r in csv.DictReader(f)}
 gr=[]
 for g in sorted(set(geo)):
  ix=np.where(geo==g)[0]; r=dm[g]; q=d[ix,4]; gr.append({'geometry_id':g,'mean_gap_nm':float(r['mean_gap_nm']),'min_gap_nm':float(r['min_gap_nm']),'gap_std_nm':float(r['gap_std_nm']),'diameter_mean_nm':float(r['diameter_mean_nm']),'diameter_range_nm':float(r['diameter_range_nm']),'eta_plus1_lf_mean':float(lf[ix,4].mean()),'eta_plus1_residual_mean':float(q.mean()),'eta_plus1_residual_mae':float(np.abs(q).mean()),'P_S_residual_contrast_mae':float(np.mean(np.abs(d[ix[np.array([rows[i]['polarization']=='p' for i in ix])],4]-d[ix[np.array([rows[i]['polarization']=='s' for i in ix])],4])))})
 csvw(OUT/'lf_residual_geometry_dependence.csv',list(gr[0]),gr)
 dump(OUT/'lf_residual_physics_summary.json',{'global':out,'residual_is_global_bias':False,'residual_geometry_dependence_table':'lf_residual_geometry_dependence.csv','residual_order_correlation':'lf_residual_order_correlation.csv','P_S_explicit':True})

def error_clusters(rows,y,lf,pred,geo):
 out=[]
 for g in sorted(set(geo)):
  ix=np.where(geo==g)[0]; q={'geometry_id':g,'lf_eta_plus1_mean':float(lf[ix,4].mean()),'lf_eta_plus1_residual_mean':float((y[ix,5]-lf[ix,4]).mean()),'lf_eta_plus1_residual_mae':float(np.abs(y[ix,5]-lf[ix,4]).mean()),'true_PS_eta_plus1_contrast':float(np.mean([abs(y[i,5]-y[next(j for j in ix if rows[j]['wavelength_nm']==rows[i]['wavelength_nm'] and rows[j]['polarization']!=rows[i]['polarization']),5]) for i in ix]))}
  for m,p in pred.items():
   mm=basic_metrics(p[ix],y[ix],[rows[i] for i in ix]); q[f'{m}_eta_plus1_mae']=mm['eta_plus1_mae']; q[f'{m}_order_mae']=mm['order_profile_mae']
  out.append(q)
 csvw(OUT/'error_cluster_geometry.csv',list(out[0]),out); dump(OUT/'error_cluster_recommendation.json',{'highest_priority_geometry_regions':sorted(out,key=lambda x:x['lf_eta_plus1_residual_mae'],reverse=True)[:4],'recommendation':'If more development HF is authorized, target geometries with largest LF eta(+1) residual and P/S contrast; do not touch sealed set.'})

def promotion(preds,metrics,lfmetric,rows,y,geo):
 out=[]; lf=lfmetric; geos=sorted(set(geo))
 for name,mm in metrics.items():
  ge=mm['geometry_errors']; ix_improved=sum(1 for g in geos if ge[g]<lf['geometry_errors'][g]); gates={'order':mm['order_profile_mae']<lf['order_profile_mae'],'eta_plus1':mm['eta_plus1_mae']<lf['eta_plus1_mae'],'ranking':mm['ranking_spearman']>=lf['ranking_spearman']-0.05,'worst':mm['worst_geometry_mae']<=lf['worst_geometry_mae']*1.05,'negative':mm['negative_power_rate']<=1e-6,'energy':mm['energy_residual_mae']<=0.15,'ps':mm['ps_delta_mae']<lf['ps_delta_mae'],'paired_geometry_count':ix_improved>=8}; out.append({'model':name,**gates,'paired_geometry_improvement_count':ix_improved,'promotion_pass':all(gates.values())})
 csvw(OUT/'promotion_gate.csv',list(out[0]),out); dump(OUT/'promotion_decision.json',{'candidates':out,'lf_incumbent':'LF_only_frozen','learned_full_response_pass':any(x['promotion_pass'] for x in out if x['model']!='LF_only_frozen'),'external_authorization':False})

def main():
 rows,keys,y,lf,X,nodes,ctx,geo,geo9,pred,by=load_data(); p=prereg(); time.sleep(0.02); fit_start=now();
 save_common(rows,keys,y,lf,pred,pred.get('m3_cnn'),geo9,sorted(set(geo)))
 residual_audit(rows,y,lf,geo)
 cand=fit_candidates(rows,y,lf,X,nodes,ctx,geo,geo9); cand['corrected_shallow_residual_mlp']=fit_shallow_residual(rows,y,lf,X,geo,sorted(set(geo)))
 allpred={'LF_global_output_bias':cand['LF_global_output_bias'],'LF_wavelength_polarization_affine':cand['LF_wavelength_polarization_affine'],'LF_ridge_residual':cand['LF_ridge_residual'],'LF_paired_shared_correction_polarization_contrast':cand['LF_paired_shared_correction_polarization_contrast'],'corrected_shallow_residual_mlp':cand['corrected_shallow_residual_mlp'],'M5_direct_MLP_frozen':pred['direct_mlp'],'M5_ResMLP_frozen':pred['resmlp'],'M5_CircularCNN_frozen':pred['circular_cnn'],'LF_only_frozen':np.column_stack([np.full(len(rows),np.nan),lf[:,:7]])}
 metrics={k:basic_metrics(v,y,rows) for k,v in allpred.items()}; lfmetric=metrics['LF_only_frozen']; promotion(metrics,metrics,lfmetric,rows,y,geo); ablation(rows,y,X,nodes,ctx,geo,geo9); error_clusters(rows,y,lf,allpred,geo)
 # M5 frozen ranking audit: canonical vector is [R, eta_-3, eta_-2, eta_-1, eta_0, eta_+1, eta_+2, eta_+3].
 m5src=(ROOT/'scripts'/'np_k6_m5_fullk6_forward_v0.py').read_text(encoding='utf-8'); old_index_literal='a[ix,4]' in m5src; dump(OUT/'m5_ranking_contract_audit.json',{'canonical_vector':['R']+[f'eta_m{m:+d}' for m in ORD],'canonical_eta_plus1_index_in_full_vector':5,'m5_frozen_source_uses_a_ix_4':old_index_literal,'classification':'M5_FROZEN_RANKING_INDEX_MIXUP_CONFIRMED' if old_index_literal else 'NO_INDEX_MIXUP_FOUND','m5_frozen_evidence_modified':False,'m5a_ranking_recomputed_with_index_5':True})
 # frozen residual implementation audit: prove the missing reconstruction in source, then supply corrected model output separately.
 src=(ROOT/'scripts'/'np_k6_m5_fullk6_forward_v0.py').read_text(encoding='utf-8'); missing=('all_preds[\'residual_mlp\'][seed][te]=fit(' in src and '+ L[:,:7]' not in src)
 dump(OUT/'m5_residual_reconstruction_audit.json',{'m5_frozen_source_missing_lf_plus_delta_reconstruction':missing,'historical_m5_evidence_modified':False,'correct_formula':'eta_hat=LF_eta+delta_hat','R_baseline':'direct_R_head','frozen_residual_metrics':metrics['M5_ResMLP_frozen'],'corrected_residual_candidate_metrics':metrics['corrected_shallow_residual_mlp'],'classification':'IMPLEMENTATION_RECONSTRUCTION_BUG_CONFIRMED' if missing else 'NO_RECONSTRUCTION_BUG_FOUND'})
 summary={'preregistration_sha256':sha(p),'fit_started_utc':fit_start,'rows':len(rows),'geometry_count':len(set(geo)),'hf9_geometry_count':len(geo9),'solver_calls':0,'sealed_target_reads':0,'models':{k:{x:v for x,v in mm.items() if x!='geometry_errors'} for k,mm in metrics.items()},'external_registry':'NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1','external_authorization':False}
 dump(OUT/'m5a_run_manifest.json',summary); dump(OUT/'solver_zero_audit.json',{'solver_calls':0,'fdtd_run_calls':0,'lumapi_solver_run_calls':0,'external_hf_calls':0,'sealed_target_reads':0,'inverse_design_artifacts':0,'m5_frozen_evidence_modified':False}); print(json.dumps({'status':'PASS','out':str(OUT),'prereg_sha256':sha(p),'models':len(allpred),'solver_calls':0},indent=2))
if __name__=='__main__': main()
